frappe.ui.form.on("Journal Entry", {

    validate(frm) {
        const val = frm.doc.paid_to_or_received_from;

        if (val) {
            if (!frm.doc.title) {
                frm.set_value("title", val);
            }
           
        }
    }

});