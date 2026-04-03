# Copyright (c) 2026, Ecclesia and contributors
# For license information, please see license.txt

"""
ecclesia_erequest/doctype/erequest/erequest.py
═══════════════════════════════════════════════════════════════════════════════
Single-file implementation of the eRequest module.

Sections
────────
 1.  Imports & constants
 2.  eRequest Document class  (DocType controller)
 3.  Portal API               (whitelisted, session-authenticated)
 4.  Payment document creation + attachment transfer
 5.  Email notifications      (triggered by hooks doc_events)
 6.  Permission logic         (has_permission hook)
 7.  Scheduler tasks          (daily reminders)
 8.  Post-install setup       (after_install hook)
 9.  Amount-to-words utility

hooks.py references for all callable paths:
  doc_events  → ecclesia_erequest.doctype.erequest.erequest.on_update
                ecclesia_erequest.doctype.erequest.erequest.on_cancel
  has_permission → ecclesia_erequest.doctype.erequest.erequest.has_permission
  scheduler   → ecclesia_erequest.doctype.erequest.erequest.send_pending_approval_reminders
  after_install → ecclesia_erequest.doctype.erequest.erequest.after_install
"""

import json
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import (
    now_datetime, flt, today, nowdate,
    money_in_words, add_days, get_url, cint,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

# Roles allowed to see all eRequests (not just their own)
APPROVER_ROLES = frozenset({
    "eRequest Manager",
    "eRequest Finance",
    "eRequest Admin",
    "System Manager",
})

# Roles allowed to create Payments documents
FINANCE_ROLES = frozenset({
    "eRequest Finance",
    "eRequest Admin",
    "System Manager",
})

# eRequest.payment_type  →  Payments.trans_type
TRANS_TYPE_MAP = {
    "Vendor Payment":         "Supplier Payment",
    "Employee Reimbursement": "Expense Payment",
    "Utility Payment":        "Expense Payment",
    "Tax Payment":            "Expense Payment",
    "Salary Advance":         "Expense Payment",
    "Petty Cash":             "Expense Payment",
    "Other":                  "Expense Payment",
}

# eRequest.payment_category  →  Payments.cashflow_type
CASHFLOW_MAP = {
    "Operational Expense": "Operating costs",
    "Capital Expenditure": "Capital expenditures",
    "Reimbursement":       "Salary payments",
    "Salary & Benefits":   "Salary payments",
    "Taxes":               "Tax Payment",
    "Other":               "Operating costs",
}

# eRequest.payment_method  →  Payments.mode_of_payment (Link → Mode of Payment)
MODE_MAP = {
    "Bank Transfer":  "Bank Transfer",
    "Cheque":         "Cheque",
    "Cash":           "Cash",
    "Mobile Money":   "Bank Transfer",
    "Online Payment": "Bank Transfer",
}

# Roles created on install
_ROLES = [
    {"role_name": "eRequest Employee", "desk_access": 0},
    {"role_name": "eRequest Manager",  "desk_access": 1},
    {"role_name": "eRequest Finance",  "desk_access": 1},
    {"role_name": "eRequest Admin",    "desk_access": 1},
]


# ═══════════════════════════════════════════════════════════════════════════════
# 2. DOCUMENT CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class eRequest(Document):
    """
    eRequest DocType controller.

    Workflow states are NOT hardcoded here — they are driven entirely by
    Frappe's Workflow engine configured per-company in the UI.  The controller
    only handles calculations, validation, audit-trail stamping, and utility
    methods invoked by custom desk buttons.
    """

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def before_insert(self):
        self.created_by   = frappe.session.user
        self.created_date = now_datetime()

    def before_save(self):
        self.last_modified_by   = frappe.session.user
        self.last_modified_date = now_datetime()
        self._calculate_totals()
        self._set_amount_in_words()

    def validate(self):
        self._validate_mandatory_fields()
        self._validate_amounts()
        self._warn_past_due_date()

    # NOTE: on_submit / on_cancel are intentionally left to the Frappe Workflow.
    # Never set workflow_state here; Workflow Actions handle all transitions.

    # ── Calculations ───────────────────────────────────────────────────────────

    def _calculate_totals(self):
        if self.request_type == "Payment Request":
            self.total_amount = flt(self.payment_amount) + flt(self.tax_amount)
        else:
            self.total_amount = 0

    def _set_amount_in_words(self):
        if self.request_type == "Payment Request" and flt(self.total_amount) > 0:
            try:
                self.amount_in_words = money_in_words(
                    self.total_amount, self.currency or "NGN"
                )
            except Exception:
                self.amount_in_words = _amount_to_words(
                    self.total_amount, self.currency or "NGN"
                )
        else:
            self.amount_in_words = ""

    # ── Validation ─────────────────────────────────────────────────────────────

    def _validate_mandatory_fields(self):
        if self.request_type == "Payment Request":
            for field, label in [
                ("payment_due_date",      "Payment Due Date"),
                ("payment_purpose",       "Payment Purpose"),
                ("payment_amount",        "Payment Amount"),
                ("payee_type",            "Payee Type"),
                ("payee_name",            "Payee Name"),
                ("payee_account_number",  "Account Number"),
                ("payee_account_name",    "Account Name"),
                ("payee_bank_name",       "Bank Name"),
            ]:
                if not self.get(field):
                    frappe.throw(
                        _("{0} is required for Payment Requests.").format(_(label))
                    )

        elif self.request_type == "Maintenance Request":
            for field, label in [
                ("maintenance_type",     "Maintenance Type"),
                ("maintenance_category", "Maintenance Category"),
                ("location",             "Location"),
                ("issue_description",    "Issue Description"),
            ]:
                if not self.get(field):
                    frappe.throw(
                        _("{0} is required for Maintenance Requests.").format(_(label))
                    )

    def _validate_amounts(self):
        if self.request_type == "Payment Request":
            if flt(self.payment_amount) <= 0:
                frappe.throw(_("Payment Amount must be greater than zero."))
            if flt(self.tax_amount) < 0:
                frappe.throw(_("Tax/Deduction Amount cannot be negative."))

    def _warn_past_due_date(self):
        if self.request_type == "Payment Request" and self.payment_due_date:
            if str(self.payment_due_date) < str(today()):
                frappe.msgprint(
                    _("Payment Due Date is in the past. Please verify."),
                    indicator="orange",
                    alert=True,
                )

    # ── Desk button methods ────────────────────────────────────────────────────

    @frappe.whitelist()
    def record_approval(self, level, comments=""):
        """
        Stamp the approval chain fields for the given level.
        level: 'manager' | 'finance' | 'final'

        The Workflow Action button (rendered by Frappe) drives the actual
        state transition.  This only records who approved and when.
        """
        level = (level or "").lower()
        field_map = {
            "manager": ("manager_approval", "manager_approval_date", "manager_comments"),
            "finance": ("finance_approval",  "finance_approval_date",  "finance_comments"),
            "final":   ("final_approval",    "final_approval_date",    "final_comments"),
        }
        if level not in field_map:
            frappe.throw(_("Invalid approval level: {0}").format(level))

        user_f, date_f, comment_f = field_map[level]
        frappe.db.set_value("eRequest", self.name, {
            user_f:    frappe.session.user,
            date_f:    now_datetime(),
            comment_f: comments or "",
        })
        frappe.db.commit()
        return {"status": "recorded", "level": level, "user": frappe.session.user}

    @frappe.whitelist()
    def record_rejection(self, reason=""):
        """Store rejection reason. Workflow Action handles the state change."""
        if not reason:
            frappe.throw(_("A rejection reason is required."))
        frappe.db.set_value("eRequest", self.name, "rejection_reason", reason)
        frappe.db.commit()
        return {"status": "recorded"}

    @frappe.whitelist()
    def create_payment_document(self):
        """
        Create a Payments document from this Approved Payment Request and
        transfer all attachments.  Called by the 'Create Payment Document'
        desk button — never auto-triggered.
        """
        return create_payment_document(self.name)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. PORTAL API  — whitelisted endpoints consumed by the employee web portal
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_supplier_details(supplier):
    """Return supplier name for auto-fill on the desk form."""
    if not supplier:
        return {}
    try:
        return {
            "supplier_name": frappe.db.get_value(
                "Supplier", supplier, "supplier_name"
            ) or ""
        }
    except Exception:
        return {}


@frappe.whitelist()
def get_employee_details(employee):
    """Return employee name + department for auto-fill on the desk form."""
    if not employee:
        return {}
    try:
        doc = frappe.get_doc("Employee", employee)
        return {
            "employee_name": doc.employee_name or "",
            "department":    doc.department    or "",
        }
    except Exception:
        return {}


@frappe.whitelist(allow_guest=False)
def get_employee_profile() -> dict:
    """
    Portal: return the Employee record linked to the current session user.
    Called immediately after the Frappe login redirect succeeds.
    """
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("Not authenticated."), frappe.AuthenticationError)

    emp = _find_employee_for_user(user)
    if not emp:
        frappe.throw(
            _("No active Employee record is linked to your account. "
              "Please contact HR."),
            frappe.PermissionError,
        )
    return {
        "name":          emp.name,
        "employee_name": emp.employee_name,
        "department":    emp.department,
        "designation":   emp.designation,
        "company":       emp.company,
        "image":         emp.image or "",
        "user":          user,
    }


@frappe.whitelist(allow_guest=False)
def portal_logout() -> dict:
    """Portal: expire the Frappe session."""
    frappe.local.login_manager.logout()
    return {"status": "logged_out"}


@frappe.whitelist(allow_guest=False)
def get_departments() -> list:
    """Portal: return active departments for the dropdown."""
    return frappe.get_all(
        "Department",
        filters={"is_group": 0},
        fields=["name"],
        order_by="name asc",
        limit=500,
    )


@frappe.whitelist(allow_guest=False)
def get_companies() -> list:
    """Portal: return companies for the dropdown."""
    return frappe.get_all(
        "Company", fields=["name", "abbr"], order_by="name asc"
    )


@frappe.whitelist(allow_guest=False)
def submit_request(data: str) -> dict:
    """
    Portal: create a new eRequest for the currently logged-in employee.
    `data` is a JSON string of field values from the portal form.
    """
    try:
        payload = json.loads(data) if isinstance(data, str) else data
    except Exception:
        frappe.throw(_("Invalid request data."))

    user = frappe.session.user
    emp  = _require_employee(user)

    doc = frappe.new_doc("eRequest")
    _populate_doc(doc, payload, emp, user)
    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status":         "success",
        "name":           doc.name,
        "workflow_state": doc.workflow_state,
    }


@frappe.whitelist(allow_guest=False)
def get_my_requests(limit: int = 15, offset: int = 0) -> dict:
    """Portal: return paginated eRequests belonging to the current employee."""
    user    = frappe.session.user
    filters = {"requested_by": user}
    total   = frappe.db.count("eRequest", filters)
    rows    = frappe.get_all(
        "eRequest",
        filters=filters,
        fields=[
            "name", "title", "request_type", "workflow_state", "priority",
            "request_date", "payment_amount", "total_amount", "currency",
            "department", "urgency_level", "maintenance_type",
            "payment_due_date", "modified",
        ],
        order_by="modified desc",
        limit=cint(limit),
        start=cint(offset),
    )
    return {"total": total, "rows": rows}


@frappe.whitelist(allow_guest=False)
def get_request_detail(name: str) -> dict:
    """Portal: return full detail of a single eRequest."""
    user = frappe.session.user
    doc  = frappe.get_doc("eRequest", name)
    if doc.requested_by != user:
        if not APPROVER_ROLES.intersection(set(frappe.get_roles(user))):
            frappe.throw(
                _("You do not have access to this request."),
                frappe.PermissionError,
            )
    return doc.as_dict()


@frappe.whitelist(allow_guest=False)
def upload_attachment(docname: str, fieldname: str) -> dict:
    """Portal: receive a multipart file upload and attach it to an eRequest."""
    if not frappe.request.files:
        frappe.throw(_("No file provided."))

    user = frappe.session.user
    doc  = frappe.get_doc("eRequest", docname)
    if doc.requested_by != user:
        if not APPROVER_ROLES.intersection(set(frappe.get_roles(user))):
            frappe.throw(
                _("You do not have access to this document."),
                frappe.PermissionError,
            )

    file_obj = list(frappe.request.files.values())[0]
    file_doc = frappe.get_doc({
        "doctype":             "File",
        "attached_to_doctype": "eRequest",
        "attached_to_name":    docname,
        "attached_to_field":   fieldname,
        "folder":              "Home/Attachments",
        "is_private":          1,
        "file_name":           file_obj.filename,
        "content":             file_obj.read(),
    })
    file_doc.save(ignore_permissions=True)
    frappe.db.set_value("eRequest", docname, fieldname, file_doc.file_url)
    frappe.db.commit()
    return {"status": "uploaded", "file_url": file_doc.file_url}


# ═══════════════════════════════════════════════════════════════════════════════
# 4. PAYMENT DOCUMENT CREATION + ATTACHMENT TRANSFER
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def create_payment_document(erequest_name: str) -> dict:
    """
    Create a Payments document (custom Ecclesia DocType) from an Approved
    eRequest, then transfer all attachments across.

    Field mapping  eRequest → Payments
    ────────────────────────────────────
    company              → company
    payment_due_date     → transaction_date
    payment_type         → trans_type          (via TRANS_TYPE_MAP)
    currency             → payment_currency
    total_amount (NGN)   → amount_paid
    total_amount (FC)    → amount_paid_in_fc
    total_amount         → local_currency_amount
    payment_method       → mode_of_payment     (via MODE_MAP)
    invoice_reference    → reference_no
    payment_purpose      → transaction_purposes
    department           → department
    cost_center          → cost_center
    project              → project
    supplier             → payee_id            (Supplier only)
    payee_name           → payee_name
    payment_category     → cashflow_type       (via CASHFLOW_MAP)
    name                 → approval_doc
    """
    if not FINANCE_ROLES.intersection(set(frappe.get_roles())):
        frappe.throw(_("Only Finance or Admin roles can create payment documents."))

    ereq = frappe.get_doc("eRequest", erequest_name)

    if ereq.request_type != "Payment Request":
        frappe.throw(_("Only Payment Requests can generate a Payments document."))

    if ereq.workflow_state != "Approved":
        frappe.throw(_(
            "Payments document can only be created for Approved requests. "
            "Current status: {0}"
        ).format(ereq.workflow_state))

    if ereq.payment_document_created:
        frappe.throw(_(
            "A Payments document already exists for this request: {0}"
        ).format(ereq.payment_reference))

    pay = _build_payments_doc(ereq)
    pay.insert(ignore_permissions=True)

    result = transfer_attachments(
        from_doctype="eRequest",
        from_name=erequest_name,
        to_doctype="Payments",
        to_name=pay.name,
    )

    frappe.db.set_value("eRequest", erequest_name, {
        "payment_document_created": 1,
        "payment_reference":        pay.name,
        "payment_created_date":     now_datetime(),
        "payment_status":           "Processing",
    })
    frappe.db.commit()

    return {
        "payment_doc":             pay.name,
        "attachments_transferred": result["transferred"],
        "attachments_skipped":     result["skipped"],
        "status":                  "created",
    }


@frappe.whitelist()
def transfer_attachments(
    from_doctype: str,
    from_name:    str,
    to_doctype:   str,
    to_name:      str,
) -> dict:
    """
    Copy all File records from from_doctype/from_name to to_doctype/to_name
    by sharing the same file_url — zero extra storage used.

    Whitelisted so Finance can re-run a transfer manually if files were
    added to the eRequest after the Payments document was already created.

    Returns {"transferred": int, "skipped": int, "errors": [str]}
    """
    attachments = frappe.get_all(
        "File",
        filters={
            "attached_to_doctype": from_doctype,
            "attached_to_name":    from_name,
        },
        fields=[
            "name", "file_name", "file_url", "file_size",
            "file_type", "is_private", "content_hash",
        ],
        order_by="creation asc",
    )

    transferred = 0
    skipped     = 0
    errors      = []

    for att in attachments:
        if not att.file_url:
            skipped += 1
            continue

        # Idempotency: skip if already on the target document
        if frappe.db.exists("File", {
            "attached_to_doctype": to_doctype,
            "attached_to_name":    to_name,
            "file_url":            att.file_url,
        }):
            skipped += 1
            continue

        try:
            frappe.get_doc({
                "doctype":             "File",
                "file_name":           att.file_name,
                "file_url":            att.file_url,
                "file_size":           att.file_size    or 0,
                "file_type":           att.file_type    or "",
                "content_hash":        att.content_hash or "",
                "is_private":          att.is_private,
                "folder":              "Home/Attachments",
                "attached_to_doctype": to_doctype,
                "attached_to_name":    to_name,
            }).insert(ignore_permissions=True, ignore_if_duplicate=True)
            transferred += 1
        except Exception:
            last = frappe.get_traceback().splitlines()[-1]
            errors.append(f"'{att.file_name}': {last}")
            frappe.log_error(
                message=frappe.get_traceback(),
                title=f"eRequest attachment transfer failed: {att.file_name} → {to_doctype}/{to_name}",
            )

    if transferred:
        frappe.db.commit()

    return {"transferred": transferred, "skipped": skipped, "errors": errors}


# ═══════════════════════════════════════════════════════════════════════════════
# 5. EMAIL NOTIFICATIONS  — called by hooks.py doc_events
# ═══════════════════════════════════════════════════════════════════════════════

def on_update(doc, method=None):
    """
    Triggered on every save.  Routes email to the correct next approver
    or back to the requestor depending on the current workflow_state.

    Because workflow_state names are configurable per-company, we check
    using case-insensitive substring matching rather than exact equality.
    """
    state = (doc.workflow_state or "").lower()

    if "manager" in state and "pending" in state:
        _notify_role(doc, "eRequest Manager", "Manager")

    elif "finance" in state and "pending" in state:
        _notify_role(doc, "eRequest Finance", "Finance")
        _notify_requestor(
            doc,
            "Your request has been approved by the manager and is now with Finance.",
        )

    elif "final" in state and "pending" in state:
        _notify_role(doc, "eRequest Admin", "Final Approver")
        _notify_requestor(
            doc,
            "Your request has been approved by Finance and is pending final approval.",
        )

    elif state == "approved":
        _notify_requestor(
            doc,
            f"🎉 Your request <b>{doc.name}</b> — <i>{doc.title}</i> — "
            f"has been fully <b>Approved</b>.",
        )

    elif state == "rejected":
        reason = doc.rejection_reason or "No reason provided."
        _notify_requestor(
            doc,
            f"Your request <b>{doc.name}</b> — <i>{doc.title}</i> — "
            f"has been <b>Rejected</b>.<br><br>Reason: {reason}",
            subject_prefix="Request Rejected",
        )


def on_cancel(doc, method=None):
    _notify_requestor(doc, f"Your request {doc.name} has been cancelled.")


# ═══════════════════════════════════════════════════════════════════════════════
# 6. PERMISSION LOGIC  — registered in hooks.py has_permission
# ═══════════════════════════════════════════════════════════════════════════════

def has_permission(doc, ptype="read", user=None):
    """
    Employees may only read/write their own requests.
    Managers, Finance, Admin, and System Manager see all.
    """
    user = user or frappe.session.user
    if user == "Administrator":
        return True

    roles = frappe.get_roles(user)

    if APPROVER_ROLES.intersection(roles):
        return True

    if "eRequest Employee" in roles:
        return doc.requested_by == user

    return False


# ═══════════════════════════════════════════════════════════════════════════════
# 7. SCHEDULER TASKS  — registered in hooks.py scheduler_events
# ═══════════════════════════════════════════════════════════════════════════════

def send_pending_approval_reminders():
    """
    Runs daily.  Sends a reminder email to approvers for any eRequest
    that has been waiting in a pending state for more than 2 days.
    """
    cutoff = add_days(today(), -2)

    # State-to-role mapping: generic keywords so it works with any workflow name
    pending_checks = [
        ("manager",  "eRequest Manager"),
        ("finance",  "eRequest Finance"),
        ("final",    "eRequest Admin"),
    ]

    for keyword, role in pending_checks:
        # Pull all requests whose state contains the keyword and 'pending'
        all_pending = frappe.get_all(
            "eRequest",
            filters={"modified": ["<", cutoff]},
            fields=["name", "title", "requested_by", "priority",
                    "request_date", "workflow_state"],
        )
        old_requests = [
            r for r in all_pending
            if "pending" in (r.workflow_state or "").lower()
            and keyword in (r.workflow_state or "").lower()
        ]
        if not old_requests:
            continue

        approvers = [
            r.parent for r in frappe.get_all(
                "Has Role",
                filters={"role": role, "parenttype": "User"},
                fields=["parent"],
            )
        ]
        if not approvers:
            continue

        rows_html = "".join(
            f"<tr>"
            f"<td>{r.name}</td>"
            f"<td>{r.title}</td>"
            f"<td>{r.priority}</td>"
            f"<td>{r.request_date}</td>"
            f"<td><a href='{get_url()}/app/erequest/{r.name}'>Open</a></td>"
            f"</tr>"
            for r in old_requests
        )

        frappe.sendmail(
            recipients=approvers,
            subject=f"[eRequest] Reminder: {len(old_requests)} Request(s) Awaiting Your Approval",
            message=f"""
                <p>The following requests have been waiting for your approval
                for more than 2 days:</p>
                <table border="1" cellpadding="6" cellspacing="0"
                       style="border-collapse:collapse;width:100%">
                  <thead style="background:#f3f4f6">
                    <tr>
                      <th>Ref</th><th>Title</th><th>Priority</th>
                      <th>Date</th><th>Link</th>
                    </tr>
                  </thead>
                  <tbody>{rows_html}</tbody>
                </table>
                <p>Please review and take action at your earliest convenience.</p>
            """,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 8. POST-INSTALL SETUP  — called by hooks.py after_install
# ═══════════════════════════════════════════════════════════════════════════════

def after_install():
    """Create required roles if they don't already exist."""
    for r in _ROLES:
        if not frappe.db.exists("Role", r["role_name"]):
            doc = frappe.new_doc("Role")
            doc.role_name   = r["role_name"]
            doc.desk_access = r["desk_access"]
            doc.insert(ignore_permissions=True)
            frappe.logger().info(f"eRequest: created role '{r['role_name']}'")
    frappe.db.commit()
    frappe.logger().info("ecclesia_erequest: after_install completed.")


# ═══════════════════════════════════════════════════════════════════════════════
# 9. PRIVATE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

# ── Employee lookup ────────────────────────────────────────────────────────────

def _find_employee_for_user(user: str):
    """
    Return the active Employee linked to this Frappe user.
    Tries user_id first (standard ERPNext link), then falls back to
    matching company_email or personal_email.
    """
    _fields = [
        "name", "employee_name", "department", "designation",
        "company", "company_email", "personal_email", "image",
    ]
    for filters in (
        {"user_id": user, "status": "Active"},
        {"company_email": user, "status": "Active"},
        {"personal_email": user, "status": "Active"},
    ):
        results = frappe.get_all(
            "Employee", filters=filters, fields=_fields, limit=1
        )
        if results:
            return frappe._dict(results[0])
    return None


def _require_employee(user: str):
    emp = _find_employee_for_user(user)
    if not emp:
        frappe.throw(
            _("No active Employee record linked to your account."),
            frappe.PermissionError,
        )
    return emp


# ── Portal doc population ──────────────────────────────────────────────────────

def _populate_doc(doc, data: dict, emp, user: str):
    """Safely copy allowed portal fields onto a new eRequest document."""
    ALLOWED = [
        "request_type", "priority", "title", "department", "company",
        "cost_center", "project", "description",
        # Payment
        "payment_due_date", "payment_purpose", "payment_type", "payment_category",
        "currency", "payment_amount", "tax_amount",
        "payee_type", "supplier", "employee", "payee_name",
        "payee_email", "payee_phone",
        "payee_account_number", "payee_account_name",
        "payee_bank_name", "payee_bank_code", "payment_method",
        "invoice_reference", "invoice_date", "invoice_amount",
        "purchase_order_reference", "attachment_notes",
        # Maintenance
        "maintenance_type", "maintenance_category", "location", "asset",
        "issue_description", "urgency_level",
        "preferred_completion_date", "estimated_cost", "recommended_vendor",
    ]
    for field in ALLOWED:
        val = data.get(field)
        if val is not None and val != "":
            doc.set(field, val)

    doc.requested_by   = user
    doc.request_date   = today()
    doc.company        = doc.company    or emp.company
    doc.department     = doc.department or emp.department or ""
    doc.workflow_state = "Draft"


# ── Payments doc builder ───────────────────────────────────────────────────────

def _build_payments_doc(ereq) -> "frappe.Document":
    """Construct (but do not insert) a Payments document from an eRequest."""
    currency    = ereq.currency or "NGN"
    is_ngn      = currency == "NGN"
    paid_amount = flt(ereq.total_amount or ereq.payment_amount)

    trans_type = TRANS_TYPE_MAP.get(ereq.payment_type or "", "Expense Payment")
    # Supplier Payment requires a linked supplier; fall back if none
    if trans_type == "Supplier Payment" and not ereq.supplier:
        trans_type = "Expense Payment"

    cashflow = CASHFLOW_MAP.get(ereq.payment_category or "", "Operating costs")
    mode     = MODE_MAP.get(ereq.payment_method or "", "Bank Transfer")

    pay = frappe.new_doc("Payments")
    pay.transaction_date          = ereq.payment_due_date or ereq.request_date or nowdate()
    pay.trans_type                = trans_type
    pay.company                   = ereq.company
    pay.payment_status            = "Draft"
    pay.payee_name                = ereq.payee_name or ""
    if ereq.payee_type == "Supplier" and ereq.supplier:
        pay.payee_id              = ereq.supplier
    pay.department                = ereq.department  or ""
    pay.cost_center               = ereq.cost_center or ""
    pay.project                   = ereq.project     or ""
    pay.payment_currency          = currency
    pay.exchange_rate             = 1
    pay.amount_paid               = paid_amount if is_ngn     else 0
    pay.amount_paid_in_fc         = paid_amount if not is_ngn else 0
    pay.local_currency_amount     = paid_amount
    pay.mode_of_payment           = mode
    pay.reference_no              = ereq.invoice_reference or ereq.name
    pay.transaction_purposes      = (
        ereq.payment_purpose or ereq.description or ereq.title or ""
    )
    pay.cashflow_type             = cashflow
    pay.approval_doc              = ereq.name
    pay.create_accounting_entries = 1
    pay.deduct_wht                = 0
    pay.is_multi_line             = 0
    pay.is_shared_cost            = 0
    pay.is_related_coy_trans      = 0
    return pay


# ── Notification helpers ───────────────────────────────────────────────────────

def _desk_link(doc) -> str:
    return f"{get_url()}/app/erequest/{doc.name}"


def _portal_link(doc) -> str:
    return f"{get_url()}/erequest-portal?view=detail&name={doc.name}"


def _notify_requestor(doc, message: str, subject_prefix: str = "Request Update"):
    recipient = doc.requested_by
    if not recipient:
        return
    try:
        frappe.sendmail(
            recipients=[recipient],
            subject=f"[eRequest] {subject_prefix}: {doc.name}",
            template="request_update",
            args={
                "employee_name": doc.requested_by,
                "message":       message,
                "doc_name":      doc.name,
                "doc_title":     doc.title,
                "portal_link":   _portal_link(doc),
            },
        )
    except Exception as e:
        frappe.log_error(str(e), "eRequest Notification Error")


def _notify_role(doc, role: str, role_label: str):
    """Send an approval-required email to all users holding `role`."""
    recipients = [
        r.parent for r in frappe.get_all(
            "Has Role",
            filters={"role": role, "parenttype": "User"},
            fields=["parent"],
        )
    ]
    if not recipients:
        frappe.log_error(
            f"No users with role '{role}' found.",
            "eRequest Notification",
        )
        return
    try:
        frappe.sendmail(
            recipients=recipients,
            subject=f"[eRequest] {role_label} Approval Required: {doc.name}",
            template="approval_request",
            args={
                "approver_role": role_label,
                "doc_name":      doc.name,
                "doc_title":     doc.title,
                "requested_by":  doc.requested_by,
                "request_type":  doc.request_type,
                "priority":      doc.priority,
                "desk_link":     _desk_link(doc),
            },
        )
    except Exception as e:
        frappe.log_error(str(e), "eRequest Notification Error")


# ── Amount to words fallback ───────────────────────────────────────────────────

def _amount_to_words(amount: float, currency: str = "NGN") -> str:
    """
    Pure-Python fallback for money_in_words when Frappe's version fails.
    Supports NGN (Naira/Kobo), USD (Dollar/Cent), GBP (Pound/Penny).
    """
    ones = [
        "", "One", "Two", "Three", "Four", "Five", "Six", "Seven",
        "Eight", "Nine", "Ten", "Eleven", "Twelve", "Thirteen",
        "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen",
    ]
    tens = [
        "", "", "Twenty", "Thirty", "Forty", "Fifty",
        "Sixty", "Seventy", "Eighty", "Ninety",
    ]

    def _below_thousand(n):
        if n == 0:
            return ""
        if n < 20:
            return ones[n]
        if n < 100:
            return tens[n // 10] + (" " + ones[n % 10] if n % 10 else "")
        rem = _below_thousand(n % 100)
        return ones[n // 100] + " Hundred" + (" and " + rem if rem else "")

    def _convert(n):
        if n == 0:
            return "Zero"
        parts = []
        for divisor, label in (
            (1_000_000_000, "Billion"),
            (1_000_000,     "Million"),
            (1_000,         "Thousand"),
        ):
            chunk, n = divmod(n, divisor)
            if chunk:
                parts.append(_below_thousand(chunk) + " " + label)
        if n:
            parts.append(_below_thousand(n))
        return " ".join(parts)

    whole = int(amount)
    frac  = round((amount - whole) * 100)
    major, minor = {
        "NGN": ("Naira", "Kobo"),
        "USD": ("Dollar", "Cent"),
        "GBP": ("Pound", "Penny"),
    }.get(currency, (currency, "Cents"))

    result = _convert(whole) + " " + major
    if frac:
        result += " and " + _convert(frac) + " " + minor
    return result + " Only"
