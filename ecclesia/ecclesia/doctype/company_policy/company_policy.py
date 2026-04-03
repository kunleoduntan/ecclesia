# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import today, add_days, now_datetime, get_fullname


class CompanyPolicy(Document):

    def validate(self):
        self._validate_dates()
        self._validate_scope()

    def before_save(self):
        if self.is_new():
            self.version = 1
        self._check_content_changed()

    def on_submit(self):
        # Frappe workflow submit maps to Published for this DocType
        pass

    def on_update_after_submit(self):
        if self.status == "Published":
            self._distribute_acknowledgements()

    # ── Versioning ──────────────────────────────────────────────────

    def _check_content_changed(self):
        if self.is_new():
            return
        old = self.get_doc_before_save()
        if not old:
            return
        if old.content != self.content or old.attachment != self.attachment:
            self._snapshot_version(old)
            self.version = (old.version or 1) + 1

    def _snapshot_version(self, old_doc):
        self.append("version_history", {
            "version_number": old_doc.version or 1,
            "changed_on":     now_datetime(),
            "changed_by":     frappe.session.user,
            "change_summary": self.version_change_summary or "Content updated",
        })

    @frappe.whitelist()
    def publish_new_version(self):
        """Called from a custom button. Supersedes old published policy, resets acks."""
        old_published = frappe.get_all(
            "Company Policy",
            filters={"policy_code": self.policy_code, "status": "Published", "name": ["!=", self.name]},
            fields=["name"]
        )
        for rec in old_published:
            frappe.db.set_value("Company Policy", rec.name, "status", "Superseded")

        self.status = "Published"
        self.save()
        self._distribute_acknowledgements()
        frappe.msgprint(f"Version {self.version} published and acknowledgements distributed.", alert=True)

    # ── Acknowledgement Distribution ─────────────────────────────────

    def _distribute_acknowledgements(self):
        if not self.requires_acknowledgement:
            return

        employees = self._resolve_scope_employees()
        deadline  = add_days(today(), self.acknowledgement_deadline_days or 7)

        created = 0
        for emp in employees:
            existing = frappe.db.exists("Policy Acknowledgement", {
                "policy": self.name,
                "policy_version": self.version,
                "employee": emp.name
            })
            if existing:
                continue

            ack = frappe.get_doc({
                "doctype":        "Policy Acknowledgement",
                "policy":         self.name,
                "policy_version": self.version,
                "employee":       emp.name,
                "status":         "Pending",
            })
            ack.insert(ignore_permissions=True)
            created += 1

            # Email notification
            self._send_ack_email(emp, deadline)

        frappe.db.commit()
        frappe.msgprint(f"Acknowledgement requests sent to {created} employees.", alert=True)

    def _send_ack_email(self, employee, deadline):
        user_email = frappe.db.get_value("Employee", employee.name, "user_id")
        if not user_email:
            return

        portal_link = frappe.utils.get_url(
            f"/policy-acknowledgement?policy={self.name}&employee={employee.name}"
        )
        frappe.sendmail(
            recipients=[user_email],
            subject=f"Action Required: Acknowledge Policy — {self.title}",
            message=f"""
                <p>Dear {employee.employee_name},</p>
                <p>A new policy <strong>{self.title}</strong> (Version {self.version}) 
                has been published and requires your acknowledgement by <strong>{deadline}</strong>.</p>
                <p><a href="{portal_link}" style="padding:8px 16px;background:#534AB7;color:#fff;
                border-radius:6px;text-decoration:none">Read & Acknowledge</a></p>
                <p style="color:#888;font-size:12px">
                  If the button does not work, copy this link: {portal_link}
                </p>
            """,
            now=True
        )

    # ── Scope Resolution ─────────────────────────────────────────────

    def _resolve_scope_employees(self):
        if self.applicable_to == "All Employees":
            return frappe.get_all("Employee",
                filters={"status": "Active"},
                fields=["name", "employee_name", "user_id"]
            )

        filters = {"status": "Active"}
        for row in self.scope:
            field_map = {
                "Department":     "department",
                "Designation":    "designation",
                "Branch":         "branch",
                "Employee Group": "employee_group",
            }
            field = field_map.get(row.scope_type)
            if field:
                filters[field] = row.scope_value

        return frappe.get_all("Employee",
            filters=filters,
            fields=["name", "employee_name", "user_id"]
        )

    # ── Validation Helpers ───────────────────────────────────────────

    def _validate_dates(self):
        if self.effective_date and self.expiry_date:
            if self.expiry_date <= self.effective_date:
                frappe.throw("Expiry Date must be after Effective Date.")

    def _validate_scope(self):
        if self.applicable_to != "All Employees" and not self.scope:
            frappe.throw(
                f"You selected '{self.applicable_to}' but added no scope targets. "
                "Either switch to 'All Employees' or add rows to the Scope table."
            )