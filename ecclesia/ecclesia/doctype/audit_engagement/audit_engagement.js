// Copyright (c) 2026, kunle Oduntan and contributors
// For license information, please see license.txt

// Audit Engagement — Client Script

// ╔══════════════════════════════════════════════════════════════════════════╗
// ║  AUDIT ENGAGEMENT  ·  Ecclesia Audit Management System                  ║
// ╚══════════════════════════════════════════════════════════════════════════╝

const STAGE_META = {
    Draft:     { icon: "✏️",  color: "#95a5a6" },
    Planning:  { icon: "📋",  color: "#3498db" },
    Fieldwork: { icon: "🔍",  color: "#9b59b6" },
    Review:    { icon: "🧐",  color: "#e67e22" },
    Reporting: { icon: "📄",  color: "#e74c3c" },
    Closed:    { icon: "✅",  color: "#27ae60" },
    Cancelled: { icon: "⛔",  color: "#7f8c8d" },
};

frappe.ui.form.on("Audit Engagement", {

    refresh(frm) {
        _render_stage_pipeline(frm);
        _render_engagement_stats(frm);
        _build_buttons(frm);
        frm.trigger("overall_materiality");
    },

    status(frm) {
        _render_stage_pipeline(frm);
    },

    overall_materiality(frm) {
        const m = flt(frm.doc.overall_materiality);
        if (m > 0) {
            frm.set_value("performance_materiality", +(m * 0.75).toFixed(2));
            frm.set_value("trivial_threshold",        +(m * 0.05).toFixed(2));
        }
    },

    validate(frm) {
        if (frm.doc.from_date && frm.doc.to_date && frm.doc.from_date > frm.doc.to_date)
            frappe.throw(__("Audit period 'From' date cannot be after 'To' date."));
    },
});


// ── Stage Pipeline ──────────────────────────────────────────────────────────
function _render_stage_pipeline(frm) {
    const stages   = ["Draft","Planning","Fieldwork","Review","Reporting","Closed"];
    const current  = frm.doc.status || "Draft";
    const cur_idx  = stages.indexOf(current);
    const next_map = { Draft:"Planning", Planning:"Fieldwork", Fieldwork:"Review",
                       Review:"Reporting", Reporting:"Closed" };
    const next     = next_map[current];

    let steps_html = "";
    stages.forEach((s, i) => {
        const m   = STAGE_META[s];
        const done = i < cur_idx;
        const act  = s === current;
        const bg   = done ? "#27ae60" : act ? m.color : "#ecf0f1";
        const tc   = done || act ? "#fff" : "#95a5a6";
        const lc   = done || act ? (done ? "#27ae60" : m.color) : "#bdc3c7";
        const fw   = act ? "700" : "400";
        const dot  = done ? "✓" : m.icon;
        const line = i < stages.length - 1
            ? `<div style="flex:1;height:3px;background:${i < cur_idx ? "#27ae60":"#ecf0f1"};margin-top:18px;"></div>`
            : "";
        steps_html += `
            <div style="display:flex;flex-direction:column;align-items:center;flex:0 0 auto;">
                <div style="width:38px;height:38px;border-radius:50%;background:${bg};
                            color:${tc};display:flex;align-items:center;justify-content:center;
                            font-size:16px;box-shadow:0 2px 6px rgba(0,0,0,.12);">${dot}</div>
                <div style="font-size:11px;color:${lc};font-weight:${fw};margin-top:5px;
                            white-space:nowrap;">${s}</div>
            </div>
            ${line}`;
    });

    const advance_btn = next ? `
        <button class="btn-advance-stage" style="margin-top:10px;background:${STAGE_META[next]?.color||"#2980b9"};
            color:#fff;border:none;border-radius:20px;padding:5px 18px;font-size:12px;
            font-weight:600;cursor:pointer;box-shadow:0 2px 6px rgba(0,0,0,.15);">
            Advance → ${next}
        </button>` : "";

    const cancelled_banner = current === "Cancelled"
        ? `<div style="background:#ffeaea;border-left:4px solid #e74c3c;padding:8px 14px;
                       border-radius:4px;color:#c0392b;font-weight:700;margin-bottom:8px;">
               ⛔ This engagement has been cancelled.
           </div>` : "";

    frm.dashboard.add_comment(`
        ${cancelled_banner}
        <div style="display:flex;align-items:center;gap:0;padding:12px 6px 2px;flex-wrap:nowrap;overflow-x:auto;">
            ${steps_html}
        </div>
        <div style="text-align:center;">${advance_btn}</div>`, "white", true);

    // Wire advance button after DOM renders
    setTimeout(() => {
        frm.layout?.$wrapper.find(".btn-advance-stage").off("click").on("click", () => {
            frappe.confirm(`Move engagement to <b>${next}</b>?`, () =>
                frappe.db.set_value("Audit Engagement", frm.doc.name, "status", next)
                         .then(() => frm.reload_doc()));
        });
    }, 200);
}


// ── Engagement Stats Cards ──────────────────────────────────────────────────
function _render_engagement_stats(frm) {
    const t = frm.doc.total_findings || 0;
    if (!t && !frm.doc.total_anomalies_detected) return;

    const risk_cards = [
        { label:"Critical", n: frm.doc.critical_findings||0, bg:"#fdf2f2", border:"#e74c3c", tc:"#c0392b" },
        { label:"High",     n: frm.doc.high_findings||0,     bg:"#fdf6ec", border:"#e67e22", tc:"#d35400" },
        { label:"Medium",   n: frm.doc.medium_findings||0,   bg:"#fefce8", border:"#f1c40f", tc:"#b7950b" },
        { label:"Low",      n: frm.doc.low_findings||0,      bg:"#f0fdf4", border:"#27ae60", tc:"#1e8449" },
    ].map(c => `
        <div style="background:${c.bg};border:1px solid ${c.border};border-radius:10px;
                    padding:10px 14px;text-align:center;flex:1;min-width:60px;">
            <div style="font-size:24px;font-weight:800;color:${c.tc};">${c.n}</div>
            <div style="font-size:10px;color:#666;font-weight:600;text-transform:uppercase;">${c.label}</div>
        </div>`).join("");

    const open = frm.doc.open_findings || 0;
    const pct  = t > 0 ? Math.round(open / t * 100) : 0;
    const ai   = frm.doc.total_anomalies_detected || 0;

    frm.dashboard.add_comment(`
        <div>
            <div style="font-size:11px;color:#999;font-weight:600;
                        text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px;">
                Findings Breakdown
            </div>
            <div style="display:flex;gap:8px;margin-bottom:10px;">${risk_cards}</div>
            <div style="display:flex;align-items:center;gap:16px;font-size:12px;color:#666;">
                <span><b>${t}</b> total &nbsp;·&nbsp; <b style="color:#e74c3c;">${open}</b> open</span>
                ${ai ? `<span style="color:#8e44ad;">🤖 <b>${ai}</b> AI anomalies</span>` : ""}
                <div style="flex:1;background:#ecf0f1;border-radius:10px;height:5px;">
                    <div style="background:linear-gradient(90deg,#e74c3c,#e67e22);
                                width:${pct}%;height:5px;border-radius:10px;"></div>
                </div>
                <span style="font-size:11px;color:#999;">${pct}% open</span>
            </div>
        </div>`, "white", true);
}


// ── Action Buttons ──────────────────────────────────────────────────────────
function _build_buttons(frm) {
    if (frm.is_new()) return;

    frm.add_custom_button(__("Samples"),    () => frappe.set_route("List","Audit Sample",    {audit_engagement: frm.doc.name}), __("View"));
    frm.add_custom_button(__("Checklists"), () => frappe.set_route("List","Audit Checklist", {audit_engagement: frm.doc.name}), __("View"));
    frm.add_custom_button(__("Findings"),   () => frappe.set_route("List","Audit Finding",   {audit_engagement: frm.doc.name}), __("View"));

    if (frm.doc.docstatus === 1 && frm.doc.status !== "Closed") {
        frm.add_custom_button(__("📄 Generate Report"), () => frappe.new_doc("Audit Report", {
            audit_engagement: frm.doc.name,
            report_title:     `Audit Report — ${frm.doc.engagement_title}`,
            report_date:       frappe.datetime.get_today(),
            issued_by:         frappe.session.user,
        }), __("Actions"));

        frm.add_custom_button(__("🤖 AI Anomaly Scan"),  () => _ai_scan_dialog(frm),   __("Actions"));
        frm.add_custom_button(__("⚖️ GL Assertions"),    () => _gl_assertions(frm),     __("Actions"));
    }
}


// ── AI Scan Dialog ──────────────────────────────────────────────────────────
function _ai_scan_dialog(frm) {
    const scope = (frm.doc.scope_doctypes || []).map(r => r.doctype_name).filter(Boolean);
    if (!scope.length) { frappe.msgprint(__("Add DocTypes to the scope first.")); return; }

    const d = new frappe.ui.Dialog({ title:"🤖 AI Anomaly Detection", size:"large",
        fields:[{fieldtype:"HTML", fieldname:"body"}] });

    d.fields_dict.body.$wrapper.html(`
        <div style="text-align:center;padding:24px;">
            <div style="font-size:52px;">🤖</div>
            <div style="font-size:16px;font-weight:700;color:#2c3e50;margin:8px 0 4px;">
                AI Anomaly Detection Engine
            </div>
            <div style="color:#7f8c8d;margin-bottom:20px;font-size:13px;">
                Scanning <b>${scope.length}</b> DocType(s): <em>${scope.join(", ")}</em>
            </div>
            <div class="scan-loader" style="display:none;color:#888;padding:20px;">
                <i class="fa fa-spinner fa-spin fa-3x" style="color:#9b59b6;"></i>
                <p style="margin-top:10px;">Analysing patterns &amp; anomalies…</p>
            </div>
            <div class="scan-output" style="display:none;text-align:left;"></div>
        </div>`);

    d.set_primary_action(__("▶ Run Scan"), () => {
        d.$wrapper.find(".scan-loader").show();
        d.$wrapper.find(".scan-output").hide();
        d.get_primary_btn().prop("disabled", true);
        frappe.call({
            method:"ecclesia.api.anomaly.run_scan",
            args:{ doctype_name: scope[0], from_date: frm.doc.from_date, to_date: frm.doc.to_date },
            callback(r) {
                const hits = r.message || [];
                d.$wrapper.find(".scan-loader").hide();
                const ok = hits.length === 0;
                const sev_color = {Critical:"#e74c3c",High:"#e67e22",Medium:"#f39c12",Low:"#27ae60"};

                let rows = hits.slice(0,8).map(h => `
                    <tr style="background:#fff;border-bottom:1px solid #f0f0f0;">
                        <td style="padding:7px 10px;font-size:12px;">${h.docname}</td>
                        <td style="padding:7px 10px;font-size:12px;">${h.anomaly_type}</td>
                        <td style="padding:7px 10px;text-align:center;">
                            <span style="background:${sev_color[h.severity]||"#999"};color:#fff;
                                         padding:2px 9px;border-radius:12px;font-size:11px;font-weight:600;">
                                ${h.severity}
                            </span>
                        </td>
                    </tr>`).join("");

                d.$wrapper.find(".scan-output").html(`
                    <div style="background:${ok?"#f0fdf4":"#fef9ec"};border-left:4px solid ${ok?"#27ae60":"#e67e22"};
                                padding:12px 16px;border-radius:4px;margin-bottom:14px;">
                        <span style="font-size:15px;font-weight:700;color:${ok?"#27ae60":"#e67e22"};">
                            ${ok ? "✅ No anomalies detected." : `⚠️ ${hits.length} anomaly(ies) found in <em>${scope[0]}</em>.`}
                        </span>
                        ${!ok ? "<br><small style='color:#888;'>Auto-raised as Audit Findings below.</small>" : ""}
                    </div>
                    ${rows ? `<table style="width:100%;border-collapse:collapse;font-size:12px;">
                        <thead><tr style="background:#2c3e50;color:#fff;">
                            <th style="padding:7px 10px;">Document</th>
                            <th style="padding:7px 10px;">Anomaly</th>
                            <th style="padding:7px 10px;text-align:center;">Severity</th>
                        </tr></thead><tbody>${rows}</tbody></table>
                        ${hits.length > 8 ? `<p style="font-size:11px;color:#888;margin-top:5px;">
                            …and ${hits.length-8} more. <a href="/app/audit-finding?audit_engagement=${frm.doc.name}">View all →</a></p>` : ""}` : ""}
                `).show();
                d.get_primary_btn().prop("disabled", false).html(__("🔄 Scan Again"));
                frm.reload_doc();
            }
        });
    });
    d.show();
}


// ── GL Assertion Dialog ─────────────────────────────────────────────────────
function _gl_assertions(frm) {
    const scope = (frm.doc.scope_doctypes || []).map(r => r.doctype_name).filter(Boolean);
    if (!scope.length) { frappe.msgprint(__("Add DocTypes to the scope first.")); return; }

    frappe.call({
        method:"ecclesia.api.gl_assertions.run_assertions_for_engagement",
        args:{ engagement_name: frm.doc.name, from_date: frm.doc.from_date,
               to_date: frm.doc.to_date, doctype_names: scope },
        freeze:true, freeze_message:"Running ISA 500 assertion tests…",
        callback(r) {
            const res = r.message || {};
            const d   = new frappe.ui.Dialog({ title:"⚖️ GL Assertion Results — ISA 500",
                size:"large", fields:[{fieldtype:"HTML",fieldname:"body"}] });

            const defs = [
                ["completeness",  "📋","Completeness",         "All transactions recorded?"],
                ["accuracy",      "🔢","Accuracy",             "Amounts match GL postings?"],
                ["existence",     "📌","Existence",            "GL entries have source docs?"],
                ["cutoff",        "✂️","Cutoff",              "Correct period classification?"],
                ["classification","🏷️","Classification",      "Correct account usage?"],
            ];
            const rows = defs.map(([k,ic,lb,ds]) => {
                const v   = res[k] || {passed:true, exceptions:[]};
                const exc = (v.exceptions||[]).length;
                const bg  = v.passed ? "#f0fdf4" : "#fef2f2";
                return `<tr style="background:${bg};">
                    <td style="padding:10px;font-size:18px;text-align:center;">${ic}</td>
                    <td style="padding:10px;">
                        <div style="font-weight:700;">${lb}</div>
                        <div style="font-size:11px;color:#888;">${ds}</div>
                    </td>
                    <td style="padding:10px;font-size:20px;text-align:center;">${v.passed?"✅":"❌"}</td>
                    <td style="padding:10px;font-weight:700;color:${v.passed?"#27ae60":"#e74c3c"};">
                        ${v.passed ? "Passed" : `${exc} exception(s)`}
                    </td>
                </tr>`;
            }).join("");

            const total_exc = defs.reduce((s,[k]) => s + ((res[k]?.exceptions||[]).length), 0);
            d.fields_dict.body.$wrapper.html(`
                <div style="background:${total_exc===0?"#f0fdf4":"#fef2f2"};border-left:4px solid ${total_exc===0?"#27ae60":"#e74c3c"};
                            padding:12px 16px;border-radius:4px;margin-bottom:14px;font-weight:700;
                            color:${total_exc===0?"#27ae60":"#e74c3c"};font-size:14px;">
                    ${total_exc===0 ? "✅ All 5 assertions passed — no exceptions." : `⚠️ ${total_exc} total exception(s) found across assertions.`}
                </div>
                <table style="width:100%;border-collapse:collapse;">
                    <thead><tr style="background:#2c3e50;color:#fff;">
                        <th style="padding:8px;width:40px;"></th>
                        <th style="padding:8px;text-align:left;">Assertion</th>
                        <th style="padding:8px;text-align:center;width:60px;">Pass/Fail</th>
                        <th style="padding:8px;text-align:left;">Result</th>
                    </tr></thead><tbody>${rows}</tbody>
                </table>
                <p style="font-size:11px;color:#888;margin-top:10px;">
                    Exceptions auto-raised as Audit Findings.
                    <a href="/app/audit-finding?audit_engagement=${frm.doc.name}" style="color:#2980b9;">View all →</a>
                </p>`);
            d.show();
            frm.reload_doc();
        }
    });
}

function flt(v) { return parseFloat(v) || 0; }



// Copyright (c) 2026, kunle Oduntan and contributors
//For license information, please see license.txt

// ╔══════════════════════════════════════════════════════════════════════╗
// ║  AUDIT SCOPE DOCTYPE  (child table)  ·  Ecclesia                     ║
// ╚══════════════════════════════════════════════════════════════════════╝

frappe.ui.form.on("Audit Scope DocType", {

	doctype_name(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.doctype_name) return;

		frappe.db.get_value(
			"Auditable DocType Registry",
			{ doctype_name: row.doctype_name },
			[
				"transaction_code", "risk_level", "sampling_method",
				"is_gl_posting", "is_active", "open_findings_count",
				"last_audit_date", "total_transactions_ytd",
				"recommended_sample_size", "audit_frequency",
			],
			val => {
				if (!val || !val.transaction_code) {
					// Not registered — clear the row and warn
					frappe.model.set_value(cdt, cdn, "doctype_name", "");
					frappe.msgprint({
						title:   "DocType Not Registered",
						message: `<b>${row.doctype_name}</b> is not in the Audit Universe yet.
						          <br><br>Go to <b>Auditable DocType Registry → New</b>, paste the
						          DocType's JSON, and Save. The system will register it automatically.`,
						indicator: "orange",
					});
					return;
				}

				if (!val.is_active) {
					frappe.show_alert({
						message: `⚠️ <b>${row.doctype_name}</b> is registered but marked <b>Inactive</b>.`,
						indicator: "orange",
					}, 6);
				}

				// Auto-populate scope row from registry
				frappe.model.set_value(cdt, cdn, "transaction_code", val.transaction_code);
				frappe.model.set_value(cdt, cdn, "risk_level",        val.risk_level);
				frappe.model.set_value(cdt, cdn, "sampling_method",   val.sampling_method);

				// Rich info alert
				const risk_icons = { Critical:"🔴", High:"🟠", Medium:"🟡", Low:"🟢" };
				const icon       = risk_icons[val.risk_level] || "📌";
				const gl_tag     = val.is_gl_posting ? " · 💳 GL-posting" : "";
				const last_tag   = val.last_audit_date
					? ` · Last audit: <b>${val.last_audit_date}</b>`
					: " · <b style='color:#e67e22;'>⚠️ Never audited</b>";
				const open_tag   = val.open_findings_count
					? ` · <span style="color:#e74c3c;">${val.open_findings_count} open finding(s)</span>`
					: "";
				const txn_tag    = val.total_transactions_ytd
					? ` · ${val.total_transactions_ytd.toLocaleString()} txns YTD` : "";

				frappe.show_alert({
					message: `${icon} <b>${row.doctype_name}</b> added — ${val.risk_level} risk${gl_tag}${last_tag}${open_tag}${txn_tag}`,
					indicator: val.risk_level === "Critical" ? "red"
					         : val.risk_level === "High"     ? "orange" : "blue",
				}, 7);
			}
		);
	},
});