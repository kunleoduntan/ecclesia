frappe.pages["data-wipe-utility"].on_page_load = function (wrapper) {
    frappe.ui.make_app_page({
        parent: wrapper,
        title: __("Data Wipe Center"),
        single_column: true,
    });

    new DataWipeUtility(wrapper);
};

class DataWipeUtility {
    constructor(wrapper) {
        this.wrapper = wrapper;
        this.page = wrapper.page;
        this.company = null;
        this.all_doctypes = [];
        this.selected_doctypes = new Set();
        this.mode = "all";
        this.theme = localStorage.getItem("dwu-theme") || "ocean";
        this.running = false;

        this.render();
        this.setup_company_field();
        this.bind_events();
    }

    render() {
        $(this.wrapper).find(".page-content").html(`
            <div class="dwu-wrap" data-theme="${frappe.utils.escape_html(this.theme)}">
                <div class="dwu-hero">
                    <div>
                        <div class="dwu-eyebrow">ERPNext Data Administration</div>
                        <h1>Data Wipe Center</h1>
                        <p>Safely reset company business data with preview, verification and detailed failure reporting.</p>
                    </div>
                    <div class="dwu-theme-box">
                        <span>Theme</span>
                        <select id="dwu-theme">
                            <option value="ocean">Ocean</option>
                            <option value="royal">Royal</option>
                            <option value="emerald">Emerald</option>
                            <option value="violet">Violet</option>
                            <option value="rose">Rose</option>
                            <option value="amber">Amber</option>
                            <option value="dark">Dark</option>
                        </select>
                    </div>
                </div>

                <div class="dwu-grid">
                    <section class="dwu-card dwu-card-company">
                        <div class="dwu-step"><span>01</span> Company</div>
                        <div class="dwu-title">Choose the company to reset</div>
                        <div id="dwu-company-field" class="dwu-company-field"></div>
                        <div class="dwu-note">Only records belonging to the selected company are targeted. System configuration remains protected.</div>
                    </section>

                    <section class="dwu-card">
                        <div class="dwu-step"><span>02</span> Scope</div>
                        <div class="dwu-scope-grid">
                            <button class="dwu-scope active" data-mode="all">
                                <b>All Company Data</b><small>Transactions and company-owned records</small>
                            </button>
                            <button class="dwu-scope" data-mode="selected">
                                <b>Selected DocTypes</b><small>Choose exactly what to remove</small>
                            </button>
                        </div>
                    </section>

                    <section class="dwu-card" id="step-picker" style="display:none;">
                        <div class="dwu-step"><span>03</span> DocTypes</div>
                        <div class="dwu-toolbar">
                            <input id="dwu-search" placeholder="Search document types...">
                            <button class="dwu-mini" id="dwu-select-all">Select visible</button>
                            <button class="dwu-mini" id="dwu-clear-all">Clear</button>
                        </div>
                        <div id="dwu-doctype-list" class="dwu-doctype-list">
                            <div class="dwu-empty">Select a company to load data.</div>
                        </div>
                        <div id="dwu-selection-summary" class="dwu-summary" style="display:none;"></div>
                    </section>

                    <section class="dwu-card dwu-danger">
                        <div class="dwu-step"><span>04</span> Review & Execute</div>
                        <div class="dwu-warning">
                            <div class="dwu-warning-icon">!</div>
                            <div>
                                <b>This is a destructive operation.</b>
                                <span>Preview first. A real wipe permanently removes targeted records. Protected system records are never deleted.</span>
                            </div>
                        </div>

                        <div class="dwu-actions">
                            <label class="dwu-confirm">
                                <input type="checkbox" id="dwu-confirm-check">
                                <span>I understand that this operation cannot be undone.</span>
                            </label>
                            <button id="dwu-dry-run-btn" class="dwu-btn secondary">Preview Data</button>
                            <button id="dwu-execute-btn" class="dwu-btn danger" disabled>Wipe Data</button>
                        </div>
                    </section>

                    <section class="dwu-card" id="step-results" style="display:none;">
                        <div class="dwu-results-head">
                            <div>
                                <div class="dwu-step"><span>05</span> Verification</div>
                                <div class="dwu-title">Operation results</div>
                            </div>
                            <button class="dwu-mini" id="dwu-refresh">Refresh Counts</button>
                        </div>
                        <div id="dwu-results-body"></div>
                    </section>
                </div>
            </div>

            <style>
                .dwu-wrap {
                    --p:#2563eb; --p2:#1d4ed8; --soft:#eff6ff;
                    --ok:#16a34a; --danger:#dc2626; --warn:#d97706;
                    --card:var(--card-bg); --bg:var(--bg-color);
                    --text:var(--text-color); --muted:var(--text-muted);
                    --border:var(--border-color);
                    max-width:1120px;margin:0 auto;padding:24px 16px 48px;color:var(--text);
                }
                .dwu-wrap[data-theme="royal"]{--p:#7c3aed;--p2:#6d28d9;--soft:#f5f3ff}
                .dwu-wrap[data-theme="emerald"]{--p:#059669;--p2:#047857;--soft:#ecfdf5}
                .dwu-wrap[data-theme="violet"]{--p:#8b5cf6;--p2:#7c3aed;--soft:#f5f3ff}
                .dwu-wrap[data-theme="rose"]{--p:#e11d48;--p2:#be123c;--soft:#fff1f2}
                .dwu-wrap[data-theme="amber"]{--p:#d97706;--p2:#b45309;--soft:#fffbeb}
                .dwu-wrap[data-theme="dark"]{--p:#60a5fa;--p2:#3b82f6;--soft:#172033}
                .dwu-hero{display:flex;justify-content:space-between;gap:24px;align-items:center;padding:28px;border-radius:20px;
                    background:linear-gradient(135deg,var(--soft),var(--card));border:1px solid var(--border);margin-bottom:18px;
                    box-shadow:0 10px 30px rgba(0,0,0,.05)}
                .dwu-eyebrow{font-size:11px;text-transform:uppercase;letter-spacing:.14em;font-weight:800;color:var(--p)}
                .dwu-hero h1{margin:6px 0;font-size:30px;letter-spacing:-.03em}.dwu-hero p{margin:0;color:var(--muted)}
                .dwu-theme-box{display:flex;flex-direction:column;gap:6px;font-size:11px;color:var(--muted)}
                #dwu-theme{border:1px solid var(--border);border-radius:10px;padding:8px 12px;background:var(--card);color:var(--text)}
                .dwu-grid{display:flex;flex-direction:column;gap:16px}.dwu-card{background:var(--card);border:1px solid var(--border);
                    border-radius:16px;padding:20px;box-shadow:0 5px 20px rgba(0,0,0,.035)}
                .dwu-step{font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);font-weight:800;margin-bottom:10px}
                .dwu-step span{display:inline-flex;align-items:center;justify-content:center;width:25px;height:25px;border-radius:50%;
                    background:var(--soft);color:var(--p);margin-right:7px}
                .dwu-title{font-size:18px;font-weight:750;margin-bottom:14px}.dwu-company-field{max-width:420px}
                .dwu-note{font-size:12px;color:var(--muted);margin-top:10px}.dwu-scope-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
                .dwu-scope{text-align:left;padding:18px;border:1.5px solid var(--border);background:var(--card);color:var(--text);border-radius:13px;cursor:pointer}
                .dwu-scope b,.dwu-scope small{display:block}.dwu-scope small{margin-top:5px;color:var(--muted)}.dwu-scope:hover,.dwu-scope.active{border-color:var(--p);background:var(--soft)}
                .dwu-scope.active b{color:var(--p)}.dwu-toolbar{display:flex;gap:8px;margin-bottom:10px}.dwu-toolbar input{flex:1}
                .dwu-toolbar input,#dwu-search{border:1px solid var(--border);background:var(--card);color:var(--text);border-radius:10px;padding:9px 12px}
                .dwu-mini{border:1px solid var(--border);background:var(--card);color:var(--text);border-radius:9px;padding:8px 11px;cursor:pointer}
                .dwu-mini:hover{border-color:var(--p);color:var(--p)}.dwu-doctype-list{max-height:390px;overflow:auto;border:1px solid var(--border);border-radius:12px}
                .dwu-dt-group{padding:9px 12px;background:var(--bg);color:var(--muted);font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.08em;position:sticky;top:0}
                .dwu-dt-row{display:flex;gap:10px;align-items:center;padding:10px 12px;border-bottom:1px solid var(--border);cursor:pointer}
                .dwu-dt-row:hover,.dwu-dt-row.checked{background:var(--soft)}.dwu-dt-name{flex:1;font-weight:600}.dwu-dt-count{font-size:11px;color:var(--muted)}
                .dwu-summary{margin-top:10px;padding:9px 12px;background:var(--soft);color:var(--p);border-radius:9px;font-size:12px;font-weight:700}
                .dwu-warning{display:flex;gap:12px;padding:13px 15px;border-radius:12px;background:#fff7ed;border:1px solid #fed7aa;color:#9a3412}
                [data-theme="dark"] .dwu-warning{background:#302414;color:#fdba74;border-color:#6b4a20}
                .dwu-warning-icon{width:25px;height:25px;border-radius:50%;background:var(--warn);color:white;text-align:center;line-height:25px;font-weight:800}
                .dwu-warning span{display:block;margin-top:3px;font-size:12px}.dwu-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:16px}
                .dwu-confirm{display:flex;gap:8px;align-items:center;flex:1;font-size:12px}.dwu-btn{border:0;border-radius:10px;padding:10px 18px;font-weight:750;cursor:pointer}
                .dwu-btn.secondary{background:var(--soft);color:var(--p)}.dwu-btn.danger{background:var(--danger);color:white}.dwu-btn:disabled{opacity:.4;cursor:not-allowed}
                .dwu-results-head{display:flex;justify-content:space-between;align-items:center}.dwu-result-summary{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:12px 0}
                .dwu-stat{padding:15px;border-radius:12px;background:var(--soft)}.dwu-stat b{display:block;font-size:20px}.dwu-stat span{font-size:11px;color:var(--muted)}
                .dwu-result-row{display:flex;gap:12px;align-items:center;padding:11px 4px;border-bottom:1px solid var(--border);font-size:12px}
                .dwu-result-row .name{flex:1;font-weight:650}.ok{color:var(--ok);font-weight:750}.partial{color:var(--warn);font-weight:750}.err{color:var(--danger);font-weight:750}.skip{color:var(--muted);font-weight:700}
                .dwu-empty{padding:30px;text-align:center;color:var(--muted)}
                @media(max-width:700px){.dwu-hero{flex-direction:column;align-items:flex-start}.dwu-scope-grid{grid-template-columns:1fr}.dwu-result-summary{grid-template-columns:1fr 1fr}.dwu-toolbar{flex-wrap:wrap}.dwu-toolbar input{min-width:100%}}
            </style>
        `);
        $("#dwu-theme").val(this.theme);
    }

    setup_company_field() {
        this.company_control = frappe.ui.form.make_control({
            parent: $(this.wrapper).find("#dwu-company-field"),
            df: {
                fieldtype: "Link", fieldname: "company", options: "Company",
                label: __("Company"), reqd: 1, placeholder: __("Select Company"),
                change: () => {
                    this.company = this.company_control.get_value();
                    this.on_company_change();
                }
            },
            render_input: true
        });
        this.company_control.refresh();
    }

    bind_events() {
        const $root = $(this.wrapper).find(".dwu-wrap");

        $root.on("change", "#dwu-theme", e => {
            this.theme = $(e.currentTarget).val();
            localStorage.setItem("dwu-theme", this.theme);
            $root.attr("data-theme", this.theme);
        });

        $root.on("click", ".dwu-scope", e => {
            $root.find(".dwu-scope").removeClass("active");
            $(e.currentTarget).addClass("active");
            this.mode = $(e.currentTarget).data("mode");
            $("#step-picker").toggle(this.mode === "selected");
            if (this.mode === "selected" && this.company && !this.all_doctypes.length) this.load_doctypes();
            if (this.mode === "all") this.selected_doctypes.clear();
            this.update_summary();
        });

        $root.on("input", "#dwu-search", e => {
            const q = String($(e.currentTarget).val() || "").toLowerCase();
            $root.find(".dwu-dt-row").each(function () {
                $(this).toggle($(this).find(".dwu-dt-name").text().toLowerCase().includes(q));
            });
        });

        $root.on("click", "#dwu-select-all", () => {
            $root.find(".dwu-dt-row:visible input").prop("checked", true).trigger("change");
        });
        $root.on("click", "#dwu-clear-all", () => {
            $root.find(".dwu-dt-row input").prop("checked", false).trigger("change");
        });
        $root.on("change", ".dwu-dt-row input", e => {
            const cb = $(e.currentTarget), dt = cb.val();
            if (cb.is(":checked")) { this.selected_doctypes.add(dt); cb.closest(".dwu-dt-row").addClass("checked"); }
            else { this.selected_doctypes.delete(dt); cb.closest(".dwu-dt-row").removeClass("checked"); }
            this.update_summary();
        });
        $root.on("click", ".dwu-dt-row", e => {
            if ($(e.target).is("input")) return;
            $(e.currentTarget).find("input").trigger("click");
        });
        $root.on("change", "#dwu-confirm-check", e => {
            $("#dwu-execute-btn").prop("disabled", !$(e.currentTarget).is(":checked") || this.running);
        });
        $root.on("click", "#dwu-dry-run-btn", () => this.run(true));
        $root.on("click", "#dwu-execute-btn", () => {
            if (!this.company) return frappe.msgprint(__("Please select a Company."));
            frappe.confirm(
                __("This will permanently delete targeted business data for {0}. Continue?", [this.company]),
                () => this.run(false)
            );
        });
        $root.on("click", "#dwu-refresh", () => this.load_doctypes());
    }

    on_company_change() {
        this.all_doctypes = [];
        this.selected_doctypes.clear();
        $(".dwu-wrap").toggleClass("dwu-locked", !this.company);
        if (this.company) this.load_doctypes();
        else $("#dwu-doctype-list").html('<div class="dwu-empty">Select a company to load data.</div>');
        this.update_summary();
    }

    load_doctypes() {
        if (!this.company) return;
        $("#dwu-doctype-list").html('<div class="dwu-empty">Loading company data...</div>');
        frappe.call({
            method: "ecclesia.ecclesia.page.data_wipe_utility.wipe_api.get_company_doctypes",
            args: { company: this.company },
            callback: r => {
                this.all_doctypes = r.message || [];
                this.render_doctype_list();
            }
        });
    }

    render_doctype_list() {
        const $list = $("#dwu-doctype-list").empty();
        if (!this.all_doctypes.length) {
            $list.html('<div class="dwu-empty">No company-owned records were found.</div>');
            return;
        }
        const groups = {};
        this.all_doctypes.forEach(d => (groups[d.module] ||= []).push(d));
        Object.keys(groups).sort().forEach(module => {
            $list.append(`<div class="dwu-dt-group">${frappe.utils.escape_html(module)}</div>`);
            groups[module].forEach(d => {
                const checked = this.selected_doctypes.has(d.doctype);
                $list.append(`
                    <div class="dwu-dt-row ${checked ? "checked" : ""}">
                        <input type="checkbox" value="${frappe.utils.escape_html(d.doctype)}" ${checked ? "checked" : ""}>
                        <span class="dwu-dt-name">${frappe.utils.escape_html(d.doctype)}</span>
                        <span class="dwu-dt-count">${Number(d.count || 0).toLocaleString()}</span>
                    </div>
                `);
            });
        });
    }

    update_summary() {
        const $s = $("#dwu-selection-summary");
        if (this.mode === "selected" && this.selected_doctypes.size) {
            $s.show().text(`${this.selected_doctypes.size} DocType(s) selected`);
        } else $s.hide();
    }

    get_targets() {
        return this.mode === "all"
            ? this.all_doctypes.map(d => d.doctype)
            : Array.from(this.selected_doctypes);
    }

    run(dry_run) {
        if (this.running) return;
        if (!this.company) return frappe.msgprint(__("Please select a Company."));
        const doctypes = this.get_targets();
        if (!doctypes.length) return frappe.msgprint(__("No company data was found or selected."));

        this.running = true;
        $("#dwu-dry-run-btn").prop("disabled", true).text(dry_run ? __("Previewing...") : __("Working..."));
        $("#dwu-execute-btn").prop("disabled", true);
        $("#step-results").show();
        $("#dwu-results-body").html('<div class="dwu-empty">Processing. Please wait...</div>');

        frappe.call({
            method: "ecclesia.ecclesia.page.data_wipe_utility.wipe_api.execute_wipe",
            args: { doctypes: JSON.stringify(doctypes), company: this.company, dry_run: dry_run ? 1 : 0 },
            freeze: true,
            freeze_message: dry_run ? __("Building preview...") : __("Deleting company data and verifying results..."),
            callback: r => {
                this.render_results(r.message || {}, dry_run);
                this.running = false;
                $("#dwu-dry-run-btn").prop("disabled", false).text(__("Preview Data"));
                $("#dwu-execute-btn").prop("disabled", !$("#dwu-confirm-check").is(":checked"));
            },
            error: () => {
                this.running = false;
                $("#dwu-results-body").html('<div class="dwu-empty err">The server operation failed. Check the Error Log.</div>');
                $("#dwu-dry-run-btn").prop("disabled", false).text(__("Preview Data"));
                $("#dwu-execute-btn").prop("disabled", !$("#dwu-confirm-check").is(":checked"));
            }
        });
    }

    render_results(data, dry_run) {
        const results = data.results || [];
        const total = Number(data.total_deleted || 0);
        const remaining = Number(data.total_remaining || 0);
        const failed = Number(data.total_failed || 0);
        const attempted = Number(data.total_targeted || 0);

        let html = `
            <div class="dwu-result-summary">
                <div class="dwu-stat"><b>${attempted.toLocaleString()}</b><span>Targeted</span></div>
                <div class="dwu-stat"><b>${total.toLocaleString()}</b><span>${dry_run ? "Would delete" : "Deleted"}</span></div>
                <div class="dwu-stat"><b>${remaining.toLocaleString()}</b><span>Remaining</span></div>
                <div class="dwu-stat"><b>${failed.toLocaleString()}</b><span>Failed</span></div>
            </div>
        `;

        if (!dry_run && remaining === 0 && failed === 0)
            html += `<div class="dwu-summary" style="color:var(--ok)">✓ Company data wipe completed and verified.</div>`;
        else if (!dry_run)
            html += `<div class="dwu-summary" style="color:var(--danger)">⚠ Wipe incomplete. Review the failure details below.</div>`;

        results.forEach(r => {
            const cls = r.status === "success" ? "ok" :
                        r.status === "partial" ? "partial" :
                        r.status === "error" ? "err" : "skip";
            html += `<div class="dwu-result-row">
                <span class="name">${frappe.utils.escape_html(r.doctype)}</span>
                <span class="${cls}">${frappe.utils.escape_html(r.status_label || r.status || "")}</span>
                <span>${Number(r.deleted || 0).toLocaleString()} deleted</span>
                <span>${Number(r.remaining || 0).toLocaleString()} remaining</span>
            </div>`;
            if (r.errors && r.errors.length) {
                html += `<details style="padding:8px 4px;color:var(--danger);font-size:11px">
                    <summary>${r.errors.length} failure(s)</summary>
                    ${r.errors.map(x => `<div>${frappe.utils.escape_html(x)}</div>`).join("")}
                </details>`;
            }
        });
        $("#dwu-results-body").html(html);
    }
}
