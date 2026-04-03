# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt



import frappe
from frappe import _
from frappe.utils import flt, getdate, today
import json
from datetime import datetime


def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)
    summary = get_summary(data)

    return columns, data, None, None, summary


def get_columns():
    return [
        {
            "label": _("Posting Date"),
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 100
        },
        {
            "label": _("Account"),
            "fieldname": "account",
            "fieldtype": "Link",
            "options": "Account",
            "width": 200
        },
        {
            "label": _("Account Name"),
            "fieldname": "account_name",
            "fieldtype": "Data",
            "width": 200
        },
        {
            "label": _("Voucher Type"),
            "fieldname": "voucher_type",
            "fieldtype": "Data",
            "width": 130
        },
        {
            "label": _("Voucher No"),
            "fieldname": "voucher_no",
            "fieldtype": "Dynamic Link",
            "options": "voucher_type",
            "width": 160
        },
        {
            "label": _("Party"),
            "fieldname": "party",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": _("Description"),
            "fieldname": "description",
            "fieldtype": "Data",
            "width": 250
        },
        {
            "label": _("Debit"),
            "fieldname": "debit",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 130
        },
        {
            "label": _("Credit"),
            "fieldname": "credit",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 130
        },
        {
            "label": _("Balance"),
            "fieldname": "balance",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 130
        },
        {
            "label": _("Cost Center"),
            "fieldname": "cost_center",
            "fieldtype": "Link",
            "options": "Cost Center",
            "width": 140
        },
        {
            "label": _("Currency"),
            "fieldname": "currency",
            "fieldtype": "Link",
            "options": "Currency",
            "width": 80,
            "hidden": 1
        }
    ]


def get_data(filters):
    conditions = get_conditions(filters)

    gl_entries = frappe.db.sql("""
        SELECT
            gle.posting_date,
            gle.account,
            acc.account_name,
            acc.account_currency as currency,
            gle.voucher_type,
            gle.voucher_no,
            gle.party_type,
            gle.party,
            gle.against,
            gle.remarks as description,
            gle.debit,
            gle.credit,
            gle.cost_center
        FROM
            `tabGL Entry` gle
        LEFT JOIN
            `tabAccount` acc ON acc.name = gle.account
        WHERE
            gle.is_cancelled = 0
            {conditions}
        ORDER BY
            gle.account, gle.posting_date, gle.creation
    """.format(conditions=conditions), filters, as_dict=1)

    # Group by account
    account_entries = {}
    account_meta = {}

    for entry in gl_entries:
        account = entry.get("account")
        if account not in account_entries:
            account_entries[account] = []
            account_meta[account] = {
                "account_name": entry.get("account_name") or account,
                "currency": entry.get("currency") or "NGN"
            }
        account_entries[account].append(entry)

    final_data = []

    for account, entries in account_entries.items():
        meta = account_meta[account]
        currency = meta.get("currency", "NGN")
        account_name = meta.get("account_name", account)

        # ── HEADER ROW ────────────────────────────────────────────
        opening_balance = get_opening_balance(account, filters)

        final_data.append({
            "posting_date": "",
            "account": account,
            "account_name": account_name,
            "voucher_type": "",
            "voucher_no": "",
            "party": "",
            "description": "",
            "debit": None,
            "credit": None,
            "balance": opening_balance if opening_balance else None,
            "cost_center": "",
            "currency": currency,
            "is_header_row": True,
            "bold": 1,
        })

        # ── TRANSACTION ROWS ──────────────────────────────────────
        running_balance = opening_balance
        total_debit = 0
        total_credit = 0

        for entry in entries:
            running_balance += flt(entry.get("debit")) - flt(entry.get("credit"))
            total_debit += flt(entry.get("debit"))
            total_credit += flt(entry.get("credit"))

            # Build party display: "Type: Name"
            party_display = ""
            if entry.get("party"):
                party_display = (
                    f"{entry.get('party_type')}: {entry.get('party')}"
                    if entry.get("party_type")
                    else entry.get("party")
                )

            final_data.append({
                "posting_date": entry.get("posting_date"),
                "account": entry.get("account"),
                "account_name": entry.get("account_name"),
                "voucher_type": entry.get("voucher_type"),
                "voucher_no": entry.get("voucher_no"),
                "party": party_display,
                "description": entry.get("description") or entry.get("against"),
                "debit": flt(entry.get("debit")),
                "credit": flt(entry.get("credit")),
                "balance": running_balance,
                "cost_center": entry.get("cost_center"),
                "currency": currency,
                "indent": 1,
            })

        # ── SUBTOTAL ROW ──────────────────────────────────────────
        final_data.append({
            "posting_date": "",
            "account": account,
            "account_name": f"Subtotal — {account_name}",
            "voucher_type": "",
            "voucher_no": "",
            "party": "",
            "description": "Closing Balance",
            "debit": total_debit,
            "credit": total_credit,
            "balance": running_balance,
            "cost_center": "",
            "currency": currency,
            "is_total_row": True,
            "bold": 1,
        })

        # ── SPACER ROW ────────────────────────────────────────────
        final_data.append({})

    return final_data


def get_conditions(filters):
    conditions = []

    if filters.get("company"):
        conditions.append("gle.company = %(company)s")

    if filters.get("from_date"):
        conditions.append("gle.posting_date >= %(from_date)s")

    if filters.get("to_date"):
        conditions.append("gle.posting_date <= %(to_date)s")

    if filters.get("account"):
        conditions.append("gle.account = %(account)s")

    if filters.get("account_type"):
        conditions.append("acc.account_type = %(account_type)s")

    if filters.get("cost_center"):
        conditions.append("gle.cost_center = %(cost_center)s")

    if filters.get("party_type"):
        conditions.append("gle.party_type = %(party_type)s")

    if filters.get("party"):
        conditions.append("gle.party = %(party)s")

    if filters.get("voucher_type"):
        conditions.append("gle.voucher_type = %(voucher_type)s")

    if filters.get("voucher_no"):
        conditions.append("gle.voucher_no = %(voucher_no)s")

    if not filters.get("show_cancelled"):
        # Already in base WHERE; reinforce for clarity
        pass  # is_cancelled = 0 is always in the base query

    return "AND " + " AND ".join(conditions) if conditions else ""


def get_opening_balance(account, filters):
    """
    Opening balance = net of all GL entries for this account
    strictly BEFORE from_date.
    """
    if not filters.get("from_date"):
        return 0

    opening = frappe.db.sql("""
        SELECT
            SUM(debit - credit) as balance
        FROM
            `tabGL Entry`
        WHERE
            account = %s
            AND posting_date < %s
            AND is_cancelled = 0
            AND company = %s
    """, (
        account,
        filters.get("from_date"),
        filters.get("company")
    ), as_dict=1)

    return flt(opening[0].get("balance")) if opening else 0


def get_summary(data):
    if not data:
        return None

    total_debit = 0
    total_credit = 0
    supplier_count = 0

    for row in data:
        if row and not row.get("is_total_row") and not row.get("is_header_row"):
            total_debit += flt(row.get("debit"))
            total_credit += flt(row.get("credit"))
        if row and row.get("is_header_row"):
            supplier_count += 1

    net_movement = total_debit - total_credit

    return [
        {
            "value": supplier_count,
            "label": "Accounts",
            "datatype": "Int"
        },
        {
            "value": total_debit,
            "label": "Total Debit",
            "datatype": "Currency",
            "currency": "NGN"
        },
        {
            "value": total_credit,
            "label": "Total Credit",
            "datatype": "Currency",
            "currency": "NGN"
        },
        {
            "value": net_movement,
            "label": "Net Movement",
            "datatype": "Currency",
            "currency": "NGN"
        }
    ]


@frappe.whitelist()
def download_excel(filters=None):
    """
    Beautifully formatted Excel export for General Ledger grouped by Account.
    Teal/green color scheme to distinguish from Supplier Ledger.
    """
    import re
    import io
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

    wb = Workbook()
    ws = wb.active
    ws.title = "General Ledger"

    # ── Color Palette (Teal/Green theme) ──────────────────────────
    colors = {
        'dark_teal':        '0E6655',
        'medium_teal':      '148F77',
        'light_teal':       'E8F8F5',
        'light_gray':       'F8F9F9',
        'white':            'FFFFFF',
        'debit_brown':      '8B4513',
        'credit_green':     '1E7E34',
        'positive_balance': '117A65',
        'negative_balance': 'B03A2E',
        'border_gray':      'D5D8DC',
        'title_bg':         'FBFCFC'
    }

    def get_fill(hex_color):
        return PatternFill("solid", fgColor=hex_color)

    thin_border = Border(
        left=Side(style='thin', color=colors['border_gray']),
        right=Side(style='thin', color=colors['border_gray']),
        top=Side(style='thin', color=colors['border_gray']),
        bottom=Side(style='thin', color=colors['border_gray'])
    )

    header_border = Border(
        bottom=Side(style='medium', color=colors['white']),
        right=Side(style='thin', color=colors['medium_teal'])
    )

    NUM_FMT = '#,##0.00'

    # ── Column widths ─────────────────────────────────────────────
    col_widths = [13, 30, 30, 16, 22, 22, 40, 17, 17, 17, 20]
    for i, width in enumerate(col_widths[:num_cols], start=1):
        ws.column_dimensions[get_column_letter(i)].width = width

    def clean_html(value):
        if isinstance(value, str):
            value = re.sub(r'<[^>]+>', '', value)
            value = value.replace('&nbsp;', ' ').replace('—', '-').strip()
        return value if value is not None else ''

    # ── Title Block ───────────────────────────────────────────────
    company = filters.get('company', '')
    from_date = filters.get('from_date', '')
    to_date = filters.get('to_date', '')
    generated_on = datetime.now().strftime('%d %B %Y at %I:%M %p')

    title_rows = [
        ('GENERAL LEDGER REPORT', Font(bold=True, size=16, color=colors['dark_teal']), 28),
        (f'Company: {company}', Font(size=11, color='444444'), 20),
        (f'Period: {from_date} to {to_date}', Font(size=11, color='444444'), 20),
        (f'Generated: {generated_on}', Font(italic=True, size=10, color='666666'), 18),
        ('', None, 8)
    ]

    for text, font, height in title_rows:
        ws.append([text] + [''] * (num_cols - 1))
        row = ws.max_row
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=num_cols)
        cell = ws.cell(row=row, column=1)
        cell.value = text
        if font:
            cell.font = font
        cell.fill = get_fill(colors['title_bg'])
        cell.alignment = Alignment(horizontal='left', vertical='center', indent=1)
        ws.row_dimensions[row].height = height

    # ── Column Headers ────────────────────────────────────────────
    ws.append(col_labels)
    header_row = ws.max_row
    for col_idx, cell in enumerate(ws[header_row], start=1):
        cell.font = Font(bold=True, color=colors['white'], size=11)
        cell.fill = get_fill(colors['medium_teal'])
        cell.alignment = Alignment(
            horizontal='right' if (col_idx - 1) in currency_idx else 'center',
            vertical='center'
        )
        cell.border = header_border
    ws.row_dimensions[header_row].height = 26
    ws.freeze_panes = f'A{header_row + 1}'

    # ── Data Rows ─────────────────────────────────────────────────
    row_counter = 0

    for row_data in data:
        if not row_data:  # Spacer
            ws.append([''] * num_cols)
            ws.row_dimensions[ws.max_row].height = 8
            continue

        is_header = row_data.get('is_header_row')
        is_total = row_data.get('is_total_row')

        excel_row = []
        for idx, field in enumerate(col_fields):
            val = row_data.get(field)
            if idx in currency_idx:
                excel_row.append(flt(val) if val is not None else 0)
            else:
                excel_row.append(clean_html(val) if val is not None else '')

        ws.append(excel_row)
        current_row = ws.max_row

        # ── Account Header Row ────────────────────────────────────
        if is_header:
            ws.merge_cells(
                start_row=current_row, start_column=1,
                end_row=current_row, end_column=num_cols
            )
            account_text = (
                f"  ⬤  {row_data.get('account_name', '')}  "
                f"[{row_data.get('account', '')}]"
            )
            cell = ws.cell(row=current_row, column=1)
            cell.value = account_text
            cell.font = Font(bold=True, color=colors['white'], size=12)
            cell.fill = get_fill(colors['dark_teal'])
            cell.alignment = Alignment(horizontal='left', vertical='center', indent=1)
            ws.row_dimensions[current_row].height = 24

            opening_bal = row_data.get('balance')
            if opening_bal:
                ws.unmerge_cells(
                    start_row=current_row, start_column=1,
                    end_row=current_row, end_column=num_cols
                )
                if num_cols > 1:
                    ws.merge_cells(
                        start_row=current_row, start_column=1,
                        end_row=current_row, end_column=num_cols - 1
                    )
                bal_cell = ws.cell(row=current_row, column=num_cols)
                bal_cell.value = flt(opening_bal)
                bal_cell.number_format = NUM_FMT
                bal_cell.font = Font(italic=True, color='A9DFBF', size=10)
                bal_cell.fill = get_fill(colors['dark_teal'])
                bal_cell.alignment = Alignment(horizontal='right', vertical='center')

        # ── Subtotal Row ──────────────────────────────────────────
        elif is_total:
            ws.row_dimensions[current_row].height = 22

            for col_idx in range(1, num_cols + 1):
                cell = ws.cell(row=current_row, column=col_idx)
                cell.fill = get_fill(colors['light_teal'])
                cell.border = Border(
                    top=Side(style='medium', color=colors['medium_teal']),
                    bottom=Side(style='thin', color=colors['border_gray'])
                )
                field = col_fields[col_idx - 1]

                if field == 'account_name':
                    cell.font = Font(bold=True, color=colors['dark_teal'], size=11)
                    cell.alignment = Alignment(horizontal='left', vertical='center', indent=1)
                elif field == 'description':
                    cell.font = Font(bold=True, color='555555', size=10)
                    cell.alignment = Alignment(horizontal='left', vertical='center')
                elif field == 'debit':
                    cell.number_format = NUM_FMT
                    cell.font = Font(bold=True, color=colors['debit_brown'], size=11)
                    cell.alignment = Alignment(horizontal='right', vertical='center')
                elif field == 'credit':
                    cell.number_format = NUM_FMT
                    cell.font = Font(bold=True, color=colors['credit_green'], size=11)
                    cell.alignment = Alignment(horizontal='right', vertical='center')
                elif field == 'balance':
                    balance = flt(row_data.get('balance'))
                    bal_color = (
                        colors['positive_balance'] if balance > 0
                        else colors['negative_balance'] if balance < 0
                        else '1E7E34'
                    )
                    cell.number_format = NUM_FMT
                    cell.font = Font(bold=True, color=bal_color, size=11)
                    cell.alignment = Alignment(horizontal='right', vertical='center')
                elif (col_idx - 1) in currency_idx:
                    cell.number_format = NUM_FMT
                    cell.font = Font(bold=True, size=11)
                    cell.alignment = Alignment(horizontal='right', vertical='center')

        # ── Normal Transaction Row ────────────────────────────────
        else:
            row_fill = (
                get_fill(colors['light_gray'])
                if row_counter % 2 == 0
                else get_fill(colors['white'])
            )

            for col_idx in range(1, num_cols + 1):
                cell = ws.cell(row=current_row, column=col_idx)
                cell.fill = row_fill
                cell.border = thin_border
                field = col_fields[col_idx - 1]

                if (col_idx - 1) in currency_idx:
                    cell.number_format = NUM_FMT
                    cell.alignment = Alignment(horizontal='right', vertical='center')
                    if field == 'debit' and flt(row_data.get('debit')) > 0:
                        cell.font = Font(color=colors['debit_brown'], size=10)
                    elif field == 'credit' and flt(row_data.get('credit')) > 0:
                        cell.font = Font(color=colors['credit_green'], size=10)
                    elif field == 'balance':
                        balance = flt(row_data.get('balance'))
                        if balance > 0:
                            cell.font = Font(color=colors['positive_balance'], size=10, bold=True)
                        elif balance < 0:
                            cell.font = Font(color=colors['negative_balance'], size=10, bold=True)
                        else:
                            cell.font = Font(size=10)
                    else:
                        cell.font = Font(size=10)
                else:
                    cell.font = Font(size=10)
                    cell.alignment = Alignment(
                        horizontal='left',
                        vertical='center',
                        wrap_text=(field == 'description')
                    )

        row_counter += 1

    # ── Grand Total Row ───────────────────────────────────────────
    if data:
        grand_debit = 0
        grand_credit = 0
        grand_balance = 0

        for row in data:
            if row and not row.get('is_header_row') and not row.get('is_total_row'):
                grand_debit += flt(row.get('debit'))
                grand_credit += flt(row.get('credit'))
            if row and row.get('is_total_row'):
                grand_balance = flt(row.get('balance'))

        ws.append([''] * num_cols)
        ws.row_dimensions[ws.max_row].height = 8

        grand_row = [''] * num_cols
        grand_row[0] = 'GRAND TOTAL'
        grand_row[6] = 'Overall Totals'
        grand_row[7] = grand_debit   # debit index
        grand_row[8] = grand_credit  # credit index
        grand_row[9] = grand_balance # balance index

        ws.append(grand_row)
        total_row = ws.max_row

        for col_idx in range(1, num_cols + 1):
            cell = ws.cell(row=total_row, column=col_idx)
            cell.font = Font(bold=True, size=11, color=colors['dark_teal'])
            cell.fill = get_fill('D5F5E3')
            cell.border = Border(
                top=Side(style='double', color=colors['dark_teal']),
                bottom=Side(style='double', color=colors['dark_teal'])
            )
            if (col_idx - 1) in currency_idx:
                cell.number_format = NUM_FMT
                cell.alignment = Alignment(horizontal='right', vertical='center')
            else:
                cell.alignment = Alignment(horizontal='left', vertical='center')

        if num_cols > 1:
            ws.merge_cells(
                start_row=total_row, start_column=1,
                end_row=total_row, end_column=2
            )

    # ── Page Setup ────────────────────────────────────────────────
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.print_options.gridLines = False
    ws.print_title_rows = f'1:{header_row}'

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    frappe.response['filename'] = f'General_Ledger_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    frappe.response['filecontent'] = output.getvalue()
    frappe.response['type'] = 'binary'