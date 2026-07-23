// Work Activity Log — Client JS
// Ecclesia Module
// This DocType is read-only (auto-generated). JS enhances display only.

frappe.ui.form.on("Work Activity Log", {

    refresh(frm) {
        // Fully read-only — disable all editing
        frm.disable_save();
        frm.set_read_only();

        frm.trigger("_render_score_breakdown");
        frm.trigger("_setup_links");
        frm.trigger("_set_indicator");
    },

    // ── Score breakdown card ──────────────────────────────────────────────

    _render_score_breakdown(frm) {
        if (!frm.doc.raw_score) return;

        const raw    = flt(frm.doc.raw_score);
        const damped = flt(frm.doc.dampened_points);
        const final  = flt(frm.doc.points);
        const isDamp = frm.doc.is_dampened;

        const html = `
            <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:14px 16px;margin:8px 0;">
                <div style="font-size:12px;font-weight:600;color:#166534;margin-bottom:10px;">
                    🧮 Score Calculation Breakdown
                </div>
                <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;font-size:13px;">
                    <div style="text-align:center;">
                        <div style="font-size:20px;font-weight:700;color:#374151;">${raw}</div>
                        <div style="font-size:11px;color:#6b7280;">Raw Score</div>
                    </div>
                    <div style="color:#9ca3af;font-size:18px;">→</div>
                    <div style="text-align:center;${isDamp ? 'opacity:0.6;' : ''}">
                        <div style="font-size:20px;font-weight:700;color:${isDamp ? '#d97706' : '#374151'};">
                            ${damped} ${isDamp ? '⚡' : ''}
                        </div>
                        <div style="font-size:11px;color:#6b7280;">After Dampening${isDamp ? ' (repeated action)' : ''}</div>
                    </div>
                    <div style="color:#9ca3af;font-size:18px;">→</div>
                    <div style="text-align:center;">
                        <div style="font-size:24px;font-weight:700;color:#16a34a;">${final}</div>
                        <div style="font-size:11px;color:#6b7280;">Final Points</div>
                    </div>
                    ${frm.doc.business_value ? `
                    <div style="margin-left:auto;text-align:right;">
                        <div style="font-size:13px;font-weight:600;color:#374151;">
                            ${frappe.format(frm.doc.business_value, { fieldtype: 'Currency' })}
                        </div>
                        <div style="font-size:11px;color:#6b7280;">Business Value</div>
                    </div>` : ''}
                </div>
            </div>`;

        // Inject after points field
        const $pts = frm.get_field("points");
        if ($pts) {
            $pts.$wrapper.closest(".form-column").find(".wfh-score-breakdown").remove();
            $pts.$wrapper.after(`<div class="wfh-score-breakdown">${html}</div>`);
        }
    },

    // ── Navigation shortcuts ──────────────────────────────────────────────

    _setup_links(frm) {
        if (frm.doc.session) {
            frm.add_custom_button(__("View Session"), () => {
                frappe.set_route("Form", "WFH Session", frm.doc.session);
            });
        }
        if (frm.doc.reference_doctype && frm.doc.reference_name) {
            frm.add_custom_button(__("View Source Document"), () => {
                frappe.set_route("Form", frm.doc.reference_doctype, frm.doc.reference_name);
            });
        }
        frm.add_custom_button(__("Employee's Logs Today"), () => {
            frappe.route_options = {
                employee: frm.doc.employee,
                date:     frm.doc.date
            };
            frappe.set_route("List", "Work Activity Log");
        });
    },

    _set_indicator(frm) {
        const pts = flt(frm.doc.points);
        const color = pts >= 20 ? "green" : pts >= 5 ? "blue" : "gray";
        frm.page.set_indicator(`${pts} pts`, color);
    }
});

// ── List View Enhancements ────────────────────────────────────────────────────

frappe.listview_settings["Work Activity Log"] = {
    get_indicator(doc) {
        const pts = parseFloat(doc.points || 0);
        if (doc.is_dampened) return [__("Dampened"), "orange", "is_dampened,=,1"];
        if (pts >= 20)       return [__(`${pts} pts`), "green",  "points,>=,20"];
        if (pts >= 5)        return [__(`${pts} pts`), "blue",   "points,>=,5"];
        return [__(`${pts} pts`), "gray", "points,<,5"];
    },

    formatters: {
        action(val) {
            const colors = {
                Submit: "#16a34a", Create: "#3b82f6",
                Update: "#6b7280", Cancel: "#dc2626", Amend: "#d97706"
            };
            const c = colors[val] || "#6b7280";
            return `<span style="color:${c};font-weight:500;">${val}</span>`;
        },
        module(val) {
            const bg = {
                Sales: "#3b82f6", Accounts: "#8b5cf6", CRM: "#ec4899",
                Buying: "#f59e0b", Stock: "#10b981"
            }[val] || "#6b7280";
            return val
                ? `<span style="background:${bg};color:white;padding:2px 7px;border-radius:4px;font-size:11px;">${val}</span>`
                : "—";
        },
        points(val) {
            const pts = parseFloat(val || 0);
            const c = pts >= 20 ? "#16a34a" : pts >= 5 ? "#3b82f6" : "#9ca3af";
            return `<b style="color:${c};">${pts}</b>`;
        }
    }
};

function flt(val) { return parseFloat(val) || 0; }
