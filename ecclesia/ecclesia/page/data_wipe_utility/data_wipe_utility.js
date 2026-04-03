

frappe.pages["data-wipe-utility"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Data Wipe Utility"),
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
		this.mode = "all"; // 'all' | 'selected'

		this._setup_toolbar();
		this._render_shell();
		this._bind_events();
	}

	// ── Toolbar ──────────────────────────────
	_setup_toolbar() {
		this.company_field = this.page.add_field({
			fieldname: "company",
			fieldtype: "Link",
			options: "Company",
			label: __("Company"),
			placeholder: __("Filter by Company (optional)"),
			change: () => {
				this.company = this.company_field.get_value();
				this._load_doctypes();
			},
		});
	}

	// ── Shell HTML ───────────────────────────
	_render_shell() {
		$(this.wrapper).find(".page-content").html(`
      <div class="dwu-wrap">

        <!-- Step 1: Mode selector -->
        <div class="dwu-card" id="step-mode">
          <div class="dwu-step-label">Step 1 — Select scope</div>
          <div class="dwu-mode-row">
            <button class="dwu-mode-btn active" data-mode="all">
              <span class="dwu-mode-icon">&#9776;</span>
              <span>All submittable documents</span>
            </button>
            <button class="dwu-mode-btn" data-mode="selected">
              <span class="dwu-mode-icon">&#9635;</span>
              <span>Selected document types</span>
            </button>
          </div>
        </div>

        <!-- Step 2: Doctype picker (shown for 'selected' mode) -->
        <div class="dwu-card" id="step-picker" style="display:none;">
          <div class="dwu-step-label">Step 2 — Choose document types</div>
          <div class="dwu-search-row">
            <input type="text" id="dwu-search" placeholder="Search document types…" />
            <button id="dwu-select-all" class="dwu-link-btn">Select all</button>
            <button id="dwu-clear-all" class="dwu-link-btn">Clear all</button>
          </div>
          <div id="dwu-doctype-list" class="dwu-doctype-list">
            <div class="dwu-loading">Loading document types…</div>
          </div>
          <div id="dwu-selection-summary" class="dwu-summary-bar" style="display:none;"></div>
        </div>

        <!-- Step 3: Confirm & Execute -->
        <div class="dwu-card dwu-danger-card" id="step-confirm">
          <div class="dwu-step-label">Step 3 — Execute wipe</div>
          <div class="dwu-warning-box">
            <div class="dwu-warning-icon">&#9888;</div>
            <div>
              <strong>This operation is irreversible.</strong>
              All submitted documents will be cancelled and permanently deleted.
              Attached files will be <em>unlinked</em> (not deleted from disk).
              The <strong>Document Audit Log</strong> is never affected.
            </div>
          </div>
          <div class="dwu-confirm-row">
            <label class="dwu-confirm-label">
              <input type="checkbox" id="dwu-confirm-check" />
              I understand this action cannot be undone
            </label>
            <button id="dwu-dry-run-btn" class="dwu-btn dwu-btn-secondary">
              Preview (dry run)
            </button>
            <button id="dwu-execute-btn" class="dwu-btn dwu-btn-danger" disabled>
              Wipe Data
            </button>
          </div>
        </div>

        <!-- Results panel -->
        <div class="dwu-card" id="step-results" style="display:none;">
          <div class="dwu-step-label">Results</div>
          <div id="dwu-results-body"></div>
        </div>

      </div>

      <style>
        .dwu-wrap { padding: 1.5rem 0; max-width: 860px; display: flex; flex-direction: column; gap: 1rem; }
        .dwu-card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: var(--border-radius-md); padding: 1.25rem 1.5rem; }
        .dwu-danger-card { border-color: #e04a4a33; }
        .dwu-step-label { font-size: 11px; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; color: var(--text-muted); margin-bottom: 1rem; }

        /* Mode buttons */
        .dwu-mode-row { display: flex; gap: .75rem; }
        .dwu-mode-btn { flex: 1; display: flex; align-items: center; gap: .75rem; padding: .75rem 1rem; border: 1.5px solid var(--border-color); border-radius: var(--border-radius-md); background: var(--card-bg); cursor: pointer; font-size: 14px; transition: border-color .15s, background .15s; }
        .dwu-mode-btn:hover { border-color: var(--blue-400, #4f93ce); background: var(--blue-50, #eef5fb); }
        .dwu-mode-btn.active { border-color: var(--blue-500, #2490ef); background: var(--blue-50, #eef5fb); color: var(--blue-600, #1e6faf); font-weight: 600; }
        .dwu-mode-icon { font-size: 18px; }

        /* Search row */
        .dwu-search-row { display: flex; align-items: center; gap: .5rem; margin-bottom: .75rem; }
        #dwu-search { flex: 1; padding: .4rem .75rem; border: 1px solid var(--border-color); border-radius: var(--border-radius-md); font-size: 13px; background: var(--input-bg); color: var(--text-color); }
        .dwu-link-btn { background: none; border: none; color: var(--blue-500, #2490ef); font-size: 13px; cursor: pointer; padding: 0 .25rem; }
        .dwu-link-btn:hover { text-decoration: underline; }

        /* Doctype list */
        .dwu-doctype-list { max-height: 320px; overflow-y: auto; border: 1px solid var(--border-color); border-radius: var(--border-radius-md); }
        .dwu-dt-row { display: flex; align-items: center; gap: .75rem; padding: .5rem .75rem; border-bottom: 1px solid var(--border-color); font-size: 13px; cursor: pointer; transition: background .1s; }
        .dwu-dt-row:last-child { border-bottom: none; }
        .dwu-dt-row:hover { background: var(--blue-50, #eef5fb); }
        .dwu-dt-row.checked { background: var(--blue-50, #eef5fb); }
        .dwu-dt-row input[type=checkbox] { margin: 0; cursor: pointer; }
        .dwu-dt-name { flex: 1; font-weight: 500; }
        .dwu-dt-module { font-size: 11px; color: var(--text-muted); }
        .dwu-dt-count { font-size: 12px; background: var(--bg-color); border: 1px solid var(--border-color); border-radius: 999px; padding: 1px 8px; color: var(--text-muted); min-width: 40px; text-align: center; }
        .dwu-dt-group { padding: .4rem .75rem; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .05em; background: var(--bg-color); color: var(--text-muted); border-bottom: 1px solid var(--border-color); }
        .dwu-loading { padding: 2rem; text-align: center; color: var(--text-muted); font-size: 13px; }

        /* Summary bar */
        .dwu-summary-bar { margin-top: .75rem; padding: .5rem .75rem; background: var(--blue-50, #eef5fb); border-radius: var(--border-radius-md); font-size: 13px; color: var(--blue-600, #1e6faf); }

        /* Warning box */
        .dwu-warning-box { display: flex; gap: .75rem; align-items: flex-start; padding: .75rem 1rem; background: #fff8e1; border: 1px solid #ffe082; border-radius: var(--border-radius-md); font-size: 13px; color: #5d4037; margin-bottom: 1rem; }
        .dwu-warning-icon { font-size: 20px; line-height: 1; margin-top: 1px; }

        /* Confirm row */
        .dwu-confirm-row { display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; }
        .dwu-confirm-label { display: flex; align-items: center; gap: .5rem; font-size: 13px; cursor: pointer; flex: 1; min-width: 200px; }

        /* Buttons */
        .dwu-btn { padding: .45rem 1.25rem; border-radius: var(--border-radius-md); font-size: 13px; font-weight: 600; border: 1.5px solid transparent; cursor: pointer; transition: opacity .15s; }
        .dwu-btn:disabled { opacity: .4; cursor: not-allowed; }
        .dwu-btn-secondary { background: var(--card-bg); border-color: var(--border-color); color: var(--text-color); }
        .dwu-btn-secondary:hover:not(:disabled) { background: var(--bg-color); }
        .dwu-btn-danger { background: #e53935; color: #fff; border-color: #c62828; }
        .dwu-btn-danger:hover:not(:disabled) { background: #c62828; }

        /* Results */
        .dwu-result-row { display: flex; align-items: center; gap: .75rem; padding: .45rem .25rem; border-bottom: 1px solid var(--border-color); font-size: 13px; }
        .dwu-result-row:last-child { border-bottom: none; }
        .dwu-status-ok { color: #2e7d32; font-weight: 600; }
        .dwu-status-err { color: #c62828; font-weight: 600; }
        .dwu-status-dry { color: #1565c0; font-weight: 600; }
        .dwu-result-summary { padding: .75rem; margin-bottom: .75rem; border-radius: var(--border-radius-md); font-weight: 600; text-align: center; }
        .dwu-result-ok { background: #e8f5e9; color: #1b5e20; }
        .dwu-result-dry { background: #e3f2fd; color: #0d47a1; }
        .dwu-result-err { background: #ffebee; color: #b71c1c; }

        .dwu-spinner { display: inline-block; width: 14px; height: 14px; border: 2px solid #ccc; border-top-color: #2490ef; border-radius: 50%; animation: dwu-spin .6s linear infinite; vertical-align: middle; margin-right: 6px; }
        @keyframes dwu-spin { to { transform: rotate(360deg); } }
      </style>
    `);
	}

	// ── Events ───────────────────────────────
	_bind_events() {
		const $wrap = $(this.wrapper).find(".page-content");

		// Mode toggle
		$wrap.on("click", ".dwu-mode-btn", (e) => {
			const btn = $(e.currentTarget);
			$wrap.find(".dwu-mode-btn").removeClass("active");
			btn.addClass("active");
			this.mode = btn.data("mode");

			if (this.mode === "selected") {
				$("#step-picker").show();
				if (!this.all_doctypes.length) this._load_doctypes();
			} else {
				$("#step-picker").hide();
				this.selected_doctypes.clear();
				this._update_summary();
			}
		});

		// Search
		$wrap.on("input", "#dwu-search", () => {
			const q = $("#dwu-search").val().toLowerCase();
			$wrap.find(".dwu-dt-row").each(function () {
				const name = $(this).find(".dwu-dt-name").text().toLowerCase();
				$(this).toggle(name.includes(q));
			});
		});

		// Select / clear all
		$wrap.on("click", "#dwu-select-all", () => {
			$wrap.find(".dwu-dt-row input[type=checkbox]:visible").prop("checked", true).trigger("change");
		});
		$wrap.on("click", "#dwu-clear-all", () => {
			$wrap.find(".dwu-dt-row input[type=checkbox]").prop("checked", false).trigger("change");
		});

		// Checkbox toggle
		$wrap.on("change", ".dwu-dt-row input[type=checkbox]", (e) => {
			const cb = $(e.currentTarget);
			const dt = cb.val();
			if (cb.is(":checked")) {
				this.selected_doctypes.add(dt);
				cb.closest(".dwu-dt-row").addClass("checked");
			} else {
				this.selected_doctypes.delete(dt);
				cb.closest(".dwu-dt-row").removeClass("checked");
			}
			this._update_summary();
		});

		// Row click
		$wrap.on("click", ".dwu-dt-row", (e) => {
			if ($(e.target).is("input")) return;
			$(e.currentTarget).find("input[type=checkbox]").trigger("click");
		});

		// Confirm checkbox
		$wrap.on("change", "#dwu-confirm-check", () => {
			$("#dwu-execute-btn").prop("disabled", !$("#dwu-confirm-check").is(":checked"));
		});

		// Dry run
		$wrap.on("click", "#dwu-dry-run-btn", () => this._run(true));

		// Execute
		$wrap.on("click", "#dwu-execute-btn", () => {
			frappe.confirm(
				__("Are you absolutely sure? This will permanently delete data and cannot be undone."),
				() => this._run(false)
			);
		});
	}

	// ── Load doctypes ─────────────────────────
	_load_doctypes() {
		$("#dwu-doctype-list").html('<div class="dwu-loading"><span class="dwu-spinner"></span> Loading…</div>');
		frappe.call({
			method: "YOUR_APP.YOUR_MODULE.wipe_api.get_submittable_doctypes",
			args: { company: this.company || "" },
			callback: (r) => {
				this.all_doctypes = r.message || [];
				this._render_doctype_list();
			},
		});
	}

	_render_doctype_list() {
		const $list = $("#dwu-doctype-list").empty();

		if (!this.all_doctypes.length) {
			$list.html('<div class="dwu-loading">No submittable documents found.</div>');
			return;
		}

		// Group by module
		const groups = {};
		this.all_doctypes.forEach((d) => {
			if (!groups[d.module]) groups[d.module] = [];
			groups[d.module].push(d);
		});

		Object.keys(groups)
			.sort()
			.forEach((module) => {
				$list.append(`<div class="dwu-dt-group">${module}</div>`);
				groups[module].forEach((d) => {
					const checked = this.selected_doctypes.has(d.doctype);
					$list.append(`
            <div class="dwu-dt-row ${checked ? "checked" : ""}">
              <input type="checkbox" value="${d.doctype}" ${checked ? "checked" : ""} />
              <span class="dwu-dt-name">${d.doctype}</span>
              <span class="dwu-dt-module">${d.module}</span>
              <span class="dwu-dt-count">${d.count.toLocaleString()}</span>
            </div>
          `);
				});
			});
	}

	_update_summary() {
		const $bar = $("#dwu-selection-summary");
		if (this.selected_doctypes.size) {
			$bar.show().text(
				`${this.selected_doctypes.size} document type${this.selected_doctypes.size > 1 ? "s" : ""} selected for wipe`
			);
		} else {
			$bar.hide();
		}
	}

	// ── Run wipe / dry run ───────────────────
	_run(dry_run) {
		const doctypes = this._get_target_doctypes();
		if (!doctypes.length) {
			frappe.msgprint(__("No document types to wipe. Please select at least one."));
			return;
		}

		const label = dry_run ? "Running preview…" : "Wiping data…";
		$("#dwu-dry-run-btn, #dwu-execute-btn").prop("disabled", true).text(label);
		$("#step-results").show();
		$("#dwu-results-body").html(`<div class="dwu-loading"><span class="dwu-spinner"></span> ${label}</div>`);

		frappe.call({
			method: "YOUR_APP.YOUR_MODULE.wipe_api.execute_wipe",
			args: {
				doctypes: JSON.stringify(doctypes),
				company: this.company || "",
				dry_run: dry_run ? 1 : 0,
			},
			callback: (r) => {
				this._render_results(r.message, dry_run);
				$("#dwu-dry-run-btn").prop("disabled", false).text(__("Preview (dry run)"));
				if (!dry_run) {
					$("#dwu-execute-btn").prop("disabled", true);
					$("#dwu-confirm-check").prop("checked", false);
				} else {
					$("#dwu-execute-btn").prop("disabled", !$("#dwu-confirm-check").is(":checked"));
				}
			},
			error: () => {
				$("#dwu-results-body").html('<div class="dwu-loading" style="color:red;">An error occurred. Check the error log.</div>');
				$("#dwu-dry-run-btn").prop("disabled", false).text(__("Preview (dry run)"));
				$("#dwu-execute-btn").prop("disabled", !$("#dwu-confirm-check").is(":checked"));
			},
		});
	}

	_get_target_doctypes() {
		if (this.mode === "all") {
			return this.all_doctypes.length
				? this.all_doctypes.map((d) => d.doctype)
				: []; // will trigger a load if needed
		}
		return Array.from(this.selected_doctypes);
	}

	_render_results(data, dry_run) {
		if (!data) {
			$("#dwu-results-body").html('<div class="dwu-loading" style="color:red;">No response from server.</div>');
			return;
		}

		const cls = dry_run ? "dwu-result-dry" : data.total_deleted > 0 ? "dwu-result-ok" : "dwu-result-err";
		const label = dry_run
			? `Preview: ${data.total_deleted.toLocaleString()} records would be deleted`
			: `Wipe complete: ${data.total_deleted.toLocaleString()} records deleted`;

		let html = `<div class="dwu-result-summary ${cls}">${label}</div>`;
		html += `<div>`;
		(data.results || []).forEach((r) => {
			const statusCls =
				r.status === "error" ? "dwu-status-err" : dry_run ? "dwu-status-dry" : "dwu-status-ok";
			const statusLabel =
				r.status === "error" ? "Error" : dry_run ? `~${r.deleted.toLocaleString()} records` : `${r.deleted.toLocaleString()} deleted`;
			html += `
        <div class="dwu-result-row">
          <span style="flex:1; font-weight:500;">${r.doctype}</span>
          <span class="${statusCls}">${statusLabel}</span>
          ${r.log && r.log !== "OK" ? `<span style="font-size:11px;color:#999;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${r.log}">${r.log}</span>` : ""}
        </div>`;
		});
		html += `</div>`;

		$("#dwu-results-body").html(html);

		// Reload doctype counts after a real wipe
		if (!dry_run && this.mode === "selected") {
			this._load_doctypes();
		}
	}
}