// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

// External Task — Client Script
// Ecclesia Module

frappe.ui.form.on("External Task", {

    refresh(frm) {
        frm.trigger("_render_completion_bar");
        frm.trigger("_setup_buttons");
        frm.trigger("_set_indicator");
    },

    onload(frm) {
        if (frm.is_new()) {
            frm.set_value("user", frappe.session.user);
            frm.set_value("task_date", frappe.datetime.get_today());
        }
    },

    // ── Completion bar ─────────────────────────────────────────────────────────
    _render_completion_bar(frm) {
        const total     = (frm.doc.items || []).length;
        const completed = (frm.doc.items || []).filter(i => i.status === "Done").length;
        const pct       = total ? Math.round(completed / total * 100) : 0;
        const color     = pct === 100 ? "#16a34a" : pct >= 50 ? "#d97706" : "#534AB7";

        frm.$wrapper.find(".ext-completion-bar").remove();
        if (!total) return;

        const html = `
            <div class="ext-completion-bar" style="padding:8px 0 4px">
                <div style="display:flex;justify-content:space-between;
                            font-size:12px;color:var(--text-muted);margin-bottom:4px">
                    <span>${completed} of ${total} tasks done</span>
                    <span style="font-weight:500;color:${color}">${pct}%</span>
                </div>
                <div style="height:6px;background:var(--border-color);border-radius:3px;overflow:hidden">
                    <div style="height:6px;width:${pct}%;background:${color};border-radius:3px;transition:width .4s"></div>
                </div>
            </div>`;

        frm.get_field("items").$wrapper
            .find(".frappe-control").before(html);
    },

    _setup_buttons(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button(__("Mark All Done"), () => {
                (frm.doc.items || []).forEach((row, i) => {
                    frappe.model.set_value(row.doctype, row.name, "status", "Done");
                });
                frm.save().then(() => frm.reload_doc());
            }, __("Actions"));

            frm.add_custom_button(__("Carry Forward Pending"), () => {
                const pending = (frm.doc.items || []).filter(
                    i => ["Pending", "In Progress"].includes(i.status)
                );
                if (!pending.length) {
                    frappe.msgprint(__("No pending tasks to carry forward."));
                    return;
                }
                frappe.confirm(
                    __("Create a new External Task tomorrow with {0} pending item(s)?", [pending.length]),
                    () => {
                        frappe.call({
                            method: "ecclesia.doctype.external_task.external_task.carry_forward",
                            args: { source_name: frm.doc.name },
                            callback(r) {
                                if (r.message) {
                                    frappe.set_route("Form", "External Task", r.message);
                                }
                            }
                        });
                    }
                );
            }, __("Actions"));
        }
    },

    _set_indicator(frm) {
        const colors = {
            "In Progress":         "blue",
            "Completed":           "green",
            "Partially Completed": "orange",
            "Carried Forward":     "yellow",
        };
        frm.page.set_indicator(frm.doc.overall_status, colors[frm.doc.overall_status] || "gray");
    }
});

// ── Child table events ─────────────────────────────────────────────────────────

frappe.ui.form.on("External Task Item", {
    status(frm, cdt, cdn) {
        frm.trigger("_render_completion_bar");
    },
    items_remove(frm) {
        frm.trigger("_render_completion_bar");
    },
    items_add(frm, cdt, cdn) {
        // Default new row to current time
        frappe.model.set_value(cdt, cdn, "status", "Pending");
        frappe.model.set_value(cdt, cdn, "priority", "Medium");
    }
});

// ── List view formatters ────────────────────────────────────────────────────────

frappe.listview_settings["External Task"] = {
    get_indicator(doc) {
        const map = {
            "Completed":           ["Completed",           "green",  "overall_status,=,Completed"],
            "In Progress":         ["In Progress",         "blue",   "overall_status,=,In Progress"],
            "Partially Completed": ["Partially Completed", "orange", "overall_status,=,Partially Completed"],
            "Carried Forward":     ["Carried Forward",     "yellow", "overall_status,=,Carried Forward"],
        };
        return map[doc.overall_status] || [doc.overall_status, "gray"];
    },
    formatters: {
        completion_pct(val) {
            const pct   = parseFloat(val || 0);
            const color = pct === 100 ? "#16a34a" : pct >= 50 ? "#d97706" : "#534AB7";
            return `
                <div style="display:flex;align-items:center;gap:6px">
                    <div style="width:60px;height:4px;background:#e5e7eb;border-radius:2px;overflow:hidden">
                        <div style="width:${pct}%;height:4px;background:${color};border-radius:2px"></div>
                    </div>
                    <span style="color:${color};font-size:11px;font-weight:500">${pct}%</span>
                </div>`;
        }
    }
};