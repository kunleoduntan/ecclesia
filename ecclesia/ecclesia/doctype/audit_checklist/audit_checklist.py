# Copyright (c) 2026, kunle Oduntan and contributors
# For license information, please see license.txt

"""
Audit Checklist Controller
===========================
Tracks progress of checklist completion and auto-raises findings
when checklist items are marked as Fail or Exception.
"""

import frappe
from frappe.model.document import Document
from frappe.utils import flt, cint


class AuditChecklist(Document):

    def validate(self):
        self._update_progress()

    def _update_progress(self):
        if not self.checklist_items:
            return

        total      = len(self.checklist_items)
        tested     = sum(1 for i in self.checklist_items if i.result != "Not Tested")
        passed     = sum(1 for i in self.checklist_items if i.result == "Pass")
        failed     = sum(1 for i in self.checklist_items if i.result in ("Fail", "Exception"))
        na_count   = sum(1 for i in self.checklist_items if i.result == "N/A")

        effective_total = total - na_count

        self.total_items          = total
        self.items_tested         = tested
        self.items_passed         = passed
        self.items_failed         = failed
        self.completion_percentage= round((tested / total * 100) if total > 0 else 0, 1)

        # Update status
        if tested == 0:
            self.status = "Not Started"
        elif tested < total:
            self.status = "In Progress"
        else:
            self.status = "Completed"

        # Overall result
        if effective_total > 0:
            fail_rate = failed / effective_total
            if fail_rate == 0:
                self.overall_result = "Satisfactory"
            elif fail_rate <= 0.2:
                self.overall_result = "Needs Improvement"
            else:
                self.overall_result = "Unsatisfactory"

    def on_update(self):
        """Auto-raise findings for failed checklist items that don't have one yet."""
        for item in self.checklist_items:
            if item.result in ("Fail", "Exception") and not item.linked_finding:
                self._raise_finding_from_item(item)

    def _raise_finding_from_item(self, item):
        """Create an Audit Finding from a failed checklist item."""
        transaction_code = frappe.db.get_value(
            "Auditable DocType Registry",
            {"doctype_name": self.doctype_name},
            "transaction_code"
        ) or self.transaction_code

        try:
            finding = frappe.get_doc({
                "doctype":           "Audit Finding",
                "finding_title":     f"Checklist Exception: {item.control_area} — {self.doctype_name}",
                "finding_type":      "Control Deficiency",
                "risk_rating":       item.risk_level or "Medium",
                "reference_doctype": self.doctype_name,
                "reference_name":    self.doctype_name,  # DocType-level finding
                "transaction_code":  transaction_code,
                "audit_engagement":  self.audit_engagement,
                "source":            "Auditor",
                "status":            "Open",
                "coso_component":    item.coso_component,
                "observation":       (
                    f"Checklist item #{item.item_number} failed during audit of {self.doctype_name}.\n\n"
                    f"Control Area: {item.control_area}\n"
                    f"Test Procedure: {item.test_procedure}\n"
                    f"Exception Detail: {item.exception_detail or 'See auditor notes.'}\n"
                    f"Auditor Note: {item.auditor_note or ''}"
                ),
                "criteria": item.test_procedure,
                "condition": item.exception_detail or item.auditor_note,
            })
            finding.insert(ignore_permissions=True)

            # Link back to checklist item
            item.linked_finding = finding.name
            frappe.db.set_value(
                "Audit Checklist Item",
                item.name,
                "linked_finding",
                finding.name
            )
        except Exception as e:
            frappe.log_error(f"Failed to auto-raise finding from checklist: {e}")
