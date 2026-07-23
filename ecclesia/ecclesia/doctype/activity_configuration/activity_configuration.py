"""
Activity Configuration Controller
Ecclesia Module

Validates scoring rules and exposes a preview_score API
used by the Test Scorer button in the client JS.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class ActivityConfiguration(Document):

    def validate(self):
        self._validate_scoring_rules()
        self._validate_dampening()

    def _validate_scoring_rules(self):
        if flt(self.base_points) < 0:
            frappe.throw(_("Base Points cannot be negative."))

        if self.points_rule != "Fixed":
            if not self.value_field:
                frappe.throw(
                    _("Value Field Name is required when Points Rule is '{0}'.").format(
                        self.points_rule
                    )
                )

        if self.value_multiplier_enabled:
            if not flt(self.value_divisor):
                frappe.throw(_("Value Divisor must be greater than zero."))
            if flt(self.max_value_bonus) <= 0:
                frappe.throw(_("Max Value Bonus must be greater than zero."))

        if flt(self.daily_cap_points) < 0:
            frappe.throw(_("Daily Cap Points cannot be negative."))

    def _validate_dampening(self):
        if self.frequency_dampening_enabled:
            mult = flt(self.dampening_multiplier)
            if not (0 < mult <= 1):
                frappe.throw(
                    _("Dampening Multiplier must be between 0 (exclusive) and 1 (inclusive). "
                      "e.g. 0.5 = half points after repeated actions.")
                )
            if int(self.dampening_window_minutes or 0) <= 0:
                frappe.throw(_("Dampening Window must be at least 1 minute."))


@frappe.whitelist()
def preview_score(config_name, employee, business_value=0):
    """
    Called by the Test Scorer button in Activity Configuration JS.
    Returns a breakdown of how many points would be awarded.
    """
    from ecclesia.api.engine import (
        _get_config, _calculate_raw_score, _apply_dampening, _apply_daily_cap
    )

    config = frappe.get_doc("Activity Configuration", config_name)
    business_value = flt(business_value)

    raw      = _calculate_raw_score(config, business_value)
    dampened, is_dampened = _apply_dampening(config, employee, raw)
    final    = _apply_daily_cap(config, employee, config.doctype_name, dampened)

    return {
        "raw_score":   round(raw, 4),
        "dampened":    round(dampened, 4),
        "final":       round(final, 4),
        "is_dampened": is_dampened,
    }
