# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/ecclesia/page/secretarial_hub/secretarial_hub.py
# Standard Frappe desk Page — no server-side context needed; all data is
# fetched client-side via ecclesia.api.hub_api through frappe.call.
import frappe


from __future__ import unicode_literals
import frappe

@frappe.whitelist()
def get_context(context):
    """No context needed; data is fetched client-side."""
    context.no_cache = 1
    return context