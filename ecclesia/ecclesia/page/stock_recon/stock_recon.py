# Copyright (c) 2026

import frappe
import json
from frappe import _
from frappe.utils import flt, nowtime


@frappe.whitelist()
def create_stock_reconciliation(data=None, stock_entry_data=None, reconciliation_ref=None):
    """
    Create Stock Reconciliation (ERPNext standard compliant)

    Expected payload:
    {
        "company": "...",
        "posting_date": "YYYY-MM-DD",
        "posting_time": "HH:MM:SS",   # optional
        "warehouse": "...",
        "remarks": "...",
        "submit": 1,
        "items": [
            {
                "item_code": "...",
                "item_name": "...",
                "warehouse": "...",   # optional
                "qty": 10,
                "valuation_rate": 100,
                "current_qty": 8,     # optional
                "current_valuation_rate": 95,  # optional
                "batch_no": "...",    # optional (required if item has batch)
                "serial_no": "SN1\nSN2"  # optional (required if serialized)
            }
        ]
    }
    """

    try:
        # ─────────────────────────────
        # INPUT NORMALIZATION
        # ─────────────────────────────
        if not data and stock_entry_data:
            data = stock_entry_data

        if isinstance(data, str):
            data = json.loads(data)

        if not data:
            frappe.throw(_("Data is required"))

        items = data.get("items") or []
        if not items:
            frappe.throw(_("Items are required"))

        company = data.get("company")
        posting_date = data.get("posting_date")
        warehouse = data.get("warehouse")

        if not company:
            frappe.throw(_("Company is required"))
        if not posting_date:
            frappe.throw(_("Posting date is required"))
        if not warehouse:
            frappe.throw(_("Warehouse is required"))

        # ─────────────────────────────
        # CREATE DOCUMENT
        # ─────────────────────────────
        doc = frappe.new_doc("Stock Reconciliation")
        doc.company = company
        doc.purpose = "Stock Reconciliation"
        doc.posting_date = posting_date
        doc.posting_time = data.get("posting_time") or nowtime()
        doc.set_posting_time = 1
        doc.set_warehouse = warehouse
        doc.remarks = data.get("remarks") or ""

        # ─────────────────────────────
        # PROCESS ITEMS
        # ─────────────────────────────
        has_difference = False

        for src in items:

            item_code = src.get("item_code")
            if not item_code:
                continue

            warehouse_ = src.get("warehouse") or warehouse

            qty = flt(src.get("qty"))
            valuation_rate = flt(src.get("valuation_rate"))

            current_qty = flt(src.get("current_qty"))
            current_rate = flt(src.get("current_valuation_rate"))

            # ─────────────────────────────
            # FETCH SYSTEM VALUES
            # ─────────────────────────────
            bin_data = frappe.db.get_value(
                "Bin",
                {"item_code": item_code, "warehouse": warehouse_},
                ["actual_qty", "valuation_rate"],
                as_dict=1
            ) or {}

            system_qty = flt(bin_data.get("actual_qty"))
            system_rate = flt(bin_data.get("valuation_rate"))

            if not current_qty:
                current_qty = system_qty
            if not current_rate:
                current_rate = system_rate

            # ─────────────────────────────
            # DIFFERENCE CHECK
            # ─────────────────────────────
            qty_diff = qty - current_qty
            rate_diff = valuation_rate - current_rate

            if abs(qty_diff) > 0.0001 or abs(rate_diff) > 0.0001:
                has_difference = True

            # ─────────────────────────────
            # ITEM META VALIDATION
            # ─────────────────────────────
            item_doc = frappe.get_cached_doc("Item", item_code)

            batch_no = src.get("batch_no")
            serial_no = src.get("serial_no")

            if item_doc.has_batch_no and not batch_no:
                frappe.throw(_("Batch is required for item {0}").format(item_code))

            if item_doc.has_serial_no:
                if not serial_no:
                    frappe.throw(_("Serial numbers required for item {0}").format(item_code))

                serial_list = [s.strip() for s in serial_no.split("\n") if s.strip()]

                if len(serial_list) != int(qty):
                    frappe.throw(_("Serial count must match qty for item {0}").format(item_code))

            # ─────────────────────────────
            # APPEND ROW
            # ─────────────────────────────
            row = doc.append("items", {})

            row.item_code = item_code
            row.item_name = src.get("item_name")
            row.warehouse = warehouse_

            # CRITICAL STANDARD FIELDS
            row.qty = qty
            row.valuation_rate = valuation_rate

            # optional system snapshot
            row.current_qty = current_qty
            row.current_valuation_rate = current_rate

            # optional fields
            if src.get("amount") is not None:
                row.amount = flt(src.get("amount"))

            row.allow_zero_valuation_rate = src.get("allow_zero_valuation_rate") or 0

            if batch_no:
                row.batch_no = batch_no

            if serial_no:
                row.serial_no = serial_no

        # ─────────────────────────────
        # FINAL VALIDATION
        # ─────────────────────────────
        if not has_difference:
            frappe.throw(_("No difference found. Nothing to reconcile."))

        # ─────────────────────────────
        # INSERT & SUBMIT
        # ─────────────────────────────
        doc.insert(ignore_permissions=True)

        if data.get("submit"):
            doc.submit()

        frappe.db.commit()

        return {
            "success": True,
            "name": doc.name,
            "message": _("Stock Reconciliation created successfully")
        }

    except Exception:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Stock Reconciliation API Error")

        return {
            "success": False,
            "error": frappe.get_traceback()
        }