# ecclesia/doctype/continuous_feedback/continuous_feedback.py
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import nowdate

class ContinuousFeedback(Document):

    def validate(self):
        if self.from_employee == self.to_employee:
            frappe.throw(_("You cannot send feedback to yourself."))
        if not self.feedback:
            frappe.throw(_("Feedback message cannot be empty."))

    def after_insert(self):
        self._notify_recipient()
        self._create_ess_notification()

    def _notify_recipient(self):
        recipient_user = frappe.db.get_value("Employee", self.to_employee, "user_id")
        sender_name = frappe.db.get_value("Employee", self.from_employee, "employee_name")
        if recipient_user:
            if self.visibility == "Public Recognition":
                subject = f"🌟 Recognition from {sender_name}"
            else:
                subject = f"New {self.feedback_type} from {sender_name}"
            frappe.sendmail(
                recipients=[recipient_user],
                subject=subject,
                message=f"<b>{sender_name}</b> has shared feedback with you:<br><br>{self.feedback}"
            )

    def _create_ess_notification(self):
        if not frappe.db.exists("DocType", "ESS Notification Log"):
            return
        frappe.get_doc({
            "doctype": "ESS Notification Log",
            "employee": self.to_employee,
            "notification_type": "Feedback Received",
            "message": f"New {self.feedback_type} from a colleague",
            "reference_doctype": "Continuous Feedback",
            "reference_name": self.name,
            "is_read": 0,
        }).insert(ignore_permissions=True)
