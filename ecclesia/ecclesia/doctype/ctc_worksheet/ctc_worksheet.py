# Copyright (c) 2026, Value Plus and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

PENSIONABLE_COMPONENTS = ("Basic Salary", "Housing", "Transport")
PRECISION = 2


class CTCWorksheet(Document):
	def validate(self):
		self.validate_percentages()
		self.calculate_components()
		self.calculate_pension()
		self.calculate_ctc()

	def validate_percentages(self):
		total_pct = sum(flt(row.percentage) for row in self.components)
		if abs(total_pct - 100) > 0.01:
			frappe.throw(
				_("Component percentages must total 100%. Currently {0}%").format(total_pct)
			)

	def calculate_components(self):
		total = 0.0
		pensionable = 0.0

		for row in self.components:
			row.is_pensionable = 1 if row.component in PENSIONABLE_COMPONENTS else 0
			row.amount = flt(
				flt(self.annual_gross_pay) * flt(row.percentage) / 100, PRECISION
			)
			total += row.amount
			if row.is_pensionable:
				pensionable += row.amount

		self.total_components = flt(total, PRECISION)
		self.pensionable_emoluments = flt(pensionable, PRECISION)

	def calculate_pension(self):
		self.pension_ee_amount = flt(
			flt(self.pensionable_emoluments) * flt(self.pension_ee_percent) / 100, PRECISION
		)
		self.pension_er_amount = flt(
			flt(self.pensionable_emoluments) * flt(self.pension_er_percent) / 100, PRECISION
		)

		expected_ee = flt(
			flt(self.pensionable_emoluments) * flt(self.pension_ee_percent) / 100, PRECISION
		)
		self.pension_ee_check = 1 if abs(self.pension_ee_amount - expected_ee) < 0.01 else 0

	def calculate_ctc(self):
		self.ctc = flt(flt(self.annual_gross_pay) + flt(self.pension_er_amount), PRECISION)
