"""
Transaction Coding System
==========================
Assigns permanent, globally unique transaction codes to every registered DocType.
Format: [MODULE]-[TYPE]-[SEQUENCE]-[ACCOUNT CLASS]

Examples:
  FIN-AP-001-LIAB  → Purchase Invoice
  FIN-AR-001-ASSET → Sales Invoice
  HR-LV-001-OPEX   → Leave Application
  CUS-XX-001-NA    → Custom DocType

These codes are permanent — they never change after first assignment.
They appear on every finding, checklist, and report for full traceability.
"""

import frappe
import re


# ─────────────────────────────────────────────────────────────────────────────
# Module code mappings
# ─────────────────────────────────────────────────────────────────────────────

MODULE_CODES = {
    "Financial":          "FIN",
    "HR & Payroll":       "HR",
    "Inventory & Stock":  "INV",
    "Procurement":        "PRC",
    "Sales":              "SLS",
    "Approval & Workflow":"APV",
    "Master Data":        "MST",
    "Custom":             "CUS",
}

# Type code inference by DocType name keywords
TYPE_MAPPINGS = [
    (["invoice", "bill"],                          "INV"),
    (["payment", "receipt", "remittance"],         "PAY"),
    (["journal", "jv", "voucher"],                 "JRN"),
    (["order", "po", "so"],                        "ORD"),
    (["expense", "claim", "reimburs"],             "EXP"),
    (["salary", "payroll", "payslip"],             "SAL"),
    (["leave", "absence", "holiday"],              "LV"),
    (["attendance", "timesheet"],                  "ATT"),
    (["asset", "depreciat", "capitaliz"],          "AST"),
    (["stock", "inventory", "warehouse"],          "STK"),
    (["delivery", "shipment", "dispatch"],         "DEL"),
    (["quotation", "rfq", "tender"],               "QOT"),
    (["customer", "client"],                       "CUS"),
    (["supplier", "vendor"],                       "SUP"),
    (["employee", "staff", "hr"],                  "EMP"),
    (["budget", "forecast", "plan"],               "BDG"),
    (["tax", "gst", "vat"],                        "TAX"),
    (["bank", "reconcil"],                         "BNK"),
    (["project", "task", "milestone"],             "PRJ"),
    (["loan", "advance", "borrow"],                "LON"),
]


def assign_transaction_code(doctype_name, classification, account_class, is_gl_posting):
    """
    Assign a unique, permanent transaction code to a DocType.

    Returns dict with full_code, module_code, type_code.
    """
    module_code = MODULE_CODES.get(classification, "CUS")
    type_code   = _infer_type_code(doctype_name)
    account_suffix = account_class.upper() if account_class else "NA"

    # Find next available sequence for this module+type combination
    sequence = _next_sequence(module_code, type_code)

    full_code = f"{module_code}-{type_code}-{sequence:03d}-{account_suffix}"

    return {
        "full_code":    full_code,
        "module_code":  module_code,
        "type_code":    type_code,
    }


def _infer_type_code(doctype_name):
    """Infer the two-to-three letter type code from the DocType name."""
    name_lower = doctype_name.lower()
    for keywords, code in TYPE_MAPPINGS:
        if any(k in name_lower for k in keywords):
            return code
    # Fallback: use first two meaningful words
    words = re.sub(r"[^a-z ]", "", name_lower).split()
    initials = "".join(w[0].upper() for w in words if len(w) > 2)
    return initials[:3] if initials else "XX"


def _next_sequence(module_code, type_code):
    """Find the next available sequence number for module+type combination."""
    existing = frappe.get_all(
        "Auditable DocType Registry",
        filters={
            "module_code": module_code,
            "type_code":   type_code,
        },
        fields=["transaction_code"],
        order_by="transaction_code asc"
    )

    if not existing:
        return 1

    # Extract sequence numbers from existing codes
    sequences = []
    for row in existing:
        parts = (row.transaction_code or "").split("-")
        if len(parts) >= 3:
            try:
                sequences.append(int(parts[2]))
            except ValueError:
                pass

    return max(sequences) + 1 if sequences else 1


def get_transaction_code(doctype_name):
    """Quick lookup of transaction code for a DocType name."""
    result = frappe.db.get_value(
        "Auditable DocType Registry",
        {"doctype_name": doctype_name},
        "transaction_code"
    )
    return result or "UNREGISTERED"


def is_registered(doctype_name):
    """Check if a DocType is registered in the audit registry."""
    return frappe.db.exists(
        "Auditable DocType Registry",
        {"doctype_name": doctype_name, "is_active": 1}
    )
