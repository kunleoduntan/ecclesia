# ecclesia/setup_posting_policy.py
# Creates the new fields as Custom Fields. Custom Field insert adds the DB
# column immediately, so `bench migrate` is NOT needed.
#
#   bench --site <site> execute ecclesia.setup_posting_policy.run
#
# Safe to re-run: existing fields are skipped.

import frappe

POLICY = {
    "fieldname": "posting_policy",
    "fieldtype": "Select",
    "label": "Posting Policy",
    "options": "Payments & Receipts\nJournal & Payment Entry",
    "default": "Payments & Receipts",
    "reqd": 1,
    "description": "Payments & Receipts = create Payments / Receipts vouchers. "
                   "Journal & Payment Entry = create ERPNext Journal / Payment Entries.",
}

# (parent doctype, field to place it after - skipped if that field is absent)
PARENTS = [
    ("Bank Transaction Processor", "bank_account"),
    ("Batch Bank Transaction", "bank_account"),
    ("Expense Batch", "cost_center"),
]

CHILD_FIELDS = [
    {"fieldname": "entry_type_created", "fieldtype": "Data", "label": "Entry Type",
     "read_only": 1, "no_copy": 1, "print_hide": 1},
    {"fieldname": "entry_reference", "fieldtype": "Data", "label": "Entry Reference",
     "read_only": 1, "no_copy": 1, "in_list_view": 1},
]
CHILDREN = ["Transaction Entry", "Petty Cash Transaction"]


def _add(dt, spec, after=None):
    if frappe.db.exists("Custom Field", {"dt": dt, "fieldname": spec["fieldname"]}) \
            or frappe.get_meta(dt).has_field(spec["fieldname"]):
        print(f"skip   {dt}.{spec['fieldname']} (exists)")
        return
    d = dict(spec, doctype="Custom Field", dt=dt)
    if after and frappe.get_meta(dt).has_field(after):
        d["insert_after"] = after
    frappe.get_doc(d).insert(ignore_permissions=True)
    frappe.clear_cache(doctype=dt)
    print(f"added  {dt}.{spec['fieldname']}")


def run():
    for dt, after in PARENTS:
        _add(dt, POLICY, after)
    for dt in CHILDREN:
        for spec in CHILD_FIELDS:
            _add(dt, spec)
    frappe.db.commit()
    print("done")
