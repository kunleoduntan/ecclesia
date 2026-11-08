# Copyright (c) 2026, kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, today
import json
from datetime import datetime, timedelta
import io


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def execute(filters=None):
    if not filters:
        filters = {}

    if not filters.get("company"):
        frappe.throw(_("Company is required"))
    if not filters.get("as_at_date"):
        filters["as_at_date"] = today()

    company_currency = get_company_currency(filters.get("company"))
    filters["currency"] = company_currency

    columns = get_columns(company_currency)
    data    = get_data(filters)
    summary = get_report_summary(data, filters)

    return columns, data, None, None, summary


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_company_currency(company):
    currency = frappe.db.get_value("Company", company, "default_currency")
    return currency or "NGN"


def get_columns(currency):
    return [
        {"label": _("Account Code"),         "fieldname": "account_code", "fieldtype": "Data",     "width": 120},
        {"label": _("Account Name"),          "fieldname": "account_name", "fieldtype": "Data",     "width": 350},
        {"label": _("Account Type"),          "fieldname": "account_type", "fieldtype": "Data",     "width": 150},
        {"label": _(f"Debit ({currency})"),   "fieldname": "debit",        "fieldtype": "Currency", "options": "currency", "width": 180},
        {"label": _(f"Credit ({currency})"),  "fieldname": "credit",       "fieldtype": "Currency", "options": "currency", "width": 180},
        {"label": _(f"Balance ({currency})"), "fieldname": "balance",      "fieldtype": "Currency", "options": "currency", "width": 180},
    ]


# ---------------------------------------------------------------------------
# Fiscal year — pure SQL, three-tier fallback, no external imports
# ---------------------------------------------------------------------------

def _get_fy_dates(as_at_date, company):
    """
    Return (fy_start, fy_end) for the FY that contains as_at_date.
    1. FY linked to company via tabFiscal Year Company (parent = FY name)
    2. Any FY whose date range covers as_at_date
    3. Calendar year fallback
    """
    as_at = getdate(as_at_date)

    row = frappe.db.sql(
        """
        SELECT fy.year_start_date, fy.year_end_date
        FROM `tabFiscal Year` fy
        INNER JOIN `tabFiscal Year Company` fyc ON fyc.parent = fy.name
        WHERE fyc.company = %(company)s
          AND %(date)s BETWEEN fy.year_start_date AND fy.year_end_date
        ORDER BY fy.year_start_date DESC
        LIMIT 1
        """,
        {"company": company, "date": as_at},
    )
    if row:
        return getdate(row[0][0]), getdate(row[0][1])

    row = frappe.db.sql(
        """
        SELECT year_start_date, year_end_date
        FROM `tabFiscal Year`
        WHERE %(date)s BETWEEN year_start_date AND year_end_date
        ORDER BY year_start_date DESC
        LIMIT 1
        """,
        {"date": as_at},
    )
    if row:
        return getdate(row[0][0]), getdate(row[0][1])

    y = as_at.year
    return getdate(f"{y}-01-01"), getdate(f"{y}-12-31")


# ---------------------------------------------------------------------------
# GL balance queries
# ---------------------------------------------------------------------------

def _query_balances(company, to_date, from_date=None):
    """
    Return { account.name -> row_dict } with raw GL totals.

    from_date=None  → inception to to_date        (BS opening mode)
    from_date set   → from_date to to_date         (period mode)
    """
    params = {"company": company, "to_date": to_date}

    if from_date:
        params["from_date"] = from_date
        date_clause = (
            "AND gle.posting_date >= %(from_date)s "
            "AND gle.posting_date <= %(to_date)s"
        )
    else:
        date_clause = "AND gle.posting_date <= %(to_date)s"

    rows = frappe.db.sql(
        f"""
        SELECT
            acc.name            AS account,
            COALESCE(SUM(gle.debit_in_account_currency),  0) AS total_debit,
            COALESCE(SUM(gle.credit_in_account_currency), 0) AS total_credit,
            COALESCE(
                SUM(gle.debit_in_account_currency) -
                SUM(gle.credit_in_account_currency), 0
            ) AS balance
        FROM `tabAccount` acc
        LEFT JOIN `tabGL Entry` gle
            ON  gle.account      = acc.name
            AND gle.company      = %(company)s
            AND gle.docstatus    = 1
            AND gle.is_cancelled = 0
            {date_clause}
        WHERE acc.company  = %(company)s
          AND acc.is_group = 0
        GROUP BY acc.name
        """,
        params,
        as_dict=True,
    )
    return {r["account"]: r for r in rows}


# ---------------------------------------------------------------------------
# Core data builder
# ---------------------------------------------------------------------------

def get_data(filters):
    as_at_date   = getdate(filters.get("as_at_date"))
    company      = filters.get("company")
    include_zero = filters.get("include_zero_balance", 0)

    fy_start, _ = _get_fy_dates(as_at_date, company)
    pre_fy_date = fy_start - timedelta(days=1)

    # Opening: everything BEFORE current FY start (BS accounts only)
    opening_map = _query_balances(company, to_date=pre_fy_date)

    # Period: current FY start → as_at_date (all accounts)
    period_map  = _query_balances(company, from_date=fy_start, to_date=as_at_date)

    # Full account master in standard display order
    account_meta = frappe.db.sql(
        """
        SELECT name, account_number, account_name, parent_account,
               root_type, account_type
        FROM `tabAccount`
        WHERE company  = %s
          AND is_group = 0
        ORDER BY
            CASE root_type
                WHEN 'Asset'     THEN 1
                WHEN 'Liability' THEN 2
                WHEN 'Equity'    THEN 3
                WHEN 'Income'    THEN 4
                WHEN 'Expense'   THEN 5
                ELSE 6
            END,
            account_number, name
        """,
        company,
        as_dict=True,
    )

    # ------------------------------------------------------------------
    # Build one display row per account
    #
    # Balance Sheet accounts (Asset, Liability, Equity):
    #   net = opening_balance + period_balance
    #   i.e. all GL entries from inception to as_at_date
    #
    # P&L accounts (Income, Expense):
    #   net = period_balance only
    #   i.e. entries within the current fiscal year — no prior-period carry
    # ------------------------------------------------------------------
    raw_rows = []

    for meta in account_meta:
        acct      = meta["name"]
        root_type = meta["root_type"]

        opening_rec = opening_map.get(acct) or {}
        period_rec  = period_map.get(acct)  or {}

        opening_bal = flt(opening_rec.get("balance",      0))
        period_bal  = flt(period_rec.get("balance",       0))
        open_dr     = flt(opening_rec.get("total_debit",  0))
        open_cr     = flt(opening_rec.get("total_credit", 0))
        period_dr   = flt(period_rec.get("total_debit",   0))
        period_cr   = flt(period_rec.get("total_credit",  0))

        if root_type in ("Asset", "Liability", "Equity"):
            net    = opening_bal + period_bal
            debit  = open_dr + period_dr
            credit = open_cr + period_cr
        else:
            net    = period_bal
            debit  = period_dr
            credit = period_cr

        if abs(net) < 0.01 and not include_zero:
            continue

        raw_rows.append({
            "account_code":   meta.get("account_number") or "",
            "account_name":   meta["account_name"],
            "account":        meta["name"],  # Add this for linking
            "account_type":   root_type,
            "parent_account": meta.get("parent_account") or "",
            "debit":          debit,
            "credit":         credit,
            "balance":        net,
            "root_type":      root_type,
        })

    # ------------------------------------------------------------------
    # Synthetic "Current Year Profit / (Loss)" Equity row
    #
    # synthetic_balance = -(sum of all account balances)
    #
    # This is the ONLY value guaranteed to make Total Debits == Total Credits.
    # We do NOT derive it from summing income/expense nets because prior-year
    # closing JEs (dated inside the current FY window) inflate those totals.
    # ------------------------------------------------------------------
    sum_of_balances = sum(flt(r["balance"]) for r in raw_rows)

    if abs(sum_of_balances) > 0.01:
        synthetic_bal = -sum_of_balances
        raw_rows.append({
            "account_code":   "",
            "account_name":   "Current Year Profit / (Loss)",
            "account":        None,  # No account link for synthetic row
            "account_type":   "Equity",
            "parent_account": "Retained Earnings",
            "debit":          0.0                if synthetic_bal < 0 else synthetic_bal,
            "credit":         abs(synthetic_bal) if synthetic_bal < 0 else 0.0,
            "balance":        synthetic_bal,
            "root_type":      "Equity",
            "is_synthetic":   True,
        })

    # ------------------------------------------------------------------
    # Group into sections with headers / subtotals
    # ------------------------------------------------------------------
    grouped_data = []
    current_type = None
    type_totals  = {}

    for row in raw_rows:
        root_type = row.get("root_type", "Other")

        if current_type != root_type:
            if current_type:
                _append_subtotal(grouped_data, type_totals, current_type)

            current_type = root_type
            type_totals[root_type] = {"debit": 0.0, "credit": 0.0, "balance": 0.0}

            grouped_data.append({
                "account_code": "", "account_name": "═" * 51,
                "account_type": "", "debit": None, "credit": None, "balance": None,
                "is_header_row": True,
            })
            grouped_data.append({
                "account_code": "",
                "account_name": f"► {root_type.upper()} ACCOUNTS",
                "account_type": "", "debit": None, "credit": None, "balance": None,
                "is_section_header": True,
            })
            grouped_data.append({
                "account_code": "", "account_name": "═" * 51,
                "account_type": "", "debit": None, "credit": None, "balance": None,
                "is_header_row": True,
            })

        type_totals[root_type]["debit"]   += flt(row.get("debit",   0))
        type_totals[root_type]["credit"]  += flt(row.get("credit",  0))
        type_totals[root_type]["balance"] += flt(row.get("balance", 0))

        grouped_data.append(row)

    if current_type:
        _append_subtotal(grouped_data, type_totals, current_type)

    # ------------------------------------------------------------------
    # Grand total (sum from raw_rows — includes synthetic row)
    # ------------------------------------------------------------------
    total_debit   = sum(flt(r.get("debit",   0)) for r in raw_rows)
    total_credit  = sum(flt(r.get("credit",  0)) for r in raw_rows)
    total_balance = sum(flt(r.get("balance", 0)) for r in raw_rows)

    grouped_data.append({})  # spacer

    grouped_data.append({
        "account_code": "",
        "account_name": "GRAND TOTAL",
        "account_type": "",
        "debit":        total_debit,
        "credit":       total_credit,
        "balance":      total_balance,
        "is_total_row": True,
    })

    return grouped_data


def _append_subtotal(grouped_data, type_totals, account_type):
    totals = type_totals.get(account_type, {})
    grouped_data.append({
        "account_code": "", "account_name": "─" * 50,
        "account_type": "", "debit": None, "credit": None, "balance": None,
        "is_separator": True,
    })
    grouped_data.append({
        "account_code": "",
        "account_name": f"SUBTOTAL — {account_type.upper()}",
        "account_type": "",
        "debit":        totals.get("debit",   0),
        "credit":       totals.get("credit",  0),
        "balance":      totals.get("balance", 0),
        "is_subtotal_row": True,
    })
    grouped_data.append({})  # spacer


# ---------------------------------------------------------------------------
# Report summary cards
# ---------------------------------------------------------------------------

def get_report_summary(data, filters):
    if not data:
        return []

    skip = {"is_header_row", "is_subtotal_row", "is_total_row",
            "is_separator", "is_section_header", "is_synthetic"}

    total_debit = total_credit = account_count = 0

    for row in data:
        if not row:
            continue
        if any(row.get(f) for f in skip):
            continue
        account_count += 1
        total_debit  += flt(row.get("debit",  0))
        total_credit += flt(row.get("credit", 0))

    difference  = abs(total_debit - total_credit)
    is_balanced = difference < 0.01
    currency    = filters.get("currency", "NGN")

    return [
        {"value": total_debit,   "label": "Total Debit",     "datatype": "Currency", "indicator": "Blue",  "currency": currency},
        {"value": total_credit,  "label": "Total Credit",    "datatype": "Currency", "indicator": "Green", "currency": currency},
        {"value": difference,    "label": "Difference",      "datatype": "Currency", "indicator": "Green" if is_balanced else "Red", "currency": currency},
        {"value": account_count, "label": "Active Accounts", "datatype": "Int",      "indicator": "Blue"},
    ]


# ---------------------------------------------------------------------------
# Excel export
# ---------------------------------------------------------------------------

@frappe.whitelist()
def download_excel(filters=None):
    """Generate a beautifully formatted Trial Balance Excel report."""
    if filters is None:
        filters = {}
    if isinstance(filters, str):
        filters = json.loads(filters)

    filters["currency"] = get_company_currency(filters.get("company"))
    columns, data = execute(filters)[:2]

    if not data:
        frappe.throw(_("No data available for the selected filters"))

    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Trial Balance"

    C = {
        "dark_blue":       "1E3F6E",
        "medium_blue":     "2C5A9E",
        "light_blue":      "E6F0FA",
        "light_gray":      "F5F5F5",
        "white":           "FFFFFF",
        "debit_blue":      "2568B2",
        "credit_green":    "1E7E34",
        "positive_orange": "E67E22",
        "negative_red":    "C0392B",
        "border_gray":     "D0D7DE",
        "synthetic_bg":    "EEF2FF",
        "synthetic_font":  "1B3B6F",
    }

    def fill(c):      return PatternFill("solid", fgColor=c)
    def F(**k):       return Font(**k)
    def A(**k):       return Alignment(**k)
    def Bdr(**k):     return Border(**k)
    def Sd(s, c):     return Side(style=s, color=c)

    thin = Bdr(
        left=Sd("thin", C["border_gray"]),  right=Sd("thin",  C["border_gray"]),
        top=Sd("thin",  C["border_gray"]),  bottom=Sd("thin", C["border_gray"]),
    )
    num_fmt = "#,##0.00"

    col_widths = [18, 50, 18, 20, 20, 20]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # Header block
    cur_row = 1

    def merge_row(r, value, fnt, fll, aln, height):
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
        c = ws.cell(row=r, column=1, value=value)
        c.font = fnt; c.fill = fll; c.alignment = aln
        ws.row_dimensions[r].height = height

    merge_row(cur_row, "TRIAL BALANCE STATEMENT",
              F(name="Arial", size=22, bold=True, color="FFFFFF"),
              fill(C["dark_blue"]), A(horizontal="center", vertical="center"), 40)
    cur_row += 1

    merge_row(cur_row, filters.get("company", "").upper(),
              F(name="Arial", size=14, bold=True, color="FFFFFF"),
              fill(C["medium_blue"]), A(horizontal="center", vertical="center"), 30)
    cur_row += 1

    merge_row(cur_row,
              f"AS AT {filters.get('as_at_date', '')} | Currency: {filters.get('currency', 'NGN')}",
              F(name="Arial", size=11, bold=True, color="333333"),
              fill("E8F0FE"), A(horizontal="center", vertical="center"), 25)
    cur_row += 1

    ws.row_dimensions[cur_row].height = 8
    cur_row += 1

    # Column headers
    header_row = cur_row
    for col_num, col in enumerate(columns, 1):
        cell = ws.cell(row=header_row, column=col_num, value=col["label"])
        cell.font      = F(name="Arial", size=11, bold=True, color="FFFFFF")
        cell.fill      = fill(C["medium_blue"])
        cell.alignment = A(horizontal="center", vertical="center", wrap_text=True)
        cell.border    = Bdr(bottom=Sd("medium", "FFFFFF"), right=Sd("thin", "4A7AB3"))
    ws.row_dimensions[header_row].height = 35
    cur_row += 1
    ws.freeze_panes = f"A{cur_row}"

    # Data rows
    row_counter = 0

    for row_data in data:
        if not row_data:
            for c in range(1, 7):
                ws.cell(row=cur_row, column=c, value="")
            ws.row_dimensions[cur_row].height = 8
            cur_row += 1
            continue

        is_header    = row_data.get("is_header_row")
        is_section   = row_data.get("is_section_header")
        is_separator = row_data.get("is_separator")
        is_subtotal  = row_data.get("is_subtotal_row")
        is_total     = row_data.get("is_total_row")
        is_synthetic = row_data.get("is_synthetic")

        if is_header or is_section or is_separator:
            ws.merge_cells(start_row=cur_row, start_column=1, end_row=cur_row, end_column=6)
            cell = ws.cell(row=cur_row, column=1, value=row_data.get("account_name", ""))
            if is_section:
                cell.font      = F(name="Arial", size=11, bold=True, color=C["dark_blue"])
                cell.fill      = fill(C["light_blue"])
                cell.alignment = A(horizontal="left", vertical="center")
                cell.border    = Bdr(top=Sd("medium", C["dark_blue"]), bottom=Sd("thin", C["border_gray"]))
                ws.row_dimensions[cur_row].height = 22
            else:
                cell.font      = F(name="Arial", size=10, color=C["border_gray"])
                cell.alignment = A(horizontal="left", vertical="center")
                ws.row_dimensions[cur_row].height = 14
            cur_row += 1

        elif is_subtotal:
            for col_num, col in enumerate(columns, 1):
                fn  = col["fieldname"]
                val = row_data.get(fn, "")
                cell = ws.cell(row=cur_row, column=col_num)
                cell.fill   = fill(C["light_blue"])
                cell.border = Bdr(top=Sd("thin", C["border_gray"]), bottom=Sd("thin", C["border_gray"]))
                cell.font   = F(name="Arial", size=10, bold=True, color=C["dark_blue"])
                if col["fieldtype"] == "Currency" and val is not None:
                    cell.value         = flt(val)
                    cell.number_format = num_fmt
                    cell.alignment     = A(horizontal="right", vertical="center")
                else:
                    cell.value     = str(val) if val else ""
                    cell.alignment = A(horizontal="left", vertical="center")
            ws.row_dimensions[cur_row].height = 22
            cur_row += 1

        elif is_total:
            for col_num, col in enumerate(columns, 1):
                fn  = col["fieldname"]
                val = row_data.get(fn, "")
                cell = ws.cell(row=cur_row, column=col_num)
                cell.font   = F(name="Arial", size=12, bold=True, color="FFFFFF")
                cell.fill   = fill(C["dark_blue"])
                cell.border = Bdr(top=Sd("double", C["dark_blue"]), bottom=Sd("double", C["dark_blue"]))
                if col["fieldtype"] == "Currency" and val is not None and val != "":
                    cell.value         = flt(val)
                    cell.number_format = num_fmt
                    cell.alignment     = A(horizontal="right", vertical="center")
                else:
                    cell.value     = str(val) if val else ""
                    cell.alignment = A(horizontal="left", vertical="center")
            ws.row_dimensions[cur_row].height = 28
            cur_row += 1

        elif is_synthetic:
            for col_num, col in enumerate(columns, 1):
                fn  = col["fieldname"]
                val = row_data.get(fn, "")
                cell = ws.cell(row=cur_row, column=col_num)
                cell.fill   = fill(C["synthetic_bg"])
                cell.border = thin
                if col["fieldtype"] == "Currency" and val is not None and val != "":
                    cell.value         = flt(val)
                    cell.number_format = num_fmt
                    cell.font          = F(name="Calibri", size=10, italic=True, bold=True, color=C["synthetic_font"])
                    cell.alignment     = A(horizontal="right", vertical="center")
                else:
                    cell.value     = str(val) if val else ""
                    cell.font      = F(name="Calibri", size=10, italic=True, color=C["synthetic_font"])
                    cell.alignment = A(horizontal="left", vertical="center")
            ws.row_dimensions[cur_row].height = 20
            cur_row += 1

        else:
            is_even      = row_counter % 2 == 0
            row_fill_obj = fill(C["white"]) if is_even else fill(C["light_gray"])

            for col_num, col in enumerate(columns, 1):
                fn  = col["fieldname"]
                val = row_data.get(fn, "")
                cell = ws.cell(row=cur_row, column=col_num)
                cell.fill   = row_fill_obj
                cell.border = thin

                if col["fieldtype"] == "Currency" and val is not None and val != "":
                    v = flt(val)
                    cell.value         = v
                    cell.number_format = num_fmt
                    cell.alignment     = A(horizontal="right", vertical="center")
                    if fn == "debit" and v > 0:
                        cell.font = F(name="Calibri", size=10, bold=True, color=C["debit_blue"])
                    elif fn == "credit" and v > 0:
                        cell.font = F(name="Calibri", size=10, bold=True, color=C["credit_green"])
                    elif fn == "balance":
                        if v > 0:
                            cell.font = F(name="Calibri", size=10, bold=True, color=C["positive_orange"])
                        elif v < 0:
                            cell.font = F(name="Calibri", size=10, bold=True, color=C["negative_red"])
                        else:
                            cell.font = F(name="Calibri", size=10)
                    else:
                        cell.font = F(name="Calibri", size=10)
                else:
                    cell.value     = str(val) if val else ""
                    cell.font      = F(name="Calibri", size=10)
                    cell.alignment = A(horizontal="left", vertical="center")

            ws.row_dimensions[cur_row].height = 18
            cur_row += 1
            row_counter += 1

    # Executive summary
    cur_row += 2
    ws.merge_cells(start_row=cur_row, start_column=1, end_row=cur_row, end_column=6)
    sc = ws.cell(row=cur_row, column=1, value="EXECUTIVE SUMMARY")
    sc.font = F(name="Arial", size=14, bold=True, color="FFFFFF")
    sc.fill = fill(C["medium_blue"])
    sc.alignment = A(horizontal="center", vertical="center")
    ws.row_dimensions[cur_row].height = 30
    cur_row += 1

    summary_data = get_report_summary(data, filters)
    for i, s in enumerate(summary_data):
        cs = 1 + (i % 2) * 3
        r  = cur_row + (i // 2) * 2

        ws.merge_cells(start_row=r, start_column=cs, end_row=r, end_column=cs + 2)
        lc = ws.cell(row=r, column=cs, value=s.get("label", ""))
        lc.font = F(name="Arial", size=10, bold=True, color="333333")
        lc.fill = fill("E8F0FE")
        lc.alignment = A(horizontal="center", vertical="center")
        lc.border = thin
        ws.row_dimensions[r].height = 22

        ws.merge_cells(start_row=r+1, start_column=cs, end_row=r+1, end_column=cs + 2)
        vc = ws.cell(row=r+1, column=cs, value=flt(s.get("value", 0)))
        vc.font = F(name="Arial", size=16, bold=True, color=C["dark_blue"])
        vc.fill = fill(C["white"])
        vc.alignment = A(horizontal="center", vertical="center")
        vc.border = Bdr(left=Sd("thin", C["border_gray"]), right=Sd("thin", C["border_gray"]),
                        bottom=Sd("thin", C["border_gray"]))
        if s.get("datatype") == "Currency":
            vc.number_format = num_fmt
        ws.row_dimensions[r+1].height = 30

    # Footer
    cur_row += 6
    ws.merge_cells(start_row=cur_row, start_column=1, end_row=cur_row, end_column=6)
    fc = ws.cell(row=cur_row, column=1,
                 value=f"Generated on: {datetime.now().strftime('%d %B %Y at %I:%M %p')} | Trial Balance Report")
    fc.font = F(name="Arial", size=9, italic=True, color="666666")
    fc.alignment = A(horizontal="center", vertical="center")
    fc.border = Bdr(top=Sd("thin", "CCCCCC"))
    ws.row_dimensions[cur_row].height = 22

    # Page setup
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize   = 9
    ws.page_setup.fitToPage   = True
    ws.page_setup.fitToWidth  = 1
    ws.page_setup.fitToHeight = 0
    ws.print_title_rows       = f"1:{header_row}"

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
    company_safe = filters.get("company", "Company").replace(" ", "_").replace("/", "_")

    frappe.response["filename"]     = f"Trial_Balance_{company_safe}_{filters.get('as_at_date')}_{timestamp}.xlsx"
    frappe.response["filecontent"]  = output.getvalue()
    frappe.response["type"]         = "binary"
    frappe.response["content_type"] = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )