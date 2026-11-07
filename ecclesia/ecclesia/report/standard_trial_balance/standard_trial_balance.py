# Copyright (c) 2026, kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate

from io import BytesIO
import pandas as pd
import json


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def execute(filters=None):
    """
    Trial Balance as at a specific date.
    """
    if not filters:
        filters = {}
    
    # Ensure filters is a dict
    if isinstance(filters, str):
        try:
            filters = json.loads(filters)
        except:
            filters = {}
    
    if not filters.get("company"):
        frappe.throw(_("Company is required"))
    if not filters.get("as_at_date"):
        frappe.throw(_("As at Date is required"))

    columns = get_columns()
    data    = get_data(filters)
    summary = get_report_summary(data)

    return columns, data, None, None, summary


# ---------------------------------------------------------------------------
# Columns
# ---------------------------------------------------------------------------

def get_columns():
    return [
        {"label": _("Code"),           "fieldname": "account_number", "fieldtype": "Data",     "width": 100},
        {"label": _("Account Name"),   "fieldname": "account_name",   "fieldtype": "Data",     "width": 300},
        {"label": _("Parent Account"), "fieldname": "parent_account", "fieldtype": "Data",     "width": 200},
        {"label": _("Balance"),        "fieldname": "balance",        "fieldtype": "Currency", "width": 150},
        {"label": _("Net Debit"),      "fieldname": "net_debit",      "fieldtype": "Currency", "width": 150},
        {"label": _("Net Credit"),     "fieldname": "net_credit",     "fieldtype": "Currency", "width": 150},
    ]


# ---------------------------------------------------------------------------
# Core data
# ---------------------------------------------------------------------------

def _get_fy_dates(as_at_date, company):
    """
    Fetch fiscal year boundaries directly from tabFiscal Year.
    """
    as_at = getdate(as_at_date)

    # Attempt 1: company-linked fiscal year
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

    # Attempt 2: any fiscal year covering the date
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

    # Attempt 3: calendar year fallback
    y = as_at.year
    return getdate(f"{y}-01-01"), getdate(f"{y}-12-31")


def _query_balances(company, to_date, from_date=None):
    """
    Return a dict keyed by account.name -> row dict with balance figures.
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
            acc.account_number,
            acc.account_name,
            acc.parent_account,
            acc.root_type,
            acc.account_type,
            COALESCE(SUM(gle.debit),  0) AS total_debit,
            COALESCE(SUM(gle.credit), 0) AS total_credit,
            COALESCE(SUM(gle.debit) - SUM(gle.credit), 0) AS balance
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


def get_data(filters):
    as_at_date = getdate(filters["as_at_date"])
    company    = filters["company"]

    fy_start, _ = _get_fy_dates(as_at_date, company)

    from datetime import timedelta
    pre_fy_date = fy_start - timedelta(days=1)

    # Opening: everything before FY start (used for BS accounts only)
    opening_map = _query_balances(company, to_date=pre_fy_date)

    # Period: FY start to as_at_date (used for ALL accounts)
    period_map  = _query_balances(company, from_date=fy_start, to_date=as_at_date)

    # Full account master
    account_meta = frappe.db.sql(
        """
        SELECT name, account_number, account_name, parent_account,
               root_type, account_type
        FROM `tabAccount`
        WHERE company = %s AND is_group = 0
        ORDER BY account_number, name
        """,
        company,
        as_dict=True,
    )

    rows = []
    for meta in account_meta:
        acct      = meta["name"]
        root_type = meta["root_type"]

        opening_balance = flt((opening_map.get(acct) or {}).get("balance", 0))
        period_balance  = flt((period_map.get(acct)  or {}).get("balance", 0))

        if root_type in ("Asset", "Liability", "Equity"):
            # Permanent accounts: prior-period opening balance + current period movements
            net = opening_balance + period_balance
        else:
            # P&L accounts: current fiscal year only — no prior period carry-forward
            net = period_balance

        if abs(net) < 0.01:
            continue

        rows.append({
            "account":        meta["name"],  # Add account name for linking
            "account_number": meta.get("account_number") or "",
            "account_name":   meta["account_name"],
            "parent_account": meta.get("parent_account") or "",
            "balance":    net,
            "net_debit":  net  if net > 0 else 0.0,
            "net_credit": -net if net < 0 else 0.0,
            "root_type":  root_type,
        })

    # ------------------------------------------------------------------
    # Synthetic "Current Year Profit / (Loss)" row
    # ------------------------------------------------------------------
    sum_of_rows = sum(flt(r["balance"]) for r in rows)

    if abs(sum_of_rows) > 0.01:
        synthetic_balance = -sum_of_rows
        rows.append({
            "account":        None,  # No account for synthetic row
            "account_number": "",
            "account_name":   "Current Year Profit / (Loss)",
            "parent_account": "Retained Earnings",
            "balance":    synthetic_balance,
            "net_debit":  0.0                   if synthetic_balance < 0 else synthetic_balance,
            "net_credit": abs(synthetic_balance) if synthetic_balance < 0 else 0.0,
            "root_type":  "Equity",
            "is_synthetic": True,
        })
    
    # Totals
    # ------------------------------------------------------------------
    total_balance    = sum(flt(r["balance"])    for r in rows)
    total_net_debit  = sum(flt(r["net_debit"])  for r in rows)
    total_net_credit = sum(flt(r["net_credit"]) for r in rows)

    if rows:
        rows.append({
            "account":        None,
            "account_number": "",
            "account_name":   "TOTAL",
            "parent_account": "",
            "balance":    total_balance,
            "net_debit":  total_net_debit,
            "net_credit": total_net_credit,
            "is_total_row": True,
        })

    return rows


# ---------------------------------------------------------------------------
# Report summary cards
# ---------------------------------------------------------------------------

def get_report_summary(data):
    if not data:
        return []

    total_debit = total_credit = account_count = 0

    for row in data:
        if row.get("is_total_row"):
            continue
        account_count += 1
        total_debit  += flt(row.get("net_debit",  0))
        total_credit += flt(row.get("net_credit", 0))

    diff        = abs(total_debit - total_credit)
    is_balanced = diff < 0.01

    return [
        {"value": total_debit,   "label": _("Total Debit"),     "datatype": "Currency", "indicator": "blue"},
        {"value": total_credit,  "label": _("Total Credit"),    "datatype": "Currency", "indicator": "orange"},
        {"value": diff,          "label": _("Difference"),      "datatype": "Currency", "indicator": "green" if is_balanced else "red"},
        {"value": account_count, "label": _("Active Accounts"), "datatype": "Int",      "indicator": "blue"},
    ]


# ---------------------------------------------------------------------------
# Excel export
# ---------------------------------------------------------------------------

@frappe.whitelist()
def download_cute_excel(filters=None):
    """Generate a world-class Excel Trial Balance report."""
    # Handle filters properly
    if filters is None:
        filters = {}
    elif isinstance(filters, str):
        try:
            filters = json.loads(filters)
        except Exception as e:
            frappe.log_error(f"Error parsing filters: {str(e)}", "Trial Balance Export")
            filters = {}
    elif isinstance(filters, dict):
        pass  # Already a dict
    else:
        filters = {}
    
    # Validate filters
    if not filters.get("company"):
        frappe.throw(_("Company is required. Please select a company."))
    if not filters.get("as_at_date"):
        frappe.throw(_("As at Date is required. Please select a date."))
    
    # Get data
    columns, data = execute(filters)[:2]

    if not data:
        frappe.throw(_("No data available for the selected filters"))

    output = BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook  = writer.book
        worksheet = workbook.add_worksheet("Trial Balance")

        # Colors
        C = {
            "navy":         "#1B3B6F",
            "royal_blue":   "#2E5090",
            "sky_blue":     "#4A90E2",
            "ice_blue":     "#E8F1FA",
            "powder_blue":  "#D4E6F7",
            "charcoal":     "#2C3E50",
            "slate":        "#5D6D7E",
            "silver":       "#BDC3C7",
            "pearl":        "#ECF0F1",
            "snow":         "#F8F9FA",
            "white":        "#FFFFFF",
            "emerald":      "#27AE60",
            "ruby":         "#C0392B",
            "gold":         "#F39C12",
            "total_gold":   "#FFF9E6",
            "border_light": "#D5DBDB",
            "synthetic_bg": "#EEF2FF",
        }

        def F(**kw):
            return workbook.add_format(kw)

        # Header formats
        branding_fmt = F(bold=True, font_size=26, font_name="Arial",
                         font_color=C["white"], bg_color=C["navy"],
                         align="center", valign="vcenter")
        company_fmt  = F(bold=True, font_size=16, font_name="Arial",
                         font_color=C["white"], bg_color=C["royal_blue"],
                         align="center", valign="vcenter")
        badge_fmt    = F(bold=True, font_size=11, font_name="Arial",
                         font_color=C["navy"], bg_color=C["ice_blue"],
                         align="center", valign="vcenter",
                         border=1, border_color=C["sky_blue"])
        lbl_fmt      = F(bold=True, font_size=10, font_name="Arial",
                         font_color=C["navy"], bg_color=C["powder_blue"],
                         align="right", valign="vcenter",
                         border=1, border_color=C["border_light"],
                         right=2, right_color=C["royal_blue"])
        val_fmt      = F(font_size=10, font_name="Arial",
                         font_color=C["charcoal"], bg_color=C["white"],
                         align="left", valign="vcenter",
                         border=1, border_color=C["border_light"])
        hdr_fmt      = F(bold=True, font_size=11, font_name="Arial",
                         font_color=C["white"], bg_color=C["royal_blue"],
                         align="center", valign="vcenter",
                         border=2, border_color=C["navy"],
                         text_wrap=True, top=3, bottom=3,
                         top_color=C["navy"], bottom_color=C["navy"])

        # Hyperlink format
        link_fmt = F(font_size=10, font_name="Arial",
                     font_color=C["sky_blue"], underline=True,
                     align="left", valign="vcenter")

        # Set row heights
        for i, h in [(0,45),(1,32),(2,8),(3,24),(4,20),(5,20),(6,8),(7,35)]:
            worksheet.set_row(i, h)

        # Set column widths
        col_widths = [16, 45, 38, 20, 20, 20]
        for i, w in enumerate(col_widths):
            worksheet.set_column(i, i, w)

        # Header
        worksheet.merge_range("A1:F1", "TRIAL BALANCE REPORT", branding_fmt)
        worksheet.merge_range("A2:F2", filters.get("company","").upper(), company_fmt)
        worksheet.merge_range("A4:F4", "FINANCIAL STATEMENT", badge_fmt)
        worksheet.merge_range("A5:B5", "Company Name:",   lbl_fmt)
        worksheet.merge_range("C5:F5", filters.get("company","N/A"), val_fmt)
        worksheet.merge_range("A6:B6", "Reporting Date:", lbl_fmt)
        worksheet.merge_range("C6:F6", str(filters.get("as_at_date","N/A")), val_fmt)

        # Column headers
        for col_num, col in enumerate(columns):
            worksheet.write(7, col_num, col["label"], hdr_fmt)

        # Data formats
        def tf(bg):
            return F(font_size=10, font_name="Calibri", font_color=C["charcoal"],
                     bg_color=bg, border=1, border_color=C["border_light"], valign="vcenter")

        def nf(bg, color=None, bold=False):
            return F(font_size=10, font_name="Calibri", num_format="#,##0.00",
                     font_color=color or C["charcoal"], bold=bold,
                     bg_color=bg, border=1, border_color=C["border_light"],
                     align="right", valign="vcenter")

        t_even  = tf(C["white"]);   t_odd  = tf(C["snow"])
        n_even  = nf(C["white"]);   n_odd  = nf(C["snow"])
        dr_even = nf(C["white"], C["emerald"], True);  dr_odd = nf(C["snow"], C["emerald"], True)
        cr_even = nf(C["white"], C["ruby"],    True);  cr_odd = nf(C["snow"], C["ruby"],    True)

        syn_t = F(italic=True, font_size=10, font_name="Calibri",
                  font_color=C["navy"], bg_color=C["synthetic_bg"],
                  border=1, border_color=C["sky_blue"], valign="vcenter")
        syn_n = F(italic=True, font_size=10, font_name="Calibri",
                  num_format="#,##0.00", font_color=C["navy"],
                  bg_color=C["synthetic_bg"], border=1, border_color=C["sky_blue"],
                  align="right", valign="vcenter")

        tot_t = F(bold=True, font_size=12, font_name="Arial",
                  font_color=C["navy"], bg_color=C["total_gold"],
                  border=2, border_color=C["gold"],
                  top=3, top_color=C["navy"], valign="vcenter")
        tot_n = F(bold=True, font_size=12, font_name="Arial",
                  num_format="#,##0.00", font_color=C["navy"],
                  bg_color=C["total_gold"], border=2, border_color=C["gold"],
                  top=3, top_color=C["navy"], align="right", valign="vcenter")

        # Write data rows
        row_num = 8
        for dr in data:
            is_total = dr.get("is_total_row")
            is_syn   = dr.get("is_synthetic")
            is_even  = (row_num - 8) % 2 == 0
            account  = dr.get("account")

            worksheet.set_row(row_num, 28 if is_total else 22)

            for col_num, col in enumerate(columns):
                fn  = col["fieldname"]
                val = dr.get(fn, "")
                
                # Create hyperlink for account name and account code if account exists
                if account and fn in ["account_name", "account_number"] and not is_total and not is_syn:
                    company = filters.get("company", "")
                    as_at_date = filters.get("as_at_date", "")
                    gl_url = f'/app/query-report/General%20Ledger?account={account}&company={company}&from_date={as_at_date}&to_date={as_at_date}'
                    worksheet.write_url(row_num, col_num, gl_url, link_fmt, str(val))
                    
                elif is_total:
                    if col["fieldtype"] == "Currency" and val != "":
                        worksheet.write_number(row_num, col_num, flt(val), tot_n)
                    else:
                        worksheet.write(row_num, col_num, str(val), tot_t)

                elif is_syn:
                    if col["fieldtype"] == "Currency" and val != "":
                        worksheet.write_number(row_num, col_num, flt(val), syn_n)
                    else:
                        worksheet.write(row_num, col_num, str(val), syn_t)

                else:
                    if col["fieldtype"] == "Currency" and val != "":
                        v = flt(val)
                        if fn == "balance":
                            fmt_ = (dr_even if is_even else dr_odd) if v > 0 else \
                                   (cr_even if is_even else cr_odd) if v < 0 else \
                                   (n_even  if is_even else n_odd)
                        elif fn == "net_debit"  and v > 0: fmt_ = dr_even if is_even else dr_odd
                        elif fn == "net_credit" and v > 0: fmt_ = cr_even if is_even else cr_odd
                        else:                               fmt_ = n_even  if is_even else n_odd
                        worksheet.write_number(row_num, col_num, v, fmt_)
                    else:
                        worksheet.write(row_num, col_num, str(val),
                                        t_even if is_even else t_odd)
            row_num += 1

        # Executive Summary
        summary_data = get_report_summary(data)
        row_num += 3

        s_title = F(bold=True, font_size=15, font_name="Arial",
                    font_color=C["white"], bg_color=C["royal_blue"],
                    align="center", valign="vcenter",
                    border=2, border_color=C["navy"])
        s_lbl   = F(bold=True, font_size=10, font_name="Arial",
                    font_color=C["navy"], bg_color=C["ice_blue"],
                    align="center", valign="vcenter",
                    border=1, border_color=C["sky_blue"])
        s_val   = F(bold=True, font_size=14, font_name="Arial",
                    font_color=C["navy"], bg_color=C["white"],
                    align="center", valign="vcenter",
                    border=2, border_color=C["sky_blue"],
                    num_format="#,##0.00")

        worksheet.set_row(row_num, 32)
        worksheet.merge_range(row_num, 0, row_num, 5, "EXECUTIVE SUMMARY", s_title)
        row_num += 1
        sr = row_num

        for i, s in enumerate(summary_data):
            co = (i % 2) * 3
            ro = sr + (i // 2) * 3
            worksheet.set_row(ro, 24); worksheet.set_row(ro+1, 32); worksheet.set_row(ro+2, 4)
            worksheet.merge_range(ro,   co, ro,   co+2, s.get("label",""), s_lbl)
            worksheet.merge_range(ro+1, co, ro+1, co+2, flt(s.get("value",0)), s_val)

        # Footer
        from datetime import datetime
        footer_row = sr + 7
        footer_fmt = F(italic=True, font_size=9, font_name="Arial",
                       font_color=C["slate"], bg_color=C["pearl"],
                       align="center", valign="vcenter",
                       border=1, border_color=C["silver"])
        worksheet.set_row(footer_row, 22)
        worksheet.merge_range(
            footer_row, 0, footer_row, 5,
            f"Report Generated: {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}"
            f" | Powered by ERPNext",
            footer_fmt,
        )

        # Page setup
        worksheet.freeze_panes(8, 0)
        worksheet.autofilter(7, 0, row_num - 1, 5)
        worksheet.set_landscape()
        worksheet.set_paper(9)
        worksheet.fit_to_pages(1, 0)
        worksheet.set_margins(left=0.6, right=0.6, top=0.8, bottom=0.8)
        worksheet.set_header(
            f'&L&"Arial,Bold"&12{filters.get("company","")}'
            f'&R&"Arial"&10Page &P of &N'
        )
        worksheet.set_footer('&C&"Arial,Italic"&9Trial Balance Report - Confidential')
        worksheet.repeat_rows(7)

    # Save and return
    from datetime import datetime
    ts           = datetime.now().strftime("%Y%m%d_%H%M%S")
    company_safe = filters.get("company","Company").replace(" ","_").replace("/","_")

    frappe.response["filename"]     = f"TB_{company_safe}_{filters.get('as_at_date')}_{ts}.xlsx"
    frappe.response["filecontent"]  = output.getvalue()
    frappe.response["type"]         = "binary"
    frappe.response["content_type"] = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )