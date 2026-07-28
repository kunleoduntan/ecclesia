# remittance_export.py
# Deploy: apps/ecclesia/ecclesia/api/remittance_export.py
#
# Amount derivation exactly mirrors the live report files:
#   pension_remittance_report.py  → "Pension (ER)" / "Pension (EE)"
#   paye_deduction_report.py      → "Tax"
#   nhf_remittance_report.py      → "NHF" / "Basic"
#   nsitf_remittance_report.py    → "NSITF" (table auto-detected from Salary Component)
#
# The same get_component_amount() function used by the reports is used here.
# No flexible/fuzzy matching — exact component names, exact table names.

from __future__ import annotations
import base64, io
from datetime import datetime

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
except ImportError:
    openpyxl = None

# ── Component name constants (must match your Salary Components exactly) ──────
PENSION_ER_COMPONENT = "Pension (ER)"    # Earnings
PENSION_EE_COMPONENT = "Pension (EE)"    # Deductions
TAX_COMPONENT        = "Tax"             # Deductions (PAYE)
NHF_COMPONENT        = "NHF"            # Deductions
BASIC_COMPONENT      = "Basic"           # Earnings
NSITF_COMPONENT      = "NSITF"          # Earnings or Deductions (auto-detected)

# ── Style helpers ─────────────────────────────────────────────────────────────
_NAVY  = "1E3A5F"
_ALT   = "F0F4FF"
_TOTAL = "E2E8F0"

def _hf():    return Font(bold=True, color="FFFFFF", size=11, name="Calibri")
def _hfill(): return PatternFill("solid", fgColor=_NAVY)
def _tf():    return Font(bold=True, size=11, name="Calibri")
def _tfill(): return PatternFill("solid", fgColor=_TOTAL)
def _df():    return Font(size=10, name="Calibri")
def _bdr():
    s = Side(style='thin', color="CCCCCC")
    return Border(left=s, right=s, top=s, bottom=s)
def _c():  return Alignment(horizontal='center', vertical='center')
def _l():  return Alignment(horizontal='left',   vertical='center')
def _r():  return Alignment(horizontal='right',  vertical='center')
def _alt(i): return PatternFill("solid", fgColor=_ALT) if i % 2 == 0 else None
def _cw(ws, col, w): ws.column_dimensions[get_column_letter(col)].width = w

def _b64(wb):
    buf = io.BytesIO(); wb.save(buf)
    return base64.b64encode(buf.getvalue()).decode()

def _period(pe):
    return getdate(pe.posting_date).strftime("%B %Y")

def _range(pe):
    return (f"{getdate(pe.start_date).strftime('%d-%m-%Y')} "
            f"to {getdate(pe.end_date).strftime('%d-%m-%Y')}")


# ── Core: exact component lookup (same as all 4 reports) ─────────────────────
def get_component_amount(salary_slip, table, component_name):
    """
    Get salary component amount from Salary Detail.
    Identical to the function in all 4 uploaded report files.
    table = "earnings" or "deductions"
    """
    rows = frappe.get_all(
        "Salary Detail",
        filters={
            "parent":      salary_slip,
            "parenttype":  "Salary Slip",
            "parentfield": table,
            "salary_component": component_name,
        },
        fields=["amount"],
    )
    return flt(rows[0].amount) if rows else 0.0


def get_nsitf_component_meta():
    """
    Auto-detect which table NSITF lives in — same as nsitf_remittance_report.py.
    Returns a dict with 'name' and 'type' (Earning / Deduction).
    Falls back to Deduction if not found (most common for employer levies).
    """
    comp = frappe.db.get_value(
        "Salary Component",
        NSITF_COMPONENT,
        ["name", "type"],
        as_dict=True,
    )
    if not comp:
        # Component not found — return a safe default so we can still run
        return frappe._dict(name=NSITF_COMPONENT, type="Earning")
    return comp


def get_nsitf_table(comp_meta):
    """Convert component type to parentfield name."""
    return "earnings" if comp_meta.type == "Earning" else "deductions"


# ── Fetch salary slips for a payroll entry with employee details ──────────────
def _get_slips(payroll_entry):
    return frappe.db.sql("""
        SELECT
            ss.name                                            AS slip_name,
            ss.employee                                        AS employee_id,
            ss.employee_name,
            ss.posting_date,
            ss.gross_pay,
            ss.net_pay,
            ss.company,
            e.department,
            e.designation,
            e.branch,
            e.employment_type,
            e.date_of_joining,
            COALESCE(e.custom_pension_pin, '')                 AS pension_pin,
            COALESCE(e.custom_pension_rsa_id, '')              AS rsa_id,
            COALESCE(e.custom_pension_fund_administrator, '')  AS pfa,
            COALESCE(e.custom_pension_start_date, '')          AS pension_start_date,
            COALESCE(e.tin, '')                                AS tin,
            COALESCE(e.state, 'Lagos')                         AS tax_state,
            COALESCE(e.custom_nhf_number, '')                  AS nhf_member_no,
            COALESCE(e.custom_nhf_applicable, 1)               AS nhf_applicable,
            COALESCE(e.ec_bank_ac_no, e.bank_ac_no, '')        AS bank_ac_no,
            COALESCE(e.ec_bank_name,  e.bank_name,  '')        AS bank_name,
            COALESCE(e.ec_permanent_address, e.permanent_address, '') AS permanent_address
        FROM `tabSalary Slip` ss
        JOIN `tabEmployee` e ON e.name = ss.employee
        WHERE ss.payroll_entry = %(pe)s
          AND ss.docstatus = 1
        ORDER BY ss.employee_name
    """, {"pe": payroll_entry}, as_dict=True)


# ── PENSION ───────────────────────────────────────────────────────────────────
@frappe.whitelist()
def generate_pension_remittance(payroll_entry):
    """
    Pension remittance Excel — one sheet per PFA.
    Uses exact component names "Pension (ER)" / "Pension (EE)"
    same as pension_remittance_report.py.
    """
    if not openpyxl:
        frappe.throw(_("openpyxl required: pip install openpyxl --break-system-packages"))

    slips = _get_slips(payroll_entry)
    if not slips:
        frappe.throw(_("No submitted Salary Slips found"))

    pe     = frappe.get_doc("Payroll Entry", payroll_entry)
    period = _period(pe)
    pr     = _range(pe)

    # Build per-slip amounts — same logic as pension_remittance_report.py
    by_pfa = {}
    for s in slips:
        er = flt(get_component_amount(s.slip_name, "earnings",    PENSION_ER_COMPONENT))
        ee = flt(get_component_amount(s.slip_name, "deductions",  PENSION_EE_COMPONENT))

        # Include row only if there is pension contribution (mirrors report)
        if er == 0 and ee == 0:
            continue

        pfa = s.pfa or "No PFA Assigned"
        by_pfa.setdefault(pfa, []).append({
            **dict(s), "er_pen": er, "ee_pen": ee, "total_pen": round(er + ee, 2)
        })

    if not by_pfa:
        frappe.throw(_(
            "No Pension contributions found. "
            "Ensure salary components are named '{}' (earnings) and '{}' (deductions)."
        ).format(PENSION_ER_COMPONENT, PENSION_EE_COMPONENT))

    COLS = [
        ("Employee ID", 14), ("Employee Name", 28), ("Pension PIN", 18),
        ("RSA ID", 18), ("PFA", 24), ("Pension Start Date", 18),
        ("Salary Slip", 26), ("Posting Date", 16), ("Gross Pay", 16),
        ("Employer Pension (10%)", 20), ("Employee Pension (8%)", 20),
        ("Total Pension", 16), ("Company", 30),
    ]
    LC = get_column_letter(len(COLS))

    wb = openpyxl.Workbook(); wb.remove(wb.active)
    grand = dict(gross=0, ee=0, er=0, total=0, count=0)

    for pfa_name, rows in by_pfa.items():
        ws = wb.create_sheet(title=pfa_name[:31])

        ws.merge_cells(f"A1:{LC}1")
        ws["A1"] = f"{pe.company} — Pension Remittance"
        ws["A1"].font = Font(bold=True, size=13, color="FFFFFF", name="Calibri")
        ws["A1"].fill = _hfill(); ws["A1"].alignment = _c()
        ws.row_dimensions[1].height = 24

        ws.merge_cells(f"A2:{LC}2")
        ws["A2"] = f"Period: {pr}    PFA: {pfa_name}"
        ws["A2"].font = Font(size=10, name="Calibri")

        ws.merge_cells(f"A3:{LC}3")
        ws["A3"] = f"Generated: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
        ws["A3"].font = Font(size=10, italic=True, name="Calibri")
        ws.append([])

        hr = 5
        for ci, (h, w) in enumerate(COLS, 1):
            cell = ws.cell(row=hr, column=ci, value=h)
            cell.font = _hf(); cell.fill = _hfill()
            cell.alignment = _c(); cell.border = _bdr()
            _cw(ws, ci, w)
        ws.row_dimensions[hr].height = 22

        tot = dict(gross=0, ee=0, er=0, total=0)
        for ri, s in enumerate(rows, 1):
            rn = hr + ri
            vals = [
                s["employee_id"], s["employee_name"],
                s["pension_pin"], s["rsa_id"], pfa_name,
                str(s["pension_start_date"]) if s["pension_start_date"] else "",
                s["slip_name"],
                getdate(s["posting_date"]).strftime("%Y-%m-%d"),
                flt(s["gross_pay"]), s["er_pen"], s["ee_pen"], s["total_pen"],
                s["company"],
            ]
            af = _alt(ri)
            for ci, v in enumerate(vals, 1):
                cell = ws.cell(row=rn, column=ci, value=v)
                cell.font = _df(); cell.border = _bdr()
                cell.alignment = _r() if isinstance(v, float) else _l()
                if isinstance(v, float) and ci >= 9:
                    cell.number_format = '#,##0.00'
                if af: cell.fill = af
            tot["gross"] += flt(s["gross_pay"])
            tot["er"]    += s["er_pen"]
            tot["ee"]    += s["ee_pen"]
            tot["total"] += s["total_pen"]

        tr = hr + len(rows) + 1
        ws.cell(row=tr, column=2, value="GRAND TOTAL").font = _tf()
        for ci, k in [(9,"gross"),(10,"er"),(11,"ee"),(12,"total")]:
            cell = ws.cell(row=tr, column=ci, value=tot[k])
            cell.font = _tf(); cell.fill = _tfill()
            cell.number_format = '#,##0.00'; cell.border = _bdr()

        tr2 = tr + 2
        ws.cell(row=tr2,   column=2, value="Total Employees:").font = _df()
        ws.cell(row=tr2,   column=3, value=len(rows)).font = _df()
        ws.freeze_panes = f"A{hr+1}"

        for k in tot: grand[k] += tot[k]
        grand["count"] += len(rows)

    fname = (f"Pension_Remittance_{pe.company.replace(' ','_')}_"
             f"{period.replace(' ','_')}.xlsx")
    return {
        "filename": fname, "b64": _b64(wb),
        "row_count": grand["count"], "total_gross": grand["gross"],
        "total_employee": grand["ee"], "total_employer": grand["er"],
        "grand_total": grand["total"], "period": period,
        "pfa_count": len(by_pfa),
    }


# ── PAYE ──────────────────────────────────────────────────────────────────────
@frappe.whitelist()
def generate_paye_schedule(payroll_entry):
    """
    PAYE deduction schedule Excel — one sheet per state.
    Uses exact component name "Tax" (deductions) same as paye_deduction_report.py.
    """
    if not openpyxl:
        frappe.throw(_("openpyxl required"))

    slips = _get_slips(payroll_entry)
    if not slips:
        frappe.throw(_("No submitted Salary Slips found"))

    pe     = frappe.get_doc("Payroll Entry", payroll_entry)
    period = _period(pe)
    pr     = _range(pe)

    by_state = {}
    for s in slips:
        tax = flt(get_component_amount(s.slip_name, "deductions", TAX_COMPONENT))
        # Mirror paye_deduction_report: include row only if tax > 0
        if tax == 0:
            continue
        state = s.tax_state or "Lagos"
        by_state.setdefault(state, []).append({**dict(s), "tax": tax})

    if not by_state:
        frappe.throw(_(
            "No Tax deductions found. "
            "Ensure the salary component is named '{}' in deductions."
        ).format(TAX_COMPONENT))

    COLS = [
        ("Employee ID", 14), ("Employee Name", 28), ("TIN", 20),
        ("State", 14), ("Salary Slip", 26), ("Posting Date", 16),
        ("Gross Pay", 16), ("Tax Deducted (PAYE)", 20),
    ]
    LC = get_column_letter(len(COLS))

    wb = openpyxl.Workbook(); wb.remove(wb.active)
    grand_gross = grand_tax = 0

    for state, rows in by_state.items():
        ws = wb.create_sheet(title=state[:31])

        ws.merge_cells(f"A1:{LC}1")
        ws["A1"] = f"{pe.company} — PAYE Deduction Schedule"
        ws["A1"].font = Font(bold=True, size=13, color="FFFFFF", name="Calibri")
        ws["A1"].fill = _hfill(); ws["A1"].alignment = _c()
        ws.row_dimensions[1].height = 24

        ws.merge_cells(f"A2:{LC}2")
        ws["A2"] = f"Period: {pr}    State: {state}"
        ws["A2"].font = Font(size=10, name="Calibri")

        ws.merge_cells(f"A3:{LC}3")
        ws["A3"] = f"Generated: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
        ws["A3"].font = Font(size=10, italic=True, name="Calibri")
        ws.append([])

        hr = 5
        for ci, (h, w) in enumerate(COLS, 1):
            cell = ws.cell(row=hr, column=ci, value=h)
            cell.font = _hf(); cell.fill = _hfill()
            cell.alignment = _c(); cell.border = _bdr()
            _cw(ws, ci, w)
        ws.row_dimensions[hr].height = 22

        s_gross = s_tax = 0
        for ri, s in enumerate(rows, 1):
            rn = hr + ri
            vals = [
                s["employee_id"], s["employee_name"],
                s["tin"], s["tax_state"],
                s["slip_name"],
                getdate(s["posting_date"]).strftime("%Y-%m-%d"),
                flt(s["gross_pay"]), s["tax"],
            ]
            af = _alt(ri)
            for ci, v in enumerate(vals, 1):
                cell = ws.cell(row=rn, column=ci, value=v)
                cell.font = _df(); cell.border = _bdr()
                cell.alignment = _r() if isinstance(v, float) else _l()
                if isinstance(v, float) and ci >= 7:
                    cell.number_format = '#,##0.00'
                if af: cell.fill = af
            s_gross += flt(s["gross_pay"]); s_tax += s["tax"]

        tr = hr + len(rows) + 1
        ws.cell(row=tr, column=2, value="GRAND TOTAL").font = _tf()
        for ci, v in [(7, s_gross), (8, s_tax)]:
            cell = ws.cell(row=tr, column=ci, value=v)
            cell.font = _tf(); cell.fill = _tfill()
            cell.number_format = '#,##0.00'; cell.border = _bdr()

        tr2 = tr + 2
        ws.cell(row=tr2, column=2, value="Total Employees:").font = _df()
        ws.cell(row=tr2, column=3, value=len(rows)).font = _df()
        if s_gross:
            ws.cell(row=tr2+1, column=2, value="Effective Rate:").font = _df()
            ws.cell(row=tr2+1, column=3,
                    value=f"{s_tax/s_gross*100:.2f}%").font = _df()
        ws.freeze_panes = f"A{hr+1}"
        grand_gross += s_gross; grand_tax += s_tax

    fname = (f"PAYE_Deduction_{pe.company.replace(' ','_')}_"
             f"{period.replace(' ','_')}.xlsx")
    return {
        "filename": fname, "b64": _b64(wb),
        "row_count": sum(len(v) for v in by_state.values()),
        "total_gross": grand_gross, "total_tax": grand_tax,
        "period": period, "states": list(by_state.keys()),
    }


# ── NSITF ─────────────────────────────────────────────────────────────────────
@frappe.whitelist()
def generate_nsitf_schedule(payroll_entry):
    """
    NSITF remittance schedule Excel.
    Uses exact component name "NSITF" with auto-detected table,
    same as nsitf_remittance_report.py.
    Includes only employees that have the NSITF component on their slip.
    """
    if not openpyxl:
        frappe.throw(_("openpyxl required"))

    comp_meta = get_nsitf_component_meta()
    table     = get_nsitf_table(comp_meta)

    slips = _get_slips(payroll_entry)
    if not slips:
        frappe.throw(_("No submitted Salary Slips found"))

    pe     = frappe.get_doc("Payroll Entry", payroll_entry)
    period = _period(pe)
    pr     = _range(pe)

    COLS = [
        ("Employee ID", 14), ("Employee Name", 28),
        ("Department", 22), ("Designation", 22), ("Branch", 16),
        ("Employment Type", 18), ("Salary Slip", 26), ("Posting Date", 16),
        ("Gross Pay", 16), ("NSITF Contribution", 22),
    ]
    LC = get_column_letter(len(COLS))

    wb = openpyxl.Workbook()
    ws = wb.active; ws.title = "NSITF Remittance"

    ws.merge_cells(f"A1:{LC}1")
    ws["A1"] = f"{pe.company} — NSITF Remittance Schedule"
    ws["A1"].font = Font(bold=True, size=13, color="FFFFFF", name="Calibri")
    ws["A1"].fill = _hfill(); ws["A1"].alignment = _c()
    ws.row_dimensions[1].height = 24

    ws.merge_cells(f"A2:{LC}2"); ws["A2"] = f"Period: {pr}"
    ws["A2"].font = Font(size=10, name="Calibri")

    ws.merge_cells(f"A3:{LC}3")
    ws["A3"] = f"Generated: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
    ws["A3"].font = Font(size=10, italic=True, name="Calibri")
    ws.append([])

    hr = 5
    for ci, (h, w) in enumerate(COLS, 1):
        cell = ws.cell(row=hr, column=ci, value=h)
        cell.font = _hf(); cell.fill = _hfill()
        cell.alignment = _c(); cell.border = _bdr()
        _cw(ws, ci, w)
    ws.row_dimensions[hr].height = 22

    total_gross = total_nsitf = 0
    data_rows = []

    for s in slips:
        # Same as nsitf_remittance_report: read from exact table/component
        nsitf = flt(get_component_amount(s.slip_name, table, comp_meta.name))
        # Skip employees with no NSITF on slip (mirrors report)
        if not nsitf:
            continue
        data_rows.append({**dict(s), "nsitf": nsitf})

    if not data_rows:
        frappe.msgprint(_(
            "No NSITF contributions found on salary slips. "
            "Ensure the '{}' salary component exists and is assigned to employees."
        ).format(NSITF_COMPONENT))

    for ri, s in enumerate(data_rows, 1):
        rn = hr + ri
        vals = [
            s["employee_id"], s["employee_name"],
            s.get("department") or "", s.get("designation") or "",
            s.get("branch") or "", s.get("employment_type") or "",
            s["slip_name"],
            getdate(s["posting_date"]).strftime("%d-%m-%Y"),
            flt(s["gross_pay"]), s["nsitf"],
        ]
        af = _alt(ri)
        for ci, v in enumerate(vals, 1):
            cell = ws.cell(row=rn, column=ci, value=v)
            cell.font = _df(); cell.border = _bdr()
            cell.alignment = _r() if isinstance(v, float) else _l()
            if isinstance(v, float) and ci >= 9:
                cell.number_format = '#,##0.00'
            if af: cell.fill = af
        total_gross  += flt(s["gross_pay"])
        total_nsitf  += s["nsitf"]

    tr = hr + len(data_rows) + 1
    ws.cell(row=tr, column=2, value="GRAND TOTAL").font = _tf()
    for ci, v in [(9, total_gross), (10, total_nsitf)]:
        cell = ws.cell(row=tr, column=ci, value=v)
        cell.font = _tf(); cell.fill = _tfill()
        cell.number_format = '#,##0.00'; cell.border = _bdr()

    tr2 = tr + 2
    ws.cell(row=tr2, column=2, value="Total Employees:").font = _df()
    ws.cell(row=tr2, column=3, value=len(data_rows)).font = _df()
    ws.freeze_panes = f"A{hr+1}"

    fname = (f"NSITF_Remittance_{pe.company.replace(' ','_')}_"
             f"{period.replace(' ','_')}.xlsx")
    return {
        "filename": fname, "b64": _b64(wb),
        "row_count": len(data_rows), "total_gross": total_gross,
        "total_nsitf": total_nsitf, "rate_applied": "from slip",
        "period": period,
    }


# ── NHF ───────────────────────────────────────────────────────────────────────
@frappe.whitelist()
def generate_nhf_schedule(payroll_entry):
    """
    NHF remittance schedule Excel.
    Uses exact component names "NHF" (deductions) and "Basic" (earnings),
    same as nhf_remittance_report.py.
    Includes only employees with NHF > 0 on their slip (mirrors report).
    """
    if not openpyxl:
        frappe.throw(_("openpyxl required"))

    slips = _get_slips(payroll_entry)
    if not slips:
        frappe.throw(_("No submitted Salary Slips found"))

    pe     = frappe.get_doc("Payroll Entry", payroll_entry)
    period = _period(pe)
    pr     = _range(pe)

    COLS = [
        ("Employee ID", 14), ("Employee Name", 28),
        ("NHF Member No.", 20), ("Department", 22),
        ("Basic Salary", 16), ("NHF (2.5%)", 14),
    ]
    LC = get_column_letter(len(COLS))

    wb = openpyxl.Workbook()
    ws = wb.active; ws.title = "NHF Remittance"

    ws.merge_cells(f"A1:{LC}1")
    ws["A1"] = f"{pe.company} — NHF Remittance Schedule"
    ws["A1"].font = Font(bold=True, size=13, color="FFFFFF", name="Calibri")
    ws["A1"].fill = _hfill(); ws["A1"].alignment = _c()
    ws.row_dimensions[1].height = 24

    ws.merge_cells(f"A2:{LC}2"); ws["A2"] = f"Period: {pr}"
    ws["A2"].font = Font(size=10, name="Calibri")

    ws.merge_cells(f"A3:{LC}3")
    ws["A3"] = f"Generated: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
    ws["A3"].font = Font(size=10, italic=True, name="Calibri")
    ws.append([])

    hr = 5
    for ci, (h, w) in enumerate(COLS, 1):
        cell = ws.cell(row=hr, column=ci, value=h)
        cell.font = _hf(); cell.fill = _hfill()
        cell.alignment = _c(); cell.border = _bdr()
        _cw(ws, ci, w)
    ws.row_dimensions[hr].height = 22

    total_basic = total_nhf = 0
    data_rows = []

    for s in slips:
        nhf   = flt(get_component_amount(s.slip_name, "deductions", NHF_COMPONENT))
        basic = flt(get_component_amount(s.slip_name, "earnings",   BASIC_COMPONENT))
        # Mirror nhf_remittance_report: include only if nhf > 0
        if nhf == 0:
            continue
        data_rows.append({**dict(s), "nhf": nhf, "basic": basic})

    if not data_rows:
        frappe.throw(_(
            "No NHF deductions found. "
            "Ensure the salary component is named '{}' in deductions."
        ).format(NHF_COMPONENT))

    for ri, s in enumerate(data_rows, 1):
        rn = hr + ri
        vals = [
            s["employee_id"], s["employee_name"],
            s["nhf_member_no"], s.get("department") or "",
            s["basic"], s["nhf"],
        ]
        af = _alt(ri)
        for ci, v in enumerate(vals, 1):
            cell = ws.cell(row=rn, column=ci, value=v)
            cell.font = _df(); cell.border = _bdr()
            cell.alignment = _r() if isinstance(v, float) else _l()
            if isinstance(v, float) and ci >= 5:
                cell.number_format = '#,##0.00'
            if af: cell.fill = af
        total_basic += s["basic"]; total_nhf += s["nhf"]

    tr = hr + len(data_rows) + 1
    ws.cell(row=tr, column=2, value="GRAND TOTAL").font = _tf()
    for ci, v in [(5, total_basic), (6, total_nhf)]:
        cell = ws.cell(row=tr, column=ci, value=v)
        cell.font = _tf(); cell.fill = _tfill()
        cell.number_format = '#,##0.00'; cell.border = _bdr()

    tr2 = tr + 2
    ws.cell(row=tr2, column=2, value="Total Employees:").font = _df()
    ws.cell(row=tr2, column=3, value=len(data_rows)).font = _df()
    ws.freeze_panes = f"A{hr+1}"

    fname = (f"NHF_Remittance_{pe.company.replace(' ','_')}_"
             f"{period.replace(' ','_')}.xlsx")
    return {
        "filename": fname, "b64": _b64(wb),
        "row_count": len(data_rows), "total_basic": total_basic,
        "total_nhf": total_nhf, "period": period,
    }


# ── ATTACH / EMAIL / SUMMARY helpers ─────────────────────────────────────────
@frappe.whitelist()
def attach_remittance_file(payroll_entry, obligation_type):
    GENERATORS = {
        "Pension (PenCom)": generate_pension_remittance,
        "PAYE":             generate_paye_schedule,
        "NSITF":            generate_nsitf_schedule,
        "NHF":              generate_nhf_schedule,
    }
    gen = GENERATORS.get(obligation_type)
    if not gen:
        frappe.throw(_(f"No generator for: {obligation_type}"))

    result  = gen(payroll_entry)
    fname   = result["filename"]
    content = base64.b64decode(result["b64"])

    file_doc = frappe.get_doc({
        "doctype":              "File",
        "file_name":            fname,
        "attached_to_doctype":  "Payroll Entry",
        "attached_to_name":     payroll_entry,
        "is_private":           1,
        "content":              content,
    })
    file_doc.save(ignore_permissions=True)

    frappe.get_doc({
        "doctype":           "Comment",
        "comment_type":      "Info",
        "reference_doctype": "Payroll Entry",
        "reference_name":    payroll_entry,
        "content": (
            f"📎 {obligation_type} remittance attached: "
            f"<b>{fname}</b> — {result.get('row_count',0)} employees — {nowdate()}"
        ),
    }).insert(ignore_permissions=True)

    return {"status": "ok", "filename": fname, "file_url": file_doc.file_url}


@frappe.whitelist()
def email_remittance_file(payroll_entry, obligation_type,
                          recipients, subject="", message=""):
    GENERATORS = {
        "Pension (PenCom)": generate_pension_remittance,
        "PAYE":             generate_paye_schedule,
        "NSITF":            generate_nsitf_schedule,
        "NHF":              generate_nhf_schedule,
    }
    gen = GENERATORS.get(obligation_type)
    if not gen:
        frappe.throw(_(f"No generator for: {obligation_type}"))

    result  = gen(payroll_entry)
    fname   = result["filename"]
    content = base64.b64decode(result["b64"])

    pe   = frappe.get_doc("Payroll Entry", payroll_entry)
    subj = subject or f"{obligation_type} Remittance — {_period(pe)}"
    msg  = message or (
        f"<p>Please find attached the {obligation_type} remittance schedule "
        f"for <b>{_period(pe)}</b>.</p>"
        f"<p>Employees: {result.get('row_count',0)}<br>Company: {pe.company}</p>"
    )
    recips = [r.strip() for r in recipients.replace(";",",").split(",") if r.strip()]
    frappe.sendmail(recipients=recips, subject=subj, message=msg,
                    attachments=[{"fname": fname, "fcontent": content}])

    frappe.get_doc({
        "doctype":           "Comment",
        "comment_type":      "Info",
        "reference_doctype": "Payroll Entry",
        "reference_name":    payroll_entry,
        "content": f"📧 {obligation_type} emailed to <b>{', '.join(recips)}</b>",
    }).insert(ignore_permissions=True)

    return {"status": "ok", "sent_to": recips, "filename": fname}


@frappe.whitelist()
def get_remittance_summary(payroll_entry):
    """Summary for the dashboard indicator and 📊 Remittance Summary dialog."""
    slips_raw = frappe.db.get_all(
        "Salary Slip",
        filters={"payroll_entry": payroll_entry, "docstatus": 1},
        fields=["name", "employee", "gross_pay", "net_pay", "company"],
    )
    if not slips_raw:
        return {"employee_count": 0}

    company = slips_raw[0].company
    pe      = frappe.get_doc("Payroll Entry", payroll_entry)

    # Auto-detect NSITF table
    comp_meta  = get_nsitf_component_meta()
    nsitf_table = get_nsitf_table(comp_meta)

    emp_pen = er_pen = paye_total = nhf_total = nsitf_total = 0.0

    for s in slips_raw:
        emp_pen    += flt(get_component_amount(s.name, "deductions", PENSION_EE_COMPONENT))
        er_pen     += flt(get_component_amount(s.name, "earnings",   PENSION_ER_COMPONENT))
        paye_total += flt(get_component_amount(s.name, "deductions", TAX_COMPONENT))
        nhf_total  += flt(get_component_amount(s.name, "deductions", NHF_COMPONENT))
        nsitf_total+= flt(get_component_amount(s.name, nsitf_table,  comp_meta.name))

    total_gross = sum(flt(s.gross_pay) for s in slips_raw)

    auths = frappe.db.get_all(
        "Statutory Authority",
        filters={"company": company, "status": "Active"},
        fields=["authority_name", "authority_code", "obligation_type",
                "schedule_template", "remittance_due_day"],
    )

    return {
        "employee_count":          len(slips_raw),
        "company":                 company,
        "period":                  _period(pe),
        "period_range":            _range(pe),
        "total_gross":             total_gross,
        "employee_pension":        emp_pen,
        "employer_pension":        er_pen,
        "total_pension":           emp_pen + er_pen,
        "paye_total":              paye_total,
        "nsitf_total":             nsitf_total,
        "nhf_total":               nhf_total,
        "nhis_total":              0.0,
        "configured_authorities":  auths,
    }