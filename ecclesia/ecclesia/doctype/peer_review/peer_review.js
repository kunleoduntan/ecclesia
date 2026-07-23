// ecclesia/doctype/peer_review/peer_review.js
frappe.ui.form.on("Peer Review", {

    refresh(frm) {
        if (frm.doc.is_anonymous) {
            frm.set_df_property("reviewer", "hidden", 1);
            frm.set_intro(__("This is an anonymous review. The reviewer identity will not be shared."), "blue");
        }
        frm.trigger("_calculate_average");
    },

    _calculate_average(frm) {
        const ratings = (frm.doc.competency_ratings || [])
            .map(r => r.rating)
            .filter(r => r > 0);
        if (!ratings.length) return;
        const avg = ratings.reduce((a, b) => a + b, 0) / ratings.length;
        if (!frm.doc.overall_peer_rating) {
            frm.set_value("overall_peer_rating", Math.round(avg * 10) / 10);
        }
    }
});

frappe.ui.form.on("Peer Review Competency", {
    rating(frm) { frm.trigger("_calculate_average"); }
});
