// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

frappe.ui.form.on("Calibration Session", {

    refresh(frm) {
        const colors = { "Planned":"blue","In Progress":"orange","Completed":"teal","Closed":"darkgrey" };
        frm.page.set_indicator(frm.doc.status || "Planned", colors[frm.doc.status] || "gray");
        _render_calibration_summary(frm);
        _add_calibration_buttons(frm);
    },
});


function _render_calibration_summary(frm) {
    if (!frm.doc.entries || !frm.doc.entries.length) return;

    const COLORS = {
        "Outstanding":"#1D9E75","Exceeds Expectations":"#185FA5",
        "Meets Expectations":"#534AB7","Needs Improvement":"#BA7517","Unsatisfactory":"#E24B4A"
    };
    const RATINGS = ["Outstanding","Exceeds Expectations","Meets Expectations",
                     "Needs Improvement","Unsatisfactory"];

    const dist   = {};
    RATINGS.forEach(r => dist[r] = 0);
    let changes  = 0;

    frm.doc.entries.forEach(e => {
        const r = e.calibrated_rating || e.system_rating || "Unrated";
        dist[r] = (dist[r] || 0) + 1;
        if (e.calibrated_rating && e.calibrated_rating !== e.system_rating) changes++;
    });

    const total   = frm.doc.entries.length;
    const avg     = frm.doc.entries.reduce((s, e) => s + (e.composite_score || 0), 0) / total;
    const outPct  = Math.round((dist["Outstanding"] || 0) / total * 100);
    const warn    = outPct > 20
        ? `<div style="background:var(--color-background-warning);border:0.5px solid
                        var(--color-border-warning);border-radius:6px;padding:8px 12px;
                        font-size:12px;color:var(--color-text-warning);margin-bottom:1rem">
               ⚠ ${outPct}% rated Outstanding — guideline is ≤20%
           </div>` : "";

    const bars = RATINGS.map(r => `
        <div style="margin-bottom:6px">
            <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:2px">
                <span style="color:var(--color-text-secondary)">${r}</span>
                <span style="font-weight:500">${dist[r] || 0}
                    <span style="color:var(--color-text-tertiary);font-weight:400">
                        (${Math.round(((dist[r]||0)/total)*100)}%)
                    </span>
                </span>
            </div>
            <div style="height:6px;background:var(--color-background-secondary);
                        border-radius:3px;overflow:hidden">
                <div style="width:${Math.round(((dist[r]||0)/total)*100)}%;
                            height:6px;background:${COLORS[r]||'#888'};border-radius:3px"></div>
            </div>
        </div>`).join("");

    const html = `
        ${warn}
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;padding:.5rem 0">
            <div>
                <p style="font-size:11px;font-weight:500;text-transform:uppercase;
                           letter-spacing:.05em;color:var(--color-text-tertiary);margin:0 0 10px">
                    Rating distribution
                </p>
                ${bars}
            </div>
            <div style="display:flex;flex-direction:column;gap:10px">
                <div style="background:var(--color-background-secondary);
                            border-radius:8px;padding:12px 16px">
                    <p style="font-size:11px;color:var(--color-text-tertiary);margin:0 0 2px">
                        Employees
                    </p>
                    <p style="font-size:24px;font-weight:500;margin:0">${total}</p>
                </div>
                <div style="background:var(--color-background-secondary);
                            border-radius:8px;padding:12px 16px">
                    <p style="font-size:11px;color:var(--color-text-tertiary);margin:0 0 2px">
                        Avg composite
                    </p>
                    <p style="font-size:24px;font-weight:500;margin:0">${avg.toFixed(2)}</p>
                </div>
                <div style="background:var(--color-background-secondary);
                            border-radius:8px;padding:12px 16px">
                    <p style="font-size:11px;color:var(--color-text-tertiary);margin:0 0 2px">
                        Manual changes
                    </p>
                    <p style="font-size:24px;font-weight:500;margin:0;
                              color:${changes ? '#BA7517' : 'inherit'}">${changes}</p>
                </div>
            </div>
        </div>`;

    frm.dashboard.add_section(html, "Calibration Summary");
}


function _add_calibration_buttons(frm) {
    if (!frappe.user.has_role(["HR Manager", "System Manager"])) return;
    if (frm.doc.docstatus === 1) return;

    frm.add_custom_button("Auto-Populate Records", () => {
        frm.call("auto_populate").then(r => {
            frappe.show_alert({ message: `Added ${r.message.added} records`, indicator: "green" });
            frm.reload_doc();
        });
    }, "Tools");

    frm.add_custom_button("Lock All Entries", () => {
        frappe.confirm("Lock all calibrated ratings? Locked rows cannot be changed.", () => {
            frm.call("lock_all").then(() => {
                frappe.show_alert({ message: "All entries locked", indicator: "green" });
                frm.reload_doc();
            });
        });
    }, "Tools");
}