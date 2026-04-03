# Copyright (c) 2026, Ecclesia Enterprise — License: MIT
# ess_portal_erequest.py
"""
ESS Portal — eRequest Integration

eRequest DocType (module: Ecclesia) already exists.
Field names used here are taken EXACTLY from the eRequest DocType JSON:

  request_type, priority, workflow_state, title, request_date,
  requested_by, department, company, cost_center, project,
  payment_due_date, payment_purpose, description, payment_type,
  payment_category, currency, payment_amount, tax_amount,
  total_amount, amount_in_words,
  payee_type, supplier, employee, payee_name, payee_email, payee_phone,
  payee_account_number, payee_account_name, payee_bank_name,
  payee_bank_code, payment_method,
  invoice_reference, purchase_order_reference, invoice_date, invoice_amount,
  attach_invoice, attach_supporting_docs, attachment_notes,
  maintenance_type, maintenance_category, location, asset,
  issue_description, urgency_level, preferred_completion_date,
  estimated_cost, recommended_vendor, vendor_quotation,
  workflow_state, rejection_reason,
  manager_approval, manager_approval_date, manager_comments,
  finance_approval, finance_approval_date, finance_comments,
  final_approval, final_approval_date, final_comments,
  payment_document_created, payment_reference, payment_created_date,
  payment_status, payment_account, payment_transaction_id,
  payment_date, payment_amount_paid,
  created_by, created_date, last_modified_by, last_modified_date

Workflow states (from workflow_state Select options):
  Draft → Pending Manager Approval → Pending Finance Approval
        → Pending Final Approval → Approved | Rejected | Cancelled
"""

import frappe
from frappe.utils import now_datetime, today, flt


# ─────────────────────────────────────────────────────────────────
# SECTION 1 — READ / LIST
# ─────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_my_requests(request_type: str = None, workflow_state: str = None, limit: int = 50):
    """
    GET all eRequests submitted by the currently logged-in user.

    Args:
        request_type  : "Payment Request" | "Maintenance Request" | None
        workflow_state: Filter by workflow_state value
        limit         : Max rows (default 50)

    Returns:
        { requests: [...], summary: {...} }
    """
    user = frappe.session.user

    filters = {"requested_by": user}
    if request_type:
        filters["request_type"] = request_type
    if workflow_state:
        filters["workflow_state"] = workflow_state

    requests = frappe.get_all(
        "eRequest",
        filters=filters,
        fields=[
            # Core
            "name", "request_type", "priority", "workflow_state",
            "title", "request_date", "department", "company",
            # Payment
            "payment_type", "payment_category", "payment_due_date",
            "currency", "payment_amount", "tax_amount", "total_amount",
            "amount_in_words", "payment_purpose",
            # Payee
            "payee_type", "payee_name", "payee_bank_name",
            "payee_account_number", "payment_method",
            # Maintenance
            "maintenance_type", "maintenance_category",
            "location", "urgency_level", "estimated_cost",
            # Payment processing
            "payment_document_created", "payment_reference",
            "payment_status", "payment_transaction_id",
            # Approval chain
            "manager_approval", "finance_approval", "final_approval",
            "rejection_reason",
        ],
        order_by="request_date desc",
        limit=limit,
    )

    pending_states = ("Pending Manager Approval",
                      "Pending Finance Approval",
                      "Pending Final Approval")

    summary = {
        "total":        len(requests),
        "draft":        sum(1 for r in requests if r.workflow_state == "Draft"),
        "pending":      sum(1 for r in requests if r.workflow_state in pending_states),
        "approved":     sum(1 for r in requests if r.workflow_state == "Approved"),
        "rejected":     sum(1 for r in requests if r.workflow_state == "Rejected"),
        "cancelled":    sum(1 for r in requests if r.workflow_state == "Cancelled"),
        "payment_reqs": sum(1 for r in requests if r.request_type == "Payment Request"),
        "maint_reqs":   sum(1 for r in requests if r.request_type == "Maintenance Request"),
        "pending_total_amount": sum(
            flt(r.total_amount) for r in requests
            if r.request_type == "Payment Request" and r.workflow_state in pending_states
        ),
    }

    return {"requests": requests, "summary": summary}


@frappe.whitelist()
def get_request_detail(name: str):
    """Return full detail of one eRequest plus a structured approval timeline."""
    doc = frappe.get_doc("eRequest", name)

    # Permission check
    user = frappe.session.user
    if doc.requested_by != user:
        privileged = {"HR Manager", "Finance Manager", "System Manager", "Accounts Manager"}
        if not (set(frappe.get_roles(user)) & privileged):
            frappe.throw("Not permitted.", frappe.PermissionError)

    return {
        "request":  doc.as_dict(),
        "timeline": _build_timeline(doc),
    }


# ─────────────────────────────────────────────────────────────────
# SECTION 2 — CREATE
# ─────────────────────────────────────────────────────────────────

@frappe.whitelist()
def create_payment_request(
    # ── Required core fields ────────────────────────────────────
    title:            str,
    priority:         str,
    payment_purpose:  str,
    payment_type:     str,
    payment_category: str,
    payment_amount:   float,
    payment_due_date: str,
    # ── Amount ──────────────────────────────────────────────────
    currency:         str   = "NGN",
    tax_amount:       float = 0,
    # ── Payee ───────────────────────────────────────────────────
    payee_type:       str   = "Supplier",
    supplier:         str   = None,
    employee_payee:   str   = None,     # maps to eRequest.employee field
    payee_name:       str   = None,
    payee_email:      str   = None,
    payee_phone:      str   = None,
    # ── Banking ─────────────────────────────────────────────────
    payee_account_number: str = None,
    payee_account_name:   str = None,
    payee_bank_name:      str = None,
    payee_bank_code:      str = None,
    payment_method:       str = "Bank Transfer",
    # ── Invoice ─────────────────────────────────────────────────
    invoice_reference:        str   = None,
    purchase_order_reference: str   = None,
    invoice_date:             str   = None,
    invoice_amount:           float = None,
    # ── Extras ──────────────────────────────────────────────────
    cost_center:   str = None,
    project:       str = None,
    description:   str = None,
    attachment_notes: str = None,
):
    """
    Create a Payment Request eRequest (workflow_state = Draft).

    All field names match the eRequest DocType exactly.
    total_amount = payment_amount − tax_amount (computed here, read_only in DocType).
    """
    user = frappe.session.user
    emp  = _resolve_employee()
    if not emp:
        frappe.throw("Your account is not linked to an Employee record.")

    dept    = frappe.db.get_value("Employee", emp, "department")
    company = (frappe.db.get_value("Employee", emp, "company")
               or frappe.db.get_single_value("Global Defaults", "default_company"))

    total     = flt(payment_amount) - flt(tax_amount)
    in_words  = frappe.utils.money_in_words(total, currency)

    doc = frappe.get_doc({
        "doctype":           "eRequest",
        # ── Core ────────────────────────────────────────────────
        "request_type":      "Payment Request",
        "title":             title,
        "priority":          priority,
        "request_date":      today(),
        "requested_by":      user,
        "department":        dept,
        "company":           company,
        "cost_center":       cost_center,
        "project":           project,
        "payment_due_date":  payment_due_date,
        "payment_purpose":   payment_purpose,
        "description":       description,
        "payment_type":      payment_type,
        "payment_category":  payment_category,
        # ── Amount ──────────────────────────────────────────────
        "currency":          currency,
        "payment_amount":    flt(payment_amount),
        "tax_amount":        flt(tax_amount),
        "total_amount":      total,
        "amount_in_words":   in_words,
        # ── Payee ───────────────────────────────────────────────
        "payee_type":            payee_type,
        "supplier":              supplier,
        "employee":              employee_payee,
        "payee_name":            payee_name,
        "payee_email":           payee_email,
        "payee_phone":           payee_phone,
        # ── Banking ─────────────────────────────────────────────
        "payee_account_number":  payee_account_number,
        "payee_account_name":    payee_account_name,
        "payee_bank_name":       payee_bank_name,
        "payee_bank_code":       payee_bank_code,
        "payment_method":        payment_method,
        # ── Invoice ─────────────────────────────────────────────
        "invoice_reference":         invoice_reference,
        "purchase_order_reference":  purchase_order_reference,
        "invoice_date":              invoice_date,
        "invoice_amount":            flt(invoice_amount) if invoice_amount else None,
        "attachment_notes":          attachment_notes,
        # ── Workflow ─────────────────────────────────────────────
        "workflow_state":  "Draft",
        "created_by":      user,
        "created_date":    now_datetime(),
    })

    doc.insert()   # uses Employee's create permission

    return {
        "status":  "success",
        "name":    doc.name,
        "total":   total,
        "message": f"{doc.name} created as Draft. Submit to start approval.",
    }


@frappe.whitelist()
def create_maintenance_request(
    title:                str,
    priority:             str,
    maintenance_type:     str,
    maintenance_category: str,
    location:             str,
    issue_description:    str,
    urgency_level:        str,
    asset:                str   = None,
    preferred_completion_date: str = None,
    estimated_cost:       float = None,
    recommended_vendor:   str   = None,
    description:          str   = None,
    attachment_notes:     str   = None,
):
    """
    Create a Maintenance Request eRequest (workflow_state = Draft).
    All field names match the eRequest DocType exactly.
    """
    user = frappe.session.user
    emp  = _resolve_employee()
    if not emp:
        frappe.throw("Your account is not linked to an Employee record.")

    dept    = frappe.db.get_value("Employee", emp, "department")
    company = (frappe.db.get_value("Employee", emp, "company")
               or frappe.db.get_single_value("Global Defaults", "default_company"))

    doc = frappe.get_doc({
        "doctype":              "eRequest",
        "request_type":         "Maintenance Request",
        "title":                title,
        "priority":             priority,
        "request_date":         today(),
        "requested_by":         user,
        "department":           dept,
        "company":              company,
        "description":          description,
        "maintenance_type":     maintenance_type,
        "maintenance_category": maintenance_category,
        "location":             location,
        "asset":                asset,
        "issue_description":    issue_description,
        "urgency_level":        urgency_level,
        "preferred_completion_date": preferred_completion_date,
        "estimated_cost":       flt(estimated_cost) if estimated_cost else None,
        "recommended_vendor":   recommended_vendor,
        "attachment_notes":     attachment_notes,
        "workflow_state":       "Draft",
        "created_by":           user,
        "created_date":         now_datetime(),
    })

    doc.insert()

    return {
        "status":  "success",
        "name":    doc.name,
        "message": f"{doc.name} created as Draft. Submit to start approval.",
    }


# ─────────────────────────────────────────────────────────────────
# SECTION 3 — WORKFLOW ACTIONS (Submit / Approve / Reject / Cancel)
# ─────────────────────────────────────────────────────────────────

@frappe.whitelist()
def submit_request(name: str):
    """
    Employee submits a Draft eRequest → Pending Manager Approval.
    Writes to workflow_state and calls doctype.submit() to set docstatus=1.
    """
    doc = frappe.get_doc("eRequest", name)

    if doc.requested_by != frappe.session.user:
        frappe.throw("You can only submit your own requests.", frappe.PermissionError)
    if doc.workflow_state != "Draft":
        frappe.throw(f"Cannot submit — current state is '{doc.workflow_state}'.")

    doc.workflow_state      = "Pending Manager Approval"
    doc.last_modified_by    = frappe.session.user
    doc.last_modified_date  = now_datetime()
    doc.save(ignore_permissions=True)
    doc.submit()

    _create_ess_task_for_approver(doc, level="Manager")
    _notify_manager(doc)

    return {"status": "success", "state": doc.workflow_state,
            "message": "Submitted for Manager approval."}


@frappe.whitelist()
def approve_request(name: str, approver_level: str, comments: str = None):
    """
    Approve eRequest at a given level.

    approver_level: "Manager" | "Finance" | "Final"

    Transition map (mirrors workflow_state Select options exactly):
        Manager → Pending Finance Approval
        Finance → Pending Final Approval
        Final   → Approved  (triggers Payment Entry creation)
    """
    TRANSITIONS = {
        "Manager": {
            "required_state": "Pending Manager Approval",
            "next_state":     "Pending Finance Approval",
            "approval_field": "manager_approval",
            "date_field":     "manager_approval_date",
            "comment_field":  "manager_comments",
            "next_level":     "Finance",
        },
        "Finance": {
            "required_state": "Pending Finance Approval",
            "next_state":     "Pending Final Approval",
            "approval_field": "finance_approval",
            "date_field":     "finance_approval_date",
            "comment_field":  "finance_comments",
            "next_level":     "Final",
        },
        "Final": {
            "required_state": "Pending Final Approval",
            "next_state":     "Approved",
            "approval_field": "final_approval",
            "date_field":     "final_approval_date",
            "comment_field":  "final_comments",
            "next_level":     None,
        },
    }

    t = TRANSITIONS.get(approver_level)
    if not t:
        frappe.throw(f"Invalid approver_level '{approver_level}'.")

    doc = frappe.get_doc("eRequest", name)

    if doc.workflow_state != t["required_state"]:
        frappe.throw(
            f"{approver_level} cannot approve — "
            f"current state is '{doc.workflow_state}' "
            f"(expected '{t['required_state']}')."
        )

    doc.set(t["approval_field"], frappe.session.user)
    doc.set(t["date_field"],     now_datetime())
    if comments:
        doc.set(t["comment_field"], comments)

    doc.workflow_state     = t["next_state"]
    doc.last_modified_by   = frappe.session.user
    doc.last_modified_date = now_datetime()
    doc.save(ignore_permissions=True)

    _complete_ess_task(name, approver_level)

    if t["next_level"]:
        _create_ess_task_for_approver(doc, level=t["next_level"])
        _notify_next_approver(doc, t["next_level"])
    else:
        # Fully Approved
        _notify_requester(doc, outcome="Approved")
        if doc.request_type == "Payment Request":
            _auto_create_payment_entry(doc)

    return {"status": "success", "new_state": doc.workflow_state}


@frappe.whitelist()
def reject_request(name: str, rejection_reason: str, approver_level: str = "Manager"):
    """
    Reject eRequest at any approval stage. Writes to rejection_reason field.
    """
    doc = frappe.get_doc("eRequest", name)

    doc.workflow_state     = "Rejected"
    doc.rejection_reason   = rejection_reason   # exact field name from DocType JSON
    doc.last_modified_by   = frappe.session.user
    doc.last_modified_date = now_datetime()
    doc.save(ignore_permissions=True)

    _complete_ess_task(name, approver_level)
    _notify_requester(doc, outcome="Rejected", reason=rejection_reason)

    return {"status": "success", "new_state": "Rejected"}


@frappe.whitelist()
def cancel_request(name: str):
    """Employee cancels their own Draft eRequest."""
    doc = frappe.get_doc("eRequest", name)

    if doc.requested_by != frappe.session.user:
        frappe.throw("You can only cancel your own requests.", frappe.PermissionError)
    if doc.workflow_state != "Draft":
        frappe.throw("Only Draft requests can be cancelled by the employee.")

    doc.workflow_state     = "Cancelled"
    doc.last_modified_by   = frappe.session.user
    doc.last_modified_date = now_datetime()
    doc.save(ignore_permissions=True)

    return {"status": "success", "new_state": "Cancelled"}


# ─────────────────────────────────────────────────────────────────
# SECTION 4 — DOC EVENT HOOKS (called from ess_portal_hooks.py)
# ─────────────────────────────────────────────────────────────────

def on_erequest_submit(doc, method=None):
    """Hook: eRequest.on_submit — ensure approval task exists."""
    if doc.workflow_state == "Pending Manager Approval":
        _create_ess_task_for_approver(doc, level="Manager")


def on_erequest_update(doc, method=None):
    """Hook: eRequest.on_update — notify requester on terminal states."""
    prev = frappe.db.get_value("eRequest", doc.name, "workflow_state")
    if doc.workflow_state != prev and doc.workflow_state in ("Approved", "Rejected", "Cancelled"):
        _notify_requester(doc, outcome=doc.workflow_state,
                         reason=doc.get("rejection_reason"))


def on_erequest_cancel(doc, method=None):
    """Hook: eRequest.on_cancel — clean up open ESS Tasks."""
    tasks = frappe.get_all(
        "ESS Task",
        filters={"linked_doctype": "eRequest", "linked_docname": doc.name, "status": ["!=", "Completed"]},
        pluck="name",
    )
    for t in tasks:
        frappe.db.set_value("ESS Task", t, "status", "Cancelled")


# ─────────────────────────────────────────────────────────────────
# SECTION 5 — PERMISSIONS
# ─────────────────────────────────────────────────────────────────

def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user
    privileged = {"HR Manager", "Finance Manager", "System Manager", "Accounts Manager"}
    if set(frappe.get_roles(user)) & privileged:
        return ""
    return f"`tabERequest`.`requested_by` = {frappe.db.escape(user)}"


def has_permission(doc, ptype, user):
    if doc.requested_by == user:
        return True
    privileged = {"HR Manager", "Finance Manager", "System Manager"}
    return bool(set(frappe.get_roles(user)) & privileged)


# ─────────────────────────────────────────────────────────────────
# SECTION 6 — SCHEDULED JOB
# ─────────────────────────────────────────────────────────────────

def send_pending_approval_reminders():
    """Daily: remind approvers of requests pending > 2 days."""
    from datetime import date, timedelta
    threshold = date.today() - timedelta(days=2)

    pending = frappe.get_all(
        "eRequest",
        filters={
            "workflow_state": ["in", [
                "Pending Manager Approval",
                "Pending Finance Approval",
                "Pending Final Approval",
            ]],
            "modified": ["<", threshold],
        },
        fields=["name", "title", "workflow_state", "requested_by",
                "request_type", "total_amount", "priority", "currency"],
    )

    for req in pending:
        approver = _get_approver_user_for_state(req.workflow_state)
        if not approver:
            continue
        frappe.sendmail(
            recipients=[approver],
            subject=f"[ESS] Reminder: {req.name} Awaiting Your Approval",
            message=f"""
                <p>An eRequest has been waiting for your approval for more than 2 days:</p>
                <ul>
                    <li><strong>Reference:</strong> {req.name}</li>
                    <li><strong>Title:</strong> {req.title}</li>
                    <li><strong>Type:</strong> {req.request_type}</li>
                    <li><strong>Priority:</strong> {req.priority}</li>
                    <li><strong>Status:</strong> {req.workflow_state}</li>
                    {"<li><strong>Amount:</strong> " + req.currency + " " + str(req.total_amount) + "</li>"
                     if req.total_amount else ""}
                </ul>
                <p><a href="{frappe.utils.get_url()}/ess">Open ESS Portal →</a></p>
            """,
            now=False,
        )


# ─────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────

def _resolve_employee():
    return frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")


def _build_timeline(doc) -> list:
    """Build structured approval timeline from eRequest approval chain fields."""
    tl = [{"stage": "Submitted", "status": "done",
           "user": doc.requested_by, "date": str(doc.request_date), "comments": None}]

    # Manager
    if doc.manager_approval:
        tl.append({"stage": "Manager Approval", "status": "done",
                   "user": doc.manager_approval,
                   "date": str(doc.manager_approval_date) if doc.manager_approval_date else None,
                   "comments": doc.manager_comments})
    elif doc.workflow_state == "Pending Manager Approval":
        tl.append({"stage": "Manager Approval", "status": "pending",
                   "user": None, "date": None, "comments": None})

    # Finance
    if doc.finance_approval:
        tl.append({"stage": "Finance Approval", "status": "done",
                   "user": doc.finance_approval,
                   "date": str(doc.finance_approval_date) if doc.finance_approval_date else None,
                   "comments": doc.finance_comments})
    elif doc.workflow_state == "Pending Finance Approval":
        tl.append({"stage": "Finance Approval", "status": "pending",
                   "user": None, "date": None, "comments": None})

    # Final
    if doc.final_approval:
        tl.append({"stage": "Final Approval", "status": "done",
                   "user": doc.final_approval,
                   "date": str(doc.final_approval_date) if doc.final_approval_date else None,
                   "comments": doc.final_comments})
    elif doc.workflow_state == "Pending Final Approval":
        tl.append({"stage": "Final Approval", "status": "pending",
                   "user": None, "date": None, "comments": None})

    # Terminal
    if doc.workflow_state == "Approved":
        tl.append({"stage": "Approved ✓", "status": "approved",
                   "user": doc.final_approval, "date": None, "comments": None})
    elif doc.workflow_state == "Rejected":
        tl.append({"stage": "Rejected ✗", "status": "rejected",
                   "user": None, "date": None, "comments": doc.rejection_reason})
    elif doc.workflow_state == "Cancelled":
        tl.append({"stage": "Cancelled", "status": "cancelled",
                   "user": None, "date": None, "comments": None})

    return tl


def _create_ess_task_for_approver(doc, level: str):
    """Create an ESS Task for the approver at the given level."""
    role_map = {
        "Manager": "HR Manager",
        "Finance": "Finance Manager",
        "Final":   "System Manager",
    }
    role = role_map.get(level)
    if not role:
        return

    # Find the first active user with the required role
    user_rows = frappe.get_all(
        "Has Role",
        filters={"role": role, "parenttype": "User"},
        pluck="parent",
        limit=1,
    )
    if not user_rows:
        return
    approver_user = user_rows[0]
    approver_emp  = frappe.db.get_value("Employee", {"user_id": approver_user}, "name")
    if not approver_emp:
        return

    try:
        frappe.get_doc({
            "doctype":        "ESS Task",
            "assigned_to":    approver_emp,
            "title":          f"Approve eRequest ({level}): {doc.title}",
            "task_category":  "Approval",
            "priority":       doc.priority or "Medium",
            "status":         "Open",
            "linked_doctype": "eRequest",
            "linked_docname": doc.name,
            "assigned_on":    today(),
        }).insert(ignore_permissions=True)
    except Exception as e:
        frappe.logger().warning(f"[ESS eRequest] Could not create ESS Task: {e}")


def _complete_ess_task(erequest_name: str, level: str):
    task = frappe.db.get_value(
        "ESS Task",
        {"linked_doctype": "eRequest", "linked_docname": erequest_name,
         "status": ["!=", "Completed"]},
        "name",
    )
    if task:
        frappe.db.set_value("ESS Task", task, {
            "status":       "Completed",
            "completed_on": now_datetime(),
        })


def _notify_manager(doc):
    mgr_emp  = frappe.db.get_value("Employee", {"user_id": doc.requested_by}, "reports_to")
    mgr_user = frappe.db.get_value("Employee", mgr_emp, "user_id") if mgr_emp else None
    if not mgr_user:
        return
    _send_approval_email(mgr_user, doc, "Manager")


def _notify_next_approver(doc, level: str):
    role_map = {"Finance": "Finance Manager", "Final": "System Manager"}
    role = role_map.get(level)
    if not role:
        return
    users = frappe.get_all("Has Role",
                           filters={"role": role, "parenttype": "User"},
                           pluck="parent", limit=1)
    if users:
        _send_approval_email(users[0], doc, level)


def _send_approval_email(recipient_user: str, doc, level: str):
    amt_line = ""
    if doc.get("total_amount"):
        amt_line = f"<li><strong>Amount:</strong> {doc.get('currency','NGN')} {doc.total_amount:,.2f}</li>"

    frappe.sendmail(
        recipients=[recipient_user],
        subject=f"[ESS] Approval Required ({level}): {doc.title} — {doc.name}",
        message=f"""
            <p>An eRequest requires your approval at the <strong>{level}</strong> stage:</p>
            <ul>
                <li><strong>Reference:</strong> {doc.name}</li>
                <li><strong>Type:</strong> {doc.request_type}</li>
                <li><strong>Title:</strong> {doc.title}</li>
                <li><strong>Priority:</strong> {doc.priority}</li>
                {amt_line}
            </ul>
            <p><a href="{frappe.utils.get_url()}/app/e-request/{doc.name}">
               Review in ERPNext →</a></p>
            <p><a href="{frappe.utils.get_url()}/ess">Open ESS Portal →</a></p>
        """,
        now=False,
    )


def _notify_requester(doc, outcome: str, reason: str = None):
    frappe.sendmail(
        recipients=[doc.requested_by],
        subject=f"[ESS] Your Request has been {outcome}: {doc.name}",
        message=f"""
            <p>Your {doc.request_type} <strong>{doc.name}</strong> —
            <em>{doc.title}</em> — has been <strong>{outcome.upper()}</strong>.</p>
            {f"<p><strong>Reason:</strong> {reason}</p>" if reason else ""}
            <p><a href="{frappe.utils.get_url()}/ess">View in ESS Portal →</a></p>
        """,
        now=False,
    )


def _get_approver_user_for_state(state: str):
    role_map = {
        "Pending Manager Approval": "HR Manager",
        "Pending Finance Approval": "Finance Manager",
        "Pending Final Approval":   "System Manager",
    }
    role = role_map.get(state)
    if not role:
        return None
    rows = frappe.get_all("Has Role",
                          filters={"role": role, "parenttype": "User"},
                          pluck="parent", limit=1)
    return rows[0] if rows else None


def _auto_create_payment_entry(doc):
    """
    When an eRequest (Payment Request type) is fully Approved,
    create a draft Payment Entry linked back via payment_reference field.
    """
    try:
        default_payable = frappe.db.get_value("Company", doc.company, "default_payable_account")

        pe = frappe.get_doc({
            "doctype":              "Payment Entry",
            "payment_type":         "Pay",
            "posting_date":         today(),
            "company":              doc.company,
            "party_type":           "Supplier" if doc.payee_type == "Supplier" else "Employee",
            "party":                doc.supplier or doc.employee,
            "party_name":           doc.payee_name,
            "paid_amount":          doc.total_amount,
            "received_amount":      doc.total_amount,
            "source_exchange_rate": 1,
            "target_exchange_rate": 1,
            "paid_from":            default_payable,
            "paid_to":              doc.payment_account or default_payable,
            "reference_no":         doc.name,
            "reference_date":       today(),
            "remarks":              f"eRequest {doc.name} — {doc.title}",
            "mode_of_payment":      _map_payment_method(doc.payment_method),
        })
        pe.insert(ignore_permissions=True)

        # Write back to eRequest using the exact field names from DocType JSON
        frappe.db.set_value("eRequest", doc.name, {
            "payment_document_created": 1,
            "payment_reference":        pe.name,      # field: payment_reference (Link→Payments)
            "payment_created_date":     now_datetime(),
            "payment_status":           "Processing", # Select: Not Started/Processing/Completed/Failed
        })

        frappe.logger().info(f"[ESS eRequest] Payment Entry {pe.name} created for {doc.name}")

    except Exception as e:
        frappe.logger().error(f"[ESS eRequest] Payment Entry failed for {doc.name}: {e}")


def _map_payment_method(pm: str) -> str:
    return {
        "Bank Transfer":  "Bank",
        "Cheque":         "Cheque",
        "Cash":           "Cash",
        "Mobile Money":   "Mobile Money",
        "Online Payment": "Wire Transfer",
    }.get(pm or "", "Bank")


# ──────────────────────────────────────────────────────────────────────────────
# PORTAL: Generic eRequest creation (called from ESS Portal "New Request" button)
# ──────────────────────────────────────────────────────────────────────────────
@frappe.whitelist()
def create_erequest(request_type: str, subject: str,
                    priority: str = "Medium", description: str = ""):
    """Create a generic eRequest from the ESS portal."""
    emp = _resolve_employee()
    if not emp:
        frappe.throw("No active Employee linked to your account.")

    doc = frappe.new_doc("eRequest")
    doc.requested_by    = frappe.session.user
    doc.employee        = emp.name
    doc.request_type    = request_type
    doc.subject         = subject
    doc.priority        = priority
    doc.description     = description
    doc.workflow_state  = "Draft"

    doc.insert(ignore_permissions=True)

    # Optionally auto-submit so it enters the approval workflow immediately
    try:
        doc.submit()
    except Exception:
        pass  # Leave as draft if workflow prevents immediate submit

    return {
        "name"          : doc.name,
        "workflow_state": doc.workflow_state,
    }