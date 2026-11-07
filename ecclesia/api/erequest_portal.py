"""
ecclesia.erequest/api/portal.py
─────────────────────────────────────────────────────────────────────────────
Portal API endpoints.

AUTH STRATEGY — Standard Frappe Login (same as Supplier/Customer portal)
─────────────────────────────────────────────────────────────────────────
We use frappe.client.login (the same endpoint ERPNext uses for its portal).
This means:
  • No custom password field, no OTP, no Redis tokens
  • The employee's Frappe User account is used directly
  • HR creates a portal-role User linked to the Employee, or the employee
    already has an ERPNext account
  • Frappe sets a secure httpOnly session cookie — all subsequent API calls
    are authenticated through that cookie automatically
  • On the frontend we simply call /api/method/login with {usr, pwd}

The only thing we add on top of standard login is:
  • Verifying the logged-in user is linked to an active Employee record
  • Returning that Employee's details for the portal UI

All data endpoints use @frappe.whitelist() (no allow_guest) so Frappe's
session cookie is checked automatically — exactly like the standard portal.
"""

import frappe
from frappe import _
from frappe.utils import cint


# ═══════════════════════════════════════════════════════════════════════════════
#  AUTH HELPERS  (called after Frappe's own login endpoint)
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist(allow_guest=False)
def get_employee_profile() -> dict:
    """
    Called immediately after a successful Frappe login.
    Returns the Employee record linked to the current logged-in user.
    Throws if no active Employee is found — the portal shows an error.
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
def logout() -> dict:
    """Expire the Frappe session."""
    frappe.local.login_manager.logout()
    return {"status": "logged_out"}


# ═══════════════════════════════════════════════════════════════════════════════
#  REFERENCE DATA
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist(allow_guest=False)
def get_departments() -> list:
    return frappe.get_all(
        "Department",
        filters={"is_group": 0},
        fields=["name"],
        order_by="name asc",
        limit=500,
    )


@frappe.whitelist(allow_guest=False)
def get_companies() -> list:
    return frappe.get_all("Company", fields=["name", "abbr"], order_by="name asc")


# ═══════════════════════════════════════════════════════════════════════════════
#  eREQUEST CRUD
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist(allow_guest=False)
def submit_request(data: str) -> dict:
    """
    Create a new eRequest for the currently logged-in employee.
    `data` — JSON string of field values.
    """
    import json
    try:
        payload = json.loads(data) if isinstance(data, str) else data
    except Exception:
        frappe.throw(_("Invalid request data."))

    user  = frappe.session.user
    emp   = _require_employee(user)

    doc = frappe.new_doc("eRequest")
    _populate_doc(doc, payload, emp, user)
    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status":          "success",
        "name":            doc.name,
        "workflow_state":  doc.workflow_state,
    }


@frappe.whitelist(allow_guest=False)
def get_my_requests(limit: int = 15, offset: int = 0) -> dict:
    """Return paginated eRequests belonging to the current employee."""
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
    """Fetch full detail of a single eRequest (must belong to current user)."""
    user = frappe.session.user
    doc  = frappe.get_doc("eRequest", name)
    if doc.requested_by != user:
        emp = _find_employee_for_user(user)
        # Allow managers / admins to view any request
        approver_roles = {"eRequest Manager","eRequest Finance","eRequest Admin","System Manager"}
        if not approver_roles.intersection(set(frappe.get_roles(user))):
            frappe.throw(_("You do not have access to this request."), frappe.PermissionError)
    return doc.as_dict()


@frappe.whitelist(allow_guest=False)
def upload_attachment(docname: str, fieldname: str) -> dict:
    """Handle file upload — file arrives as multipart form data."""
    if not frappe.request.files:
        frappe.throw(_("No file provided."))

    # Verify ownership or approver role
    user = frappe.session.user
    doc  = frappe.get_doc("eRequest", docname)
    if doc.requested_by != user:
        approver_roles = {"eRequest Manager","eRequest Finance","eRequest Admin","System Manager"}
        if not approver_roles.intersection(set(frappe.get_roles(user))):
            frappe.throw(_("You do not have access to this document."), frappe.PermissionError)

    file_obj = list(frappe.request.files.values())[0]

    file_doc = frappe.get_doc({
        "doctype":              "File",
        "attached_to_doctype":  "eRequest",
        "attached_to_name":     docname,
        "attached_to_field":    fieldname,
        "folder":               "Home/Attachments",
        "is_private":           1,
        "file_name":            file_obj.filename,
        "content":              file_obj.read(),
    })
    file_doc.save(ignore_permissions=True)

    frappe.db.set_value("eRequest", docname, fieldname, file_doc.file_url)
    frappe.db.commit()

    return {"status": "uploaded", "file_url": file_doc.file_url}


# ═══════════════════════════════════════════════════════════════════════════════
#  PRIVATE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _find_employee_for_user(user: str):
    """
    Find an active Employee whose user_id matches the Frappe user.
    Falls back to matching company_email or personal_email.
    """
    # Primary: user_id field on Employee (standard ERPNext link)
    results = frappe.get_all(
        "Employee",
        filters={"user_id": user, "status": "Active"},
        fields=["name","employee_name","department","designation",
                "company","company_email","personal_email","image"],
        limit=1,
    )
    if results:
        return frappe._dict(results[0])

    # Fallback: match by email in company_email or personal_email
    for field in ("company_email", "personal_email"):
        results = frappe.get_all(
            "Employee",
            filters={field: user, "status": "Active"},
            fields=["name","employee_name","department","designation",
                    "company","company_email","personal_email","image"],
            limit=1,
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


def _populate_doc(doc, data: dict, emp, user: str):
    """Safely copy allowed fields from portal payload onto an eRequest doc."""
    ALLOWED = [
        "request_type","priority","title","department","company",
        "cost_center","project","description",
        # Payment
        "payment_due_date","payment_purpose","payment_type","payment_category",
        "currency","payment_amount","tax_amount",
        "payee_type","supplier","employee","payee_name","payee_email","payee_phone",
        "payee_account_number","payee_account_name","payee_bank_name",
        "payee_bank_code","payment_method",
        "invoice_reference","invoice_date","invoice_amount",
        "purchase_order_reference","attachment_notes",
        # Maintenance
        "maintenance_type","maintenance_category","location","asset",
        "issue_description","urgency_level","preferred_completion_date",
        "estimated_cost","recommended_vendor",
    ]
    for field in ALLOWED:
        val = data.get(field)
        if val is not None and val != "":
            doc.set(field, val)

    doc.requested_by  = user
    doc.request_date  = frappe.utils.today()
    doc.company       = doc.company or emp.company
    doc.department    = doc.department or emp.department or ""
    doc.workflow_state = "Draft"
