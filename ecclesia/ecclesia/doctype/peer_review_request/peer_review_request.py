# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
from ecclesia.utils.score_engine import compute_composite_score


class PeerReviewRequest(Document):

    def validate(self):
        self._prevent_self_review()
        self._prevent_duplicate()

    def on_update(self):
        if self.status == "Completed":
            self._recompute_reviewee_score()
            self._update_epr_peer_count()

    # ── Validation ───────────────────────────────────────────────────

    def _prevent_self_review(self):
        if self.reviewee == self.reviewer:
            frappe.throw("An employee cannot review themselves.", title="Invalid Reviewer")

    def _prevent_duplicate(self):
        existing = frappe.db.get_value(
            "Peer Review Request",
            {
                "cycle":    self.cycle,
                "reviewee": self.reviewee,
                "reviewer": self.reviewer,
                "name":     ["!=", self.name or ""],
            },
            "name"
        )
        if existing:
            frappe.throw(
                f"A peer review request already exists for this reviewer–reviewee pair "
                f"in this cycle ({existing}).",
                title="Duplicate Request"
            )

    # ── Post-completion actions ───────────────────────────────────────

    def _recompute_reviewee_score(self):
        epr = frappe.db.get_value(
            "Employee Performance Record",
            {"cycle": self.cycle, "employee": self.reviewee},
            "name"
        )
        if epr:
            compute_composite_score(epr)

    def _update_epr_peer_count(self):
        epr = frappe.db.get_value(
            "Employee Performance Record",
            {"cycle": self.cycle, "employee": self.reviewee},
            "name"
        )
        if not epr:
            return
        count = frappe.db.count(
            "Peer Review Request",
            {"cycle": self.cycle, "reviewee": self.reviewee, "status": "Completed"}
        )
        frappe.db.set_value("Employee Performance Record", epr, "peer_review_count", count)
        frappe.db.commit()


# ── Whitelisted methods ───────────────────────────────────────────────

@frappe.whitelist()
def get_my_pending_reviews(cycle: str = None):
    """
    Return all Peer Review Requests assigned to the current user's employee record.
    Used by the employee portal / dashboard page.
    """
    employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
    if not employee:
        return []

    filters = {"reviewer": employee, "status": ["in", ("Pending", "In Progress")]}
    if cycle:
        filters["cycle"] = cycle

    return frappe.get_all(
        "Peer Review Request",
        filters=filters,
        fields=[
            "name", "cycle", "reviewee", "reviewee_name",
            "relationship", "status", "is_anonymous"
        ],
        order_by="creation asc"
    )


@frappe.whitelist()
def submit_peer_review(request_name: str, responses: list):
    """
    Bulk-save competency ratings and mark the request Completed.
    Called from the employee portal or a custom dialog.

    responses = [{"competency": "Communication", "rating": 4, "comment": "..."}, ...]
    """
    if isinstance(responses, str):
        import json
        responses = json.loads(responses)

    doc = frappe.get_doc("Peer Review Request", request_name)

    if doc.reviewer != frappe.db.get_value(
        "Employee", {"user_id": frappe.session.user}, "name"
    ):
        frappe.throw("You are not the assigned reviewer for this request.", frappe.PermissionError)

    if doc.status == "Completed":
        frappe.throw("This review has already been submitted.")

    if not responses:
        frappe.throw("At least one competency rating is required.")

    doc.responses = []
    for r in responses:
        if not r.get("rating"):
            frappe.throw(f"Rating missing for competency: {r.get('competency', '?')}")
        doc.append("responses", {
            "competency": r["competency"],
            "rating":     r["rating"],
            "comment":    r.get("comment", ""),
        })

    doc.status       = "Completed"
    doc.submitted_on = now_datetime()
    doc.save(ignore_permissions=True)

    return {"status": "Completed", "request": request_name}