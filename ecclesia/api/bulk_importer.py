# ecclesia/api/bulk_importer.py
#
# ── Architecture ─────────────────────────────────────────────────────────────
#
# validate_import and run_import receive data DIRECTLY as arguments.
# They no longer create or read a Bulk Import Log as a data transport layer.
#
# Why: frappe.client.insert silently drops any key that is not a defined
# schema field on the target DocType. If field_mapping / import_data were not
# real schema fields on "Bulk Import Log", they came back as None after insert,
# mapped_fnames became {}, and every required field falsely appeared unmapped.
#
# A Bulk Import Log is still created — but ONLY after a successful import,
# for audit purposes only, using _try_set helpers that check field existence
# before writing so it is safe regardless of the schema.
#
# ── Field mapping ────────────────────────────────────────────────────────────
#
# auto_map_with_samples delegates to ecclesia.utils.field_mapper which uses
# a proper LCS algorithm. The inline SequenceMatcher fallback is kept for
# cases where field_mapper is unavailable.
#
# ── JSON import ──────────────────────────────────────────────────────────────
#
# parse_uploaded_file stores list-of-dicts in rows_raw for JSON files.
# _row_to_dict detects dict rows and returns them as-is, so the import
# loop handles both CSV/XLSX (list-of-lists) and JSON (list-of-dicts)
# without any extra branching in callers.
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import base64
import csv
import io
import json
import re
import time
from difflib import SequenceMatcher

import frappe

try:
    import openpyxl
except ImportError:
    openpyxl = None

try:
    from ecclesia.utils.field_mapper import (
        auto_map,
        detect_column_type,
        get_doctype_fields as fm_get_doctype_fields,
    )
    _FIELD_MAPPER_AVAILABLE = True
except ImportError:
    _FIELD_MAPPER_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _parse_arg(value, default):
    """Parse a JSON string arg that Frappe may pass as str or already-parsed."""
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default


def _row_to_dict(row, mapping):
    """
    Normalise a row to {col_header: value}.
    dict  → returned as-is (JSON upload path).
    list  → zipped with mapping key order (CSV/XLSX path).
    """
    if isinstance(row, dict):
        return row
    headers = list(mapping.keys())
    if len(headers) >= len(row):
        return dict(zip(headers, row))
    extra = [str(i) for i in range(len(headers), len(row))]
    return dict(zip(headers + extra, row))


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _try_set(doc, fieldname, value):
    """Set a field only if it exists in the doc's schema."""
    try:
        if frappe.get_meta(doc.doctype).has_field(fieldname):
            doc.set(fieldname, value)
    except Exception:
        pass


def _try_set_json(doc, fieldname, value):
    """Set a Long Text / Text / Code field only if it exists."""
    LONG_TYPES = {"Long Text", "Text", "Code", "Small Text"}
    try:
        df = frappe.get_meta(doc.doctype).get_field(fieldname)
        if df and df.fieldtype in LONG_TYPES:
            doc.set(fieldname, json.dumps(value))
    except Exception:
        pass


def _create_audit_log(doctype, mapping, rows, result,
                      duplicate_action, date_format, file_name):
    """
    Create a Bulk Import Log for audit AFTER import completes.
    Never raises — failure here must not mask the import result.
    """
    try:
        doc  = frappe.new_doc("Bulk Import Log")
        meta = frappe.get_meta("Bulk Import Log")

        for fname in ("doctype_name", "reference_doctype"):
            if meta.has_field(fname):
                doc.set(fname, doctype)
                break

        _try_set(doc, "file_name",        file_name)
        _try_set(doc, "duplicate_action", duplicate_action)
        _try_set(doc, "date_format",      date_format)
        _try_set(doc, "status",
                 "Completed" if result["errors"] == 0 else "Partially Completed")
        _try_set(doc, "success_count", result["success"])
        _try_set(doc, "skipped_count", result["skipped"])
        _try_set(doc, "error_count",   result["errors"])
        _try_set(doc, "time_taken",    result["time_taken"])
        _try_set_json(doc, "field_mapping", mapping)
        _try_set_json(doc, "import_data",   rows)

        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return doc.name
    except Exception:
        frappe.log_error(frappe.get_traceback(),
                         "bulk_importer: audit log creation failed")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1 — DocType picker
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_all_doctypes():
    """
    Return all importable DocTypes grouped by module.
    Response: { "modules": { "<Module>": [{name, description}, …], … } }
    """
    EXCLUDE = {
        "DocType", "DocField", "DocPerm", "Custom Field", "Property Setter",
        "System Settings", "Patch Log", "Error Log", "Scheduled Job Log",
        "Activity Log", "Access Log", "Energy Point Log", "File",
        "Communication", "Comment", "Version", "View Log",
    }

    records = frappe.get_all(
        "DocType",
        filters={"istable": 0, "issingle": 0, "is_virtual": 0},
        fields=["name", "module", "description"],
        order_by="module asc, name asc",
    )

    modules = {}
    for r in records:
        if r.name in EXCLUDE:
            continue
        modules.setdefault(r.module or "Other", []).append({
            "name":        r.name,
            "description": r.description or "",
        })

    return {"modules": modules}


@frappe.whitelist()
def get_doctype_fields(doctype):
    """
    Return all usable fields for a DocType including child-table fields.
    Delegates to field_mapper when available; falls back to inline logic.

    Response: { "fields": [{fieldname, label, fieldtype, reqd, options,
                             is_child_table, parent_table_label}, …] }
    """
    frappe.has_permission(doctype, throw=True)

    if _FIELD_MAPPER_AVAILABLE:
        raw    = fm_get_doctype_fields(doctype)
        fields = [{
            "fieldname":          f["fieldname"],
            "label":              f["label"],
            "fieldtype":          f["fieldtype"],
            "reqd":               f["reqd"],
            "options":            f["options"] or "",
            "is_child_table":     f["is_child_table"],
            "parent_table_label": f.get("parent_table_label", ""),
        } for f in raw]
        return {"fields": fields}

    # ── Inline fallback ──────────────────────────────────────────────────────
    SKIP = {"Section Break", "Column Break", "Tab Break", "HTML",
            "Fold", "Heading", "Button", "Image", "Geolocation"}

    meta   = frappe.get_meta(doctype)
    fields = []

    for f in meta.fields:
        if f.fieldtype in SKIP:
            continue
        fields.append({
            "fieldname":          f.fieldname,
            "label":              f.label or f.fieldname,
            "fieldtype":          f.fieldtype,
            "reqd":               bool(f.reqd),
            "options":            f.options or "",
            "is_child_table":     False,
            "parent_table_label": "",
        })

    for f in meta.fields:
        if f.fieldtype != "Table" or not f.options:
            continue
        try:
            child_meta = frappe.get_meta(f.options)
        except Exception:
            continue
        for cf in child_meta.fields:
            if cf.fieldtype in SKIP:
                continue
            fields.append({
                "fieldname":          cf.fieldname,
                "label":              cf.label or cf.fieldname,
                "fieldtype":          cf.fieldtype,
                "reqd":               bool(cf.reqd),
                "options":            cf.options or "",
                "is_child_table":     True,
                "parent_table_label": f.label or f.fieldname,
            })

    return {"fields": fields}


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Upload / parse file
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def parse_uploaded_file(file_name, file_content_b64):
    """
    Parse a base-64 encoded file from the browser.
    Supports CSV, XLSX/XLS, JSON (list-of-objects or wrapped dict).

    Response:
        {
          "format":         "csv" | "xlsx" | "json",
          "is_multi_sheet": bool,
          "sheets": {
            "<n>": {
              "headers":  [str, …],
              "rows":     [[str, …], …],   # preview (always list-of-lists)
              "rows_raw": [{…}, …],        # JSON only: full list-of-dicts
              "total":    int
            }
          }
        }

    For JSON files, rows_raw holds the complete list-of-dicts so that
    _row_to_dict() can return them as-is at import time without information
    loss from the list-of-lists conversion in rows (preview only).
    """
    try:
        raw = base64.b64decode(file_content_b64)
    except Exception:
        return {"error": "Could not decode file — ensure it is base-64 encoded."}

    ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""

    if ext == "csv":              return _parse_csv(raw)
    if ext in ("xlsx", "xls"):   return _parse_xlsx(raw)
    if ext == "json":             return _parse_json(raw)

    return {"error": f"Unsupported format '.{ext}'. Use CSV, XLSX, or JSON."}


def _parse_csv(raw):
    text   = raw.decode("utf-8-sig", errors="replace")
    reader = list(csv.reader(io.StringIO(text)))
    if not reader:
        return {"error": "The CSV file is empty."}
    headers = [h.strip() for h in reader[0]]
    rows    = [r for r in reader[1:] if any(c.strip() for c in r)]
    return {
        "format": "csv", "is_multi_sheet": False,
        "sheets": {"Sheet1": {"headers": headers, "rows": rows[:100], "total": len(rows)}},
    }


def _parse_xlsx(raw):
    if not openpyxl:
        return {"error": "openpyxl is not installed. Run: bench pip install openpyxl"}
    try:
        wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    except Exception as e:
        return {"error": f"Could not open Excel file: {e}"}

    sheets = {}
    for name in wb.sheetnames:
        ws       = wb[name]
        all_rows = list(ws.iter_rows(values_only=True))
        if not all_rows:
            continue
        headers = [str(c).strip() if c is not None else "" for c in all_rows[0]]
        rows    = [
            [str(c) if c is not None else "" for c in r]
            for r in all_rows[1:]
            if any(c is not None for c in r)
        ]
        sheets[name] = {"headers": headers, "rows": rows[:100], "total": len(rows)}

    return {"format": "xlsx", "is_multi_sheet": len(sheets) > 1, "sheets": sheets}


def _parse_json(raw):
    """
    Parse JSON.  Accepts list-of-objects or {"data": […]} (any wrapper key).
    rows_raw stores the full list-of-dicts for import.
    rows stores list-of-lists for the UI preview table.
    """
    try:
        data = json.loads(raw.decode("utf-8", errors="replace"))
    except Exception as e:
        return {"error": f"Invalid JSON: {e}"}

    if isinstance(data, dict):
        for key in ("data", "rows", "records", "items"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
        else:
            for v in data.values():
                if isinstance(v, list):
                    data = v
                    break
            else:
                data = []

    if not isinstance(data, list) or not data:
        return {"error": "JSON must contain a non-empty list of objects."}
    if not isinstance(data[0], dict):
        return {"error": "Each JSON element must be an object ({key: value, …})."}

    headers      = list(dict.fromkeys(k for row in data for k in row.keys()))
    preview_rows = [[str(row.get(h, "")) for h in headers] for row in data[:100]]

    return {
        "format": "json", "is_multi_sheet": False,
        "sheets": {
            "Sheet1": {
                "headers":  headers,
                "rows":     preview_rows,   # list-of-lists for UI
                "rows_raw": data,           # list-of-dicts for import
                "total":    len(data),
            }
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Field mapping
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def auto_map_with_samples(doctype, column_data_json):
    """
    Auto-map column headers → fieldnames, detect column types from samples.
    Uses field_mapper (LCS algorithm) when available; falls back to inline
    SequenceMatcher.

    Args:
        doctype:          target DocType
        column_data_json: JSON { col_header: [sample_val, …], … }

    Response:
        {
          "mapping":        { col_header: fieldname | "__ignore__" },
          "detected_types": { col_header: "Date"|"Datetime"|"Float"|"Int"|"Currency"|"Check"|"Data" },
          "fields":         […same shape as get_doctype_fields…]
        }
    """
    frappe.has_permission(doctype, throw=True)

    col_data     = _parse_arg(column_data_json, {})
    headers      = list(col_data.keys())
    fields_resp  = get_doctype_fields(doctype)
    fields       = fields_resp["fields"]

    if _FIELD_MAPPER_AVAILABLE:
        fm_fields   = fm_get_doctype_fields(doctype)
        raw_mapping = auto_map(headers, fm_fields)
        mapping     = {col: (fn or "__ignore__") for col, fn in raw_mapping.items()}
        detected    = {
            col: detect_column_type([str(v) for v in samples if v is not None])
            for col, samples in col_data.items()
        }
    else:
        mapping, detected = _inline_auto_map(headers, col_data, fields)

    return {"mapping": mapping, "detected_types": detected, "fields": fields}


def _inline_auto_map(headers, col_data, fields):
    """Fallback auto-map using normalised exact + SequenceMatcher fuzzy match."""
    field_index = {}
    for f in fields:
        field_index[_norm(f["label"])]     = f["fieldname"]
        field_index[_norm(f["fieldname"])] = f["fieldname"]

    mapping  = {}
    detected = {}

    for col in headers:
        norm_col = _norm(col)
        if norm_col in field_index:
            mapping[col] = field_index[norm_col]
        else:
            best_score, best_fn = 0.0, "__ignore__"
            for label_norm, fn in field_index.items():
                score = SequenceMatcher(None, norm_col, label_norm).ratio()
                if score > best_score:
                    best_score, best_fn = score, fn
            mapping[col] = best_fn if best_score >= 0.72 else "__ignore__"

        detected[col] = _detect_type_inline(col_data.get(col, []))

    return mapping, detected


def _detect_type_inline(samples):
    non_empty = [str(s).strip() for s in samples if s not in (None, "", "None")]
    if not non_empty:
        return "Data"

    date_re     = re.compile(r"^\d{4}-\d{2}-\d{2}$|^\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}$")
    datetime_re = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}")

    if all(datetime_re.match(v) for v in non_empty): return "Datetime"
    if all(date_re.match(v)     for v in non_empty): return "Date"

    bool_vals = {"0", "1", "true", "false", "yes", "no", "y", "n"}
    if all(v.lower() in bool_vals for v in non_empty): return "Check"

    def _is_float(v):
        try:
            float(v.replace(",", ""))
            return True
        except ValueError:
            return False

    if all(_is_float(v) for v in non_empty):
        return "Float" if any("." in v for v in non_empty) else "Int"

    return "Data"


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Validate  (data passed directly — no log round-trip)
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def validate_import(doctype, mapping_json, rows_json):
    """
    Validate rows against a DocType without inserting anything.

    Args:
        doctype:      target DocType name
        mapping_json: JSON { col_header: fieldname | "__ignore__" }
        rows_json:    JSON [[…], …] list-of-lists  OR  [{…}, …] list-of-dicts

    Response:
        {
          "status":  "ok" | "error",
          "message": str,          # only present on error
          "details": {
            "total_rows":         int,
            "rows_with_errors":   int,
            "rows_with_warnings": int,
            "blockers":           [{field, label, fieldtype, message}, …],
            "row_issues":         { "1": {errors:[…], warnings:[]}, … }
          }
        }
    """
    try:
        return _validate_inner(doctype, mapping_json, rows_json)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "validate_import error")
        return {
            "status": "error", "message": str(e),
            "details": {
                "total_rows": 0, "rows_with_errors": 0, "rows_with_warnings": 0,
                "blockers": [], "row_issues": {},
            },
        }


def _validate_inner(doctype, mapping_json, rows_json):
    frappe.has_permission(doctype, throw=True)

    mapping = _parse_arg(mapping_json, {})
    rows    = _parse_arg(rows_json, [])

    meta          = frappe.get_meta(doctype)
    reqd_fields   = [f for f in meta.fields if f.reqd]
    mapped_fnames = {v for v in mapping.values() if v and v != "__ignore__"}

    # Structural blockers — required fields with no mapping at all
    blockers = [
        {
            "field":     f.fieldname,
            "label":     f.label or f.fieldname,
            "fieldtype": f.fieldtype,
            "message":   f"Required field '{f.label or f.fieldname}' is not mapped.",
        }
        for f in reqd_fields
        if f.fieldname not in mapped_fnames
    ]

    if blockers:
        return {
            "status": "error",
            "details": {
                "total_rows": len(rows), "rows_with_errors": 0,
                "rows_with_warnings": 0, "blockers": blockers, "row_issues": {},
            },
        }

    fn_to_col        = {v: k for k, v in mapping.items() if v and v != "__ignore__"}
    rows_with_errors = 0
    row_issues       = {}

    for i, raw_row in enumerate(rows):
        row_dict = _row_to_dict(raw_row, mapping)
        errors   = []
        for f in reqd_fields:
            col = fn_to_col.get(f.fieldname, f.fieldname)
            if not str(row_dict.get(col, "")).strip():
                errors.append({
                    "field":   f.fieldname,
                    "label":   f.label or f.fieldname,
                    "message": f"'{f.label or f.fieldname}' is empty on this row.",
                })
        if errors:
            rows_with_errors += 1
            row_issues[str(i + 1)] = {"errors": errors, "warnings": []}

    return {
        "status": "ok",
        "details": {
            "total_rows":         len(rows),
            "rows_with_errors":   rows_with_errors,
            "rows_with_warnings": 0,
            "blockers":           [],
            "row_issues":         row_issues,
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Templates
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def save_template(doctype, template_name, mapping_json,
                  duplicate_action="Skip", date_format="YYYY-MM-DD"):
    """Save a mapping template. Uses 'Bulk Import Template' DocType if it
    exists; otherwise stores in Frappe cache."""
    if frappe.db.exists("DocType", "Bulk Import Template"):
        existing = frappe.db.get_value(
            "Bulk Import Template",
            {"reference_doctype": doctype, "template_name": template_name},
            "name",
        )
        doc = (
            frappe.get_doc("Bulk Import Template", existing)
            if existing else frappe.new_doc("Bulk Import Template")
        )
        if not existing:
            doc.reference_doctype = doctype
            doc.template_name     = template_name
        doc.field_mapping     = mapping_json
        doc.duplicate_action  = duplicate_action
        doc.date_format       = date_format
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        return {"name": doc.name, "template_name": template_name}

    key = f"bi_tpl_{frappe.scrub(doctype)}_{frappe.scrub(template_name)}"
    frappe.cache().set_value(key, json.dumps({
        "name": key, "template_name": template_name,
        "field_mapping": mapping_json, "duplicate_action": duplicate_action,
        "date_format": date_format, "is_default": False,
    }))
    return {"name": key, "template_name": template_name}


@frappe.whitelist()
def get_templates(doctype):
    """Return saved templates for a DocType."""
    if frappe.db.exists("DocType", "Bulk Import Template"):
        return frappe.get_all(
            "Bulk Import Template",
            filters={"reference_doctype": doctype},
            fields=["name", "template_name", "field_mapping",
                    "duplicate_action", "date_format", "is_default"],
            order_by="template_name asc",
        )
    return []


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4 — Run import  (data passed directly — no log round-trip)
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def run_import(doctype, mapping_json, rows_json,
               duplicate_action="Skip", date_format="YYYY-MM-DD",
               file_name="import.csv"):
    """
    Execute the import.  Data arrives directly as arguments.

    Args:
        doctype:          target DocType
        mapping_json:     JSON { col_header: fieldname | "__ignore__" }
        rows_json:        JSON [[…],…] or [{…},…]
        duplicate_action: "Skip" | "Update" | "Create New"
        date_format:      stored in audit log for display only
        file_name:        stored in audit log

    Response:
        { "status": "ok"|"error", "details": { success, skipped, errors, … } }
    """
    try:
        return _run_import_inner(
            doctype, mapping_json, rows_json,
            duplicate_action, date_format, file_name,
        )
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "run_import error")
        return {
            "status": "error", "message": str(e),
            "details": {
                "success": 0, "skipped": 0, "errors": 1,
                "time_taken": 0, "success_rate": 0,
                "error_details":   [{"row": 0, "field": "", "message": str(e)}],
                "success_details": [],
                "import_log_name": None,
            },
        }


def _run_import_inner(doctype, mapping_json, rows_json,
                      duplicate_action, date_format, file_name):
    frappe.has_permission(doctype, throw=True)

    mapping = _parse_arg(mapping_json, {})
    rows    = _parse_arg(rows_json, [])

    meta  = frappe.get_meta(doctype)
    start = time.time()

    success_count   = 0
    skipped_count   = 0
    error_details   = []
    success_details = []

    for i, raw_row in enumerate(rows):
        row_num  = i + 1
        row_dict = _row_to_dict(raw_row, mapping)

        try:
            doc_data = {"doctype": doctype}
            for col, fieldname in mapping.items():
                if not fieldname or fieldname == "__ignore__":
                    continue
                val = str(row_dict.get(col, "")).strip()
                if val:
                    doc_data[fieldname] = val

            existing_name = _find_existing(doctype, doc_data, meta)

            if existing_name:
                if duplicate_action == "Skip":
                    skipped_count += 1
                    continue
                if duplicate_action == "Update":
                    upd = frappe.get_doc(doctype, existing_name)
                    upd.update(doc_data)
                    upd.save(ignore_permissions=True)
                    success_count += 1
                    success_details.append(
                        {"row": row_num, "name": existing_name, "action": "updated"}
                    )
                    continue
                # "Create New" falls through

            new_doc = frappe.get_doc(doc_data)
            new_doc.insert(ignore_permissions=True)
            success_count += 1
            success_details.append(
                {"row": row_num, "name": new_doc.name, "action": "created"}
            )

        except Exception as e:
            error_details.append({"row": row_num, "field": "", "message": str(e)})

    frappe.db.commit()

    time_taken   = round(time.time() - start, 2)
    total        = len(rows)
    success_rate = round((success_count / total) * 100, 1) if total else 0

    result = {
        "success":         success_count,
        "skipped":         skipped_count,
        "errors":          len(error_details),
        "time_taken":      time_taken,
        "success_rate":    success_rate,
        "error_details":   error_details[:50],
        "success_details": success_details[:50],
    }

    log_name = _create_audit_log(
        doctype, mapping, rows, result,
        duplicate_action, date_format, file_name,
    )
    result["import_log_name"] = log_name

    return {"status": "ok", "details": result}


def _find_existing(doctype, doc_data, meta):
    title_field = meta.title_field or "name"
    val = doc_data.get(title_field)
    if not val:
        return None
    try:
        return frappe.db.get_value(doctype, {title_field: val}, "name")
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — Download CSV template
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def download_template(doctype, file_format="csv"):
    """Return base-64 CSV with the header row for a DocType."""
    frappe.has_permission(doctype, throw=True)
    fields_resp = get_doctype_fields(doctype)
    headers     = [f["label"] for f in fields_resp["fields"] if not f["is_child_table"]]
    buf         = io.StringIO()
    csv.writer(buf).writerow(headers)
    encoded = base64.b64encode(buf.getvalue().encode("utf-8")).decode("utf-8")
    return {"filename": f"{frappe.scrub(doctype)}_template.csv", "content": encoded}


# ═══════════════════════════════════════════════════════════════════════════════
# STANDALONE — direct import via file_url (not the wizard)
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def bulk_import(doctype, file_url, field_map):
    """
    Import from an already-uploaded Frappe File record.
    field_map: { frappe_fieldname: spreadsheet_column_header }
    """
    from ecclesia.utils.import_engine import run_import as engine_run

    if isinstance(field_map, str):
        field_map = json.loads(field_map)

    if not doctype:   frappe.throw("doctype is required")
    if not file_url:  frappe.throw("file_url is required")
    if not field_map: frappe.throw("field_map is required")

    return engine_run(doctype=doctype, file_url=file_url, field_map=field_map)


# ═══════════════════════════════════════════════════════════════════════════════
# STANDALONE — progress polling for parallel bulk_import jobs
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_import_progress(job_id):
    """Poll progress of a parallel import job.
    Response: { status, processed, errors, total }"""
    if not job_id:
        frappe.throw("job_id is required")

    raw = frappe.cache().get_value(f"bulk_import_{job_id}")
    if not raw:
        return {"status": "not_found", "processed": 0, "total": 0, "errors": 0}

    data = json.loads(raw)
    if data.get("processed", 0) + data.get("errors", 0) >= data.get("total", 1):
        data["status"] = "done"
        frappe.cache().set_value(f"bulk_import_{job_id}", json.dumps(data))

    return data