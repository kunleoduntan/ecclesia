# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

"""
ecclesia/doctype/wa_quick_reply/wa_quick_reply.py
WA Quick Reply DocType controller.
Canned responses triggered by /shortcut in the chat widget.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class WAQuickReply(Document):

    def validate(self):
        # Ensure shortcut starts with /
        if self.shortcut and not self.shortcut.startswith("/"):
            self.shortcut = "/" + self.shortcut

        # Enforce body length limit (WhatsApp max is 1024 chars)
        body_plain = frappe.utils.strip_html(self.body or "")
        if len(body_plain) > 1024:
            frappe.throw(
                _("Quick Reply body cannot exceed 1024 characters. Current length: {0}").format(len(body_plain))
            )

        # Prevent duplicate shortcuts
        if self.shortcut:
            existing = frappe.db.get_value(
                "WA Quick Reply",
                {"shortcut": self.shortcut, "name": ("!=", self.name or "")},
                "name"
            )
            if existing:
                frappe.throw(
                    _("Shortcut <b>{0}</b> is already used by {1}.").format(self.shortcut, existing)
                )

    def before_save(self):
        # Normalise shortcut to lowercase
        if self.shortcut:
            self.shortcut = self.shortcut.lower().strip()


# ─────────────────────────────────────────────────────────────────────────────
# WHITELISTED HELPERS — called by internal_chat.js
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def search_quick_replies(query: str = "") -> list:
    """
    Returns quick replies matching a /shortcut prefix.
    Called by the chat widget when user types / in the message input.
    """
    filters = {"is_active": 1}
    if query:
        # Strip leading slash if present
        q = query.lstrip("/").lower()
        filters["shortcut"] = ("like", f"/{q}%")

    replies = frappe.get_all(
        "WA Quick Reply",
        filters=filters,
        fields=["name", "shortcut", "title", "body", "category"],
        order_by="shortcut asc",
        limit=10
    )
    return replies


@frappe.whitelist()
def get_quick_reply_body(shortcut: str) -> str:
    """
    Return the body text for a given shortcut string.
    Called when user selects a quick reply from the picker.
    """
    shortcut = shortcut.lower().strip()
    if not shortcut.startswith("/"):
        shortcut = "/" + shortcut

    body = frappe.db.get_value(
        "WA Quick Reply",
        {"shortcut": shortcut, "is_active": 1},
        "body"
    )
    if not body:
        frappe.throw(_("Quick reply not found for shortcut: {0}").format(shortcut))

    return body
