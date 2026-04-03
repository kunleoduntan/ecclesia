"""
Checklist Generator
====================
Auto-generates audit checklists based on DocType classification.
All checklist items are aligned with IIA Standards, COSO Framework,
and ISA audit procedures.

When a new DocType is registered, a default checklist template is created.
When an engagement is submitted, live checklists are generated from templates.
"""

import frappe


# ─────────────────────────────────────────────────────────────────────────────
# Master Checklist Library (IIA / COSO / ISA aligned)
# ─────────────────────────────────────────────────────────────────────────────

CHECKLIST_LIBRARY = {
    "Financial": [
        # Completeness
        ("Completeness", "Verify that all transactions in the period are recorded in the system", "Critical", "Risk Assessment"),
        ("Completeness", "Confirm sequential numbering has no gaps in document series", "High", "Control Activities"),
        ("Completeness", "Reconcile total transaction count to source register/log", "High", "Control Activities"),
        # Accuracy
        ("Accuracy", "Verify that computed totals (tax, discount, grand total) are mathematically correct", "Critical", "Control Activities"),
        ("Accuracy", "Confirm amounts match supporting documentation (invoices, contracts, POs)", "Critical", "Control Activities"),
        ("Accuracy", "Test currency conversion rates for foreign currency transactions", "Medium", "Control Activities"),
        # GL Posting
        ("GL Posting", "Verify GL entries were posted to correct accounts per Chart of Accounts", "Critical", "Control Activities"),
        ("GL Posting", "Confirm debit/credit postings are balanced (total debits = total credits)", "Critical", "Control Activities"),
        ("GL Posting", "Check that posting date falls within the correct accounting period", "High", "Information & Communication"),
        ("GL Posting", "Review any cancelled GL entries and verify they were properly reposted", "High", "Monitoring"),
        ("GL Posting", "Confirm no postings to suspense or clearing accounts without resolution", "High", "Control Activities"),
        # Authorization
        ("Authorization", "Verify all transactions have required approvals per authorization matrix", "Critical", "Control Environment"),
        ("Authorization", "Confirm that preparers and approvers are different individuals (SOD)", "Critical", "Control Environment"),
        ("Authorization", "Check that high-value transactions have appropriate level of approval", "High", "Control Environment"),
        ("Authorization", "Verify approval timestamps are before or contemporaneous with posting", "High", "Control Activities"),
        # Cutoff
        ("Cutoff", "Test transactions around period end for correct period classification", "High", "Control Activities"),
        ("Cutoff", "Verify no backdated entries without proper authorization", "High", "Control Activities"),
        # Valuation
        ("Valuation", "Confirm amounts are stated at correct value per applicable standard", "Medium", "Control Activities"),
        ("Valuation", "Test any manual adjustments or write-offs for proper authorization", "High", "Control Activities"),
    ],
    "HR & Payroll": [
        ("Existence", "Verify all employees on payroll are active (not resigned/terminated)", "Critical", "Control Environment"),
        ("Existence", "Confirm no ghost employees — cross-reference HR records with payroll", "Critical", "Control Environment"),
        ("Authorization", "Verify salary changes have proper authorization and supporting documentation", "Critical", "Control Activities"),
        ("Authorization", "Confirm overtime, allowances, and deductions are approved per policy", "High", "Control Activities"),
        ("Cutoff", "Verify join/resign dates are correctly reflected in payroll calculations", "High", "Control Activities"),
        ("Compliance", "Check statutory deductions (tax, pension, social security) are correctly computed", "Critical", "Control Activities"),
        ("Compliance", "Verify leave balances and deductions match approved leave records", "High", "Information & Communication"),
        ("Segregation of Duties", "Confirm HR and payroll functions are handled by different personnel", "Critical", "Control Environment"),
        ("Bank Details", "Verify bank account details for all employees match authorized records", "High", "Control Activities"),
        ("Master Data", "Confirm pay grades, steps, and scales are per approved pay structure", "High", "Control Environment"),
    ],
    "Inventory & Stock": [
        ("Existence", "Verify physical stock balances agree with system quantities (spot count)", "Critical", "Control Activities"),
        ("Valuation", "Confirm stock is valued at correct cost (FIFO/LIFO/Weighted Average per policy)", "High", "Control Activities"),
        ("Authorization", "Verify all stock movements (receipts, issues, transfers) are properly authorized", "High", "Control Activities"),
        ("Completeness", "Confirm all goods received are entered in the system on same day", "High", "Control Activities"),
        ("Accuracy", "Verify unit of measure conversions are consistently applied", "Medium", "Control Activities"),
        ("Write-offs", "Review all stock write-offs and adjustments for proper authorization", "High", "Control Activities"),
        ("Cutoff", "Confirm stock count does not include goods in transit to/from suppliers", "High", "Control Activities"),
    ],
    "Procurement": [
        ("Authorization", "Verify all purchase orders are within the authorized approval limits", "Critical", "Control Environment"),
        ("Segregation of Duties", "Confirm that requisitioner, purchaser, and approver are different persons", "Critical", "Control Environment"),
        ("Vendor Verification", "Verify suppliers are registered on approved vendor list", "High", "Control Activities"),
        ("Three-way Match", "Confirm PO, Goods Receipt, and Invoice amounts agree (three-way match)", "Critical", "Control Activities"),
        ("Competitive Quotes", "Verify procurement policy requires minimum quotes — test compliance", "High", "Control Activities"),
        ("Related Party", "Check for transactions with related parties — verify disclosure and approval", "High", "Risk Assessment"),
        ("Duplicate Payments", "Scan for duplicate invoices/payments to same vendor in the period", "Critical", "Control Activities"),
        ("Contract Compliance", "Verify amounts billed agree with contracted rates", "High", "Control Activities"),
    ],
    "Sales": [
        ("Authorization", "Verify credit limits are applied and not exceeded without authorization", "High", "Control Activities"),
        ("Revenue Recognition", "Confirm revenue is recognized only upon delivery/service completion", "Critical", "Control Activities"),
        ("Accuracy", "Verify pricing, discounts, and taxes match approved price list", "High", "Control Activities"),
        ("Completeness", "Confirm all deliveries are billed — reconcile delivery notes to invoices", "High", "Control Activities"),
        ("Cutoff", "Test that revenue is recorded in the correct period (not premature recognition)", "Critical", "Control Activities"),
        ("Customer Verification", "Verify customers are creditworthy and on approved customer list", "Medium", "Risk Assessment"),
        ("Collections", "Trace outstanding receivables and verify follow-up actions are documented", "High", "Monitoring"),
    ],
    "Approval & Workflow": [
        ("Authorization Matrix", "Verify approval matrix is current and approved by management", "High", "Control Environment"),
        ("Completeness", "Confirm all required workflow steps were completed before final approval", "Critical", "Control Activities"),
        ("Timeliness", "Check that approvals are made within required timeframe per policy", "Medium", "Monitoring"),
        ("Segregation of Duties", "Verify no single user can both initiate and finally approve a transaction", "Critical", "Control Environment"),
        ("Bypass Detection", "Review any transactions where workflow steps were skipped or overridden", "Critical", "Control Activities"),
    ],
    "Custom": [
        ("General Controls", "Review access controls — only authorized users can create and modify records", "High", "Control Environment"),
        ("Authorization", "Verify all high-value or sensitive transactions have documented approval", "High", "Control Activities"),
        ("Completeness", "Confirm all expected transactions for the period are present", "Medium", "Control Activities"),
        ("Accuracy", "Spot-check accuracy of key data fields against supporting documents", "Medium", "Control Activities"),
        ("Data Integrity", "Verify no unauthorized modifications to submitted/approved records", "High", "Information & Communication"),
    ]
}


def create_default_checklist_template(registry_name, doctype_name, classification):
    """
    Create a default Audit Checklist Template for a newly registered DocType.
    Called automatically after DocType registration.
    """
    # Don't duplicate
    if frappe.db.exists("Audit Checklist Template", {"doctype_name": doctype_name}):
        return

    classification = classification or "Custom"
    items = CHECKLIST_LIBRARY.get(classification, CHECKLIST_LIBRARY["Custom"])

    template = frappe.get_doc({
        "doctype":           "Audit Checklist Template",
        "template_name":     f"Default Checklist — {doctype_name}",
        "doctype_name":      doctype_name,
        "classification":    classification,
        "is_default":        1,
        "checklist_items":   []
    })

    for i, (control_area, test_procedure, risk_level, coso) in enumerate(items, 1):
        template.append("checklist_items", {
            "item_number":     i,
            "control_area":    control_area,
            "test_procedure":  test_procedure,
            "risk_level":      risk_level,
            "coso_component":  coso,
            "iia_standard":    _map_iia_standard(control_area),
        })

    template.insert(ignore_permissions=True)
    frappe.db.commit()


def generate_checklists_for_engagement(engagement_name):
    """
    Generate live Audit Checklist instances for all DocTypes in an engagement scope.
    Called asynchronously after engagement submission.
    """
    engagement = frappe.get_doc("Audit Engagement", engagement_name)

    for scope_row in engagement.scope_doctypes:
        _generate_checklist_for_doctype(engagement, scope_row.doctype_name)

    frappe.db.commit()


def _generate_checklist_for_doctype(engagement, doctype_name):
    """Generate one Audit Checklist from the default template."""
    template = frappe.db.get_value(
        "Audit Checklist Template",
        {"doctype_name": doctype_name, "is_default": 1},
        "name"
    )
    if not template:
        return

    template_doc = frappe.get_doc("Audit Checklist Template", template)
    transaction_code = frappe.db.get_value(
        "Auditable DocType Registry",
        {"doctype_name": doctype_name},
        "transaction_code"
    )

    checklist = frappe.get_doc({
        "doctype":           "Audit Checklist",
        "audit_engagement":  engagement.name,
        "doctype_name":      doctype_name,
        "transaction_code":  transaction_code,
        "from_date":         engagement.from_date,
        "to_date":           engagement.to_date,
        "assigned_to":       engagement.lead_auditor,
        "status":            "Not Started",
        "checklist_items":   []
    })

    for item in template_doc.checklist_items:
        checklist.append("checklist_items", {
            "item_number":    item.item_number,
            "control_area":   item.control_area,
            "test_procedure": item.test_procedure,
            "risk_level":     item.risk_level,
            "coso_component": item.coso_component,
            "iia_standard":   item.iia_standard,
            "result":         "Not Tested",
        })

    checklist.insert(ignore_permissions=True)


def _map_iia_standard(control_area):
    """Map control area to relevant IIA Standard reference."""
    mapping = {
        "Completeness":           "IIA 2320 — Analysis and Evaluation",
        "Accuracy":               "IIA 2320 — Analysis and Evaluation",
        "GL Posting":             "IIA 2310 — Identifying Information",
        "Authorization":          "IIA 2330 — Documenting Information",
        "Cutoff":                 "IIA 2320 — Analysis and Evaluation",
        "Valuation":              "IIA 2320 — Analysis and Evaluation",
        "Existence":              "IIA 2310 — Identifying Information",
        "Segregation of Duties":  "IIA 2130 — Control",
        "Compliance":             "IIA 2130.A1 — Compliance",
        "Three-way Match":        "IIA 2320 — Analysis and Evaluation",
        "Duplicate Payments":     "IIA 2310 — Identifying Information",
        "General Controls":       "IIA 2130 — Control",
        "Data Integrity":         "IIA 2130 — Control",
    }
    return mapping.get(control_area, "IIA 2300 — Performing the Engagement")
