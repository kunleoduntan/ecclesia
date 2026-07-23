# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt



import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import date_diff, nowdate, getdate, add_days, flt
 
 
class ExpatriatePermitRegister(Document):
 
    def validate(self):
        self._compute_days_to_expiry()
        self._update_status()
        self._validate_permit_title()
 
    def before_save(self):
        self._compute_days_to_expiry()
        self._update_status()
 
    # ── Helpers ───────────────────────────────────────────────────────────────
 
    def _compute_days_to_expiry(self):
        if self.expiry_date:
            self.days_to_expiry = date_diff(self.expiry_date, nowdate())
 
    def _update_status(self):
        if not self.expiry_date:
            return
        days = self.days_to_expiry or 0
        if self.status == "Cancelled":
            return
        if days < 0:
            self.status = "Expired"
        elif days <= 30:
            self.status = "Expiring Soon"
        elif days <= 90:
            pass  # keep current, alert will fire
        else:
            if self.status not in ("Renewing",):
                self.status = "Active"
 
    def _validate_permit_title(self):
        if not self.permit_title and self.employee and self.permit_type:
            emp_name = frappe.db.get_value("Employee", self.employee, "employee_name")
            self.permit_title = f"{emp_name} — {self.permit_type}"
 
 
@frappe.whitelist()
def get_expiring_permits(company, days=90):
    """Return permits expiring within N days."""
    cutoff = add_days(nowdate(), int(days))
    return frappe.db.get_all(
        "Expatriate Permit Register",
        filters={
            "company": company,
            "expiry_date": ["between", [nowdate(), cutoff]],
            "status": ["not in", ["Cancelled", "Expired"]]
        },
        fields=["name", "permit_title", "employee", "permit_type",
                "expiry_date", "days_to_expiry", "status", "renewal_cost"],
        order_by="expiry_date asc"
    )
 
 
@frappe.whitelist()
def get_permit_dashboard(company):
    permits = frappe.db.get_all(
        "Expatriate Permit Register",
        filters={"company": company},
        fields=["status", "permit_type"]
    )
    return {
        "total":          len(permits),
        "active":         sum(1 for p in permits if p.status == "Active"),
        "expiring_soon":  sum(1 for p in permits if p.status == "Expiring Soon"),
        "expired":        sum(1 for p in permits if p.status == "Expired"),
        "by_type": {}
    }