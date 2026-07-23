# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/ecclesia/page/admin_dashboard/admin_dashboard.py
# Page controller for Admin 360° Power Dashboard — no logic needed here,
# all data is fetched client-side via frappe.client.get_list in the JS.

import frappe


def get_context(context):
    context.no_cache = 1
