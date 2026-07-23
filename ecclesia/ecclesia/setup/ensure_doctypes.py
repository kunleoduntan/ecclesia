# Copyright (c) 2026, kunle Oduntan and contributors
# For license information, please see license.txt

"""
Self-healing DocType installer.

WHY THIS EXISTS
────────────────
These 14 DocTypes keep disappearing after `bench migrate`. The two most
common root causes for that symptom in Frappe:

  1. The DocType's .json file was never actually written to the correct
     on-disk location for its module (`apps/{app}/{app}/{module}/doctype/
     {name}/{name}.json`), or the module isn't registered in modules.txt.
     `bench migrate` walks disk to sync — if a DocType exists only in the
     database with no matching file, migrate's sync step has nothing to
     re-create it from, and any process that reconciles DB-vs-disk state
     (drift cleanup, a stale patch, a fixture uninstall, etc.) can remove it.
  2. The DocType was created via Desk UI but under conditions where the
     file export silently failed (e.g. developer_mode toggled off at some
     point, or the module didn't resolve to a real folder).

The permanent fix is to get these files correctly placed under the app's
real module/doctype folder structure so `bench migrate`'s normal sync
handles them like any other standard DocType — no custom code needed at
that point. This installer is the safety net in the meantime (and forever,
if you want the extra insurance): it does NOT touch the filesystem sync
mechanism at all. Instead, it holds the full JSON definition for each
DocType directly, and after every migrate (or on demand), checks whether
each one exists in the database — if not, it recreates it from the bundled
definition. This works regardless of where the files physically live.

USAGE
─────
1. Drop this file at:  ecclesia/ecclesia/setup/ensure_doctypes.py
2. Drop the fixtures/ folder (all 14 .json files) alongside it at:
   ecclesia/ecclesia/setup/fixtures/
3. Wire it up one of three ways (pick any/all):

   a) Automatically after every `bench migrate` — add to hooks.py:
        after_migrate = ["ecclesia.ecclesia.setup.ensure_doctypes.ensure_doctypes_exist"]
      (If `after_migrate` already exists in hooks.py as a list, just
      append this string to it instead of overwriting.)

   b) On demand, zero extra setup, using Frappe's built-in `execute` command:
        bench --site your-site.local execute ecclesia.ecclesia.setup.ensure_doctypes.ensure_doctypes_exist

   c) On demand, via the custom `bench ensure-doctypes` command — see
      commands.py in this bundle for the one-line hooks.py wiring.
"""

import json
import os

import frappe

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _load_fixtures():
    """Yield (filename, dict) for every .json file in the fixtures folder."""
    if not os.path.isdir(FIXTURE_DIR):
        frappe.logger().warning(f"ensure_doctypes: fixture dir not found at {FIXTURE_DIR}")
        return

    for fname in sorted(os.listdir(FIXTURE_DIR)):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(FIXTURE_DIR, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                yield fname, json.load(f)
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"ensure_doctypes: failed to parse {fname}")


def ensure_doctypes_exist(force_update=False):
    """
    Ensure every bundled DocType definition exists in the database.

    force_update=False (default): only CREATES doctypes that are missing.
        Never touches ones that already exist — safe to run on every
        migrate without clobbering any manual tweaks made via Desk.

    force_update=True: for doctypes that already exist, also re-applies
        the bundled field/layout definition (useful right after you've
        edited a fixture .json and want the DB to catch up without going
        through Desk). Existing data in the doctype's own table is NOT
        touched either way — this only ever affects the DocType's schema
        definition, never its records.

    Returns a summary dict: {created: [...], updated: [...], skipped: [...],
    failed: [{"name":..., "error":...}]}
    """
    created, updated, skipped, failed = [], [], [], []

    for fname, definition in _load_fixtures():
        doctype_name = definition.get("name")
        if not doctype_name:
            failed.append({"name": fname, "error": "fixture has no 'name' key"})
            continue

        try:
            exists = frappe.db.exists("DocType", doctype_name)

            if not exists:
                doc = frappe.get_doc(definition)
                doc.flags.ignore_permissions = True
                # New DocTypes route through frappe.core.doctype.doctype's
                # own validation (field_order coverage, naming rules, etc.)
                # — that's a feature here: if a fixture is malformed this
                # will raise instead of silently creating a broken doctype.
                doc.insert(ignore_permissions=True)
                frappe.db.commit()
                created.append(doctype_name)
                frappe.logger().info(f"ensure_doctypes: created '{doctype_name}'")

            elif force_update:
                doc = frappe.get_doc("DocType", doctype_name)
                incoming = frappe.get_doc(definition)
                # Replace field list, field_order, and layout-relevant
                # metadata from the fixture; preserve the existing doc's
                # own identity fields (name/owner/creation) by editing
                # the loaded doc in place rather than inserting a new one.
                doc.fields = incoming.fields
                doc.field_order = incoming.field_order
                for key in ("autoname", "naming_rule", "is_submittable", "istable",
                            "quick_entry", "track_changes", "sort_field", "sort_order",
                            "module", "engine", "editable_grid"):
                    if incoming.get(key) is not None:
                        doc.set(key, incoming.get(key))
                doc.flags.ignore_permissions = True
                doc.save(ignore_permissions=True)
                frappe.db.commit()
                updated.append(doctype_name)
                frappe.logger().info(f"ensure_doctypes: updated '{doctype_name}'")

            else:
                skipped.append(doctype_name)

        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(frappe.get_traceback(), f"ensure_doctypes: failed on '{doctype_name}'")
            failed.append({"name": doctype_name, "error": str(e)})

    summary = {"created": created, "updated": updated, "skipped": skipped, "failed": failed}

    msg = (f"ensure_doctypes_exist: {len(created)} created, {len(updated)} updated, "
           f"{len(skipped)} already present, {len(failed)} failed")
    print(msg)
    frappe.logger().info(msg)
    if failed:
        print("  Failures:")
        for f in failed:
            print(f"   - {f['name']}: {f['error']}")

    return summary


@frappe.whitelist()
def ensure_doctypes_exist_api(force_update=False):
    """Whitelisted wrapper so this can also be triggered from Desk
    (e.g. a server script, or a button on some admin page) without
    needing bench console access. System Manager only."""
    frappe.only_for("System Manager")
    if isinstance(force_update, str):
        force_update = force_update.lower() in ("1", "true", "yes")
    return ensure_doctypes_exist(force_update=force_update)
