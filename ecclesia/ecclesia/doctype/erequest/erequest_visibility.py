# Copyright (c) 2026, Ecclesia and contributors
# For license information, please see license.txt

"""
ecclesia/ecclesia/doctype/erequest/erequest_visibility.py
═══════════════════════════════════════════════════════════════════════════════
Standalone record-level visibility for eRequest.

RULES
─────
 1. Requester (requested_by / owner) sees ONLY their own requests.
 2. Manager  sees a request only when:
        • it is Pending Manager Approval AND the requester is within the
          manager's scope (reports to them and/or same department), or
        • they personally acted on it.
 3. Finance  sees a request only when:
        • it is Pending Finance Approval, or
        • it is an Approved Payment Request (needed to create the Payments
          document), or
        • they personally acted on it.
 4. Final approver (eRequest Admin) sees a request only when:
        • it is Pending Final Approval, or
        • they personally acted on it.
 5. System Manager / Administrator see everything.
 6. Nobody else sees anything else.

NOTES ON THIS VERSION
─────────────────────
 A. The document-level check reads PERSISTED values from the database, not the
    in-memory doc. apply_workflow() puts the NEXT state on the in-memory doc
    before it saves, so judging the in-memory doc denied an approver the moment
    their own Approve/Reject click moved the request on.

 B. "Personally acted" also uses the "Workflow" comment Frappe writes on every
    transition (owner = the acting user). Workflow Action rows exist only when the
    Workflow has email alerts enabled, and manager_approval / finance_approval /
    final_approval are stamped only when the desk button or the pending popup is
    used, so approvers could lose sight of requests they had just approved.

 C. The set of known workflow states is cached for the duration of a request
    (it used to be re-queried several times for every list view and count).

WIRING (hooks.py)
─────────────────
    permission_query_conditions = {
        "eRequest": "ecclesia.ecclesia.doctype.erequest.erequest_visibility.get_permission_query_conditions",
    }
    has_permission = {
        "eRequest": "ecclesia.ecclesia.doctype.erequest.erequest_visibility.has_permission",
    }

Portal endpoints in erequest.py call `can_view(doc, user)` (doc may be a name or a
Document); the signature is unchanged.
"""

import frappe
from frappe import _


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

DOCTYPE = "eRequest"
TABLE   = "`tabeRequest`"

ROLE_MANAGER = "eRequest Manager"
ROLE_FINANCE = "eRequest Finance"
ROLE_FINAL   = "eRequest Admin"

# Roles that bypass all restrictions
SUPERUSER_ROLES = frozenset({"System Manager"})

# How a Manager is tied to a requester:
#   "reports_to"  → requester's Employee.reports_to == manager's Employee
#   "department"  → request.department == manager's Employee.department
#   "both"        → either of the above
#   "none"        → every eRequest Manager sees every pending-manager request
MANAGER_SCOPE = "both"

# Finance can see fully Approved Payment Requests (to create Payments docs)
FINANCE_SEES_APPROVED_PAYMENTS = True

# stage keyword → (role, approver field stamped on the doc)
_STAGES = {
    "manager": (ROLE_MANAGER, "manager_approval"),
    "finance": (ROLE_FINANCE, "finance_approval"),
    "final":   (ROLE_FINAL,   "final_approval"),
}

# Persisted columns the document-level check needs
_FIELDS = [
    "owner", "requested_by", "department", "workflow_state", "request_type",
    "manager_approval", "finance_approval", "final_approval", "modified_by",
]


# ═══════════════════════════════════════════════════════════════════════════════
# 2. SHARED HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _is_superuser(user: str, roles) -> bool:
    return user == "Administrator" or bool(SUPERUSER_ROLES.intersection(roles))


def _known_states() -> set:
    """
    All workflow state names for eRequest: from the active Workflow(s) plus
    the workflow_state Select options.  Names are configurable per company,
    so stages are detected by keyword, never by hardcoded equality.

    Cached on frappe.local, so it is computed once per request.
    """
    cached = getattr(frappe.local, "_erq_known_states", None)
    if cached is not None:
        return cached

    states = set()
    for wf in frappe.get_all(
        "Workflow",
        filters={"document_type": DOCTYPE, "is_active": 1},
        pluck="name",
    ):
        states.update(
            frappe.get_all(
                "Workflow Document State", filters={"parent": wf}, pluck="state"
            )
        )
    try:
        opts = frappe.get_meta(DOCTYPE).get_field("workflow_state").options or ""
        states.update(o.strip() for o in opts.split("\n") if o.strip())
    except Exception:
        pass

    result = {s for s in states if s}
    frappe.local._erq_known_states = result
    return result


def _pending_states(keyword: str) -> list:
    return [
        s for s in _known_states()
        if "pending" in s.lower() and keyword in s.lower()
    ]


def _approved_states() -> list:
    return [s for s in _known_states() if s.lower() == "approved"]


def _stage_of(state: str):
    s = (state or "").lower()
    if "pending" not in s:
        return None
    for kw in _STAGES:
        if kw in s:
            return kw
    return None


def _my_employee(user: str):
    return frappe.db.get_value(
        "Employee",
        {"user_id": user, "status": "Active"},
        ["name", "department"],
        as_dict=True,
    )


def _in_sql(values: list) -> str:
    return "(" + ", ".join(frappe.db.escape(v) for v in values) + ")"


def _has_acted(name: str, user: str) -> bool:
    """True if `user` moved this request through the workflow."""
    # Frappe adds a "Workflow" comment (owner = acting user) on every transition.
    if frappe.db.exists(
        "Comment",
        {
            "reference_doctype": DOCTYPE,
            "reference_name": name,
            "comment_type": "Workflow",
            "owner": user,
        },
    ):
        return True
    # completed_by only — NOT `user`, because Frappe creates an Open Workflow
    # Action for EVERY user holding the transition role.
    return bool(
        frappe.db.exists(
            "Workflow Action",
            {
                "reference_doctype": DOCTYPE,
                "reference_name": name,
                "completed_by": user,
            },
        )
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 3. LIST-LEVEL FILTER  (permission_query_conditions)
# ═══════════════════════════════════════════════════════════════════════════════

def _manager_scope_sql(user: str) -> str:
    if MANAGER_SCOPE == "none":
        return "1=1"

    emp = _my_employee(user)
    if not emp:
        return "1=0"

    parts = []
    if MANAGER_SCOPE in ("reports_to", "both"):
        parts.append(
            f"{TABLE}.requested_by in ("
            f"select user_id from `tabEmployee` "
            f"where reports_to = {frappe.db.escape(emp.name)} "
            f"and ifnull(user_id, '') != '')"
        )
    if MANAGER_SCOPE in ("department", "both") and emp.department:
        parts.append(f"{TABLE}.department = {frappe.db.escape(emp.department)}")

    return "(" + " or ".join(parts) + ")" if parts else "1=0"


def get_permission_query_conditions(user=None, **kwargs) -> str:
    """Return the SQL WHERE fragment limiting eRequest list/report/search results."""
    user = user or frappe.session.user
    roles = set(frappe.get_roles(user))

    if _is_superuser(user, roles):
        return ""

    u = frappe.db.escape(user)

    # Rule 1 — everyone sees their own
    clauses = [
        f"{TABLE}.requested_by = {u}",
        f"{TABLE}.owner = {u}",
    ]

    acted = False

    # Rule 2 — Manager
    if ROLE_MANAGER in roles:
        acted = True
        states = _pending_states("manager")
        if states:
            clauses.append(
                f"({TABLE}.workflow_state in {_in_sql(states)} "
                f"and {_manager_scope_sql(user)})"
            )
        clauses.append(f"{TABLE}.manager_approval = {u}")

    # Rule 3 — Finance
    if ROLE_FINANCE in roles:
        acted = True
        states = _pending_states("finance")
        if states:
            clauses.append(f"{TABLE}.workflow_state in {_in_sql(states)}")
        if FINANCE_SEES_APPROVED_PAYMENTS:
            approved = _approved_states()
            if approved:
                clauses.append(
                    f"({TABLE}.workflow_state in {_in_sql(approved)} "
                    f"and {TABLE}.request_type = 'Payment Request')"
                )
        clauses.append(f"{TABLE}.finance_approval = {u}")

    # Rule 4 — Final approver
    if ROLE_FINAL in roles:
        acted = True
        states = _pending_states("final")
        if states:
            clauses.append(f"{TABLE}.workflow_state in {_in_sql(states)}")
        clauses.append(f"{TABLE}.final_approval = {u}")

    # Requests an approver personally actioned (approve / reject / amend)
    if acted:
        clauses.append(f"{TABLE}.modified_by = {u}")
        clauses.append(
            f"{TABLE}.name in (select reference_name from `tabComment` "
            f"where reference_doctype = '{DOCTYPE}' and comment_type = 'Workflow' "
            f"and owner = {u})"
        )
        clauses.append(
            f"{TABLE}.name in (select reference_name from `tabWorkflow Action` "
            f"where reference_doctype = '{DOCTYPE}' and completed_by = {u})"
        )

    return "(" + " or ".join(clauses) + ")"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. DOCUMENT-LEVEL CHECK  (has_permission)
# ═══════════════════════════════════════════════════════════════════════════════

def _manager_in_scope(row, user: str) -> bool:
    if MANAGER_SCOPE == "none":
        return True

    emp = _my_employee(user)
    if not emp:
        return False

    if MANAGER_SCOPE in ("reports_to", "both") and row.requested_by:
        reports_to = frappe.db.get_value(
            "Employee",
            {"user_id": row.requested_by, "status": "Active"},
            "reports_to",
        )
        if reports_to and reports_to == emp.name:
            return True

    if MANAGER_SCOPE in ("department", "both"):
        if emp.department and row.department == emp.department:
            return True

    return False


def can_view(doc, user=None) -> bool:
    """
    True if `user` may see this eRequest.  Mirrors the SQL filter above; also
    used by the portal endpoints in erequest.py and by erequest_pending.py.

    `doc` may be a name or a Document. Only its NAME is used: every value is read
    from the database, so a workflow transition in progress cannot change the
    answer half way through a save.
    """
    user = user or frappe.session.user
    name = doc if isinstance(doc, str) else doc.get("name")

    roles = set(frappe.get_roles(user))
    if _is_superuser(user, roles):
        return True

    row = (
        frappe.db.get_value(DOCTYPE, name, _FIELDS, as_dict=True) if name else None
    )
    if not row:  # not saved yet -> nothing to restrict
        return True

    # Rule 1
    if row.requested_by == user or row.owner == user:
        return True

    stage = _stage_of(row.workflow_state)
    state = (row.workflow_state or "").lower()
    acted = False

    # Rule 2 — Manager
    if ROLE_MANAGER in roles:
        acted = True
        if row.manager_approval == user:
            return True
        if stage == "manager" and _manager_in_scope(row, user):
            return True

    # Rule 3 — Finance
    if ROLE_FINANCE in roles:
        acted = True
        if row.finance_approval == user:
            return True
        if stage == "finance":
            return True
        if (
            FINANCE_SEES_APPROVED_PAYMENTS
            and state == "approved"
            and row.request_type == "Payment Request"
        ):
            return True

    # Rule 4 — Final
    if ROLE_FINAL in roles:
        acted = True
        if row.final_approval == user:
            return True
        if stage == "final":
            return True

    if acted and (row.modified_by == user or _has_acted(name, user)):
        return True

    return False


def has_permission(doc, ptype=None, user=None, **kwargs):
    """
    Frappe has_permission hook.  Role-level DocPerm still applies first;
    this only DENIES records the user has no business with.
    """
    user = user or frappe.session.user

    # Creating a new request is never blocked by visibility
    if ptype == "create":
        return True
    if not isinstance(doc, str) and (doc.is_new() or not doc.get("name")):
        return True

    return can_view(doc, user)