"""
Field Classifier
================
Reads a DocType's field list and intelligently classifies each field
into audit-relevant categories: amounts, dates, approvals, parties,
accounts, cost centers, statuses, and users.

This is the foundation of "register once, audit forever."
"""

import re


# ─────────────────────────────────────────────────────────────────────────────
# Field name pattern libraries (world-class audit field detection)
# ─────────────────────────────────────────────────────────────────────────────

AMOUNT_PATTERNS = [
    r"amount", r"total", r"grand_total", r"net_total", r"tax_amount",
    r"base_amount", r"base_total", r"base_net", r"outstanding",
    r"paid_amount", r"balance", r"debit", r"credit", r"value",
    r"rate", r"price", r"cost", r"salary", r"wage", r"remuneration",
    r"fee", r"charge", r"discount", r"freight", r"insurance",
    r"net_pay", r"gross_pay", r"basic_salary"
]

DATE_PATTERNS = [
    r"date$", r"_date", r"posting_date", r"transaction_date",
    r"due_date", r"from_date", r"to_date", r"start_date", r"end_date",
    r"issue_date", r"delivery_date", r"schedule_date", r"expected_date",
    r"clearance_date", r"valid_till", r"expiry_date", r"birth_date",
    r"joining_date", r"relieving_date"
]

APPROVAL_PATTERNS = [
    r"approved_by", r"authorized_by", r"sanctioned_by", r"verified_by",
    r"reviewed_by", r"approved$", r"approval_status", r"approval_date",
    r"approver", r"workflow_state", r"docstatus", r"status.*approv",
    r"checked_by", r"validated_by", r"confirmed_by"
]

PARTY_PATTERNS = [
    r"^customer$", r"^supplier$", r"^vendor$", r"^employee$",
    r"party$", r"^party$", r"party_name", r"party_type",
    r"customer_name", r"supplier_name", r"employee_name",
    r"lead_name", r"contact_person"
]

ACCOUNT_PATTERNS = [
    r"account$", r"^account$", r"debit_to", r"credit_to",
    r"income_account", r"expense_account", r"receivable_account",
    r"payable_account", r"tax_account", r"cost_of_goods_sold",
    r"stock_received_but_not_billed", r"bank_account", r"cash_account"
]

COST_CENTER_PATTERNS = [
    r"cost_center", r"profit_center", r"business_unit",
    r"department", r"division", r"project"
]

STATUS_PATTERNS = [
    r"^status$", r"payment_status", r"billing_status",
    r"delivery_status", r"dispatch_status", r"approval_status",
    r"workflow_state", r"docstatus"
]

USER_PATTERNS = [
    r"^owner$", r"modified_by", r"created_by", r"user$",
    r"prepared_by", r"posted_by", r"entered_by",
    r"approved_by", r"authorized_by"
]

GL_POSTING_INDICATORS = [
    r"debit_to", r"credit_to", r"income_account", r"expense_account",
    r"receivable_account", r"payable_account", r"accounts",
    r"gl_entry", r"make_gl_entries", r"posting_date"
]


def _matches_any(field_name, patterns):
    """Check if field name matches any pattern in the list."""
    fn = field_name.lower()
    return any(re.search(p, fn) for p in patterns)


def classify_fields(fields):
    """
    Classify all fields in a DocType field list into audit categories.

    Args:
        fields: list of field dicts from DocType JSON

    Returns:
        dict of categorized field name lists
    """
    result = {
        "amount_fields":      [],
        "date_fields":        [],
        "approval_fields":    [],
        "party_fields":       [],
        "account_fields":     [],
        "cost_center_fields": [],
        "status_fields":      [],
        "user_fields":        [],
    }

    for field in fields:
        fname = field.get("fieldname", "")
        ftype = field.get("fieldtype", "")
        if not fname:
            continue

        # Currency/Float fields with amount-like names
        if ftype in ("Currency", "Float") and _matches_any(fname, AMOUNT_PATTERNS):
            result["amount_fields"].append(fname)

        # Date fields
        if ftype in ("Date", "Datetime") or _matches_any(fname, DATE_PATTERNS):
            if fname not in result["amount_fields"]:
                result["date_fields"].append(fname)

        # Approval fields
        if _matches_any(fname, APPROVAL_PATTERNS):
            result["approval_fields"].append(fname)

        # Party fields (Link to customer/supplier/employee)
        if ftype == "Link" and _matches_any(fname, PARTY_PATTERNS):
            result["party_fields"].append(fname)

        # Account fields
        if ftype == "Link" and field.get("options", "") == "Account":
            result["account_fields"].append(fname)
        elif _matches_any(fname, ACCOUNT_PATTERNS):
            result["account_fields"].append(fname)

        # Cost center fields
        if ftype == "Link" and field.get("options", "") == "Cost Center":
            result["cost_center_fields"].append(fname)
        elif _matches_any(fname, COST_CENTER_PATTERNS):
            result["cost_center_fields"].append(fname)

        # Status fields
        if _matches_any(fname, STATUS_PATTERNS):
            result["status_fields"].append(fname)

        # User/owner fields
        if ftype == "Link" and field.get("options", "") == "User":
            result["user_fields"].append(fname)
        elif _matches_any(fname, USER_PATTERNS):
            result["user_fields"].append(fname)

    # Deduplicate
    for key in result:
        result[key] = list(dict.fromkeys(result[key]))

    return result


def detect_gl_posting(dt_def, classified_fields):
    """
    Detect whether a DocType posts to the General Ledger.

    Uses multiple signals:
    1. Has account fields (debit_to, credit_to, income_account etc.)
    2. DocType has 'accounts' child table
    3. Known GL-posting DocType names
    4. Has both posting_date and account-type fields
    """
    name = dt_def.get("name", "").lower()

    # Known GL-posting DocTypes
    known_gl_doctypes = [
        "sales invoice", "purchase invoice", "payment entry",
        "journal entry", "expense claim", "salary slip",
        "stock entry", "asset", "purchase receipt",
        "delivery note", "purchase order", "sales order"
    ]
    if any(k in name for k in known_gl_doctypes):
        return True

    # Has account fields detected
    if len(classified_fields.get("account_fields", [])) > 0:
        return True

    # Has child table named 'accounts'
    fields = dt_def.get("fields", [])
    for field in fields:
        if field.get("fieldtype") == "Table" and \
           field.get("options", "").lower() in ("accounts", "gl entry", "payment schedule"):
            return True

    # Has both posting_date and amount fields — strong GL signal
    has_posting_date = any(
        f.get("fieldname") == "posting_date" for f in fields
    )
    has_amounts = len(classified_fields.get("amount_fields", [])) > 0
    if has_posting_date and has_amounts:
        return True

    return False


def get_key_financial_fields(registry_doc):
    """
    Return a structured dict of the most important financial fields
    for a registered DocType, used by the audit sampling engine.
    """
    return {
        "primary_amount": _first_field(registry_doc.amount_fields),
        "posting_date":   _first_date(registry_doc.date_fields),
        "party":          _first_field(registry_doc.party_fields),
        "account":        _first_field(registry_doc.account_fields),
        "approved_by":    _first_field(registry_doc.approval_fields),
        "status":         _first_field(registry_doc.status_fields),
    }


def _first_field(comma_list):
    if not comma_list:
        return None
    parts = [p.strip() for p in comma_list.split(",") if p.strip()]
    return parts[0] if parts else None


def _first_date(comma_list):
    """Get primary date field, preferring posting_date."""
    if not comma_list:
        return None
    parts = [p.strip() for p in comma_list.split(",") if p.strip()]
    for p in parts:
        if "posting" in p:
            return p
    return parts[0] if parts else None
