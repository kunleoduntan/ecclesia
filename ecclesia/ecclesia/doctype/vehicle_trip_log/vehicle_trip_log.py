# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

"""
Vehicle Trip Log DocType Controller
Records each trip: driver, odometer, distance, fuel.
On submit: updates vehicle current odometer and triggers vehicle analytics refresh.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class VehicleTripLog(Document):

    def validate(self):
        self._compute_distance()
        self._compute_fuel_cost()
        self._validate_odometer()

    def on_submit(self):
        self._update_vehicle_odometer()
        self._update_vehicle_status_to_available()
        self._refresh_vehicle_analytics()

    def on_cancel(self):
        self._refresh_vehicle_analytics()

    # ── Computed fields ──────────────────────────────────────────────────────

    def _compute_distance(self):
        if self.odometer_end and self.odometer_start:
            self.distance_km = flt(self.odometer_end) - flt(self.odometer_start)
            if self.distance_km < 0:
                frappe.throw(_("Odometer End must be greater than Odometer Start."))

    def _compute_fuel_cost(self):
        total = 0.0
        for row in (self.fuel_details or []):
            # auto-fill amount in the child table
            if row.litres and row.rate_per_litre:
                row.amount = flt(row.litres) * flt(row.rate_per_litre)
            total += flt(row.amount or 0)
        self.total_fuel_cost = total

    def _validate_odometer(self):
        if not self.vehicle or not self.odometer_start:
            return
        current = frappe.db.get_value("Company Vehicle", self.vehicle, "odometer_reading") or 0
        if flt(self.odometer_start) < flt(current) - 1:  # allow 1 km tolerance
            frappe.msgprint(
                _("Odometer Start ({0} km) is lower than the vehicle's current reading ({1} km). "
                  "Please verify.").format(self.odometer_start, current),
                indicator="orange",
            )

    # ── Post-submit side-effects ─────────────────────────────────────────────

    def _update_vehicle_odometer(self):
        if self.vehicle and self.odometer_end:
            frappe.db.set_value(
                "Company Vehicle", self.vehicle,
                "odometer_reading", flt(self.odometer_end),
                update_modified=False,
            )

    def _update_vehicle_status_to_available(self):
        if self.vehicle:
            current_status = frappe.db.get_value("Company Vehicle", self.vehicle, "status")
            if current_status == "In Use":
                frappe.db.set_value(
                    "Company Vehicle", self.vehicle, "status", "Available",
                    update_modified=False
                )

    def _refresh_vehicle_analytics(self):
        if self.vehicle:
            vehicle_doc = frappe.get_doc("Company Vehicle", self.vehicle)
            vehicle_doc.refresh_analytics()
