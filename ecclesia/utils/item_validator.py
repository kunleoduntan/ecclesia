import frappe
from frappe import _


# ─────────────────────────────────────────────
# CACHE HELPERS
# ─────────────────────────────────────────────

def get_company_setting(company):
    """Cached fetch of hide_disabled_items from Company."""
    cache_key = f"hide_disabled_items_{company}"
    cached = frappe.cache().get_value(cache_key)
    if cached is not None:
        return cached

    value = frappe.db.get_value("Company", company, "hide_disabled_items") or 0
    frappe.cache().set_value(cache_key, value, expires_in_sec=300)  # 5 min cache
    return value


def clear_company_item_filter_cache(doc, method=None):
    """Clear cached setting when Company doc is saved."""
    frappe.cache().delete_value(f"hide_disabled_items_{doc.name}")


# ─────────────────────────────────────────────
# CORE VALIDATOR
# ─────────────────────────────────────────────

def validate_disabled_items(doc, method=None):
    """
    Universal validator hooked into doc_before_save for every doctype.
    Blocks transactions containing disabled items when company setting is ON.
    """
    company = getattr(doc, "company", None) or frappe.defaults.get_default("company")
    if not company:
        return

    if not get_company_setting(company):
        return  # Setting is OFF — allow everything

    disabled_items_found = []

    # ── Check direct item_code on the document itself ──
    item_code = getattr(doc, "item_code", None)
    if item_code:
        if frappe.db.get_value("Item", item_code, "disabled"):
            item_name = frappe.db.get_value("Item", item_code, "item_name") or item_code
            disabled_items_found.append(
                f"<b>{item_name}</b> ({item_code}) on the main document"
            )

    # ── Check all child tables dynamically ──
    for field in doc.meta.fields:
        if field.fieldtype != "Table":
            continue

        child_rows = getattr(doc, field.fieldname, [])
        for row in child_rows:
            row_item_code = getattr(row, "item_code", None)
            if not row_item_code:
                continue

            if frappe.db.get_value("Item", row_item_code, "disabled"):
                item_name = getattr(row, "item_name", None) or row_item_code
                disabled_items_found.append(
                    f"Row {row.idx} in <b>{field.label or field.fieldname}</b>: "
                    f"<b>{item_name}</b> ({row_item_code})"
                )

    if disabled_items_found:
        item_list = "<br>".join(disabled_items_found)
        frappe.throw(
            title=_("Disabled Items Not Allowed"),
            msg=_(
                f"The following disabled items cannot be used in transactions "
                f"for company <b>{company}</b>:<br><br>{item_list}<br><br>"
                f"Please remove or replace these items before saving."
            )
        )