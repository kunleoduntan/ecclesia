# export_fixtures.py
# Ecclesia — safe fixture export script for records that can't use
# module= filter (custom DocTypes without a module column).
#
# Deploy: apps/ecclesia/ecclesia/scripts/export_fixtures.py
#
# Usage:
#   # Export everything
#   bench --site default execute ecclesia.scripts.export_fixtures.run
#
#   # Export one specific doctype only
#   bench --site default execute ecclesia.scripts.export_fixtures.run \
#         --kwargs '{"only": "Compliance Rule"}'
#
# What this exports (complements hooks.py fixtures):
#   - WFH Activity Mapping   → fixtures/wfh_activity_mapping.json
#   - Regulatory Authority   → fixtures/regulatory_authority.json
#   - Compliance Rule        → fixtures/compliance_rule.json
#   - Compliance Policy      → fixtures/compliance_policy.json
#   (add more below as needed)
#
# This script is safe because it:
#   1. Checks frappe.db.table_exists() before querying
#   2. Catches all exceptions per-doctype — one failure never blocks the rest
#   3. Writes to separate JSON files per DocType — keeps fixtures organised
#   4. Reports exactly what was exported and what was skipped

from __future__ import annotations

import json
import os

import frappe

# ─── Export targets ────────────────────────────────────────────────────────────
# Each entry: (DocType name, output filename, filters)
# filters=None → export ALL records of that DocType
# filters=dict → passed to frappe.get_all as filters

EXPORT_TARGETS = [
    {
        "dt":       "WFH Activity Mapping",
        "file":     "wfh_activity_mapping.json",
        "filters":  None,
        "fields":   ["name", "doctype_name", "activity_type",
                     "points", "is_active", "description"],
    },
    {
        "dt":       "Regulatory Authority",
        "file":     "regulatory_authority.json",
        "filters":  None,
        "fields":   ["name", "authority_name", "authority_type",
                     "country", "website", "notes"],
    },
    {
        "dt":       "Compliance Rule",
        "file":     "compliance_rule.json",
        "filters":  None,
        "fields":   ["name", "rule_code", "rule_title", "category",
                     "obligation_type", "penalty_amount", "is_active",
                     "description", "legal_reference"],
    },
    {
        "dt":       "Compliance Policy",
        "file":     "compliance_policy.json",
        "filters":  None,
        "fields":   ["name", "policy_name", "policy_type",
                     "effective_date", "is_active"],
    },
]


def _fixtures_dir() -> str:
    """Return absolute path to ecclesia/fixtures/."""
    app_path = frappe.get_app_path("ecclesia")
    return os.path.join(app_path, "fixtures")


def _export_one(target: dict) -> dict:
    """
    Export one DocType to its fixture JSON file.
    Returns a result dict: {dt, file, count, status, error}.
    """
    dt      = target["dt"]
    fname   = target["file"]
    filters = target.get("filters") or {}
    fields  = target.get("fields")  or ["name"]

    result = {"dt": dt, "file": fname, "count": 0, "status": "ok", "error": None}

    try:
        # Safety: don't query if the table doesn't exist yet
        if not frappe.db.table_exists(f"tab{dt}"):
            result["status"] = "skipped"
            result["error"]  = f"tab{dt} does not exist — run bench migrate first"
            return result

        records = frappe.get_all(dt, filters=filters, fields=fields)

        if not records:
            result["status"] = "empty"
            result["count"]  = 0
            # Still write an empty array so import-fixtures doesn't fail
            # if the file is referenced elsewhere

        # Add doctype field so Frappe knows what to import
        for rec in records:
            rec["doctype"] = dt

        out_path = os.path.join(_fixtures_dir(), fname)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, default=str)

        result["count"] = len(records)

    except Exception as e:
        result["status"] = "error"
        result["error"]  = str(e)

    return result


def run(only: str = None):
    """
    Export all targets (or just one if only=DocType name is given).

    bench --site default execute ecclesia.scripts.export_fixtures.run
    bench --site default execute ecclesia.scripts.export_fixtures.run \
          --kwargs '{"only": "Compliance Rule"}'
    """
    targets = [t for t in EXPORT_TARGETS
               if only is None or t["dt"] == only]

    if not targets:
        frappe.throw(f"No export target found for: {only!r}")

    results   = []
    ok_count  = 0
    err_count = 0

    print(f"\n{'='*60}")
    print(f"Ecclesia Fixture Export")
    print(f"Fixtures dir: {_fixtures_dir()}")
    print(f"{'='*60}\n")

    for target in targets:
        res = _export_one(target)
        results.append(res)

        if res["status"] == "ok":
            print(f"  ✅  {res['dt']:<35} {res['count']:>4} records → {res['file']}")
            ok_count += 1
        elif res["status"] == "empty":
            print(f"  ⬜  {res['dt']:<35}    0 records → {res['file']} (empty table)")
            ok_count += 1
        elif res["status"] == "skipped":
            print(f"  ⏭   {res['dt']:<35} SKIPPED — {res['error']}")
        else:
            print(f"  ❌  {res['dt']:<35} ERROR — {res['error']}")
            err_count += 1

    print(f"\n{'='*60}")
    print(f"Done — {ok_count} exported, {err_count} errors")
    print(f"{'='*60}\n")

    return results