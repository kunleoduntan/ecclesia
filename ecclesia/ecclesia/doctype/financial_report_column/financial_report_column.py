# Copyright (c) 2026, kunle Oduntan and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class FinancialReportColumn(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		calculation_formula: DF.SmallText | None
		column_code: DF.Data
		column_label: DF.Data | None
		column_number: DF.Int
		column_type: DF.Literal["", "Period Actual", "Period Budget", "Period Last Year", "YTD Actual", "YTD Budget", "YTD Last Year", "Calculated", "Static"]
		column_width: DF.Int
		is_hidden: DF.Check
		number_format: DF.Literal["Currency", "Percent", "Integer", "Decimal"]
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
	# end: auto-generated types

	pass