# Copyright (c) 2026, Value Impacts Consulting
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today


class ExecutiveTask(Document):
	def validate(self):
		self.sync_completion_date()
		self.sync_escalation_date()

	def sync_completion_date(self):
		if self.status == "Completed" and not self.completion_date:
			self.completion_date = today()
		if self.status != "Completed":
			self.completion_date = None

	def sync_escalation_date(self):
		if self.escalated and not self.escalated_date:
			self.escalated_date = today()
		if self.escalated and not self.escalated_to:
			frappe.msgprint(
				_("Task is marked Escalated but no Escalated To has been set."),
				alert=True,
			)
