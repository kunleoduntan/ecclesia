# Copyright (c) 2026, Value Plus and contributors
# For license information, please see license.txt
import frappe


@frappe.whitelist()
def sync_monthly_tax_payable():
	"""
	Pushes monthly_tax_payable from the most recently modified submitted
	Employee Tax Computation record of each employee onto
	Employee.monthly_tax_payable.

	Callable via API (/api/method/ecclesia.api.employee_tax_sync.sync_monthly_tax_payable)
	and via scheduler (see hooks.py, runs every minute under cron).
	"""
	employees = frappe.get_all(
		"Employee",
		pluck="name"
	)

	for emp in employees:
		_sync_single_employee(emp)

	frappe.db.commit()


def sync_on_employee_update(doc, method=None):
	"""
	doc_events hook for Employee on_update. Syncs only the employee being
	saved, not the whole table. Uses frappe.db.set_value internally, which
	does NOT re-trigger on_update, so this is safe from recursion.
	"""
	_sync_single_employee(doc.name)


def _sync_single_employee(employee):
	etc = frappe.get_all(
		"Employee Tax Computation",
		filters={
			"employee": employee,
			"docstatus": 1
		},
		fields=["monthly_tax_payable"],
		order_by="modified desc",
		limit=1
	)

	if etc:
		frappe.db.set_value(
			"Employee",
			employee,
			"monthly_tax_payable",
			etc[0].monthly_tax_payable,
			update_modified=False
		)