# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

"""
Utility Consumption DocType Controller
Records monthly meter readings. Computes consumption, bill, and variance vs prior month.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class UtilityConsumption(Document):

    def validate(self):
        self._compute_consumption()
        self._compute_bill()
        self._compute_variance()
        self._validate_readings()

    def _validate_readings(self):
        if flt(self.closing_reading) < flt(self.opening_reading):
            frappe.throw(
                _("Closing Reading ({0}) cannot be less than Opening Reading ({1}).").format(
                    self.closing_reading, self.opening_reading
                )
            )

    def _compute_consumption(self):
        self.consumption = flt(self.closing_reading) - flt(self.opening_reading)

    def _compute_bill(self):
        self.consumption_cost = flt(self.consumption) * flt(self.rate_per_unit)
        self.total_bill = flt(self.consumption_cost) + flt(self.fixed_charges) + flt(self.vat_amount)

    def _compute_variance(self):
        """Compare to the previous month's record for the same meter."""
        prev = frappe.db.sql("""
            SELECT consumption, total_bill
            FROM `tabUtility Consumption`
            WHERE utility_meter = %s
              AND docstatus = 1
              AND name != %s
            ORDER BY period_year DESC, FIELD(period_month,
                'January','February','March','April','May','June',
                'July','August','September','October','November','December') DESC
            LIMIT 1
        """, (self.utility_meter, self.name or ""), as_dict=True)

        if prev:
            self.previous_month_consumption = flt(prev[0].consumption)
            if flt(self.previous_month_consumption) > 0:
                variance = (
                    (flt(self.consumption) - flt(self.previous_month_consumption))
                    / flt(self.previous_month_consumption)
                ) * 100
                self.variance_pct = round(variance, 2)
            else:
                self.variance_pct = 0.0

        # Average daily
        days_in_month = self._days_in_period()
        if days_in_month:
            self.avg_daily_consumption = round(
                flt(self.consumption) / days_in_month, 3
            )

    def _days_in_period(self):
        import calendar
        month_map = {
            "January": 1, "February": 2, "March": 3, "April": 4,
            "May": 5, "June": 6, "July": 7, "August": 8,
            "September": 9, "October": 10, "November": 11, "December": 12,
        }
        m = month_map.get(self.period_month)
        y = self.period_year
        if m and y:
            return calendar.monthrange(y, m)[1]
        return None
