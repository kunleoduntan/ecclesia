# Copyright (c) 2026, Value Impacts Consulting
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today, date_diff, cint


class CorporateDocument(Document):
	def validate(self):
		self.set_defaults_from_category()
		self.calculate_analytics()

	def set_defaults_from_category(self):
		if self.document_category and not self.get("_approval_manually_set"):
			requires = frappe.db.get_value("Document Category", self.document_category, "requires_approval")
			if requires is not None:
				self.requires_approval = cint(requires)

	def calculate_analytics(self):
		today_date = getdate(today())
		if self.expiry_date:
			self.days_to_expiry = date_diff(getdate(self.expiry_date), today_date)
			reminder = cint(self.renewal_reminder_days) or 30
			self.is_expiring_soon = 1 if 0 <= self.days_to_expiry <= reminder else 0
			if self.days_to_expiry < 0 and self.status not in ("Superseded", "Archived"):
				self.status = "Expired"
		else:
			self.days_to_expiry = 0
			self.is_expiring_soon = 0

	def on_submit(self):
		if self.requires_approval and not self.approved_by:
			frappe.throw(_("This document requires approval. Please set Approved By before submitting."))
		if self.status == "Draft":
			self.status = "Approved"
			self.db_set("status", "Approved")
		frappe.msgprint(_("Corporate Document {0} submitted.").format(self.name))
