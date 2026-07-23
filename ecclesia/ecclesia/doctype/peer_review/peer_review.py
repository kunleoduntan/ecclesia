# ecclesia/doctype/peer_review/peer_review.py
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import nowdate, flt

class PeerReview(Document):

    def validate(self):
        self._validate_rating()
        self._not_self_review()

    def on_submit(self):
        self.submission_date = nowdate()
        self.status = "Submitted"
        self._mark_request_row_complete()
        self._recalculate_peer_average()
        self._notify_reviewee()

    def _validate_rating(self):
        rating = flt(self.overall_peer_rating)
        if rating and not (1 <= rating <= 5):
            frappe.throw(_("Overall rating must be between 1 and 5."))
        for row in (self.competency_ratings or []):
            if flt(row.rating) and not (1 <= flt(row.rating) <= 5):
                frappe.throw(_("Competency rating for {0} must be between 1 and 5.").format(row.competency))

    def _not_self_review(self):
        if self.reviewer == self.reviewee:
            frappe.throw(_("An employee cannot review themselves."))

    def _mark_request_row_complete(self):
        if not self.peer_review_request:
            return
        req = frappe.get_doc("Peer Review Request", self.peer_review_request)
        for row in req.peers:
            if row.peer == self.reviewer:
                row.status = "Completed"
                row.review_name = self.name
                break
        # Check if all complete
        all_done = all(r.status == "Completed" for r in req.peers)
        if all_done:
            req.status = "Completed"
        req.save(ignore_permissions=True)

    def _recalculate_peer_average(self):
        reviews = frappe.get_all("Peer Review",
            filters={"reviewee": self.reviewee,
                     "performance_cycle": self.performance_cycle,
                     "docstatus": 1},
            fields=["overall_peer_rating"])
        if reviews:
            avg = sum(flt(r.overall_peer_rating) for r in reviews) / len(reviews)
            from ecclesia.api.performance_portal import _update_perf_record
            _update_perf_record(self.reviewee, self.performance_cycle,
                {"peer_score": round(avg, 2)})

    def _notify_reviewee(self):
        if self.is_anonymous:
            return  # never reveal anonymous reviewer
        reviewee_user = frappe.db.get_value("Employee", self.reviewee, "user_id")
        reviewer_name = frappe.db.get_value("Employee", self.reviewer, "employee_name")
        if reviewee_user:
            frappe.sendmail(
                recipients=[reviewee_user],
                subject="You received a peer review",
                message=f"{reviewer_name} has submitted a peer review for you. "
                        f"Log in to view your feedback in the ESS portal."
            )
