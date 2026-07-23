# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class BiometricSyncLog(Document):
	@classmethod
	def start(cls, device_name, mode="Manual"):
		"""
		Create a new sync log record in 'Running' state and return its name.
		mode should be one of "Scheduled", "Manual", or "Push" (matches the
		sync_mode Select options on this DocType).
		"""
		doc = frappe.get_doc({
			"doctype": "Biometric Sync Log",
			"biometric_device": device_name,
			"sync_start_time": now_datetime(),
			"sync_status": "Running",
			"sync_mode": mode,
		})
		doc.insert(ignore_permissions=True)
		frappe.db.commit()
		return doc.name

	@classmethod
	def finish(cls, log_name, fetched=0, created=0, skipped=0, failed=0, errors=None):
		"""
		Update a running sync log with final results and status.
		Status is derived from the counts: any failures alongside successful
		records is "Partial"; failures with nothing else succeeding is
		"Failed"; otherwise "Completed".
		"""
		if failed and (created or skipped):
			status = "Partial"
		elif failed:
			status = "Failed"
		else:
			status = "Completed"

		frappe.db.set_value("Biometric Sync Log", log_name, {
			"sync_status": status,
			"records_fetched": fetched,
			"attendance_created": created,
			"duplicates_skipped": skipped,
			"failed_records": failed,
			"error_log": errors or "",
		})
		frappe.db.commit()