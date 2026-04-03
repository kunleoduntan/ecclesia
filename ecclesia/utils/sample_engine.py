"""
Sample Engine
=============
Implements audit sampling per ISA 530 and ACFE best practices.

Sampling methods:
- Monetary Unit Sampling (MUS) — for financial DocTypes, weighted by amount
- Random Statistical Sampling — for non-financial DocTypes
- 100% Population — for critical/low-volume DocTypes
- Risk-based / Judgmental — guided by AI anomaly flags

MUS gives higher selection probability to larger amounts,
ensuring material misstatements are more likely to be detected.
"""

import frappe
import random
from frappe.utils import flt, cint


def generate_samples_for_engagement(engagement_name):
    """
    Generate audit samples for all DocTypes in scope for an engagement.
    Called asynchronously after engagement submission.
    """
    engagement = frappe.get_doc("Audit Engagement", engagement_name)

    for scope_row in engagement.scope_doctypes:
        try:
            _generate_samples_for_doctype(engagement, scope_row.doctype_name)
        except Exception as e:
            frappe.log_error(
                f"Sample generation failed for {scope_row.doctype_name} "
                f"in engagement {engagement_name}: {e}"
            )

    frappe.db.commit()
    frappe.publish_realtime(
        "audit_samples_ready",
        {"engagement": engagement_name},
        user=engagement.lead_auditor
    )


def _generate_samples_for_doctype(engagement, doctype_name):
    """Generate samples for one DocType within an engagement."""
    reg = frappe.db.get_value(
        "Auditable DocType Registry",
        {"doctype_name": doctype_name},
        ["doctype_name", "sampling_method", "recommended_sample_size",
         "amount_fields", "date_fields", "risk_level", "transaction_code"],
        as_dict=True
    )
    if not reg:
        return

    if not frappe.db.table_exists(f"tab{doctype_name}"):
        return

    # Get date field
    date_field = "posting_date" if frappe.db.has_column(doctype_name, "posting_date") else "creation"

    # Get amount field
    amount_fields = [f.strip() for f in (reg.amount_fields or "").split(",") if f.strip()]
    amount_field = None
    for af in amount_fields:
        if frappe.db.has_column(doctype_name, af):
            amount_field = af
            break

    # Get population
    fields = ["name", "owner", "creation", date_field]
    if amount_field:
        fields.append(amount_field)

    population = frappe.db.get_all(
        doctype_name,
        filters={
            "docstatus": 1,
            date_field: ["between", [engagement.from_date, engagement.to_date]]
        },
        fields=list(set(fields)),
        limit=10000,
        order_by=f"{date_field} asc"
    )

    if not population:
        return

    # Determine sample size
    sample_size_pct = cint(reg.recommended_sample_size) or 15
    target_count = max(5, int(len(population) * sample_size_pct / 100))
    target_count = min(target_count, len(population))

    # Select sample based on method
    method = reg.sampling_method or "Random Statistical"
    if "100%" in method or len(population) <= 10:
        sampled = population
        selection_basis = "100% Population — low volume or critical risk"
    elif "Monetary Unit" in method and amount_field:
        sampled = _mus_sample(population, amount_field, target_count)
        selection_basis = f"Monetary Unit Sampling (MUS) — weighted by {amount_field}"
    else:
        sampled = random.sample(population, target_count)
        selection_basis = f"Random Statistical Sampling — {sample_size_pct}% of population"

    # Always include AI-flagged anomalies in sample
    flagged = _get_flagged_records(doctype_name, engagement.from_date, engagement.to_date)
    flagged_names = {f.reference_name for f in flagged}

    # Create Audit Sample records
    for record in sampled:
        is_ai_flagged = record.name in flagged_names
        _create_sample_record(
            engagement_name=engagement.name,
            doctype_name=doctype_name,
            document_name=record.name,
            selection_basis=selection_basis,
            is_ai_flagged=is_ai_flagged,
            amount=flt(record.get(amount_field, 0)) if amount_field else 0,
            transaction_code=reg.transaction_code
        )

    # Add AI-flagged records not already in sample
    for flagged_name in flagged_names:
        if not any(r.name == flagged_name for r in sampled):
            _create_sample_record(
                engagement_name=engagement.name,
                doctype_name=doctype_name,
                document_name=flagged_name,
                selection_basis="AI Anomaly Flag — mandatory inclusion",
                is_ai_flagged=True,
                amount=0,
                transaction_code=reg.transaction_code
            )


def _mus_sample(population, amount_field, target_count):
    """
    Monetary Unit Sampling (MUS) implementation.

    Each monetary unit has equal probability of selection,
    so larger amounts have proportionally higher selection probability.
    This ensures material misstatements are more likely to be detected.
    """
    # Build cumulative total
    population_with_amounts = [
        (r, flt(r.get(amount_field, 0)))
        for r in population
        if flt(r.get(amount_field, 0)) > 0
    ]

    if not population_with_amounts:
        return random.sample(population, min(target_count, len(population)))

    total = sum(amt for _, amt in population_with_amounts)
    if total <= 0:
        return random.sample(population, min(target_count, len(population)))

    interval = total / target_count
    start = random.uniform(0, interval)

    selected = []
    seen_names = set()
    cumulative = 0

    for record, amount in population_with_amounts:
        cumulative += amount
        while start <= cumulative:
            if record["name"] not in seen_names:
                selected.append(record)
                seen_names.add(record["name"])
            start += interval
            if len(selected) >= target_count:
                break
        if len(selected) >= target_count:
            break

    return selected


def _get_flagged_records(doctype_name, from_date, to_date):
    """Get AI-flagged anomaly findings for a DocType in the date range."""
    return frappe.get_all(
        "Audit Finding",
        filters={
            "reference_doctype": doctype_name,
            "source": "AI Auto-Detection",
            "transaction_date": ["between", [from_date, to_date]]
        },
        fields=["reference_name"]
    )


def _create_sample_record(engagement_name, doctype_name, document_name,
                           selection_basis, is_ai_flagged, amount, transaction_code):
    """Create an Audit Sample record."""
    if frappe.db.exists("Audit Sample", {
        "audit_engagement": engagement_name,
        "reference_doctype": doctype_name,
        "reference_name": document_name
    }):
        return

    frappe.get_doc({
        "doctype":           "Audit Sample",
        "audit_engagement":  engagement_name,
        "reference_doctype": doctype_name,
        "reference_name":    document_name,
        "selection_basis":   selection_basis,
        "is_ai_flagged":     1 if is_ai_flagged else 0,
        "sample_amount":     amount,
        "transaction_code":  transaction_code,
        "status":            "Pending Review",
    }).insert(ignore_permissions=True)
