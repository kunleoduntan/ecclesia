(function () {
    const doctypes = ["Sales Invoice", "Sales Order", "Purchase Invoice", "Purchase Order"];

    doctypes.forEach(function (doctype) {
        frappe.ui.form.on(doctype, {
            setup: function (frm) {
                frm.set_query("item_code", "items", function () {
                    return {
                        query: "ecclesia.utils.item_filters.item_query",
                        filters: {
                            parenttype: frm.doctype,
                        },
                    };
                });
            },
        });
    });
})();