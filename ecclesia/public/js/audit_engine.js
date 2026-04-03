/**
 * Universal Audit Engine — Global JavaScript
 * ============================================
 * This single file injects the Audit button into EVERY registered DocType's
 * List View and Form View dynamically — no per-DocType scripting needed.
 *
 * When a new DocType is registered, it automatically gets the audit button
 * on the next page load. No code changes required ever.
 */

frappe.provide("ecclesia");

// ─────────────────────────────────────────────────────────────────────────────
// Registry Cache — loaded once per session
// ─────────────────────────────────────────────────────────────────────────────

ecclesia.registry = null;
ecclesia.registry_loaded = false;

ecclesia.load_registry = function () {
    return new Promise((resolve) => {
        if (ecclesia.registry_loaded) {
            resolve(ecclesia.registry);
            return;
        }
        frappe.call({
            method: "ecclesia.api.registry.get_registered_doctypes",
            callback: function (r) {
                ecclesia.registry = r.message || {};
                ecclesia.registry_loaded = true;
                resolve(ecclesia.registry);
            }
        });
    });
};

ecclesia.is_registered = function (doctype) {
    return ecclesia.registry && ecclesia.registry[doctype];
};


// ─────────────────────────────────────────────────────────────────────────────
// List View Hook — inject "Audit" button
// ─────────────────────────────────────────────────────────────────────────────

$(document).on("app_ready", function () {
    ecclesia.load_registry().then(() => {
        // Patch ListView to inject button on render
        const original_refresh = frappe.views.ListView.prototype.refresh;
        frappe.views.ListView.prototype.refresh = function () {
            original_refresh.apply(this, arguments);
            ecclesia.inject_list_button(this);
        };
    });
});

ecclesia.inject_list_button = function (listview) {
    const doctype = listview && listview.doctype;
    if (!doctype || !ecclesia.is_registered(doctype)) return;
    if (listview.$page && listview.$page.find(".btn-audit-universal").length) return;

    const reg = ecclesia.registry[doctype];

    const btn = $(`
        <button class="btn btn-default btn-sm btn-audit-universal"
                style="margin-left:8px; border-color:#2c6fad; color:#2c6fad; font-weight:600;">
            <i class="fa fa-shield" style="margin-right:4px;"></i>Audit
            <span class="badge" style="background:#e74c3c; margin-left:4px; font-size:10px;">
                ${reg.open_findings || ''}
            </span>
        </button>
    `);

    btn.on("click", function () {
        const checked = listview.get_checked_items();
        if (checked.length === 0) {
            ecclesia.show_doctype_audit_panel(doctype, reg, listview);
        } else {
            ecclesia.show_record_audit_panel(doctype, reg, checked, listview);
        }
    });

    if (listview.$page) {
        listview.$page.find(".page-actions .standard-actions").prepend(btn);
    }
};


// ─────────────────────────────────────────────────────────────────────────────
// DocType-level Audit Panel (no records selected)
// ─────────────────────────────────────────────────────────────────────────────

ecclesia.show_doctype_audit_panel = function (doctype, reg, listview) {
    const d = new frappe.ui.Dialog({
        title: `<i class="fa fa-shield"></i> Audit — ${doctype}`,
        size: "large",
        fields: [
            {fieldtype: "HTML", fieldname: "panel_html"}
        ]
    });

    // Render summary card
    const html = `
        <div class="ua-panel">
            <div class="ua-header" style="background:#2c3e50; color:#fff; padding:16px; border-radius:6px; margin-bottom:16px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <h4 style="margin:0; color:#fff;">${doctype}</h4>
                        <small style="opacity:0.8;">Transaction Code: <b>${reg.transaction_code}</b></small>
                    </div>
                    <div style="text-align:right;">
                        <span class="badge ua-risk-${(reg.risk_level||'').toLowerCase()}" style="font-size:13px; padding:4px 10px;">
                            ${reg.risk_level || ''} Risk
                        </span>
                    </div>
                </div>
            </div>

            <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; margin-bottom:16px;">
                <div class="ua-stat-card">
                    <div class="ua-stat-value" style="color:#e74c3c;">${reg.open_findings || 0}</div>
                    <div class="ua-stat-label">Open Findings</div>
                </div>
                <div class="ua-stat-card">
                    <div class="ua-stat-value" style="color:#2980b9;">${reg.total_transactions_ytd || 0}</div>
                    <div class="ua-stat-label">Transactions YTD</div>
                </div>
                <div class="ua-stat-card">
                    <div class="ua-stat-value" style="color:#27ae60;">${reg.last_audit_opinion || 'Not Audited'}</div>
                    <div class="ua-stat-label">Last Opinion</div>
                </div>
            </div>

            <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:16px;">
                <div>
                    <p style="margin:2px 0;"><b>Classification:</b> ${reg.doctype_classification || '—'}</p>
                    <p style="margin:2px 0;"><b>GL Posting:</b> ${reg.is_gl_posting ? '✅ Yes' : '❌ No'}</p>
                    <p style="margin:2px 0;"><b>Sampling Method:</b> ${reg.sampling_method || '—'}</p>
                    <p style="margin:2px 0;"><b>Audit Frequency:</b> ${reg.audit_frequency || '—'}</p>
                </div>
                <div>
                    <p style="margin:2px 0;"><b>Financial Statement:</b> ${reg.financial_statement_line || 'N/A'}</p>
                    <p style="margin:2px 0;"><b>COSO Component:</b> ${reg.coso_component || '—'}</p>
                    <p style="margin:2px 0;"><b>Last Audited:</b> ${reg.last_audit_date || 'Never'}</p>
                    <p style="margin:2px 0;"><b>Materiality Basis:</b> ${reg.materiality_benchmark || '—'}</p>
                </div>
            </div>

            <div style="background:#fff8e1; border-left:4px solid #f39c12; padding:10px; border-radius:4px; margin-bottom:12px;">
                <b>🤖 AI Risk Summary</b><br>
                <small>${reg.ai_risk_summary || 'AI profile not yet generated.'}</small>
            </div>

            <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                <div style="background:#ffeaea; border-radius:4px; padding:10px;">
                    <b>🚩 Red Flags</b><br>
                    <small>${reg.ai_red_flags || '—'}</small>
                </div>
                <div style="background:#e8f5e9; border-radius:4px; padding:10px;">
                    <b>✓ Key Controls</b><br>
                    <small>${reg.ai_key_controls || '—'}</small>
                </div>
            </div>
        </div>
    `;

    d.fields_dict.panel_html.$wrapper.html(html);

    d.set_primary_action("➕ Raise Finding", function () {
        d.hide();
        ecclesia.open_finding_form(doctype, null, reg);
    });

    d.add_custom_action("📋 View Checklist", function () {
        frappe.set_route("List", "Audit Checklist", {doctype_name: doctype});
        d.hide();
    });

    d.add_custom_action("🔍 Run AI Anomaly Scan", function () {
        ecclesia.run_anomaly_scan(doctype, listview, d);
    });

    d.add_custom_action("📊 All Findings", function () {
        frappe.set_route("List", "Audit Finding", {reference_doctype: doctype});
        d.hide();
    });

    d.show();
};


// ─────────────────────────────────────────────────────────────────────────────
// Record-level Audit Panel (records selected in list)
// ─────────────────────────────────────────────────────────────────────────────

ecclesia.show_record_audit_panel = function (doctype, reg, checked_items, listview) {
    const d = new frappe.ui.Dialog({
        title: `Audit — ${checked_items.length} Record(s) Selected`,
        size: "large",
        fields: [
            {fieldtype: "HTML", fieldname: "records_html"},
            {fieldtype: "Section Break", label: "Raise Finding on Selected Records"},
            {
                fieldname: "finding_title", fieldtype: "Data",
                label: "Finding Title", reqd: 1
            },
            {
                fieldname: "risk_rating", fieldtype: "Select",
                label: "Risk Rating", reqd: 1,
                options: "\nCritical\nHigh\nMedium\nLow"
            },
            {
                fieldname: "finding_type", fieldtype: "Select",
                label: "Finding Type",
                options: "Control Deficiency\nSegregation of Duties\nUnauthorized Transaction\nPolicy Non-Compliance\nGL Posting Error\nCutoff Error\nDuplicate Transaction\nMissing Documentation\nApproval Bypass\nFraud Indicator\nStatistical Outlier\nOther"
            },
            {fieldname: "observation", fieldtype: "Text Editor", label: "Observation"},
            {fieldname: "corrective_action_suggested", fieldtype: "Text Editor", label: "Recommendation"},
        ]
    });

    // Show selected records
    const record_rows = checked_items.map(r =>
        `<tr><td><a href="/app/${frappe.router.slug(doctype)}/${r.name}" target="_blank">${r.name}</a></td>
         <td>${r.modified || ''}</td>
         <td>${r.owner || ''}</td></tr>`
    ).join("");

    d.fields_dict.records_html.$wrapper.html(`
        <div style="margin-bottom:12px;">
            <b>${checked_items.length} record(s) selected for audit finding:</b>
            <table class="table table-bordered table-sm" style="margin-top:8px;">
                <thead><tr><th>Document</th><th>Modified</th><th>Owner</th></tr></thead>
                <tbody>${record_rows}</tbody>
            </table>
        </div>
    `);

    d.set_primary_action("Raise Finding", function () {
        const vals = d.get_values();
        if (!vals) return;

        // Create finding for first selected record (others noted in observation)
        const primary = checked_items[0];
        const all_names = checked_items.map(r => r.name).join(", ");

        frappe.call({
            method: "ecclesia.api.findings.create_finding",
            args: {
                reference_doctype:          doctype,
                reference_name:             primary.name,
                finding_title:              vals.finding_title,
                risk_rating:                vals.risk_rating,
                finding_type:               vals.finding_type,
                observation:                vals.observation + (
                    checked_items.length > 1
                        ? `\n\nAffected records: ${all_names}`
                        : ""
                ),
                corrective_action_suggested: vals.corrective_action_suggested,
                transaction_code:            reg.transaction_code,
            },
            callback: function (r) {
                if (r.message) {
                    d.hide();
                    frappe.set_route("Form", "Audit Finding", r.message);
                    frappe.show_alert({
                        message: `Finding created: ${r.message}`,
                        indicator: "green"
                    });
                }
            }
        });
    });

    d.add_custom_action("🔍 AI Anomaly Check", function () {
        ecclesia.run_anomaly_scan_on_records(doctype, checked_items, reg, d);
    });

    d.show();
};


// ─────────────────────────────────────────────────────────────────────────────
// Open Finding Form (pre-populated)
// ─────────────────────────────────────────────────────────────────────────────

ecclesia.open_finding_form = function (doctype, docname, reg) {
    frappe.new_doc("Audit Finding", {
        reference_doctype: doctype,
        reference_name:    docname,
        transaction_code:  reg ? reg.transaction_code : "",
        finding_type:      "Control Deficiency",
    });
};


// ─────────────────────────────────────────────────────────────────────────────
// AI Anomaly Scanner
// ─────────────────────────────────────────────────────────────────────────────

ecclesia.run_anomaly_scan = function (doctype, listview, parent_dialog) {
    const scan_dialog = new frappe.ui.Dialog({
        title: `🤖 AI Anomaly Scan — ${doctype}`,
        fields: [
            {
                fieldname: "from_date", fieldtype: "Date",
                label: "From Date", reqd: 1,
                default: frappe.datetime.add_months(frappe.datetime.get_today(), -3)
            },
            {
                fieldname: "to_date", fieldtype: "Date",
                label: "To Date", reqd: 1,
                default: frappe.datetime.get_today()
            },
            {fieldtype: "HTML", fieldname: "results_html"}
        ]
    });

    scan_dialog.set_primary_action("Run Scan", function () {
        const vals = scan_dialog.get_values();
        if (!vals) return;

        scan_dialog.fields_dict.results_html.$wrapper.html(
            `<div style="text-align:center; padding:20px;">
                <i class="fa fa-spinner fa-spin fa-2x"></i>
                <p>AI is analysing ${doctype} records...</p>
             </div>`
        );

        frappe.call({
            method: "ecclesia.api.anomaly.run_scan",
            args: {
                doctype_name: doctype,
                from_date:    vals.from_date,
                to_date:      vals.to_date
            },
            callback: function (r) {
                const results = r.message || [];
                ecclesia.render_anomaly_results(
                    scan_dialog, results, doctype
                );
            }
        });
    });

    scan_dialog.show();
};

ecclesia.run_anomaly_scan_on_records = function (doctype, records, reg, parent_dialog) {
    frappe.call({
        method: "ecclesia.api.anomaly.run_scan_on_records",
        args: {
            doctype_name: doctype,
            record_names: records.map(r => r.name)
        },
        callback: function (r) {
            const results = r.message || [];
            if (results.length === 0) {
                frappe.show_alert({message: "✅ No anomalies detected in selected records", indicator: "green"});
            } else {
                frappe.show_alert({
                    message: `🚩 ${results.length} anomaly(ies) detected. Check findings list.`,
                    indicator: "orange"
                });
            }
        }
    });
};

ecclesia.render_anomaly_results = function (dialog, results, doctype) {
    if (results.length === 0) {
        dialog.fields_dict.results_html.$wrapper.html(`
            <div style="text-align:center; padding:20px; color:green;">
                <i class="fa fa-check-circle fa-3x"></i>
                <h4>No anomalies detected</h4>
                <p>AI analysis found no significant anomalies in the selected period.</p>
            </div>
        `);
        return;
    }

    const rows = results.map(a => `
        <tr>
            <td><a href="/app/${frappe.router.slug(doctype)}/${a.docname}" target="_blank">${a.docname}</a></td>
            <td>${a.anomaly_type}</td>
            <td><span class="badge ua-risk-${a.severity.toLowerCase()}">${a.severity}</span></td>
            <td style="max-width:300px; font-size:12px;">${a.description}</td>
            <td>
                <button class="btn btn-xs btn-primary btn-raise-finding"
                        data-docname="${a.docname}"
                        data-type="${a.anomaly_type}"
                        data-severity="${a.severity}"
                        data-desc="${a.description}">
                    Raise Finding
                </button>
            </td>
        </tr>
    `).join("");

    dialog.fields_dict.results_html.$wrapper.html(`
        <div>
            <div style="background:#fff3cd; border:1px solid #ffc107; border-radius:4px; padding:10px; margin-bottom:12px;">
                🚩 <b>${results.length} anomaly(ies) detected</b> by AI analysis
            </div>
            <table class="table table-bordered table-hover" style="font-size:13px;">
                <thead>
                    <tr>
                        <th>Document</th><th>Anomaly Type</th>
                        <th>Severity</th><th>Description</th><th>Action</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        </div>
    `);

    // Bind raise finding buttons
    dialog.fields_dict.results_html.$wrapper.find(".btn-raise-finding").on("click", function () {
        const btn = $(this);
        frappe.call({
            method: "ecclesia.api.findings.create_finding",
            args: {
                reference_doctype: doctype,
                reference_name:    btn.data("docname"),
                finding_title:     `AI Flag: ${btn.data("type")} — ${btn.data("docname")}`,
                risk_rating:       btn.data("severity"),
                finding_type:      btn.data("type"),
                observation:       btn.data("desc"),
                source:            "AI Auto-Detection",
            },
            callback: function (r) {
                if (r.message) {
                    btn.text("✅ Created").prop("disabled", true);
                    frappe.show_alert({message: "Finding created", indicator: "green"});
                }
            }
        });
    });
};


// ─────────────────────────────────────────────────────────────────────────────
// Form View Hook — Audit button on individual document forms
// ─────────────────────────────────────────────────────────────────────────────

frappe.ui.form.on("*", {
    refresh: function (frm) {
        ecclesia.load_registry().then(() => {
            if (!ecclesia.is_registered(frm.doctype)) return;
            if (frm.is_new()) return;

            const reg = ecclesia.registry[frm.doctype];

            frm.add_custom_button(
                '<i class="fa fa-shield"></i> Audit This Record',
                function () {
                    ecclesia.show_form_audit_panel(frm, reg);
                },
                "Audit"
            );

            frm.add_custom_button(
                "Audit History",
                function () {
                    frappe.set_route("List", "Audit Finding", {
                        reference_doctype: frm.doctype,
                        reference_name:    frm.doc.name
                    });
                },
                "Audit"
            );
        });
    }
});

ecclesia.show_form_audit_panel = function (frm, reg) {
    // Load existing findings for this record
    frappe.call({
        method: "ecclesia.api.findings.get_findings_for_record",
        args: {
            reference_doctype: frm.doctype,
            reference_name:    frm.doc.name
        },
        callback: function (r) {
            const findings = r.message || [];
            const d = new frappe.ui.Dialog({
                title: `Audit — ${frm.doctype}: ${frm.doc.name}`,
                size: "large",
                fields: [{fieldtype: "HTML", fieldname: "content"}]
            });

            const findings_html = findings.length > 0
                ? findings.map(f => `
                    <tr>
                        <td><a href="/app/audit-finding/${f.name}">${f.name}</a></td>
                        <td>${f.finding_title}</td>
                        <td><span class="badge ua-risk-${(f.risk_rating||'').toLowerCase()}">${f.risk_rating}</span></td>
                        <td>${f.status}</td>
                    </tr>`).join("")
                : `<tr><td colspan="4" style="text-align:center; color:#888;">No findings yet</td></tr>`;

            d.fields_dict.content.$wrapper.html(`
                <div style="margin-bottom:16px;">
                    <div style="background:#2c3e50; color:#fff; padding:12px; border-radius:6px; margin-bottom:12px;">
                        <b>${frm.doctype}</b> &nbsp;|&nbsp; ${frm.doc.name}
                        &nbsp;|&nbsp; Code: <b>${reg.transaction_code}</b>
                        &nbsp;|&nbsp; <span class="badge ua-risk-${(reg.risk_level||'').toLowerCase()}">${reg.risk_level}</span>
                    </div>
                    <h5>Existing Findings</h5>
                    <table class="table table-bordered table-sm">
                        <thead><tr><th>Finding</th><th>Title</th><th>Risk</th><th>Status</th></tr></thead>
                        <tbody>${findings_html}</tbody>
                    </table>
                </div>
            `);

            d.set_primary_action("Raise New Finding", function () {
                d.hide();
                ecclesia.open_finding_form(frm.doctype, frm.doc.name, reg);
            });

            d.add_custom_action("AI Anomaly Check", function () {
                frappe.call({
                    method: "ecclesia.api.anomaly.run_scan_on_records",
                    args: {
                        doctype_name: frm.doctype,
                        record_names: [frm.doc.name]
                    },
                    callback: function (r) {
                        const results = r.message || [];
                        frappe.show_alert({
                            message: results.length > 0
                                ? `🚩 ${results.length} anomaly(ies) detected`
                                : "✅ No anomalies detected",
                            indicator: results.length > 0 ? "orange" : "green"
                        });
                    }
                });
            });

            d.show();
        }
    });
};
