"""Anomaly Detection API — called from the frontend audit panel."""

import frappe
from ecclesia.utils.ai_engine import run_anomaly_detection, _csv_to_list
from ecclesia.utils.ai_engine import _log_ai_anomaly


@frappe.whitelist()
def run_scan(doctype_name, from_date, to_date):
    """
    Run AI anomaly scan on a DocType for a given date range.
    Returns list of anomalies found.
    """
    reg = frappe.db.get_value(
        "Auditable DocType Registry",
        {"doctype_name": doctype_name},
        ["name", "amount_fields", "date_fields", "approval_fields",
         "risk_level", "transaction_code"],
        as_dict=True
    )
    if not reg:
        return []

    if not frappe.db.table_exists(f"tab{doctype_name}"):
        return []

    date_field = "posting_date" if frappe.db.has_column(doctype_name, "posting_date") else "creation"

    # Build field list to fetch
    base_fields = ["name", "owner", "modified", "modified_by", "creation"]
    extra_fields = (
        _csv_to_list(reg.amount_fields or "") +
        _csv_to_list(reg.date_fields or "") +
        _csv_to_list(reg.approval_fields or "")
    )
    fields = list(set(base_fields + [
        f for f in extra_fields if frappe.db.has_column(doctype_name, f)
    ]))

    records = frappe.db.get_all(
        doctype_name,
        filters={date_field: ["between", [from_date, to_date]]},
        fields=fields,
        limit=1000
    )

    if not records:
        return []

    anomalies = run_anomaly_detection(doctype_name, records, reg)

    # Auto-log as findings
    for anomaly in anomalies:
        try:
            _log_ai_anomaly(anomaly)
        except Exception:
            pass

    return anomalies


@frappe.whitelist()
def run_scan_on_records(doctype_name, record_names):
    """Run anomaly scan on specific records (from list view selection)."""
    import json
    if isinstance(record_names, str):
        record_names = json.loads(record_names)

    reg = frappe.db.get_value(
        "Auditable DocType Registry",
        {"doctype_name": doctype_name},
        ["name", "amount_fields", "date_fields", "approval_fields",
         "risk_level", "transaction_code"],
        as_dict=True
    )
    if not reg:
        return []

    base_fields = ["name", "owner", "modified", "modified_by", "creation"]
    extra_fields = (
        _csv_to_list(reg.amount_fields or "") +
        _csv_to_list(reg.date_fields or "") +
        _csv_to_list(reg.approval_fields or "")
    )
    fields = list(set(base_fields + [
        f for f in extra_fields if frappe.db.has_column(doctype_name, f)
    ]))

    records = frappe.db.get_all(
        doctype_name,
        filters={"name": ["in", record_names]},
        fields=fields
    )

    anomalies = run_anomaly_detection(doctype_name, records, reg)
    for anomaly in anomalies:
        try:
            _log_ai_anomaly(anomaly)
        except Exception:
            pass

    return anomalies
