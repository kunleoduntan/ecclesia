# Copyright (c) 2026, Value Impacts Consulting
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, nowdate, add_days, get_datetime
from frappe import _


class CRMLead(Document):

    def validate(self):
        self.validate_contact_info()
        self.auto_assign_territory()
        self.calculate_lead_score()
        self.set_dashboard_html()

    def validate_contact_info(self):
        """At least one contact method required."""
        if not self.email and not self.mobile_no and not self.phone:
            frappe.msgprint(
                _("Tip: Add an email or phone number to enable outreach tracking."),
                alert=True, indicator="orange"
            )

    def auto_assign_territory(self):
        """Auto-assign territory from state if not already set."""
        if self.state and not self.territory:
            territory = frappe.db.get_value(
                "CRM Territory",
                {"states": ["like", f"%{self.state}%"]},
                "name"
            )
            if territory:
                self.territory = territory

    def calculate_lead_score(self):
        """
        Multi-factor ICP scoring heuristic.
        Factors: revenue (25%), industry fit (20%), seniority (20%),
                 contact completeness (15%), engagement age (10%), source (10%)
        """
        score = 0

        # Revenue signal (25 pts)
        rev = flt(self.annual_revenue)
        if rev >= 50_000_000:   score += 25
        elif rev >= 5_000_000:  score += 20
        elif rev >= 1_000_000:  score += 14
        elif rev >= 100_000:    score += 8
        else:                   score += 2

        # Industry fit (20 pts)
        ideal_industries = {
            "Financial Services": 20, "Insurance": 20, "Oil & Gas": 18,
            "ICT / Technology": 18, "Manufacturing": 16, "Healthcare": 15,
            "Banking & Finance": 18, "Real Estate": 14, "FMCG": 12,
        }
        score += ideal_industries.get(self.industry or "", 5)

        # Seniority / role (20 pts)
        title = (self.job_title or "").lower()
        if any(kw in title for kw in ["ceo", "cfo", "cto", "managing director", "md ", "owner"]):
            score += 20
        elif any(kw in title for kw in ["director", "vp ", "vice president", "head of"]):
            score += 16
        elif any(kw in title for kw in ["manager", "lead", "senior"]):
            score += 10
        else:
            score += 3

        # Contact completeness (15 pts)
        completeness = 0
        if self.email:      completeness += 5
        if self.mobile_no:  completeness += 4
        if self.website:    completeness += 3
        if self.company_name: completeness += 3
        score += completeness

        # Source quality (10 pts)
        source_scores = {"Referral": 10, "Website": 8, "LinkedIn": 7,
                         "Exhibition": 6, "Cold Call": 4, "Email Campaign": 5}
        score += source_scores.get(self.lead_source or "", 3)

        # Engagement recency (10 pts — penalise stale leads)
        if self.modified:
            try:
                days_since = (get_datetime() - get_datetime(self.modified)).days
                if days_since <= 2:   score += 10
                elif days_since <= 7:  score += 7
                elif days_since <= 14: score += 4
                elif days_since > 30:  score -= 5
            except Exception:
                pass

        final = max(0, min(100, score))
        self.lead_score     = final
        self.icp_fit_score  = final
        self.last_score_date = nowdate()

        # Grade in score_notes
        grade = "A" if final >= 80 else "B" if final >= 60 else "C" if final >= 40 else "D"
        self.score_notes = f"Grade {grade} | Score: {final}/100 | {self._score_breakdown(final)}"

    def _score_breakdown(self, score):
        parts = []
        if self.industry:      parts.append(f"Industry: {self.industry}")
        if self.job_title:     parts.append(f"Role: {self.job_title}")
        if self.annual_revenue: parts.append(f"Revenue: ₦{flt(self.annual_revenue):,.0f}")
        return " · ".join(parts[:2]) if parts else "Incomplete profile — add firmographics for a better score"

    def set_dashboard_html(self):
        """Render the live intelligence dashboard into the HTML field."""
        self.lead_dashboard_html = self._build_dashboard_html()

    def _build_dashboard_html(self):
        score       = self.lead_score or 0
        grade       = "A" if score >= 80 else "B" if score >= 60 else "C" if score >= 40 else "D"
        grade_color = "#10B981" if score >= 80 else "#F59E0B" if score >= 60 else "#06B6D4" if score >= 40 else "#94A3B8"
        status_colors = {
            "New": "#2563EB", "Open": "#06B6D4", "Replied": "#8B5CF6",
            "Opportunity": "#F59E0B", "Qualified": "#10B981",
            "Unqualified": "#94A3B8", "Junk": "#EF4444",
            "Do Not Contact": "#EF4444", "Converted": "#10B981",
        }
        status_color = status_colors.get(self.status or "New", "#6B7280")

        # Activity summary
        activity_count = frappe.db.count("CRM Activity", {"lead": self.name}) if self.name else 0
        wa_count       = frappe.db.count("WA Conversation", {"lead": self.name}) if self.name else 0
        call_count     = frappe.db.count("Telephone Call Log",
                            {"caller_name": ["like", f"%{self.lead_name or ''}%"]}) if self.name and self.lead_name else 0

        # Score ring (SVG)
        circumference = 2 * 3.14159 * 32
        dash_offset   = circumference * (1 - score / 100)

        return f"""
<style>
.cl-dash {{font-family:-apple-system,'Segoe UI',system-ui,sans-serif;padding:8px 0}}
.cl-kpis {{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:16px}}
.cl-kpi  {{background:#f8fafc;border:1px solid #E2E8F0;border-radius:12px;padding:14px 16px;text-align:center}}
.cl-kpi-val  {{font-size:22px;font-weight:800;color:#0F172A;margin-bottom:2px}}
.cl-kpi-lbl  {{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:#94A3B8}}
.cl-row {{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:16px}}
.cl-card {{flex:1;min-width:200px;background:#f8fafc;border:1px solid #E2E8F0;border-radius:12px;padding:14px}}
.cl-card h4 {{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#94A3B8;margin:0 0 10px}}
.cl-ai  {{background:#EFF6FF;border:1px solid #BFDBFE;border-radius:10px;padding:12px 14px;margin-bottom:12px}}
.cl-ai h4 {{font-size:11px;font-weight:700;color:#2563EB;margin:0 0 6px}}
.cl-ai-item {{display:flex;gap:7px;font-size:11px;color:#1E3A5F;margin-bottom:4px}}
.cl-bullet {{width:5px;height:5px;background:#2563EB;border-radius:50%;margin-top:4px;flex-shrink:0}}
.cl-badge {{display:inline-flex;padding:3px 9px;border-radius:20px;font-size:10px;font-weight:700}}
</style>
<div class="cl-dash">
  <div class="cl-kpis">
    <div class="cl-kpi" style="border-top:3px solid {status_color}">
      <div class="cl-kpi-val" style="color:{status_color}">{self.status or 'New'}</div>
      <div class="cl-kpi-lbl">Status</div>
    </div>
    <div class="cl-kpi" style="border-top:3px solid {grade_color}">
      <div style="display:flex;align-items:center;justify-content:center;gap:8px">
        <svg width="48" height="48" viewBox="0 0 80 80">
          <circle cx="40" cy="40" r="32" fill="none" stroke="#E2E8F0" stroke-width="10"/>
          <circle cx="40" cy="40" r="32" fill="none" stroke="{grade_color}" stroke-width="10"
            stroke-dasharray="{circumference:.1f}" stroke-dashoffset="{dash_offset:.1f}"
            stroke-linecap="round" transform="rotate(-90 40 40)"/>
          <text x="40" y="46" text-anchor="middle" font-size="18" font-weight="800" fill="#0F172A">{score}</text>
        </svg>
        <div>
          <div style="font-size:22px;font-weight:800;color:{grade_color}">Grade {grade}</div>
          <div style="font-size:10px;color:#94A3B8">AI ICP Score</div>
        </div>
      </div>
    </div>
    <div class="cl-kpi" style="border-top:3px solid #8B5CF6">
      <div class="cl-kpi-val">{activity_count}</div>
      <div class="cl-kpi-lbl">Activities</div>
    </div>
    <div class="cl-kpi" style="border-top:3px solid #25D366">
      <div class="cl-kpi-val">{wa_count}</div>
      <div class="cl-kpi-lbl">WA Threads</div>
    </div>
    <div class="cl-kpi" style="border-top:3px solid #06B6D4">
      <div class="cl-kpi-val">{call_count}</div>
      <div class="cl-kpi-lbl">Calls</div>
    </div>
  </div>

  <div class="cl-row">
    <div class="cl-card">
      <h4>🏢 Firmographics</h4>
      {'<div style="display:flex;flex-direction:column;gap:5px">' +
       ''.join(f'<div style="display:flex;justify-content:space-between;font-size:12px"><span style="color:#94A3B8">{k}</span><span style="font-weight:600">{v}</span></div>'
               for k, v in [
                   ("Industry",  self.industry or "—"),
                   ("Revenue",   f"₦{flt(self.annual_revenue):,.0f}" if self.annual_revenue else "—"),
                   ("Size",      self.no_of_employees or "—"),
                   ("Territory", self.territory or "—"),
                   ("State",     self.state or "—"),
               ]) +
       '</div>'}
    </div>
    <div class="cl-card">
      <h4>👤 Contact Details</h4>
      {'<div style="display:flex;flex-direction:column;gap:5px">' +
       ''.join(f'<div style="display:flex;justify-content:space-between;font-size:12px"><span style="color:#94A3B8">{k}</span><span style="font-weight:600;max-width:160px;overflow:hidden;text-overflow:ellipsis">{v}</span></div>'
               for k, v in [
                   ("Email",    self.email or "—"),
                   ("Mobile",   self.mobile_no or "—"),
                   ("Title",    self.job_title or "—"),
                   ("Source",   self.lead_source or "—"),
                   ("Campaign", self.campaign or "—"),
               ]) +
       '</div>'}
    </div>
  </div>

  <div class="cl-ai">
    <h4>🤖 AI Score Breakdown — {self.score_notes or 'Score your lead by filling in firmographic details'}</h4>
    <div class="cl-ai-item"><div class="cl-bullet"></div>
      {"Grade A (80-100): Ideal prospect — prioritise immediately" if score >= 80 else
       "Grade B (60-79): Good fit — qualify and nurture actively" if score >= 60 else
       "Grade C (40-59): Possible fit — gather more information before investing time" if score >= 40 else
       "Grade D (0-39): Low fit — consider nurture campaign or disqualify"}
    </div>
    <div class="cl-ai-item"><div class="cl-bullet"></div>
      {"All key data present — score is reliable" if (self.email and self.industry and self.annual_revenue) else
       "Add email, industry, revenue and job title to improve score accuracy"}
    </div>
    <div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap">
      <span class="cl-badge" style="background:{grade_color}22;color:{grade_color}">ICP Grade {grade}</span>
      <span class="cl-badge" style="background:#EFF6FF;color:#2563EB">Score {score}/100</span>
      {'<span class="cl-badge" style="background:#ECFDF5;color:#10B981">✓ Email on file</span>' if self.email else ''}
      {'<span class="cl-badge" style="background:#ECFDF5;color:#10B981">✓ Mobile on file</span>' if self.mobile_no else ''}
      {'<span class="cl-badge" style="background:#F5F3FF;color:#8B5CF6">WA: {wa_count} threads</span>' if wa_count > 0 else ''}
    </div>
  </div>
</div>
"""

    def after_insert(self):
        """Auto-create first activity for immediate follow-up."""
        frappe.get_doc({
            "doctype":       "CRM Activity",
            "activity_type": "Task",
            "subject":       f"First contact: {self.lead_name or self.company_name}",
            "due_date":      add_days(nowdate(), 1),
            "lead":          self.name,
            "assigned_to":   self.assigned_to or frappe.session.user,
            "status":        "Open",
        }).insert(ignore_permissions=True)


@frappe.whitelist()
def convert_lead_to_opportunity_from_form(lead_name):
    """Called from form button — returns URL to new opportunity."""
    lead = frappe.get_doc("CRM Lead", lead_name)
    return frappe.get_doc({
        "doctype":            "CRM Opportunity",
        "opportunity_title":  f"{lead.company_name or lead.lead_name} — Opportunity",
        "lead":               lead_name,
        "assigned_to":        lead.assigned_to,
        "territory":          lead.territory,
        "status":             "Needs Analysis",
        "probability":        30,
        "expected_close_date": add_days(nowdate(), 30),
    }).insert(ignore_permissions=True).name
