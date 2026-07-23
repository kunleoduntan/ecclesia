// ecclesia/doctype/continuous_feedback/continuous_feedback.js
frappe.ui.form.on("Continuous Feedback", {

    refresh(frm) {
        const icons = {
            "Recognition 🌟":    "🌟",
            "Coaching 💡":       "💡",
            "Growth Area 📈":    "📈",
            "One-on-One Note 🤝":"🤝"
        };
        const icon = icons[frm.doc.feedback_type] || "💬";
        frm.set_intro(`${icon} ${frm.doc.feedback_type || "Feedback"}`, "blue");
    },

    feedback_type(frm) {
        const placeholders = {
            "Recognition 🌟":     "Describe what this person did exceptionally well and the impact it had...",
            "Coaching 💡":        "Share a specific observation and a constructive suggestion for improvement...",
            "Growth Area 📈":     "Describe an area you've noticed could help them grow, with a supportive tone...",
            "One-on-One Note 🤝": "Summarise the key points from your one-on-one conversation..."
        };
        frm.set_df_property("feedback", "description",
            placeholders[frm.doc.feedback_type] || "");
    },

    to_employee(frm) {
        if (frm.doc.to_employee === frappe.session.user) {
            frappe.msgprint(__("You cannot send feedback to yourself."));
            frm.set_value("to_employee", "");
        }
    }
});
