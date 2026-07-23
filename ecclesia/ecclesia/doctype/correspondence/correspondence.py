# Copyright (c) 2026, Value Impacts Consulting
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today, date_diff, cint


class Correspondence(Document):
	def validate(self):
		self.set_defaults_by_type()
		self.calculate_response_status()
		self.calculate_analytics()
		self.guard_confidential_access()

	def set_defaults_by_type(self):
		"""Pull default priority / acknowledgement flag from the Correspondence Type master."""
		if self.correspondence_category and not self.get("_priority_manually_set"):
			cat = frappe.db.get_value(
				"Correspondence Type", self.correspondence_category,
				["default_priority", "requires_acknowledgement"], as_dict=True,
			)
			if cat:
				if not self.priority:
					self.priority = cat.default_priority
				if cat.requires_acknowledgement and not self.acknowledgement_required:
					self.acknowledgement_required = 1

	def calculate_response_status(self):
		if not self.response_required:
			self.response_status = "Not Required"
			return
		if self.response_date or self.responded_by:
			self.response_status = "Responded"
			if self.status == "Pending Response":
				self.status = "Responded"
			return
		if self.response_due_date and getdate(self.response_due_date) < getdate(today()):
			self.response_status = "Overdue"
		else:
			self.response_status = "Pending"

	def calculate_analytics(self):
		today_date = getdate(today())
		if self.date_received:
			self.days_since_received = date_diff(today_date, getdate(self.date_received))
		if self.due_date:
			self.days_to_due = date_diff(getdate(self.due_date), today_date)
			self.is_overdue = 1 if self.days_to_due < 0 and self.status not in ("Closed", "Responded", "Dispatched") else 0
		else:
			self.is_overdue = 0

	def guard_confidential_access(self):
		"""Confidential correspondence is visible only to System Manager / Accounts Manager
		and the assigned owner. Enforced here in addition to any role-level permissions."""
		if not self.confidential or self.is_new():
			return
		user = frappe.session.user
		if user == "Administrator":
			return
		allowed_roles = {"System Manager", "Accounts Manager"}
		user_roles = set(frappe.get_roles(user))
		is_owner = self.assigned_to and frappe.db.get_value("Employee", self.assigned_to, "user_id") == user
		if not (allowed_roles & user_roles) and not is_owner and user != self.owner:
			frappe.throw(_("This correspondence is marked Confidential. You do not have access."), frappe.PermissionError)

	def on_submit(self):
		frappe.msgprint(_("Correspondence {0} submitted successfully").format(self.name))
