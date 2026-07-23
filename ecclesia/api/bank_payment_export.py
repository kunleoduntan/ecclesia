# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/api/bank_payment_export.py
"""
Bank Payment Export Engine
══════════════════════════
Generates bank payment files from ERPNext Payroll Entry or Payments DocType
in multiple formats used globally.

Supported formats:
  · zenith_iso20022   — Zenith Bank Nigeria (ISO 20022 pain.001 CSV, semicolon)
  · gtb_csv           — GTBank Nigeria (pipe-delimited CSV)
  · access_csv        — Access Bank Nigeria
  · uba_csv           — UBA Nigeria
  · firstbank_csv     — First Bank Nigeria
  · sepa_xml          — SEPA Credit Transfer (EU banks, pain.001.001.03 XML)
  · bacs_csv          — BACS Direct Credit (UK)
  · ach_nacha         — ACH/NACHA (USA)
  · swift_mt103       — SWIFT MT103 (international wires)

Whitelisted methods:
  generate_payroll_payment_file(payroll_entry, bank_format)
  generate_batch_payment_file(payment_batch, bank_format)
  get_supported_formats()
  preview_payment_file(payroll_entry, bank_format)
"""

import frappe
from frappe import _
from frappe.utils import flt, nowdate, getdate, formatdate
import csv
import io
import base64
from datetime import datetime


# ══════════════════════════════════════════════════════════════════════════════
#  FORMAT REGISTRY
# ══════════════════════════════════════════════════════════════════════════════

FORMATS = {
    "zenith_iso20022": {
        "label":       "Zenith Bank Nigeria — ISO 20022 pain.001 CSV",
        "delimiter":   ";",
        "extension":   "csv",
        "country":     "NG",
        "description": "138-column semicolon-delimited ISO 20022 Credit Transfer format",
    },
    "gtb_csv": {
        "label":       "GTBank Nigeria — CSV",
        "delimiter":   ",",
        "extension":   "csv",
        "country":     "NG",
        "description": "GTBank Nigeria salary batch upload format",
    },
    "access_csv": {
        "label":       "Access Bank Nigeria — CSV",
        "delimiter":   ",",
        "extension":   "csv",
        "country":     "NG",
        "description": "Access Bank Nigeria salary payment format",
    },
    "uba_csv": {
        "label":       "UBA Nigeria — CSV",
        "delimiter":   ",",
        "extension":   "csv",
        "country":     "NG",
        "description": "UBA Nigeria bulk salary transfer format",
    },
    "firstbank_csv": {
        "label":       "First Bank Nigeria — CSV",
        "delimiter":   ",",
        "extension":   "csv",
        "country":     "NG",
        "description": "First Bank Nigeria bulk payment format",
    },
    "sepa_xml": {
        "label":       "SEPA Credit Transfer — XML (EU)",
        "delimiter":   None,
        "extension":   "xml",
        "country":     "EU",
        "description": "pain.001.001.03 SEPA Credit Transfer XML",
    },
    "bacs_csv": {
        "label":       "BACS Direct Credit — UK",
        "delimiter":   ",",
        "extension":   "csv",
        "country":     "GB",
        "description": "UK BACS Direct Credit standard format",
    },
    "ach_nacha": {
        "label":       "ACH/NACHA — USA",
        "delimiter":   None,
        "extension":   "txt",
        "country":     "US",
        "description": "US ACH NACHA fixed-width format",
    },
    "swift_mt103": {
        "label":       "SWIFT MT103 — International",
        "delimiter":   None,
        "extension":   "txt",
        "country":     "INT",
        "description": "SWIFT MT103 single customer credit transfer",
    },
}


@frappe.whitelist()
def get_supported_formats():
    """Return all supported bank payment formats."""
    return [{"key": k, **v} for k, v in FORMATS.items()]


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN ENTRY POINTS
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def generate_payroll_payment_file(payroll_entry, bank_format="zenith_iso20022"):
    """
    Generate a bank payment file from a submitted Payroll Entry.
    Returns base64-encoded file content + filename.
    """
    if bank_format not in FORMATS:
        frappe.throw(_(f"Unsupported format: {bank_format}. Use get_supported_formats() to list options."))

    pe = frappe.get_doc("Payroll Entry", payroll_entry)
    if pe.docstatus != 1:
        frappe.throw(_("Payroll Entry must be submitted before generating payment file."))

    # Get all salary slips for this payroll entry
    slips = frappe.db.get_all(
        "Salary Slip",
        filters={"payroll_entry": payroll_entry, "docstatus": 1},
        fields=["name", "employee", "employee_name", "net_pay",
                "bank_account_no", "bank_name", "company", "posting_date",
                "start_date", "end_date"]
    )

    if not slips:
        frappe.throw(_("No submitted Salary Slips found for this Payroll Entry."))

    # Enrich with employee bank details
    payments = _enrich_payroll_payments(slips, pe)

    # Generate file
    content, filename = _generate_file(payments, bank_format, pe.company,
                                        pe.payment_account, pe.posting_date,
                                        f"PAYROLL {_month_label(pe.posting_date)}")

    return {
        "success":    True,
        "file_data":  base64.b64encode(content.encode("utf-8") if isinstance(content, str) else content).decode(),
        "file_name":  filename,
        "format":     FORMATS[bank_format]["label"],
        "row_count":  len(payments),
        "total_amount": sum(p["amount"] for p in payments),
    }


@frappe.whitelist()
def generate_batch_payment_file(payment_batch, bank_format="zenith_iso20022"):
    """
    Generate a bank payment file from a Batch Bank Transaction.
    Returns base64-encoded file content + filename.
    """
    if bank_format not in FORMATS:
        frappe.throw(_(f"Unsupported format: {bank_format}"))

    batch = frappe.get_doc("Batch Bank Transaction", payment_batch)
    if batch.docstatus != 1:
        frappe.throw(_("Batch Bank Transaction must be submitted."))

    payments = _enrich_batch_payments(batch)
    content, filename = _generate_file(payments, bank_format, batch.company,
                                        batch.company_bank_account, batch.transaction_date,
                                        f"PAYMENT BATCH {batch.name}")

    return {
        "success":    True,
        "file_data":  base64.b64encode(content.encode("utf-8") if isinstance(content, str) else content).decode(),
        "file_name":  filename,
        "format":     FORMATS[bank_format]["label"],
        "row_count":  len(payments),
        "total_amount": sum(p["amount"] for p in payments),
    }


@frappe.whitelist()
def preview_payment_file(payroll_entry, bank_format="zenith_iso20022"):
    """Return first 3 rows as preview (for JS display before download)."""
    result = generate_payroll_payment_file(payroll_entry, bank_format)
    content = base64.b64decode(result["file_data"]).decode("utf-8", errors="replace")
    lines   = content.splitlines()
    preview = "\n".join(lines[:4])  # header + 3 rows
    return {**result, "preview": preview, "total_lines": len(lines)}


# ══════════════════════════════════════════════════════════════════════════════
#  DATA ENRICHMENT
# ══════════════════════════════════════════════════════════════════════════════

def _enrich_payroll_payments(slips, payroll_entry, gateway_name=None):
    """Build standardised payment list from salary slips."""
    payments  = []
    company   = frappe.get_doc("Company", slips[0].company)
    comp_name = company.name

    # Resolve gateway for this company if not supplied
    if not gateway_name:
        gws = frappe.db.get_all(
            "Payment Gateway Settings",
            filters={"company": comp_name, "enabled": 1},
            fields=["name"],
            order_by="is_default desc",
            limit=1
        )
        gateway_name = gws[0].name if gws else None

    # Debtor (company) fields — resolved once for all rows
    debt_addr   = _get_company_address(company, gateway_name)
    debt_acc_no = _clean_acc(payroll_entry.payment_account, comp_name, gateway_name)
    debt_bic    = _get_bank_bic_from_account(
                      payroll_entry.payment_account, comp_name, gateway_name)
    narration   = f"PAYROLL {_month_label(payroll_entry.posting_date)}"

    for slip in slips:
        emp = frappe.get_doc("Employee", slip.employee)

        # ── Employee bank account number ──────────────────────────────────
        bank_ac_no  = ""
        bank_name   = ""

        # 1. Employee master main fields
        emp_bank = frappe.db.get_value(
            "Employee", slip.employee, ["bank_ac_no", "bank_name"], as_dict=True
        ) or {}
        bank_ac_no = emp_bank.get("bank_ac_no") or ""
        bank_name  = emp_bank.get("bank_name")  or ""

        # 2. Employee Bank Account child table (primary)
        if not bank_ac_no:
            acc_docs = frappe.db.get_all(
                "Employee Bank Account",
                filters={"parent": slip.employee, "is_primary_account": 1},
                fields=["account_no", "bank"],
                limit=1
            )
            if not acc_docs:
                acc_docs = frappe.db.get_all(
                    "Employee Bank Account",
                    filters={"parent": slip.employee},
                    fields=["account_no", "bank"],
                    limit=1
                )
            if acc_docs:
                bank_ac_no = acc_docs[0].account_no or ""
                bank_name  = acc_docs[0].bank       or bank_name

        # 3. ERPNext Bank Account linked to Employee
        if not bank_ac_no:
            ba = frappe.db.get_all(
                "Bank Account",
                filters={"party_type": "Employee", "party": slip.employee},
                fields=["bank_account_no", "bank"],
                order_by="is_default desc",
                limit=1
            )
            if ba:
                bank_ac_no = ba[0].bank_account_no or ""
                bank_name  = ba[0].bank            or bank_name

        # ── Employee BIC ──────────────────────────────────────────────────
        cred_bic = _get_bank_bic(bank_name)
        if not cred_bic and bank_name:
            swift = frappe.db.get_value("Bank", bank_name, "swift_number")
            if swift:
                cred_bic = str(swift)

        # ── Employee address (CRED_ADDRESS_COUNTRYSUBDIVISION) ───────────
        emp_address = (
            getattr(emp, "permanent_address", "") or
            getattr(emp, "current_address",   "") or
            getattr(emp, "residential_address","") or ""
        )
        # Clean to single line, max 70 chars for ISO 20022
        emp_address = " ".join(emp_address.split())[:70].upper()

        cred_city = (
            getattr(emp, "city", "")     or
            getattr(emp, "town", "")     or
            "LAGOS"
        )

        payments.append({
            # Debtor (company)
            "debt_name":     company.company_name.upper(),
            "debt_address":  debt_addr,
            "debt_country":  "NG",
            "debt_bic":      debt_bic,
            "debt_acc_no":   debt_acc_no,
            "debt_acc_type": "DOMESTIC",
            "debt_acc_bic":  debt_bic,

            # Creditor (employee)
            "cred_name":         emp.employee_name.upper(),
            "cred_city":         cred_city.upper(),
            "cred_country":      "NG",
            "cred_district":     emp_address,
            "cred_acc_no":       bank_ac_no,
            "cred_acc_type":     "DOMESTIC",
            "cred_acc_country":  "NG",
            "cred_acc_bic":      cred_bic,
            "cred_bank_name":    bank_name,

            # Transaction
            "amount":         flt(slip.net_pay),
            "currency":       "NGN",
            "execution_date": str(getdate(payroll_entry.posting_date)).replace("-", "/"),
            "details":        narration,
            "reference":      slip.name,
            "employee_id":    slip.employee,
        })

    return payments


def _enrich_batch_payments(batch):
    """
    Build standardised payment list from a Batch Bank Transaction.

    Field mapping (actual BBT/Transaction Entry field names):
      batch.bank_account         → debit bank account link (Bank Account DocType)
      batch.bank_gl              → debit GL account name (fallback for acc no)
      batch.bank_account_currency→ currency
      batch.batch_date           → execution date
      batch.transaction_entry    → child table rows
      row.party_name             → creditor name
      row.payee_account_no       → creditor NUBAN account number
      row.payee_bank_name        → creditor bank name for BIC lookup
      row.remark                 → narration
      row.amount                 → payment amount
    """
    payments  = []
    comp_name = batch.company
    company   = frappe.get_doc("Company", comp_name)

    # Resolve gateway for address and BIC lookup
    gws = frappe.db.get_all(
        "Payment Gateway Settings",
        filters={"company": comp_name, "enabled": 1},
        fields=["name"],
        order_by="is_default desc",
        limit=1
    )
    gateway_name = gws[0].name if gws else None

    # Debtor fields — resolved once
    debt_addr   = _get_company_address(company, gateway_name)
    debt_acc_no = _clean_acc(batch.bank_account, comp_name, gateway_name) or                   _clean_acc(getattr(batch, "bank_gl", ""), comp_name, gateway_name)
    debt_bic    = _get_bank_bic_from_account(batch.bank_account, comp_name, gateway_name)
    currency    = getattr(batch, "bank_account_currency", None) or "NGN"
    exec_dt     = str(getdate(batch.batch_date)).replace("-", "/")

    for row in batch.transaction_entry:
        cred_acc_no = getattr(row, "payee_account_no", "") or ""
        cred_bank   = getattr(row, "payee_bank_name",  "") or ""
        cred_name   = (getattr(row, "party_name", "") or
                       getattr(row, "payee_name",  "") or "")

        # BIC: name-based lookup first, then Bank.swift_number
        cred_bic = _get_bank_bic(cred_bank)
        if not cred_bic and cred_bank:
            swift = frappe.db.get_value("Bank", cred_bank, "swift_number")
            if swift:
                cred_bic = str(swift)

        narration = (getattr(row, "remark", "") or
                     getattr(row, "transaction_description", "") or
                     batch.name)

        payments.append({
            "debt_name":         company.company_name.upper(),
            "debt_address":      debt_addr,
            "debt_country":      "NG",
            "debt_bic":          debt_bic,
            "debt_acc_no":       debt_acc_no,
            "debt_acc_type":     "DOMESTIC",
            "debt_acc_bic":      debt_bic,
            "cred_name":         cred_name.upper() if cred_name else "",
            "cred_city":         "LAGOS",
            "cred_country":      "NG",
            "cred_district":     "",
            "cred_acc_no":       cred_acc_no,
            "cred_acc_type":     "DOMESTIC",
            "cred_acc_country":  "NG",
            "cred_acc_bic":      cred_bic,
            "cred_bank_name":    cred_bank,
            "amount":            flt(row.amount),
            "currency":          currency,
            "execution_date":    exec_dt,
            "details":           narration.upper()[:35],
            "reference":         row.name,
        })
    return payments


# ══════════════════════════════════════════════════════════════════════════════
#  FORMAT GENERATORS
# ══════════════════════════════════════════════════════════════════════════════

def _generate_file(payments, bank_format, company, debit_account, payment_date, narration):
    """Route to the correct format generator."""
    fn_map = {
        "zenith_iso20022": _fmt_zenith_iso20022,
        "gtb_csv":         _fmt_gtb,
        "access_csv":      _fmt_access,
        "uba_csv":         _fmt_uba,
        "firstbank_csv":   _fmt_firstbank,
        "sepa_xml":        _fmt_sepa_xml,
        "bacs_csv":        _fmt_bacs,
        "ach_nacha":       _fmt_ach_nacha,
        "swift_mt103":     _fmt_swift_mt103,
    }
    ext      = FORMATS[bank_format]["extension"]
    date_str = str(getdate(payment_date)).replace("-","")
    filename = f"BankPayment_{bank_format}_{company}_{date_str}.{ext}"
    filename = filename.replace(" ", "_").replace("/", "_")

    content = fn_map[bank_format](payments, company, debit_account, payment_date, narration)
    return content, filename


# ── Zenith Bank Nigeria — ISO 20022 pain.001 CSV ─────────────────────────────

# All 138 column headers — exact match to NG11NGNSalaryUploadJune26v3.csv
# Col 39 DEBT_RESIDENCE_COUNTRY added (was missing in previous version)
_ZENITH_HEADERS = [
    "PMT_MTD","BATCH_BOOKING","BATCH_END_TO_END_ID","ULTDEBT_NAME","ULTDEBT_ADDRESS",
    "ULTDEBT_ADDRESS_DEPARTMENT","ULTDEBT_ADDRESS_SUBDEPARTMENT","ULTDEBT_ADDRESS_BUILDINGNUMBER",
    "ULTDEBT_ADDRESS_STREETNAME","ULTDEBT_ADDRESS_BUILDINGNAME","ULTDEBT_ADDRESS_FLOOR",
    "ULTDEBT_ADDRESS_ROOM","ULTDEBT_ADDRESS_POSTBOX","ULTDEBT_ADDRESS_TOWNLOCATIONNAME",
    "ULTDEBT_ADDRESS_POSTCODE","ULTDEBT_ADDRESS_TOWNNAME","ULTDEBT_ADDRESS_DISTRICTNAME",
    "ULTDEBT_ADDRESS_COUNTRY","ULTDEBT_ADDRESS_COUNTRYSUBDIVISION","ULTDEBT_RESIDENCE_COUNTRY",
    "ULTDEBT_BIC","ULTDEBT_NATIONAL_ID","DEBT_NAME","DEBT_ADDRESS","DEBT_ADDRESS_DEPARTMENT",
    "DEBT_ADDRESS_SUBDEPARTMENT","DEBT_ADDRESS_BUILDINGNUMBER","DEBT_ADDRESS_STREETNAME",
    "DEBT_ADDRESS_BUILDINGNAME","DEBT_ADDRESS_FLOOR","DEBT_ADDRESS_ROOM","DEBT_ADDRESS_POSTBOX",
    "DEBT_ADDRESS_TOWNLOCATIONNAME","DEBT_ADDRESS_POSTCODE","DEBT_ADDRESS_TOWNNAME",
    "DEBT_ADDRESS_DISTRICTNAME","DEBT_ADDRESS_COUNTRY","DEBT_ADDRESS_COUNTRYSUBDIVISION",
    "DEBT_RESIDENCE_COUNTRY",                                    # col 39 — was missing
    "DEBT_BIC_CODE","DEBT_NATIONAL_ID","DEBTACC_CURRENCY","DEBTACC_NUMBER","DEBTACC_TYPE",
    "DEBTACC_COUNTRY","DEBTACC_BIC","DEBTACC_NCC","DEBTACC_NCC_TYPE","DEBTACC_BANK_NAME",
    "DEBTACC_ADDRESS","DEBTACC_ADDRESS_DEPARTMENT","DEBTACC_ADDRESS_SUBDEPARTMENT",
    "DEBTACC_ADDRESS_BUILDINGNUMBER","DEBTACC_ADDRESS_STREETNAME","DEBTACC_ADDRESS_BUILDINGNAME",
    "DEBTACC_ADDRESS_FLOOR","DEBTACC_ADDRESS_ROOM","DEBTACC_ADDRESS_POSTBOX",
    "DEBTACC_ADDRESS_TOWNLOCATIONNAME","DEBTACC_ADDRESS_POSTCODE","DEBTACC_ADDRESS_TOWNNAME",
    "DEBTACC_ADDRESS_DISTRICTNAME","DEBTACC_ADDRESS_COUNTRY","DEBTACC_ADDRESS_COUNTRYSUBDIVISION",
    "INTERAGENT_NAME","INTERAGENT_ADDRESS","INTERAGENT_COUNTRY","INTERAGENT_BIC_CODE",
    "INTERAGENT_NCC","INTERAGENT_NCC_TYPE","INTERAGENT_CURRENCY","INTERAGENT_NUMBER",
    "INTERAGENT_TYPE","INTERAGENT2_NAME","INTERAGENT2_ADDRESS","INTERAGENT2_COUNTRY",
    "INTERAGENT2_BIC_CODE","INTERAGENT2_NCC","INTERAGENT2_NCC_TYPE","INTERAGENT2_CURRENCY",
    "INTERAGENT2_NUMBER","INTERAGENT2_TYPE","CRED_NAME","CRED_ADDRESS","CRED_ADDRESS_DEPARTMENT",
    "CRED_ADDRESS_SUBDEPARTMENT","CRED_ADDRESS_BUILDINGNUMBER","CRED_ADDRESS_STREETNAME",
    "CRED_ADDRESS_BUILDINGNAME","CRED_ADDRESS_FLOOR","CRED_ADDRESS_ROOM","CRED_ADDRESS_POSTBOX",
    "CRED_ADDRESS_TOWNLOCATIONNAME","CRED_ADDRESS_POSTCODE","CRED_ADDRESS_TOWNNAME",
    "CRED_ADDRESS_DISTRICTNAME","CRED_ADDRESS_COUNTRY","CRED_ADDRESS_COUNTRYSUBDIVISION",
    "CRED_RESIDENCE_COUNTRY","CRED_BIC_CODE","CRED_NATIONAL_ID","CREDACC_CURRENCY",
    "CREDACC_NUMBER","CREDACC_TYPE","CREDACC_COUNTRY","CREDACC_BIC","CREDACC_NCC",
    "CREDACC_NCC_TYPE","CREDACC_BANK_NAME","CREDACC_ADDRESS","CREDACC_ADDRESS_DEPARTMENT",
    "CREDACC_ADDRESS_SUBDEPARTMENT","CREDACC_ADDRESS_BUILDINGNUMBER","CREDACC_ADDRESS_STREETNAME",
    "CREDACC_ADDRESS_BUILDINGNAME","CREDACC_ADDRESS_FLOOR","CREDACC_ADDRESS_ROOM",
    "CREDACC_ADDRESS_POSTBOX","CREDACC_ADDRESS_TOWNLOCATIONNAME","CREDACC_ADDRESS_POSTCODE",
    "CREDACC_ADDRESS_TOWNNAME","CREDACC_ADDRESS_DISTRICTNAME","CREDACC_ADDRESS_COUNTRY",
    "CREDACC_ADDRESS_COUNTRYSUBDIVISION","OPE_EXECUTION_DATE","OPE_PAYMENT_AMOUNT",
    "OPE_PAYMENT_CURRENCY","OPE_PAYMENT_CURRENCY_QUALIFIER","OPE_END_TO_END_ID",
    "OPE_INSTR_ID","OPE_INST_PRIORITY","OPE_DETAILS","OPE_PURPOSE_CODE","OPE_PURP_PRTRY",
    "OPE_REGULATORY_REPORTING_CODE","OPE_REGULATORY_REPORTING_INFO","OPE_FEES_RESPONSABILITY",
    "CREDACC_TP_PRTRY",
]


def _fmt_zenith_iso20022(payments, company, debit_account, payment_date, narration):
    """
    Zenith Bank Nigeria ISO 20022 pain.001 semicolon CSV.
    138 columns — only 25 are populated, rest remain empty.
    Exactly matches the format in NG11NGNSalaryUploadJune26v2.csv.
    """
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_ZENITH_HEADERS,
                            delimiter=";", extrasaction="ignore",
                            lineterminator="\r\n")
    writer.writeheader()

    for p in payments:
        addr = p.get("debt_address") or {}
        row = {k: "" for k in _ZENITH_HEADERS}
        row.update({
            # Batch
            "PMT_MTD":                         "CT",
            "BATCH_BOOKING":                   "TRUE",

            # Debtor (company)
            "DEBT_NAME":                       p["debt_name"],
            "DEBT_ADDRESS_BUILDINGNUMBER":     addr.get("building_number", ""),
            "DEBT_ADDRESS_STREETNAME":         addr.get("street", ""),
            "DEBT_ADDRESS_BUILDINGNAME":       addr.get("building_name", ""),
            "DEBT_ADDRESS_TOWNNAME":           addr.get("city", "LAGOS"),
            "DEBT_RESIDENCE_COUNTRY":          "NG",
            "DEBTACC_NUMBER":                  p["debt_acc_no"],
            "DEBTACC_TYPE":                    "DOMESTIC",
            "DEBTACC_COUNTRY":                 "NG",
            "DEBTACC_BIC":                     p["debt_bic"],

            # Creditor (employee / beneficiary)
            "CRED_NAME":                       p["cred_name"],
            "CRED_ADDRESS_TOWNNAME":           p["cred_city"],
            "CRED_ADDRESS_COUNTRY":            p["cred_country"],
            "CRED_ADDRESS_COUNTRYSUBDIVISION": p.get("cred_district", ""),
            "CRED_RESIDENCE_COUNTRY":          p["cred_country"],
            "CREDACC_NUMBER":                  p["cred_acc_no"],
            "CREDACC_TYPE":                    "DOMESTIC",
            "CREDACC_COUNTRY":                 "NG",
            "CREDACC_BIC":                     p["cred_acc_bic"],

            # Operation
            "OPE_EXECUTION_DATE":              p["execution_date"],
            "OPE_PAYMENT_AMOUNT":              f"{flt(p['amount']):.2f}",
            "OPE_PAYMENT_CURRENCY":            p["currency"],
            "OPE_DETAILS":                     p["details"],
        })
        writer.writerow(row)

    return buf.getvalue()


# ── GTBank Nigeria ─────────────────────────────────────────────────────────────

_GTB_HEADERS = [
    "Beneficiary Name", "Beneficiary Account Number", "Bank Name",
    "Amount", "Narration", "Reference"
]

def _fmt_gtb(payments, company, debit_account, payment_date, narration):
    """GTBank Nigeria bulk salary CSV."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_GTB_HEADERS,
                            delimiter=",", lineterminator="\r\n")
    writer.writeheader()
    for p in payments:
        writer.writerow({
            "Beneficiary Name":           p["cred_name"],
            "Beneficiary Account Number": p["cred_acc_no"],
            "Bank Name":                  p["cred_bank_name"],
            "Amount":                     f"{flt(p['amount']):.2f}",
            "Narration":                  p["details"],
            "Reference":                  p.get("reference", ""),
        })
    return buf.getvalue()


# ── Access Bank Nigeria ───────────────────────────────────────────────────────

_ACCESS_HEADERS = [
    "AccountName", "AccountNumber", "BankCode", "Amount", "CurrencyCode",
    "Narration", "Reference", "PaymentDate"
]

def _fmt_access(payments, company, debit_account, payment_date, narration):
    """Access Bank Nigeria bulk salary CSV."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_ACCESS_HEADERS,
                            delimiter=",", lineterminator="\r\n")
    writer.writeheader()
    for p in payments:
        writer.writerow({
            "AccountName":   p["cred_name"],
            "AccountNumber": p["cred_acc_no"],
            "BankCode":      _bic_to_sort_code(p["cred_acc_bic"]),
            "Amount":        f"{flt(p['amount']):.2f}",
            "CurrencyCode":  p["currency"],
            "Narration":     p["details"],
            "Reference":     p.get("reference", ""),
            "PaymentDate":   p["execution_date"],
        })
    return buf.getvalue()


# ── UBA Nigeria ───────────────────────────────────────────────────────────────

_UBA_HEADERS = [
    "S/N", "Employee Name", "Account Number", "Bank Code",
    "Net Pay", "Payment Description"
]

def _fmt_uba(payments, company, debit_account, payment_date, narration):
    """UBA Nigeria bulk transfer CSV."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_UBA_HEADERS,
                            delimiter=",", lineterminator="\r\n")
    writer.writeheader()
    for i, p in enumerate(payments, 1):
        writer.writerow({
            "S/N":                  i,
            "Employee Name":        p["cred_name"],
            "Account Number":       p["cred_acc_no"],
            "Bank Code":            _bic_to_sort_code(p["cred_acc_bic"]),
            "Net Pay":              f"{flt(p['amount']):.2f}",
            "Payment Description":  p["details"],
        })
    return buf.getvalue()


# ── First Bank Nigeria ────────────────────────────────────────────────────────

_FBN_HEADERS = [
    "RECORD_TYPE", "BENEFICIARY_ACCOUNT", "AMOUNT", "BENEFICIARY_NAME",
    "NARRATION", "BANK_CODE", "CURRENCY"
]

def _fmt_firstbank(payments, company, debit_account, payment_date, narration):
    """First Bank Nigeria bulk payment CSV."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_FBN_HEADERS,
                            delimiter=",", lineterminator="\r\n")
    writer.writeheader()
    for p in payments:
        writer.writerow({
            "RECORD_TYPE":         "SALARY",
            "BENEFICIARY_ACCOUNT": p["cred_acc_no"],
            "AMOUNT":              f"{flt(p['amount']):.2f}",
            "BENEFICIARY_NAME":    p["cred_name"],
            "NARRATION":           p["details"],
            "BANK_CODE":           _bic_to_sort_code(p["cred_acc_bic"]),
            "CURRENCY":            p["currency"],
        })
    return buf.getvalue()


# ── SEPA Credit Transfer — EU banks ─────────────────────────────────────────

def _fmt_sepa_xml(payments, company, debit_account, payment_date, narration):
    """
    SEPA pain.001.001.03 Credit Transfer XML.
    Used by all EU banks (HSBC, Deutsche Bank, BNP, Société Générale, etc.)
    """
    now      = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    exec_dt  = str(getdate(payment_date))
    total    = sum(flt(p["amount"]) for p in payments)
    msg_id   = f"MSG{datetime.now().strftime('%Y%m%d%H%M%S')}"
    pmtinf   = f"PMT{datetime.now().strftime('%Y%m%d')}"
    ccy      = payments[0]["currency"] if payments else "EUR"

    txns = ""
    for p in payments:
        end_to_end = f"ETE{p.get('reference','').replace(' ','')[-30:]}"
        txns += f"""
        <CdtTrfTxInf>
          <PmtId>
            <EndToEndId>{end_to_end}</EndToEndId>
          </PmtId>
          <Amt>
            <InstdAmt Ccy="{ccy}">{flt(p['amount']):.2f}</InstdAmt>
          </Amt>
          <CdtrAgt>
            <FinInstnId>
              <BIC>{p['cred_acc_bic']}</BIC>
            </FinInstnId>
          </CdtrAgt>
          <Cdtr>
            <Nm>{p['cred_name']}</Nm>
          </Cdtr>
          <CdtrAcct>
            <Id>
              <IBAN>{p['cred_acc_no']}</IBAN>
            </Id>
          </CdtrAcct>
          <RmtInf>
            <Ustrd>{p['details']}</Ustrd>
          </RmtInf>
        </CdtTrfTxInf>"""

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.03">
  <CstmrCdtTrfInitn>
    <GrpHdr>
      <MsgId>{msg_id}</MsgId>
      <CreDtTm>{now}</CreDtTm>
      <NbOfTxs>{len(payments)}</NbOfTxs>
      <CtrlSum>{total:.2f}</CtrlSum>
      <InitgPty>
        <Nm>{payments[0]['debt_name'] if payments else company}</Nm>
      </InitgPty>
    </GrpHdr>
    <PmtInf>
      <PmtInfId>{pmtinf}</PmtInfId>
      <PmtMtd>TRF</PmtMtd>
      <NbOfTxs>{len(payments)}</NbOfTxs>
      <CtrlSum>{total:.2f}</CtrlSum>
      <PmtTpInf>
        <SvcLvl>
          <Cd>SEPA</Cd>
        </SvcLvl>
      </PmtTpInf>
      <ReqdExctnDt>{exec_dt}</ReqdExctnDt>
      <Dbtr>
        <Nm>{payments[0]['debt_name'] if payments else company}</Nm>
      </Dbtr>
      <DbtrAcct>
        <Id>
          <IBAN>{_clean_acc(debit_account)}</IBAN>
        </Id>
      </DbtrAcct>
      <DbtrAgt>
        <FinInstnId>
          <BIC>{payments[0]['debt_bic'] if payments else ''}</BIC>
        </FinInstnId>
      </DbtrAgt>
      {txns}
    </PmtInf>
  </CstmrCdtTrfInitn>
</Document>"""
    return xml


# ── BACS Direct Credit — UK ───────────────────────────────────────────────────

_BACS_HEADERS = [
    "Destination Sort Code", "Account Number", "Account Type",
    "Amount (pence)", "Originator Name", "Reference", "Transaction Code"
]

def _fmt_bacs(payments, company, debit_account, payment_date, narration):
    """
    UK BACS Direct Credit standard format.
    Amount in pence (multiply by 100). Transaction code 99 = Direct Credit.
    """
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_BACS_HEADERS,
                            delimiter=",", lineterminator="\r\n")
    writer.writeheader()
    for p in payments:
        sort_code = _bic_to_sort_code(p["cred_acc_bic"]).replace("-", "")
        amount_p  = int(flt(p["amount"]) * 100)
        writer.writerow({
            "Destination Sort Code": sort_code[:6],
            "Account Number":        p["cred_acc_no"][:8],
            "Account Type":          "0",
            "Amount (pence)":        amount_p,
            "Originator Name":       p["cred_name"][:18],
            "Reference":             p["details"][:18],
            "Transaction Code":      "99",
        })
    return buf.getvalue()


# ── ACH / NACHA — USA ────────────────────────────────────────────────────────

def _fmt_ach_nacha(payments, company, debit_account, payment_date, narration):
    """
    US ACH NACHA fixed-width format.
    File Header (1) + Batch Header (5) + Detail records (6) +
    Batch Control (8) + File Control (9).
    """
    today     = getdate(payment_date)
    date_str  = today.strftime("%y%m%d")
    time_str  = datetime.now().strftime("%H%M")
    company_n = (company + " " * 16)[:16]
    origin    = "1000000000"   # Placeholder originator routing
    dest      = "0210000089"   # Placeholder destination (Wells Fargo test)
    seq       = "0001"

    total_debit   = sum(int(flt(p["amount"]) * 100) for p in payments)
    entry_count   = len(payments)
    entry_hash    = sum(int(p.get("cred_acc_bic", "0")[:9] or 0) for p in payments) % 10_000_000_000

    lines = []
    # File Header
    lines.append(f"101 {dest:<10}{origin:<10}{date_str}{time_str}A094101{company_n[:23]:<23}{'BANK':<23}  ")
    # Batch Header
    co_entry_desc = (narration + " " * 10)[:10]
    lines.append(f"5200{company_n:<16}{'':10}PPD{co_entry_desc}{date_str}   1{dest[:8]:<8}0{seq}")

    for i, p in enumerate(payments, 1):
        routing   = (p.get("cred_acc_bic", "")[:9] + "000000000")[:9]
        acc_no    = (p["cred_acc_no"] + " " * 17)[:17]
        amount_c  = int(flt(p["amount"]) * 100)
        name      = (p["cred_name"] + " " * 22)[:22]
        trace     = f"{dest[:8]}{i:07d}"
        lines.append(f"622{routing}{acc_no}{amount_c:010d}{name}  0{trace}")

    # Batch Control
    lines.append(f"820000{entry_count:06d}{entry_hash:010d}{0:012d}{total_debit:012d}{company_n:<23}{'':39}{dest[:8]:<8}0{seq}")
    # File Control
    block_count = ((len(lines) + 1) // 10) + 1
    lines.append(f"9000001{block_count:06d}{entry_count:08d}{entry_hash:010d}{0:012d}{total_debit:012d}{'':39}")

    # Pad to multiple of 10 lines
    while len(lines) % 10 != 0:
        lines.append("9" * 94)

    return "\r\n".join(lines)


# ── SWIFT MT103 — International ──────────────────────────────────────────────

def _fmt_swift_mt103(payments, company, debit_account, payment_date, narration):
    """
    SWIFT MT103 Single Customer Credit Transfer.
    One message block per payment. Used for international wires.
    """
    today    = getdate(payment_date).strftime("%y%m%d")
    blocks   = []

    for i, p in enumerate(payments, 1):
        ref = f"REF{today}{i:04d}"
        amount_str = f"{p['currency']}{flt(p['amount']):.2f}"
        msg = (
            f"{{1:F01{p['debt_bic'][:8]}AXXX0000000000}}"
            f"{{2:I103{p['cred_acc_bic'][:8]}XXXXN}}"
            f"{{3:{{108:{ref}}}}}"
            f"{{4:\n"
            f":20:{ref}\n"
            f":23B:CRED\n"
            f":32A:{today}{amount_str}\n"
            f":50K:/{_clean_acc(debit_account)}\n"
            f"{p['debt_name']}\n"
            f":59:/{p['cred_acc_no']}\n"
            f"{p['cred_name']}\n"
            f":70:{p['details'][:35]}\n"
            f":71A:SHA\n"
            f"-}}"
        )
        blocks.append(msg)

    return "\r\n\r\n".join(blocks)


# ══════════════════════════════════════════════════════════════════════════════
#  HELPER UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

# Nigerian bank BIC/SWIFT codes
_NG_BANK_BICS = {
    "zenith":       "ZEIBNGLA",
    "zenith bank":  "ZEIBNGLA",
    "gtb":          "GTBINGLA",
    "gtbank":       "GTBINGLA",
    "guaranty trust bank": "GTBINGLA",
    "access":       "ABNGNGLA",
    "access bank":  "ABNGNGLA",
    "uba":          "UNAFNGLA",
    "united bank for africa": "UNAFNGLA",
    "first bank":   "FBNINGLA",
    "firstbank":    "FBNINGLA",
    "first bank of nigeria": "FBNINGLA",
    "fcmb":         "FCMBNGLA",
    "sterling":     "NAMENGLA",
    "stanbic":      "SBICNGLA",
    "stanbic ibtc": "SBICNGLA",
    "union bank":   "UBNINGLA",
    "wema":         "WEMANGLA",
    "providus":     "PROVNGLA",
    "polaris":      "PLRISNGLA",
    "keystone":     "KEYSINGLA",
    "heritage":     "HBCLNGLA",
    "standard chartered": "SCBLNGLA",
    "citibank":     "CITINGLA",
    "citi":         "CITINGLA",
    "ecobank":      "ECOCNGLA",
    "fidelity":     "FIDTNGLA",
    "jaiz":         "JAIZNGLA",
    "lotus":        "LOTUSNGLA",
    "parallex":     "PARALLNGLA",
    "opay":         "OPAYNG",
    "kuda":         "KUDANGLA",
    "moniepoint":   "TEAMAPT",
    "palmpay":      "PALMPAYNG",
}

def _get_bank_bic(bank_name):
    if not bank_name:
        return ""
    return _NG_BANK_BICS.get(bank_name.lower().strip(), "")


def _get_bank_bic_from_account(bank_account_name, company=None, gateway_name=None):
    """
    Get BIC/SWIFT from a Bank Account name or GL Account name.

    Priority:
      1. Bank Account DocType (by name) → Bank.swift_number
      2. Bank Account DocType (by linked GL account) → Bank.swift_number
      3. Payment Gateway Settings bank_bic_code
    """
    if not bank_account_name:
        # Fallback to gateway settings
        if gateway_name:
            bic = frappe.db.get_value("Payment Gateway Settings", gateway_name, "bank_bic_code")
            if bic: return str(bic)
        return ""

    # Priority 1: it IS a Bank Account name
    bank = frappe.db.get_value("Bank Account", bank_account_name, "bank")
    if bank:
        swift = frappe.db.get_value("Bank", bank, "swift_number")
        if swift: return str(swift)
        return _get_bank_bic(bank)

    # Priority 2: it is a GL Account — find matching Bank Account
    if company:
        ba = frappe.db.get_all(
            "Bank Account",
            filters={"account": bank_account_name, "company": company},
            fields=["bank"],
            limit=1
        )
        if ba and ba[0].bank:
            swift = frappe.db.get_value("Bank", ba[0].bank, "swift_number")
            if swift: return str(swift)
            return _get_bank_bic(ba[0].bank)

    # Priority 3: Payment Gateway Settings
    if gateway_name:
        bic = frappe.db.get_value("Payment Gateway Settings", gateway_name, "bank_bic_code")
        if bic: return str(bic)

    if company:
        gws = frappe.db.get_all(
            "Payment Gateway Settings",
            filters={"company": company, "enabled": 1},
            fields=["bank_bic_code"],
            limit=1
        )
        if gws and gws[0].bank_bic_code:
            return str(gws[0].bank_bic_code)

    return ""


def _get_company_bic(payroll_entry_or_acc, company=None, gateway_name=None):
    """Get BIC from the company's debit bank account."""
    if hasattr(payroll_entry_or_acc, "payment_account"):
        acc     = payroll_entry_or_acc.payment_account
        company = company or getattr(payroll_entry_or_acc, "company", None)
    else:
        acc = str(payroll_entry_or_acc)
    return _get_bank_bic_from_account(acc, company, gateway_name)


def _get_company_address(company, gateway_name=None):
    """
    Return address dict for ISO 20022 DEBT_ADDRESS_* fields.

    Priority:
      1. Payment Gateway Settings record (debt_building_number, debt_street_name,
         debt_building_name, debt_city) — these are set to exactly match
         the company's bank registration details.
      2. ERPNext Address DocType linked to the company (fallback).
      3. Blanks with city defaulting to LAGOS.
    """
    # Priority 1: Payment Gateway Settings address fields
    if gateway_name:
        gw = frappe.db.get_value(
            "Payment Gateway Settings", gateway_name,
            ["debt_building_number", "debt_street_name",
             "debt_building_name", "debt_city", "debt_country"],
            as_dict=True
        )
        if gw and (gw.get("debt_street_name") or gw.get("debt_building_number")):
            return {
                "building_number": (gw.get("debt_building_number") or "").upper(),
                "street":          (gw.get("debt_street_name")     or "").upper(),
                "building_name":   (gw.get("debt_building_name")   or "").upper(),
                "city":            (gw.get("debt_city")            or "LAGOS").upper(),
            }

    # Priority 2: try any active gateway for this company
    gws = frappe.db.get_all(
        "Payment Gateway Settings",
        filters={"company": company.name, "enabled": 1},
        fields=["name", "debt_building_number", "debt_street_name",
                "debt_building_name", "debt_city"],
        limit=1
    )
    if gws:
        gw = gws[0]
        if gw.get("debt_street_name") or gw.get("debt_building_number"):
            return {
                "building_number": (gw.get("debt_building_number") or "").upper(),
                "street":          (gw.get("debt_street_name")     or "").upper(),
                "building_name":   (gw.get("debt_building_name")   or "").upper(),
                "city":            (gw.get("debt_city")            or "LAGOS").upper(),
            }

    # Priority 3: ERPNext Address DocType
    addr = frappe.db.get_all(
        "Address",
        filters={"link_doctype": "Company", "link_name": company.name,
                 "is_primary_address": 1},
        fields=["address_line1", "address_line2", "city"],
        limit=1
    )
    if addr:
        a = addr[0]
        return {
            "building_number": "",
            "street":          (a.address_line1 or "").upper(),
            "building_name":   (a.address_line2 or "").upper(),
            "city":            (a.city          or "LAGOS").upper(),
        }

    return {"building_number": "", "street": "", "building_name": "", "city": "LAGOS"}


def _clean_acc(account_name, company=None, gateway_name=None):
    """
    Resolve the debit account number (10-digit NUBAN) from various sources.

    Priority:
      1. Bank Account DocType — match by name or by linked GL account
      2. Payment Gateway Settings — company_account_no field
      3. Return raw value as last resort (will be wrong but visible)
    """
    if not account_name:
        # Try Payment Gateway Settings as fallback
        if gateway_name:
            acc = frappe.db.get_value("Payment Gateway Settings", gateway_name, "company_account_no")
            if acc: return str(acc)
        return ""

    # Priority 1a: account_name IS a Bank Account name
    acc_no = frappe.db.get_value("Bank Account", account_name, "bank_account_no")
    if acc_no:
        return str(acc_no)

    # Priority 1b: account_name is a GL Account — find matching Bank Account
    if company:
        ba = frappe.db.get_all(
            "Bank Account",
            filters={"account": account_name, "company": company},
            fields=["bank_account_no"],
            limit=1
        )
        if ba and ba[0].bank_account_no:
            return str(ba[0].bank_account_no)

    # Priority 2: Payment Gateway Settings company_account_no
    if gateway_name:
        acc = frappe.db.get_value("Payment Gateway Settings", gateway_name, "company_account_no")
        if acc: return str(acc)

    if company:
        gws = frappe.db.get_all(
            "Payment Gateway Settings",
            filters={"company": company, "enabled": 1},
            fields=["company_account_no"],
            limit=1
        )
        if gws and gws[0].company_account_no:
            return str(gws[0].company_account_no)

    # Last resort
    return str(account_name)


def _bic_to_sort_code(bic):
    """Map BIC to local sort code for Nigerian / UK banks."""
    _NG_SORT_CODES = {
        "ZEIBNGLA": "057",
        "GTBINGLA": "058",
        "ABNGNGLA": "044",
        "UNAFNGLA": "033",
        "FBNINGLA": "011",
        "FCMBNGLA": "214",
        "NAMENGLA": "232",
        "SBICNGLA": "221",
        "UBNINGLA": "032",
        "WEMANGLA": "035",
        "ECOCNGLA": "050",
        "FIDTNGLA": "070",
    }
    return _NG_SORT_CODES.get(bic, "000")


def _month_label(date_val):
    """Return 'JUNE 2026' style label."""
    d = getdate(date_val)
    return d.strftime("%B %Y").upper()


# ══════════════════════════════════════════════════════════════════════════════
#  ATTACH & EMAIL — save file to ERPNext or send via email
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def attach_payment_file_to_doc(source_doctype, source_name, bank_format="zenith_iso20022"):
    """
    Generate the bank payment file and attach it as a File record
    linked to the source document (Payroll Entry or Batch Bank Transaction).

    Returns the file URL so JS can show a clickable link.
    """
    if source_doctype == "Payroll Entry":
        result = generate_payroll_payment_file(source_name, bank_format)
    elif source_doctype == "Batch Bank Transaction":
        result = generate_batch_payment_file(source_name, bank_format)
    else:
        frappe.throw(_(f"Unsupported doctype: {source_doctype}"))

    if not result.get("success"):
        frappe.throw(_(result.get("error", "File generation failed")))

    file_content = base64.b64decode(result["file_data"])
    file_name    = result["file_name"]

    # Save to Frappe file system, attached to the source document
    from frappe.utils.file_manager import save_file
    file_doc = save_file(
        fname     = file_name,
        content   = file_content,
        dt        = source_doctype,
        dn        = source_name,
        folder    = "Home/Bank Payment Files",
        decode    = False,
        is_private= 1,          # private — visible only to logged-in users
    )

    # Log on the source document
    frappe.get_doc({
        "doctype":   "Comment",
        "comment_type": "Info",
        "reference_doctype": source_doctype,
        "reference_name":    source_name,
        "content":   f"Bank payment file attached: {file_name} · {result['row_count']} rows · {bank_format} · {frappe.utils.now()}",
    }).insert(ignore_permissions=True)

    frappe.db.commit()

    return {
        "success":    True,
        "file_name":  file_name,
        "file_url":   file_doc.file_url,
        "row_count":  result["row_count"],
        "total_amount": result["total_amount"],
        "format":     result.get("format", bank_format),
    }


@frappe.whitelist()
def email_payment_file(source_doctype, source_name, bank_format="zenith_iso20022",
                       recipients=None, subject=None, message=None):
    """
    Generate the bank payment file and send it as an email attachment.

    recipients: comma-separated email addresses (defaults to gateway contact email
                or current user's email if not provided)
    subject:    email subject (auto-generated if not provided)
    message:    email body (auto-generated if not provided)
    """
    if source_doctype == "Payroll Entry":
        result = generate_payroll_payment_file(source_name, bank_format)
    elif source_doctype == "Batch Bank Transaction":
        result = generate_batch_payment_file(source_name, bank_format)
    else:
        frappe.throw(_(f"Unsupported doctype: {source_doctype}"))

    if not result.get("success"):
        frappe.throw(_(result.get("error", "File generation failed")))

    file_content = base64.b64decode(result["file_data"])
    file_name    = result["file_name"]

    # Resolve recipients
    if not recipients:
        recipients = frappe.session.user
    if isinstance(recipients, str):
        recipient_list = [r.strip() for r in recipients.split(",") if r.strip()]
    else:
        recipient_list = recipients

    # Build subject and body
    doc_label = f"{source_doctype} {source_name}"
    if not subject:
        subject = f"Bank Payment File — {file_name}"
    if not message:
        message = f"""
<p>Please find attached the bank payment file generated from <b>{doc_label}</b>.</p>
<ul>
  <li><b>File:</b> {file_name}</li>
  <li><b>Format:</b> {result.get('format', bank_format)}</li>
  <li><b>Transactions:</b> {result['row_count']}</li>
  <li><b>Total Amount:</b> ₦{result['total_amount']:,.2f}</li>
  <li><b>Generated:</b> {frappe.utils.now()}</li>
</ul>
<p>This file should be uploaded to your bank's Corporate Internet Banking portal
or transmitted via the configured SFTP channel.</p>
<p style="color:#64748B;font-size:12px">Generated by Ecclesia ERP — Value Impacts Consulting</p>
"""

    # Send email with the CSV/XML/TXT as attachment
    frappe.sendmail(
        recipients = recipient_list,
        subject    = subject,
        message    = message,
        attachments= [{
            "fname":   file_name,
            "fcontent": file_content,
        }],
        reference_doctype = source_doctype,
        reference_name    = source_name,
    )

    # Log on source document
    frappe.get_doc({
        "doctype":   "Comment",
        "comment_type": "Info",
        "reference_doctype": source_doctype,
        "reference_name":    source_name,
        "content":   f"Bank payment file emailed: {file_name} to {', '.join(recipient_list)} · {frappe.utils.now()}",
    }).insert(ignore_permissions=True)

    frappe.db.commit()

    return {
        "success":     True,
        "file_name":   file_name,
        "recipients":  recipient_list,
        "row_count":   result["row_count"],
        "total_amount": result["total_amount"],
    }


@frappe.whitelist()
def get_attached_payment_files(source_doctype, source_name):
    """Return list of previously attached bank payment files for this document."""
    files = frappe.db.get_all(
        "File",
        filters={
            "attached_to_doctype": source_doctype,
            "attached_to_name":    source_name,
            "file_name":           ["like", "BankPayment%"],
        },
        fields=["name", "file_name", "file_url", "file_size", "creation", "modified_by"],
        order_by="creation desc",
        limit=20,
    )
    return {"success": True, "files": files}