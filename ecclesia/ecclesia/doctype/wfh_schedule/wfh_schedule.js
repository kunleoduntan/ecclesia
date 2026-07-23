// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

// WFH Schedule — Client Script
// Ecclesia Module

frappe.ui.form.on("WFH Schedule", {

    refresh(frm) {
        frm.trigger("_toggle_scope_fields");
        frm.trigger("_render_week_preview");
        frm.trigger("_setup_buttons");
    },

    applies_to(frm) { frm.trigger("_toggle_scope_fields"); },

    monday(frm)    { frm.trigger("_render_week_preview"); },
    tuesday(frm)   { frm.trigger("_render_week_preview"); },
    wednesday(frm) { frm.trigger("_render_week_preview"); },
    thursday(frm)  { frm.trigger("_render_week_preview"); },
    friday(frm)    { frm.trigger("_render_week_preview"); },
    saturday(frm)  { frm.trigger("_render_week_preview"); },
    sunday(frm)    { frm.trigger("_render_week_preview"); },

    // ── Field visibility ───────────────────────────────────────────────────────
    _toggle_scope_fields(frm) {
        const t = frm.doc.applies_to;
        frm.toggle_display("department", t === "Department");
        frm.toggle_display("employee",   t === "Individual Employee");
        frm.toggle_reqd("department", t === "Department");
        frm.toggle_reqd("employee",   t === "Individual Employee");
    },

    // ── Week preview card ──────────────────────────────────────────────────────
    _render_week_preview(frm) {
        const days = [
            { key: "monday",    label: "Mon" },
            { key: "tuesday",   label: "Tue" },
            { key: "wednesday", label: "Wed" },
            { key: "thursday",  label: "Thu" },
            { key: "friday",    label: "Fri" },
            { key: "saturday",  label: "Sat" },
            { key: "sunday",    label: "Sun" },
        ];

        const cells = days.map(d => {
            const isWFH = frm.doc[d.key];
            const isWeekend = d.key === "saturday" || d.key === "sunday";
            let bg, color, label, border;
            if (isWFH) {
                bg = "#EEEDFE"; color = "#3C3489"; label = "WFH"; border = "#CECBF6";
            } else if (isWeekend) {
                bg = "#F1EFE8"; color = "#888780"; label = "—"; border = "#E2DFDA";
            } else {
                bg = "#EAF3DE"; color = "#27500A"; label = "WFO"; border = "#C0DD97";
            }
            return `
                <div style="text-align:center;padding:10px 8px;border-radius:8px;
                            background:${bg};border:1px solid ${border};min-width:52px">
                    <div style="font-size:12px;font-weight:500;color:${color}">${d.label}</div>
                    <div style="font-size:10px;color:${color};margin-top:3px">${label}</div>
                </div>`;
        }).join("");

        const wfhCount = days.filter(d => frm.doc[d.key] && !["saturday","sunday"].includes(d.key)).length;
        const wfoCount = 5 - wfhCount;

        const html = `
            <div style="padding:0 0 12px">
                <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px">${cells}</div>
                <div style="display:flex;gap:16px;font-size:12px;color:var(--text-muted)">
                    <span style="display:flex;align-items:center;gap:4px">
                        <span style="width:10px;height:10px;border-radius:2px;background:#534AB7;display:inline-block"></span>
                        ${wfhCount} WFH day${wfhCount !== 1 ? "s" : ""}/week
                    </span>
                    <span style="display:flex;align-items:center;gap:4px">
                        <span style="width:10px;height:10px;border-radius:2px;background:#1D9E75;display:inline-block"></span>
                        ${wfoCount} WFO day${wfoCount !== 1 ? "s" : ""}/week
                    </span>
                </div>
            </div>`;

        frm.$wrapper.find(".wfh-week-preview").remove();
        frm.get_field("monday").$wrapper.closest(".form-section").find(".section-body")
            .prepend(`<div class="wfh-week-preview" style="padding:12px 0 0">${html}</div>`);
    },

    // ── Toolbar buttons ────────────────────────────────────────────────────────
    _setup_buttons(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button(__("View Employees on this Schedule"), () => {
                frappe.call({
                    method: "ecclesia.ecclesia.doctype.wfh_schedule.wfh_schedule.get_employees_on_schedule",
                    args: { schedule_name: frm.doc.name },
                    callback(r) {
                        if (!r.message || !r.message.length) {
                            frappe.msgprint(__("No active employees found on this schedule."));
                            return;
                        }
                        const rows = r.message.map(e =>
                            `<tr><td>${e.employee}</td><td>${e.employee_name}</td><td>${e.department || "—"}</td></tr>`
                        ).join("");
                        frappe.msgprint({
                            title: __("Employees on this Schedule"),
                            message: `<table style="width:100%;border-collapse:collapse">
                                <thead><tr>
                                    <th style="padding:6px;border-bottom:1px solid #e2e8f0">ID</th>
                                    <th style="padding:6px;border-bottom:1px solid #e2e8f0">Name</th>
                                    <th style="padding:6px;border-bottom:1px solid #e2e8f0">Dept</th>
                                </tr></thead><tbody>${rows}</tbody></table>`,
                        });
                    }
                });
            }, __("Tools"));

            frm.add_custom_button(__("Check Today's Mode"), () => {
                const emp = frm.doc.employee || "";
                if (frm.doc.applies_to === "Individual Employee" && emp) {
                    frappe.call({
                        method: "ecclesia.ecclesia.doctype.wfh_schedule.wfh_schedule.get_employee_schedule",
                        args: { employee: emp },
                        callback(r) {
                            if (r.message) {
                                frappe.msgprint({
                                    title: __("Today's Work Mode"),
                                    message: `<b>${r.message.work_mode}</b> for ${emp} today.`,
                                    indicator: r.message.is_wfh ? "green" : "blue"
                                });
                            }
                        }
                    });
                } else {
                    frappe.msgprint(__("Select an individual employee to check today's mode."));
                }
            }, __("Tools"));
        }
    }
});