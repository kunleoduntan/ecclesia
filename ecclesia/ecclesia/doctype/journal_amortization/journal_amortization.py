# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, add_months, cint, flt, getdate

MONTHS_PER_PERIOD = {"Monthly": 1, "Quarterly": 3, "Half Yearly": 6, "Yearly": 12}
LOCKED_FIELDS = ("journal_entry", "frequency", "no_of_periods", "start_date")


class JournalAmortization(Document):
	# ------------------------------------------------------------------ validate
	def validate(self):
		self.sync_row_entries()
		self.pull_journal_details()
		self.validate_terms()
		self.calculate_terms()

		if self.has_entries():
			self.validate_locked()
		else:
			self.build_schedule()

		self.update_totals()

	def sync_row_entries(self):
		"""Unlink rows whose Journal Entry was cancelled or no longer exists."""
		for r in self.get("amortization_schedule") or []:
			if r.journal_entry:
				ds = frappe.db.get_value("Journal Entry", r.journal_entry, "docstatus")
				if ds is None or ds == 2:
					r.journal_entry = None

	def pull_journal_details(self):
		je = frappe.db.get_value(
			"Journal Entry",
			self.journal_entry,
			["docstatus", "total_debit", "company", "posting_date", "pay_to_recd_from"],
			as_dict=True,
		)
		if not je or je.docstatus == 2:
			frappe.throw(_("Journal Entry {0} is cancelled or does not exist.").format(self.journal_entry))

		self.company = je.company
		self.journal_date = je.posting_date
		self.total_amount = flt(je.total_debit)
		if not self.beneficiary:
			self.beneficiary = je.pay_to_recd_from
		if not self.start_date:
			self.start_date = je.posting_date

	def validate_terms(self):
		if flt(self.total_amount) <= 0:
			frappe.throw(_("Total Debit of the Journal Entry must be greater than zero."))
		if cint(self.no_of_periods) <= 0:
			frappe.throw(_("No. of Periods must be greater than zero."))
		if self.frequency not in MONTHS_PER_PERIOD:
			frappe.throw(_("Invalid Frequency."))

	def calculate_terms(self):
		step = MONTHS_PER_PERIOD[self.frequency]
		n = cint(self.no_of_periods)
		self.period_charge = flt(flt(self.total_amount) / n, self.precision("period_charge"))
		self.end_date = add_days(add_months(getdate(self.start_date), step * n), -1)

	def has_entries(self):
		return any(r.journal_entry for r in self.get("amortization_schedule") or [])

	def validate_locked(self):
		if self.is_new():
			return
		for f in LOCKED_FIELDS:
			if self.has_value_changed(f):
				frappe.throw(
					_("Cannot change {0} while amortisation Journal Entries exist. Use Reset Entries first.").format(
						self.meta.get_label(f)
					)
				)

	def build_schedule(self):
		step = MONTHS_PER_PERIOD[self.frequency]
		n = cint(self.no_of_periods)
		start = getdate(self.start_date)
		total = flt(self.total_amount)
		prec = self.precision("period_charge")

		self.set("amortization_schedule", [])
		accumulated = 0.0
		for i in range(n):
			amount = flt(self.period_charge, prec) if i < n - 1 else flt(total - accumulated, prec)
			accumulated = flt(accumulated + amount, prec)
			self.append(
				"amortization_schedule",
				{
					"period_no": i + 1,
					"from_date": add_months(start, step * i),
					"to_date": add_days(add_months(start, step * (i + 1)), -1),
					"amount": amount,
					"accumulated_amount": accumulated,
					"balance_amount": flt(total - accumulated, prec),
				},
			)

	def update_totals(self):
		rows = self.get("amortization_schedule") or []
		done = [r for r in rows if r.journal_entry]
		self.amortized_amount = flt(sum(flt(r.amount) for r in done), self.precision("amortized_amount"))
		self.balance_amount = flt(flt(self.total_amount) - self.amortized_amount, self.precision("balance_amount"))
		if not done:
			self.status = "Pending"
		elif len(done) == len(rows):
			self.status = "Created"
		else:
			self.status = "Partially Created"

	def on_trash(self):
		if self.has_entries():
			frappe.throw(_("Cannot delete: amortisation Journal Entries exist. Use Reset Entries first."))

	# ------------------------------------------------------------------ actions
	@frappe.whitelist()
	def create_entries(self):
		"""Create a draft Journal Entry for every period without one. Nothing is submitted or scheduled."""
		self.check_permission("write")
		if not (self.prepaid_account and self.expense_account):
			frappe.throw(_("Set the Prepaid and Expense accounts under Posting Accounts first."))

		created = []
		for row in self.amortization_schedule:
			if row.journal_entry:
				continue
			je = self.make_journal_entry(row)
			row.db_set("journal_entry", je)
			row.journal_entry = je
			created.append(je)

		self.update_totals()
		self.db_set(
			{
				"amortized_amount": self.amortized_amount,
				"balance_amount": self.balance_amount,
				"status": self.status,
			}
		)
		return created

	@frappe.whitelist()
	def reset_entries(self):
		"""Delete draft amortisation Journal Entries and unlink them. Submitted ones must be cancelled first."""
		self.check_permission("write")
		to_delete = []
		for row in self.amortization_schedule:
			if not row.journal_entry:
				continue
			ds = frappe.db.get_value("Journal Entry", row.journal_entry, "docstatus")
			if ds == 1:
				frappe.throw(_("Journal Entry {0} is submitted. Cancel it first.").format(row.journal_entry))
			if ds == 0:
				to_delete.append(row.journal_entry)

		for row in self.amortization_schedule:
			if row.journal_entry:
				row.db_set("journal_entry", None)
				row.journal_entry = None

		for name in to_delete:
			frappe.delete_doc("Journal Entry", name)

		self.update_totals()
		self.db_set(
			{
				"amortized_amount": self.amortized_amount,
				"balance_amount": self.balance_amount,
				"status": self.status,
			}
		)
		return to_delete

	def make_journal_entry(self, row):
		remark = _("Amortisation {0}/{1} of {2} ({3})").format(
			row.period_no, self.no_of_periods, self.journal_entry, self.name
		)
		if self.purpose:
			remark = f"{self.purpose} - {remark}"

		je = frappe.new_doc("Journal Entry")
		je.voucher_type = "Journal Entry"
		je.company = self.company
		je.posting_date = row.to_date
		je.paid_to_or_received_from = self.beneficiary
		je.cheque_no = self.name
		je.cheque_date = row.to_date
		je.user_remark = remark
		je.append(
			"accounts",
			{
				"account": self.expense_account,
				"debit_in_account_currency": flt(row.amount),
				"cost_center": self.cost_center,
			},
		)
		je.append(
			"accounts",
			{"account": self.prepaid_account, "credit_in_account_currency": flt(row.amount)},
		)
		je.insert()
		return je.name