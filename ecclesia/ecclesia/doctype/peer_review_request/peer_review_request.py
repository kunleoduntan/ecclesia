# ecclesia/doctype/peer_review_request/peer_review_request.py
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import nowdate, getdate, date_diff

class PeerReviewRequest(Document):

    def validate(self):
        self._validate_peers()
        self._check_no_self_review()
        self._validate_deadline()

    def on_submit(self):
        self._send_invitations()
        self.status = "Open"

    def on_cancel(self):
        self.status = "Expired"

    def _validate_peers(self):
        if not self.peers:
            frappe.throw(_("Please add at least one peer reviewer."))
        # Check for duplicates
        peer_names = [r.peer for r in self.peers]
        if len(peer_names) != len(set(peer_names)):
            frappe.throw(_("Duplicate peers found. Each peer can only be added once."))

    def _check_no_self_review(self):
        for row in self.peers:
            if row.peer == self.reviewee:
                frappe.throw(_("An employee cannot review themselves. Remove {0} from the peer list.").format(
                    row.peer_name or row.peer))

    def _validate_deadline(self):
        if self.deadline and getdate(self.deadline) < getdate(nowdate()):
            frappe.throw(_("Review deadline cannot be in the past."))

    def _send_invitations(self):
        reviewee_name = frappe.db.get_value("Employee", self.reviewee, "employee_name")
        for row in self.peers:
            peer_user = frappe.db.get_value("Employee", row.peer, "user_id")
            if peer_user:
                frappe.sendmail(
                    recipients=[peer_user],
                    subject=f"Peer Review Request: {reviewee_name}",
                    message=(
                        f"You have been requested to complete a peer review for "
                        f"<b>{reviewee_name}</b> as part of the {self.performance_cycle} cycle.<br><br>"
                        f"<b>Deadline:</b> {self.deadline}<br>"
                        f"{'<b>This review is anonymous.</b><br>' if self.is_anonymous else ''}<br>"
                        f"Please log in to the ESS Performance Portal to complete your review.<br><br>"
                        f"{self.instructions or ''}"
                    )
                )
