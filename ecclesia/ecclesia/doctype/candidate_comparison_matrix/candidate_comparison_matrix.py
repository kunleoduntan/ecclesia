# ecclesia/doctype/candidate_comparison_matrix/candidate_comparison_matrix.py
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, nowdate


class CandidateComparisonMatrix(Document):

    def validate(self):
        if not self.candidates:
            frappe.throw(_("Please add at least two candidates to compare."))
        self._auto_rank()

    def before_save(self):
        self.comparison_date = nowdate()

    def on_submit(self):
        self._generate_ai_comparison()

    def _auto_rank(self):
        """Sort candidates by total_score descending and assign rank."""
        sorted_rows = sorted(
            self.candidates,
            key=lambda r: flt(r.total_score),
            reverse=True
        )
        for i, row in enumerate(sorted_rows, 1):
            row.hr_rank = i

    def _generate_ai_comparison(self):
        if len(self.candidates) < 2:
            return
        frappe.enqueue(
            "ecclesia.api.recruitment_ai.generate_candidate_comparison",
            matrix_name=self.name,
            queue="short",
            timeout=60
        )


@frappe.whitelist()
def generate_candidate_comparison(matrix_name):
    """
    Whitelisted background function — called via frappe.enqueue.
    Generates AI comparison narrative for the Candidate Comparison Matrix.
    """
    try:
        import requests

        doc = frappe.get_doc("Candidate Comparison Matrix", matrix_name)

        # Build one line per candidate — join uses a variable, not a backslash
        # escape inside an expression (avoids the unterminated-string-literal
        # bug that occurs when Python writes \n inside a triple-quoted heredoc).
        sep = "\n"
        lines = []
        for r in sorted(doc.candidates, key=lambda x: flt(x.total_score), reverse=True):
            lines.append(
                "- {name}: Score {score}%, AI verdict: {verdict}, Rank #{rank}".format(
                    name=r.candidate_name,
                    score=r.total_score,
                    verdict=r.ai_recommendation or "Not assessed",
                    rank=r.hr_rank,
                )
            )
        candidates_text = sep.join(lines)

        prompt = (
            "You are an HR consultant. Compare these candidates for the position: {opening}.\n\n"
            "Candidates:\n{candidates}\n\n"
            "In 3-4 sentences, explain who the top candidates are and why, "
            "and any considerations HR should weigh. Be specific and professional."
        ).format(opening=doc.job_opening, candidates=candidates_text)

        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json"},
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 300,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=25
        )
        if resp.ok:
            text = resp.json().get("content", [{}])[0].get("text", "")
            if text:
                frappe.db.set_value(
                    "Candidate Comparison Matrix",
                    matrix_name,
                    "ai_comparison",
                    text
                )
                frappe.db.commit()

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Candidate Comparison AI Error"
        )