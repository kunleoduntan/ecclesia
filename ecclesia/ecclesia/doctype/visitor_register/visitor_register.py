# Copyright (c) 2026, Kunle Oduntan and contributors
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate, now_datetime
from frappe.utils import format_time

class VisitorRegister(Document):
    def before_insert(self):
        if not self.visit_date:
            self.visit_date = nowdate()
        if not self.status:
            self.status = "Expected"

    def validate(self):
        if self.check_in_time and self.check_out_time:
            if str(self.check_out_time) < str(self.check_in_time):
                frappe.throw(_("Check-Out Time cannot be before Check-In Time."))

@frappe.whitelist()
def check_in_visitor(visitor_name):
    """Record actual check-in time."""
    import frappe.utils
    doc = frappe.get_doc("Visitor Register", visitor_name)
    doc.db_set("check_in_time", frappe.utils.now_datetime().strftime("%H:%M:%S"))
    doc.db_set("status", "Checked In")
    return "Checked In"

@frappe.whitelist()
def check_out_visitor(visitor_name):
    import frappe.utils
    doc = frappe.get_doc("Visitor Register", visitor_name)
    doc.db_set("check_out_time", frappe.utils.now_datetime().strftime("%H:%M:%S"))
    doc.db_set("status", "Checked Out")
    return "Checked Out"
