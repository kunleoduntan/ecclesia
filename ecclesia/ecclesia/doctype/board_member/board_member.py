# Copyright (c) 2026, Value Impacts Consulting
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class BoardMember(Document):
	def validate(self):
		if self.appointment_date and self.term_end_date:
			if getdate(self.term_end_date) < getdate(self.appointment_date):
				frappe.throw(_("Term End Date cannot be before Appointment Date."))
