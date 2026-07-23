# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

# Copyright (c) 2026, Value Impacts Consulting
# Intercompany Invoice — Python Controller
# Handles: totals, interest, WHT/VAT, GL Journal Entry auto-posting

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import (
    flt, cint, getdate, date_diff, nowdate, fmt_money,
    add_days, get_first_day, get_last_day
)
from frappe.utils.data import rounded
import json


class IntercompanyInvoice(Document):

    # ------------------------------------------------------------------
    # DOCUMENT HOOKS
    # ------------------------------------------------------------------

    def validate(self):
        self.validate_companies()
        self.validate_accounts()
        self.calculate_item_amounts()
        self.calculate_interest()
        self.calculate_taxes()
        self.calculate_grand_total()
        self.set_status()

    def on_submit(self):
        self.validate_gl_accounts_mandatory()
        self.create_journal_entry()
        self.set_status()

    def on_cancel(self):
        self.cancel_journal_entry()
        self.db_set("status", "Cancelled")
        self.db_set("gl_entry_status", "Cancelled")

    def before_amend(self):
        self.db_set("journal_entry", None)
        self.db_set("gl_entry_status", "Pending")

    # ------------------------------------------------------------------
    # VALIDATIONS
    # ------------------------------------------------------------------

    def validate_companies(self):
        if self.company == self.counterparty_company:
            frappe.throw(_("Issuing Company and Counterparty Company cannot be the same."))

    def validate_accounts(self):
        if self.intercompany_account:
            acc = frappe.get_value(
                "Account", self.intercompany_account,
                ["company", "account_type", "is_group"], as_dict=True
            )
            if acc:
                if acc.company != self.company:
                    frappe.throw(_(
                        "Intercompany Account <b>{0}</b> does not belong to company <b>{1}</b>."
                    ).format(self.intercompany_account, self.company))
                if acc.is_group:
                    frappe.throw(_("Intercompany Account cannot be a group account."))

    def validate_gl_accounts_mandatory(self):
        if not self.intercompany_account:
            frappe.throw(_("Intercompany Account (Issuer) is mandatory before submission."))
        if not self.items:
            frappe.throw(_("At least one item line is required."))

    # ------------------------------------------------------------------
    # ITEM CALCULATIONS
    # ------------------------------------------------------------------

    def calculate_item_amounts(self):
        for row in self.items:
            row.amount = flt(row.qty) * flt(row.rate)
            row.tax_amount = flt(row.amount) * flt(row.tax_rate) / 100
            row.interest_amount = flt(row.amount) * flt(row.interest_rate) / 100
            row.line_total = row.amount + row.tax_amount + row.interest_amount

    # ------------------------------------------------------------------
    # INTEREST COMPUTATION
    # ------------------------------------------------------------------

    def calculate_interest(self):
        """
        Arms-length interest on the principal (total_base_amount).
        Supports: Actual/365, Actual/360, 30/360
        """
        if not self.interest_period_from or not self.interest_period_to:
            self.days_outstanding = 0
            self.total_interest_charged = 0
            return

        days = date_diff(self.interest_period_to, self.interest_period_from)
        self.days_outstanding = max(days, 0)

        if flt(self.annual_interest_rate) == 0 or self.days_outstanding == 0:
            self.total_interest_charged = 0
            return

        basis = self.interest_basis or "Actual/365"
        principal = flt(self.total_base_amount)

        if basis == "Actual/365":
            divisor = 365
        elif basis == "Actual/360":
            divisor = 360
        elif basis == "30/360":
            # 30/360: treat each month as 30 days
            d1 = getdate(self.interest_period_from)
            d2 = getdate(self.interest_period_to)
            days_360 = (
                (d2.year - d1.year) * 360
                + (d2.month - d1.month) * 30
                + (min(d2.day, 30) - min(d1.day, 30))
            )
            self.days_outstanding = days_360
            divisor = 360
        else:
            divisor = 365

        interest = principal * (flt(self.annual_interest_rate) / 100) * (self.days_outstanding / divisor)
        self.total_interest_charged = rounded(interest, 2)

    # ------------------------------------------------------------------
    # TAX COMPUTATION (Document Level)
    # ------------------------------------------------------------------

    def calculate_taxes(self):
        base = flt(self.total_base_amount)

        # WHT (applied on gross base, deducted at source)
        self.withholding_tax_amount = rounded(base * flt(self.withholding_tax_rate) / 100, 2)

        # VAT (applied on base + interest, exclusive of WHT)
        if cint(self.vat_applicable):
            vat_base = base + flt(self.total_interest_charged)
            self.vat_amount = rounded(vat_base * flt(self.vat_rate) / 100, 2)
        else:
            self.vat_amount = 0

    # ------------------------------------------------------------------
    # GRAND TOTAL
    # ------------------------------------------------------------------

    def calculate_grand_total(self):
        total_base = sum(flt(r.amount) for r in self.items)
        total_tax = sum(flt(r.tax_amount) for r in self.items)
        total_item_interest = sum(flt(r.interest_amount) for r in self.items)

        self.total_base_amount = rounded(total_base, 2)
        self.total_tax_amount = rounded(total_tax + flt(self.vat_amount), 2)
        self.total_interest_amount = rounded(
            total_item_interest + flt(self.total_interest_charged), 2
        )

        # Grand Total = base + all taxes + all interest − WHT (WHT is deducted)
        self.grand_total = rounded(
            self.total_base_amount
            + self.total_tax_amount
            + self.total_interest_amount
            - flt(self.withholding_tax_amount),
            2
        )

    # ------------------------------------------------------------------
    # STATUS
    # ------------------------------------------------------------------

    def set_status(self):
        if self.docstatus == 0:
            self.status = "Draft"
        elif self.docstatus == 2:
            self.status = "Cancelled"
        elif self.docstatus == 1:
            if self.gl_entry_status == "Posted":
                self.status = "Submitted"
            else:
                self.status = "Submitted"

    # ------------------------------------------------------------------
    # JOURNAL ENTRY CREATION
    # ------------------------------------------------------------------

    def create_journal_entry(self):
        """
        Creates a balanced Journal Entry for the intercompany invoice.

        GL Logic:
        ─────────────────────────────────────────────────────────
        DEBIT Intercompany Account  → if direction = "Debit Intercompany Account"
        CREDIT Income/Expense accounts per item line
        CREDIT/DEBIT VAT Payable account
        DEBIT WHT Payable (as WHT is withheld from the settlement amount)
        DEBIT/CREDIT Interest Income account

        If direction = "Credit Intercompany Account":
        CREDIT Intercompany Account
        DEBIT  Expense/Income accounts per item line
        ─────────────────────────────────────────────────────────
        """
        company = self.company
        direction = self.intercompany_direction  # "Debit..." or "Credit..."
        is_debit = direction == "Debit Intercompany Account"

        # Fetch default accounts
        company_doc = frappe.get_doc("Company", company)
        default_cost_center = company_doc.cost_center
        default_currency = self.currency or company_doc.default_currency

        accounts = []

        # ── 1. Intercompany GL Leg ──────────────────────────────
        ic_amount = flt(self.grand_total) + flt(self.withholding_tax_amount)  # gross receivable/payable
        accounts.append({
            "account": self.intercompany_account,
            "debit_in_account_currency":  ic_amount if is_debit else 0,
            "credit_in_account_currency": 0 if is_debit else ic_amount,
            "cost_center": default_cost_center,
            "user_remark": f"Intercompany Invoice: {self.name}",
            "party_type": "Company",
            "party": self.counterparty_company,
        })

        # ── 2. Item Lines ───────────────────────────────────────
        for row in self.items:
            if not row.income_account:
                frappe.throw(_(
                    "Row {0}: Income / Expense Account is required for GL posting."
                ).format(row.idx))

            accounts.append({
                "account": row.income_account,
                "debit_in_account_currency":  0 if is_debit else flt(row.amount),
                "credit_in_account_currency": flt(row.amount) if is_debit else 0,
                "cost_center": row.cost_center or default_cost_center,
                "user_remark": row.item_name,
            })

            # Per-line interest if any
            if flt(row.interest_amount):
                interest_account = self._get_interest_income_account(company)
                accounts.append({
                    "account": interest_account,
                    "debit_in_account_currency":  0 if is_debit else flt(row.interest_amount),
                    "credit_in_account_currency": flt(row.interest_amount) if is_debit else 0,
                    "cost_center": row.cost_center or default_cost_center,
                    "user_remark": f"Interest on {row.item_name}",
                })

        # ── 3. Document-Level Interest ──────────────────────────
        if flt(self.total_interest_charged):
            interest_account = self._get_interest_income_account(company)
            accounts.append({
                "account": interest_account,
                "debit_in_account_currency":  0 if is_debit else flt(self.total_interest_charged),
                "credit_in_account_currency": flt(self.total_interest_charged) if is_debit else 0,
                "cost_center": default_cost_center,
                "user_remark": f"Arms-length interest: {self.days_outstanding} days @ {self.annual_interest_rate}% p.a.",
            })

        # ── 4. VAT ──────────────────────────────────────────────
        if flt(self.vat_amount):
            vat_account = self._get_vat_account(company)
            accounts.append({
                "account": vat_account,
                "debit_in_account_currency":  0 if is_debit else flt(self.vat_amount),
                "credit_in_account_currency": flt(self.vat_amount) if is_debit else 0,
                "cost_center": default_cost_center,
                "user_remark": f"Output VAT @ {self.vat_rate}%",
            })

        # ── 5. WHT (always a liability — debit the payable) ─────
        if flt(self.withholding_tax_amount):
            wht_account = self._get_wht_account(company)
            accounts.append({
                "account": wht_account,
                "debit_in_account_currency":  0,
                "credit_in_account_currency": flt(self.withholding_tax_amount),
                "cost_center": default_cost_center,
                "user_remark": f"WHT @ {self.withholding_tax_rate}% — {self.name}",
            })

        # ── Build and submit JE ─────────────────────────────────
        je = frappe.get_doc({
            "doctype": "Journal Entry",
            "voucher_type": "Journal Entry",
            "posting_date": self.posting_date,
            "company": company,
            "multi_currency": 1 if default_currency != company_doc.default_currency else 0,
            "user_remark": (
                f"Intercompany Invoice: {self.name} | "
                f"{self.company} → {self.counterparty_company} | "
                f"{self.transaction_type}"
            ),
            "custom_intercompany_invoice": self.name,
            "accounts": accounts,
        })

        je.insert(ignore_permissions=True)
        je.submit()

        self.db_set("journal_entry", je.name)
        self.db_set("gl_entry_status", "Posted")

        frappe.msgprint(
            _("Journal Entry <b>{0}</b> created and submitted.").format(
                frappe.utils.get_link_to_form("Journal Entry", je.name)
            ),
            indicator="green",
            alert=True,
        )

    def cancel_journal_entry(self):
        if self.journal_entry:
            je_status = frappe.get_value("Journal Entry", self.journal_entry, "docstatus")
            if je_status == 1:
                je = frappe.get_doc("Journal Entry", self.journal_entry)
                je.cancel()
            frappe.msgprint(
                _("Journal Entry <b>{0}</b> cancelled.").format(self.journal_entry),
                indicator="orange",
                alert=True,
            )

    # ------------------------------------------------------------------
    # ACCOUNT HELPERS
    # ------------------------------------------------------------------

    def _get_interest_income_account(self, company):
        acc = frappe.db.get_value(
            "Account",
            {"company": company, "account_name": ["like", "%Interest Income%"], "is_group": 0},
            "name"
        )
        if not acc:
            acc = frappe.db.get_value(
                "Account",
                {"company": company, "root_type": "Income", "is_group": 0},
                "name"
            )
        if not acc:
            frappe.throw(_(
                "Could not find an Interest Income account for company <b>{0}</b>. "
                "Please set one up."
            ).format(company))
        return acc

    def _get_vat_account(self, company):
        acc = frappe.db.get_value(
            "Account",
            {"company": company, "account_name": ["like", "%VAT%"], "account_type": "Tax", "is_group": 0},
            "name"
        )
        if not acc:
            acc = frappe.db.get_value(
                "Account",
                {"company": company, "account_type": "Tax", "is_group": 0},
                "name"
            )
        if not acc:
            frappe.throw(_(
                "Could not find a VAT/Tax account for company <b>{0}</b>."
            ).format(company))
        return acc

    def _get_wht_account(self, company):
        acc = frappe.db.get_value(
            "Account",
            {
                "company": company,
                "account_name": ["like", "%Withholding%"],
                "is_group": 0
            },
            "name"
        )
        if not acc:
            acc = frappe.db.get_value(
                "Account",
                {"company": company, "account_type": "Tax", "is_group": 0},
                "name"
            )
        if not acc:
            frappe.throw(_(
                "Could not find a Withholding Tax account for company <b>{0}</b>."
            ).format(company))
        return acc


# ------------------------------------------------------------------
# WHITELISTED API METHODS
# ------------------------------------------------------------------

@frappe.whitelist()
def get_amortization_schedule(principal, annual_rate, periods, period_type="Monthly", start_date=None):
    """
    Generate a straight-line amortization schedule for display in the print format.
    Returns JSON list of period rows.
    """
    principal = flt(principal)
    annual_rate = flt(annual_rate)
    periods = cint(periods)
    start_date = getdate(start_date or nowdate())

    if periods <= 0 or principal <= 0:
        return []

    # Period rate
    period_map = {
        "Monthly": (12, 1),
        "Quarterly": (4, 3),
        "Semi-Annual": (2, 6),
        "Annual": (1, 12),
    }
    periods_per_year, months_per_period = period_map.get(period_type, (12, 1))
    period_rate = annual_rate / 100 / periods_per_year

    # Equal instalment (PMT formula)
    if period_rate == 0:
        instalment = principal / periods
    else:
        instalment = principal * period_rate / (1 - (1 + period_rate) ** -periods)
    instalment = rounded(instalment, 2)

    schedule = []
    balance = principal
    cumulative_principal = 0
    cumulative_interest = 0

    for i in range(1, periods + 1):
        interest_component = rounded(balance * period_rate, 2)
        principal_component = rounded(instalment - interest_component, 2)

        # Adjust last row for rounding
        if i == periods:
            principal_component = rounded(balance, 2)
            instalment = rounded(principal_component + interest_component, 2)

        balance = rounded(balance - principal_component, 2)
        cumulative_principal += principal_component
        cumulative_interest += interest_component

        # Period date
        period_end = frappe.utils.add_months(start_date, i * months_per_period)

        schedule.append({
            "period": i,
            "period_end": str(period_end),
            "opening_balance": rounded(balance + principal_component, 2),
            "instalment": instalment,
            "principal_component": principal_component,
            "interest_component": interest_component,
            "closing_balance": max(balance, 0),
            "cumulative_principal": rounded(cumulative_principal, 2),
            "cumulative_interest": rounded(cumulative_interest, 2),
        })

    return schedule


@frappe.whitelist()
def get_interest_accrual_schedule(principal, annual_rate, from_date, to_date, basis="Actual/365"):
    """
    Monthly interest accrual breakdown between two dates.
    """
    principal = flt(principal)
    annual_rate = flt(annual_rate)
    from_date = getdate(from_date)
    to_date = getdate(to_date)

    if principal <= 0 or annual_rate == 0:
        return []

    rows = []
    current = from_date

    while current < to_date:
        # Month end
        month_end = get_last_day(current)
        period_end = min(month_end, to_date)
        days = date_diff(period_end, current) + 1
        divisor = 365 if "365" in basis else 360
        interest = rounded(principal * (annual_rate / 100) * (days / divisor), 2)

        rows.append({
            "period_start": str(current),
            "period_end": str(period_end),
            "days": days,
            "principal": principal,
            "rate": annual_rate,
            "interest": interest,
        })

        current = add_days(period_end, 1)

    return rows


@frappe.whitelist()
def get_tax_summary(docname):
    """
    Returns consolidated tax summary for print format.
    """
    doc = frappe.get_doc("Intercompany Invoice", docname)
    lines = []

    # Per-line taxes
    for row in doc.items:
        if flt(row.tax_amount):
            lines.append({
                "description": f"Tax on {row.item_name} @ {row.tax_rate}%",
                "taxable_amount": row.amount,
                "rate": row.tax_rate,
                "tax_amount": row.tax_amount,
                "type": "Item Tax",
            })

    # VAT
    if flt(doc.vat_amount):
        lines.append({
            "description": f"Value Added Tax (VAT) @ {doc.vat_rate}%",
            "taxable_amount": doc.total_base_amount,
            "rate": doc.vat_rate,
            "tax_amount": doc.vat_amount,
            "type": "VAT",
        })

    # WHT
    if flt(doc.withholding_tax_amount):
        lines.append({
            "description": f"Withholding Tax (WHT) @ {doc.withholding_tax_rate}%",
            "taxable_amount": doc.total_base_amount,
            "rate": doc.withholding_tax_rate,
            "tax_amount": -flt(doc.withholding_tax_amount),  # negative — reduces settlement
            "type": "WHT",
        })

    return {
        "lines": lines,
        "total_tax": sum(l["tax_amount"] for l in lines),
    }