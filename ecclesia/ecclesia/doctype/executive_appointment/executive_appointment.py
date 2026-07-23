# Copyright (c) 2026, Value Impacts Consulting
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, add_to_date


class ExecutiveAppointment(Document):
	def validate(self):
		self.validate_times()

	def validate_times(self):
		if self.start_time and self.end_time and self.end_time <= self.start_time:
			frappe.throw(_("End Time must be after Start Time."))

	def on_update(self):
		self._sync_calendar_event()

	def on_trash(self):
		if self.calendar_event_ref and frappe.db.exists("Event", self.calendar_event_ref):
			try:
				frappe.delete_doc("Event", self.calendar_event_ref, ignore_permissions=True)
			except Exception:
				pass

	def _sync_calendar_event(self):
		"""
		Mirror this appointment into Frappe's core "Event" doctype (the one
		that actually backs the standard Calendar view — confirmed against
		frappe/desk/doctype/event/event.py; there is no "Calendar Event"
		doctype in core Frappe/ERPNext, that was my error in an earlier
		version of this file) so it shows up in the executive's Calendar
		alongside everything else.

		Event does NOT have a generic ref_type/ref_name field for "what
		created this event" — the only source-document linking mechanism on
		Event is the `event_participants` child table's `reference_doctype`/
		`reference_docname`, which is meant for participants (e.g. a Contact
		or Employee), not a back-reference to the record that spawned the
		event. Rather than guess at how to (mis)use that child table for a
		purpose it isn't meant for, this sync intentionally does NOT attempt
		any reverse-reference on the Event side — the relationship lives on
		this side only, via `calendar_event_ref`. Wrapped defensively:
		Event's exact field set can still vary slightly across versions, and
		a sync failure here should never block saving the appointment itself.
		"""
		if not (self.appointment_date and self.start_time):
			return
		if self.status == "Cancelled":
			self._remove_calendar_event()
			return

		try:
			starts_on = get_datetime(f"{self.appointment_date} {self.start_time}")
			ends_on = (
				get_datetime(f"{self.appointment_date} {self.end_time}")
				if self.end_time else add_to_date(starts_on, hours=1)
			)

			if self.calendar_event_ref and frappe.db.exists("Event", self.calendar_event_ref):
				event = frappe.get_doc("Event", self.calendar_event_ref)
			else:
				event = frappe.new_doc("Event")
				event.event_type = "Private"

			event.subject = self.appointment_title
			event.starts_on = starts_on
			event.ends_on = ends_on
			event.description = self.purpose or ""

			event.save(ignore_permissions=True)

			if not self.calendar_event_ref:
				self.db_set("calendar_event_ref", event.name, update_modified=False)

		except Exception:
			frappe.log_error(
				title="Executive Appointment: Event sync failed",
				message=frappe.get_traceback(),
			)

	def _remove_calendar_event(self):
		if self.calendar_event_ref and frappe.db.exists("Event", self.calendar_event_ref):
			try:
				frappe.delete_doc("Event", self.calendar_event_ref, ignore_permissions=True)
				self.db_set("calendar_event_ref", None, update_modified=False)
			except Exception:
				pass
