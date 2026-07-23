// WFH Activity Mapping — Client Script (FIXED)
// All frappe.call method paths corrected to ecclesia.ecclesia.* prefix

frappe.ui.form.on("WFH Activity Mapping", {

    onload(frm) {
        frm.set_query("doctype_name", "mappings", () => ({
            filters: { istable: 0, issingle: 0 }
        }));
    },

    refresh(frm) {
        frm.trigger("_render_status_panel");
        frm.trigger("_setup_buttons");
        frm.trigger("_warn_inactive");
    },

    is_active(frm) {
        frm.trigger("_warn_inactive");
    },

    // ── Status panel ──────────────────────────────────────────────────────────
    _render_status_panel(frm) {
        frappe.call({
            // FIXED PATH ↓
            method: "ecclesia.ecclesia.doctype.wfh_activity_mapping.wfh_activity_mapping.get_mapping_status",
            callback(r) {
                if (!r.message) return;
                const s = r.message;
                const globalColor = s.globally_active ? "#16a34a" : "#dc2626";
                const globalLabel = s.globally_active ? "● ACTIVE" : "● INACTIVE";

                const warnHtml = s.without_scoring
                    ? `<div style="margin-top:8px;padding:8px 12px;background:#fffbeb;
                           border:1px solid #fde68a;border-radius:6px;font-size:12px;color:#92400e;">
                          ⚠ <b>${s.without_scoring}</b> active mapping(s) have no Activity Configuration.
                          Scoring will use base defaults (5 pts/action).
                       </div>`
                    : "";

                const notActive = !s.globally_active
                    ? `<div style="margin-top:8px;padding:8px 12px;background:#fee2e2;
                           border:1px solid #fca5a5;border-radius:6px;font-size:12px;color:#991b1b;">
                          ❌ Activity Tracking is <b>DISABLED</b>.
                          Enable the "Enable Activity Tracking" toggle and save.
                       </div>` : "";

                const html = `
                    <div style="background:var(--card-bg);border:1px solid var(--border-color);
                                border-radius:10px;padding:16px 20px;margin-bottom:16px;">
                        <div style="display:flex;align-items:center;
                                    justify-content:space-between;flex-wrap:wrap;gap:12px;">
                            <div style="display:flex;gap:24px;flex-wrap:wrap;">
                                <div style="text-align:center;">
                                    <div style="font-size:20px;font-weight:600;color:${globalColor}">
                                        ${globalLabel}
                                    </div>
                                    <div style="font-size:11px;color:var(--text-muted)">Engine Status</div>
                                </div>
                                <div style="text-align:center;">
                                    <div style="font-size:20px;font-weight:600;color:var(--text-primary)">${s.total}</div>
                                    <div style="font-size:11px;color:var(--text-muted)">Total Mappings</div>
                                </div>
                                <div style="text-align:center;">
                                    <div style="font-size:20px;font-weight:600;color:#16a34a">${s.active}</div>
                                    <div style="font-size:11px;color:var(--text-muted)">Active</div>
                                </div>
                                <div style="text-align:center;">
                                    <div style="font-size:20px;font-weight:600;color:#534AB7">${s.with_scoring}</div>
                                    <div style="font-size:11px;color:var(--text-muted)">With Scoring</div>
                                </div>
                                <div style="text-align:center;">
                                    <div style="font-size:20px;font-weight:600;color:#d97706">${s.without_scoring}</div>
                                    <div style="font-size:11px;color:var(--text-muted)">No Scoring</div>
                                </div>
                            </div>
                            <div style="font-size:11px;color:var(--text-muted);text-align:right;">
                                Runtime: ${s.runtime_mappings.length} mappings<br>
                                Cache: 5 min TTL
                            </div>
                        </div>
                        ${notActive}
                        ${warnHtml}
                    </div>`;

                frm.$wrapper.find(".wfh-mapping-status").remove();
                frm.layout.wrapper.find(".form-page").prepend(
                    $(`<div class="wfh-mapping-status">${html}</div>`)
                );
            }
        });
    },

    // ── Buttons ───────────────────────────────────────────────────────────────
    _setup_buttons(frm) {
        frm.add_custom_button(__("Seed Default Mappings"), () => {
            frappe.confirm(
                __("Add the 14 standard ERPNext DocTypes to the mapping table? Existing rows will not be changed."),
                () => {
                    frappe.call({
                        // FIXED PATH ↓
                        method: "ecclesia.ecclesia.doctype.wfh_activity_mapping.wfh_activity_mapping.seed_default_mappings",
                        callback(r) {
                            frappe.show_alert({ message: r.message, indicator: "green" }, 5);
                            frm.reload_doc();
                        }
                    });
                }
            );
        }, __("Tools")).addClass("btn-primary");

        frm.add_custom_button(__("Activity Configurations"), () => {
            frappe.set_route("List", "Activity Configuration");
        }, __("Tools"));

        frm.add_custom_button(__("Flush Cache"), () => {
            frappe.call({
                // FIXED PATH ↓
                method: "ecclesia.ecclesia.doctype.wfh_activity_mapping.wfh_activity_mapping.flush_cache",
                callback() {
                    frappe.show_alert({ message: __("Cache flushed — engine will reload on next event."), indicator: "blue" }, 5);
                    frm.trigger("_render_status_panel");
                }
            });
        }, __("Tools"));
    },

    _warn_inactive(frm) {
        if (!frm.doc.is_active) {
            frm.dashboard.add_comment(
                "⚠ Activity Tracking is <b>DISABLED</b>. " +
                "No activity logs will be written. Enable the toggle above and save.",
                "red", true
            );
        } else {
            frm.dashboard.clear_comment();
        }
    }
});

// ── Child table events ─────────────────────────────────────────────────────────

frappe.ui.form.on("WFH DocType Event Map", {

    doctype_name(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.doctype_name) return;

        // Auto-fill module from DocType metadata
        frappe.db.get_value("DocType", row.doctype_name, "module", r => {
            if (r && r.module && !row.module_tag) {
                frappe.model.set_value(cdt, cdn, "module_tag", r.module);
            }
        });

        // Check if Activity Configuration exists
        frappe.db.get_value(
            "Activity Configuration",
            { doctype_name: row.doctype_name, is_active: 1 },
            "name",
            r => {
                const has = r && r.name ? 1 : 0;
                frappe.model.set_value(cdt, cdn, "has_activity_config", has);
                frappe.model.set_value(cdt, cdn, "activity_config", r?.name || "");
                if (!has) {
                    frappe.show_alert({
                        message: __("No scoring config for {0}. Base default (5 pts) will apply. " +
                                    "Create an Activity Configuration to customise scoring.", [row.doctype_name]),
                        indicator: "orange"
                    }, 8);
                }
            }
        );

        // Auto-select on_submit for submittable DocTypes
        frappe.db.get_value("DocType", row.doctype_name, "is_submittable", r => {
            if (r && r.is_submittable) {
                frappe.model.set_value(cdt, cdn, "on_submit", 1);
            } else {
                frappe.model.set_value(cdt, cdn, "on_submit", 0);
                frappe.model.set_value(cdt, cdn, "on_update", 1);
            }
        });
    },

    // Warn if row is active but no events ticked
    on_submit(frm, cdt, cdn) { _check_events(frm, cdt, cdn); },
    on_cancel(frm, cdt, cdn) { _check_events(frm, cdt, cdn); },
    on_update(frm, cdt, cdn) { _check_events(frm, cdt, cdn); },
    after_insert(frm, cdt, cdn) { _check_events(frm, cdt, cdn); },
});

function _check_events(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (!row.is_active) return;
    const any = row.on_submit || row.on_cancel || row.on_update || row.after_insert;
    if (!any) {
        frappe.show_alert({
            message: __("Row {0} ({1}): select at least one event.", [row.idx, row.doctype_name]),
            indicator: "orange"
        }, 5);
    }
}