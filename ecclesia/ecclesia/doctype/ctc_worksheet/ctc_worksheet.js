// Copyright (c) 2026, Value Plus and contributors
// For license information, please see license.txt

const PENSIONABLE_COMPONENTS = ["Basic Salary", "Housing", "Transport"];

function recalculate(frm) {
	let total = 0;
	let pensionable = 0;

	(frm.doc.components || []).forEach((row) => {
		row.is_pensionable = PENSIONABLE_COMPONENTS.includes(row.component) ? 1 : 0;
		row.amount = flt(
			(flt(frm.doc.annual_gross_pay) * flt(row.percentage)) / 100,
			precision("amount", row)
		);
		total += row.amount;
		if (row.is_pensionable) {
			pensionable += row.amount;
		}
	});

	frm.set_value("total_components", flt(total, precision("total_components")));
	frm.set_value("pensionable_emoluments", flt(pensionable, precision("pensionable_emoluments")));

	const pension_ee = flt(
		(frm.doc.pensionable_emoluments * flt(frm.doc.pension_ee_percent)) / 100,
		precision("pension_ee_amount")
	);
	const pension_er = flt(
		(frm.doc.pensionable_emoluments * flt(frm.doc.pension_er_percent)) / 100,
		precision("pension_er_amount")
	);

	frm.set_value("pension_ee_amount", pension_ee);
	frm.set_value("pension_er_amount", pension_er);
	frm.set_value("pension_ee_check", 1);
	frm.set_value("ctc", flt(flt(frm.doc.annual_gross_pay) + pension_er, precision("ctc")));

	frm.refresh_fields();
}

frappe.ui.form.on("CTC Worksheet", {
	annual_gross_pay: recalculate,
	pension_ee_percent: recalculate,
	pension_er_percent: recalculate,
	refresh: recalculate,
});

frappe.ui.form.on("CTC Component", {
	percentage: (frm) => recalculate(frm),
	component: (frm) => recalculate(frm),
	components_remove: (frm) => recalculate(frm),
});
