# Copyright (c) 2026, Ecclesia Enterprise — License: MIT
# ecclesia/ess_portal_expense.py

import frappe
from frappe.utils import today


def _get_employee():
    emp = frappe.db.get_value(
        "Employee",
        {"user_id": frappe.session.user, "status": "Active"},
        ["name", "employee_name", "company", "department"],
        as_dict=True,
    )
    if not emp:
        frappe.throw("No active Employee record linked to your account.")
    return emp


def _resolve_cost_center(label, company):
    """Try to find a matching cost center by partial name, fallback to company default."""
    if label:
        cc = frappe.db.get_value(
            "Cost Center",
            {"cost_center_name": ["like", f"%{label}%"], "company": company, "disabled": 0},
            "name",
        )
        if cc:
            return cc
    # fallback: root cost center for company
    return frappe.db.get_value("Company", company, "cost_center") or None


def _resolve_expense_type(label):
    """Match the display label to an Expense Claim Type docname."""
    et = frappe.db.get_value(
        "Expense Claim Type",
        {"expense_type": ["like", f"%{label}%"]},
        "name",
    )
    return et or label


@frappe.whitelist()
def submit_expense_claim(expense_type, amount, expense_date, cost_center="", description=""):
    emp = _get_employee()

    # Resolve expense type docname
    expense_type_name = _resolve_expense_type(expense_type)
    cost_center_name  = _resolve_cost_center(cost_center, emp.company)

    doc = frappe.new_doc("Expense Claim")
    doc.employee         = emp.name
    doc.company          = emp.company
    doc.posting_date     = expense_date or today()
    doc.approval_status  = "Draft"

    doc.append("expenses", {
        "expense_date"  : expense_date or today(),
        "expense_type"  : expense_type_name,
        "description"   : description,
        "amount"        : float(amount),
        "sanctioned_amount": float(amount),
        "cost_center"   : cost_center_name,
    })

    doc.insert(ignore_permissions=True)
    # Don't submit — let HR review and approve

    return {
        "name"            : doc.name,
        "approval_status" : doc.approval_status,
        "total_claimed_amount": float(amount),
    }


@frappe.whitelist()
def get_expense_claims():
    emp = _get_employee()

    records = frappe.get_all(
        "Expense Claim",
        filters={"employee": emp.name, "docstatus": ["!=", 2]},
        fields=["name", "posting_date", "total_claimed_amount",
                "approval_status", "status"],
        order_by="posting_date desc",
        limit=20,
    )
    # Flatten expense type for display
    result = []
    for r in records:
        exp_items = frappe.get_all(
            "Expense Claim Detail",
            filters={"parent": r.name},
            fields=["expense_type"],
            limit=1,
        )
        r["expense_type"] = exp_items[0].expense_type if exp_items else "—"
        result.append(r)

    return result