# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/ecclesia/doctype/board_resolution/board_resolution.py
"""
Board Resolution — Python Controller
Records board decisions, tracks implementation, and flags CAC filing requirements.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate, getdate


class BoardResolution(Document):

    def before_insert(self):
        self._set_resolution_number()

    def validate(self):
        self._validate_quorum()
        self._flag_cac_requirement()

    def on_submit(self):
        self._validate_signatories_complete()
        self.db_set("implementation_status", "Pending")
        self._create_compliance_task()

    def on_cancel(self):
        pass

    # ── Private helpers ───────────────────────────────────────────────────────

    def _set_resolution_number(self):
        """Auto-generate resolution number if not provided."""
        if not self.resolution_number and self.meeting_type and self.meeting_date:
            d = getdate(self.meeting_date)
            count = frappe.db.count("Board Resolution", {
                "company": self.company,
                "meeting_type": self.meeting_type,
                "meeting_date": ["between", [f"{d.year}-01-01", f"{d.year}-12-31"]]
            })
            prefix_map = {
                "Board Meeting": "BR",
                "AGM": "AGM",
                "EGM": "EGM",
                "Committee Meeting": "CM",
                "Written Resolution": "WR"
            }
            prefix = prefix_map.get(self.meeting_type, "RES")
            self.resolution_number = f"{prefix}-{d.year}-{count + 1:03d}"

    def _validate_quorum(self):
        if self.directors_present is not None and self.directors_present < 1:
            frappe.throw(_("Directors Present must be at least 1."))

    def _flag_cac_requirement(self):
        """
        Certain resolution categories require CAC notification filing.
        Automatically set the flag.
        """
        requires_cac = {
            "Appointment / Removal",  # Director changes → CAC Form 7
            "Capital",                 # Share capital changes → CAC Form 2
            "Contracts",               # Debentures / charges → CAC Form 8C
        }
        if self.resolution_category in requires_cac:
            if not self.cac_filing_required:
                self.cac_filing_required = 1
                frappe.msgprint(
                    _("This resolution category typically requires a CAC filing. "
                      "The 'CAC Filing Required' flag has been set."),
                    indicator="orange",
                    alert=True
                )

    def _validate_signatories_complete(self):
        """
        Written Resolutions (round-robin board decisions signed outside a formal
        meeting) cannot be submitted/approved until every signatory has signed.
        No-op for all other meeting types, and no-op if the Signatories table
        is empty (older resolutions predating this field, or resolutions where
        the secretary hasn't populated it).
        """
        if self.meeting_type != "Written Resolution":
            return
        if not self.get("signatories"):
            return
        unsigned = [
            s.signatory_name or s.board_member
            for s in self.signatories
            if not s.signed
        ]
        if unsigned:
            frappe.throw(
                _("Cannot submit: the following signatories have not yet signed: {0}").format(
                    ", ".join(unsigned)
                )
            )

    def _create_compliance_task(self):
        """
        For CAC-filing-required resolutions, create a Compliance Task
        to remind the company secretary to file within 15 days.
        """
        if not self.cac_filing_required:
            return
        if frappe.db.exists("Compliance Task", {
            "related_doctype": "Board Resolution",
            "related_document": self.name
        }):
            return

        task = frappe.new_doc("Compliance Task")
        task.task_title   = f"CAC Filing: {self.resolution_number or self.resolution_title[:50]}"
        task.task_type    = "Filing"
        task.obligation_type = "CAC Annual Return"
        task.company      = self.company
        task.priority     = "High"
        task.description  = (
            f"File CAC form for Board Resolution {self.resolution_number} "
            f"dated {self.meeting_date}. Category: {self.resolution_category}."
        )
        from frappe.utils import add_days
        task.start_date       = nowdate()
        task.target_completion = add_days(self.meeting_date, 15)
        task.related_doctype  = "Board Resolution"
        task.related_document = self.name
        if self.responsible_officer:
            task.assigned_owner = self.responsible_officer
        task.insert(ignore_permissions=True)
        frappe.msgprint(
            _("Compliance Task created for CAC filing: {0}").format(task.name),
            indicator="green", alert=True
        )
