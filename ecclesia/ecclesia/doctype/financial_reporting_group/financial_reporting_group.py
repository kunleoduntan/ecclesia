# Copyright (c) Value Plus
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class FinancialReportingGroup(Document):
	def validate(self):
		if self.is_formula:
			self.validate_formula()
		else:
			self.highlight = None
			self.set("components", [])

	def validate_formula(self):
		if self.is_group:
			frappe.throw(_("A formula row cannot also be a parent group"))
		if self.report_type == "Balance Sheet":
			frappe.throw(_("Formula rows are for the Income Statement, not the Balance Sheet"))
		if not self.components:
			frappe.throw(_("Add at least one component to the formula"))

		seen = set()
		for row in self.components:
			if row.component == self.name or row.component == self.group_name:
				frappe.throw(_("Row {0}: a formula cannot use itself").format(row.idx))
			if row.component in seen:
				frappe.throw(_("Row {0}: {1} is already in the formula").format(row.idx, row.component))
			seen.add(row.component)

		self.validate_no_cycle()

	def validate_no_cycle(self):
		me = self.name or self.group_name
		stack = [row.component for row in self.components]
		visited = set()
		while stack:
			current = stack.pop()
			if current == me:
				frappe.throw(_("Circular formula: {0} depends on itself"). format(me))
			if current in visited:
				continue
			visited.add(current)
			stack.extend(
				frappe.get_all(
					"Financial Reporting Group Component",
					filters={"parent": current, "parenttype": "Financial Reporting Group"},
					pluck="component",
					parent_doctype="Financial Reporting Group",
				)
			)