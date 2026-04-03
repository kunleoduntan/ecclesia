// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

frappe.ui.form.on("Peer Review Request", {

    refresh(frm) {
        const colors = {
            "Pending":"orange","In Progress":"blue","Completed":"green","Declined":"red"
        };
        frm.page.set_indicator(frm.doc.status || "Pending", colors[frm.doc.status] || "gray");
        _add_peer_buttons(frm);
        _render_completeness(frm);
    },
});


function _add_peer_buttons(frm) {
    if (frm.doc.status !== "Pending" && frm.doc.status !== "In Progress") return;

    frm.add_custom_button("Mark Complete", () => {
        const responses = frm.doc.responses || [];
        const incomplete = responses.filter(r => !r.rating);
        if (!responses.length) {
            frappe.msgprint("Add at least one competency rating before marking complete.");
            return;
        }
        if (incomplete.length) {
            frappe.msgprint(`${incomplete.length} competency row(s) have no rating.`);
            return;
        }
        frappe.confirm("Submit this peer review? It cannot be edited after submission.", () => {
            frappe.db.set_value("Peer Review Request", frm.doc.name, {
                "status": "Completed",
                "submitted_on": frappe.datetime.now_datetime()
            }).then(() => frm.reload_doc());
        });
    }).addClass("btn-primary");

    frm.add_custom_button("Decline", () => {
        frappe.confirm("Decline this review request?", () => {
            frappe.db.set_value("Peer Review Request", frm.doc.name, "status", "Declined")
                .then(() => frm.reload_doc());
        });
    });
}


function _render_completeness(frm) {
    const rows     = frm.doc.responses || [];
    const rated    = rows.filter(r => r.rating).length;
    if (!rows.length) return;
    const pct      = Math.round((rated / rows.length) * 100);
    frm.dashboard.add_indicator(
        `${rated}/${rows.length} competencies rated (${pct}%)`,
        pct === 100 ? "green" : pct > 0 ? "orange" : "gray"
    );
}