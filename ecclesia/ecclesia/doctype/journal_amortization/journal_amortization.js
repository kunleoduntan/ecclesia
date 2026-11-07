// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

const AMZ_STEP = { "Monthly": 1, "Quarterly": 3, "Half Yearly": 6, "Yearly": 12 };

frappe.ui.form.on("Journal Amortization", {
	setup(frm) {
		frm.set_query("journal_entry", () => ({ filters: { docstatus: ["<", 2] } }));
		frm.set_query("prepaid_account", () => ({
			filters: { company: frm.doc.company, is_group: 0, root_type: "Asset" },
		}));
		frm.set_query("expense_account", () => ({
			filters: { company: frm.doc.company, is_group: 0, root_type: "Expense" },
		}));
		frm.set_query("cost_center", () => ({
			filters: { company: frm.doc.company, is_group: 0 },
		}));
	},

	refresh(frm) {
		if (frm.is_new()) return;

		const total = flt(frm.doc.total_amount);
		const done = flt(frm.doc.amortized_amount);
		frm.dashboard.add_progress(
			__("Journalised"),
			total ? (done / total) * 100 : 0,
			`${format_currency(done)} / ${format_currency(total)}`
		);

		const rows = frm.doc.amortization_schedule || [];
		const pending = rows.some((r) => !r.journal_entry);
		const created = rows.some((r) => r.journal_entry);

		if (!frm.is_dirty()) {
			if (pending) {
				frm.add_custom_button(__("Create Journal Entries"), () => amz_create(frm)).addClass("btn-primary");
			}
			if (created) {
				frm.add_custom_button(__("Reset Entries"), () => amz_reset(frm), __("Actions"));
			}
		}
		frm.add_custom_button(__("Source Journal Entry"), () =>
			frappe.set_route("Form", "Journal Entry", frm.doc.journal_entry), __("View"));
	},

	journal_entry(frm) {
		if (!frm.doc.journal_entry) {
			frm.set_value({ total_amount: 0, company: "", journal_date: null, start_date: null, beneficiary: "" });
			return;
		}
		frappe.db
			.get_value("Journal Entry", frm.doc.journal_entry, ["total_debit", "posting_date", "company", "pay_to_recd_from"])
			.then(({ message }) => {
				frm.set_value({
					company: message.company,
					journal_date: message.posting_date,
					total_amount: message.total_debit,
					start_date: message.posting_date,
					beneficiary: message.pay_to_recd_from,
				});
				amz_recalc(frm);
			});
	},

	frequency: (frm) => amz_recalc(frm),
	no_of_periods: (frm) => amz_recalc(frm),
	start_date: (frm) => amz_recalc(frm),
});

function amz_create(frm) {
	if (!frm.doc.prepaid_account || !frm.doc.expense_account) {
		frappe.msgprint(__("Set the Prepaid and Expense accounts under Posting Accounts first."));
		return;
	}
	const n = (frm.doc.amortization_schedule || []).filter((r) => !r.journal_entry).length;
	frappe.confirm(__("Create {0} draft Journal Entries?", [n]), () => {
		frm.call({
			doc: frm.doc,
			method: "create_entries",
			freeze: true,
			freeze_message: __("Creating Journal Entries..."),
		}).then((r) => {
			frappe.show_alert({
				message: __("{0} Journal Entries created", [(r.message || []).length]),
				indicator: "green",
			});
			frm.reload_doc();
		});
	});
}

function amz_reset(frm) {
	frappe.confirm(__("Delete draft amortisation Journal Entries and unlink them?"), () => {
		frm.call({ doc: frm.doc, method: "reset_entries", freeze: true }).then(() => frm.reload_doc());
	});
}

// Live preview; server rebuilds the schedule authoritatively on save.
function amz_recalc(frm) {
	const d = frm.doc;
	const n = cint(d.no_of_periods);
	const total = flt(d.total_amount);
	const step = AMZ_STEP[d.frequency];
	if (!n || !total || !step || !d.start_date) return;
	if ((d.amortization_schedule || []).some((r) => r.journal_entry)) return;

	const charge = flt(total / n, 2);
	frm.set_value("period_charge", charge);
	frm.set_value(
		"end_date",
		frappe.datetime.add_days(frappe.datetime.add_months(d.start_date, step * n), -1)
	);

	frm.clear_table("amortization_schedule");
	let acc = 0;
	for (let i = 0; i < n; i++) {
		const amount = i < n - 1 ? charge : flt(total - acc, 2);
		acc = flt(acc + amount, 2);
		const row = frm.add_child("amortization_schedule");
		row.period_no = i + 1;
		row.from_date = frappe.datetime.add_months(d.start_date, step * i);
		row.to_date = frappe.datetime.add_days(frappe.datetime.add_months(d.start_date, step * (i + 1)), -1);
		row.amount = amount;
		row.accumulated_amount = acc;
		row.balance_amount = flt(total - acc, 2);
	}
	frm.refresh_field("amortization_schedule");
}