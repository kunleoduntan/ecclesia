# Copyright (c) 2026, Value Impacts Consulting
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class ExecutiveCommunication(Document):
	def validate(self):
		self.calculate_stats()

	def calculate_stats(self):
		recipients = self.recipients or []
		self.total_recipients = len(recipients)
		self.total_read = len([r for r in recipients if r.read_date])
		self.total_acknowledged = len([r for r in recipients if r.acknowledged])
		self.read_rate = (
			flt(self.total_read) / flt(self.total_recipients) * 100 if self.total_recipients else 0
		)
		self.acknowledgement_rate = (
			flt(self.total_acknowledged) / flt(self.total_recipients) * 100 if self.total_recipients else 0
		)

	def on_submit(self):
		if not self.recipients:
			frappe.throw(
				_("No recipients on this communication. Use 'Load Recipients' before submitting.")
			)
		if self.status == "Draft":
			self.status = "Sent"
			self.db_set("status", "Sent")
		frappe.msgprint(_("Executive Communication {0} submitted. Use 'Dispatch' to send it.").format(self.name))
