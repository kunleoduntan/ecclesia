# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

"""
Generator Log DocType Controller
Nigerian-specific: tracks diesel generator runtime, consumption, cost per session.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, time_diff_in_hours


class GeneratorLog(Document):

    def validate(self):
        self._compute_run_hours()
        self._compute_fuel_consumed()
        self._compute_fuel_cost()

    def _compute_run_hours(self):
        if self.start_time and self.stop_time:
            start = frappe.utils.get_datetime(
                "{} {}".format(self.log_date or frappe.utils.nowdate(), self.start_time)
            )
            stop = frappe.utils.get_datetime(
                "{} {}".format(self.log_date or frappe.utils.nowdate(), self.stop_time)
            )
            if stop > start:
                self.run_hours = round(
                    (stop - start).total_seconds() / 3600, 2
                )
            else:
                frappe.throw(_("Stop Time must be after Start Time."))

    def _compute_fuel_consumed(self):
        opening = flt(self.opening_fuel_litres)
        added   = flt(self.fuel_added_litres)
        closing = flt(self.closing_fuel_litres)
        if opening or closing:
            consumed = (opening + added) - closing
            self.fuel_consumed_litres = max(round(consumed, 2), 0)

    def _compute_fuel_cost(self):
        if self.fuel_consumed_litres and self.diesel_rate_per_litre:
            self.fuel_cost = flt(self.fuel_consumed_litres) * flt(self.diesel_rate_per_litre)
