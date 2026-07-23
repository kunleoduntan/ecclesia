// Copyright (c) 2026, Value Plus and contributors
// For license information, please see license.txt

const PENSIONABLE_COMPONENTS = ["Basic Salary", "Housing", "Transport"];

function recalculate_ctc(frm) {
	if (!(frm.doc.ctc_components || []).length) return;

	let total = 0;
	let pensionable = 0;

	frm.doc.ctc_components.forEach((row) => {
		row.is_pensionable = PENSIONABLE_COMPONENTS.includes(row.component) ? 1 : 0;
		row.amount = flt(
			(flt(frm.doc.annual_gross_pay) * flt(row.percentage)) / 100,
			precision("amount", row)
		);
		total += row.amount;
		if (row.is_pensionable) pensionable += row.amount;
	});

	frm.set_value("total_components", flt(total, precision("total_components")));
	frm.set_value("pensionable_emoluments", flt(pensionable, precision("pensionable_emoluments")));

	const pension_ee = flt(
		(pensionable * flt(frm.doc.pension_ee_percent || 8)) / 100,
		precision("pension_ee_amount")
	);
	const pension_er = flt(
		(pensionable * flt(frm.doc.pension_er_percent || 10)) / 100,
		precision("pension_er_amount")
	);

	frm.set_value("pension_ee_amount", pension_ee);
	frm.set_value("pension_er_amount", pension_er);
	// NOTE: assumes the existing CTC field is named "ctc" — rename if yours differs.
	frm.set_value("ctc", flt(flt(frm.doc.annual_gross_pay) + pension_er, precision("ctc")));

	frm.refresh_fields();
}

frappe.ui.form.on("Employee", {
	annual_gross_pay: recalculate_ctc,
	pension_ee_percent: recalculate_ctc,
	pension_er_percent: recalculate_ctc,
	ctc_components_add: (frm) => recalculate_ctc(frm),
	ctc_components_remove: (frm) => recalculate_ctc(frm),
	refresh: recalculate_ctc,
});

frappe.ui.form.on("CTC Component", {
	percentage: (frm) => recalculate_ctc(frm),
	component: (frm) => recalculate_ctc(frm),
});
