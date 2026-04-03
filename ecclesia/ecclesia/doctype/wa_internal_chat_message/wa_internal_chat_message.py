# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

"""
ecclesia/doctype/wa_internal_chat_message/wa_internal_chat_message.py
"""

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class WAInternalChatMessage(Document):

    def before_insert(self):
        if not self.timestamp:
            self.timestamp = now_datetime()

    def after_insert(self):
        # Thread reply count
        if self.reply_to:
            frappe.db.sql("""
                UPDATE `tabWA Internal Chat Message`
                SET reply_count = COALESCE(reply_count, 0) + 1
                WHERE name = %s
            """, self.reply_to)
            frappe.db.commit()
