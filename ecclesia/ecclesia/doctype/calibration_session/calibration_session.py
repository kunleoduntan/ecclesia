# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CalibrationSession(Document):

    def on_submit(self):
        self._push_calibrated_ratings()
        self._warn_distribution()

    @frappe.whitelist()
    def auto_populate(self):
        filters = {"cycle": self.cycle}
        if self.department:
            filters["department"] = self.department
        existing = {e.performance_record for e in self.entries}
        added = 0
        for rec in frappe.get_all("Employee Performance Record",
                                  filters=filters, fields=["name", "final_rating"]):
            if rec.name in existing:
                continue
            self.append("entries", {"performance_record": rec.name,
                                    "proposed_rating": rec.final_rating, "is_locked": 0})
            added += 1
        self.save()
        return {"added": added}

    @frappe.whitelist()
    def lock_all(self):
        for entry in self.entries:
            if not entry.calibrated_rating:
                frappe.throw(f"Fill calibrated rating for {entry.employee_name} before locking.")
            entry.is_locked = 1
        self.save()

    def _push_calibrated_ratings(self):
        for entry in self.entries:
            if not entry.calibrated_rating:
                continue
            frappe.db.set_value("Employee Performance Record",
                                entry.performance_record, {
                                    "calibrated_rating": entry.calibrated_rating,
                                    "status": "Calibration",
                                })
        frappe.db.commit()

    def _warn_distribution(self):
        if not self.entries:
            return
        from collections import Counter
        dist   = Counter(e.calibrated_rating for e in self.entries if e.calibrated_rating)
        total  = len(self.entries)
        pct    = round(dist.get("Outstanding", 0) / total * 100, 1)
        if pct > 20:
            frappe.msgprint(
                f"{pct}% rated Outstanding — guideline is ≤20%. Review before releasing.",
                indicator="orange", alert=True
            )