# Copyright (c) 2026, Ecclesia and contributors
# For license information, please see license.txt

"""
ecclesia/ecclesia/doctype/erequest/erequest_pending.py
═══════════════════════════════════════════════════════════════════════════════
Backend for the "My Pending Approvals" popup (public/js/erequest_pending.js).

Whitelisted API
───────────────
  get_pending()                  → {is_approver, items:[...]}
  approve(name)                  → approve at the caller's current stage
  reject(name, reason)           → reject with a mandatory reason
  approve_many(names)            → {done:[names], failed:[{name, error}]}

How it decides what the user can do
───────────────────────────────────
Everything goes through the Frappe Workflow engine (get_transitions /
apply_workflow), so roles, conditions and self-approval rules configured on
the Workflow are always respected.  The request list is read with
frappe.get_list, so erequest_visibility's permission_query_conditions also
applies: a user only ever sees requests that concern them.

Optional realtime nudge (hooks.py)
──────────────────────────────────
    doc_events = {
        "eRequest": {
            "on_update": [
                "ecclesia.ecclesia.doctype.erequest.erequest.on_update",
                "ecclesia.ecclesia.doctype.erequest.erequest_pending.notify_pending_refresh",
            ],
            "on_cancel": "ecclesia.ecclesia.doctype.erequest.erequest.on_cancel",
        }
    }
"""

import frappe
from frappe import _
from frappe.model.workflow import apply_workflow, get_transitions
from frappe.utils import fmt_money, now_datetime, pretty_date, strip_html_tags

from .erequest_visibility import _pending_states, can_view

DOCTYPE        = "eRequest"
REALTIME_EVENT = "erequest_pending_refresh"
MAX_ITEMS      = 200

APPROVER_ROLES = ("eRequest Manager", "eRequest Finance", "eRequest Admin")

# stage keyword → fields stamped on the doc when that stage approves
_STAMP_FIELDS = {
    "manager": ("manager_approval", "manager_approval_date"),
    "finance": ("finance_approval", "finance_approval_date"),
    "final":   ("final_approval",   "final_approval_date"),
}


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _is_approver(user: str) -> bool:
    return bool(set(APPROVER_ROLES) & set(frappe.get_roles(user)))


def _level_of(state: str):
    s = (state or "").lower()
    if "pending" not in s:
        return None
    for kw in _STAMP_FIELDS:
        if kw in s:
            return kw
    return None


def _all_pending_states() -> list:
    states = set()
    for kw in _STAMP_FIELDS:
        states.update(_pending_states(kw))
    return sorted(states)


def _classify(transitions):
    """Split available transitions into (approve, reject)."""
    approve = reject = None
    for t in transitions or []:
        nxt = (t.get("next_state") or "").lower()
        if "reject" in nxt or "declin" in nxt:
            reject = reject or t
        elif "cancel" in nxt or "draft" in nxt:
            continue
        else:
            approve = approve or t
    return approve, reject


def _safe_transitions(doc):
    try:
        return get_transitions(doc)
    except Exception:
        return []


def _amount(doc) -> str:
    cur = doc.currency or "NGN"
    if doc.request_type == "Payment Request":
        return fmt_money(doc.total_amount or doc.payment_amount or 0, currency=cur)
    if doc.estimated_cost:
        return fmt_money(doc.estimated_cost, currency=cur)
    return ""


def _purpose(doc) -> str:
    text = doc.payment_purpose or strip_html_tags(doc.issue_description or "") \
        or strip_html_tags(doc.description or "")
    text = (text or "").strip()
    return text if len(text) <= 220 else text[:217] + "..."


def _item(doc, approve, reject, names_cache: dict) -> dict:
    user_id = doc.requested_by or doc.owner
    if user_id not in names_cache:
        names_cache[user_id] = (
            frappe.db.get_value("User", user_id, "full_name") or user_id
        )
    return {
        "name":           doc.name,
        "title":          doc.title or "",
        "request_type":   doc.request_type or "",
        "category":       doc.payment_category or doc.maintenance_category or "",
        "beneficiary":    doc.payee_name or "",
        "priority":       doc.priority or "",
        "amount":         _amount(doc),
        "purpose":        _purpose(doc),
        "requester":      names_cache[user_id],
        "waiting":        pretty_date(doc.modified),
        "workflow_state": doc.workflow_state or "",
        "can_approve":    bool(approve),
        "can_reject":     bool(reject),
        "approve_label":  (approve or {}).get("action") or _("Approve"),
        "reject_label":   (reject or {}).get("action") or _("Reject"),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# API
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_pending() -> dict:
    user = frappe.session.user
    if user == "Guest" or not _is_approver(user):
        return {"is_approver": False, "items": []}

    states = _all_pending_states()
    if not states:
        return {"is_approver": True, "items": []}

    rows = frappe.get_list(
        DOCTYPE,
        filters={"workflow_state": ["in", states], "docstatus": ["<", 2]},
        fields=["name"],
        order_by="modified asc",
        limit_page_length=MAX_ITEMS,
    )

    items, names_cache = [], {}
    for r in rows:
        doc = frappe.get_doc(DOCTYPE, r.name)
        approve, reject = _classify(_safe_transitions(doc))
        if not approve and not reject:
            continue                      # nothing for this user to do here
        items.append(_item(doc, approve, reject, names_cache))

    return {"is_approver": True, "items": items}


def _act(name: str, kind: str, reason: str = ""):
    doc = frappe.get_doc(DOCTYPE, name)

    if not can_view(doc, frappe.session.user):
        frappe.throw(_("You do not have access to this request."), frappe.PermissionError)

    approve, reject = _classify(_safe_transitions(doc))
    transition = approve if kind == "approve" else reject
    if not transition:
        frappe.throw(
            _("You cannot {0} {1} at its current stage ({2}).").format(
                kind, name, doc.workflow_state
            )
        )

    level = _level_of(doc.workflow_state)

    if kind == "reject":
        if not (reason or "").strip():
            frappe.throw(_("A rejection reason is required."))
        doc.rejection_reason = reason.strip()

    apply_workflow(doc, transition.get("action"))

    if kind == "approve" and level:
        user_f, date_f = _STAMP_FIELDS[level]
        frappe.db.set_value(
            DOCTYPE, name,
            {user_f: frappe.session.user, date_f: now_datetime()},
        )


@frappe.whitelist(methods=["POST"])
def approve(name: str) -> dict:
    _act(name, "approve")
    return {"status": "approved", "name": name}


@frappe.whitelist(methods=["POST"])
def reject(name: str, reason: str = "") -> dict:
    _act(name, "reject", reason)
    return {"status": "rejected", "name": name}


@frappe.whitelist(methods=["POST"])
def approve_many(names) -> dict:
    names = frappe.parse_json(names) if isinstance(names, str) else (names or [])
    done, failed = [], []

    for name in names:
        try:
            _act(name, "approve")
            frappe.db.commit()
            done.append(name)
        except Exception as e:
            frappe.db.rollback()
            frappe.clear_messages()
            failed.append({"name": name, "error": str(e)})

    return {"done": done, "failed": failed}


# ═══════════════════════════════════════════════════════════════════════════════
# Realtime nudge (optional, via hooks doc_events)
# ═══════════════════════════════════════════════════════════════════════════════

def notify_pending_refresh(doc=None, method=None):
    """Tell approvers' browsers to refresh their badge."""
    try:
        users = set(frappe.get_all(
            "Has Role",
            filters={"role": ["in", list(APPROVER_ROLES)], "parenttype": "User"},
            pluck="parent",
        ))
        for u in users:
            frappe.publish_realtime(REALTIME_EVENT, {}, user=u, after_commit=True)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "eRequest realtime nudge failed")