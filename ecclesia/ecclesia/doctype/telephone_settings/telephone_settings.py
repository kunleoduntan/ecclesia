# Copyright (c) 2026, kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TelephoneSettings(Document):

    def validate(self):
        self._auto_fill_webhook_urls()
        self._validate_ringtone_volume()
        self._validate_provider_credentials()

    # ─── Webhook URL Auto-fill ────────────────────────────────────────────────

    def _auto_fill_webhook_urls(self):
        base = frappe.utils.get_url()

        if self.active_provider == "Twilio" or self.fallback_provider == "Twilio":
            self.twilio_webhook_url = f"{base}/api/method/ecclesia.api.twilio_webhook"

        if self.active_provider == "Vonage" or self.fallback_provider == "Vonage":
            self.vonage_webhook_url = f"{base}/api/method/ecclesia.api.vonage_webhook"

        if self.active_provider == "Plivo" or self.fallback_provider == "Plivo":
            self.plivo_webhook_url  = f"{base}/api/method/ecclesia.api.plivo_webhook"

    # ─── Validation ───────────────────────────────────────────────────────────

    def _validate_ringtone_volume(self):
        if not (0 <= int(self.ringtone_volume or 80) <= 100):
            frappe.throw("Ringtone Volume must be between 0 and 100.")

    def _validate_provider_credentials(self):
        provider = self.active_provider
        missing = []

        if provider == "Twilio":
            if not self.twilio_account_sid:
                missing.append("Twilio Account SID")
            if not self.twilio_auth_token:
                missing.append("Twilio Auth Token")
            if not self.twilio_phone_number:
                missing.append("Twilio Phone Number")

        elif provider == "Vonage":
            if not self.vonage_api_key:
                missing.append("Vonage API Key")
            if not self.vonage_api_secret:
                missing.append("Vonage API Secret")
            if not self.vonage_app_id:
                missing.append("Vonage Application ID")

        elif provider == "Plivo":
            if not self.plivo_auth_id:
                missing.append("Plivo Auth ID")
            if not self.plivo_auth_token:
                missing.append("Plivo Auth Token")
            if not self.plivo_phone_number:
                missing.append("Plivo Phone Number")

        elif provider == "Asterisk":
            if not self.asterisk_ami_host:
                missing.append("Asterisk AMI Host")
            if not self.asterisk_ami_username:
                missing.append("Asterisk AMI Username")
            if not self.asterisk_ami_password:
                missing.append("Asterisk AMI Password")

        if missing:
            frappe.msgprint(
                f"Warning: Active provider <b>{provider}</b> is missing: {', '.join(missing)}. "
                "External calls will not work until these are filled.",
                indicator="orange",
                title="Incomplete Provider Config"
            )

    # ─── Helper ───────────────────────────────────────────────────────────────

    @staticmethod
    def get_settings():
        return frappe.get_single("Telephone Settings")
