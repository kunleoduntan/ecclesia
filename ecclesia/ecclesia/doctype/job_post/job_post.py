# ecclesia/doctype/job_post/job_post.py
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import cint, nowdate, now_datetime, get_url


class JobPost(Document):

    def validate(self):
        self._auto_fill_from_opening()
        self._auto_fill_apply_url()
        self._update_counts()
        self._validate_targets()

    def before_submit(self):
        self._update_counts()
        if cint(self.post_immediately):
            self.posting_status = "Posting"
        else:
            self.posting_status = "Scheduled"

    def on_submit(self):
        if cint(self.post_immediately):
            frappe.enqueue(
                "ecclesia.api.job_post_api._execute_job_post",
                job_post_name=self.name,
                queue="short",
                timeout=180
            )

    def on_cancel(self):
        self.posting_status = "Expired"
        for target in self.targets:
            if target.post_status in ("Pending", "Scheduled"):
                frappe.db.set_value("Job Post Target", target.name,
                                    "post_status", "Skipped")

    # ── Private helpers ────────────────────────────────────────────────

    def _auto_fill_from_opening(self):
        if not self.job_opening:
            return
        job = frappe.get_doc("Job Opening", self.job_opening)
        if not self.base_description and job.description:
            self.base_description = job.description
        if not self.location_display:
            self.location_display = getattr(job, "location", "") or ""
        if not self.key_requirements:
            # Try to extract from description
            desc_plain = frappe.utils.strip_html(job.description or "")
            if len(desc_plain) > 200:
                self.key_requirements = desc_plain[:300]

    def _auto_fill_apply_url(self):
        if not self.apply_url and self.job_opening:
            self.apply_url = get_url(f"/apply?job={self.job_opening}")

    def _update_counts(self):
        included  = [t for t in self.targets if cint(t.include)]
        posted    = [t for t in included if t.post_status == "Posted"]
        self.total_platforms    = len(included)
        self.successfully_posted = len(posted)
        self.total_views = sum(t.views or 0 for t in self.targets)
        self.total_likes = sum(t.likes or 0 for t in self.targets)

    def _validate_targets(self):
        if not self.targets:
            frappe.msgprint(
                _("No platform targets added. Add at least one platform before posting."),
                indicator="orange", alert=True
            )
            return
        active_platforms = frappe.db.sql_list("""
            SELECT name FROM `tabJob Board Platform` WHERE status = 'Active'
        """)
        for row in self.targets:
            if cint(row.include) and row.platform not in active_platforms:
                frappe.msgprint(
                    _(f"Platform '{row.platform}' is not Active. "
                      f"Activate it in Job Board Platform before posting."),
                    indicator="orange", alert=True
                )

    def populate_all_active_platforms(self):
        """Add all active Job Board Platforms as targets (called from JS button)."""
        existing = {t.platform for t in self.targets}
        platforms = frappe.get_all("Job Board Platform",
            filters={"status": "Active"},
            fields=["name","platform_name","platform_type","character_limit"])
        added = 0
        for p in platforms:
            if p.name not in existing:
                self.append("targets", {
                    "platform":       p.name,
                    "platform_name":  p.platform_name,
                    "platform_type":  p.platform_type,
                    "character_limit":p.character_limit,
                    "include":        1,
                    "post_status":    "Pending",
                })
                added += 1
        return added
