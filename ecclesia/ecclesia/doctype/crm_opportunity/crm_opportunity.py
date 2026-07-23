# Copyright (c) 2026, Value Impacts Consulting
# broker/broker/doctype/crm_opportunity/crm_opportunity.py

import frappe
from frappe.model.document import Document
from frappe.utils import flt, nowdate, add_days, get_datetime
from frappe import _
import math


class CRMOpportunity(Document):

    # Status-based Bayesian prior for win probability
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

    def validate(self):
        self.update_days_in_status()
        self.calculate_predicted_prob()
        self.calculate_opportunity_score()
        self.set_ai_recommendation()
        self.set_dashboard_html()

    def update_days_in_status(self):
        if self.modified:
            try:
                self.days_in_status = (get_datetime() - get_datetime(self.modified)).days
            except Exception:
                self.days_in_status = 0

    def calculate_predicted_prob(self):
        """Bayesian win probability: status prior + recency lift."""
        prior = self.STATUS_PRIOR.get(self.status or "Needs Analysis", 0.30)

        # Recency lift based on last_activity_date
        days_silent = 99
        if self.last_activity_date:
            try:
                days_silent = (get_datetime() - get_datetime(self.last_activity_date)).days
            except Exception:
                pass

        recency_lift = 0.08 if days_silent <= 2 else 0 if days_silent <= 7 else -0.05 if days_silent <= 14 else -0.15

        predicted = min(0.99, max(0.01, prior + recency_lift))
        self.predicted_close_prob = round(predicted * 100)

    def calculate_opportunity_score(self):
        """Composite 0-100 score: predicted prob + value signal + recency + close timing."""
        prob_component = flt(self.predicted_close_prob)  # already 0-100

        # Value signal (0-20)
        val = flt(self.opportunity_value)
        val_s = 20 if val >= 50_000_000 else 15 if val >= 5_000_000 else 10 if val >= 1_000_000 else 5

        # Close timing (0-15 bonus; negative if overdue)
        days_to_close = 30
        if self.expected_close_date:
            try:
                days_to_close = (get_datetime(self.expected_close_date) - get_datetime()).days
            except Exception:
                pass
        timing = -15 if days_to_close < 0 else 0

        raw = (prob_component * 0.65) + val_s + timing
        self.opportunity_score = max(0, min(100, round(raw)))

    def set_ai_recommendation(self):
        recs = []
        days_silent = 99
        if self.last_activity_date:
            try:
                days_silent = (get_datetime() - get_datetime(self.last_activity_date)).days
            except Exception:
                pass

        if days_silent > 7:
            recs.append(f"Silent {days_silent} days — book a call or send a check-in email today.")
        if not self.expected_close_date:
            recs.append("No close date set — add one to appear in forecasting reports.")
        if self.status in ("Prospecting", "Needs Analysis") and flt(self.probability) < 30:
            recs.append("Consider moving to Proposal stage or disqualifying.")
        if not self.next_step:
            recs.append("Define a clear next step to keep momentum.")
        if not recs:
            recs.append("Opportunity progressing well — maintain engagement cadence.")

        self.ai_recommendation = " | ".join(recs[:2])

    def set_dashboard_html(self):
        self.opportunity_dashboard_html = self._build_dashboard_html()

    def _build_dashboard_html(self):
        score       = self.opportunity_score or 0
        prob        = self.predicted_close_prob or 0
        grade       = "A" if score >= 75 else "B" if score >= 55 else "C" if score >= 35 else "D"
        score_col   = "#10B981" if score >= 75 else "#F59E0B" if score >= 55 else "#06B6D4" if score >= 35 else "#94A3B8"
        status_cols = {
            "Prospecting":"#06B6D4","Needs Analysis":"#2563EB",
            "Value Proposition":"#8B5CF6","Proposal/Price Quote":"#F59E0B",
            "Negotiation/Review":"#F97316","Won":"#10B981","Lost":"#EF4444",
            "Closed":"#10B981","Suspended":"#94A3B8",
        }
        status_col = status_cols.get(self.status or "", "#6B7280")

        activity_count = frappe.db.count("CRM Activity", {"opportunity": self.name}) if self.name else 0
        days_silent    = 99
        if self.last_activity_date:
            try:
                days_silent = (get_datetime() - get_datetime(self.last_activity_date)).days
            except Exception:
                pass

        # SVG probability gauge
        r   = 34
        c   = 2 * 3.14159 * r
        off = c * (1 - prob / 100)
        prob_col = "#10B981" if prob >= 70 else "#F59E0B" if prob >= 40 else "#EF4444"

        return f"""
<style>
.co-dash {{font-family:-apple-system,'Segoe UI',system-ui,sans-serif}}
.co-kpis {{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:16px}}
.co-kpi  {{background:#f8fafc;border:1px solid #E2E8F0;border-radius:12px;padding:14px 16px;text-align:center}}
.co-kpi-val {{font-size:22px;font-weight:800;color:#0F172A;margin-bottom:2px}}
.co-kpi-lbl {{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:#94A3B8}}
.co-row {{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:14px}}
.co-card {{flex:1;min-width:200px;background:#f8fafc;border:1px solid #E2E8F0;border-radius:12px;padding:14px}}
.co-card h4 {{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#94A3B8;margin:0 0 10px}}
.co-ai  {{background:#F5F3FF;border:1px solid #DDD6FE;border-radius:10px;padding:12px 14px;margin-bottom:12px}}
.co-ai h4 {{font-size:11px;font-weight:700;color:#7C3AED;margin:0 0 6px}}
.co-ai-item {{display:flex;gap:7px;font-size:11px;color:#2E1065;margin-bottom:4px}}
.co-bullet  {{width:5px;height:5px;background:#7C3AED;border-radius:50%;margin-top:4px;flex-shrink:0}}
.co-row2 {{display:flex;align-items:center;justify-content:space-between;font-size:12px;margin-bottom:6px}}
.co-badge {{display:inline-flex;padding:3px 9px;border-radius:20px;font-size:10px;font-weight:700}}
</style>
<div class="co-dash">
  <div class="co-kpis">
    <div class="co-kpi" style="border-top:3px solid {status_col}">
      <div class="co-kpi-val" style="color:{status_col}">{self.status or '—'}</div>
      <div class="co-kpi-lbl">Status</div>
    </div>
    <div class="co-kpi" style="border-top:3px solid {score_col}">
      <div style="display:flex;align-items:center;justify-content:center;gap:10px">
        <svg width="76" height="76" viewBox="0 0 76 76">
          <circle cx="38" cy="38" r="{r}" fill="none" stroke="#E2E8F0" stroke-width="10"/>
          <circle cx="38" cy="38" r="{r}" fill="none" stroke="{prob_col}" stroke-width="10"
            stroke-dasharray="{c:.1f}" stroke-dashoffset="{off:.1f}"
            stroke-linecap="round" transform="rotate(-90 38 38)"/>
          <text x="38" y="43" text-anchor="middle" font-size="16" font-weight="800" fill="#0F172A">{prob}%</text>
        </svg>
        <div>
          <div style="font-size:11px;color:#94A3B8;margin-bottom:2px">AI Win Prob</div>
          <div style="font-size:18px;font-weight:800;color:{score_col}">Score {score}</div>
          <div style="font-size:11px;color:{score_col}">Grade {grade}</div>
        </div>
      </div>
    </div>
    <div class="co-kpi" style="border-top:3px solid #2563EB">
      <div class="co-kpi-val">₦{flt(self.opportunity_value)/1e6:.1f}M</div>
      <div class="co-kpi-lbl">Opportunity Value</div>
    </div>
    <div class="co-kpi" style="border-top:3px solid {'#EF4444' if days_silent > 14 else '#F59E0B' if days_silent > 7 else '#10B981'}">
      <div class="co-kpi-val" style="color:{'#EF4444' if days_silent > 14 else '#F59E0B' if days_silent > 7 else '#10B981'}">{days_silent if days_silent < 99 else '—'}d</div>
      <div class="co-kpi-lbl">Days Silent</div>
    </div>
    <div class="co-kpi" style="border-top:3px solid #8B5CF6">
      <div class="co-kpi-val">{activity_count}</div>
      <div class="co-kpi-lbl">Activities</div>
    </div>
  </div>

  <div class="co-row">
    <div class="co-card">
      <h4>📋 Deal Details</h4>
      {''.join(f'<div class="co-row2"><span style="color:#94A3B8">{k}</span><span style="font-weight:600">{v}</span></div>'
               for k, v in [
                   ("Rep Probability", f"{flt(self.probability):.0f}%"),
                   ("AI Win Prob",     f"{prob}%"),
                   ("Close Date",      str(self.expected_close_date) if self.expected_close_date else "Not set"),
                   ("Territory",       self.territory or "—"),
                   ("Source",          self.source or "—"),
                   ("Next Step",       (self.next_step or "")[:50] + "..." if len(self.next_step or "") > 50 else self.next_step or "Not defined"),
               ])}
    </div>
    <div class="co-card">
      <h4>🤖 Win Probability Factors</h4>
      <div style="font-size:11px;color:#475569;margin-bottom:10px">Bayesian model: status prior + activity recency lift</div>
      {''.join(f'''<div style="margin-bottom:8px">
        <div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:3px">
          <span style="color:#94A3B8">{lbl}</span><span style="font-weight:700;color:{col}">{val}</span>
        </div>
        <div style="height:5px;background:#E2E8F0;border-radius:4px;overflow:hidden">
          <div style="width:{pct}%;height:100%;background:{col};border-radius:4px"></div>
        </div>
      </div>'''
               for lbl, val, pct, col in [
                   ("Status Prior",    f"{self.STATUS_PRIOR.get(self.status or '', 0.3)*100:.0f}%",
                    self.STATUS_PRIOR.get(self.status or "", 0.3)*100, "#8B5CF6"),
                   ("Rep Probability", f"{flt(self.probability):.0f}%",  flt(self.probability), "#2563EB"),
                   ("AI Win Prob",     f"{prob}%",                        prob,                  prob_col),
                   ("Score",           f"{score}/100",                    score,                 "#F59E0B"),
               ])}
    </div>
  </div>

  <div class="co-ai">
    <h4>🤖 AI Recommendation</h4>
    {''.join(f'<div class="co-ai-item"><div class="co-bullet"></div>{rec}</div>' for rec in (self.ai_recommendation or "").split(" | "))}
    <div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap">
      <span class="co-badge" style="background:{score_col}22;color:{score_col}">Grade {grade} · {score}/100</span>
      <span class="co-badge" style="background:{prob_col}22;color:{prob_col}">AI Win: {prob}%</span>
      {'<span class="co-badge" style="background:#FEE2E2;color:#EF4444">🔥 Overdue</span>' if (self.expected_close_date and (get_datetime() - get_datetime(self.expected_close_date)).days > 0 if self.expected_close_date else False) else ''}
      {'<span class="co-badge" style="background:#FEF3C7;color:#F59E0B">⚡ Stale</span>' if days_silent > 14 else ''}
    </div>
  </div>
</div>
"""

    def on_submit(self):
        self.db_set("last_activity_date", nowdate())

    def promote_to_deal(self, deal_title, deal_value, stage="Qualified", close_date=None, pipeline=None):
        """Create a CRM Deal from this Opportunity and mark Opp as Closed."""
        deal = frappe.get_doc({
            "doctype":    "CRM Deal",
            "deal_title": deal_title,
            "deal_value": flt(deal_value),
            "stage":      stage,
            "close_date": close_date or add_days(nowdate(), 30),
            "pipeline":   pipeline,
            "contact":    self.contact,
            "account":    self.account,
            "assigned_to": self.assigned_to,
            "territory":  self.territory,
            "lead":       self.lead,
            "probability": flt(self.probability),
            "last_activity_date": nowdate(),
            "stage_entered_date": nowdate(),
        })
        deal.insert(ignore_permissions=True)
        self.db_set({"status": "Closed", "deal": deal.name})
        frappe.db.commit()
        return deal.name
