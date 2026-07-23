# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

# ══════════════════════════════════════════════════════════════════════════════
# compliance_training_calendar.py
# ecclesia/ecclesia/doctype/compliance_training_calendar/compliance_training_calendar.py
# ══════════════════════════════════════════════════════════════════════════════

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate, flt


class ComplianceTrainingCalendar(Document):

    def validate(self):
        self._compute_completion()
        self._update_participant_count()

    def on_submit(self):
        self.db_set("status", "Scheduled")
        self._send_invites_to_participants()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _update_participant_count(self):
        if self.participants:
            self.actual_attendees = len([
                p for p in self.participants
                if p.completion_status in ("Attended","Passed","Completed")
            ])
            if self.target_headcount and self.target_headcount > 0:
                self.actual_completion_pct = round(
                    self.actual_attendees / self.target_headcount * 100, 1
                )

    def _compute_completion(self):
        if self.participants:
            completed = sum(1 for p in self.participants if p.completion_status in ("Passed","Attended"))
            total = len(self.participants)
            if total > 0:
                self.actual_completion_pct = round(completed / total * 100, 1)
                if self.actual_completion_pct >= flt(self.completion_target_pct or 100):
                    self.status = "Completed"

    def _send_invites_to_participants(self):
        if not self.participants:
            return
        for row in self.participants[:50]:  # cap at 50 to avoid massive sends
            email = frappe.db.get_value("Employee", row.employee, "company_email")
            if not email:
                continue
            frappe.sendmail(
                recipients=[email],
                subject=_(f"Compliance Training Scheduled: {self.training_category}"),
                message=_("""
                    <p>You are enrolled in a mandatory compliance training session.</p>
                    <table cellpadding="6" style="font-size:13px">
                      <tr><td><b>Training:</b></td><td>{0}</td></tr>
                      <tr><td><b>Category:</b></td><td>{1}</td></tr>
                      <tr><td><b>Date:</b></td><td>{2}</td></tr>
                      <tr><td><b>Duration:</b></td><td>{3} hours</td></tr>
                      <tr><td><b>Venue/Mode:</b></td><td>{4}</td></tr>
                      <tr><td><b>Trainer:</b></td><td>{5}</td></tr>
                    </table>
                    <p><b>This is a mandatory compliance requirement.</b>
                    Non-attendance must be approved in advance by your line manager.</p>
                    <p><a href="/Form/Compliance Training Calendar/{6}">View Training Details →</a></p>
                """).format(
                    self.calendar_title, self.training_category,
                    self.scheduled_date, self.duration_hours or "TBD",
                    self.venue or "TBD", self.trainer or "TBD", self.name
                )
            )
