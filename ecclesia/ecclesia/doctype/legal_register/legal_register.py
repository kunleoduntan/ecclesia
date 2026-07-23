# Copyright (c) 2026, Value Impacts Consulting
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today, date_diff, cint, nowdate, add_days


class LegalRegister(Document):
	def validate(self):
		self.calculate_analytics()
		self.auto_transition_status()

	def calculate_analytics(self):
		today_date = getdate(today())
		if self.expiry_date:
			self.days_to_expiry = date_diff(getdate(self.expiry_date), today_date)
			reminder = cint(self.renewal_reminder_days) or 30
			self.is_expiring_soon = 1 if 0 <= self.days_to_expiry <= reminder else 0
			self.is_expired = 1 if self.days_to_expiry < 0 else 0
		else:
			self.days_to_expiry = 0
			self.is_expiring_soon = 0
			self.is_expired = 0

	def auto_transition_status(self):
		if self.status in ("Renewed", "Lapsed"):
			return  # manual terminal states, don't override
		if self.is_expired:
			self.status = "Expired"
			self.compliance_status = "Non-Compliant"
		elif self.is_expiring_soon:
			self.status = "Pending Renewal"
		elif self.status == "Pending Renewal" and not self.is_expiring_soon:
			self.status = "Active"

	def on_update(self):
		# Fires on every save (not just submit) since expiry tracking needs to
		# stay live even while the record is still a draft-status working copy.
		if self.is_expiring_soon or self.is_expired:
			self._try_create_compliance_task()

	def add_renewal(self, renewal_date, new_expiry_date, renewed_by=None, cost=None):
		"""Called from the API when a renewal is recorded — appends history,
		resets status, and clears the expired/expiring flags."""
		self.append("renewal_history", {
			"renewal_date": renewal_date,
			"previous_expiry_date": self.expiry_date,
			"new_expiry_date": new_expiry_date,
			"renewed_by": renewed_by,
			"cost": cost,
		})
		self.expiry_date = new_expiry_date
		self.status = "Renewed"
		self.compliance_status = "Compliant"
		self.save(ignore_permissions=True)

	def _try_create_compliance_task(self):
		"""
		Best-effort integration with the existing Compliance Task doctype
		(the one used by Board Resolution's CAC filing reminders). We don't
		have that doctype's full schema — in particular we don't know the
		valid options for its `task_type` / `obligation_type` Select fields
		outside the "Filing" / "CAC Annual Return" values already proven to
		work for Board Resolution. Rather than guess and risk a validation
		error blocking the save of this Legal Register entry, this wraps
		the attempt in try/except and degrades to an on-screen reminder.

		TODO: once the Compliance Task DocType JSON is available, replace
		the try/except fallback with explicit field values (task_type,
		obligation_type) the way Board Resolution does.
		"""
		if not frappe.db.exists("DocType", "Compliance Task"):
			return
		if frappe.db.exists("Compliance Task", {
			"related_doctype": "Legal Register",
			"related_document": self.name,
			"target_completion": [">=", nowdate()],
		}):
			return

		try:
			task = frappe.new_doc("Compliance Task")
			task.task_title = f"Renew: {self.instrument_title}"
			task.company = self.company
			task.priority = "High" if self.is_expired else "Medium"
			task.description = (
				f"Legal instrument '{self.instrument_title}' "
				f"({self.instrument_type or 'Legal Register'}) "
				f"{'has expired' if self.is_expired else 'is expiring'} on {self.expiry_date}. "
				f"Issuing authority: {self.issuing_authority or '—'}."
			)
			task.start_date = nowdate()
			task.target_completion = self.expiry_date
			task.related_doctype = "Legal Register"
			task.related_document = self.name
			if self.responsible_officer:
				task.assigned_owner = self.responsible_officer
			task.insert(ignore_permissions=True)
			self.db_set("compliance_task_ref", task.name)
			frappe.msgprint(
				_("Compliance Task created for renewal: {0}").format(task.name),
				indicator="green", alert=True,
			)
		except Exception:
			frappe.log_error(
				title="Legal Register: Compliance Task auto-creation failed",
				message=frappe.get_traceback(),
			)
			frappe.msgprint(
				_("Could not auto-create a Compliance Task (unknown field constraints on that "
				  "doctype). Please log the renewal task manually for now."),
				indicator="orange", alert=True,
			)
