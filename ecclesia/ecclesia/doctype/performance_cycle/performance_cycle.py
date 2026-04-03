# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from ecclesia.utils.score_engine import compute_composite_score
from ecclesia.utils.notifications import notify_peer_reviewers, notify_results_released


class PerformanceCycle(Document):

    def validate(self):
        self._validate_weights()
        self._validate_deadlines()

    def on_submit(self):
        frappe.db.set_value("Performance Cycle", self.name, "status", "Goal Setting")
        self._create_employee_records()

    # ── Phase gate ───────────────────────────────────────────────────

    @frappe.whitelist()
    def advance_phase(self):
        gate = {
            "Goal Setting":    ("Self Appraisal",  None),
            "Self Appraisal":  ("Peer Review",     self._open_peer_review),
            "Peer Review":     ("Manager Review",  self._open_manager_review),
            "Manager Review":  ("Calibration",     self._open_calibration),
            "Calibration":     ("Results Released", self._release_results),
            "Results Released":("Closed",          None),
        }
        nxt, action = gate.get(self.status, (None, None))
        if not nxt:
            frappe.throw(f"No next phase from '{self.status}'.")
        frappe.db.set_value("Performance Cycle", self.name, "status", nxt)
        self.reload()
        if action:
            action()
        frappe.db.commit()
        return nxt

    # ── Phase actions ────────────────────────────────────────────────

    def _create_employee_records(self):
        for emp in self._resolve_employees():
            if frappe.db.exists("Employee Performance Record",
                                {"cycle": self.name, "employee": emp.name}):
                continue
            frappe.get_doc({
                "doctype": "Employee Performance Record",
                "cycle": self.name, "employee": emp.name,
                "status": "Goal Setting",
            }).insert(ignore_permissions=True)
        frappe.db.commit()

    def _open_peer_review(self):
        records = frappe.get_all("Employee Performance Record",
                                 filters={"cycle": self.name},
                                 fields=["name", "employee", "department"])
        for rec in records:
            peers = frappe.get_all("Employee Performance Record",
                                   filters={"cycle": self.name,
                                            "department": rec.department,
                                            "employee": ["!=", rec.employee]},
                                   fields=["employee"], limit=3)
            for peer in peers:
                if frappe.db.exists("Peer Review Request",
                                    {"cycle": self.name, "reviewee": rec.employee,
                                     "reviewer": peer.employee}):
                    continue
                frappe.get_doc({
                    "doctype": "Peer Review Request",
                    "cycle": self.name, "reviewee": rec.employee,
                    "reviewer": peer.employee, "relationship": "Peer",
                    "is_anonymous": 1, "status": "Pending",
                }).insert(ignore_permissions=True)
        frappe.db.commit()
        notify_peer_reviewers(self.name, self.title)

    def _open_manager_review(self):
        records = frappe.get_all("Employee Performance Record",
                                 filters={"cycle": self.name},
                                 fields=["name", "employee", "manager"])
        for rec in records:
            if not rec.manager:
                continue
            if frappe.db.exists("Manager Review", {"performance_record": rec.name}):
                continue
            frappe.get_doc({
                "doctype": "Manager Review",
                "performance_record": rec.name,
                "employee": rec.employee,
                "manager": rec.manager,
                "status": "Draft",
            }).insert(ignore_permissions=True)
        frappe.db.commit()

    def _open_calibration(self):
        depts = frappe.db.sql_list("""
            SELECT DISTINCT department FROM `tabEmployee Performance Record`
            WHERE cycle = %s AND department IS NOT NULL
        """, self.name)
        hr_emp = frappe.db.get_value(
            "Employee",
            {"user_id": frappe.db.get_value("Has Role",
                        {"role": "HR Manager", "parenttype": "User"}, "parent")},
            "name"
        )
        for dept in depts:
            if frappe.db.exists("Calibration Session",
                                {"cycle": self.name, "department": dept}):
                continue
            session = frappe.get_doc({
                "doctype": "Calibration Session",
                "title": f"{self.title} — {dept}",
                "cycle": self.name, "department": dept,
                "facilitator": hr_emp,
                "session_date": self.calibration_deadline,
                "status": "Planned",
            })
            for rec in frappe.get_all("Employee Performance Record",
                                      filters={"cycle": self.name, "department": dept},
                                      fields=["name"]):
                session.append("entries", {"performance_record": rec.name, "is_locked": 0})
            session.insert(ignore_permissions=True)
        frappe.db.commit()

    def _release_results(self):
        records = frappe.get_all("Employee Performance Record",
                                 filters={"cycle": self.name},
                                 fields=["name", "employee",
                                         "calibrated_rating", "composite_score"])
        for rec in records:
            frappe.db.set_value("Employee Performance Record",
                                rec.name, "status", "Results Released")
            notify_results_released(rec.employee, rec.name, self.title,
                                    rec.composite_score or 0,
                                    rec.calibrated_rating)
        frappe.db.commit()

    # ── Validation helpers ───────────────────────────────────────────

    def _validate_weights(self):
        total = ((self.kpi_weight or 0) + (self.manager_weight or 0) +
                 (self.peer_weight or 0) + (self.self_weight or 0))
        if abs(total - 100) > 0.01:
            frappe.throw(f"Score weights must sum to 100% — currently {total:.1f}%.")

    def _validate_deadlines(self):
        dates = [self.goal_setting_deadline, self.self_appraisal_deadline,
                 self.peer_review_deadline, self.manager_review_deadline,
                 self.calibration_deadline]
        for i in range(len(dates) - 1):
            if dates[i] and dates[i+1] and dates[i] >= dates[i+1]:
                frappe.throw("Phase deadlines must be in ascending chronological order.")

    def _resolve_employees(self):
        if self.applicable_to == "All Employees":
            return frappe.get_all("Employee", filters={"status": "Active"}, fields=["name"])
        filters = {"status": "Active"}
        field_map = {"Department": "department", "Designation": "designation",
                     "Branch": "branch", "Employee Group": "employee_group"}
        for row in (self.scope or []):
            f = field_map.get(row.scope_type)
            if f:
                filters[f] = row.scope_value
        return frappe.get_all("Employee", filters=filters, fields=["name"])