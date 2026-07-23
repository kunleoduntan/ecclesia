# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

# ecclesia/doctype/performance_rating_scale/performance_rating_scale.py
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, nowdate

class PerformanceRatingScale(Document):

    def validate(self):
        self._validate_levels()
        self._validate_ranges()
        self._ensure_one_default()

    def before_save(self):
        self._compute_scale_stats()
        self._compute_usage_stats()
        self._compute_level_stats()
        self._update_dashboard_fields()

    # ── Validation ───────────────────────────────────────────────────

    def _validate_levels(self):
        if not self.rating_levels:
            frappe.throw(_("At least one rating level is required."))
        active_levels = [r for r in self.rating_levels if r.get("is_active", 1)]
        if not active_levels:
            frappe.throw(_("At least one active rating level is required."))

    def _validate_ranges(self):
        sorted_levels = sorted(
            [r for r in self.rating_levels if r.get("is_active", 1)],
            key=lambda r: flt(r.min_score))
        for i, row in enumerate(sorted_levels):
            if flt(row.min_score) >= flt(row.max_score):
                frappe.throw(
                    _("Row {0}: Min Score must be less than Max Score for '{1}'.").format(
                        i + 1, row.rating_label))
            if i > 0:
                prev = sorted_levels[i - 1]
                if flt(row.min_score) < flt(prev.max_score):
                    frappe.throw(
                        _("Rating levels overlap: '{0}' (max {1}%) and '{2}' (min {3}%).").format(
                            prev.rating_label, prev.max_score,
                            row.rating_label, row.min_score))

    def _ensure_one_default(self):
        if self.is_default:
            frappe.db.set_value("Performance Rating Scale",
                {"name": ("!=", self.name), "is_default": 1},
                "is_default", 0)

    # ── Computed stats ───────────────────────────────────────────────

    def _compute_scale_stats(self):
        active = [r for r in self.rating_levels if r.get("is_active", 1)]
        if not active:
            return
        self.total_levels = len(active)
        scores_min = [flt(r.min_score) for r in active]
        scores_max = [flt(r.max_score) for r in active]
        self.min_overall_score = min(scores_min)
        self.max_overall_score = max(scores_max)
        self.scale_midpoint    = round(
            (self.min_overall_score + self.max_overall_score) / 2, 1)
        # Compute midpoint and width on each child row
        for row in self.rating_levels:
            row.range_midpoint = round((flt(row.min_score) + flt(row.max_score)) / 2, 1)
            row.range_width    = round(flt(row.max_score) - flt(row.min_score), 1)

    def _compute_usage_stats(self):
        # Cycles using this scale
        total_cycles = frappe.db.count("Performance Cycle",
            {"rating_scale": self.name})
        self.total_cycles_used = total_cycles

        # Employees rated via cycles that use this scale
        cycles = frappe.db.sql_list("""
            SELECT name FROM `tabPerformance Cycle` WHERE rating_scale=%s
        """, self.name)
        if cycles:
            total_emp = frappe.db.sql("""
                SELECT COUNT(DISTINCT employee)
                FROM `tabEmployee Performance Record`
                WHERE cycle IN ({})
            """.format(",".join(["%s"] * len(cycles))), cycles)[0][0] or 0
            self.total_employees_rated = total_emp

            # Last used cycle
            last_cycle = frappe.db.sql("""
                SELECT name FROM `tabPerformance Cycle`
                WHERE rating_scale=%s ORDER BY end_date DESC LIMIT 1
            """, self.name)
            if last_cycle:
                self.last_used_cycle = last_cycle[0][0]

            # Score distribution
            epr_scores = frappe.db.sql("""
                SELECT composite_score FROM `tabEmployee Performance Record`
                WHERE cycle IN ({}) AND composite_score > 0
            """.format(",".join(["%s"] * len(cycles))), cycles, as_list=True)
            scores = [flt(r[0]) for r in epr_scores]
            if scores:
                self.avg_score_given = round(sum(scores) / len(scores), 1)
                mean = self.avg_score_given
                variance = sum((s - mean) ** 2 for s in scores) / len(scores)
                self.score_std_dev = round(variance ** 0.5, 1)
                # Bias detection
                mid = flt(self.scale_midpoint)
                if mean > mid + 10:
                    self.bias_indicator = "Leniency Bias"
                elif mean < mid - 10:
                    self.bias_indicator = "Severity Bias"
                elif self.score_std_dev < 5:
                    self.bias_indicator = "Central Tendency Bias"
                else:
                    self.bias_indicator = "No Significant Bias"

                # Distribution by band
                band_counts = {}
                for r in self.rating_levels:
                    if not r.get("is_active", 1):
                        continue
                    count = sum(1 for s in scores
                                if flt(r.min_score) <= s <= flt(r.max_score))
                    band_counts[r.rating_label] = count
                if band_counts:
                    total = len(scores)
                    self.rating_distribution = "  |  ".join(
                        f"{label}: {round(c/total*100)}%"
                        for label, c in band_counts.items()
                    )
        # Effectiveness
        if self.total_cycles_used >= 3:
            self.scale_effectiveness = "Highly Effective"
        elif self.total_cycles_used >= 1:
            self.scale_effectiveness = "Effective"
        else:
            self.scale_effectiveness = "Rarely Used"

    def _compute_level_stats(self):
        """Update usage_count on each rating level child row."""
        cycles = frappe.db.sql_list("""
            SELECT name FROM `tabPerformance Cycle` WHERE rating_scale=%s
        """, self.name)
        if not cycles:
            return
        epr_scores = frappe.db.sql("""
            SELECT composite_score FROM `tabEmployee Performance Record`
            WHERE cycle IN ({}) AND composite_score > 0
        """.format(",".join(["%s"] * len(cycles))), cycles, as_list=True)
        scores = [flt(r[0]) for r in epr_scores]
        for row in self.rating_levels:
            count = sum(1 for s in scores
                        if flt(row.min_score) <= s <= flt(row.max_score))
            row.usage_count = count
            if count > 0:
                row.last_used_date = nowdate()
                in_band = [s for s in scores
                           if flt(row.min_score) <= s <= flt(row.max_score)]
                row.avg_score_given = round(sum(in_band) / count, 1)
                row.variance_from_midpoint = round(
                    row.avg_score_given - row.range_midpoint, 1)
            total_used = len(scores)
            if total_used > 0:
                pct = count / total_used * 100
                if pct >= 30:
                    row.rating_effectiveness = "High Usage"
                elif pct >= 15:
                    row.rating_effectiveness = "Medium Usage"
                elif pct >= 5:
                    row.rating_effectiveness = "Low Usage"
                else:
                    row.rating_effectiveness = "Rarely Used"

    def _update_dashboard_fields(self):
        self.dashboard_summary = (
            f"{self.scale_name}  |  Status: {self.status or 'Draft'}"
            f"  |  Levels: {self.total_levels or 0}")
        self.dashboard_range = (
            f"{self.min_overall_score or 0}% – {self.max_overall_score or 0}%"
            f"  (Mid: {self.scale_midpoint or 0}%)")
        self.dashboard_usage = (
            f"{self.total_cycles_used or 0} cycles"
            f"  |  {self.total_employees_rated or 0} employees")
        self.dashboard_effectiveness = (
            f"{self.scale_effectiveness or '—'}"
            f"  |  Bias: {self.bias_indicator or '—'}")

    # ── Rating lookup ────────────────────────────────────────────────

    def get_rating_for_score(self, score):
        for row in sorted(self.rating_levels,
                          key=lambda r: flt(r.min_score), reverse=True):
            if not row.get("is_active", 1):
                continue
            if flt(score) >= flt(row.min_score):
                return {
                    "label": row.rating_label,
                    "value": flt(row.rating_value),
                    "color": row.color_indicator,
                }
        return {"label": "Below Scale", "value": 0, "color": "Red"}