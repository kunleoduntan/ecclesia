# Copyright (c) 2026, Value Impacts Consulting
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today, date_diff, cint


class Meeting(Document):
	def validate(self):
		self.validate_meeting_date()
		self.calculate_notice_compliance()
		self.calculate_attendance()
		self.calculate_resolution_stats()
		self.calculate_analytics()

	def validate_meeting_date(self):
		if self.is_new() and self.meeting_date:
			if getdate(self.meeting_date) < getdate(today()) and self.status == "Draft":
				frappe.msgprint(
					_("Meeting Date is in the past. Please confirm this is a record of a past meeting."),
					alert=True,
				)

	def calculate_notice_compliance(self):
		"""Notice days = gap between notice_date and meeting_date. Compliance is
		measured against the linked Meeting Type's default_notice_days, if set."""
		if self.notice_date and self.meeting_date:
			self.notice_days = date_diff(getdate(self.meeting_date), getdate(self.notice_date))
		required_days = 0
		if self.meeting_type:
			required_days = cint(
				frappe.db.get_value("Meeting Type", self.meeting_type, "default_notice_days")
			)
		self.notice_compliant = 1 if (self.notice_days or 0) >= required_days else 0

	def calculate_attendance(self):
		present = [a for a in (self.attendees or []) if a.attendance_status == "Present"]
		self.total_attendees = len(present)
		if self.quorum_required:
			self.quorum_met = 1 if len(present) >= cint(self.quorum_required) else 0

	def calculate_resolution_stats(self):
		self.resolutions_passed = len([r for r in (self.resolutions or []) if r.result == "Passed"])
		self.resolutions_failed = len([r for r in (self.resolutions or []) if r.result == "Defeated"])

	def calculate_analytics(self):
		today_date = getdate(today())
		if self.meeting_date:
			self.days_to_meeting = date_diff(getdate(self.meeting_date), today_date)
		self.days_notice_given = self.notice_days or 0
		self.open_action_items = len(
			[a for a in (self.action_items or []) if a.status in ("Open", "In Progress")]
		)

	def on_submit(self):
		frappe.msgprint(_("Meeting {0} submitted successfully").format(self.name))

	def on_update_after_submit(self):
		# Recalculate rollups if attendance/resolutions are edited after submission
		self.calculate_attendance()
		self.calculate_resolution_stats()
		self.calculate_analytics()
