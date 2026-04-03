# Copyright (c) 2026, kunle Oduntan and contributors
# For license information, please see license.txt

"""
Annual Plan Engagement Row — child table controller.
Auto-updates status to In Progress when a linked engagement is submitted,
and to Completed when the linked engagement is closed.
"""

import frappe
from frappe.model.document import Document


class AnnualPlanEngagementRow(Document):

    def validate(self):
        """Sync status from linked engagement if one exists."""
        if not self.linked_engagement:
            return

        eng_status = frappe.db.get_value(
            "Audit Engagement", self.linked_engagement, "status"
        )
        if not eng_status:
            return

        status_map = {
            "Planning":  "In Progress",
            "Fieldwork": "In Progress",
            "Review":    "In Progress",
            "Reporting": "In Progress",
            "Closed":    "Completed",
            "Cancelled": "Cancelled",
        }
        mapped = status_map.get(eng_status)
        if mapped and self.status not in ("Completed", "Cancelled", "Deferred"):
            self.status = mapped