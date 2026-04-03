# Copyright (c) 2026, Ecclesia Enterprise — License: MIT
# ess_portal_documents.py
"""
ESS Portal — Employee Document Module

Custom doctype `Employee Document` ships with this app.
Fields (all ours — no standard doctype modified):
  employee (Link→Employee), document_title, document_category,
  document_type (Employee Upload / HR Assigned / System Generated),
  file_url (Attach), file_name (Data),
  uploaded_on (Date), uploaded_by (Link→User),
  assigned_by (Link→Employee), assigned_by_name (Data), assigned_on (Date),
  action_required (Check), action_type (Select: Signature/Acknowledge/View Only),
  action_status (Select: Pending/Completed/Not Required),
  action_completed_on (Datetime), actioned_by (Link→User),
  signature_image (Attach Image),
  expiry_date (Date), is_expired (Check, read_only),
  linked_doctype (Data), linked_docname (Dynamic Link), notes (Small Text)
"""

import frappe
import base64
import io
from frappe.utils.file_manager import save_file
from frappe.utils import now_datetime, today, getdate


# ─────────────────────────────────────────────────────────────────
# SECTION 1 — READ
# ─────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_my_documents(category: str = None):
    """
    Return all documents for the current employee, grouped by category.
    Also returns a list of pending actions and expiry warnings.
    """
    from datetime import date
    emp = _resolve_employee()
    if not emp:
        frappe.throw("No Employee record linked to your account.")

    filters = {"employee": emp}
    if category:
        filters["document_category"] = category

    docs = frappe.get_all(
        "Employee Document",
        filters=filters,
        fields=[
            "name", "document_title", "document_category", "document_type",
            "file_url", "file_name", "uploaded_on", "uploaded_by",
            "assigned_by", "assigned_by_name", "assigned_on",
            "action_required", "action_type", "action_status",
            "action_completed_on", "expiry_date", "is_expired",
            "linked_doctype", "linked_docname", "notes",
        ],
        order_by="assigned_on desc, uploaded_on desc",
    )

    today_date = date.today()
    for d in docs:
        if d.expiry_date:
            exp = getdate(d.expiry_date)
            d["is_expired"]      = exp < today_date
            d["expires_in_days"] = (exp - today_date).days
            d["expiry_warning"]  = 0 < (exp - today_date).days <= 90
        else:
            d["is_expired"]      = False
            d["expires_in_days"] = None
            d["expiry_warning"]  = False

    grouped = {}
    for d in docs:
        grouped.setdefault(d.document_category or "other", []).append(d)

    pending = [d for d in docs if d.action_required and d.action_status == "Pending"]
    expiring = [d for d in docs if d.get("expiry_warning")]

    return {
        "documents":       docs,
        "grouped":         grouped,
        "pending_actions": pending,
        "expiring_soon":   expiring,
        "summary": {
            "total":           len(docs),
            "pending_actions": len(pending),
            "expiring_soon":   len(expiring),
            "expired":         sum(1 for d in docs if d.get("is_expired")),
        },
    }


# ─────────────────────────────────────────────────────────────────
# SECTION 2 — EMPLOYEE UPLOAD
# ─────────────────────────────────────────────────────────────────

@frappe.whitelist()
def upload_document(
    document_title:    str,
    document_category: str,
    file_b64:          str,
    file_name:         str,
    file_type:         str  = "application/pdf",
    expiry_date:       str  = None,
    notes:             str  = None,
    employee:          str  = None,
):
    """
    Employee uploads a personal document to their vault.
    HR can upload on behalf of employee by passing `employee` explicitly.
    """
    emp = employee or _resolve_employee()
    if not emp:
        frappe.throw("No Employee record linked to your account.")

    # Employees may only upload to their own vault unless HR
    current_emp = _resolve_employee()
    if current_emp != emp:
        frappe.only_for(["HR Manager", "HR User"])

    file_bytes = base64.b64decode(file_b64)
    file_doc   = save_file(
        fname=file_name,
        content=file_bytes,
        dt="Employee Document",
        dn="new",
        is_private=1,
    )

    doc = frappe.get_doc({
        "doctype":           "Employee Document",
        "employee":          emp,
        "document_title":    document_title,
        "document_category": document_category,
        "document_type":     "Employee Upload",
        "file_url":          file_doc.file_url,
        "file_name":         file_name,
        "uploaded_on":       today(),
        "uploaded_by":       frappe.session.user,
        "expiry_date":       expiry_date,
        "notes":             notes,
        "action_required":   0,
        "action_status":     "Not Required",
    })
    doc.insert()

    return {"status": "success", "document": doc.name, "file_url": file_doc.file_url}


# ─────────────────────────────────────────────────────────────────
# SECTION 3 — HR ASSIGNS DOCUMENT TO EMPLOYEE
# ─────────────────────────────────────────────────────────────────

@frappe.whitelist()
def assign_document(
    employee:          str,
    document_title:    str,
    document_category: str,
    action_type:       str,           # Signature | Acknowledge | View Only
    file_url:          str   = None,
    file_b64:          str   = None,
    file_name:         str   = None,
    linked_doctype:    str   = None,
    linked_docname:    str   = None,
    due_date:          str   = None,
    notes:             str   = None,
):
    """HR assigns a document to an employee for action."""
    frappe.only_for(["HR Manager", "HR User", "System Manager"])

    assigner     = _resolve_employee()
    assigner_name = frappe.db.get_value("Employee", assigner, "employee_name") \
                    if assigner else frappe.session.user

    if file_b64 and file_name and not file_url:
        fd = save_file(fname=file_name, content=base64.b64decode(file_b64),
                       dt="Employee Document", dn="new", is_private=1)
        file_url = fd.file_url

    doc = frappe.get_doc({
        "doctype":           "Employee Document",
        "employee":          employee,
        "document_title":    document_title,
        "document_category": document_category,
        "document_type":     "HR Assigned",
        "file_url":          file_url,
        "file_name":         file_name,
        "assigned_by":       assigner,
        "assigned_by_name":  assigner_name,
        "assigned_on":       today(),
        "action_required":   1,
        "action_type":       action_type,
        "action_status":     "Pending",
        "linked_doctype":    linked_doctype,
        "linked_docname":    linked_docname,
        "notes":             notes,
    })
    doc.insert()

    if action_type in ("Signature", "Acknowledge"):
        _create_document_action_task(doc, due_date)

    _notify_document_assigned(doc, employee)

    return {"status": "success", "document": doc.name}


# ─────────────────────────────────────────────────────────────────
# SECTION 4 — EMPLOYEE ACKNOWLEDGES / SIGNS
# ─────────────────────────────────────────────────────────────────

@frappe.whitelist()
def action_document(document_name: str, action_type: str, signature_b64: str = None):
    """
    Employee acknowledges or signs a document.

    Args:
        document_name : Employee Document docname
        action_type   : "Acknowledge" | "Signature"
        signature_b64 : Optional base64 signature PNG (for Signature type)
    """
    emp = _resolve_employee()
    doc = frappe.get_doc("Employee Document", document_name)

    if doc.employee != emp:
        frappe.throw("You can only action your own documents.", frappe.PermissionError)
    if doc.action_status == "Completed":
        return {"status": "already_done", "message": "Already actioned."}

    doc.action_status       = "Completed"
    doc.action_completed_on = now_datetime()
    doc.actioned_by         = frappe.session.user

    if signature_b64 and action_type == "Signature":
        sig_file = save_file(
            fname=f"sig_{document_name}.png",
            content=base64.b64decode(signature_b64),
            dt="Employee Document",
            dn=document_name,
            is_private=1,
        )
        doc.signature_image = sig_file.file_url

    doc.save(ignore_permissions=True)
    _complete_document_task(document_name)
    _notify_document_actioned(doc)

    return {
        "status":    "success",
        "message":   f"Document {action_type.lower()}d successfully.",
        "timestamp": str(now_datetime()),
    }


# ─────────────────────────────────────────────────────────────────
# SECTION 5 — DOC EVENT HOOKS
# ─────────────────────────────────────────────────────────────────

def notify_payslip_ready(doc, method=None):
    """Hook: Salary Slip.on_submit — notify employee their payslip is available."""
    emp_user = frappe.db.get_value("Employee", doc.employee, "user_id")
    if not emp_user:
        return

    frappe.sendmail(
        recipients=[emp_user],
        subject=f"[ESS] Your {doc.salary_slip_based_on_timesheet and 'Timesheet' or ''} "
                f"Payslip is Ready — {doc.month_name if hasattr(doc, 'month_name') else doc.name}",
        message=f"""
            <p>Your payslip for <strong>{doc.start_date} to {doc.end_date}</strong> is ready.</p>
            <p><strong>Net Pay:</strong> {doc.net_pay:,.2f}</p>
            <p><a href="{frappe.utils.get_url()}/ess">Download in ESS Portal →</a></p>
        """,
        now=False,
    )


# ─────────────────────────────────────────────────────────────────
# SECTION 6 — SCHEDULED JOBS
# ─────────────────────────────────────────────────────────────────

def flag_expired_documents():
    """Daily: mark expired Employee Document records."""
    expired = frappe.get_all(
        "Employee Document",
        filters={"expiry_date": ["<", today()], "is_expired": 0},
        pluck="name",
    )
    for name in expired:
        frappe.db.set_value("Employee Document", name, "is_expired", 1)

    if expired:
        frappe.logger().info(f"[ESS Documents] Flagged {len(expired)} expired documents.")


def send_document_expiry_reminders():
    """Weekly: warn employees of documents expiring in 90/60/30/7 days."""
    from datetime import date, timedelta

    for days in [90, 60, 30, 7]:
        target = date.today() + timedelta(days=days)
        expiring = frappe.get_all(
            "Employee Document",
            filters={"expiry_date": target, "is_expired": 0},
            fields=["name", "employee", "document_title", "expiry_date"],
        )
        for d in expiring:
            emp_user = frappe.db.get_value("Employee", d.employee, "user_id")
            if not emp_user:
                continue
            frappe.sendmail(
                recipients=[emp_user],
                subject=f"[ESS] Document Expiring in {days} Days: {d.document_title}",
                message=f"""
                    <p>Your document <strong>{d.document_title}</strong>
                    expires on <strong>{d.expiry_date}</strong> ({days} days remaining).
                    Please upload a renewal.</p>
                    <p><a href="{frappe.utils.get_url()}/ess">ESS Portal →</a></p>
                """,
                now=False,
            )


# ─────────────────────────────────────────────────────────────────
# PERMISSIONS
# ─────────────────────────────────────────────────────────────────

def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user
    privileged = {"HR Manager", "HR User", "System Manager"}
    if set(frappe.get_roles(user)) & privileged:
        return ""
    emp = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if not emp:
        return "1=0"
    return f"`tabEmployee Document`.`employee` = {frappe.db.escape(emp)}"


def has_permission(doc, ptype, user):
    emp = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if doc.employee == emp:
        return True
    privileged = {"HR Manager", "HR User", "System Manager"}
    return bool(set(frappe.get_roles(user)) & privileged)


# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────

def _resolve_employee():
    return frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")


def _create_document_action_task(doc, due_date: str = None):
    try:
        frappe.get_doc({
            "doctype":        "ESS Task",
            "assigned_to":    doc.employee,
            "assigned_by_name": doc.assigned_by_name or "HR",
            "title":          f"{doc.action_type}: {doc.document_title}",
            "task_category":  "Document Action",
            "priority":       "High",
            "status":         "Open",
            "due_date":       due_date,
            "linked_doctype": "Employee Document",
            "linked_docname": doc.name,
            "assigned_on":    today(),
        }).insert(ignore_permissions=True)
    except Exception as e:
        frappe.logger().warning(f"[ESS Documents] Could not create task: {e}")


def _complete_document_task(document_name: str):
    task = frappe.db.get_value(
        "ESS Task",
        {"linked_doctype": "Employee Document", "linked_docname": document_name,
         "status": ["!=", "Completed"]},
        "name",
    )
    if task:
        frappe.db.set_value("ESS Task", task, {
            "status":       "Completed",
            "completed_on": now_datetime(),
        })


def _notify_document_assigned(doc, employee: str):
    emp_user = frappe.db.get_value("Employee", employee, "user_id")
    if not emp_user:
        return
    frappe.sendmail(
        recipients=[emp_user],
        subject=f"[ESS] Action Required: {doc.document_title}",
        message=f"""
            <p>A document has been assigned to you for <strong>{doc.action_type}</strong>:</p>
            <ul>
                <li><strong>Document:</strong> {doc.document_title}</li>
                <li><strong>Assigned By:</strong> {doc.assigned_by_name}</li>
                {"<li><strong>Notes:</strong> " + doc.notes + "</li>" if doc.notes else ""}
            </ul>
            <p><a href="{frappe.utils.get_url()}/ess">Open ESS Portal →</a></p>
        """,
        now=False,
    )


def _notify_document_actioned(doc):
    if not doc.assigned_by:
        return
    assigner_user = frappe.db.get_value("Employee", doc.assigned_by, "user_id")
    if not assigner_user:
        return
    emp_name = frappe.db.get_value("Employee", doc.employee, "employee_name")
    frappe.sendmail(
        recipients=[assigner_user],
        subject=f"[ESS] Document {doc.action_type}d: {doc.document_title}",
        message=f"<p><strong>{emp_name}</strong> has {doc.action_type.lower()}d "
                f"<em>{doc.document_title}</em> on {doc.action_completed_on}.</p>",
        now=False,
    )