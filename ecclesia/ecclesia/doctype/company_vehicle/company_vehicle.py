# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

"""
Company Vehicle Master DocType Controller
Tracks cars, buses, trucks, forklifts.
Computes YTD cost, cost-per-km, and flags expiring documents.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate, date_diff, add_days


EXPIRY_WARN_DAYS = 30  # warn this many days before document expiry


class CompanyVehicle(Document):

    def before_insert(self):
        if not self.status:
            self.status = "Available"

    def validate(self):
        self._validate_plate_number()
        self._check_document_expiries()

    def on_update(self):
        self.refresh_analytics()

    # ── Validation ──────────────────────────────────────────────────────────

    def _validate_plate_number(self):
        if not self.plate_number:
            return
        existing = frappe.db.get_value(
            "Company Vehicle",
            {"plate_number": self.plate_number, "name": ["!=", self.name]},
            "name"
        )
        if existing:
            frappe.throw(
                _("Plate number {0} already registered to vehicle {1}.").format(
                    self.plate_number, existing
                )
            )

    def _check_document_expiries(self):
        today = getdate(nowdate())
        warn_date = add_days(today, EXPIRY_WARN_DAYS)
        for field, label in [
            ("insurance_expiry",        "Insurance"),
            ("license_expiry",          "Vehicle Licence"),
            ("road_worthiness_expiry",  "Road Worthiness"),
            ("hackney_permit_expiry",   "Hackney Permit"),
        ]:
            val = self.get(field)
            if val:
                if getdate(val) < today:
                    frappe.msgprint(
                        _("{0} for {1} has EXPIRED on {2}. Please renew immediately.").format(
                            label, self.vehicle_name, val
                        ),
                        indicator="red",
                    )
                elif getdate(val) <= warn_date:
                    frappe.msgprint(
                        _("{0} for {1} expires on {2} — within {3} days.").format(
                            label, self.vehicle_name, val, EXPIRY_WARN_DAYS
                        ),
                        indicator="orange",
                    )

    # ── Analytics ────────────────────────────────────────────────────────────

    def refresh_analytics(self):
        year_start = frappe.utils.get_first_day(
            frappe.utils.add_months(nowdate(), -11)
        )

        fuel_cost = frappe.db.sql("""
            SELECT COALESCE(SUM(total_fuel_cost), 0)
            FROM `tabVehicle Trip Log`
            WHERE vehicle = %s AND docstatus = 1 AND trip_date >= %s
        """, (self.name, year_start))[0][0]

        maint_cost = frappe.db.sql("""
            SELECT 0
        """)[0][0]  # placeholder; link via Maintenance Work Order vehicle field if added

        total_km = frappe.db.sql("""
            SELECT COALESCE(SUM(distance_km), 0)
            FROM `tabVehicle Trip Log`
            WHERE vehicle = %s AND docstatus = 1 AND trip_date >= %s
        """, (self.name, year_start))[0][0]

        trips = frappe.db.count(
            "Vehicle Trip Log",
            {"vehicle": self.name, "docstatus": 1,
             "trip_date": [">=", year_start]}
        )

        total_cost = flt(fuel_cost) + flt(maint_cost)
        cost_per_km = round(total_cost / flt(total_km), 2) if flt(total_km) > 0 else 0.0

        self.db_set("fuel_cost_ytd", flt(fuel_cost), update_modified=False)
        self.db_set("maintenance_cost_ytd", flt(maint_cost), update_modified=False)
        self.db_set("total_km_ytd", flt(total_km), update_modified=False)
        self.db_set("trips_ytd", trips, update_modified=False)
        self.db_set("cost_per_km", cost_per_km, update_modified=False)


@frappe.whitelist()
def get_vehicle_analytics(vehicle):
    """Called from JS dashboard loader."""
    doc = frappe.get_doc("Company Vehicle", vehicle)
    doc.refresh_analytics()
    return {
        "fuel_cost_ytd":       doc.fuel_cost_ytd,
        "maintenance_cost_ytd": doc.maintenance_cost_ytd,
        "total_km_ytd":        doc.total_km_ytd,
        "trips_ytd":           doc.trips_ytd,
        "cost_per_km":         doc.cost_per_km,
        "status":              doc.status,
    }


@frappe.whitelist()
def set_vehicle_status(vehicle, status):
    """Quick status update from JS button."""
    allowed = ["Available", "In Use", "Under Maintenance", "Grounded"]
    if status not in allowed:
        frappe.throw(_("Invalid status: {0}").format(status))
    frappe.db.set_value("Company Vehicle", vehicle, "status", status)
    return status
