frappe.ui.form.on("Journal Entry", {

    validate(frm) {
        const val = frm.doc.paid_to_or_received_from;

        if (val) {
            if (!frm.doc.title) {
                frm.set_value("title", val);
            }
            if (!frm.doc.payee_name) {
                frm.set_value("payee_name", val);
            }
        }
    }

});