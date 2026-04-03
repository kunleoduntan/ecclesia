# Copyright (c) 2026, kunle Oduntan and contributors
# For license information, please see license.txt

"""
GL Audit Log — Controller
==========================
Immutable, tamper-evident record of every GL-related event.
Created automatically by gl_monitor.py hooks; never created manually.
"""

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, get_time, flt


# Suspicious patterns — hours outside which transactions raise risk
BUSINESS_HOURS = (7, 20)   # 07:00 – 20:00


class GlAuditLog(Document):

    # ─────────────────────────────────────────────────────────────
    # Lifecycle hooks
    # ─────────────────────────────────────────────────────────────

    def before_insert(self):
        self._assign_transaction_code()
        self._detect_risk_patterns()

    def after_insert(self):
        if self.risk_flag:
            self._auto_raise_finding()

    def before_save(self):
        """Prevent edits after insert (immutability)."""
        if not self.is_new():
            frappe.throw(
                "GL Audit Logs are immutable. "
                "This record cannot be edited after creation.",
                title="Immutable Record",
            )

    # ─────────────────────────────────────────────────────────────
    # Private helpers
    # ─────────────────────────────────────────────────────────────

    def _assign_transaction_code(self):
        """Pull transaction code from registry for the voucher type."""
        if self.voucher_type and not self.transaction_code:
            code = frappe.db.get_value(
                "Auditable DocType Registry",
                {"doctype_name": self.voucher_type},
                "transaction_code",
            )
            if code:
                self.transaction_code = code

    def _detect_risk_patterns(self):
        """
        Score event and set risk_flag + flag_reason if suspicious.
        """
        reasons = []

        # 1. Cancellation always flagged
        if self.event_type == "GL Entry Cancelled":
            reasons.append("GL Entry cancelled — requires review of reversal reason.")

        # 2. Amendment chain
        if self.event_type == "GL Entry Amended":
            prior = frappe.db.count(
                "GL Audit Log",
                {"voucher_no": self.voucher_no, "event_type": "GL Entry Amended"},
            )
            if prior >= 1:
                reasons.append(
                    f"Multiple GL amendments detected on {self.voucher_no} "
                    f"({prior + 1} total)."
                )

        # 3. Suspense account usage
        if self.gl_account:
            acct_lower = (self.gl_account or "").lower()
            if any(k in acct_lower for k in ["suspense", "holding", "clearing", "wash"]):
                reasons.append(
                    f"Suspense/clearing account used: {self.gl_account}."
                )

        # 4. After-hours posting
        if self.event_datetime:
            try:
                t = get_time(str(self.event_datetime))
                hour = t.hour
                if hour < BUSINESS_HOURS[0] or hour >= BUSINESS_HOURS[1]:
                    reasons.append(
                        f"Transaction posted outside business hours ({t.strftime('%H:%M')})."
                    )
            except Exception:
                pass

        # 5. Round-number posting
        for amt in [flt(self.debit_amount), flt(self.credit_amount)]:
            if amt > 0 and amt % 1000 == 0 and amt >= 10000:
                reasons.append(
                    f"Round-number amount detected: {amt:,.0f} — statistical anomaly."
                )
                break

        # 6. Reconciliation variance
        if self.event_type == "Reconciliation Variance":
            reasons.append("GL-to-document reconciliation variance detected.")

        if reasons:
            self.risk_flag = 1
            self.flag_reason = " | ".join(reasons)

    def _auto_raise_finding(self):
        """Auto-create Audit Finding for critical events."""
        existing = frappe.db.exists(
            "Audit Finding",
            {"gl_entry_reference": self.voucher_no or self.name},
        )
        if existing:
            return

        auto_raise_events = {
            "GL Entry Cancelled": ("GL Posting Error", "High"),
            "Reconciliation Variance": ("GL Posting Error", "High"),
            "Suspense Account Used": ("Policy Non-Compliance", "Medium"),
        }

        if self.event_type not in auto_raise_events:
            return

        finding_type, risk_rating = auto_raise_events[self.event_type]

        finding = frappe.get_doc({
            "doctype": "Audit Finding",
            "finding_title": f"GL Exception: {self.event_type} — {self.voucher_no}",
            "finding_type": finding_type,
            "risk_rating": risk_rating,
            "source": "Continuous Monitoring",
            "status": "Open",
            "reference_doctype": self.voucher_type,
            "reference_name": self.voucher_no,
            "transaction_code": self.transaction_code,
            "gl_entry_reference": self.voucher_no,
            "observation": self.flag_reason,
            "transaction_amount": flt(self.debit_amount) or flt(self.credit_amount),
            "transaction_date": self.posting_date,
        })

        finding.insert(ignore_permissions=True)

        frappe.db.set_value(
            "GL Audit Log",
            self.name,
            "linked_finding",
            finding.name
        )

        frappe.logger().info(
            f"Ecclesia GL Monitor: auto-raised finding {finding.name} "
            f"for {self.event_type} on {self.voucher_no}"
        )


# ─────────────────────────────────────────────────────────────
# Public Service Function (Used by gl_monitor.py)
# ─────────────────────────────────────────────────────────────

def create_gl_log(
    event_type,
    voucher_type=None,
    voucher_no=None,
    account=None,
    debit=0,
    credit=0,
    posting_date=None,
):
    """
    Create immutable GL Audit Log entry.
    Safe for use in hooks.
    """

    try:
        # Prevent duplicate identical logs
        exists = frappe.db.exists(
            "GL Audit Log",
            {
                "event_type": event_type,
                "voucher_type": voucher_type,
                "voucher_no": voucher_no,
                "gl_account": account,
                "debit_amount": flt(debit),
                "credit_amount": flt(credit),
                "posting_date": posting_date,
            },
        )
        if exists:
            return exists

        log = frappe.get_doc({
            "doctype": "GL Audit Log",
            "naming_series": "GAL-",
            "event_type": event_type,
            "event_datetime": now_datetime(),
            "voucher_type": voucher_type,
            "voucher_no": voucher_no,
            "gl_account": account,
            "debit_amount": flt(debit),
            "credit_amount": flt(credit),
            "posting_date": posting_date,
            "event_user": frappe.session.user,
        })

        log.insert(ignore_permissions=True)
        return log.name

    except Exception as e:
        frappe.log_error(
            f"Failed to create GL Audit Log for {voucher_type} {voucher_no}: {e}",
            "Ecclesia GL Audit Log Error"
        )
        return None