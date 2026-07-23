# Copyright (c) 2026, Kunle Oduntan and contributors
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate, add_days

class ComplianceRegister(Document):
    def validate(self):
        self._update_status()

    def _update_status(self):
        if not self.expiry_date:
            return
        today = getdate(nowdate())
        expiry = getdate(self.expiry_date)
        remind = int(self.renewal_reminder_days or 30)
        if expiry < today:
            self.status = "Expired"
        elif expiry <= add_days(today, remind):
            self.status = "Expiring Soon"
        else:
            self.status = "Valid"
