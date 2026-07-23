# Copyright (c) 2026, Value Impacts Consulting
# broker/broker/doctype/crm_deal/crm_deal.py

import frappe
from frappe.model.document import Document
from frappe.utils import flt, nowdate, get_datetime
from frappe import _

STAGE_WEIGHT = {
    "Lead In": 5, "Qualified": 25, "Proposal Sent": 45,
    "Negotiation": 65, "Closed Won": 100, "Closed Lost": 0,
}


class CRMDeal(Document):

    def validate(self):
        self.update_days_in_stage()
        self.calculate_deal_health()
        self.set_ai_recommendation()
        self.set_dashboard_html()

    def update_days_in_stage(self):
        if self.stage_entered_date:
            try:
                self.days_in_stage = (get_datetime() - get_datetime(self.stage_entered_date)).days
            except Exception:
                self.days_in_stage = 0

    def calculate_deal_health(self):
        stage_s = STAGE_WEIGHT.get(self.stage or "Lead In", 20) * 0.40

        days_silent = 99
        if self.last_activity_date:
            try:
                days_silent = (get_datetime() - get_datetime(self.last_activity_date)).days
            except Exception:
                pass
        act_s = max(0, 30 - days_silent * 2)
        prob_s = flt(self.probability) * 0.15

        days_to_close = 30
        if self.close_date:
            try:
                days_to_close = (get_datetime(self.close_date) - get_datetime()).days
            except Exception:
                pass
        date_pen = 20 if days_to_close < 0 else 0

        self.deal_health_score = max(0, min(100, round(stage_s + act_s + prob_s - date_pen)))

    def set_ai_recommendation(self):
        recs = []
        days_silent = 99
        if self.last_activity_date:
            try:
                days_silent = (get_datetime() - get_datetime(self.last_activity_date)).days
            except Exception:
                pass

        if days_silent > 7:
            recs.append(f"No activity for {days_silent} days — log a call or send a follow-up.")
        if self.stage == "Proposal Sent" and days_silent > 5:
            recs.append("Proposal sent — call to confirm receipt and ask for feedback.")
        if not self.close_date:
            recs.append("Set a close date so pipeline forecasting is accurate.")
        if not recs:
            recs.append("Deal progressing well — maintain engagement cadence.")

        self.ai_recommendation = " | ".join(recs[:2])

    def set_dashboard_html(self):
        self.deal_dashboard_html = self._build_dashboard_html()

    def _build_dashboard_html(self):
        health = self.deal_health_score or 0
        h_col  = "#10B981" if health >= 70 else "#F59E0B" if health >= 40 else "#EF4444"
        stage_colors = {
            "Lead In": "#06B6D4", "Qualified": "#8B5CF6", "Proposal Sent": "#F59E0B",
            "Negotiation": "#F97316", "Closed Won": "#10B981", "Closed Lost": "#EF4444",
        }
        s_col   = stage_colors.get(self.stage or "", "#6B7280")
        circ    = 2 * 3.14159 * 32
        dashoff = circ * (1 - health / 100)
        activities = frappe.db.count("CRM Activity", {"deal": self.name}) if self.name else 0

        sw = STAGE_WEIGHT.get(self.stage or "Lead In", 20)

        # Build factor bars as a plain string (no nested f-string)
        def factor_bar(lbl, val_str, pct, col):
            return (
                '<div style="margin-bottom:8px">'
                '<div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:3px">'
                f'<span style="color:#94A3B8">{lbl}</span>'
                f'<span style="font-weight:700;color:{col}">{val_str}</span>'
                '</div>'
                '<div style="height:5px;background:#E2E8F0;border-radius:4px;overflow:hidden">'
                f'<div style="width:{pct}%;height:100%;background:{col};border-radius:4px"></div>'
                '</div></div>'
            )

        health_factors = (
            factor_bar("Stage Weight", f"{sw}/100", sw, "#8B5CF6") +
            factor_bar("Probability",  f"{flt(self.probability):.0f}%", flt(self.probability), "#2563EB") +
            factor_bar("Overall Health", f"{health}/100", health, h_col)
        )

        # AI recommendation rows
        ai_rows = "".join(
            f'<div style="display:flex;gap:7px;font-size:11px;color:#78350F;margin-bottom:4px">'
            f'<div style="width:5px;height:5px;background:#F59E0B;border-radius:50%;margin-top:4px;flex-shrink:0"></div>'
            f'{rec}</div>'
            for rec in (self.ai_recommendation or "").split(" | ")
        )

        # Detail rows
        def detail_row(label, value):
            return (
                f'<div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:6px">'
                f'<span style="color:#94A3B8">{label}</span>'
                f'<span style="font-weight:600">{value}</span></div>'
            )

        details = (
            detail_row("Account",      self.account or "—") +
            detail_row("Contact",      self.contact or "—") +
            detail_row("Close Date",   str(self.close_date) if self.close_date else "Not set") +
            detail_row("Days in Stage", f"{self.days_in_stage or 0}d") +
            detail_row("Pipeline",     self.pipeline or "Default") +
            detail_row("Territory",    self.territory or "—")
        )

        return f"""
<style>
.cd-dash{{font-family:-apple-system,'Segoe UI',system-ui,sans-serif}}
.cd-kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(148px,1fr));gap:12px;margin-bottom:16px}}
.cd-kpi{{background:#f8fafc;border:1px solid #E2E8F0;border-radius:12px;padding:14px;text-align:center;border-top-width:3px;border-top-style:solid}}
.cd-kv{{font-size:22px;font-weight:800;color:#0F172A;margin-bottom:2px}}
.cd-kl{{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#94A3B8}}
.cd-row{{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:14px}}
.cd-card{{flex:1;min-width:190px;background:#f8fafc;border:1px solid #E2E8F0;border-radius:12px;padding:14px}}
.cd-card h4{{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#94A3B8;margin:0 0 10px}}
.cd-ai{{background:#FFFBEB;border:1px solid #FDE68A;border-radius:10px;padding:12px 14px;margin-bottom:12px}}
.cd-ai h4{{font-size:11px;font-weight:700;color:#B45309;margin:0 0 6px}}
</style>
<div class="cd-dash">
  <div class="cd-kpis">
    <div class="cd-kpi" style="border-top-color:{s_col}">
      <div class="cd-kv" style="color:{s_col}">{self.stage or '—'}</div>
      <div class="cd-kl">Stage</div>
    </div>
    <div class="cd-kpi" style="border-top-color:{h_col}">
      <div style="display:flex;align-items:center;justify-content:center;gap:8px">
        <svg width="52" height="52" viewBox="0 0 76 76">
          <circle cx="38" cy="38" r="32" fill="none" stroke="#E2E8F0" stroke-width="10"/>
          <circle cx="38" cy="38" r="32" fill="none" stroke="{h_col}" stroke-width="10"
            stroke-dasharray="{circ:.1f}" stroke-dashoffset="{dashoff:.1f}"
            stroke-linecap="round" transform="rotate(-90 38 38)"/>
          <text x="38" y="44" text-anchor="middle" font-size="18" font-weight="800" fill="#0F172A">{health}</text>
        </svg>
        <div style="text-align:left">
          <div style="font-size:18px;font-weight:800;color:{h_col}">Health</div>
          <div style="font-size:10px;color:#94A3B8">AI Score</div>
        </div>
      </div>
    </div>
    <div class="cd-kpi" style="border-top-color:#2563EB">
      <div class="cd-kv">&#8358;{flt(self.deal_value)/1e6:.1f}M</div>
      <div class="cd-kl">Deal Value</div>
    </div>
    <div class="cd-kpi" style="border-top-color:#8B5CF6">
      <div class="cd-kv">{flt(self.probability):.0f}%</div>
      <div class="cd-kl">Probability</div>
    </div>
    <div class="cd-kpi" style="border-top-color:#06B6D4">
      <div class="cd-kv">{activities}</div>
      <div class="cd-kl">Activities</div>
    </div>
  </div>

  <div class="cd-row">
    <div class="cd-card">
      <h4>📋 Deal Info</h4>
      {details}
    </div>
    <div class="cd-card">
      <h4>📊 Health Factors</h4>
      {health_factors}
    </div>
  </div>

  <div class="cd-ai">
    <h4>🤖 AI Recommendation</h4>
    {ai_rows}
  </div>
</div>
"""

    def before_save(self):
        if not self.stage_entered_date:
            self.stage_entered_date = nowdate()
