# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class WANotificationRule(Document):
    """
    Defines automated WhatsApp notification rules triggered by
    DocType events (e.g., Sales Order submitted → send WA notification).
    """

    def validate(self):
        self.validate_conditions()
        self.validate_recipients()

    def validate_conditions(self):
        if self.condition:
            try:
                compile(self.condition, "<string>", "eval")
            except SyntaxError as e:
                frappe.throw(frappe._("Invalid condition syntax: {0}").format(str(e)))

    def validate_recipients(self):
        if not self.recipients:
            frappe.throw(frappe._("At least one recipient must be defined"))

    def evaluate_condition(self, doc) -> bool:
        """Evaluate the rule condition against a given document."""
        if not self.condition:
            return True
        try:
            return bool(frappe.safe_eval(self.condition, eval_locals={"doc": doc}))
        except Exception as e:
            frappe.log_error(title="WANotificationRule Condition Error", message=str(e))
            return False

    def get_recipients(self, doc) -> list:
        """Resolve recipient phone numbers from the document context."""
        recipients = []
        for row in self.recipients:
            if row.field_name:
                value = doc.get(row.field_name)
                if value:
                    recipients.append(value)
            elif row.static_number:
                recipients.append(row.static_number)
        return recipients

