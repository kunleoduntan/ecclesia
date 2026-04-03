# Copyright (c) 2026, Ecclesia Enterprise — License: MIT
# FILE LOCATION: apps/ecclesia/ecclesia/www/ess.py
# (NOT in api/ — this is the web page controller)

import frappe
from frappe.utils import today, getdate, flt


def get_context(context):
    # ── 1. Require login ─────────────────────────────────────────
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/ess"
        raise frappe.Redirect

    # ── 2. Read ESS Settings directly from DB (no cache) ────────
    portal_title = "ESS Portal"
    show_demo    = False

    try:
        if frappe.db.exists("DocType", "ESS Settings"):
            row = frappe.db.get_values(
                "ESS Settings",
                filters={"name": "ESS Settings"},
                fieldname=["portal_title", "show_demo_data"],
                as_dict=True,
            )
            if row:
                portal_title = row[0].get("portal_title") or "ESS Portal"
                raw          = row[0].get("show_demo_data")
                if raw is None:
                    show_demo = False
                elif isinstance(raw, str):
                    show_demo = raw.lower() in ("1", "true", "yes", "on")
                else:
                    show_demo = bool(int(raw))
    except Exception as e:
        frappe.log_error(f"ESS Settings read error: {e}", "ESS Portal")

    context.title        = portal_title
    context.portal_title = portal_title

    # ── 3. Demo mode — return minimal boot ───────────────────────
    if show_demo:
        context.boot = frappe.as_json({
            "demo_mode":    True,
            "user":         frappe.session.user,
            "portal_title": portal_title,
            "today":        today(),
        })
        return

    # ── 4. Resolve employee ───────────────────────────────────────
    emp_id = frappe.db.get_value(
        "Employee",
        {"user_id": frappe.session.user, "status": "Active"},
    )
    if not emp_id:
        # Try without status filter (in case status field differs)
        emp_id = frappe.db.get_value("Employee", {"user_id": frappe.session.user})

    if not emp_id:
        context.boot = frappe.as_json({
            "demo_mode":    False,
            "user":         frappe.session.user,
            "error":        "no_employee",
            "portal_title": portal_title,
            "today":        today(),
        })
        return

    # Build field list — only add custom ESS fields if columns exist
    fields = [
        "name", "employee_name", "department", "designation",
        "date_of_joining", "company", "image", "status",
    ]
    for col in ("ess_qr_code_image", "ess_face_registered"):
        if frappe.db.has_column("Employee", col):
            fields.append(col)

    emp = frappe.db.get_value("Employee", emp_id, fields, as_dict=True)
    if not emp:
        context.boot = frappe.as_json({
            "demo_mode":    False,
            "user":         frappe.session.user,
            "error":        "no_employee",
            "portal_title": portal_title,
            "today":        today(),
        })
        return

    # ── 5. Counts ─────────────────────────────────────────────────
    open_tasks       = _safe_count("ESS Task",          {"assigned_to": emp.name, "status": ["in", ["Open", "In Progress"]]})
    pending_docs     = _safe_count("Employee Document",  {"employee": emp.name, "action_required": 1, "action_status": "Pending"})
    open_loans       = _safe_count("Loan Application",  {"applicant_type": "Employee", "applicant": emp.name, "status": ["in", ["Open", "Approved"]]})
    pending_requests = _safe_count("eRequest",           {"requested_by": frappe.session.user, "workflow_state": ["in", ["Draft", "Pending Manager Approval", "Pending Finance Approval", "Pending Final Approval"]]})

    # ── 6. Leave balances ─────────────────────────────────────────
    leave_balances = _get_leave_balances(emp.name)

    # ── 7. Loan types ─────────────────────────────────────────────
    loan_types = []
    try:
        if frappe.db.exists("DocType", "Loan Type"):
            loan_types = frappe.get_all(
                "Loan Type",
                filters={"disabled": 0},
                fields=["name", "loan_name", "maximum_loan_amount", "rate_of_interest"],
                order_by="loan_name",
            )
    except Exception as e:
        frappe.log_error(f"ESS loan types error: {e}", "ESS Portal")

    # ── 8. Build boot payload ─────────────────────────────────────
    context.boot = frappe.as_json({
        "demo_mode":      False,
        "user":           frappe.session.user,
        "portal_title":   portal_title,
        "employee":       emp.name,
        "employee_name":  emp.employee_name,
        "department":     emp.department     or "",
        "designation":    emp.designation    or "",
        "company":        emp.company        or "",
        "doj":            str(emp.date_of_joining) if emp.date_of_joining else None,
        "avatar":         emp.get("image")              or None,
        "qr_code":        emp.get("ess_qr_code_image")  or None,
        "face_registered":bool(emp.get("ess_face_registered")),
        "today":          getdate(today()).strftime("%Y-%m-%d"),
        "stats": {
            "open_tasks":       open_tasks,
            "pending_docs":     pending_docs,
            "pending_requests": pending_requests,
            "open_loans":       open_loans,
        },
        "leave_balances": leave_balances,
        "loan_types":     [dict(lt) for lt in loan_types],
        "roles":          frappe.get_roles(frappe.session.user),
    })


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_count(doctype, filters):
    """Count records safely — returns 0 if doctype missing or error."""
    try:
        if not frappe.db.exists("DocType", doctype):
            return 0
        return frappe.db.count(doctype, filters=filters) or 0
    except Exception as e:
        frappe.log_error(f"ESS count error ({doctype}): {e}", "ESS Portal")
        return 0


def _get_leave_balances(employee: str) -> list:
    """Return list of {leave_type, allocated, used, remaining} for today."""
    try:
        if not frappe.db.exists("DocType", "Leave Allocation"):
            return []

        today_d = getdate(today())
        allocs  = frappe.get_all(
            "Leave Allocation",
            filters={
                "employee":   employee,
                "docstatus":  1,
                "from_date":  ["<=", today_d],
                "to_date":    [">=", today_d],
            },
            fields=["leave_type", "total_leaves_allocated", "from_date", "to_date"],
        )

        result = []
        for a in allocs:
            # Sum total_leave_days from approved Leave Applications
            used_rows = frappe.db.get_all(
                "Leave Application",
                filters={
                    "employee":   employee,
                    "leave_type": a.leave_type,
                    "status":     "Approved",
                    "docstatus":  1,
                    "from_date":  [">=", a.from_date],
                    "to_date":    ["<=", a.to_date],
                },
                fields=["total_leave_days"],
            )
            used      = sum(flt(r.total_leave_days) for r in used_rows)
            allocated = flt(a.total_leaves_allocated)
            result.append({
                "leave_type": a.leave_type,
                "allocated":  allocated,
                "used":       used,
                "remaining":  max(0.0, allocated - used),
            })

        return result

    except Exception as e:
        frappe.log_error(f"ESS leave balances error: {e}", "ESS Portal")
        return []