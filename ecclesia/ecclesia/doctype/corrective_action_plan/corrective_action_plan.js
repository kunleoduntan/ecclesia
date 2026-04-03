// Copyright (c) 2026, kunle Oduntan and contributors
// For license information, please see license.txt

// ╔══════════════════════════════════════════════════════════════════════════╗
// ║  CORRECTIVE ACTION PLAN  ·  Ecclesia Audit Management System            ║
// ╚══════════════════════════════════════════════════════════════════════════╝

frappe.ui.form.on("Corrective Action Plan", {

    refresh(frm) {
        _render_cap_header(frm);
        _render_milestone_progress(frm);
        _build_buttons(frm);
    },

    status(frm)   { _render_cap_header(frm); _render_milestone_progress(frm); },

    audit_finding(frm) {
        if (!frm.doc.audit_finding) return;
        frappe.db.get_value("Audit Finding", frm.doc.audit_finding,
            ["risk_rating","finding_title","action_owner","due_date"], v => {
                if (!v) return;
                if (!frm.doc.risk_rating)  frm.set_value("risk_rating",  v.risk_rating);
                if (!frm.doc.action_owner) frm.set_value("action_owner", v.action_owner);
                if (!frm.doc.due_date)     frm.set_value("due_date",     v.due_date);
                if (!frm.doc.cap_title)    frm.set_value("cap_title",    `CAP: ${v.finding_title}`);
            });
    },

    due_date(frm) {
        if (frm.doc.due_date && frm.doc.due_date < frappe.datetime.get_today()
            && !["Completed","Accepted Risk"].includes(frm.doc.status))
            frappe.show_alert({
                message: "⏰ Due date is in the past — this CAP will be marked <b>Overdue</b>.",
                indicator: "orange",
            }, 6);
    },
});


// ── CAP Status Header ───────────────────────────────────────────────────────
function _render_cap_header(frm) {
    const st = frm.doc.status || "Open";
    const risk = frm.doc.risk_rating;

    const st_cfg = {
        "Open":          { bg:"#e8f4fd", border:"#3498db", text:"#2980b9", icon:"📂" },
        "In Progress":   { bg:"#f3e5f5", border:"#9b59b6", text:"#8e44ad", icon:"⚙️" },
        "Completed":     { bg:"#f0fdf4", border:"#27ae60", text:"#1e8449", icon:"✅" },
        "Overdue":       { bg:"#fdf2f2", border:"#e74c3c", text:"#c0392b", icon:"⏰" },
        "Accepted Risk": { bg:"#f8f9fa", border:"#7f8c8d", text:"#666",   icon:"🤝" },
    };
    const sc = st_cfg[st] || st_cfg["Open"];

    const risk_badge = risk ? `
        <span style="background:${{Critical:"#e74c3c",High:"#e67e22",Medium:"#f39c12",Low:"#27ae60"}[risk]||"#aaa"};
                     color:#fff;padding:3px 12px;border-radius:12px;font-size:12px;font-weight:600;">
            ${risk} Risk
        </span>` : "";

    const days_left = frm.doc.due_date
        ? frappe.datetime.get_diff(frm.doc.due_date, frappe.datetime.get_today()) : null;
    const due_html  = days_left !== null
        ? `<span style="color:${days_left < 0 ? "#e74c3c" : days_left <= 7 ? "#e67e22" : "#666"};font-size:12px;">
               📅 Due: <b>${frm.doc.due_date}</b>
               ${days_left < 0 ? `<b style="color:#e74c3c;"> (${Math.abs(days_left)}d overdue)</b>`
                : days_left === 0 ? " <b style='color:#e67e22;'>(Today!)</b>"
                : ` (${days_left}d remaining)`}
           </span>` : "";

    frm.dashboard.add_comment(`
        <div style="background:${sc.bg};border-left:5px solid ${sc.border};
                    border-radius:0 8px 8px 0;padding:12px 16px;">
            <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
                <span style="font-size:20px;">${sc.icon}</span>
                <span style="font-weight:700;font-size:14px;color:${sc.text};">${st}</span>
                ${risk_badge}
                ${due_html}
            </div>
            ${frm.doc.action_owner
                ? `<div style="margin-top:6px;font-size:12px;color:#666;">
                       👤 Owner: <b>${frm.doc.action_owner}</b>
                   </div>` : ""}
        </div>`, "white", true);
}


// ── Milestone Progress Bar ──────────────────────────────────────────────────
function _render_milestone_progress(frm) {
    const ms = frm.doc.milestones || [];
    if (!ms.length) return;

    const total     = ms.length;
    const completed = ms.filter(m => m.status === "Completed").length;
    const overdue   = ms.filter(m => m.status === "Overdue").length;
    const pending   = total - completed - overdue;
    const pct       = Math.round(completed / total * 100);

    const dots = ms.map(m => {
        const mc = { Completed:"#27ae60", Overdue:"#e74c3c", "In Progress":"#3498db",
                     Pending:"#bdc3c7" };
        const c  = mc[m.status] || "#bdc3c7";
        return `<span title="${m.milestone_description||""} — ${m.status}"
                      style="display:inline-block;width:14px;height:14px;border-radius:50%;
                             background:${c};margin:0 2px;border:2px solid ${c}cc;"></span>`;
    }).join("");

    frm.dashboard.add_comment(`
        <div style="background:#f8f9fa;border-radius:8px;padding:12px 14px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <span style="font-size:13px;font-weight:600;color:#2c3e50;">
                    📍 Milestones: ${completed}/${total} completed
                </span>
                <span style="font-size:13px;font-weight:700;color:${pct===100?"#27ae60":"#2c3e50"};">
                    ${pct}%
                </span>
            </div>
            <div style="background:#ecf0f1;border-radius:6px;height:10px;overflow:hidden;margin-bottom:8px;">
                <div style="background:linear-gradient(90deg,#27ae60,#2ecc71);
                            width:${pct}%;height:10px;border-radius:6px;
                            transition:width .4s ease;"></div>
            </div>
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                ${dots}
                <span style="font-size:11px;color:#888;margin-left:4px;">
                    ${pending} pending
                    ${overdue ? `· <span style="color:#e74c3c;font-weight:600;">${overdue} overdue</span>` : ""}
                </span>
            </div>
        </div>`, "white", true);
}


// ── Action Buttons ──────────────────────────────────────────────────────────
function _build_buttons(frm) {
    if (frm.is_new()) return;

    if (frm.doc.audit_finding)
        frm.add_custom_button(__("📌 View Finding"), () =>
            frappe.set_route("Form","Audit Finding", frm.doc.audit_finding), __("View"));

    if (["Open","In Progress","Overdue"].includes(frm.doc.status))
        frm.add_custom_button(__("✅ Mark Completed"), () => _complete_dialog(frm), __("Actions"));

    if (frm.doc.status === "Open")
        frm.add_custom_button(__("🤝 Accept Risk"), () =>
            frappe.confirm("Close this CAP as <b>Accepted Risk</b>? No remediation will be made.",
                () => frappe.db.set_value("Corrective Action Plan", frm.doc.name, "status","Accepted Risk")
                             .then(() => frm.reload_doc())), __("Actions"));

    if (frm.doc.status === "In Progress")
        frm.add_custom_button(__("📊 Update Progress"), () => _progress_dialog(frm), __("Actions"));
}


// ── Completion Dialog ───────────────────────────────────────────────────────
function _complete_dialog(frm) {
    const d = new frappe.ui.Dialog({
        title: "✅ Complete CAP",
        fields: [
            { fieldtype:"HTML",       fieldname:"banner" },
            { fieldtype:"Date",       label:"Completion Date", fieldname:"completion_date",
              reqd:1, default: frappe.datetime.get_today() },
            { fieldtype:"Text Editor",label:"Evidence of Completion", fieldname:"completion_evidence",
              reqd:1, description:"Describe what was done: policy updates, training, system changes, screenshots, etc." },
            { fieldtype:"Check",      label:"Re-audit Required to verify effectiveness",
              fieldname:"re_audit_required" },
        ]
    });
    d.fields_dict.banner.$wrapper.html(`
        <div style="background:#f0fdf4;border-left:4px solid #27ae60;padding:10px 14px;
                    border-radius:4px;margin-bottom:6px;font-size:13px;">
            ✅ Completing: <b>${frm.doc.cap_title}</b>
        </div>`);
    d.set_primary_action(__("Mark Completed"), () => {
        const v = d.get_values(); if (!v) return;
        frappe.db.set_value("Corrective Action Plan", frm.doc.name, {
            status:               "Completed",
            completion_date:      v.completion_date,
            completion_evidence:  v.completion_evidence,
            re_audit_required:    v.re_audit_required,
        }).then(() => { d.hide(); frm.reload_doc();
            frappe.show_alert({ message:"CAP marked as completed 🎉", indicator:"green" }, 4); });
    });
    d.get_primary_btn().css({ background:"#27ae60", color:"#fff", border:"none" });
    d.show();
}


// ── Progress Update Dialog ──────────────────────────────────────────────────
function _progress_dialog(frm) {
    const d = new frappe.ui.Dialog({
        title: "📊 Update Progress",
        fields: [
            { fieldtype:"Select", label:"Current Status", fieldname:"new_status",
              options:"Open\nIn Progress\nCompleted", default: frm.doc.status },
            { fieldtype:"Small Text", label:"Progress Note", fieldname:"note",
              description:"Brief update for audit trail" },
        ]
    });
    d.set_primary_action(__("Update"), () => {
        const v = d.get_values(); if (!v) return;
        frappe.db.set_value("Corrective Action Plan", frm.doc.name, "status", v.new_status)
            .then(() => { d.hide(); frm.reload_doc();
                frappe.show_alert({ message:`Status updated to ${v.new_status}`, indicator:"blue" }, 3); });
    });
    d.show();
}