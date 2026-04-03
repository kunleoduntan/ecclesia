# -*- coding: utf-8 -*-
# Copyright (c) 2026, Kunle Oduntan and contributors
# License: MIT

import frappe
from frappe.model.document import Document
import json


class DoctypeExport(Document):

	def validate(self):
		"""Ensure the export has something to work with."""
		if not self.module and not self.doctypes:
			frappe.throw(
				frappe._("Please specify a Module or add at least one DocType to the table."),
				title=frappe._("Nothing to Export"),
			)

	def before_save(self):
		"""
		If a module is set, auto-populate the child table.
		Existing manually-added rows are preserved and merged.
		"""
		if self.module:
			self._sync_doctypes_from_module()

	# ------------------------------------------------------------------
	# Private helpers
	# ------------------------------------------------------------------

	def _sync_doctypes_from_module(self):
		"""
		Merge every DocType in self.module into the child table.
		Rows already present are never duplicated.
		"""
		module_doctypes = frappe.get_all(
			"DocType",
			filters={"module": self.module},
			pluck="name",
			order_by="name",
		)

		if not module_doctypes:
			frappe.msgprint(
				frappe._("No DocTypes found in module {0}.").format(self.module),
				alert=True,
				indicator="orange",
			)
			return

		existing = {row.doctype_name for row in self.doctypes if row.doctype_name}

		added = 0
		for dt in module_doctypes:
			if dt not in existing:
				self.append("doctypes", {"doctype_name": dt})
				added += 1

		if added:
			frappe.msgprint(
				frappe._("Added {0} DocType(s) from module <b>{1}</b>.").format(added, self.module),
				alert=True,
				indicator="green",
			)


# ======================================================================
# Whitelisted API endpoints
# ======================================================================

@frappe.whitelist()
def get_doctype_fields_json(docname):
	"""
	Build the export payload and return it to the browser as a JSON string
	so the client-side JS can create a Blob download.

	Returns
	-------
	dict  { status, filename, data, summary }
	"""
	doc = _get_validated_doc(docname)
	dt_names = _resolve_doctype_names(doc)
	export_data, exported, failed = _build_export_payload(dt_names)

	if failed:
		frappe.log_error(
			title="[Doctype Export] Partial failure",
			message="\n".join(failed),
		)

	filename = frappe.scrub(doc.export_name or docname) + "_export.json"

	return {
		"status": "ok",
		"filename": filename,
		"data": frappe.as_json(export_data, indent=2),
		"summary": {
			"exported": exported,
			"failed": failed,
		},
	}


@frappe.whitelist()
def validate_export(docname):
	"""Dry-run — checks every listed DocType exists. No side-effects."""
	doc = _get_validated_doc(docname)
	dt_names = _resolve_doctype_names(doc)
	missing = [dt for dt in dt_names if not frappe.db.exists("DocType", dt)]

	if missing:
		return {
			"valid": False,
			"missing": missing,
			"message": frappe._("Missing DocType(s): {0}").format(", ".join(missing)),
		}

	return {
		"valid": True,
		"count": len(dt_names),
		"message": frappe._("Ready to export {0} DocType(s).").format(len(dt_names)),
	}


@frappe.whitelist()
def populate_from_module(docname):
	"""Manually trigger module population and save."""
	doc = frappe.get_doc("Doctype Export", docname)

	if not doc.module:
		frappe.throw(frappe._("No module is set on this document."))

	doc._sync_doctypes_from_module()
	doc.save(ignore_permissions=False)
	frappe.db.commit()

	return {
		"status": "ok",
		"count": len(doc.doctypes),
		"message": frappe._("Table populated with {0} DocType(s) from module {1}.").format(
			len(doc.doctypes), doc.module
		),
	}


@frappe.whitelist()
def get_module_doctypes(module):
	"""Return a quick list of DocTypes in a module (used by UI preview)."""
	if not module:
		return []

	return frappe.get_all(
		"DocType",
		filters={"module": module},
		fields=["name", "istable", "issingle"],
		order_by="name",
	)


# ======================================================================
# Private helpers  (not whitelisted — never exposed to the browser)
# ======================================================================

def _get_validated_doc(docname):
	doc = frappe.get_doc("Doctype Export", docname)

	if not doc.module and not doc.doctypes:
		frappe.throw(
			frappe._("No module or DocTypes defined on this export."),
			title=frappe._("Nothing to Export"),
		)

	return doc


def _resolve_doctype_names(doc):
	"""
	Deduplicated ordered list of DocType names to export.

	Logic
	-----
	- If module is set  → all DocTypes in that module, then merge table rows.
	- If no module      → only the table rows.

	This means the table always acts as an extension/override regardless.
	"""
	names = []
	seen = set()

	def _add(name):
		if name and name not in seen:
			seen.add(name)
			names.append(name)

	if doc.module:
		for dt in frappe.get_all(
			"DocType",
			filters={"module": doc.module},
			pluck="name",
			order_by="name",
		):
			_add(dt)

	for row in doc.doctypes:
		_add(row.doctype_name)

	if not names:
		frappe.throw(
			frappe._("No DocTypes resolved. Check the module name or the table."),
			title=frappe._("Nothing to Export"),
		)

	return names


def _build_export_payload(dt_names):
	"""Return (export_data, exported_list, failed_list)."""
	export_data = {}
	exported = []
	failed = []

	for dt in dt_names:
		try:
			if not frappe.db.exists("DocType", dt):
				failed.append(frappe._("DocType '{0}' does not exist.").format(dt))
				continue

			export_data[dt] = _export_single_doctype(dt)
			exported.append(dt)

		except Exception as exc:
			frappe.log_error(
				title=f"[Doctype Export] Failed: {dt}",
				message=frappe.get_traceback(),
			)
			failed.append(f"{dt}: {exc}")

	return export_data, exported, failed


# ======================================================================
# Replace _export_single_doctype entirely
# ======================================================================

def _export_single_doctype(dt):
    """
    Export a single DocType in ERPNext fixture/JSON format.
    Matches the structure used by `bench export-fixtures` and
    the JSON files found in ERPNext's module `doctype/` folders.
    """

    # Keys that are internal Frappe scaffolding — never written to fixtures
    STRIP_INTERNAL = frozenset({
        "creation", "modified", "modified_by", "owner",
        "docstatus", "idx",
        # child-row keys (present in as_dict() sub-lists)
        "parent", "parentfield", "parenttype", "name",
    })

    # Keys that exist on the DocType record itself but are noise in fixtures
    STRIP_DOCTYPE_KEYS = frozenset({
        "doctype",   # always re-added as "DocType" string below
    })

    doc = frappe.get_doc("DocType", dt)
    doc_dict = doc.as_dict()

    # ── Top-level cleanup ───────────────────────────────────────────────
    for key in STRIP_INTERNAL | STRIP_DOCTYPE_KEYS:
        doc_dict.pop(key, None)

    # ERPNext fixtures always carry this at the top
    doc_dict["doctype"] = "DocType"

    # ── Fields ──────────────────────────────────────────────────────────
    cleaned_fields = []
    for field in doc_dict.get("fields", []):
        cleaned = {
            k: v
            for k, v in field.items()
            if k not in STRIP_INTERNAL and v is not None and v != "" and v != 0
        }
        # fieldname and fieldtype must always be present
        if cleaned.get("fieldname") and cleaned.get("fieldtype"):
            cleaned_fields.append(cleaned)
    doc_dict["fields"] = cleaned_fields

    # ── Child tables (permissions, links, actions, states) ──────────────
    for section in ("permissions", "links", "actions", "states"):
        rows = doc_dict.get(section, [])
        doc_dict[section] = [
            {k: v for k, v in row.items() if k not in STRIP_INTERNAL and v is not None}
            for row in rows
        ]

    # ── Key order — match ERPNext fixture convention ─────────────────────
    KEY_ORDER = [
        "doctype", "name", "module", "custom",
        "autoname", "naming_rule", "is_submittable",
        "track_changes", "title_field", "sort_field", "sort_order",
        "description", "image_field",
        "fields", "permissions", "links", "actions", "states",
    ]
    ordered = {}
    for key in KEY_ORDER:
        if key in doc_dict:
            ordered[key] = doc_dict.pop(key)
    # Append any remaining keys not in the explicit order list
    ordered.update(doc_dict)

    return ordered


# ======================================================================
# Replace get_doctype_fields_json entirely
# ======================================================================

@frappe.whitelist()
def get_doctype_fields_json(docname):
    """
    Build the export payload.

    - Single DocType  → returns one JSON blob directly (existing behaviour).
    - Module set      → returns a ZIP containing one .json file per DocType.

    Return shape (single):
        { status, filename, data, summary, mode: "single" }

    Return shape (zip / module):
        { status, filename, data, summary, mode: "zip" }
        where `data` is a base64-encoded ZIP.
    """
    import base64
    import io
    import zipfile

    doc = _get_validated_doc(docname)
    dt_names = _resolve_doctype_names(doc)
    export_data, exported, failed = _build_export_payload(dt_names)

    if failed:
        frappe.log_error(
            title="[Doctype Export] Partial failure",
            message="\n".join(failed),
        )

    base_name = frappe.scrub(doc.export_name or docname)

    # ── Module export → ZIP of individual files ──────────────────────────
    if doc.module and len(export_data) > 1:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for dt_name, dt_data in export_data.items():
                file_content = frappe.as_json(dt_data, indent=2)
                safe_name = frappe.scrub(dt_name) + ".json"
                zf.writestr(safe_name, file_content)

        zip_bytes = zip_buffer.getvalue()
        encoded = base64.b64encode(zip_bytes).decode("utf-8")

        return {
            "status": "ok",
            "filename": base_name + "_export.zip",
            "data": encoded,
            "mode": "zip",
            "summary": {
                "exported": exported,
                "failed": failed,
            },
        }

    # ── Single DocType or no module → one JSON file ──────────────────────
    # Unwrap the single-item dict so the file is just the DocType object
    single_data = list(export_data.values())[0] if len(export_data) == 1 else export_data

    return {
        "status": "ok",
        "filename": base_name + "_export.json",
        "data": frappe.as_json(single_data, indent=2),
        "mode": "single",
        "summary": {
            "exported": exported,
            "failed": failed,
        },
    }