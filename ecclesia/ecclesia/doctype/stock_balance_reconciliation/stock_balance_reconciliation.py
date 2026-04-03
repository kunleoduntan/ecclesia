# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt



# Copyright (c) 2026

import frappe
from frappe.model.document import Document
from frappe.utils import flt, nowdate
from frappe import _


class StockBalanceReconciliation(Document):

    # ─────────────────────────────────────────────
    # VALIDATION
    # ─────────────────────────────────────────────
    def validate(self):
        self.validate_duplicate()
        self.validate_posting_time()
        self.calculate_item_values()
        self.calculate_summary()
        self.validate_fifo_impact()

    def validate_duplicate(self):
        if self.is_new():
            existing = frappe.db.exists("Stock Balance Reconciliation", {
                "warehouse": self.warehouse,
                "reconciliation_date": self.reconciliation_date,
                "docstatus": ["in", [0, 1]],
                "name": ["!=", self.name]
            })
            if existing:
                frappe.throw(_("Duplicate reconciliation exists: {0}").format(existing))

    def validate_posting_time(self):
        if self.reconciliation_date < frappe.utils.add_days(nowdate(), -30):
            frappe.throw(_("Backdated reconciliation beyond 30 days not allowed"))

    def validate_fifo_impact(self):
        if not self.freeze_rate:
            return

        for item in self.items:
            if abs(flt(item.valuation_price) - flt(item.current_price)) > 0.01:
                frappe.throw(
                    _("Rate change not allowed for item {0} when Freeze Rate is enabled")
                    .format(item.item_code)
                )

    # ─────────────────────────────────────────────
    # CALCULATIONS
    # ─────────────────────────────────────────────
    def calculate_item_values(self):
        for item in self.items:
            item.system_valuation = flt(item.current_qty) * flt(item.current_price)
            item.valuation_now = flt(item.physical_count_qty) * flt(item.valuation_price)
            item.difference_qty = flt(item.physical_count_qty) - flt(item.current_qty)
            item.net_adjusted_qty = item.difference_qty
            item.net_adjusted_amount = flt(item.net_adjusted_qty) * flt(item.valuation_price)

            if abs(item.difference_qty) < 0.001:
                item.status = "OK"
            elif item.difference_qty > 0:
                item.status = "Surplus"
            else:
                item.status = "Deficit"

    def calculate_summary(self):
        total_sys_val = sum(flt(i.system_valuation) for i in self.items)
        net_amt = sum(flt(i.net_adjusted_amount) for i in self.items)

        self.total_items = len(self.items)
        self.total_adjusted_items = sum(1 for i in self.items if i.status != "OK")
        self.net_adjustment_amount = net_amt
        self.variance_percent = (
            flt((net_amt / total_sys_val) * 100, 2) if total_sys_val else 0
        )

    # ─────────────────────────────────────────────
    # SUBMIT
    # ─────────────────────────────────────────────
    def on_submit(self):
        if not self.items:
            frappe.throw(_("No items to reconcile"))

        if self.create_stock_entry:
            self._create_draft_stock_entry()
        else:
            self._post_stock_reconciliation()

    # ─────────────────────────────────────────────
    # TRUE STOCK RECONCILIATION (SLE)
    # ─────────────────────────────────────────────
    def _post_stock_reconciliation(self):

        adjusted_items = [i for i in self.items if i.status != "OK"]
        if not adjusted_items:
            return

        company = self._get_company()

        sr = frappe.new_doc("Stock Reconciliation")
        sr.company = company
        sr.posting_date = self.reconciliation_date
        sr.posting_time = "00:00:00"
        sr.set_posting_time = 1
        sr.purpose = "Stock Reconciliation"
        sr.remarks = "Auto from {0}".format(self.name)

        for item in adjusted_items:

            item_doc = frappe.get_cached_doc("Item", item.item_code)

            row = {
                "item_code": item.item_code,
                "warehouse": self.warehouse,
                "qty": flt(item.physical_count_qty),
                "valuation_rate": flt(item.valuation_price),
                "current_qty": flt(item.current_qty),
                "current_valuation_rate": flt(item.current_price),
                "uom": item_doc.stock_uom,
            }

            # ─── OPTIONAL BATCH ───
            if item_doc.has_batch_no:
                if item.batch_no:
                    row["batch_no"] = item.batch_no
                else:
                    frappe.throw(_("Batch required for item {0}").format(item.item_code))

            # ─── OPTIONAL SERIAL ───
            if item_doc.has_serial_no:
                if not item.serial_no:
                    frappe.throw(_("Serial numbers required for item {0}").format(item.item_code))

                serial_list = [s.strip() for s in item.serial_no.split("\n") if s.strip()]

                if len(serial_list) != int(item.physical_count_qty):
                    frappe.throw(_("Serial count mismatch for item {0}").format(item.item_code))

                row["serial_no"] = "\n".join(serial_list)

            sr.append("items", row)

        sr.insert(ignore_permissions=True)
        sr.submit()

        self.db_set("stock_entry_reference", sr.name)
        self.db_set("stock_entry_status", "Submitted")

    # ─────────────────────────────────────────────
    # DRAFT STOCK ENTRY (REVIEW MODE)
    # ─────────────────────────────────────────────
    def _create_draft_stock_entry(self):

        if self.stock_entry_reference:
            frappe.throw(_("Stock Entry already exists"))

        company = self._get_company()

        surplus_items = [i for i in self.items if i.status == "Surplus"]
        deficit_items = [i for i in self.items if i.status == "Deficit"]

        created = []

        # ─── RECEIPT ───
        if surplus_items:
            se = frappe.new_doc("Stock Entry")
            se.stock_entry_type = "Material Receipt"
            se.purpose = "Material Receipt"
            se.company = company
            se.posting_date = self.reconciliation_date

            for item in surplus_items:
                item_doc = frappe.get_cached_doc("Item", item.item_code)

                row = {
                    "item_code": item.item_code,
                    "t_warehouse": self.warehouse,
                    "qty": flt(item.net_adjusted_qty),
                    "basic_rate": flt(item.valuation_price),
                    "uom": item_doc.stock_uom,
                    "stock_uom": item_doc.stock_uom,
                    "conversion_factor": 1,
                    "expense_account": self._get_expense_account(item.item_code, company),
                }

                if item_doc.has_batch_no and item.batch_no:
                    row["batch_no"] = item.batch_no

                if item_doc.has_serial_no and item.serial_no:
                    row["serial_no"] = item.serial_no

                se.append("items", row)

            se.insert(ignore_permissions=True)
            created.append(se.name)

        # ─── ISSUE ───
        if deficit_items:
            se = frappe.new_doc("Stock Entry")
            se.stock_entry_type = "Material Issue"
            se.purpose = "Material Issue"
            se.company = company
            se.posting_date = self.reconciliation_date

            for item in deficit_items:
                item_doc = frappe.get_cached_doc("Item", item.item_code)

                row = {
                    "item_code": item.item_code,
                    "s_warehouse": self.warehouse,
                    "qty": abs(flt(item.net_adjusted_qty)),
                    "basic_rate": flt(item.valuation_price),
                    "uom": item_doc.stock_uom,
                    "stock_uom": item_doc.stock_uom,
                    "conversion_factor": 1,
                    "expense_account": self._get_expense_account(item.item_code, company),
                }

                if item_doc.has_batch_no and item.batch_no:
                    row["batch_no"] = item.batch_no

                if item_doc.has_serial_no and item.serial_no:
                    row["serial_no"] = item.serial_no

                se.append("items", row)

            se.insert(ignore_permissions=True)
            created.append(se.name)

        if created:
            self.db_set("stock_entry_reference", ", ".join(created))
            self.db_set("stock_entry_status", "Draft")

    # ─────────────────────────────────────────────
    # CANCEL CONTROL
    # ─────────────────────────────────────────────
    def before_cancel(self):
        frappe.throw(_("Cancellation not allowed. Use reversal entry."))

    # ─────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────
    def _get_company(self):
        company = frappe.defaults.get_defaults().get("company")
        if not company:
            frappe.throw(_("Set default company"))
        return company

    def _get_expense_account(self, item_code, company):
        item = frappe.get_cached_doc("Item", item_code)
        for d in item.item_defaults:
            if d.company == company and d.expense_account:
                return d.expense_account
        return frappe.db.get_value("Company", company, "default_expense_account")