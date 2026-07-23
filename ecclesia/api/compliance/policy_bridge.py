# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/api/compliance/policy_bridge.py
"""
Policy Bridge
═════════════
Called by hooks.py doc_events → Company Policy → on_submit.

When a Company Policy is published (submitted), this bridge:
  1. Creates or updates a linked Compliance Policy record.
  2. Tags the Company Policy with its compliance_domain if not already set.
  3. Logs the event to Compliance Event Log for audit trail.

This connects the existing, rich Company Policy DocType (with acknowledgement
workflows, version history, etc.) to the Compliance module's policy register,
so the Compliance Officer has a single view of all compliance-related policies.
"""

import frappe
from frappe import _
from frappe.utils import nowdate


def sync_to_compliance_policy(doc, method=None):
    """
    hooks.py → Company Policy → on_submit

    `doc` is the submitted Company Policy document.
    Creates or updates a Compliance Policy that mirrors it.
    """
    if not doc or not doc.name:
        return

    # Only sync policies that are tagged to a compliance domain
    # (the compliance_domain custom field we added in install_custom_fields.py)
    compliance_domain = doc.get("compliance_domain")
    if not compliance_domain or compliance_domain == "General":
        # Still create a general Compliance Policy record but without domain mapping
        pass  # fall through — create for all submitted policies

    try:
        _upsert_compliance_policy(doc, compliance_domain)
        _log_policy_event(doc)
    except Exception as e:
        frappe.log_error(
            f"Policy bridge failed for Company Policy {doc.name}: {e}",
            "Policy Bridge"
        )


def _upsert_compliance_policy(company_policy_doc, compliance_domain):
    """
    Create a Compliance Policy if none exists for this Company Policy,
    or update the existing one.
    """
    cp_doc = company_policy_doc

    # Check if a Compliance Policy already links to this Company Policy
    existing = frappe.db.get_value(
        "Compliance Policy",
        {"company_policy": cp_doc.name},
        "name"
    )

    # Map Company Policy category to Compliance Policy category
    category_map = {
        "HR":                    "General",
        "Finance":               "Tax Compliance",
        "IT":                    "Data Protection",
        "Legal":                 "Corporate Governance",
        "Compliance":            "General",
        "Health & Safety":       "HSE",
        "Anti-Money Laundering": "AML",
        "Data Protection":       "Data Protection",
    }
    mapped_category = (
        compliance_domain
        if compliance_domain and compliance_domain != "General"
        else category_map.get(cp_doc.get("category") or "", "General")
    )

    if existing:
        # Update the existing Compliance Policy
        comp_pol = frappe.get_doc("Compliance Policy", existing)
        comp_pol.policy_name     = cp_doc.policy_name or cp_doc.name
        comp_pol.policy_category = mapped_category
        comp_pol.effective_date  = cp_doc.get("effective_date") or nowdate()
        comp_pol.review_date     = cp_doc.get("review_date") or None
        comp_pol.status          = "Active"
        comp_pol.version         = str(cp_doc.get("version") or "1.0")
        comp_pol.document        = cp_doc.get("policy_document") or None
        comp_pol.policy_owner    = cp_doc.get("policy_owner") or None
        comp_pol.save(ignore_permissions=True)

        frappe.msgprint(
            _("Compliance Policy {0} updated from Company Policy.").format(existing),
            indicator="blue", alert=True
        )

    else:
        # Create a new Compliance Policy
        comp_pol = frappe.new_doc("Compliance Policy")
        comp_pol.policy_name     = cp_doc.get("policy_name") or cp_doc.name
        comp_pol.policy_code     = f"CP-{cp_doc.name[:20]}"
        comp_pol.policy_category = mapped_category
        comp_pol.effective_date  = cp_doc.get("effective_date") or nowdate()
        comp_pol.review_date     = cp_doc.get("review_date") or None
        comp_pol.status          = "Active"
        comp_pol.version         = str(cp_doc.get("version") or "1.0")
        comp_pol.document        = cp_doc.get("policy_document") or None
        comp_pol.policy_owner    = cp_doc.get("policy_owner") or None

        # Store a reference back to the source Company Policy
        # (uses the company_policy custom field we added)
        if frappe.db.has_column("Compliance Policy", "company_policy"):
            comp_pol.company_policy = cp_doc.name

        comp_pol.insert(ignore_permissions=True)

        # Back-link on the Company Policy if the compliance_rule_ref field exists
        if frappe.db.has_column("Company Policy", "compliance_rule_ref"):
            frappe.db.set_value(
                "Company Policy", cp_doc.name,
                "compliance_rule_ref", comp_pol.name,
                update_modified=False
            )

        frappe.msgprint(
            _("Compliance Policy {0} created and linked to this policy.").format(comp_pol.name),
            indicator="green", alert=True
        )

    frappe.db.commit()


def _log_policy_event(cp_doc):
    """Write an entry to Compliance Event Log for audit trail."""
    try:
        ev = frappe.new_doc("Compliance Event Log")
        ev.event_name      = f"Policy Synced: {cp_doc.name}"
        ev.event_type      = "Manual"
        ev.source_doctype  = "Company Policy"
        ev.source_document = cp_doc.name
        ev.obligation_type = "Other"
        ev.company         = cp_doc.get("company") or frappe.defaults.get_default("company")
        ev.status          = "Success"
        ev.processed_on    = frappe.utils.now()
        ev.triggered_by    = frappe.session.user
        ev.insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        pass  # Event log failure must never block the main operation


# ── Whitelisted utility ───────────────────────────────────────────────────────

@frappe.whitelist()
def sync_all_company_policies(company=None):
    """
    Bulk sync: sync all submitted Company Policies to Compliance Policy.
    Call from bench console or ComplianceHQ dashboard as a one-time migration.

        frappe.call('ecclesia.api.compliance.policy_bridge.sync_all_company_policies',
                    args={company: 'MyCompany Ltd'})
    """
    filters = {"docstatus": 1}
    if company:
        filters["company"] = company

    policies = frappe.get_all(
        "Company Policy",
        filters=filters,
        fields=["name", "policy_name", "category", "effective_date",
                "review_date", "policy_owner", "policy_document", "version"]
    )

    synced, failed = 0, 0
    for pol in policies:
        try:
            doc = frappe.get_doc("Company Policy", pol.name)
            _upsert_compliance_policy(doc, doc.get("compliance_domain"))
            synced += 1
        except Exception as e:
            frappe.log_error(f"Bulk sync failed for {pol.name}: {e}", "Policy Bridge")
            failed += 1

    return {
        "synced": synced,
        "failed": failed,
        "message": f"Synced {synced} policies. {failed} failed."
    }