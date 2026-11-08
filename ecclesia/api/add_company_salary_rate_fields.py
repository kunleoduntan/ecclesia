"""
Place this file inside your Ecclesia app, e.g.:
    apps/ecclesia/ecclesia/api/add_company_salary_rate_fields.py

Then run on your CloudClusters instance:
    bench --site <your-site-name> execute ecclesia.api.add_company_salary_rate_fields.execute

This creates a Section Break ("Salary Rate Settings") after
default_employee_advance_account on Company, followed by:
    custom_basic_salary_rate        (Percent, default 30)
    custom_transport_allowance_rate (Percent, default 30)
    col_break_salary_rate           (Column Break)
    custom_housing_allowance_rate   (Percent, default 30)
    custom_employer_pension_rate    (Percent, default 10)

Safe to re-run: create_custom_fields skips fields that already exist
unless update=True is passed.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	custom_fields = {
		"Company": [
			{
				"fieldname": "sb_salary_rate_settings",
				"label": "Salary Rate Settings",
				"fieldtype": "Section Break",
				"insert_after": "default_employee_advance_account",
				"collapsible": 1,
				"module": "Ecclesia",
				"description": (
					"Default rates used to break annual_gross_salary into "
					"monthly_gross_pay and ctc on Employee."
				),
			},
			{
				"fieldname": "custom_basic_salary_rate",
				"label": "Basic Salary Rate (%)",
				"fieldtype": "Percent",
				"default": "30",
				"insert_after": "sb_salary_rate_settings",
				"module": "Ecclesia",
				"description": "Basic Salary as a % of Annual Gross Salary.",
			},
			{
				"fieldname": "custom_transport_allowance_rate",
				"label": "Transport Allowance Rate (%)",
				"fieldtype": "Percent",
				"default": "30",
				"insert_after": "custom_basic_salary_rate",
				"module": "Ecclesia",
				"description": "Transport Allowance as a % of Annual Gross Salary.",
			},
			{
				"fieldname": "col_break_salary_rate",
				"fieldtype": "Column Break",
				"insert_after": "custom_transport_allowance_rate",
				"module": "Ecclesia",
			},
			{
				"fieldname": "custom_housing_allowance_rate",
				"label": "Housing Allowance Rate (%)",
				"fieldtype": "Percent",
				"default": "30",
				"insert_after": "col_break_salary_rate",
				"module": "Ecclesia",
				"description": "Housing Allowance as a % of Annual Gross Salary.",
			},
			{
				"fieldname": "custom_employer_pension_rate",
				"label": "Employer Pension Rate (%)",
				"fieldtype": "Percent",
				"default": "10",
				"insert_after": "custom_housing_allowance_rate",
				"module": "Ecclesia",
				"description": (
					"Employer PenCom contribution rate, added to Annual Gross "
					"Salary to derive CTC."
				),
			},
		]
	}

	create_custom_fields(custom_fields, update=True)
	frappe.db.commit()
	print("✔ Company salary rate fields created/updated.")