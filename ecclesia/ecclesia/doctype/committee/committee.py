# Copyright (c) 2026, Value Impacts Consulting
import frappe
from frappe import _
from frappe.model.document import Document


class Committee(Document):
	def validate(self):
		self.validate_single_chairperson()

	def validate_single_chairperson(self):
		chair_rows = [m for m in (self.members or []) if m.role == "Chairperson" and m.is_active]
		if len(chair_rows) > 1:
			frappe.throw(_("Only one active member can be marked as Chairperson."))
