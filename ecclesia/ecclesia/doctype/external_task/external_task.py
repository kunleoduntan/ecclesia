# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

"""
External Task Controller
Ecclesia Module

Tracks external activities: calls, letters, proposals, visits etc.
Works for any user. Auto-calculates completion metrics.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate


class ExternalTask(Document):

    def before_save(self):
        self._resolve_user_identity()
        self._auto_link_session()
        self._calc_completion()
        self._set_overall_status()

    def _resolve_user_identity(self):
        if not self.user:
            self.user = frappe.session.user
        emp = frappe.db.get_value(
            "Employee", {"user_id": self.user, "status": "Active"},
            ["name", "employee_name", "department"], as_dict=True
        )
        if emp:
            self.employee      = emp.name
            self.employee_name = emp.employee_name
            self.department    = emp.department
        elif not self.employee_name:
            self.employee_name = frappe.db.get_value("User", self.user, "full_name") or self.user

    def _auto_link_session(self):
        if not self.work_session and self.task_date == nowdate():
            sess = frappe.db.get_value(
                "Work Session",
                {"user": self.user, "date": self.task_date, "docstatus": ("!=", 2)},
                "name",
            )
            if sess:
                self.work_session = sess

    def _calc_completion(self):
        total     = len(self.items)
        completed = sum(1 for i in self.items if i.status in ("Done",))
        self.total_tasks     = total
        self.completed_tasks = completed
        self.completion_pct  = round(completed / total * 100, 1) if total else 0

    def _set_overall_status(self):
        pct = self.completion_pct
        if pct == 100:
            self.overall_status = "Completed"
        elif pct > 0:
            self.overall_status = "Partially Completed"
        else:
            self.overall_status = "In Progress"