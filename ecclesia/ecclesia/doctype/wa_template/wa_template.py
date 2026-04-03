# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document

class WATemplate(Document):
    """
    Stores WhatsApp Message Templates approved by Meta/WhatsApp Business API.
    Used for sending structured, pre-approved messages to customers.
    """

    def validate(self):
        self.validate_template_name()
        self.validate_language_code()

    def validate_template_name(self):
        if not self.template_name:
            frappe.throw(frappe._("Template Name is required"))
        # WhatsApp template names must be lowercase with underscores
        if not self.template_name.replace("_", "").isalnum():
            frappe.throw(
                frappe._("Template Name must contain only lowercase letters, numbers, and underscores")
            )

    def validate_language_code(self):
        valid_codes = ["en", "en_US", "en_GB", "ar", "fr", "de", "es", "pt_BR", "it", "ja", "ko", "zh_CN"]
        if self.language_code and self.language_code not in valid_codes:
            frappe.msgprint(
                frappe._("Language code '{0}' may not be supported by WhatsApp").format(self.language_code),
                indicator="orange",
            )

    def before_submit(self):
        if self.status != "Approved":
            frappe.throw(frappe._("Only Approved templates can be submitted"))