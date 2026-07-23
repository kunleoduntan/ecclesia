# Copyright (c) 2026, Kunle Oduntan and contributors
import frappe
from frappe import _
from frappe.model.document import Document

class MeetingRoomBooking(Document):
    def validate(self):
        if self.start_time and self.end_time:
            if str(self.end_time) >= str(self.end_time) and str(self.end_time) <= str(self.start_time):
                frappe.throw(_("End Time must be after Start Time."))
        self._check_conflicts()

    def on_submit(self):
        self.db_set("status", "Confirmed")

    def on_cancel(self):
        self.db_set("status", "Cancelled")

    def _check_conflicts(self):
        if not (self.facility and self.booking_date and self.start_time and self.end_time):
            return
        conflict = frappe.db.sql("""
            SELECT name FROM `tabMeeting Room Booking`
            WHERE facility = %s AND booking_date = %s AND name != %s
              AND docstatus = 1 AND status != 'Cancelled'
              AND ((start_time < %s AND end_time > %s) OR (start_time >= %s AND start_time < %s))
        """, (self.facility, self.booking_date, self.name or "",
              self.end_time, self.start_time, self.start_time, self.end_time))
        if conflict:
            frappe.throw(_("Room already booked during this slot: {0}").format(conflict[0][0]))
