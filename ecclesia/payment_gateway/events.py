import frappe


def on_sales_invoice_submit(doc, method):
    """
    Fires on Sales Invoice on_submit.
    Generates a payment link and attaches it as a comment on the invoice.
    Non-blocking — errors are logged, never raised.
    """
    if not frappe.db.exists(
        "Payment Gateway Settings", {"is_default": 1, "enabled": 1}
    ):
        return

    try:
        from ecclesia.api.payment import initiate
        result = initiate(
            reference_doctype="Sales Invoice",
            reference_docname=doc.name
        )
        if result and result.get("payment_url"):
            frappe.get_doc({
                "doctype":           "Comment",
                "comment_type":      "Info",
                "reference_doctype": "Sales Invoice",
                "reference_name":    doc.name,
                "content":           f"Payment Link: {result['payment_url']}",
            }).insert(ignore_permissions=True)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Ecclesia: Payment Link Generation Failed")


def prevent_manual_edit(doc, method):
    """
    Payment Gateway Log is system-managed — block manual edits from the UI.
    API calls (ignore_permissions=True) bypass this check intentionally.
    """
    if frappe.flags.in_migrate or frappe.flags.in_install:
        return
    if doc.is_new():
        return
    if frappe.local.flags.get("ignore_permissions"):
        return
    frappe.throw(
        "Payment Gateway Logs are system-managed and cannot be edited manually.",
        frappe.PermissionError
    )


def get_permission_query(user):
    """
    Restrict Payment Gateway Log list view:
    - System Manager and Accounts Manager see all records
    - Others see nothing
    """
    if not user:
        user = frappe.session.user
    if "System Manager" in frappe.get_roles(user):
        return ""
    if "Accounts Manager" in frappe.get_roles(user):
        return ""
    if "Ecclesia Payment Manager" in frappe.get_roles(user):
        return ""
    return "1=0"


def has_permission(doc, ptype, user):
    """Row-level permission for Payment Gateway Log."""
    if not user:
        user = frappe.session.user
    roles = frappe.get_roles(user)
    return bool(
        {"System Manager", "Accounts Manager", "Ecclesia Payment Manager"} & set(roles)
    )