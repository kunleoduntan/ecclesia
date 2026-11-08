# Copyright (c) 2024, Ecclesia and contributors
# For license information, please see license.txt

import json
import re
import io
from datetime import datetime

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    summary = get_summary(data)
    return columns, data, None, None, summary


def get_columns():
    return [
        {"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
        {"label": _("Customer ID"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 120},
        {"label": _("Customer Name"), "fieldname": "customer_name", "fieldtype": "Data", "width": 220},
        {"label": _("Voucher Type"), "fieldname": "voucher_type", "fieldtype": "Data", "width": 120},
        {"label": _("Voucher No"), "fieldname": "voucher_no", "fieldtype": "Dynamic Link", "options": "voucher_type", "width": 150},
        {"label": _("Reference"), "fieldname": "against_voucher", "fieldtype": "Data", "width": 150},
        {"label": _("Description"), "fieldname": "description", "fieldtype": "Data", "width": 250},
        {"label": _("Debit"), "fieldname": "debit", "fieldtype": "Currency", "options": "currency", "width": 130},
        {"label": _("Credit"), "fieldname": "credit", "fieldtype": "Currency", "options": "currency", "width": 130},
        {"label": _("Balance"), "fieldname": "balance", "fieldtype": "Currency", "options": "currency", "width": 130},
        {"label": _("Currency"), "fieldname": "currency", "fieldtype": "Link", "options": "Currency", "width": 80, "hidden": 1},
    ]


def get_data(filters):
    conditions = get_conditions(filters)

    gl_entries = frappe.db.sql("""
        SELECT
            gle.posting_date,
            gle.party as customer,
            cust.customer_name,
            gle.voucher_type,
            gle.voucher_no,
            gle.against_voucher,
            gle.remarks as description,
            gle.debit,
            gle.credit,
            gle.debit_in_account_currency as debit_in_currency,
            gle.credit_in_account_currency as credit_in_currency,
            gle.account_currency as currency,
            gle.against
        FROM `tabGL Entry` gle
        LEFT JOIN `tabCustomer` cust ON cust.name = gle.party
        WHERE gle.party_type = 'Customer'
            AND gle.is_cancelled = 0
            {conditions}
        ORDER BY gle.party, gle.posting_date, gle.creation
    """.format(conditions=conditions), filters, as_dict=1)

    customer_entries = {}
    customer_meta = {}

    for entry in gl_entries:
        customer = entry.get("customer")
        if customer not in customer_entries:
            customer_entries[customer] = []
            customer_meta[customer] = {
                "customer_name": entry.get("customer_name"),
                "currency": entry.get("currency") or "NGN",
            }
        customer_entries[customer].append(entry)

    final_data = []
    grand_total_debit = 0
    grand_total_credit = 0
    grand_total_balance = 0

    for customer, entries in customer_entries.items():
        meta = customer_meta[customer]
        currency = meta.get("currency", "NGN")
        customer_name = meta.get("customer_name") or customer

        # ── Header row ──
        opening_balance = get_opening_balance(customer, filters)

        final_data.append({
            "posting_date": "",
            "customer": customer,
            "customer_name": customer_name,
            "voucher_type": "",
            "voucher_no": "",
            "against_voucher": "",
            "description": "",
            "debit": None,
            "credit": None,
            "balance": opening_balance if opening_balance else None,
            "currency": currency,
            "is_header_row": True,
            "bold": 1,
        })

        # ── Transaction rows ──
        running_balance = opening_balance
        customer_total_debit = 0
        customer_total_credit = 0

        for entry in entries:
            running_balance += flt(entry.get("debit")) - flt(entry.get("credit"))
            customer_total_debit += flt(entry.get("debit"))
            customer_total_credit += flt(entry.get("credit"))

            final_data.append({
                "posting_date": entry.get("posting_date"),
                "customer": entry.get("customer"),
                "customer_name": entry.get("customer_name"),
                "voucher_type": entry.get("voucher_type"),
                "voucher_no": entry.get("voucher_no"),
                "against_voucher": entry.get("against_voucher"),
                "description": entry.get("description") or entry.get("against"),
                "debit": flt(entry.get("debit")),
                "credit": flt(entry.get("credit")),
                "balance": running_balance,
                "currency": currency,
                "indent": 1,
            })

        grand_total_debit += customer_total_debit
        grand_total_credit += customer_total_credit
        grand_total_balance += running_balance

        # ── Subtotal row ──
        final_data.append({
            "posting_date": "",
            "customer": customer,
            "customer_name": f"Subtotal – {customer_name}",
            "voucher_type": "",
            "voucher_no": "",
            "against_voucher": "",
            "description": "Closing Balance",
            "debit": customer_total_debit,
            "credit": customer_total_credit,
            "balance": running_balance,
            "currency": currency,
            "is_total_row": True,
            "bold": 1,
        })

        # ── Spacer ──
        final_data.append({})

    # ── Grand total row ──
    final_data.append({
        "posting_date": "",
        "customer": "",
        "customer_name": "",
        "voucher_type": "",
        "voucher_no": "",
        "against_voucher": "",
        "description": "GRAND TOTAL (All Customers)",
        "debit": grand_total_debit,
        "credit": grand_total_credit,
        "balance": grand_total_balance,
        "currency": "NGN",
        "is_grand_total": True,
        "bold": 1,
    })

    return final_data


def get_conditions(filters):
    conditions = []

    if filters.get("company"):
        conditions.append("gle.company = %(company)s")
    if filters.get("from_date"):
        conditions.append("gle.posting_date >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append("gle.posting_date <= %(to_date)s")
    if filters.get("customer"):
        conditions.append("gle.party = %(customer)s")

    return "AND " + " AND ".join(conditions) if conditions else ""


def get_opening_balance(customer, filters):
    if not filters.get("from_date"):
        return 0

    opening = frappe.db.sql("""
        SELECT SUM(debit - credit) as balance
        FROM `tabGL Entry`
        WHERE party_type = 'Customer'
            AND party = %s
            AND posting_date < %s
            AND is_cancelled = 0
    """, (customer, filters.get("from_date")), as_dict=1)

    return flt(opening[0].get("balance")) if opening else 0


def get_summary(data):
    if not data:
        return None

    total_debit = total_credit = final_balance = 0

    for row in data:
        if row and row.get("is_grand_total"):
            final_balance = flt(row.get("balance"))
            total_debit = flt(row.get("debit"))
            total_credit = flt(row.get("credit"))
            break

    return [
        {"value": total_debit, "label": _("Total Debit"), "datatype": "Currency", "currency": "NGN", "indicator": "Blue"},
        {"value": total_credit, "label": _("Total Credit"), "datatype": "Currency", "currency": "NGN", "indicator": "Green"},
        {"value": final_balance, "label": _("Outstanding Balance"), "datatype": "Currency", "currency": "NGN",
         "indicator": "Orange" if final_balance > 0 else "Red" if final_balance < 0 else "Green"},
    ]


@frappe.whitelist()
def download_excel(filters=None):
    """Clean, professionally styled Excel export of the Customer Ledger."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    if filters is None:
        filters = {}
    if isinstance(filters, str):
        filters = json.loads(filters)

    data = get_data(filters)
    columns = get_columns()

    vis_cols = [c for c in columns if not c.get("hidden")]
    col_labels = [c.get("label") for c in vis_cols]
    col_fields = [c.get("fieldname") for c in vis_cols]
    col_types = [c.get("fieldtype") for c in vis_cols]
    num_cols = len(vis_cols)
    currency_idx = {i for i, ft in enumerate(col_types) if ft == "Currency"}
    date_idx = {i for i, ft in enumerate(col_types) if ft == "Date"}

    wb = Workbook()
    ws = wb.active
    ws.title = "Customer Ledger"
    ws.sheet_view.showGridLines = False

    # ── Palette ──
    C = {
        "navy": "1F3A5F",
        "band": "E8EEF5",
        "subtle": "F4F7FA",
        "title_bg": "F8FAFC",
        "white": "FFFFFF",
        "debit": "1D4ED8",
        "credit": "0F766E",
        "owing": "B45309",
        "negative": "B91C1C",
        "muted": "6B7280",
        "hairline": "E5E7EB",
    }
    FONT = "Calibri"
    NUM_FMT = '#,##0.00;[Red]-#,##0.00'
    DATE_FMT = "DD-MMM-YYYY"

    def fill(hex_color):
        return PatternFill("solid", fgColor=hex_color)

    def font(**kw):
        kw.setdefault("name", FONT)
        kw.setdefault("size", 10)
        return Font(**kw)

    def bal_color(b):
        return C["owing"] if b > 0 else C["negative"] if b < 0 else C["muted"]

    hairline = Border(bottom=Side(style="hair", color=C["hairline"]))

    # ── Column widths ──
    widths = [13, 14, 30, 16, 22, 22, 38, 16, 16, 16]
    for i, w in enumerate(widths[:num_cols], start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    def clean_html(value):
        if isinstance(value, str):
            value = re.sub(r"<[^>]+>", "", value).replace("&nbsp;", " ").strip()
        return value if value is not None else ""

    # ── Title block ──
    company = filters.get("company", "")
    from_date = filters.get("from_date", "")
    to_date = filters.get("to_date", "")
    generated_on = datetime.now().strftime("%d %B %Y at %I:%M %p")

    title_rows = [
        ("CUSTOMER LEDGER", font(bold=True, size=16, color=C["navy"]), 30),
        (f"{company}", font(size=11, bold=True, color="374151"), 20),
        (f"Period: {from_date}  to  {to_date}", font(size=10, color=C["muted"]), 18),
        (f"Generated: {generated_on}", font(italic=True, size=9, color=C["muted"]), 16),
        ("", None, 8),
    ]
    for text, f, height in title_rows:
        ws.append([text] + [""] * (num_cols - 1))
        r = ws.max_row
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=num_cols)
        c = ws.cell(row=r, column=1)
        c.value = text
        if f:
            c.font = f
        c.fill = fill(C["title_bg"])
        c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        ws.row_dimensions[r].height = height

    # ── Column headers ──
    ws.append(col_labels)
    header_row = ws.max_row
    for idx, c in enumerate(ws[header_row]):
        c.font = font(bold=True, color=C["white"], size=10)
        c.fill = fill(C["navy"])
        c.alignment = Alignment(horizontal="right" if idx in currency_idx else "left",
                                vertical="center", indent=0 if idx in currency_idx else 1)
    ws.row_dimensions[header_row].height = 26
    ws.freeze_panes = f"A{header_row + 1}"

    # ── Data rows ──
    for row_data in data:
        if not row_data:  # spacer
            ws.append([""] * num_cols)
            ws.row_dimensions[ws.max_row].height = 8
            continue

        is_header = row_data.get("is_header_row")
        is_total = row_data.get("is_total_row")
        is_grand = row_data.get("is_grand_total")

        excel_row = []
        for idx, field in enumerate(col_fields):
            val = row_data.get(field)
            if idx in currency_idx:
                excel_row.append(flt(val) if val is not None else 0)
            elif idx in date_idx:
                excel_row.append(val if val else "")
            else:
                excel_row.append(clean_html(val) if val is not None else "")

        ws.append(excel_row)
        r = ws.max_row

        # ── Customer header band ──
        if is_header:
            opening = flt(row_data.get("balance"))
            for ci in range(1, num_cols + 1):
                ws.cell(row=r, column=ci).fill = fill(C["band"])
            last = num_cols - 1 if opening else num_cols
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=last)
            c = ws.cell(row=r, column=1)
            c.value = f"{row_data.get('customer_name', '')}   [{row_data.get('customer', '')}]"
            c.font = font(bold=True, size=11, color=C["navy"])
            c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
            c.border = Border(left=Side(style="thick", color=C["navy"]))
            if opening:
                b = ws.cell(row=r, column=num_cols)
                b.value = opening
                b.number_format = '"Opening  "#,##0.00;"Opening  "-#,##0.00'
                b.font = font(bold=True, color=bal_color(opening))
                b.alignment = Alignment(horizontal="right", vertical="center")
            ws.row_dimensions[r].height = 24

        # ── Subtotal row ──
        elif is_total:
            ws.row_dimensions[r].height = 22
            top = Border(top=Side(style="thin", color=C["navy"]))
            for ci in range(1, num_cols + 1):
                c = ws.cell(row=r, column=ci)
                c.fill = fill(C["subtle"])
                c.border = top
                field = col_fields[ci - 1]
                if field == "customer_name":
                    c.font = font(bold=True, color=C["navy"], size=10)
                    c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
                elif field == "description":
                    c.font = font(color=C["muted"], italic=True)
                    c.alignment = Alignment(horizontal="left", vertical="center")
                elif field == "debit":
                    c.number_format = NUM_FMT
                    c.font = font(bold=True, color=C["debit"])
                    c.alignment = Alignment(horizontal="right", vertical="center")
                elif field == "credit":
                    c.number_format = NUM_FMT
                    c.font = font(bold=True, color=C["credit"])
                    c.alignment = Alignment(horizontal="right", vertical="center")
                elif field == "balance":
                    c.number_format = NUM_FMT
                    c.font = font(bold=True, color=bal_color(flt(row_data.get("balance"))))
                    c.alignment = Alignment(horizontal="right", vertical="center")

        # ── Grand total row ──
        elif is_grand:
            ws.row_dimensions[r].height = 28
            for ci in range(1, num_cols + 1):
                c = ws.cell(row=r, column=ci)
                c.fill = fill(C["navy"])
                c.font = font(bold=True, color=C["white"], size=11)
                if (ci - 1) in currency_idx:
                    c.number_format = '#,##0.00'
                    c.alignment = Alignment(horizontal="right", vertical="center")
            # label spans everything left of Debit
            label_end = col_fields.index("debit")  # 0-based -> columns 1..label_end
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=label_end)
            lc = ws.cell(row=r, column=1)
            lc.value = row_data.get("description", "GRAND TOTAL")
            lc.alignment = Alignment(horizontal="left", vertical="center", indent=1)

        # ── Transaction row ──
        else:
            for ci in range(1, num_cols + 1):
                c = ws.cell(row=r, column=ci)
                c.border = hairline
                field = col_fields[ci - 1]

                if (ci - 1) in currency_idx:
                    c.number_format = NUM_FMT
                    c.alignment = Alignment(horizontal="right", vertical="center")
                    if field == "debit" and flt(row_data.get("debit")) > 0:
                        c.font = font(color=C["debit"])
                    elif field == "credit" and flt(row_data.get("credit")) > 0:
                        c.font = font(color=C["credit"])
                    elif field == "balance":
                        c.font = font(bold=True, color=bal_color(flt(row_data.get("balance"))))
                    else:
                        c.font = font(color=C["muted"])
                else:
                    if (ci - 1) in date_idx:
                        c.number_format = DATE_FMT
                    c.font = font(color=C["muted"] if field in ("voucher_type", "against_voucher") else "111827")
                    c.alignment = Alignment(horizontal="left", vertical="center",
                                            indent=1 if ci == 1 else 0,
                                            wrap_text=(field == "description"))

    # ── Page setup ──
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_title_rows = f"{header_row}:{header_row}"

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    frappe.response["filename"] = f'Customer_Ledger_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    frappe.response["filecontent"] = output.getvalue()
    frappe.response["type"] = "binary"