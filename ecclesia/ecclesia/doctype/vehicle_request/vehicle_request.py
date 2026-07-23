# Copyright (c) 2026, Kunle Oduntan and contributors
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate, getdate

class VehicleRequest(Document):
    def before_insert(self):
        if not self.departure_date:
            self.departure_date = nowdate()
        if not self.status:
            self.status = "Draft"

    def validate(self):
        if self.departure_date and self.return_date:
            if getdate(self.return_date) < getdate(self.departure_date):
                frappe.throw(_("Return Date cannot be before Departure Date."))

    def on_submit(self):
        self.db_set("status", "Submitted")

@frappe.whitelist()
def assign_vehicle(request_name, vehicle, driver):
    doc = frappe.get_doc("Vehicle Request", request_name)
    if doc.status not in ("Submitted", "Approved"):
        frappe.throw(_("Can only assign vehicle to Submitted or Approved requests."))
    doc.db_set("vehicle", vehicle)
    doc.db_set("driver", driver)
    doc.db_set("status", "Vehicle Assigned")
    frappe.db.set_value("Company Vehicle", vehicle, "status", "In Use")
    return "Vehicle Assigned"
