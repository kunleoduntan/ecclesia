# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


# Maps each brand to its protocol and default port
BRAND_CONFIG = {
    "ZKTeco":    {"protocol": "SDK",            "port": 4370},
    "eSSL":      {"protocol": "SDK",            "port": 4370},   # ZKTeco-compatible
    "Hikvision": {"protocol": "ISAPI / REST",   "port": 80},
    "Dahua":     {"protocol": "HTTP API",       "port": 80},
    "Suprema":   {"protocol": "BioStar API",    "port": 443},
    "Anviz":     {"protocol": "CloudClox API",  "port": 5010},
    "Virdi":     {"protocol": "REST API",       "port": 80},
    "Realand":   {"protocol": "SDK",            "port": 4370},
    "Other":     {"protocol": "HTTP API",       "port": 80},
}


class BiometricDevice(Document):

    def validate(self):
        self._auto_set_protocol_and_port()

    def _auto_set_protocol_and_port(self):
        """Auto-fill protocol and default port when brand is selected."""
        cfg = BRAND_CONFIG.get(self.device_brand or "", {})
        if cfg.get("protocol"):
            self.protocol = cfg["protocol"]
        if not self.port and cfg.get("port"):
            self.port = cfg["port"]

    def ping(self):
        """Test connectivity to device. Returns True/False."""
        try:
            connector = self._get_connector()
            result = connector.ping()
            self.db_set("device_status", "Online" if result else "Offline")
            return result
        except Exception as e:
            self.db_set("device_status", "Offline")
            frappe.log_error(str(e), f"Biometric Device Ping Failed: {self.name}")
            return False

    def pull_logs(self, from_date=None):
        """Pull attendance logs from device and save to Biometric Attendance Log."""
        from ecclesia.biometric_attendance.sync import pull_device_logs
        return pull_device_logs(self, from_date)

    def get_users(self):
        """Fetch enrolled users from device for mapping to employees."""
        return self._get_connector().get_users()

    def _get_connector(self):
        from ecclesia.utils.device_connector import get_connector
        return get_connector(self)