# Copyright (c) 2026, Value Impacts Consulting
import frappe
from frappe.model.document import Document


class AIInteractionLog(Document):
	def before_insert(self):
		if not self.requested_by:
			self.requested_by = frappe.session.user
