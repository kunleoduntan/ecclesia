"""
Registry API
============
Whitelist API endpoints for the frontend audit engine.
"""

import frappe


@frappe.whitelist()
def get_registered_doctypes():
    """
    Return all active registered DocTypes as a dict keyed by doctype_name.
    Called once per session by the global JS to build the registry cache.
    """
    registries = frappe.get_all(
        "Auditable DocType Registry",
        filters={"is_active": 1},
        fields=[
            "doctype_name", "transaction_code", "doctype_classification",
            "risk_level", "is_gl_posting", "audit_frequency",
            "financial_statement_line", "coso_component", "sampling_method",
            "materiality_benchmark", "ai_risk_summary", "ai_red_flags",
            "ai_key_controls", "open_findings_count", "total_transactions_ytd",
            "last_audit_date", "last_audit_opinion"
        ]
    )

    result = {}
    for reg in registries:
        result[reg.doctype_name] = {
            "transaction_code":       reg.transaction_code,
            "doctype_classification": reg.doctype_classification,
            "risk_level":             reg.risk_level,
            "is_gl_posting":          reg.is_gl_posting,
            "audit_frequency":        reg.audit_frequency,
            "financial_statement_line": reg.financial_statement_line,
            "coso_component":         reg.coso_component,
            "sampling_method":        reg.sampling_method,
            "materiality_benchmark":  reg.materiality_benchmark,
            "ai_risk_summary":        reg.ai_risk_summary,
            "ai_red_flags":           reg.ai_red_flags,
            "ai_key_controls":        reg.ai_key_controls,
            "open_findings":          reg.open_findings_count or 0,
            "total_transactions_ytd": reg.total_transactions_ytd or 0,
            "last_audit_date":        str(reg.last_audit_date) if reg.last_audit_date else None,
            "last_audit_opinion":     reg.last_audit_opinion,
        }

    return result