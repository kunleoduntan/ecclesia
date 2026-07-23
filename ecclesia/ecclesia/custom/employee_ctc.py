# Copyright (c) 2026, Value Plus and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt

# Fallback only — used if CTC Settings has no rows configured yet
# (e.g. right after a fresh install, before anyone has visited the
# settings page). Once CTC Settings has data, that always wins.
FALLBACK_COMPONENT_PERCENTAGES = {
	"Basic Salary": 30,
	"Housing": 30,
	"Transport": 30,
	"Others": 10,
}

PENSIONABLE_COMPONENTS = ("Basic Salary", "Housing", "Transport")
PRECISION = 2


def get_default_component_split():
	"""Read the configured split from CTC Settings; fall back to the
	hardcoded default only if nothing has been configured there."""
	settings = frappe.get_single("CTC Settings")
	if settings.ctc_component_defaults:
		return {row.component: flt(row.percentage) for row in settings.ctc_component_defaults}
	return dict(FALLBACK_COMPONENT_PERCENTAGES)


def get_default_pension_percentages():
	settings = frappe.get_single("CTC Settings")
	return (
		flt(settings.pension_ee_percent) or 8,
		flt(settings.pension_er_percent) or 10,
	)


EMPLOYEE_CTC_CUSTOM_FIELDS = {
	"Employee": [
		{
			"fieldname": "ctc_section_break",
			"fieldtype": "Section Break",
			"label": "CTC Breakdown",
			"insert_after": "grade",
			"collapsible": 1,
		},
		{
			"fieldname": "annual_gross_pay",
			"fieldtype": "Currency",
			"label": "Annual Gross Pay",
			"insert_after": "ctc_section_break",
			"options": "currency",
		},
		{
			"fieldname": "ctc_components",
			"fieldtype": "Table",
			"label": "CTC Components",
			"insert_after": "annual_gross_pay",
			"options": "CTC Component",
		},
		{
			"fieldname": "total_components",
			"fieldtype": "Currency",
			"label": "Total of Components",
			"insert_after": "ctc_components",
			"options": "currency",
			"read_only": 1,
		},
		{
			"fieldname": "column_break_ctc",
			"fieldtype": "Column Break",
			"insert_after": "total_components",
		},
		{
			"fieldname": "pensionable_emoluments",
			"fieldtype": "Currency",
			"label": "Pensionable Emoluments",
			"insert_after": "column_break_ctc",
			"options": "currency",
			"read_only": 1,
		},
		{
			"fieldname": "pension_ee_percent",
			"fieldtype": "Percent",
			"label": "Pension EE %",
			"insert_after": "pensionable_emoluments",
			"default": "8",
		},
		{
			"fieldname": "pension_ee_amount",
			"fieldtype": "Currency",
			"label": "Pension EE",
			"insert_after": "pension_ee_percent",
			"options": "currency",
			"read_only": 1,
		},
		{
			"fieldname": "pension_er_percent",
			"fieldtype": "Percent",
			"label": "Pension ER %",
			"insert_after": "pension_ee_amount",
			"default": "10",
		},
		{
			"fieldname": "pension_er_amount",
			"fieldtype": "Currency",
			"label": "Pension ER",
			"insert_after": "pension_er_percent",
			"options": "currency",
			"read_only": 1,
		},
	]
}


def create_employee_ctc_fields():
	"""One-off setup. Run with:
	bench --site default execute ecclesia.ecclesia.custom.employee_ctc.create_employee_ctc_fields
	"""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields(EMPLOYEE_CTC_CUSTOM_FIELDS, update=True)
	frappe.db.commit()
	print("Employee CTC custom fields created/updated.")


def set_default_components(doc, method=None):
	"""before_insert: seed the CTC Components table (and pension %) from
	CTC Settings so a new Employee doesn't get created empty."""
	if not doc.get("ctc_components"):
		for component, percentage in get_default_component_split().items():
			doc.append(
				"ctc_components",
				{
					"component": component,
					"percentage": percentage,
					"is_pensionable": 1 if component in PENSIONABLE_COMPONENTS else 0,
				},
			)

	if not doc.get("pension_ee_percent") and not doc.get("pension_er_percent"):
		ee_pct, er_pct = get_default_pension_percentages()
		doc.pension_ee_percent = ee_pct
		doc.pension_er_percent = er_pct


def calculate_ctc(doc, method=None):
	"""validate: recompute component amounts, pension, and CTC every time
	Annual Gross Pay, a component row, or a pension % changes."""
	if not doc.get("ctc_components"):
		return

	total = 0.0
	pensionable = 0.0

	for row in doc.ctc_components:
		row.is_pensionable = 1 if row.component in PENSIONABLE_COMPONENTS else 0
		row.amount = flt(flt(doc.annual_gross_pay) * flt(row.percentage) / 100, PRECISION)
		total += row.amount
		if row.is_pensionable:
			pensionable += row.amount

	doc.total_components = flt(total, PRECISION)
	doc.pensionable_emoluments = flt(pensionable, PRECISION)
	doc.pension_ee_amount = flt(
		pensionable * flt(doc.pension_ee_percent or 8) / 100, PRECISION
	)
	doc.pension_er_amount = flt(
		pensionable * flt(doc.pension_er_percent or 10) / 100, PRECISION
	)

	# NOTE: assumes the existing CTC field on Employee is named "ctc".
	# Rename below if yours differs.
	doc.ctc = flt(flt(doc.annual_gross_pay) + doc.pension_er_amount, PRECISION)
