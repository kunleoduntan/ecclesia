

# ------------------------------------------------------------------ #
#  ecclesia/ecclesia/doctype/bank_statement_upload/api.py             #
#  Whitelisted API for client-side polling                            #
# ------------------------------------------------------------------ #

import frappe


@frappe.whitelist()
def get_import_progress(import_name: str) -> dict:
    """
    Called by JS polling / Realtime fallback.
    Returns current progress counters and status.
    """
    doc = frappe.get_doc("Bank Statement Upload", import_name)
    return doc.get_progress()


@frappe.whitelist()
def save_alias_from_review(
    raw_pattern: str,
    cleaned_name: str,
    entity_type: str,
    supplier_id: str = None,
    customer_id: str = None,
    account_to_debit: str = None,
    trans_type: str = None,
    cashflow_type: str = None,
    company: str = None
):
    """
    Called when a user manually corrects an entity in the review queue.
    Upserts a Bank Statement Alias for future automatic matching.
    """
    existing = frappe.db.exists("Bank Statement Alias", {"raw_pattern": raw_pattern})
    if existing:
        doc = frappe.get_doc("Bank Statement Alias", existing)
    else:
        doc = frappe.new_doc("Bank Statement Alias")
        doc.raw_pattern = raw_pattern

    doc.cleaned_name    = cleaned_name
    doc.entity_type     = entity_type
    doc.supplier_id     = supplier_id or ""
    doc.customer_id     = customer_id or ""
    doc.account_to_debit = account_to_debit or ""
    doc.trans_type      = trans_type or ""
    doc.cashflow_type   = cashflow_type or ""
    doc.company         = company or frappe.defaults.get_user_default("company")

    if existing:
        doc.save(ignore_permissions=True)
    else:
        doc.insert(ignore_permissions=True)

    frappe.db.commit()
    return {"saved": True, "name": doc.name}