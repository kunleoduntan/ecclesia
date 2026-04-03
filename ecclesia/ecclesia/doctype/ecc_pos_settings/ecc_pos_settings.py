# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document


class ECCPOSSettings(Document):

    def validate(self):
        self._validate_vat()
        self._validate_users()
        self._ensure_default_customer()

    def _validate_vat(self):
        if self.enable_vat:
            if not self.vat_rate or self.vat_rate <= 0:
                frappe.throw(_("VAT Rate must be greater than 0 when VAT is enabled."))
            if self.vat_rate > 100:
                frappe.throw(_("VAT Rate cannot exceed 100%."))

    def _validate_users(self):
        seen = []
        for row in self.user_permissions:
            if row.user in seen:
                frappe.throw(_(f"User {row.user} appears more than once in the User Permissions table."))
            seen.append(row.user)
            if row.max_discount_pct and row.max_discount_pct > 100:
                frappe.throw(_(f"Max Discount for {row.user} cannot exceed 100%."))

    def _ensure_default_customer(self):
        if not self.default_customer:
            name = _get_or_create_walkin_customer(self.company)
            self.default_customer = name


def _get_or_create_walkin_customer(company):
    customer_name = "Walk-In Customer"
    if not frappe.db.exists("Customer", customer_name):
        frappe.get_doc({
            "doctype": "Customer",
            "customer_name": customer_name,
            "customer_type": "Individual",
            "customer_group": frappe.db.get_value(
                "Customer Group", {"is_group": 0}, "name"
            ) or "Individual",
            "territory": frappe.db.get_value(
                "Territory", {"is_group": 0}, "name"
            ) or "All Territories",
        }).insert(ignore_permissions=True)
        frappe.db.commit()
    return customer_name
