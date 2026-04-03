"""
ecclesia.utils.field_mapper
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Auto-map source file column headers to Frappe DocType field definitions.

Usage:
    from ecclesia.utils.field_mapper import auto_map, get_doctype_fields

    fields = get_doctype_fields("Customer")
    mapping = auto_map(["customer_name", "email_address", "mobile"], fields)
    # => {"customer_name": "customer_name", "email_address": "email_id", "mobile": "mobile_no"}
"""

from __future__ import annotations
import re
import frappe


# ── Public API ────────────────────────────────────────────────────────────────

def get_doctype_fields(doctype: str) -> list[dict]:
    """
    Return all importable fields for a DocType, including child-table info.
    Each item:
        {
          "fieldname":  str,
          "label":      str,
          "fieldtype":  str,
          "options":    str | None,   # linked doctype or select options
          "reqd":       bool,
          "in_list_view": bool,
          "is_child_table": bool,
          "child_doctype":  str | None,  # set when fieldtype == "Table"
        }
    """
    meta = frappe.get_meta(doctype)
    result = []

    SKIP_TYPES = {"Section Break", "Column Break", "HTML", "Fold", "Heading",
                  "Tab Break", "Button", "Image", "Geolocation"}

    for f in meta.fields:
        if f.fieldtype in SKIP_TYPES:
            continue
        entry = {
            "fieldname":      f.fieldname,
            "label":          f.label or f.fieldname,
            "fieldtype":      f.fieldtype,
            "options":        f.options or None,
            "reqd":           bool(f.reqd),
            "in_list_view":   bool(f.in_list_view),
            "is_child_table": f.fieldtype == "Table",
            "child_doctype":  f.options if f.fieldtype == "Table" else None,
        }
        result.append(entry)

        # If this is a Table field, recurse one level to get child fields
        if f.fieldtype == "Table" and f.options:
            try:
                child_fields = get_doctype_fields(f.options)
                for cf in child_fields:
                    cf["parent_table_fieldname"] = f.fieldname
                    cf["parent_table_label"]     = f.label or f.fieldname
                result.extend(child_fields)
            except Exception:
                pass  # child doctype might not exist in this instance

    return result


def auto_map(source_headers: list[str], doctype_fields: list[dict]) -> dict[str, str | None]:
    """
    For each source header return the best-matching fieldname, or None.
    Matching priority:
      1. Exact match (normalised)
      2. One token fully contains the other
      3. Longest common subsequence score ≥ 0.6
    """
    mapping: dict[str, str | None] = {}
    target_fields = [f for f in doctype_fields if not f["is_child_table"]]

    for header in source_headers:
        mapping[header] = _best_match(header, target_fields)

    return mapping


def detect_column_type(values: list[str]) -> str:
    """
    Infer the likely Frappe fieldtype from a sample of raw cell values.
    Returns one of: Date, Datetime, Int, Float, Currency, Check, Data
    """
    non_empty = [v.strip() for v in values if v and str(v).strip()]
    if not non_empty:
        return "Data"

    import re

    date_rx      = re.compile(r"^\d{4}-\d{2}-\d{2}$|^\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}$")
    datetime_rx  = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}")
    int_rx       = re.compile(r"^-?\d+$")
    float_rx     = re.compile(r"^-?\d+\.\d+$")
    currency_rx  = re.compile(r"^[$€£₦]?\s*[\d,]+(\.\d{1,2})?$")
    bool_vals    = {"0", "1", "true", "false", "yes", "no", "y", "n"}

    if all(datetime_rx.match(v) for v in non_empty):  return "Datetime"
    if all(date_rx.match(v)     for v in non_empty):  return "Date"
    if all(v.lower() in bool_vals for v in non_empty): return "Check"
    if all(currency_rx.match(v.replace(",", "")) for v in non_empty): return "Currency"
    if all(float_rx.match(v)    for v in non_empty):  return "Float"
    if all(int_rx.match(v)      for v in non_empty):  return "Int"
    return "Data"


# ── Internal helpers ──────────────────────────────────────────────────────────

def _normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _best_match(header: str, fields: list[dict]) -> str | None:
    norm_header = _normalise(header)
    if not norm_header:
        return None

    best_field    = None
    best_score    = 0.0

    for f in fields:
        norm_fn    = _normalise(f["fieldname"])
        norm_label = _normalise(f["label"])

        # Exact match wins immediately
        if norm_header == norm_fn or norm_header == norm_label:
            return f["fieldname"]

        # Containment score
        for norm_target in (norm_fn, norm_label):
            if norm_header in norm_target or norm_target in norm_header:
                longer  = max(len(norm_header), len(norm_target))
                shorter = min(len(norm_header), len(norm_target))
                score   = shorter / longer * 0.9  # slightly below LCS
                if score > best_score:
                    best_score = score
                    best_field = f["fieldname"]

        # LCS score
        score = _lcs_score(norm_header, norm_fn)
        if score > best_score:
            best_score = score
            best_field = f["fieldname"]

    return best_field if best_score >= 0.55 else None


def _lcs_score(a: str, b: str) -> float:
    """Normalised LCS length / max(len(a), len(b))."""
    if not a or not b:
        return 0.0
    m, n  = len(a), len(b)
    dp    = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            dp[i][j] = dp[i-1][j-1] + 1 if a[i-1] == b[j-1] else max(dp[i-1][j], dp[i][j-1])
    return dp[m][n] / max(m, n)