# Copyright (c) 2025, Value Impacts Consulting
# Ecclesia Investment Management – Python Controller
# Handles: Money Market | Shares | Bonds | T-Bills | Fixed Deposits
# Interest Modes: Upfront | At Maturity | Periodic | Combinations
# WHT: Per period, upfront, maturity, dividend

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import (
    flt, add_months, add_days, getdate, nowdate, date_diff, get_datetime, cint
)
import json


class EcclesiaInvestment(Document):

    # =========================================================================
    # LIFECYCLE EVENTS
    # =========================================================================

    def validate(self):
        self._validate_required_fields()
        self._validate_dates()
        self._validate_amounts()
        self._validate_accounts()
        self._calculate_interest()
        self._calculate_management_fee()
        self._calculate_wht()
        self._calculate_shares_metrics()
        self._calculate_ai_metrics()
        self._set_duration_category()

    def on_submit(self):
        try:
            self._validate_before_submit()

            if self.book_investment:
                self._book_principal_entry()

            # Route by interest payment mode
            mode = self.interest_payment_mode or ''

            if mode == 'Upfront':
                self._book_upfront_interest_entry()
                if self.amortise_upfront_interest:
                    self._create_upfront_amortisation_entries()

            elif mode == 'At Maturity':
                if self.recognise_income:
                    self._book_accrual_at_maturity()

            elif mode == 'Periodic':
                if self.recognise_income and self.amortise_income:
                    self._create_periodic_income_entries()

            elif mode == 'Upfront and At Maturity':
                self._book_upfront_interest_entry()
                if self.amortise_upfront_interest:
                    self._create_upfront_amortisation_entries()
                if self.recognise_income:
                    self._book_accrual_at_maturity(is_split=True)

            elif mode == 'Periodic and At Maturity':
                if self.recognise_income and self.amortise_income:
                    self._create_periodic_income_entries()
                # Maturity portion booked separately via recognition

            frappe.db.commit()

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), _("Ecclesia Investment Submit Error"))
            frappe.throw(_("Error processing investment: {0}").format(str(e)))

    def on_cancel(self):
        """Cancel all linked journal entries in sequence."""
        try:
            journal_entries = frappe.get_all(
                "Journal Entry",
                filters={
                    "reference_document_no": self.name,
                    "reference_doctype": "Ecclesia Investment",
                    "docstatus": 1,
                },
                pluck="name",
                order_by="posting_date asc",
            )

            if not journal_entries:
                frappe.msgprint(_("No journal entries found for this investment."), indicator='blue')
                return

            cancelled, failed = 0, []
            for je_name in journal_entries:
                try:
                    je = frappe.get_doc("Journal Entry", je_name)
                    je.flags.ignore_permissions = True
                    je.cancel()
                    cancelled += 1
                    frappe.db.commit()
                except Exception as e:
                    failed.append(f"{je_name}: {str(e)}")
                    frappe.log_error(
                        f"Cancel error – {je_name}: {e}\n{frappe.get_traceback()}",
                        _("Ecclesia Investment Cancel Error")
                    )

            msg = _("Cancelled {0} journal entries.").format(cancelled)
            if failed:
                msg += _("<br><b>{0} failed:</b><br>").format(len(failed)) + "<br>".join(failed[:5])
                frappe.msgprint(msg, indicator='orange', title=_("Partial Cancellation"))
            else:
                frappe.msgprint(msg, indicator='green', title=_("Cancellation Complete"))

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), _("Ecclesia Investment Cancel Error"))
            frappe.throw(_("Error cancelling investment: {0}").format(str(e)))

    # =========================================================================
    # VALIDATION HELPERS
    # =========================================================================

    def _validate_required_fields(self):
        required = [
            ("investment_name", "Investment Name"),
            ("investment_type", "Investment Type"),
            ("counterparty_name", "Counterparty / Issuer Name"),
            ("company", "Company"),
            ("posting_date", "Posting Date"),
            ("start_date", "Start Date"),
            ("tenure_in_days", "Tenure In Days"),
            ("investment_amount", "Investment Amount"),
        ]
        for field, label in required:
            if not self.get(field):
                frappe.throw(_("Please set <b>{0}</b>").format(label))

    def _validate_dates(self):
        if self.start_date and self.end_date:
            if getdate(self.end_date) <= getdate(self.start_date):
                frappe.throw(_("Maturity Date must be after Start Date."))
        if self.posting_date and self.start_date:
            if getdate(self.start_date) < getdate(self.posting_date):
                frappe.throw(_("Start Date cannot be before Posting Date."))

    def _validate_amounts(self):
        if flt(self.investment_amount) <= 0:
            frappe.throw(_("Investment Amount must be greater than zero."))
        if cint(self.tenure_in_days) <= 0:
            frappe.throw(_("Tenure in Days must be greater than zero."))
        if self.investment_type != 'Shares' and flt(self.interest_rate) < 0:
            frappe.throw(_("Interest Rate cannot be negative."))
        if flt(self.management_fee) > 100:
            frappe.throw(_("Management Fee cannot exceed 100%."))

    def _validate_accounts(self):
        accounts = []
        if self.principal_account:
            accounts.append((self.principal_account, "Investment Account"))
        if self.interest_income_account:
            accounts.append((self.interest_income_account, "Interest Income Account"))
        if self.wht_payable_account:
            accounts.append((self.wht_payable_account, "WHT Payable Account"))
        if self.management_fee_expense_account:
            accounts.append((self.management_fee_expense_account, "Management Fee Expense Account"))
        if self.upfront_interest_deferred_account:
            accounts.append((self.upfront_interest_deferred_account, "Deferred Interest Income Account"))
        if self.accrued_interest_account:
            accounts.append((self.accrued_interest_account, "Accrued Interest Account"))

        for acct, label in accounts:
            is_group = frappe.db.get_value("Account", acct, "is_group")
            if is_group:
                frappe.throw(
                    _("Account <b>{0}</b> ({1}) is a group account. Please select a ledger account.").format(
                        acct, label
                    )
                )

    def _validate_before_submit(self):
        # Prevent duplicate bookings
        existing = frappe.db.exists("Journal Entry", {
            "reference_document_no": self.name,
            "reference_doctype": "Ecclesia Investment",
            "docstatus": ["!=", 2],
        })
        if existing:
            frappe.throw(
                _("Investment already booked. Journal Entry <b>{0}</b> exists.").format(existing),
                title=_("Duplicate Booking")
            )

        if self.book_investment:
            for f, label in [("principal_account", "Investment Account"),
                              ("bank_account", "Bank Account"),
                              ("posting_date", "Posting Date")]:
                if not self.get(f):
                    frappe.throw(_("Please specify <b>{0}</b> to book investment.").format(label))

        if self.recognise_income and self.amortise_income:
            for f, label in [("interest_income_account", "Interest Income Account"),
                              ("cost_center", "Cost Center"),
                              ("department", "Department")]:
                if not self.get(f):
                    frappe.throw(_("Please specify <b>{0}</b> for income recognition.").format(label))
            
            # The schedule must be built from the client (JS) before submit.
            # Python never auto-generates it — it only posts JEs for rows already present.
            if not self.schedule_of_interest:
                frappe.throw(
                    _("Income schedule is empty. Please click <b>Build Schedule</b> on the form "
                      "before submitting to generate the amortisation table."),
                    title=_("Schedule Required")
                )

    # =========================================================================
    # CALCULATION HELPERS (called from validate)
    # =========================================================================

    def _calculate_interest(self):
        p = flt(self.investment_amount)
        days = cint(self.tenure_in_days)
        r = flt(self.interest_rate) / 100

        if not p or not days or not r:
            return

        t = days / 365.0
        method = self.interest_type or 'Simple Interest'

        if method == 'Simple Interest':
            gross = p * r * t
        elif method == 'Compound Interest':
            gross = p * ((1 + r) ** t - 1)
        elif method == 'Discount (T-Bills)':
            gross = p * r * t / (1 + r * t)
        else:  # Flat Rate
            gross = p * r * t

        # Allow manual override
        effective_gross = flt(self.total_gross_interest) if flt(self.total_gross_interest) > 0 else flt(gross)
        self.returns = round(effective_gross, 4)

        mode = self.interest_payment_mode or ''
        periods = self._get_periods()

        if mode == 'Upfront':
            self.upfront_interest_amount = self.returns
            self.maturity_interest_amount = 0
            self.monthly_interest_income = 0

        elif mode == 'At Maturity':
            self.upfront_interest_amount = 0
            self.maturity_interest_amount = self.returns
            self.monthly_interest_income = 0

        elif mode == 'Periodic':
            self.upfront_interest_amount = 0
            self.maturity_interest_amount = 0
            self.monthly_interest_income = round(self.returns / periods, 4) if periods > 0 else 0

        elif mode == 'Upfront and At Maturity':
            # 50/50 split — adjust if cert specifies otherwise
            half = round(self.returns / 2, 4)
            self.upfront_interest_amount = half
            self.maturity_interest_amount = round(self.returns - half, 4)
            self.monthly_interest_income = 0

        elif mode == 'Periodic and At Maturity':
            periodic_total = round(self.returns * 0.7, 4)
            self.maturity_interest_amount = round(self.returns * 0.3, 4)
            self.upfront_interest_amount = 0
            self.monthly_interest_income = round(periodic_total / periods, 4) if periods > 0 else 0

        self.amount_realisable_on_liquidation = flt(p) + flt(self.returns)
        self.investment_amount_base = flt(p) * flt(self.exchange_rate or 1)

    def _calculate_management_fee(self):
        if flt(self.management_fee) > 0 and flt(self.returns) > 0:
            self.management_fee_amount = round(flt(self.returns) * flt(self.management_fee) / 100, 4)
        else:
            self.management_fee_amount = 0

    def _calculate_wht(self):
        """
        WHT in Nigeria is statutory:
            - 10% for companies (CITA S.78)
            - 5%  for individuals (PITA)
        The same rate applies to ALL income types: periodic, upfront, maturity, dividend.
        One wht_rate field drives everything.
        """
        zero_all = (not self.wht_applicable or not self.wht_rate)
        if zero_all:
            self.wht_amount_periodic  = 0
            self.wht_amount_upfront   = 0
            self.wht_amount_maturity  = 0
            self.wht_amount_dividend  = 0
            self.total_wht_amount     = 0
            self.net_income_after_wht = flt(self.returns)
            return

        rate = 0.05 if '5%' in (self.wht_rate or '') else 0.10

        # Per-component WHT (shown on form per payment mode for transparency)
        self.wht_amount_periodic = (
            round(flt(self.monthly_interest_income) * rate, 4)
            if flt(self.monthly_interest_income) > 0 else 0
        )
        self.wht_amount_upfront = (
            round(flt(self.upfront_interest_amount) * rate, 4)
            if flt(self.upfront_interest_amount) > 0 else 0
        )
        self.wht_amount_maturity = (
            round(flt(self.maturity_interest_amount) * rate, 4)
            if flt(self.maturity_interest_amount) > 0 else 0
        )
        self.wht_amount_dividend = (
            round(flt(self.expected_dividend_income) * rate, 4)
            if flt(self.expected_dividend_income) > 0 else 0
        )

        # Aggregate WHT on total returns — for WHT certificate / remittance reporting
        self.total_wht_amount = round(flt(self.returns) * rate, 4) if flt(self.returns) > 0 else 0
        self.net_income_after_wht = round(flt(self.returns) - self.total_wht_amount, 4)

    def _calculate_shares_metrics(self):
        if self.investment_type != 'Shares':
            return
        units = flt(self.number_of_units)
        cost  = flt(self.unit_price)
        mkt   = flt(self.market_price_per_unit)
        div_r = flt(self.dividend_rate) / 100

        if units and cost:
            self.total_share_cost = round(units * cost, 4)
        if units and mkt:
            self.market_value = round(units * mkt, 4)
            self.unrealised_gain_loss = round(self.market_value - (units * cost), 4)
        if units and cost and div_r:
            self.expected_dividend_income = round(units * cost * div_r, 4)

    def _calculate_ai_metrics(self):
        p = flt(self.investment_amount)
        r = flt(self.returns)
        if not p or not r:
            return

        roi = (r / p) * 100
        score = 50

        if flt(self.interest_rate) > 15: score += 20
        elif flt(self.interest_rate) > 10: score += 10
        elif flt(self.interest_rate) < 5: score -= 10

        if cint(self.tenure_in_days) > 1825: score += 15
        elif cint(self.tenure_in_days) < 90: score += 5

        if self.market_asset_class == 'Unquoted': score += 15
        if self.investment_type == 'Shares':      score += 10
        if flt(self.liquidity_ratio) < 50:        score += 10
        if self.rate_of_inflation and flt(self.interest_rate) - flt(self.rate_of_inflation) < 2:
            score += 10

        self.ai_risk_score = min(max(score, 0), 100)

        ann = roi * (365 / cint(self.tenure_in_days)) if cint(self.tenure_in_days) > 0 else roi
        if ann > 15 and score < 60:
            self.ai_recommendation = "⭐ EXCELLENT – High returns with acceptable risk"
        elif ann > 10 and score < 70:
            self.ai_recommendation = "✅ GOOD – Solid performance, moderate risk"
        elif score > 80:
            self.ai_recommendation = "🔴 HIGH RISK – Monitor closely or consider exit"
        elif ann < 5:
            self.ai_recommendation = "⚠️ REVIEW – Returns are below target"
        else:
            self.ai_recommendation = "📊 FAIR – Within market expectations"

    def _set_duration_category(self):
        days = cint(self.tenure_in_days)
        years = days / 365
        if years <= 1:      self.investment_duration_category = 'Short-Term (Up to 1 year)'
        elif years <= 3:    self.investment_duration_category = 'Short-Term (1-3 years)'
        elif years <= 5:    self.investment_duration_category = 'Medium-Term (3-5 years)'
        else:               self.investment_duration_category = 'Long-Term (5+ years)'

    # =========================================================================
    # JOURNAL ENTRY BUILDERS
    # =========================================================================

    def _get_company(self):
        company = self.company or frappe.db.get_value("Bank Account", self.bank_account, "company")
        if not company:
            frappe.throw(_("Cannot determine Company. Please set the Company field."))
        return company

    def _base_je(self, voucher_type="Journal Entry", naming="ECC-INV-JV-.#####"):
        return frappe.get_doc({
            "doctype": "Journal Entry",
            "voucher_type": voucher_type,
            "naming_series": naming,
            "paid_to_or_received_from": self.counterparty_name,
            "custom_party_name": self.counterparty_name,
            "posting_date": self.posting_date,
            "company": self._get_company(),
            "user_remark": f"Investment: {self.investment_name} – {self.counterparty_name}",
            "reference_document_no": self.name,
            "reference_doctype": "Ecclesia Investment",
        })

    def _submit_je(self, je):
        je.flags.ignore_permissions = True
        je.insert()
        je.submit()
        return je.name

    def _msg_je(self, label, je_name):
        frappe.msgprint(
            _("{0}: <a href='/app/journal-entry/{1}' target='_blank'><b>{1}</b></a>").format(label, je_name),
            indicator='green',
            title=_("Journal Entry Created")
        )

    # ── PRINCIPAL BOOKING ──────────────────────────────────────────────────

    def _book_principal_entry(self):
        """Dr Investment Account / Cr Bank Account"""
        je = self._base_je(voucher_type="Bank Entry")
        je.cheque_no = self.cheque_no
        je.cheque_date = self.posting_date
        je.user_remark = f"Principal investment – {self.investment_name} ({self.counterparty_name})"

        je.append("accounts", {
            "account": self.principal_account,
            "debit_in_account_currency": self.investment_amount,
            "user_remark": f"Investment principal: {self.investment_name}",
            "cost_center": self.cost_center,
            "department": self.department,
        })
        je.append("accounts", {
            "account": self.bank_gl,
            "credit_in_account_currency": self.investment_amount,
            "user_remark": f"Payment for investment: {self.investment_name}",
        })

        name = self._submit_je(je)
        self._msg_je("Investment booked", name)
        return name

    # ── UPFRONT INTEREST ──────────────────────────────────────────────────

    def _book_upfront_interest_entry(self):
        """
        When interest is received upfront:
            Dr Bank Account
            Cr Deferred Interest Income (if amortised) OR Cr Interest Income (if recognised immediately)
        
        WHT portion (if applicable):
            Dr Bank (net only)
            Dr WHT Payable
            Cr Deferred/Income
        """
        if not flt(self.upfront_interest_amount):
            return

        gross = flt(self.upfront_interest_amount)
        wht   = flt(self.wht_amount_upfront) if self.wht_applicable else 0
        net   = gross - wht

        income_acct = (self.upfront_interest_deferred_account
                       if self.amortise_upfront_interest and self.upfront_interest_deferred_account
                       else self.interest_income_account)

        if not income_acct:
            frappe.throw(_("Please set Interest Income Account (or Deferred Interest Account) for upfront interest booking."))

        je = self._base_je()
        je.user_remark = f"Upfront interest received – {self.investment_name}"

        # Dr Bank (net received)
        je.append("accounts", {
            "account": self.bank_gl,
            "debit_in_account_currency": net,
            "user_remark": f"Net upfront interest received",
        })

        # Dr WHT Payable (amount withheld by issuer)
        if wht > 0 and self.wht_payable_account:
            je.append("accounts", {
                "account": self.wht_payable_account,
                "debit_in_account_currency": wht,
                "user_remark": f"WHT withheld on upfront interest ({self.wht_rate_upfront})",
            })

        # Cr Deferred/Income Account (gross)
        je.append("accounts", {
            "account": income_acct,
            "credit_in_account_currency": gross,
            "user_remark": f"Upfront interest {'deferred' if self.amortise_upfront_interest else 'recognised'}: {self.investment_name}",
            "cost_center": self.cost_center,
            "department": self.department,
        })

        name = self._submit_je(je)
        self._msg_je("Upfront interest booked", name)
        return name

    # ── UPFRONT INTEREST AMORTISATION SCHEDULE ───────────────────────────

    def _create_upfront_amortisation_entries(self):
        """
        Each month: Dr Deferred Interest Income / Cr Interest Income
        Straight-line or EIR (Straight-line implemented here)
        """
        if not self.upfront_interest_deferred_account or not self.interest_income_account:
            frappe.throw(_("Please set both Deferred Interest Account and Interest Income Account for amortisation."))

        months = int(cint(self.tenure_in_days) / 30)
        if months <= 0:
            return

        amount_per_period = round(flt(self.upfront_interest_amount) / months, 4)
        created = 0

        for i in range(1, months + 1):
            period_date = add_months(getdate(self.start_date), i)
            if period_date > getdate(self.end_date):
                break

            je = frappe.get_doc({
                "doctype": "Journal Entry",
                "voucher_type": "Journal Entry",
                "naming_series": "ECC-INV-AMR-.#####",
                "posting_date": period_date,
                "company": self._get_company(),
                "user_remark": f"Upfront interest amortisation – Period {i}/{months} – {self.investment_name}",
                "reference_document_no": self.name,
                "reference_doctype": "Ecclesia Investment",
                "accounts": [
                    {
                        "account": self.upfront_interest_deferred_account,
                        "debit_in_account_currency": amount_per_period,
                        "user_remark": f"Amortise deferred interest – Period {i}/{months}",
                        "cost_center": self.cost_center,
                        "department": self.department,
                    },
                    {
                        "account": self.interest_income_account,
                        "credit_in_account_currency": amount_per_period,
                        "user_remark": f"Interest income recognised – Period {i}/{months}",
                        "cost_center": self.cost_center,
                        "department": self.department,
                    },
                ],
            })
            je.flags.ignore_permissions = True
            je.insert()
            je.submit()

            # Update schedule row if present
            for row in self.schedule_of_interest:
                if row.period == i and row.is_deferred_amortisation:
                    frappe.db.set_value("Ecclesia Interest Schedule", row.name, {
                        "journal_entry": je.name,
                        "status": "Posted",
                    })

            created += 1

        frappe.msgprint(
            _("{0} upfront interest amortisation entries created for <b>{1}</b>").format(created, self.investment_name),
            indicator='green',
            title=_("Amortisation Complete")
        )

    # ── MATURITY INTEREST ACCRUAL ─────────────────────────────────────────

    def _book_accrual_at_maturity(self, is_split=False):
        """
        At maturity:
            Dr Accrued Interest Receivable
            Cr Interest Income
        
        WHT:
            Dr Accrued Interest Receivable
            Dr WHT Payable
            Cr Interest Income (gross)
        """
        gross = flt(self.maturity_interest_amount)
        if not gross:
            return

        wht = flt(self.wht_amount_maturity) if self.wht_applicable else 0

        acct = self.accrued_interest_account or self.principal_account
        income_acct = self.interest_income_account

        if not income_acct:
            frappe.throw(_("Please set Interest Income Account for maturity interest recognition."))

        je = frappe.get_doc({
            "doctype": "Journal Entry",
            "voucher_type": "Journal Entry",
            "naming_series": "ECC-INV-MAT-.#####",
            "posting_date": self.end_date or self.posting_date,
            "company": self._get_company(),
            "user_remark": f"Maturity interest accrual – {self.investment_name} ({'split' if is_split else 'full'})",
            "reference_document_no": self.name,
            "reference_doctype": "Ecclesia Investment",
        })

        # Dr Accrued Interest (net)
        je.append("accounts", {
            "account": acct,
            "debit_in_account_currency": gross - wht,
            "user_remark": f"Net maturity interest receivable",
            "cost_center": self.cost_center,
            "department": self.department,
        })

        # Dr WHT Payable
        if wht > 0 and self.wht_payable_account:
            je.append("accounts", {
                "account": self.wht_payable_account,
                "debit_in_account_currency": wht,
                "user_remark": f"WHT on maturity interest ({self.wht_rate_maturity})",
            })

        # Cr Interest Income (gross)
        je.append("accounts", {
            "account": income_acct,
            "credit_in_account_currency": gross,
            "user_remark": f"Maturity interest income: {self.investment_name}",
            "cost_center": self.cost_center,
            "department": self.department,
        })

        je.flags.ignore_permissions = True
        je.insert()
        je.submit()

        self._msg_je("Maturity interest accrued", je.name)
        return je.name

    # ── PERIODIC INCOME SCHEDULE ──────────────────────────────────────────

    def _create_periodic_income_entries(self):
        """
        For each period in schedule_of_interest:
            Dr Accrued Interest Receivable (gross)
            [Dr WHT Payable (wht)]
            [Dr Management Fee Expense (fee)]
            Cr Interest Income (total credit = gross + fee)  ← net of WHT flows to P&L
        
        Accounting model used here:
            Dr Accrued Interest     gross
            Cr Interest Income      gross - wht
            Cr WHT Payable          wht
        """
        if not self.schedule_of_interest:
            frappe.throw(_("No interest schedule found. Please build the schedule before submitting."))

        if not self.interest_income_account:
            frappe.throw(_("Please set Interest Income Account."))

        acct = self.accrued_interest_account or self.principal_account
        company = self._get_company()
        periods = len(self.schedule_of_interest)
        created, failed = 0, []

        for row in self.schedule_of_interest:
            try:
                period_date = getdate(row.date)
                if period_date > getdate(self.end_date):
                    break

                gross = flt(row.interest_amount)
                wht   = flt(row.wht_amount) if row.wht_amount else 0
                fee   = flt(row.management_fee_amount) if row.management_fee_amount else 0
                net_income = gross - wht

                je = frappe.get_doc({
                    "doctype": "Journal Entry",
                    "voucher_type": "Journal Entry",
                    "naming_series": "ECC-INV-PER-.#####",
                    "posting_date": period_date,
                    "company": company,
                    "user_remark": (
                        f"Periodic interest – {row.period_label or f'Period {row.period}'} – {self.investment_name}"
                    ),
                    "reference_document_no": self.name,
                    "reference_doctype": "Ecclesia Investment",
                })

                # Dr Accrued Interest (gross receivable)
                je.append("accounts", {
                    "account": acct,
                    "debit_in_account_currency": gross,
                    "user_remark": f"Accrued interest – Period {row.period}/{periods}",
                    "cost_center": self.cost_center,
                    "department": self.department,
                })

                # Dr Management Fee Expense
                if fee > 0 and self.management_fee_expense_account:
                    je.append("accounts", {
                        "account": self.management_fee_expense_account,
                        "debit_in_account_currency": fee,
                        "user_remark": f"Management fee – Period {row.period}/{periods}",
                        "cost_center": self.cost_center,
                        "department": self.department,
                    })

                # Cr Interest Income (net of WHT)
                je.append("accounts", {
                    "account": self.interest_income_account,
                    "credit_in_account_currency": net_income + fee,
                    "user_remark": f"Interest income recognised – Period {row.period}/{periods}",
                    "cost_center": self.cost_center,
                    "department": self.department,
                })

                # Cr WHT Payable
                if wht > 0 and self.wht_payable_account:
                    je.append("accounts", {
                        "account": self.wht_payable_account,
                        "credit_in_account_currency": wht,
                        "user_remark": f"WHT payable – Period {row.period}/{periods} ({row.wht_type})",
                    })

                je.flags.ignore_permissions = True
                je.insert()
                je.submit()

                # Update schedule status
                frappe.db.set_value("Ecclesia Interest Schedule", row.name, {
                    "journal_entry": je.name,
                    "status": "Posted",
                })

                created += 1

            except Exception as e:
                failed.append(f"Period {row.period}: {str(e)}")
                frappe.log_error(
                    f"Period {row.period} JE error\nInvestment: {self.name}\n{str(e)}\n{frappe.get_traceback()}",
                    _("Ecclesia Income Recognition Error")
                )

        msg = _("{0} periodic income entries created.").format(created)
        if failed:
            msg += _("<br><b>{0} failed:</b><br>").format(len(failed)) + "<br>".join(failed[:5])
            frappe.msgprint(msg, indicator='orange', title=_("Partial Success"))
        else:
            frappe.msgprint(msg, indicator='green', title=_("Income Recognition Complete"))

    # =========================================================================
    # UTILITY
    # =========================================================================

    def _get_periods(self):
        freq_days = {
            'Monthly': 30, 'Quarterly': 90, 'Half-yearly': 180, 'Yearly': 365
        }
        days_per = freq_days.get(self.frequency_of_income_recognition, 30)
        return int(cint(self.tenure_in_days) / days_per) if days_per else 0


# =============================================================================
# WHITELISTED API ENDPOINTS
# =============================================================================

@frappe.whitelist()
def generate_investment_analysis(investment_name):
    """Return AI-computed analytics for dialog display."""
    try:
        doc = frappe.get_doc("Ecclesia Investment", investment_name)

        p   = flt(doc.investment_amount)
        ret = flt(doc.returns)
        roi = (ret / p * 100) if p else 0
        ann = roi * (365 / cint(doc.tenure_in_days)) if cint(doc.tenure_in_days) > 0 else roi

        risk_score = int(flt(doc.ai_risk_score) or 0)

        # Market average
        mkt_avg = _market_average(doc.market_asset_class, doc.investment_type)
        comparison = "Above Market" if ann > mkt_avg else "Below Market"

        recommendation = _recommendation(ann, risk_score, mkt_avg)
        insights = _insights(doc, roi, ann, risk_score)

        return {
            "success": True,
            "roi": round(roi, 2),
            "annualized_return": round(ann, 2),
            "risk_score": risk_score,
            "liquidity_rating": f"{doc.liquidity_ratio}%" if doc.liquidity_ratio else "N/A",
            "market_comparison": comparison,
            "market_average": round(mkt_avg, 2),
            "recommendation": recommendation,
            "insights": insights,
            "total_return_amount": flt(doc.amount_realisable_on_liquidation),
            "days_to_maturity": date_diff(doc.end_date, nowdate()) if doc.end_date else 0,
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Ecclesia Investment Analysis Error"))
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_investment_summary(investment_name):
    """Return performance summary including linked JEs."""
    doc = frappe.get_doc("Ecclesia Investment", investment_name)

    journal_entries = frappe.get_all(
        "Journal Entry",
        filters={"reference_document_no": doc.name, "docstatus": 1},
        fields=["name", "posting_date", "total_debit", "voucher_type"],
        order_by="posting_date asc",
    )

    total_wht = (
        flt(doc.wht_amount_periodic) +
        flt(doc.wht_amount_upfront) +
        flt(doc.wht_amount_maturity) +
        flt(doc.wht_amount_dividend)
    )

    return {
        "investment_name": doc.investment_name,
        "investment_type": doc.investment_type,
        "investment_amount": doc.investment_amount,
        "returns": doc.returns,
        "amount_realisable": doc.amount_realisable_on_liquidation,
        "roi_percentage": (flt(doc.returns) / flt(doc.investment_amount) * 100) if doc.investment_amount else 0,
        "total_wht": total_wht,
        "management_fee_amount": doc.management_fee_amount,
        "interest_payment_mode": doc.interest_payment_mode,
        "start_date": doc.start_date,
        "end_date": doc.end_date,
        "tenure_in_days": doc.tenure_in_days,
        "status": doc.status,
        "schedule_count": len(doc.schedule_of_interest or []),
        "journal_entries": journal_entries,
        "ai_risk_score": doc.ai_risk_score,
        "ai_recommendation": doc.ai_recommendation,
    }


@frappe.whitelist()
def book_maturity_proceeds(investment_name):
    """
    Called manually at maturity to record:
        Dr Bank Account (principal + net interest)
        Cr Investment Account (principal)
        Cr Accrued Interest Receivable (net interest)
    
    Also records WHT settlement if applicable.
    """
    doc = frappe.get_doc("Ecclesia Investment", investment_name)

    if doc.docstatus != 1:
        frappe.throw(_("Investment must be submitted to book maturity proceeds."))

    company = doc.company or frappe.db.get_value("Bank Account", doc.bank_account, "company")
    net_interest = flt(doc.net_maturity_income) or flt(doc.maturity_interest_amount)
    wht = flt(doc.wht_amount_maturity) if doc.wht_applicable else 0
    total_cash = flt(doc.investment_amount) + net_interest

    je = frappe.get_doc({
        "doctype": "Journal Entry",
        "voucher_type": "Bank Entry",
        "naming_series": "ECC-INV-MAT-.#####",
        "posting_date": doc.end_date or nowdate(),
        "company": company,
        "user_remark": f"Maturity proceeds – {doc.investment_name}",
        "reference_document_no": doc.name,
        "reference_doctype": "Ecclesia Investment",
    })

    # Dr Bank (total cash received)
    je.append("accounts", {
        "account": doc.bank_gl,
        "debit_in_account_currency": total_cash,
        "user_remark": "Maturity proceeds received",
    })

    # Dr WHT Payable (settles the liability)
    if wht > 0 and doc.wht_payable_account:
        je.append("accounts", {
            "account": doc.wht_payable_account,
            "debit_in_account_currency": wht,
            "user_remark": f"WHT settlement on maturity ({doc.wht_rate_maturity})",
        })

    # Cr Investment Account (principal return)
    je.append("accounts", {
        "account": doc.principal_account,
        "credit_in_account_currency": flt(doc.investment_amount),
        "user_remark": "Return of principal",
        "cost_center": doc.cost_center,
        "department": doc.department,
    })

    # Cr Accrued Interest (if previously accrued)
    if net_interest > 0:
        acct = doc.accrued_interest_account or doc.principal_account
        je.append("accounts", {
            "account": acct,
            "credit_in_account_currency": net_interest,
            "user_remark": "Settlement of accrued maturity interest",
            "cost_center": doc.cost_center,
            "department": doc.department,
        })

    je.flags.ignore_permissions = True
    je.insert()
    je.submit()

    # Update investment status
    frappe.db.set_value("Ecclesia Investment", investment_name, "status", "Matured")

    frappe.msgprint(
        _("Maturity proceeds booked: <a href='/app/journal-entry/{0}' target='_blank'><b>{0}</b></a>").format(je.name),
        indicator='green',
        title=_("Maturity Booking Complete")
    )
    return {"success": True, "journal_entry": je.name}


@frappe.whitelist()
def book_dividend(investment_name, dividend_date, gross_dividend, wht_rate=None, dividend_type="Final"):
    """
    Record a dividend receipt:
        Dr Bank (net)
        Dr WHT Payable (if applicable)
        Cr Dividend Income (gross)
    """
    doc = frappe.get_doc("Ecclesia Investment", investment_name)

    if doc.investment_type != 'Shares':
        frappe.throw(_("Dividend booking is only applicable for Shares investments."))

    gross = flt(gross_dividend)
    # Use the document's statutory WHT rate — same rate applies to dividends
    _rate_str = doc.wht_rate or wht_rate or ''
    wht_r = 0.05 if '5%' in _rate_str else (0.10 if '10%' in _rate_str else 0)
    wht   = round(gross * wht_r, 4) if doc.wht_applicable else 0
    net   = gross - wht

    company = doc.company

    je = frappe.get_doc({
        "doctype": "Journal Entry",
        "voucher_type": "Bank Entry",
        "naming_series": "ECC-INV-DIV-.#####",
        "posting_date": dividend_date,
        "company": company,
        "user_remark": f"{dividend_type} dividend – {doc.investment_name} ({doc.counterparty_name})",
        "reference_document_no": doc.name,
        "reference_doctype": "Ecclesia Investment",
    })

    # Dr Bank (net received)
    je.append("accounts", {
        "account": doc.bank_gl,
        "debit_in_account_currency": net,
        "user_remark": "Net dividend received",
    })

    # Dr WHT Payable
    if wht > 0 and doc.wht_payable_account:
        je.append("accounts", {
            "account": doc.wht_payable_account,
            "debit_in_account_currency": wht,
            "user_remark": f"WHT on dividend ({wht_rate})",
        })

    # Cr Dividend Income
    if not doc.dividend_income_account:
        frappe.throw(_("Please set Dividend Income Account."))
    je.append("accounts", {
        "account": doc.dividend_income_account,
        "credit_in_account_currency": gross,
        "user_remark": f"{dividend_type} dividend income: {doc.investment_name}",
        "cost_center": doc.cost_center,
        "department": doc.department,
    })

    je.flags.ignore_permissions = True
    je.insert()
    je.submit()

    frappe.msgprint(
        _("Dividend booked: <a href='/app/journal-entry/{0}' target='_blank'><b>{0}</b></a>").format(je.name),
        indicator='green',
        title=_("Dividend Booking Complete")
    )
    return {"success": True, "journal_entry": je.name, "net_dividend": net}


@frappe.whitelist()
def book_bonus_shares(investment_name, bonus_date, bonus_units, notes=None):
    """
    Record a bonus share issue (scrip dividend / capitalisation issue).
    No cash changes hands — the company issues new shares from reserves.

    Accounting:
        Dr  Investment in Shares (at nominal/zero cost)  [memo entry — cost basis unchanged]
        Cr  Capital Reserve / Bonus Shares Received      [nominal account]

    In practice many firms record bonus at zero cost (IFRS 9) or at nominal value.
    We create the journal entry as a memo (equal Dr/Cr on the investment account) so
    the ledger reflects the event, and we update the unit count on the document.
    """
    doc = frappe.get_doc("Ecclesia Investment", investment_name)
    if doc.investment_type != 'Shares':
        frappe.throw(_("Bonus share booking is only applicable for Shares investments."))

    bonus_units = flt(bonus_units)
    if bonus_units <= 0:
        frappe.throw(_("Bonus units must be greater than zero."))

    company = doc.company

    # ── Journal Entry ────────────────────────────────────────────────────────
    # We record the bonus at zero cost (IFRS 9 / cost model common practice).
    # A memo JE is still created for audit trail completeness.
    # If your policy requires nominal value, adjust debit_in_account_currency below.
    je = frappe.get_doc({
        "doctype": "Journal Entry",
        "voucher_type": "Journal Entry",
        "naming_series": "ECC-INV-BNS-.#####",
        "posting_date": bonus_date,
        "company": company,
        "user_remark": (
            f"Bonus share issue – {bonus_units:,.4f} units – {doc.investment_name} ({doc.counterparty_name})"
        ),
        "reference_document_no": doc.name,
        "reference_doctype": "Ecclesia Investment",
    })

    # Dr Investment Account (memo — zero or nominal amount; both sides equal)
    je.append("accounts", {
        "account": doc.principal_account,
        "debit_in_account_currency": 0,
        "credit_in_account_currency": 0,
        "user_remark": (
            f"Bonus: {bonus_units:,.4f} additional units received at zero cost "
            f"(new total: {flt(doc.number_of_units) + bonus_units:,.4f} units)"
        ),
        "cost_center": doc.cost_center,
        "department": doc.department,
    })

    # For a proper double-entry memo we add a matching line
    je.append("accounts", {
        "account": doc.principal_account,
        "debit_in_account_currency": 0,
        "credit_in_account_currency": 0,
        "user_remark": "Bonus issue contra – zero cost basis",
        "cost_center": doc.cost_center,
    })

    je.flags.ignore_permissions = True
    je.insert()
    je.submit()

    # ── Update document ──────────────────────────────────────────────────────
    new_units = flt(doc.number_of_units) + bonus_units

    # Log in shares activity
    doc.append("shares_activity_log", {
        "activity_date": bonus_date,
        "activity_type": "Bonus Issue",
        "units_affected": bonus_units,
        "price_per_unit": 0,
        "total_value": 0,
        "description": notes or f"Bonus issue of {bonus_units:,.4f} units. New holding: {new_units:,.4f} units.",
        "journal_entry": je.name,
    })

    doc.number_of_units = new_units

    # Recalculate derived share fields
    if flt(doc.unit_price):
        doc.total_share_cost = round(new_units * flt(doc.unit_price), 4)
    if flt(doc.market_price_per_unit):
        doc.market_value = round(new_units * flt(doc.market_price_per_unit), 4)
        doc.unrealised_gain_loss = round(doc.market_value - flt(doc.total_share_cost), 4)

    doc.flags.ignore_permissions = True
    doc.save()

    frappe.msgprint(
        _(
            "Bonus shares recorded: <a href='/app/journal-entry/{0}' target='_blank'><b>{0}</b></a>"
            " | New holding: <b>{1:,.4f} units</b>"
        ).format(je.name, new_units),
        indicator='green',
        title=_("Bonus Issue Complete"),
    )
    return {"success": True, "journal_entry": je.name, "new_total_units": new_units}


@frappe.whitelist()
def book_rights_issue(
    investment_name, rights_date, units_subscribed,
    subscription_price_per_unit, notes=None
):
    """
    Record a rights issue subscription.
    Investor pays cash to subscribe for new shares at a preferential price.

    Accounting:
        Dr  Investment in Shares  (units × subscription price)
        Cr  Bank Account          (cash paid out)

    The cost basis of the investment increases by the subscription amount.
    """
    doc = frappe.get_doc("Ecclesia Investment", investment_name)
    if doc.investment_type != 'Shares':
        frappe.throw(_("Rights issue booking is only applicable for Shares investments."))

    units     = flt(units_subscribed)
    sub_price = flt(subscription_price_per_unit)

    if units <= 0:
        frappe.throw(_("Units subscribed must be greater than zero."))
    if sub_price <= 0:
        frappe.throw(_("Subscription price must be greater than zero."))
    if not doc.bank_gl:
        frappe.throw(_("Please set Bank Account on the investment before booking a rights issue."))

    total_cost = round(units * sub_price, 4)
    company    = doc.company

    # ── Journal Entry ────────────────────────────────────────────────────────
    je = frappe.get_doc({
        "doctype": "Journal Entry",
        "voucher_type": "Bank Entry",
        "naming_series": "ECC-INV-RTS-.#####",
        "posting_date": rights_date,
        "company": company,
        "user_remark": (
            f"Rights issue subscription – {units:,.4f} units @ ₦{sub_price:,.4f} – "
            f"{doc.investment_name} ({doc.counterparty_name})"
        ),
        "reference_document_no": doc.name,
        "reference_doctype": "Ecclesia Investment",
    })

    # Dr Investment Account (additional cost of shares subscribed)
    je.append("accounts", {
        "account": doc.principal_account,
        "debit_in_account_currency": total_cost,
        "user_remark": (
            f"Rights issue: {units:,.4f} units @ ₦{sub_price:,.4f} = ₦{total_cost:,.4f}"
        ),
        "cost_center": doc.cost_center,
        "department": doc.department,
    })

    # Cr Bank Account (cash paid)
    je.append("accounts", {
        "account": doc.bank_gl,
        "credit_in_account_currency": total_cost,
        "user_remark": f"Cash paid for rights issue subscription",
    })

    je.flags.ignore_permissions = True
    je.insert()
    je.submit()

    # ── Update document ──────────────────────────────────────────────────────
    old_units      = flt(doc.number_of_units)
    old_cost       = flt(doc.total_share_cost) or (old_units * flt(doc.unit_price))
    new_units      = old_units + units
    new_total_cost = old_cost + total_cost

    # Weighted average cost per unit
    new_avg_cost = round(new_total_cost / new_units, 4) if new_units else flt(doc.unit_price)

    # Log in shares activity
    doc.append("shares_activity_log", {
        "activity_date": rights_date,
        "activity_type": "Rights Issue",
        "units_affected": units,
        "price_per_unit": sub_price,
        "total_value": total_cost,
        "description": (
            notes or (
                f"Rights issue subscription: {units:,.4f} units @ ₦{sub_price:,.4f}. "
                f"New holding: {new_units:,.4f} units. "
                f"New avg cost: ₦{new_avg_cost:,.4f}/unit."
            )
        ),
        "journal_entry": je.name,
    })

    doc.number_of_units = new_units
    doc.unit_price       = new_avg_cost   # Weighted average cost basis
    doc.total_share_cost = new_total_cost
    doc.investment_amount = new_total_cost  # Update principal to reflect full cost

    if flt(doc.market_price_per_unit):
        doc.market_value = round(new_units * flt(doc.market_price_per_unit), 4)
        doc.unrealised_gain_loss = round(doc.market_value - new_total_cost, 4)

    doc.flags.ignore_permissions = True
    doc.save()

    frappe.msgprint(
        _(
            "Rights issue booked: <a href='/app/journal-entry/{0}' target='_blank'><b>{0}</b></a>"
            " | New holding: <b>{1:,.4f} units</b> | Avg cost: <b>₦{2:,.4f}</b>"
        ).format(je.name, new_units, new_avg_cost),
        indicator='green',
        title=_("Rights Issue Complete"),
    )
    return {
        "success": True,
        "journal_entry": je.name,
        "new_total_units": new_units,
        "new_avg_cost_per_unit": new_avg_cost,
        "new_total_cost": new_total_cost,
    }


@frappe.whitelist()
def book_disposal(investment_name, disposal_date, units_disposed, disposal_price_per_unit, notes=None):
    """
    Record full or partial disposal of shares:
        Gain: Dr Bank / Cr Investment Account / Cr Capital Gain
        Loss: Dr Bank / Dr Capital Loss / Cr Investment Account
    """
    doc = frappe.get_doc("Ecclesia Investment", investment_name)

    if doc.investment_type != 'Shares':
        frappe.throw(_("Disposal booking is only applicable for Shares investments."))

    units = flt(units_disposed)
    price = flt(disposal_price_per_unit)
    cost_per = flt(doc.unit_price)
    proceeds = units * price
    cost_basis = units * cost_per
    gain_loss  = proceeds - cost_basis

    company = doc.company
    is_gain  = gain_loss >= 0

    je = frappe.get_doc({
        "doctype": "Journal Entry",
        "voucher_type": "Bank Entry",
        "naming_series": "ECC-INV-DSP-.#####",
        "posting_date": disposal_date,
        "company": company,
        "user_remark": f"Share disposal – {units} units @ {price} – {doc.investment_name}",
        "reference_document_no": doc.name,
        "reference_doctype": "Ecclesia Investment",
    })

    # Dr Bank
    je.append("accounts", {
        "account": doc.bank_gl,
        "debit_in_account_currency": proceeds,
        "user_remark": "Proceeds from share disposal",
    })

    if is_gain:
        # Cr Investment Account (cost basis)
        je.append("accounts", {
            "account": doc.principal_account,
            "credit_in_account_currency": cost_basis,
            "user_remark": f"Cost basis of {units} units disposed",
        })
        # Cr Capital Gain
        if gain_loss > 0:
            je.append("accounts", {
                "account": doc.capital_gain_account or doc.interest_income_account,
                "credit_in_account_currency": gain_loss,
                "user_remark": f"Capital gain on disposal",
                "cost_center": doc.cost_center,
                "department": doc.department,
            })
    else:
        # Cr Investment Account (full proceeds)
        je.append("accounts", {
            "account": doc.principal_account,
            "credit_in_account_currency": proceeds,
            "user_remark": f"Investment account – disposal",
        })
        # Dr Capital Loss
        je.append("accounts", {
            "account": doc.capital_gain_account or doc.interest_income_account,
            "debit_in_account_currency": abs(gain_loss),
            "user_remark": f"Capital loss on disposal",
            "cost_center": doc.cost_center,
        })

    je.flags.ignore_permissions = True
    je.insert()
    je.submit()

    # Log in shares activity
    doc.append("shares_activity_log", {
        "activity_date": disposal_date,
        "activity_type": "Full Disposal" if units >= flt(doc.number_of_units) else "Partial Disposal",
        "units_affected": units,
        "price_per_unit": price,
        "total_value": proceeds,
        "description": notes or f"Disposal of {units} units. Gain/Loss: {gain_loss:,.2f}",
        "journal_entry": je.name,
    })
    doc.flags.ignore_permissions = True
    doc.save()

    frappe.msgprint(
        _("Disposal booked: <a href='/app/journal-entry/{0}' target='_blank'><b>{0}</b></a> | Gain/(Loss): <b>{1:,.2f}</b>").format(
            je.name, gain_loss
        ),
        indicator='green' if is_gain else 'orange',
        title=_("Disposal Complete")
    )
    return {"success": True, "journal_entry": je.name, "gain_loss": gain_loss}


# =============================================================================
# PRIVATE HELPERS
# =============================================================================

def _market_average(market_class=None, inv_type=None):
    defaults = {
        'Equity': 12.0, 'Shares': 12.0,
        'Money Market': 9.0, 'Fixed Income': 9.0,
        'Treasury Bills': 7.5, 'Bonds': 10.0,
        'Commercial Paper': 11.0, 'Fixed Deposit': 8.5,
    }
    return defaults.get(inv_type, defaults.get(market_class, 10.0))


def _recommendation(ann, risk_score, mkt_avg):
    if ann > mkt_avg * 1.2 and risk_score < 60:
        return "⭐ HOLD – Excellent performance with acceptable risk"
    elif ann > mkt_avg and risk_score < 70:
        return "✅ HOLD – Good performance within risk tolerance"
    elif ann < mkt_avg * 0.7 and risk_score > 70:
        return "🚨 CONSIDER EXIT – Underperforming with elevated risk"
    elif risk_score > 80:
        return "🔴 HIGH RISK – Monitor closely or consider exit strategy"
    elif ann < mkt_avg * 0.8:
        return "⚡ REVIEW – Performance below market expectations"
    else:
        return "📊 MAINTAIN – Performance within normal parameters"


def _insights(doc, roi, ann, risk_score):
    parts = []

    if ann > 15:
        parts.append("🎯 <b>Exceptional returns</b> – significantly outperforming market averages.")
    elif ann < 5:
        parts.append("📉 <b>Low returns</b> – consider reviewing the investment strategy.")

    if risk_score > 75:
        parts.append("⚠️ <b>High risk profile</b> detected. Diversification is recommended.")
    elif risk_score < 30:
        parts.append("🛡️ <b>Low risk investment</b> – suitable for conservative portfolios.")

    mode = doc.interest_payment_mode or ''
    if mode == 'Upfront':
        parts.append("💰 <b>Upfront interest model</b> – cash received early improves liquidity.")
    elif mode == 'At Maturity':
        parts.append("🏁 <b>Bullet interest model</b> – income only at maturity; monitor cash flow.")
    elif 'Periodic' in mode:
        parts.append("📅 <b>Periodic recognition</b> – regular income stream enhances cash flow predictability.")

    total_wht = (flt(doc.wht_amount_periodic) + flt(doc.wht_amount_upfront) +
                 flt(doc.wht_amount_maturity) + flt(doc.wht_amount_dividend))
    if total_wht > 0:
        eff_wht = (total_wht / flt(doc.returns) * 100) if doc.returns else 0
        parts.append(f"💰 <b>WHT Impact</b> – {eff_wht:.1f}% of gross returns withheld (₦{total_wht:,.2f}). Ensure WHT certificates are obtained.")

    if doc.rate_of_inflation and flt(doc.interest_rate):
        real = flt(doc.interest_rate) - flt(doc.rate_of_inflation)
        if real < 2:
            parts.append("📊 <b>Inflation risk</b> – real return below 2%. Investment may be value-destructive in real terms.")
        elif real > 5:
            parts.append("💪 <b>Strong real returns</b> – well ahead of inflation.")

    if doc.investment_type == 'Shares' and flt(doc.unrealised_gain_loss) != 0:
        gl = flt(doc.unrealised_gain_loss)
        colour = "green" if gl > 0 else "red"
        parts.append(f"📈 <b>Mark-to-market:</b> <span style='color:{colour};'>₦{gl:,.2f}</span> unrealised {'gain' if gl > 0 else 'loss'}.")

    return "<br>".join(parts) if parts else "Investment performing as expected within normal parameters."