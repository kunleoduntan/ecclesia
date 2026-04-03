// Copyright (c) 2026, kunle Oduntan and contributors
// For license information, please see license.txt
// ╔══════════════════════════════════════════════════════════════════════════╗
// ║  AUDIT FINDING  ·  Ecclesia Audit Management System                     ║
// ╚══════════════════════════════════════════════════════════════════════════╝

const RISK_CFG = {
    Critical: { bg:"#fdf2f2", border:"#e74c3c", text:"#c0392b", badge:"#e74c3c" },
    High:     { bg:"#fdf6ec", border:"#e67e22", text:"#d35400", badge:"#e67e22" },
    Medium:   { bg:"#fefce8", border:"#f1c40f", text:"#b7950b", badge:"#f39c12" },
    Low:      { bg:"#f0fdf4", border:"#27ae60", text:"#1e8449", badge:"#27ae60" },
};

frappe.ui.form.on("Audit Finding", {

    refresh(frm) {
        _render_finding_header(frm);
        _check_5cs(frm);
        _build_buttons(frm);
    },

    risk_rating(frm)       { _render_finding_header(frm); },
    status(frm)            { _render_finding_header(frm); },

    financial_impact(frm)  { _live_materiality_hint(frm); },

    reference_doctype(frm) {
        if (!frm.doc.reference_doctype) return;
        frappe.db.get_value("Auditable DocType Registry",
            { doctype_name: frm.doc.reference_doctype },
            ["transaction_code","financial_statement_line","coso_component"],
            v => {
                if (!v) return;
                if (!frm.doc.transaction_code)          frm.set_value("transaction_code",         v.transaction_code);
                if (!frm.doc.financial_statement_line)  frm.set_value("financial_statement_line", v.financial_statement_line);
                if (!frm.doc.coso_component)            frm.set_value("coso_component",           v.coso_component);
            });
    },

    criteria(frm)    { _check_5cs(frm); },
    condition(frm)   { _check_5cs(frm); },
    cause(frm)       { _check_5cs(frm); },
    consequence(frm) { _check_5cs(frm); },
    corrective_action_suggested(frm) { _check_5cs(frm); },
});


// ── Finding Header Banner ───────────────────────────────────────────────────
function _render_finding_header(frm) {
    const rr  = frm.doc.risk_rating;
    const cfg = RISK_CFG[rr] || { bg:"#f8f9fa", border:"#dee2e6", text:"#666", badge:"#aaa" };
    const st  = frm.doc.status || "Open";

    const status_colors = {
        "Open":"#3498db", "In Progress":"#9b59b6",
        "Management Response Pending":"#e67e22",
        "Closed - Resolved":"#27ae60", "Closed - Accepted Risk":"#7f8c8d",
        "Escalated":"#e74c3c",
    };
    const sc = status_colors[st] || "#aaa";

    const fi = frm.doc.financial_impact
        ? `<span style="background:#fdf2f2;border:1px solid #e74c3c;color:#c0392b;
                         padding:3px 10px;border-radius:12px;font-size:12px;">
               💰 ${fmt_money(frm.doc.financial_impact)}
           </span>` : "";

    const ml = frm.doc.materiality_level
        ? `<span style="background:#f0f4ff;border:1px solid #3498db;color:#2980b9;
                         padding:3px 10px;border-radius:12px;font-size:12px;">
               📏 ${frm.doc.materiality_level}
           </span>` : "";

    const code = frm.doc.transaction_code
        ? `<span style="font-family:monospace;background:#2c3e50;color:#ecf0f1;
                         padding:3px 10px;border-radius:4px;font-size:11px;">
               ${frm.doc.transaction_code}
           </span>` : "";

    const source_icons = {
        "Auditor":"👤","AI Auto-Detection":"🤖",
        "Continuous Monitoring":"📡","Whistleblower":"🔔","External Audit":"🏛️"
    };
    const src = frm.doc.source
        ? `<span style="color:#666;font-size:12px;">
               ${source_icons[frm.doc.source]||"📌"} ${frm.doc.source}
           </span>` : "";

    frm.dashboard.add_comment(`
        <div style="background:${cfg.bg};border-left:5px solid ${cfg.border};
                    border-radius:0 8px 8px 0;padding:12px 16px;">
            <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:6px;">
                <span style="background:${cfg.badge};color:#fff;font-weight:700;
                             padding:4px 14px;border-radius:14px;font-size:13px;">
                    🚨 ${rr || "—"} Risk
                </span>
                <span style="background:${sc};color:#fff;padding:4px 14px;
                             border-radius:14px;font-size:12px;font-weight:600;">
                    ${st}
                </span>
                ${fi}${ml}${code}${src}
            </div>
            ${frm.doc.coso_component
                ? `<div style="font-size:11px;color:#888;">COSO: <b>${frm.doc.coso_component}</b></div>` : ""}
        </div>`, "white", true);
}


// ── 5Cs Completeness Tracker ────────────────────────────────────────────────
function _check_5cs(frm) {
    if (!["Critical","High"].includes(frm.doc.risk_rating)) return;
    const five_c = [
        { key:"criteria",                  label:"Criteria"         },
        { key:"condition",                 label:"Condition"        },
        { key:"cause",                     label:"Cause"            },
        { key:"consequence",               label:"Consequence"      },
        { key:"corrective_action_suggested",label:"Corrective Action"},
    ];
    const filled  = five_c.filter(f => (frm.doc[f.key]||"").length > 10);
    const missing = five_c.filter(f => (frm.doc[f.key]||"").length <= 10);
    if (filled.length === 5) return;

    const dots = five_c.map(f => {
        const ok = (frm.doc[f.key]||"").length > 10;
        return `<span title="${f.label}" style="display:inline-flex;align-items:center;
                    gap:4px;font-size:12px;color:${ok?"#27ae60":"#e74c3c"};">
                    ${ok?"✅":"⭕"} ${f.label}
                </span>`;
    }).join("  ");

    frm.dashboard.add_comment(`
        <div style="background:#fef9ec;border-left:4px solid #f39c12;padding:10px 14px;border-radius:4px;">
            <div style="font-weight:700;color:#e67e22;margin-bottom:6px;">
                📝 5Cs Completeness: ${filled.length}/5 documented
            </div>
            <div style="display:flex;flex-wrap:wrap;gap:10px;">${dots}</div>
            ${missing.length
                ? `<div style="font-size:11px;color:#888;margin-top:6px;">
                       Missing: ${missing.map(f=>f.label).join(", ")}
                   </div>` : ""}
        </div>`, "white", true);
}


// ── Live Materiality Hint ───────────────────────────────────────────────────
function _live_materiality_hint(frm) {
    if (!frm.doc.audit_engagement || !flt(frm.doc.financial_impact)) return;
    frappe.db.get_value("Audit Engagement", frm.doc.audit_engagement,
        ["overall_materiality","performance_materiality","trivial_threshold"],
        v => {
            if (!v) return;
            const imp = flt(frm.doc.financial_impact);
            let level, color;
            if (imp >= flt(v.overall_materiality))       { level="Material";          color="#e74c3c"; }
            else if (imp >= flt(v.performance_materiality)){ level="Significant";     color="#e67e22"; }
            else if (imp >= flt(v.trivial_threshold))    { level="Management Letter"; color="#3498db"; }
            else                                         { level="Trivial";           color="#27ae60"; }

            frappe.show_alert({
                message: `Materiality → <b style="color:${color};">${level}</b>
                          <small style="color:#888;"> (Threshold: ${fmt_money(v.overall_materiality)})</small>`,
                indicator: level === "Material" ? "red" : level === "Significant" ? "orange" : "blue",
            }, 5);
        });
}


// ── Action Buttons ──────────────────────────────────────────────────────────
function _build_buttons(frm) {
    if (frm.is_new()) return;

    if (frm.doc.reference_doctype && frm.doc.reference_name)
        frm.add_custom_button(__("📂 Source Document"), () =>
            frappe.set_route("Form", frm.doc.reference_doctype, frm.doc.reference_name), __("View"));

    if (frm.doc.gl_entry_reference)
        frm.add_custom_button(__("🔗 GL Entry"), () =>
            frappe.set_route("Form","GL Entry", frm.doc.gl_entry_reference), __("View"));

    if (!frm.doc.corrective_action_plan && !["Closed - Resolved","Closed - Accepted Risk"].includes(frm.doc.status))
        frm.add_custom_button(__("📋 Create CAP"), () => frappe.new_doc("Corrective Action Plan", {
            audit_finding: frm.doc.name,
            cap_title:     `CAP: ${frm.doc.finding_title}`,
            risk_rating:   frm.doc.risk_rating,
            action_owner:  frm.doc.action_owner,
            due_date:      frm.doc.due_date,
        }), __("Actions"));

    if (["Open","In Progress"].includes(frm.doc.status))
        frm.add_custom_button(__("🔒 Close Finding"), () => _close_dialog(frm), __("Actions"));

    if (frm.doc.risk_rating === "Critical" && frm.doc.status === "Open")
        frm.add_custom_button(__("🚨 Escalate"), () =>
            frappe.confirm("Escalate this Critical finding to senior management?", () =>
                frappe.db.set_value("Audit Finding", frm.doc.name, "status", "Escalated")
                         .then(() => frm.reload_doc())), __("Actions"));
}


// ── Close Finding Dialog ────────────────────────────────────────────────────
function _close_dialog(frm) {
    const d = new frappe.ui.Dialog({
        title: "🔒 Close Finding",
        fields: [
            { fieldtype:"HTML", fieldname:"banner" },
            { fieldtype:"Select", label:"Closure Type", fieldname:"closure_status", reqd:1,
              options:"\nClosed - Resolved\nClosed - Accepted Risk" },
            { fieldtype:"Date", label:"Closure Date", fieldname:"actual_closure_date",
              reqd:1, default: frappe.datetime.get_today() },
            { fieldtype:"Text Editor", label:"Evidence of Closure", fieldname:"closure_evidence", reqd:1 },
            { fieldtype:"Text Editor", label:"Auditor Remarks", fieldname:"auditor_closure_remarks" },
        ]
    });
    d.fields_dict.banner.$wrapper.html(`
        <div style="background:#f0fdf4;border-left:4px solid #27ae60;padding:10px 14px;
                    border-radius:4px;margin-bottom:6px;font-size:13px;color:#1e8449;">
            ✅ Closing: <b>${frm.doc.finding_title}</b>
        </div>`);
    d.set_primary_action(__("Close Finding"), () => {
        const v = d.get_values();
        if (!v) return;
        frappe.db.set_value("Audit Finding", frm.doc.name, {
            status:                  v.closure_status,
            actual_closure_date:     v.actual_closure_date,
            closure_evidence:        v.closure_evidence,
            auditor_closure_remarks: v.auditor_closure_remarks,
        }).then(() => { d.hide(); frm.reload_doc();
            frappe.show_alert({ message:"Finding closed successfully ✅", indicator:"green" }, 4); });
    });
    d.get_primary_btn().css({ background:"#27ae60", color:"#fff", border:"none" });
    d.show();
}

function flt(v)           { return parseFloat(v) || 0; }
function fmt_money(v)     { return frappe.utils.fmt_money(v || 0); }