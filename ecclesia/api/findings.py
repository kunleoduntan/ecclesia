"""Findings API — whitelist endpoints for creating and fetching findings."""

import frappe


@frappe.whitelist()
def create_finding(reference_doctype, reference_name, finding_title, risk_rating,
                   finding_type=None, observation=None, corrective_action_suggested=None,
                   transaction_code=None, source="Auditor", audit_engagement=None):
    """Create an Audit Finding and return its name."""
    doc = frappe.get_doc({
        "doctype":                    "Audit Finding",
        "finding_title":              finding_title,
        "reference_doctype":          reference_doctype,
        "reference_name":             reference_name,
        "risk_rating":                risk_rating,
        "finding_type":               finding_type or "Control Deficiency",
        "observation":                observation,
        "corrective_action_suggested": corrective_action_suggested,
        "transaction_code":           transaction_code,
        "source":                     source,
        "audit_engagement":           audit_engagement,
        "status":                     "Open",
    })
    doc.insert(ignore_permissions=True)
    return doc.name


@frappe.whitelist()
def get_findings_for_record(reference_doctype, reference_name):
    """Get all audit findings for a specific document."""
    return frappe.get_all(
        "Audit Finding",
        filters={
            "reference_doctype": reference_doctype,
            "reference_name":    reference_name,
        },
        fields=["name", "finding_title", "risk_rating", "status",
                "finding_type", "transaction_code", "creation"],
        order_by="creation desc"
    )
