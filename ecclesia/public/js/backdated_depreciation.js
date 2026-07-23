frappe.ui.form.on("Asset", {
     refresh(frm) {
         if (frm.doc.docstatus === 1) {
             frm.add_custom_button(__("Book Backdated Depreciation"), function () {
                 frappe.call({
                     method: "ecclesia.api.backdated_depreciation.run_for_asset",
                     args: { asset_name: frm.doc.name },
                     freeze: true,
                     freeze_message: __("Creating journal entries..."),
                     callback(r) {
                         if (r.message) {
                             frappe.msgprint(r.message.message);
                             frm.reload_doc();
                         }
                     }
                 });
             }, __("Actions"));
         }
     }
 });