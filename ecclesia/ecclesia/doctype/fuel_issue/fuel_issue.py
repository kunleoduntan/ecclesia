# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class FuelIssue(Document):

    def validate(self):
        self._compute_total_cost()
        self._validate_litres()

    def on_submit(self):
        self._update_vehicle_odometer()

    def on_cancel(self):
        pass  # no stock ledger in this lightweight implementation

    def _compute_total_cost(self):
        if self.litres_issued and self.rate_per_litre:
            self.total_cost = flt(self.litres_issued) * flt(self.rate_per_litre)

    def _validate_litres(self):
        if flt(self.litres_issued) <= 0:
            frappe.throw(_("Litres Issued must be greater than zero."))

    def _update_vehicle_odometer(self):
        if self.vehicle and self.odometer_at_issue:
            current = frappe.db.get_value("Company Vehicle", self.vehicle, "odometer_reading") or 0
            if flt(self.odometer_at_issue) > flt(current):
                frappe.db.set_value(
                    "Company Vehicle", self.vehicle,
                    "odometer_reading", flt(self.odometer_at_issue),
                    update_modified=False,
                )
