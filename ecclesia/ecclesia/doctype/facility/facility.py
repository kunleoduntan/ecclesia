# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

"""
Facility Master DocType Controller
Manages offices, warehouses, halls, guest houses, conference rooms.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate, add_days


class Facility(Document):

    def before_insert(self):
        if not self.status:
            self.status = "Active"

    def validate(self):
        self._validate_lease()
        self._set_facility_code()

    def _set_facility_code(self):
        if not self.facility_code:
            self.facility_code = self.name  # autoname already set

    def _validate_lease(self):
        if not self.is_owned and self.lease_expiry_date:
            if getdate(self.lease_expiry_date) < getdate(nowdate()):
                frappe.msgprint(
                    _("Warning: Lease for {0} expired on {1}. Please renew.").format(
                        self.facility_name, self.lease_expiry_date
                    ),
                    indicator="orange",
                )

    def update_kpis(self):
        """Recalculate KPI fields — call from maintenance request hooks."""
        open_requests = frappe.db.count(
            "Facility Maintenance Request",
            {"facility": self.name, "status": ["not in", ["Completed", "Closed", "Cancelled"]]}
        )
        self.db_set("open_maintenance_requests", open_requests)

        # Maintenance cost YTD
        year_start = frappe.utils.get_first_day(frappe.utils.add_months(nowdate(), -11))
        maint_cost = frappe.db.sql("""
            SELECT COALESCE(SUM(actual_cost), 0)
            FROM `tabMaintenance Work Order`
            WHERE facility = %s AND docstatus = 1
            AND start_date >= %s
        """, (self.name, year_start))[0][0]
        self.db_set("maintenance_cost_ytd", flt(maint_cost))

        # Utility cost YTD
        util_cost = frappe.db.sql("""
            SELECT COALESCE(SUM(total_bill), 0)
            FROM `tabUtility Consumption`
            WHERE facility = %s AND docstatus = 1
            AND reading_date >= %s
        """, (self.name, year_start))[0][0]
        self.db_set("utility_cost_ytd", flt(util_cost))


@frappe.whitelist()
def get_facility_kpis(facility):
    """Return KPI data for the dashboard HTML field."""
    doc = frappe.get_doc("Facility", facility)
    doc.update_kpis()
    return {
        "open_maintenance_requests": doc.open_maintenance_requests,
        "maintenance_cost_ytd":      doc.maintenance_cost_ytd,
        "utility_cost_ytd":          doc.utility_cost_ytd,
        "status":                    doc.status,
        "capacity":                  doc.capacity,
    }
