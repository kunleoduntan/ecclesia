# Copyright (c) 2026, kunle Oduntan and contributors
# For license information, please see license.txt

"""
Audit Universe — Controller
=============================
Read-only live view of every registered DocType in the audit universe.
Records are created/updated by sync_audit_universe() which is called:
  ▸ Weekly by the scheduler (hooks.py)
  ▸ On-demand from the Audit Universe list/form button
  ▸ Automatically after each Auditable DocType Registry save

Each row mirrors key risk and coverage data from the registry so
auditors can see the full universe at a glance without opening
individual registry records.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import date_diff, today, cint


class AuditUniverse(Document):

    def before_save(self):
        """Universe records are managed by sync — block manual edits."""
        if not frappe.flags.in_sync_audit_universe:
            frappe.throw(
                _("Audit Universe records are managed automatically. "
                  "Use <b>Actions → Sync All</b> to refresh, or edit "
                  "the source <b>Auditable DocType Registry</b> record."),
                title=_("Read-Only Record"),
            )


# ─────────────────────────────────────────────────────────────────────────────
# Priority scoring
# ─────────────────────────────────────────────────────────────────────────────

def _compute_priority_score(reg) -> float:
    """0–100 composite priority score. Mirrors logic in annual_audit_plan.py."""
    score = 0.0
    score += {"Critical": 40, "High": 30, "Medium": 20, "Low": 10}.get(
        reg.get("risk_level"), 15
    )
    if reg.get("is_gl_posting"):
        score += 15
    score += min(cint(reg.get("open_findings_count", 0)) * 3, 20)
    last = reg.get("last_audit_date")
    if not last:
        score += 20
    else:
        days = date_diff(today(), last)
        score += 20 if days > 365 else 15 if days > 180 else 8 if days > 90 else 2
    score += {
        "Financial": 5, "Procurement": 4, "HR & Payroll": 3,
        "Inventory & Stock": 3, "Sales": 2, "Custom": 1,
    }.get(reg.get("doctype_classification"), 1)
    return round(min(score, 100), 1)


# ─────────────────────────────────────────────────────────────────────────────
# Sync — plain function for scheduler + whitelisted wrapper for UI
# ─────────────────────────────────────────────────────────────────────────────

def sync_audit_universe():
    """
    Sync Audit Universe from Auditable DocType Registry.

    Called directly by:
      - hooks.py weekly scheduler:
            ecclesia.doctype.audit_universe.audit_universe.sync_audit_universe
      - frappe.enqueue() calls from auditable_doctype_registry.py

    NOTE: This is intentionally NOT decorated with @frappe.whitelist().
    Frappe scheduler jobs must be plain importable functions — the whitelist
    decorator has no effect on scheduler calls but can cause import confusion.
    For UI/API calls use sync_audit_universe_from_ui() below.
    """
    registries = frappe.get_all(
        "Auditable DocType Registry",
        filters={"is_active": 1},
        fields=[
            "name", "doctype_name", "transaction_code", "doctype_classification",
            "risk_level", "is_gl_posting", "financial_statement_line",
            "audit_frequency", "last_audit_date", "total_transactions_ytd",
            "open_findings_count", "cumulative_findings", "last_audit_opinion",
        ],
    )

    created = updated = 0
    frappe.flags.in_sync_audit_universe = True

    try:
        for reg in registries:
            score = _compute_priority_score(reg)
            values = {
                "doctype_name":             reg.doctype_name,
                "transaction_code":         reg.transaction_code,
                "doctype_classification":   reg.doctype_classification,
                "risk_level":               reg.risk_level,
                "risk_score":               score,
                "is_gl_posting":            reg.is_gl_posting,
                "financial_statement_line": reg.financial_statement_line,
                "audit_frequency":          reg.audit_frequency,
                "last_audit_date":          reg.last_audit_date,
                "total_transactions_ytd":   reg.total_transactions_ytd,
                "open_findings":            reg.open_findings_count,
                "cumulative_findings":      reg.cumulative_findings,
                "last_audit_opinion":       reg.last_audit_opinion,
                "registry_ref":             reg.name,
            }

            existing = frappe.db.exists("Audit Universe", {"doctype_name": reg.doctype_name})
            if existing:
                frappe.db.set_value("Audit Universe", existing, values)
                updated += 1
            else:
                doc = frappe.get_doc({"doctype": "Audit Universe", **values})
                doc.insert(ignore_permissions=True)
                created += 1

        frappe.db.commit()
    finally:
        frappe.flags.in_sync_audit_universe = False

    return f"Audit Universe synced — {created} created, {updated} updated."


@frappe.whitelist()
def sync_audit_universe_from_ui():
    """
    Whitelisted wrapper for UI buttons and API calls.
    Delegates to sync_audit_universe() which is the scheduler-safe plain function.
    """
    return sync_audit_universe()