# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

# ecclesia/handover/handover_note.py
import frappe
from frappe.model.document import Document
from frappe.utils import today, now_datetime, get_url


class HandoverNote(Document):

    # ── Lifecycle hooks ─────────────────────────────────────────────

    def validate(self):
        self._validate_tasks_exist()
        self._validate_leave_link()
        self._set_leave_dates()
        self._default_acting_officer_on_tasks()
        self._validate_delegations()

    def on_submit(self):
        frappe.db.set_value("Handover Note", self.name, "status", "Approved")
        self._update_leave_application_link()
        self._notify_supervisor_for_review()

    def on_cancel(self):
        self._revoke_delegations()
        frappe.db.set_value("Handover Note", self.name, "status", "Closed")
        self._update_leave_application_link(status="Cancelled")

    # ── Validation helpers ───────────────────────────────────────────

    def _validate_tasks_exist(self):
        if not self.tasks:
            frappe.throw(
                "At least one task is required in the Handover Note before submission.",
                title="Tasks Required"
            )

    def _validate_leave_link(self):
        emp = frappe.db.get_value(
            "Leave Application", self.leave_application, "employee"
        )
        if emp and emp != self.employee:
            frappe.throw("The selected Leave Application does not belong to this employee.")

        status = frappe.db.get_value(
            "Leave Application", self.leave_application, "status"
        )
        if status in ("Rejected", "Cancelled"):
            frappe.throw("Cannot create a Handover Note for a rejected or cancelled leave.")

    def _set_leave_dates(self):
        if self.leave_application:
            dates = frappe.db.get_value(
                "Leave Application", self.leave_application,
                ["from_date", "to_date"], as_dict=True
            )
            if dates:
                self.leave_from = dates.from_date
                self.leave_to   = dates.to_date

    def _default_acting_officer_on_tasks(self):
        """Fill acting officer on tasks that have none, using the default."""
        if not self.default_acting_officer:
            return
        for task in self.tasks:
            if not task.acting_officer:
                task.acting_officer = self.default_acting_officer

    def _validate_delegations(self):
        for row in self.delegations:
            if row.valid_to < row.valid_from:
                frappe.throw(
                    f"Delegation row {row.idx}: Valid To must be after Valid From."
                )

    # ── Leave Application sync ───────────────────────────────────────

    def _update_leave_application_link(self, status="Submitted"):
        if self.leave_application:
            frappe.db.set_value("Leave Application", self.leave_application, {
                "custom_handover_note":   self.name if status != "Cancelled" else "",
                "custom_handover_status": status
            })

    # ── Delegation management ────────────────────────────────────────

    @frappe.whitelist()
    def activate_delegations(self):
        _activate_delegations(self)

    @frappe.whitelist()
    def revoke_delegations(self):
        _revoke_delegations(self)

    # ── Return workflow ──────────────────────────────────────────────

    @frappe.whitelist()
    def process_return(self):
        """Called when employee marks themselves as returned."""
        open_tasks = [
            t for t in self.tasks
            if t.status in ("Pending", "In Progress", "Escalated")
        ]
        frappe.db.set_value("Handover Note", self.name, {
            "status":        "Return Pending",
            "return_status": "Returned"
        })
        self._revoke_delegations()
        self._notify_return(open_tasks)
        return {"open_task_count": len(open_tasks)}

    @frappe.whitelist()
    def close_handover(self):
        """Final closure after employee has reviewed all outstanding tasks."""
        open_critical = [
            t for t in self.tasks
            if t.status in ("Pending", "In Progress") and t.priority == "Critical"
        ]
        if open_critical:
            frappe.throw(
                f"{len(open_critical)} Critical task(s) are still open. "
                "Resolve or defer them before closing the handover.",
                title="Open Critical Tasks"
            )
        frappe.db.set_value("Handover Note", self.name, {
            "status":        "Closed",
            "return_status": "Handover Closed"
        })
        frappe.msgprint("Handover closed successfully.", alert=True)

    # ── Notifications ────────────────────────────────────────────────

    def _notify_supervisor_for_review(self):
        sup_user = frappe.db.get_value("Employee", self.supervisor, "user_id")
        if not sup_user:
            return
        link = get_url(f"/app/handover-note/{self.name}")
        frappe.sendmail(
            recipients=[sup_user],
            subject=f"Handover Note awaiting your review — {self.employee_name}",
            message=f"""
                <p>Dear {self.supervisor},</p>
                <p><strong>{self.employee_name}</strong> has submitted a Handover Note
                for leave from <strong>{self.leave_from}</strong> to <strong>{self.leave_to}</strong>.
                Please review and approve before the leave commences.</p>
                <p><a href="{link}" style="padding:8px 16px;background:#534AB7;color:#fff;
                border-radius:6px;text-decoration:none">Review Handover Note</a></p>
            """,
            now=True
        )

    def _notify_return(self, open_tasks):
        emp_user = frappe.db.get_value("Employee", self.employee, "user_id")
        if not emp_user:
            return
        task_lines = "".join(
            f"<li><strong>{t.task_description}</strong> — {t.status} "
            f"(Officer: {t.acting_officer_name or 'Default'})</li>"
            for t in open_tasks
        )
        link = get_url(f"/app/handover-note/{self.name}")
        frappe.sendmail(
            recipients=[emp_user],
            subject=f"Welcome back — {len(open_tasks)} open handover task(s) await your review",
            message=f"""
                <p>Welcome back, {self.employee_name}.</p>
                <p>The following tasks were pending at the time of your return:</p>
                <ul>{task_lines or '<li>All tasks completed.</li>'}</ul>
                <p><a href="{link}">Review and close your handover</a></p>
            """,
            now=True
        )


# ── Module-level delegation helpers ─────────────────────────────────

def _activate_delegations(hn_doc):
    """Add the delegated role to the target user's Has Role records."""
    for row in hn_doc.delegations:
        user = row.delegated_to_user or frappe.db.get_value(
            "Employee", row.delegated_to, "user_id"
        )
        if not user:
            frappe.log_error(
                f"Cannot activate delegation: Employee {row.delegated_to} has no user account.",
                "Handover Delegation"
            )
            continue

        if not frappe.db.exists("Has Role", {"parent": user, "role": row.system_role}):
            user_doc = frappe.get_doc("User", user)
            user_doc.append("roles", {"role": row.system_role})
            user_doc.save(ignore_permissions=True)

        frappe.db.set_value(
            "Handover Delegation", row.name, "is_active", 1
        )

    frappe.db.commit()
    frappe.logger().info(f"[Ecclesia] Delegations activated for {hn_doc.name}")


def _revoke_delegations(hn_doc):
    """Remove delegated roles from target users — only if this was the source."""
    for row in hn_doc.delegations:
        if not row.is_active:
            continue
        user = row.delegated_to_user or frappe.db.get_value(
            "Employee", row.delegated_to, "user_id"
        )
        if not user:
            continue

        # Only revoke if no OTHER active handover grants the same role to the same user
        other_active = frappe.db.sql("""
            SELECT COUNT(*) FROM `tabHandover Delegation` hd
            JOIN `tabHandover Note` hn ON hn.name = hd.parent
            WHERE hd.delegated_to = %s
              AND hd.system_role   = %s
              AND hd.is_active     = 1
              AND hn.name         != %s
              AND hn.status        = 'Active'
        """, (row.delegated_to, row.system_role, hn_doc.name))[0][0]

        if other_active == 0:
            user_doc = frappe.get_doc("User", user)
            user_doc.roles = [r for r in user_doc.roles if r.role != row.system_role]
            user_doc.save(ignore_permissions=True)

        frappe.db.set_value("Handover Delegation", row.name, "is_active", 0)

    frappe.db.commit()
    frappe.logger().info(f"[Ecclesia] Delegations revoked for {hn_doc.name}")


def _notify_acting_officers(hn_doc):
    """Notify all unique acting officers when the leave goes active."""
    officers = {t.acting_officer for t in hn_doc.tasks if t.acting_officer}
    officers.add(hn_doc.default_acting_officer)
    officers.discard(None)

    link = get_url(f"/app/handover-note/{hn_doc.name}")
    for officer_emp in officers:
        user = frappe.db.get_value("Employee", officer_emp, "user_id")
        if not user:
            continue
        officer_tasks = [
            t for t in hn_doc.tasks
            if (t.acting_officer or hn_doc.default_acting_officer) == officer_emp
        ]
        task_lines = "".join(
            f"<li>[{t.priority}] {t.task_description} — due {t.due_date or 'no date'}</li>"
            for t in officer_tasks
        )
        frappe.sendmail(
            recipients=[user],
            subject=f"Acting cover for {hn_doc.employee_name} — {hn_doc.leave_from} to {hn_doc.leave_to}",
            message=f"""
                <p>You are the acting officer for <strong>{hn_doc.employee_name}</strong>
                who is on leave from <strong>{hn_doc.leave_from}</strong> to
                <strong>{hn_doc.leave_to}</strong>.</p>
                <p><strong>Your assigned tasks:</strong><ul>{task_lines}</ul></p>
                <p><a href="{link}">Open Handover Note</a></p>
            """,
            now=False
        )