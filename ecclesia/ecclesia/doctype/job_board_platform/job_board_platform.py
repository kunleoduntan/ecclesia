# ecclesia/doctype/job_board_platform/job_board_platform.py
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import cint, now_datetime


class JobBoardPlatform(Document):

    def validate(self):
        self._validate_character_limit()
        self._set_defaults_by_platform()

    def _validate_character_limit(self):
        if cint(self.character_limit) < 0:
            frappe.throw(_("Character limit cannot be negative."))

    def _set_defaults_by_platform(self):
        """Auto-fill sensible defaults when platform name is typed."""
        name_lower = (self.platform_name or "").lower()
        defaults = {
            "linkedin":  {"character_limit": 3000, "supports_image": 1,
                          "supports_hashtags": 1, "supports_rich_text": 0,
                          "best_days": "Tuesday, Wednesday, Thursday",
                          "best_time_utc": "08:00",
                          "default_hashtags": "#Hiring #Jobs #Nigeria"},
            "twitter":   {"character_limit": 280, "supports_image": 1,
                          "supports_hashtags": 1, "supports_rich_text": 0,
                          "best_days": "Monday, Tuesday, Wednesday",
                          "best_time_utc": "09:00",
                          "default_hashtags": "#Hiring #NigeriaJobs #Job"},
            "facebook":  {"character_limit": 63206, "supports_image": 1,
                          "supports_hashtags": 1, "supports_rich_text": 0,
                          "best_days": "Wednesday, Thursday, Friday",
                          "best_time_utc": "10:00"},
            "instagram": {"character_limit": 2200, "supports_image": 1,
                          "supports_hashtags": 1, "supports_rich_text": 0,
                          "best_days": "Wednesday, Friday",
                          "best_time_utc": "11:00"},
            "telegram":  {"character_limit": 4096, "supports_image": 1,
                          "supports_hashtags": 1, "supports_rich_text": 1,
                          "best_time_utc": "09:00"},
            "whatsapp":  {"character_limit": 4096, "supports_image": 1,
                          "supports_hashtags": 0, "supports_rich_text": 0,
                          "best_time_utc": "09:00"},
            "indeed":    {"character_limit": 0, "supports_image": 0,
                          "supports_hashtags": 0, "supports_rich_text": 0},
            "glassdoor": {"character_limit": 5000, "supports_image": 0,
                          "supports_hashtags": 0, "supports_rich_text": 0},
            "jobberman": {"character_limit": 5000, "supports_image": 1,
                          "supports_hashtags": 0, "supports_rich_text": 0,
                          "best_time_utc": "09:00"},
        }
        for key, vals in defaults.items():
            if key in name_lower:
                for field, value in vals.items():
                    if not self.get(field):
                        self.set(field, value)
                break

    def after_insert(self):
        frappe.msgprint(
            _(f"Platform '{self.platform_name}' created. "
              f"Add your API credentials and click 'Test Connection' to verify."),
            indicator="blue", alert=True
        )
