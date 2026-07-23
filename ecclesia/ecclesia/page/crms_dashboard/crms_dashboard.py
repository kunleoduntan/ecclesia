# Copyright (c) 2026, Value Impacts Consulting
# broker/broker/page/crm_dashboard/crm_dashboard.py
#
# Whitelisted server-side API methods for the CRM Command Centre.
# All heavy aggregations, AI scoring, and cross-DocType queries live here.
# Called from JS via: frappe.call('broker.broker.page.crm_dashboard.crm_dashboard.<method>')

import frappe
from frappe import _
from frappe.utils import nowdate, add_days, flt, cint, get_first_day, get_last_day
from datetime import datetime, timedelta
import json


# ════════════════════════════════════════════════════════════════════════════
#  OVERVIEW / KPI SUMMARY
# ════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_dashboard_summary(rep=None):
    """Master KPI summary for the My Day / Overview panel."""
    today  = nowdate()
    lead_f = [["status","not in",["Converted","Junk"]]]
    deal_f = [["stage","not in",["Closed Won","Closed Lost"]]]
    if rep:
        lead_f.append(["assigned_to","=",rep])
        deal_f.append(["assigned_to","=",rep])

    leads = frappe.get_all("CRM Lead", filters=lead_f,
                           fields=["name","status","lead_score","icp_fit_score","annual_revenue","creation"], limit=1000)
    deals = frappe.get_all("CRM Deal", filters=deal_f,
                           fields=["name","stage","deal_value","probability","close_date","last_activity_date"], limit=1000)
    won   = frappe.get_all("CRM Deal", filters=[["stage","=","Closed Won"]],
                           fields=["deal_value"], limit=1000)

    pipeline_value = sum(flt(d.deal_value) for d in deals)
    won_value      = sum(flt(d.deal_value) for d in won)
    new_leads      = len([l for l in leads if l.status in ("New","Open")])
    overdue_acts   = frappe.db.count("CRM Activity",
                        {"status":["not in",["Completed","Cancelled"]],"due_date":["<",today]})
    today_acts     = frappe.db.count("CRM Activity", {"due_date":today,"status":["not in",["Completed","Cancelled"]]})
    open_wa        = frappe.db.count("WA Conversation",{"status":"Open"})

    # Win rate
    all_closed_count = len(won) + frappe.db.count("CRM Deal",{"stage":"Closed Lost"})
    win_rate = round(len(won) / max(1, all_closed_count) * 100, 1)

    # Average deal size
    avg_deal = round(pipeline_value / max(1, len(deals)))

    return {
        "pipeline_value":  pipeline_value,
        "won_value":       won_value,
        "total_leads":     len(leads),
        "new_leads":       new_leads,
        "open_deals":      len(deals),
        "win_rate":        win_rate,
        "avg_deal_size":   avg_deal,
        "overdue_activities": overdue_acts,
        "today_activities":   today_acts,
        "open_wa_threads":    open_wa,
    }


# ════════════════════════════════════════════════════════════════════════════
#  AI DEAL HEALTH SCORE  (server-side heuristic — replace with ML model)
# ════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def score_deal_health(deal_name):
    """
    Compute a 0–100 deal health score based on:
      - Stage weight (40%)
      - Activity recency (30%)
      - Probability set by rep (15%)
      - Days-to-close urgency (15%)
    Returns score, grade, urgency level, and actionable recommendation.
    """
    deal = frappe.get_doc("CRM Deal", deal_name)
    today = datetime.today()

    STAGE_WEIGHT = {
        "Lead In":       10,
        "Qualified":     25,
        "Proposal Sent": 45,
        "Negotiation":   65,
        "Closed Won":    100,
        "Closed Lost":   0,
    }
    stage_score = STAGE_WEIGHT.get(deal.stage, 20)

    # Activity recency
    last_act = deal.last_activity_date
    days_silent = (today - datetime.strptime(str(last_act)[:10], "%Y-%m-%d")).days if last_act else 99
    act_score   = max(0, 30 - (days_silent * 3))

    # Probability
    prob_score = flt(deal.probability) * 0.15

    # Days to close
    close_date = deal.close_date
    days_to_close = (datetime.strptime(str(close_date), "%Y-%m-%d") - today).days if close_date else 30
    if days_to_close < 0:
        date_penalty = 20
    elif days_to_close <= 7:
        date_penalty = 0
    else:
        date_penalty = 0

    # Weighted score
    raw  = (stage_score * 0.40) + (act_score) + (prob_score) + (30 - date_penalty) * 0.15
    score = max(0, min(100, round(raw)))
    grade = "A" if score >= 80 else "B" if score >= 60 else "C" if score >= 40 else "D"
    urgency = "high" if days_to_close < 7 or days_silent > 14 else "medium" if days_to_close < 14 or days_silent > 7 else "low"

    # Recommendation
    recs = []
    if days_silent > 7:
        recs.append(f"No activity for {days_silent} days — log a call or send a follow-up email today.")
    if deal.stage == "Proposal Sent" and days_silent > 5:
        recs.append("Proposal sent but no response — call to confirm receipt and ask for feedback.")
    if not close_date:
        recs.append("Set a close date so pipeline forecasting is accurate.")
    if flt(deal.probability) == 0:
        recs.append("Set a probability percentage to improve forecast accuracy.")
    if not recs:
        recs.append("Deal is progressing well — maintain engagement cadence.")

    # Persist score back to deal
    frappe.db.set_value("CRM Deal", deal_name, "deal_health_score", score)
    frappe.db.commit()

    return {
        "name":          deal_name,
        "score":         score,
        "grade":         grade,
        "urgency":       urgency,
        "days_silent":   days_silent,
        "days_to_close": days_to_close,
        "recommendation": recs,
        "breakdown": {
            "stage_weight":  round(stage_score * 0.40),
            "activity":      round(act_score),
            "probability":   round(prob_score),
            "close_timing":  round((30 - date_penalty) * 0.15),
        }
    }


@frappe.whitelist()
def score_all_deals(rep=None):
    """Batch-score all open deals. Call from a scheduled task nightly."""
    filters = [["stage","not in",["Closed Won","Closed Lost"]]]
    if rep:
        filters.append(["assigned_to","=",rep])
    deals = frappe.get_all("CRM Deal", filters=filters, fields=["name"], limit=1000)
    results = []
    for d in deals:
        try:
            r = score_deal_health(d.name)
            results.append(r)
        except Exception as e:
            frappe.log_error(f"CRM score error for {d.name}: {e}", "CRM Deal Scoring")
    return {"scored": len(results), "results": results}


# ════════════════════════════════════════════════════════════════════════════
#  AI LEAD SCORING  (ICP fit + engagement heuristic)
# ════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def score_lead(lead_name):
    """
    Compute a 0–100 ICP-fit score for a CRM Lead.
    Factors: firmographic fit (industry, revenue, size) + engagement signals.
    Persist to lead_score field.
    """
    lead  = frappe.get_doc("CRM Lead", lead_name)
    score = 0
    breakdown = {}

    # Firmographic fit (40 points)
    rev = flt(lead.annual_revenue)
    rev_s = 20 if rev >= 5_000_000 else 15 if rev >= 1_000_000 else 10 if rev >= 100_000 else 3
    score += rev_s
    breakdown["revenue"] = rev_s

    ind_s = 15 if lead.industry in ("Technology","Financial Services","Manufacturing","Healthcare") else 8
    score += ind_s
    breakdown["industry"] = ind_s

    role_s = 15 if lead.job_title and any(kw in (lead.job_title or "").lower() for kw in ["ceo","cfo","cto","director","vp","head","manager"]) else 5
    score += role_s
    breakdown["role"] = role_s

    # Engagement signals (60 points)
    activities = frappe.db.count("CRM Activity", {"lead": lead_name})
    act_s = min(20, activities * 5)
    score += act_s
    breakdown["activities"] = act_s

    wa_threads = frappe.db.count("WA Conversation", {"lead": lead_name})
    wa_s = min(10, wa_threads * 5)
    score += wa_s
    breakdown["wa_engagement"] = wa_s

    calls = frappe.db.count("Telephone Call Log", {"outcome_notes": ["like", f"%{lead.lead_name or ''}%"]})
    call_s = min(10, calls * 5)
    score += call_s
    breakdown["calls"] = call_s

    # Source quality bonus
    source_bonus = {"Referral": 10, "Website": 8, "LinkedIn": 7, "Exhibition": 6}.get(lead.lead_source or "", 3)
    score += source_bonus
    breakdown["source"] = source_bonus

    final = min(100, score)
    grade = "A" if final >= 80 else "B" if final >= 60 else "C" if final >= 40 else "D"

    frappe.db.set_value("CRM Lead", lead_name, {"lead_score": final, "icp_fit_score": final})
    frappe.db.commit()

    return {"name": lead_name, "score": final, "grade": grade, "breakdown": breakdown}


@frappe.whitelist()
def score_all_leads():
    """Batch-score all active leads. Intended for nightly scheduled task."""
    leads = frappe.get_all("CRM Lead",
                           filters=[["status","not in",["Converted","Junk","Do Not Contact"]]],
                           fields=["name"], limit=2000)
    results = []
    for l in leads:
        try:
            results.append(score_lead(l.name))
        except Exception as e:
            frappe.log_error(f"Lead score error {l.name}: {e}", "CRM Lead Scoring")
    return {"scored": len(results)}


# ════════════════════════════════════════════════════════════════════════════
#  NEXT BEST ACTION ENGINE
# ════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_next_best_action(rep=None):
    """
    Return the single highest-priority action for the logged-in rep.
    Priority: overdue activities > stale high-value deals > new uncontacted leads > closing deals.
    """
    today = nowdate()
    user  = rep or frappe.session.user

    # 1. Overdue activity
    overdue = frappe.get_all("CRM Activity",
        filters=[["assigned_to","=",user],["status","not in",["Completed","Cancelled"]],["due_date","<",today]],
        fields=["name","subject","activity_type","deal","lead","due_date"],
        limit=1, order_by="due_date asc")
    if overdue:
        a = overdue[0]
        return {"type":"overdue_activity","title":a.subject or a.activity_type,
                "meta":f"Overdue since {a.due_date}","link":f"/app/crm-activity/{a.name}",
                "action":"Complete activity","doc":a.name,"doctype":"CRM Activity"}

    # 2. Stale high-value deal
    stale_cutoff = add_days(today, -7)
    stale = frappe.get_all("CRM Deal",
        filters=[["assigned_to","=",user],["stage","not in",["Closed Won","Closed Lost"]],
                 ["last_activity_date","<",stale_cutoff]],
        fields=["name","deal_title","deal_value","stage","last_activity_date"],
        limit=1, order_by="deal_value desc")
    if stale:
        d = stale[0]
        days = (datetime.today() - datetime.strptime(str(d.last_activity_date)[:10],"%Y-%m-%d")).days if d.last_activity_date else 99
        return {"type":"stale_deal","title":f"Call {d.deal_title}",
                "meta":f"{days} days without activity · ₦{_fmt(d.deal_value)} · {d.stage}",
                "link":f"/app/crm-deal/{d.name}","action":"Log a call","doc":d.name,"doctype":"CRM Deal"}

    # 3. New lead uncontacted > 3 days
    old_lead_cutoff = add_days(today, -3)
    new_leads = frappe.get_all("CRM Lead",
        filters=[["assigned_to","=",user],["status","in",["New","Open"]],["creation","<",old_lead_cutoff]],
        fields=["name","lead_name","company_name","lead_source","creation"],
        limit=1, order_by="creation asc")
    if new_leads:
        l = new_leads[0]
        age = (datetime.today() - datetime.strptime(str(l.creation)[:10],"%Y-%m-%d")).days
        return {"type":"new_lead","title":f"Contact {l.lead_name or l.company_name}",
                "meta":f"New lead — {age} days since arrival, not yet contacted",
                "link":f"/app/crm-lead/{l.name}","action":"Log first activity","doc":l.name,"doctype":"CRM Lead"}

    # 4. Deal closing this week
    week_end = add_days(today, 7)
    closing = frappe.get_all("CRM Deal",
        filters=[["assigned_to","=",user],["stage","not in",["Closed Won","Closed Lost"]],
                 ["close_date",">=",today],["close_date","<=",week_end]],
        fields=["name","deal_title","deal_value","stage","close_date"],
        limit=1, order_by="close_date asc")
    if closing:
        d = closing[0]
        return {"type":"closing_deal","title":f"Push to close: {d.deal_title}",
                "meta":f"Closing {d.close_date} · ₦{_fmt(d.deal_value)} · {d.stage}",
                "link":f"/app/crm-deal/{d.name}","action":"Prepare close","doc":d.name,"doctype":"CRM Deal"}

    return {"type":"none","title":"Pipeline looks healthy!","meta":"No urgent actions right now — great job staying on top of your deals.","link":"","action":"","doc":"","doctype":""}


def _fmt(v):
    n = flt(v)
    if n >= 1_000_000: return f"₦{n/1_000_000:.1f}M"
    if n >= 1_000:     return f"₦{n/1_000:.0f}K"
    return f"₦{n:.0f}"


# ════════════════════════════════════════════════════════════════════════════
#  PIPELINE & FUNNEL ANALYTICS
# ════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_pipeline_summary(rep=None, territory=None):
    """Value and count per stage for funnel chart and Kanban header."""
    filters = []
    if rep:       filters.append(["assigned_to","=",rep])
    if territory: filters.append(["territory","=",territory])

    deals = frappe.get_all("CRM Deal", filters=filters,
                           fields=["stage","deal_value","probability","close_date","assigned_to","last_activity_date"])

    stages = ["Lead In","Qualified","Proposal Sent","Negotiation","Closed Won","Closed Lost"]
    result = {}
    for s in stages:
        sdeals = [d for d in deals if d.stage == s]
        result[s] = {
            "stage": s,
            "count": len(sdeals),
            "value": sum(flt(d.deal_value) for d in sdeals),
            "weighted_value": sum(flt(d.deal_value) * flt(d.probability) / 100 for d in sdeals),
        }

    total_closed = (result["Closed Won"]["count"] + result["Closed Lost"]["count"])
    result["win_rate"] = round(result["Closed Won"]["count"] / max(1, total_closed) * 100, 1)
    result["avg_deal_size"] = round(
        sum(flt(d.deal_value) for d in deals if d.stage not in ("Closed Won","Closed Lost")) /
        max(1, sum(1 for d in deals if d.stage not in ("Closed Won","Closed Lost")))
    )
    return result


@frappe.whitelist()
def get_revenue_trend(months=6, rep=None):
    """Monthly won revenue for the last N months."""
    today = datetime.today()
    result = []
    for i in range(months - 1, -1, -1):
        mo    = (today.replace(day=1) - timedelta(days=i*28)).replace(day=1)
        from_ = mo.strftime("%Y-%m-01")
        to_   = (mo.replace(month=mo.month%12+1, day=1) - timedelta(days=1)).strftime("%Y-%m-%d") if mo.month < 12 else f"{mo.year}-12-31"
        filters = [["stage","=","Closed Won"],["modified",">=",from_],["modified","<=",to_]]
        if rep: filters.append(["assigned_to","=",rep])
        won_this_month = frappe.get_all("CRM Deal", filters=filters, fields=["deal_value"])
        result.append({
            "month": mo.strftime("%b %Y"),
            "value": sum(flt(d.deal_value) for d in won_this_month),
            "count": len(won_this_month),
        })
    return result


@frappe.whitelist()
def get_rep_performance():
    """Leaderboard: deals, won, pipeline value, win rate per rep."""
    deals = frappe.get_all("CRM Deal",
                           fields=["assigned_to","stage","deal_value"], limit=2000)
    perf = {}
    for d in deals:
        r = d.assigned_to or "Unassigned"
        if r not in perf:
            perf[r] = {"rep":r,"deals":0,"won":0,"lost":0,"value":0}
        perf[r]["deals"] += 1
        perf[r]["value"] += flt(d.deal_value)
        if d.stage == "Closed Won":  perf[r]["won"]  += 1
        if d.stage == "Closed Lost": perf[r]["lost"] += 1

    rows = list(perf.values())
    for r in rows:
        closed = r["won"] + r["lost"]
        r["win_rate"] = round(r["won"] / max(1, closed) * 100, 1)
        r["avg_deal"] = round(r["value"] / max(1, r["deals"]))

    return sorted(rows, key=lambda x: x["won"], reverse=True)


# ════════════════════════════════════════════════════════════════════════════
#  LEAD ANALYTICS
# ════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_lead_analytics():
    """Source distribution, status counts, conversion rate."""
    leads = frappe.get_all("CRM Lead",
                           fields=["status","lead_source","territory","industry","creation"], limit=2000)

    by_source  = {}
    by_status  = {}
    by_industry= {}

    for l in leads:
        src = l.lead_source or "Unknown"
        st  = l.status      or "Unknown"
        ind = l.industry    or "Unknown"
        by_source[src]   = by_source.get(src,  0) + 1
        by_status[st]    = by_status.get(st,   0) + 1
        by_industry[ind] = by_industry.get(ind, 0) + 1

    converted = by_status.get("Converted", 0)
    conv_rate = round(converted / max(1, len(leads)) * 100, 1)

    return {
        "total":         len(leads),
        "by_source":     by_source,
        "by_status":     by_status,
        "by_industry":   by_industry,
        "conversion_rate": conv_rate,
    }


# ════════════════════════════════════════════════════════════════════════════
#  QUOTA & FORECAST
# ════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_quota_progress(rep=None):
    """Current period quota vs achieved + forecast (3-scenario)."""
    today   = nowdate()
    filters = [["period_start","<=",today],["period_end",">=",today]]
    if rep: filters.append(["rep","=",rep])

    quotas = frappe.get_all("CRM Quota Target", filters=filters,
                            fields=["name","rep","period","target_value","achieved_value","period_start","period_end"])

    result = []
    for q in quotas:
        target    = flt(q.target_value)
        achieved  = flt(q.achieved_value)
        pct       = round(achieved / max(1, target) * 100, 1)

        # Forecast: days elapsed / total days in period
        start = datetime.strptime(str(q.period_start),"%Y-%m-%d")
        end   = datetime.strptime(str(q.period_end),"%Y-%m-%d")
        now   = datetime.today()
        period_days  = max(1, (end - start).days)
        elapsed_days = max(0, (now - start).days)
        run_rate_pct = elapsed_days / period_days

        # Pipeline from open deals for this rep
        deal_filters = [["stage","not in",["Closed Won","Closed Lost"]]]
        if q.rep: deal_filters.append(["assigned_to","=",q.rep])
        pipeline = sum(flt(d.deal_value) for d in frappe.get_all("CRM Deal", filters=deal_filters, fields=["deal_value"]))
        weighted  = sum(flt(d.deal_value)*flt(d.probability)/100 for d in frappe.get_all("CRM Deal", filters=deal_filters, fields=["deal_value","probability"]))

        result.append({
            **{k:v for k,v in q.items()},
            "pct_achieved": pct,
            "gap":          max(0, target - achieved),
            "run_rate":     round(run_rate_pct * 100, 1),
            "on_track":     achieved >= (target * run_rate_pct * 0.9),
            "pipeline":     pipeline,
            "weighted_pipeline": weighted,
            "forecast_conservative": achieved + weighted * 0.5,
            "forecast_base":         achieved + weighted * 0.75,
            "forecast_optimistic":   achieved + pipeline  * 0.4,
        })

    return result


# ════════════════════════════════════════════════════════════════════════════
#  LEAD → OPPORTUNITY CONVERSION (with contact creation)
# ════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def convert_lead_to_opportunity(lead_name, opportunity_title, opportunity_value,
                                 status="Needs Analysis", probability=30,
                                 expected_close_date=None, assigned_to=None,
                                 territory=None, source=None, next_step=None):
    """
    One-click Lead → CRM Opportunity conversion.
    - Creates a CRM Contact from lead data (if not already existing)
    - Creates a CRM Opportunity linked to the lead
    - Marks lead status = 'Opportunity'
    Returns opportunity name and contact name.
    """
    lead = frappe.get_doc("CRM Lead", lead_name)

    # Create CRM Contact if not existing
    contact_name = None
    if lead.lead_name:
        existing_contact = frappe.db.get_value("CRM Contact", {"email": lead.email or "__none__"}, "name") or \
                           frappe.db.get_value("CRM Contact", {"mobile_no": lead.mobile_no or "__none__"}, "name")
        if not existing_contact:
            contact = frappe.get_doc({
                "doctype":    "CRM Contact",
                "full_name":  lead.lead_name,
                "email":      lead.email,
                "mobile_no":  lead.mobile_no,
                "company_name": lead.company_name,
                "job_title":  lead.job_title,
                "lead":       lead_name,
                "territory":  lead.territory or territory,
                "assigned_to": assigned_to or lead.assigned_to,
            })
            contact.insert(ignore_permissions=True)
            contact_name = contact.name
        else:
            contact_name = existing_contact

    # Create CRM Opportunity
    opp = frappe.get_doc({
        "doctype":              "CRM Opportunity",
        "opportunity_title":    opportunity_title,
        "opportunity_value":    flt(opportunity_value),
        "status":               status,
        "probability":          flt(probability),
        "expected_close_date":  expected_close_date or add_days(nowdate(), 30),
        "lead":                 lead_name,
        "contact":              contact_name,
        "account":              lead.company_name,
        "territory":            territory or lead.territory,
        "source":               source or lead.lead_source,
        "assigned_to":          assigned_to or lead.assigned_to,
        "next_step":            next_step or "",
        "last_activity_date":   nowdate(),
    })
    opp.insert(ignore_permissions=True)

    # Mark lead as Opportunity
    frappe.db.set_value("CRM Lead", lead_name, {
        "status": "Opportunity",
        "converted_deal": opp.name,
    })
    frappe.db.commit()

    return {"opportunity": opp.name, "contact": contact_name}


# ════════════════════════════════════════════════════════════════════════════
#  OPPORTUNITY → DEAL PROMOTION
# ════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def promote_opportunity_to_deal(opportunity_name, deal_title, deal_value,
                                 stage="Qualified", close_date=None, pipeline=None):
    """
    Promote a CRM Opportunity to a CRM Deal.
    - Creates CRM Deal linked to the Opportunity
    - Updates Opportunity status to Closed (Won pending deal outcome)
    Returns new deal name.
    """
    opp = frappe.get_doc("CRM Opportunity", opportunity_name)

    deal = frappe.get_doc({
        "doctype":       "CRM Deal",
        "deal_title":    deal_title,
        "deal_value":    flt(deal_value),
        "stage":         stage,
        "close_date":    close_date or add_days(nowdate(), 30),
        "pipeline":      pipeline,
        "contact":       opp.contact,
        "account":       opp.account,
        "assigned_to":   opp.assigned_to,
        "territory":     opp.territory,
        "lead":          opp.lead,
        "probability":   flt(opp.probability),
        "last_activity_date": nowdate(),
        "stage_entered_date": nowdate(),
    })
    deal.insert(ignore_permissions=True)

    # Mark opportunity as promoted
    frappe.db.set_value("CRM Opportunity", opportunity_name, {
        "status":      "Closed",
        "deal":        deal.name,
    })
    frappe.db.commit()

    return {"deal": deal.name, "opportunity": opportunity_name}


# ════════════════════════════════════════════════════════════════════════════
#  OPPORTUNITY AI SCORING
# ════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def score_opportunity(opportunity_name):
    """
    Score a CRM Opportunity 0–100 using:
    - Status-based Bayesian prior
    - Activity recency lift/penalty
    - Value signal
    - Days-to-close urgency
    """
    opp   = frappe.get_doc("CRM Opportunity", opportunity_name)
    today = datetime.today()

    STATUS_PRIOR = {
        "Prospecting":                  0.20,
        "Needs Analysis":               0.30,
        "Value Proposition":            0.40,
        "Identified Decision Makers":   0.50,
        "Perception Analysis":          0.55,
        "Proposal/Price Quote":         0.65,
        "Negotiation/Review":           0.75,
        "Won":  1.0, "Lost": 0.0, "Closed": 0.90, "Suspended": 0.05,
    }
    prior = STATUS_PRIOR.get(opp.status, 0.30)

    # Activity recency
    last_act = opp.last_activity_date
    days_silent = (today - datetime.strptime(str(last_act)[:10],"%Y-%m-%d")).days if last_act else 99
    recency_lift = 0.08 if days_silent <= 2 else 0 if days_silent <= 7 else -0.05 if days_silent <= 14 else -0.15

    # Value signal (larger deals get slight confidence boost)
    val    = flt(opp.opportunity_value)
    val_s  = 10 if val >= 5_000_000 else 6 if val >= 1_000_000 else 3 if val >= 100_000 else 0

    # Close date urgency
    close  = opp.expected_close_date
    days_to_close = (datetime.strptime(str(close),"%Y-%m-%d") - today).days if close else 30
    close_pen = 15 if days_to_close < 0 else 0

    predicted_prob = min(0.99, max(0.01, prior + recency_lift))
    score = round(predicted_prob * 80 + val_s - close_pen)
    score = max(0, min(100, score))
    grade = "A" if score >= 75 else "B" if score >= 55 else "C" if score >= 35 else "D"

    recs = []
    if days_silent > 7:
        recs.append(f"Silent for {days_silent} days — book a call or send a status-check email.")
    if not close:
        recs.append("No close date set — add one to improve forecast accuracy.")
    if opp.status in ("Prospecting","Needs Analysis") and flt(opp.probability) < 30:
        recs.append("Move to Proposal stage or disqualify — reduce pipeline bloat.")
    if not recs:
        recs.append("Opportunity is progressing well — maintain engagement cadence.")

    frappe.db.set_value("CRM Opportunity", opportunity_name, {
        "opportunity_score":    score,
        "predicted_close_prob": round(predicted_prob * 100),
    })
    frappe.db.commit()

    return {
        "name":           opportunity_name,
        "score":          score,
        "grade":          grade,
        "predicted_prob": round(predicted_prob * 100),
        "days_silent":    days_silent,
        "days_to_close":  days_to_close,
        "recommendation": recs,
    }


@frappe.whitelist()
def score_all_opportunities():
    """Nightly batch scoring for all open opportunities."""
    opps = frappe.get_all("CRM Opportunity",
                          filters=[["status","not in",["Won","Lost","Closed","Suspended"]]],
                          fields=["name"], limit=2000)
    results = []
    for o in opps:
        try:
            results.append(score_opportunity(o.name))
        except Exception as e:
            frappe.log_error(f"Opp score error {o.name}: {e}", "CRM Opportunity Scoring")
    return {"scored": len(results)}


# ════════════════════════════════════════════════════════════════════════════
#  LEAD VELOCITY & FUNNEL ANALYTICS
# ════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_lead_velocity(days=30):
    """
    Lead velocity: how many new leads per day are entering the funnel
    vs how many are being converted to Opportunities.
    Returns a trend array for velocity chart.
    """
    today = datetime.today()
    result = []
    for i in range(days - 1, -1, -1):
        date = add_days(nowdate(), -i)
        new_on_day  = frappe.db.count("CRM Lead", {"creation": ["like", f"{date}%"]})
        conv_on_day = frappe.db.count("CRM Lead", {"status": "Opportunity", "modified": ["like", f"{date}%"]})
        opp_on_day  = frappe.db.count("CRM Opportunity", {"creation": ["like", f"{date}%"]})
        result.append({
            "date":       date,
            "new_leads":  new_on_day,
            "converted":  conv_on_day,
            "new_opps":   opp_on_day,
        })
    return result


@frappe.whitelist()
def get_full_funnel():
    """
    Complete Lead → Opportunity → Deal → Closed Won funnel with
    conversion rates at each stage.
    """
    total_leads = frappe.db.count("CRM Lead")
    opp_leads   = frappe.db.count("CRM Lead", {"status": ["in", ["Opportunity","Converted"]]})
    total_opps  = frappe.db.count("CRM Opportunity")
    won_opps    = frappe.db.count("CRM Opportunity", {"status": "Won"})
    total_deals = frappe.db.count("CRM Deal")
    won_deals   = frappe.db.count("CRM Deal", {"stage": "Closed Won"})

    return {
        "total_leads":        total_leads,
        "leads_to_opp":       opp_leads,
        "lead_to_opp_rate":   round(opp_leads / max(1, total_leads) * 100, 1),
        "total_opportunities":total_opps,
        "opps_won":           won_opps,
        "opp_win_rate":       round(won_opps / max(1, total_opps) * 100, 1),
        "total_deals":        total_deals,
        "deals_won":          won_deals,
        "deal_win_rate":      round(won_deals / max(1, total_deals) * 100, 1),
        "end_to_end_rate":    round(won_deals / max(1, total_leads) * 100, 2),
    }


# Add to nightly_scoring_run:
@frappe.whitelist()
def nightly_scoring_run():
    """Nightly: score all open deals, opportunities, and active leads."""
    score_all_deals()
    score_all_leads()
    score_all_opportunities()
    frappe.logger().info("CRM nightly scoring run complete — deals, opportunities, leads")

@frappe.whitelist()
def convert_lead_to_deal(lead_name, deal_title, deal_value, stage="Qualified", pipeline=None, close_date=None):
    """
    Convert a CRM Lead to a CRM Deal + optionally create CRM Contact.
    Marks lead status = Converted. Returns new deal name.
    """
    lead = frappe.get_doc("CRM Lead", lead_name)

    # Create CRM Contact from lead data if it doesn't exist
    contact_name = None
    if lead.lead_name:
        existing = frappe.db.get_value("CRM Contact", {"lead": lead_name}, "name")
        if not existing:
            contact = frappe.get_doc({
                "doctype":    "CRM Contact",
                "full_name":  lead.lead_name,
                "email":      lead.email,
                "mobile_no":  lead.mobile_no,
                "company_name": lead.company_name,
                "lead":       lead_name,
                "territory":  lead.territory,
                "industry":   lead.industry,
            })
            contact.insert(ignore_permissions=True)
            contact_name = contact.name

    # Create CRM Deal
    deal = frappe.get_doc({
        "doctype":     "CRM Deal",
        "deal_title":  deal_title,
        "deal_value":  flt(deal_value),
        "stage":       stage,
        "pipeline":    pipeline,
        "close_date":  close_date or add_days(nowdate(), 30),
        "contact":     contact_name,
        "account":     lead.company_name,
        "assigned_to": lead.assigned_to,
        "territory":   lead.territory,
        "lead":        lead_name,
    })
    deal.insert(ignore_permissions=True)

    # Mark lead as converted
    frappe.db.set_value("CRM Lead", lead_name, "status", "Converted")
    frappe.db.commit()

    return {"deal": deal.name, "contact": contact_name}


# ════════════════════════════════════════════════════════════════════════════
#  DEAL STAGE MOVEMENT (with SLA timestamp + stage history)
# ════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def move_deal_stage(deal_name, new_stage, reason=None):
    """
    Move a CRM Deal to a new stage.
    Writes a CRM Stage History child record with SLA timing.
    Triggers Closed Won → Journal Entry Voucher creation if applicable.
    """
    deal = frappe.get_doc("CRM Deal", deal_name)
    old_stage    = deal.stage
    today        = nowdate()
    days_in_stage= 0

    if deal.stage_entered_date:
        try:
            days_in_stage = (datetime.strptime(today,"%Y-%m-%d") - datetime.strptime(str(deal.stage_entered_date),"%Y-%m-%d")).days
        except: pass

    # Append stage history
    deal.append("stage_history", {
        "stage":           old_stage,
        "entered_date":    deal.stage_entered_date or deal.creation,
        "exited_date":     today,
        "days_in_stage":   days_in_stage,
        "moved_by":        frappe.session.user,
        "reason":          reason or "",
    })

    deal.stage             = new_stage
    deal.stage_entered_date= today
    deal.days_in_stage     = 0
    deal.save(ignore_permissions=True)

    # Closed Won → auto-create Journal Entry Voucher (Ecclesia pattern)
    je_name = None
    if new_stage == "Closed Won" and flt(deal.deal_value) > 0:
        try:
            je_name = _create_won_je(deal)
        except Exception as e:
            frappe.log_error(f"CRM Won JE error for {deal_name}: {e}", "CRM JE Creation")

    frappe.db.commit()
    return {
        "deal":      deal_name,
        "old_stage": old_stage,
        "new_stage": new_stage,
        "days_in_old_stage": days_in_stage,
        "je_created": je_name,
    }


def _create_won_je(deal):
    """Create a Journal Entry Voucher for a Closed Won deal — uses your Ecclesia JE pattern."""
    je = frappe.get_doc({
        "doctype":   "Journal Entry Voucher",
        "voucher_type": "Journal Entry",
        "posting_date": nowdate(),
        "user_remark": f"CRM Deal Won: {deal.deal_title}",
        "accounts": [
            {
                "account":  "Accounts Receivable - {company}",
                "debit_in_account_currency": flt(deal.deal_value),
                "party_type": "Customer",
            },
            {
                "account": "Sales Revenue",
                "credit_in_account_currency": flt(deal.deal_value),
            },
        ]
    })
    je.insert(ignore_permissions=True)
    je.submit()
    return je.name


# ════════════════════════════════════════════════════════════════════════════
#  STALE DEAL ALERTS (for scheduled task)
# ════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_stale_deals(days=7, rep=None):
    """Deals with no activity in the last N days."""
    cutoff  = add_days(nowdate(), -days)
    filters = [["stage","not in",["Closed Won","Closed Lost"]],
               ["last_activity_date","<",cutoff]]
    if rep: filters.append(["assigned_to","=",rep])
    return frappe.get_all("CRM Deal", filters=filters,
                          fields=["name","deal_title","stage","deal_value","assigned_to","last_activity_date","close_date"],
                          order_by="deal_value desc", limit=50)


# ════════════════════════════════════════════════════════════════════════════
#  WA + CALL ACTIVITY LINKAGE
# ════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def link_wa_to_lead(wa_name, lead_name):
    """Link a WA Conversation to a CRM Lead (wa_conversation already has lead field)."""
    frappe.db.set_value("WA Conversation", wa_name, "lead", lead_name)
    frappe.db.commit()
    return {"linked": True}


@frappe.whitelist()
def get_contact_timeline(contact_name=None, lead_name=None):
    """
    360° timeline: activities, calls, WA messages for a contact or lead.
    Sorted by date descending for the timeline panel.
    """
    events = []
    ref_filter = {}
    if lead_name:    ref_filter = {"lead": lead_name}
    if contact_name: ref_filter = {"contact": contact_name}

    # CRM Activities
    acts = frappe.get_all("CRM Activity", filters=ref_filter,
                          fields=["name","activity_type","subject","status","due_date","outcome","creation"])
    for a in acts:
        events.append({"date": str(a.due_date or a.creation)[:10], "type":"activity",
                       "icon":"📋", "title":a.subject or a.activity_type, "meta":a.status, "link":f"/app/crm-activity/{a.name}"})

    # Telephone call logs (search by caller_name ≈ lead name — extend with crm_lead link field)
    if lead_name:
        lead = frappe.get_doc("CRM Lead", lead_name)
        if lead.lead_name:
            calls = frappe.get_all("Telephone Call Log",
                                   filters=[["caller_name","like",f"%{lead.lead_name}%"]],
                                   fields=["name","direction","status","started_at","duration_seconds","outcome_notes"])
            for c in calls:
                events.append({"date": str(c.started_at or "")[:10], "type":"call",
                               "icon":"📞", "title":f"{c.direction} Call — {c.status}",
                               "meta":f"{int(flt(c.duration_seconds)//60)}min" if c.duration_seconds else c.status,
                               "link":f"/app/telephone-call-log/{c.name}"})

        # WA Conversations linked to this lead
        wa = frappe.get_all("WA Conversation", filters={"lead": lead_name},
                            fields=["name","contact_display_name","last_message_preview","last_message_at","status"])
        for w in wa:
            events.append({"date": str(w.last_message_at or "")[:10], "type":"whatsapp",
                           "icon":"💬", "title":f"WhatsApp: {w.contact_display_name}",
                           "meta": (w.last_message_preview or "")[:80], "link":f"/app/wa-conversation/{w.name}"})

    events.sort(key=lambda x: x["date"], reverse=True)
    return events[:50]


# ════════════════════════════════════════════════════════════════════════════
#  SCHEDULED TASKS (register in hooks.py)
# ════════════════════════════════════════════════════════════════════════════
# Add to hooks.py:
#   scheduler_events = {
#       "daily": [
#           "broker.broker.page.crm_dashboard.crm_dashboard.nightly_scoring_run",
#           "broker.broker.page.crm_dashboard.crm_dashboard.send_stale_deal_alerts",
#       ]
#   }

@frappe.whitelist()
def nightly_scoring_run():
    """Nightly: score all open deals and active leads. Triggered by scheduler."""
    score_all_deals()
    score_all_leads()
    frappe.logger().info("CRM nightly scoring run complete")

@frappe.whitelist()
def send_stale_deal_alerts():
    """Nightly: email reps about stale deals."""
    stale = get_stale_deals(days=7)
    # Group by assigned_to
    by_rep = {}
    for d in stale:
        r = d.assigned_to or "Administrator"
        if r not in by_rep: by_rep[r] = []
        by_rep[r].append(d)

    for rep, deals in by_rep.items():
        email = frappe.db.get_value("User", rep, "email")
        if not email: continue
        rows = "".join(f"<tr><td>{d.deal_title}</td><td>{d.stage}</td><td>{_fmt(d.deal_value)}</td></tr>" for d in deals)
        frappe.sendmail(
            recipients=[email],
            subject=f"⚠️ {len(deals)} Stale Deal{'s' if len(deals)>1 else ''} Need Your Attention",
            message=f"""
            <p>Hi {rep.split('@')[0].title()},</p>
            <p>These deals have had no activity for 7+ days:</p>
            <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;font-size:13px">
                <thead><tr><th>Deal</th><th>Stage</th><th>Value</th></tr></thead>
                <tbody>{rows}</tbody>
            </table>
            <p><a href="/app/crm-dashboard">Open CRM Dashboard</a></p>
            """
        )