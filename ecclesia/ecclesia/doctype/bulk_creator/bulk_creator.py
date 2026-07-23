# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import json

import frappe
from frappe.model.document import Document


class BulkCreator(Document):
	pass


@frappe.whitelist()
def create_doctypes_from_json(name):
	"""
	Called from the "Create DocTypes" button on the Bulk Creator doctype.

	Reads the pasted JSON from `json_input`, reorders the definitions so
	that any DocType referenced by a Table / Table MultiSelect field
	(i.e. a child table) is created before the parent that uses it, then
	creates each DocType that doesn't already exist.

	Accepts either:
	  - a single DocType JSON object, or
	  - a JSON list of DocType JSON objects (mixed parents + children, any order)
	"""
	frappe.only_for("System Manager")

	doc = frappe.get_doc("Bulk Creator", name)
	raw = (doc.json_input or "").strip()

	if not raw:
		frappe.throw("Paste one or more DocType JSON definitions into the JSON field first.")

	try:
		data = json.loads(raw)
	except ValueError as e:
		frappe.throw(f"Invalid JSON: {e}")

	if isinstance(data, dict):
		definitions = [data]
	elif isinstance(data, list):
		definitions = data
	else:
		frappe.throw("JSON must be a DocType definition object, or a list of them.")

	ordered = _topo_sort(definitions)

	log_lines = []
	created, skipped, failed = [], [], []

	for dt_def in ordered:
		dt_name = dt_def.get("name")
		if not dt_name:
			failed.append(["(unnamed)", "Missing 'name' key"])
			log_lines.append("FAILED   — (unnamed): missing 'name' key")
			continue

		if frappe.db.exists("DocType", dt_name):
			skipped.append(dt_name)
			log_lines.append(f"SKIPPED  — {dt_name} already exists")
			continue

		try:
			_create_single_doctype(dt_def)
			created.append(dt_name)
			log_lines.append(f"CREATED  — {dt_name}")
		except Exception as e:
			frappe.db.rollback()
			failed.append([dt_name, str(e)])
			log_lines.append(f"FAILED   — {dt_name}: {e}")

	frappe.db.commit()

	doc.db_set("log", "\n".join(log_lines), update_modified=False)

	return {
		"created": created,
		"skipped": skipped,
		"failed": failed,
	}


def _create_single_doctype(dt_def):
	"""
	Create one DocType from its exported JSON definition. Frappe's DocType
	doctype accepts the same JSON shape used by `bench export-fixtures` /
	the files under <app>/<app>/doctype/<name>/<name>.json, so it can be
	loaded directly via frappe.get_doc().
	"""
	dt_def = dict(dt_def)  # don't mutate the caller's dict
	dt_def["doctype"] = "DocType"

	# Strip fields that shouldn't be carried over from an exported fixture
	for key in ("modified", "creation", "owner", "idx", "docstatus"):
		dt_def.pop(key, None)

	new_doc = frappe.get_doc(dt_def)
	new_doc.insert(ignore_permissions=True)

	frappe.clear_cache(doctype=dt_def["name"])


def _topo_sort(definitions):
	"""
	Reorder `definitions` so that any DocType referenced by a Table /
	Table MultiSelect field in another definition is created first.

	If a referenced child table isn't part of this batch, it's assumed to
	already exist (or will be created separately) and is simply skipped
	as a dependency.
	"""
	by_name = {d.get("name"): d for d in definitions if d.get("name")}
	names = list(by_name.keys())

	# dt_name -> set of dt_names it depends on (must be created first)
	deps = {name: set() for name in names}
	for name, d in by_name.items():
		for f in d.get("fields", []) or []:
			if f.get("fieldtype") in ("Table", "Table MultiSelect"):
				target = f.get("options")
				if target in by_name and target != name:
					deps[name].add(target)

	ordered = []
	visited = set()
	in_progress = set()

	def visit(n):
		if n in visited:
			return
		if n in in_progress:
			# circular reference between two definitions in this batch —
			# break the cycle rather than recursing forever
			return
		in_progress.add(n)
		for dep in deps.get(n, ()):
			visit(dep)
		in_progress.discard(n)
		visited.add(n)
		ordered.append(by_name[n])

	for n in names:
		visit(n)

	return ordered