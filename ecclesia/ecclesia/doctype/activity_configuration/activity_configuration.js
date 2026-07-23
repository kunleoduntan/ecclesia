// Activity Configuration — Client JS
// Ecclesia Module

frappe.ui.form.on("Activity Configuration", {

    refresh(frm) {
        frm.trigger("_toggle_fields");
        frm.trigger("_setup_buttons");
        frm.trigger("_render_preview");
    },

    points_rule(frm)               { frm.trigger("_toggle_fields"); frm.trigger("_render_preview"); },
    value_multiplier_enabled(frm)  { frm.trigger("_toggle_fields"); frm.trigger("_render_preview"); },
    frequency_dampening_enabled(frm){ frm.trigger("_toggle_fields"); },
    base_points(frm)               { frm.trigger("_render_preview"); },
    value_divisor(frm)             { frm.trigger("_render_preview"); },
    max_value_bonus(frm)           { frm.trigger("_render_preview"); },
    daily_cap_points(frm)          { frm.trigger("_render_preview"); },
    dampening_multiplier(frm)      { frm.trigger("_render_preview"); },

    // ── Dynamic field visibility ──────────────────────────────────────────

    _toggle_fields(frm) {
        const rule     = frm.doc.points_rule;
        const hasValue = frm.doc.value_multiplier_enabled;
        const dampOn   = frm.doc.frequency_dampening_enabled;

        frm.toggle_display("value_field",             rule !== "Fixed");
        frm.toggle_display("value_multiplier_enabled",rule !== "Fixed");
        frm.toggle_display("value_divisor",           hasValue && rule !== "Fixed");
        frm.toggle_display("max_value_bonus",         hasValue && rule !== "Fixed");

        frm.toggle_display("dampening_window_minutes",dampOn);
        frm.toggle_display("dampening_multiplier",    dampOn);
    },

    // ── Scoring preview panel ─────────────────────────────────────────────

    _render_preview(frm) {
        const base   = parseFloat(frm.doc.base_points   || 0);
        const div    = parseFloat(frm.doc.value_divisor  || 1);
        const maxB   = parseFloat(frm.doc.max_value_bonus || 0);
        const damp   = parseFloat(frm.doc.dampening_multiplier || 1);
        const cap    = parseFloat(frm.doc.daily_cap_points || 0);
        const hasVal = frm.doc.value_multiplier_enabled;
        const rule   = frm.doc.points_rule;

        // Example values
        const ex_val = 500000;   // ₦500k transaction
        let raw = base;
        if (rule === "Formula" && hasVal && div) {
            raw = base + Math.min(ex_val / div, maxB);
        } else if (rule === "Percentage of Value") {
            raw = base + (ex_val * base / 100);
        }
        const dampened = raw * damp;

        const html = `
            <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;padding:14px 16px;margin:8px 0;">
                <div style="font-size:12px;font-weight:600;color:#374151;margin-bottom:10px;">
                    📊 Scoring Preview (example: ₦500k transaction)
                </div>
                <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;">
                    <div style="text-align:center;">
                        <div style="font-size:20px;font-weight:700;color:#4f46e5;">${raw.toFixed(1)}</div>
                        <div style="font-size:11px;color:#6b7280;">Raw Points</div>
                    </div>
                    <div style="text-align:center;">
                        <div style="font-size:20px;font-weight:700;color:#8b5cf6;">${dampened.toFixed(1)}</div>
                        <div style="font-size:11px;color:#6b7280;">After Dampening</div>
                    </div>
                    <div style="text-align:center;">
                        <div style="font-size:20px;font-weight:700;color:#10b981;">${cap}</div>
                        <div style="font-size:11px;color:#6b7280;">Daily Cap</div>
                    </div>
                    <div style="text-align:center;">
                        <div style="font-size:20px;font-weight:700;color:#f59e0b;">
                            ${cap ? Math.floor(cap / Math.max(dampened, 0.1)) : "∞"}
                        </div>
                        <div style="font-size:11px;color:#6b7280;">Actions to Cap</div>
                    </div>
                </div>
            </div>`;

        // Place preview below daily_cap_points field
        const $cap = frm.get_field("daily_cap_points").$wrapper;
        $cap.find(".wfh-scoring-preview").remove();
        $cap.after(`<div class="wfh-scoring-preview">${html}</div>`);
    },

    // ── Toolbar buttons ───────────────────────────────────────────────────

    _setup_buttons(frm) {
        if (frappe.user.has_role(["System Manager", "HR Manager"])) {
            if (frm.is_new()) {
                frm.add_custom_button(__("Seed Defaults"), () => {
                    frappe.confirm(
                        __("This will create default Activity Configurations for all standard ERPNext DocTypes. Continue?"),
                        () => {
                            frappe.call({
                                method: "ecclesia.api.engine.seed_default_configurations",
                                callback(r) {
                                    frappe.msgprint(r.message || __("Defaults seeded."));
                                    frm.reload_doc();
                                }
                            });
                        }
                    );
                }, __("Tools"));
            }

            frm.add_custom_button(__("Test Scorer"), () => {
                frappe.prompt([
                    { label: __("Employee"), fieldname: "employee", fieldtype: "Link", options: "Employee", reqd: 1 },
                    { label: __("Business Value"), fieldname: "value", fieldtype: "Currency", default: 500000 }
                ], (vals) => {
                    frappe.call({
                        method: "ecclesia.api.engine.preview_score",
                        args: {
                            config_name:    frm.doc.name,
                            employee:       vals.employee,
                            business_value: vals.value
                        },
                        callback(r) {
                            if (r.message) {
                                const m = r.message;
                                frappe.msgprint({
                                    title:   __("Score Preview"),
                                    message: `
                                        <table style="width:100%;border-collapse:collapse;">
                                            <tr><td style="padding:4px 8px;"><b>Raw Score</b></td><td>${m.raw_score}</td></tr>
                                            <tr><td style="padding:4px 8px;"><b>After Dampening</b></td><td>${m.dampened}</td></tr>
                                            <tr><td style="padding:4px 8px;"><b>After Daily Cap</b></td><td>${m.final}</td></tr>
                                            <tr><td style="padding:4px 8px;"><b>Is Dampened</b></td><td>${m.is_dampened ? "Yes" : "No"}</td></tr>
                                        </table>`,
                                    indicator: "blue"
                                });
                            }
                        }
                    });
                }, __("Test Score Calculation"));
            }, __("Tools"));

            // Toggle active
            frm.add_custom_button(
                frm.doc.is_active ? __("Deactivate") : __("Activate"),
                () => {
                    frm.set_value("is_active", !frm.doc.is_active);
                    frm.save().then(() => {
                        frappe.show_alert({
                            message: frm.doc.is_active ? __("Activated") : __("Deactivated"),
                            indicator: frm.doc.is_active ? "green" : "red"
                        }, 4);
                    });
                },
                __("Tools")
            );
        }
    }
});
