# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from ecclesia.utils.score_engine import compute_composite_score


class ManagerReview(Document):

    def before_insert(self):
        self._mirror_goals()

    def validate(self):
        self._validate_score_range()
        self._validate_narrative_fields()

    def before_submit(self):
        self._preflight_check()

    def on_submit(self):
        frappe.db.set_value("Manager Review", self.name, "status", "Submitted")
        compute_composite_score(self.performance_record)
        frappe.db.set_value(
            "Employee Performance Record",
            self.performance_record,
            "status", "Calibration"
        )
        self._notify_hr()

    # ── Goal mirroring ───────────────────────────────────────────────

    def _mirror_goals(self):
        """
        Copy goals from the linked Employee Performance Record into the
        goals_commentary child table so the manager reviews each goal inline.
        Only runs on insert — subsequent edits to EPR goals are not re-mirrored
        to avoid overwriting manager comments already entered.
        """
        if not self.performance_record:
            return

        epr = frappe.get_doc("Employee Performance Record", self.performance_record)
        self.goals_commentary = []

        for g in epr.goals:
            self.append("goals_commentary", {
                "performance_goal": g.name,
                "goal":             g.goal_description,
                "kpi":              g.kpi,
                "target_value":     g.target_value,
                "actual_value":     g.actual_value,
                "achievement_pct":  g.achievement_pct or 0,
                "manager_score":    "",
                "manager_comment":  "",
            })

    # ── Validation ───────────────────────────────────────────────────

    def _validate_score_range(self):
        if self.overall_score is None:
            return
        if not (1 <= self.overall_score <= 5):
            frappe.throw(
                f"Overall Score must be between 1 and 5 — got {self.overall_score}.",
                title="Invalid Score"
            )

    def _validate_narrative_fields(self):
        """Warn (not block) on save if narratives are empty — block only on submit."""
        if self.docstatus == 1:
            return
        if not (self.strengths or "").strip():
            frappe.msgprint(
                "Key Strengths is empty. This field is required before submission.",
                alert=True, indicator="orange"
            )
        if not (self.areas_for_improvement or "").strip():
            frappe.msgprint(
                "Areas for Improvement is empty. This field is required before submission.",
                alert=True, indicator="orange"
            )

    def _preflight_check(self):
        """Hard validation gate — fires on submit, blocks if anything is missing."""
        errors = []

        if not self.overall_score:
            errors.append("Overall Score is required.")
        elif not (1 <= self.overall_score <= 5):
            errors.append("Overall Score must be between 1 and 5.")

        if not self.recommended_rating:
            errors.append("Recommended Rating is required.")

        if not (self.strengths or "").strip():
            errors.append("Key Strengths narrative is required.")

        if not (self.areas_for_improvement or "").strip():
            errors.append("Areas for Improvement is required.")

        unscored = [
            r.goal for r in (self.goals_commentary or [])
            if not r.manager_score
        ]
        if unscored:
            errors.append(
                f"{len(unscored)} goal(s) have no manager score: "
                + ", ".join(str(g) for g in unscored[:3])
                + ("…" if len(unscored) > 3 else "")
            )

        if errors:
            frappe.throw(
                "<ul>" + "".join(f"<li>{e}</li>" for e in errors) + "</ul>",
                title="Cannot submit — resolve the following"
            )

    # ── Computed helpers ─────────────────────────────────────────────

    def get_goal_average(self) -> float:
        """
        Average of all scored goal rows in goals_commentary.
        Used by JS via frm.call() and by the score engine blending logic.
        """
        scored = [
            float(r.manager_score)
            for r in (self.goals_commentary or [])
            if r.manager_score
        ]
        return round(sum(scored) / len(scored), 2) if scored else 0.0

    def suggest_rating(self) -> str:
        """Map current overall_score to a rating label."""
        s = self.overall_score or 0
        if   s >= 4.5: return "Outstanding"
        elif s >= 3.5: return "Exceeds Expectations"
        elif s >= 2.5: return "Meets Expectations"
        elif s >= 1.5: return "Needs Improvement"
        else:          return "Unsatisfactory"

    def rating_deviation(self) -> int:
        """
        Number of rating bands between recommended_rating and the system
        final_rating on the EPR. Used by JS to surface a deviation warning.
        """
        bands = [
            "Unsatisfactory", "Needs Improvement", "Meets Expectations",
            "Exceeds Expectations", "Outstanding"
        ]
        sys_rating = frappe.db.get_value(
            "Employee Performance Record",
            self.performance_record, "final_rating"
        )
        if not sys_rating or not self.recommended_rating:
            return 0
        try:
            return abs(bands.index(self.recommended_rating) - bands.index(sys_rating))
        except ValueError:
            return 0

    # ── Notification ─────────────────────────────────────────────────

    def _notify_hr(self):
        hr_users = frappe.db.sql_list("""
            SELECT parent FROM `tabHas Role`
            WHERE role = 'HR Manager' AND parenttype = 'User'
        """)
        if not hr_users:
            return

        cycle_title = frappe.db.get_value(
            "Employee Performance Record", self.performance_record, "cycle"
        )
        link = frappe.utils.get_url(f"/app/manager-review/{self.name}")

        for user in hr_users:
            frappe.sendmail(
                recipients=[user],
                subject=f"Manager review submitted — {self.employee_name}",
                message=f"""
                    <div style="font-family:sans-serif;max-width:600px;padding:24px">
                        <p><strong>{self.manager}</strong> has submitted a manager review
                        for <strong>{self.employee_name}</strong>
                        ({cycle_title or self.performance_record}).</p>
                        <p>
                            <strong>Overall Score:</strong> {self.overall_score} / 5<br>
                            <strong>Recommended Rating:</strong> {self.recommended_rating}
                        </p>
                        <p>
                            <a href="{link}"
                               style="display:inline-block;padding:10px 20px;background:#534AB7;
                                      color:#fff;border-radius:6px;text-decoration:none;
                                      font-weight:500">
                                View Review
                            </a>
                        </p>
                    </div>
                """,
                now=False
            )


# ── Module-level doc_event hook ───────────────────────────────────────

def on_submit_hook(doc, method):
    """
    Frappe doc_events entry point. hooks.py points here:

        doc_events = {
            "Manager Review": {
                "on_submit": "ecclesia.doctype.manager_review.manager_review.on_submit_hook"
            }
        }

    The class on_submit() already handles everything; this wrapper exists
    purely because Frappe doc_events require a module-level callable,
    not a class method reference.
    """
    pass  # on_submit() on the Document class fires automatically before this hook