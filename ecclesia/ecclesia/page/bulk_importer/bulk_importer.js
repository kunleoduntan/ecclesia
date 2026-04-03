// ecclesia/public/js/bulk_importer.js
//
// Bulk Import Wizard — 4-step Frappe page script.
//
// ── Key changes from original ─────────────────────────────────────────────
// 1. validate_import and run_import now receive data DIRECTLY as args.
//    No more frappe.client.insert → get_doc round-trip which silently
//    dropped field_mapping / import_data when those weren't real schema
//    fields on "Bulk Import Log".
//
// 2. JSON files use sheet.rows_raw (list-of-dicts) for import_data, not
//    sheet.rows (list-of-lists preview). rows_raw is set by parse_uploaded_file.
//
// 3. All frappe.call()s have both callback: and error: handlers.
//
// 4. The standalone frappe.call({method:"bulk_import"…}) snippet that was
//    appended at page level (referencing an undefined `file` variable and
//    crashing on load) has been removed entirely.
// ─────────────────────────────────────────────────────────────────────────────

frappe.pages["bulk-importer"].on_page_load = function (wrapper) {
  frappe.ui.make_app_page({
    parent:     wrapper,
    title:      "Bulk Importer",
    single_column: true,
  });

  const page = wrapper.page;
  const $body = $(wrapper).find(".page-content");

  const importer = new BulkImporter($body[0], page);
  importer.init();
};


// ═══════════════════════════════════════════════════════════════════════════
// BulkImporter class
// ═══════════════════════════════════════════════════════════════════════════

class BulkImporter {
  constructor(container, page) {
    this.container = container;
    this.page      = page;

    this.state = {
      step:            "doctype",   // doctype → upload → map → import → done
      doctype:         null,
      fileName:        null,
      parsedFile:      null,
      activeSheet:     null,
      mapping:         {},          // { col_header: fieldname | "__ignore__" }
      fieldErrors:     {},          // { col_header: error_message }
      duplicateAction: "Skip",
      dateFormat:      "YYYY-MM-DD",
      importResult:    null,
      _importRows:     null,        // cached after _validateBeforeImport
    };
  }

  // ── Lifecycle ─────────────────────────────────────────────────────────────

  init() {
    this._injectStyles();
    this.render();
  }

  render() {
    this.container.innerHTML = "";

    const wrapper = document.createElement("div");
    wrapper.className = "bi-wizard-wrapper";
    wrapper.innerHTML = this._renderStep();
    this.container.appendChild(wrapper);

    this._bindEvents();
    this._updatePageButtons();
  }

  // ── Step router ───────────────────────────────────────────────────────────

  _renderStep() {
    switch (this.state.step) {
      case "doctype": return this._renderDoctypeStep();
      case "upload":  return this._renderUploadStep();
      case "map":     return this._renderMapStep();
      case "import":  return this._renderImportStep();
      case "done":    return this._renderDoneStep();
      default:        return "<p>Unknown step.</p>";
    }
  }

  _updatePageButtons() {
    this.page.clear_primary_action();
    this.page.clear_secondary_action();

    switch (this.state.step) {
      case "doctype":
        this.page.set_primary_action("Next →", () => {
          if (!this.state.doctype) {
            frappe.show_alert({ message: "Please select a DocType first", indicator: "red" });
            return;
          }
          this.state.step = "upload";
          this.render();
        });
        break;

      case "upload":
        this.page.set_primary_action("Next →", () => {
          if (!this.state.parsedFile) {
            frappe.show_alert({ message: "Please upload a file first", indicator: "red" });
            return;
          }
          this._loadMapping();
        });
        this.page.set_secondary_action("← Back", () => {
          this.state.step = "doctype";
          this.render();
        });
        break;

      case "map":
        this.page.set_primary_action("Validate & Continue", () => {
          this.state.fieldErrors = {};
          this._validateBeforeImport();
        });
        this.page.set_secondary_action("← Back", () => {
          this.state.step = "upload";
          this.render();
        });
        break;

      case "import":
        this.page.set_primary_action("Start Import", () => this._runImport());
        this.page.set_secondary_action("← Back", () => {
          this.state.step = "map";
          this.render();
        });
        break;

      case "done":
        this.page.set_primary_action("Import Again", () => {
          this.state = {
            step: "doctype", doctype: null, fileName: null,
            parsedFile: null, activeSheet: null, mapping: {},
            fieldErrors: {}, duplicateAction: "Skip",
            dateFormat: "YYYY-MM-DD", importResult: null, _importRows: null,
          };
          this.render();
        });
        break;
    }
  }

  // ── Step 1 — DocType picker ───────────────────────────────────────────────

  _renderDoctypeStep() {
    return `
      <div class="bi-step">
        <h3 class="bi-step-title">Step 1 — Select DocType</h3>
        <p class="bi-step-desc">Choose the DocType you want to import records into.</p>
        <div class="bi-field-row">
          <label class="bi-label">DocType</label>
          <input id="bi-doctype-input" class="form-control" type="text"
                 placeholder="e.g. Customer, Supplier, Item…"
                 value="${this.state.doctype || ""}">
          <small class="text-muted">Start typing to search</small>
        </div>
      </div>`;
  }

  _bindDoctypeEvents() {
    const input = document.getElementById("bi-doctype-input");
    if (!input) return;

    let timeout;
    input.addEventListener("input", () => {
      clearTimeout(timeout);
      timeout = setTimeout(() => {
        this.state.doctype = input.value.trim() || null;
      }, 300);
    });

    // Use Frappe's awesomplete if available
    if (window.Awesomplete) {
      frappe.call({
        method: "ecclesia.api.bulk_importer.get_all_doctypes",
        callback: (r) => {
          if (!r.message) return;
          const all = [];
          Object.values(r.message.modules || {}).forEach(list => {
            list.forEach(d => all.push(d.name));
          });
          new Awesomplete(input, { list: all, minChars: 1, maxItems: 20 });
        },
      });
    }
  }

  // ── Step 2 — Upload ───────────────────────────────────────────────────────

  _renderUploadStep() {
    return `
      <div class="bi-step">
        <h3 class="bi-step-title">Step 2 — Upload File</h3>
        <p class="bi-step-desc">
          Upload a CSV, XLSX, or JSON file for <strong>${this.state.doctype}</strong>.
        </p>

        <div class="bi-upload-area" id="bi-upload-area">
          <div class="bi-upload-icon">📂</div>
          <div class="bi-upload-text">Drag &amp; drop or click to upload</div>
          <div class="bi-upload-sub">CSV, XLSX, or JSON · Max 10 MB</div>
          <input id="bi-file-input" type="file" accept=".csv,.xlsx,.xls,.json"
                 style="display:none">
        </div>

        ${this.state.parsedFile ? this._renderFilePreview() : ""}

        <div class="bi-sidebar-action">
          <button class="btn btn-default btn-sm" id="bi-download-template">
            ⬇ Download CSV Template
          </button>
        </div>
      </div>`;
  }

  _renderFilePreview() {
    const sheet = this.state.parsedFile.sheets[this.state.activeSheet];
    if (!sheet) return "";
    const headers = sheet.headers.slice(0, 6);
    const rows    = (sheet.rows || []).slice(0, 3);

    return `
      <div class="bi-preview-box">
        <div class="bi-preview-header">
          <span>📄 ${this.state.fileName}</span>
          <span class="text-muted">${sheet.total} rows · ${sheet.headers.length} columns</span>
        </div>
        <div class="bi-preview-table-wrap">
          <table class="bi-preview-table">
            <thead><tr>${headers.map(h => `<th>${h}</th>`).join("")}${sheet.headers.length > 6 ? "<th>…</th>" : ""}</tr></thead>
            <tbody>
              ${rows.map(r => `<tr>${headers.map((_, i) => `<td>${r[i] || ""}</td>`).join("")}${sheet.headers.length > 6 ? "<td>…</td>" : ""}</tr>`).join("")}
            </tbody>
          </table>
        </div>
      </div>`;
  }

  _bindUploadEvents() {
    const area  = document.getElementById("bi-upload-area");
    const input = document.getElementById("bi-file-input");
    const btn   = document.getElementById("bi-download-template");

    if (area) {
      area.addEventListener("click", () => input && input.click());
      area.addEventListener("dragover", e => { e.preventDefault(); area.classList.add("drag-over"); });
      area.addEventListener("dragleave", () => area.classList.remove("drag-over"));
      area.addEventListener("drop", e => {
        e.preventDefault();
        area.classList.remove("drag-over");
        const file = e.dataTransfer?.files?.[0];
        if (file) this._handleFileUpload(file);
      });
    }

    if (input) {
      input.addEventListener("change", () => {
        const file = input.files?.[0];
        if (file) this._handleFileUpload(file);
      });
    }

    if (btn) {
      btn.addEventListener("click", () => this._downloadTemplate());
    }
  }

  _handleFileUpload(file) {
    this.state.fileName = file.name;
    frappe.show_alert({ message: "Parsing file…", indicator: "blue" });

    const reader = new FileReader();
    reader.onload = (e) => {
      const b64 = btoa(
        new Uint8Array(e.target.result).reduce(
          (data, byte) => data + String.fromCharCode(byte), ""
        )
      );

      frappe.call({
        method: "ecclesia.api.bulk_importer.parse_uploaded_file",
        args:   { file_name: file.name, file_content_b64: b64 },
        callback: (r) => {
          if (!r.message || r.message.error) {
            frappe.show_alert({
              message:   r.message?.error || "Could not parse file",
              indicator: "red",
            });
            return;
          }
          this.state.parsedFile  = r.message;
          this.state.activeSheet = Object.keys(r.message.sheets)[0];
          frappe.show_alert({ message: "File parsed successfully", indicator: "green" });
          this.render();
        },
        error: (err) => {
          frappe.show_alert({ message: err.message || "Upload failed", indicator: "red" });
        },
      });
    };
    reader.readAsArrayBuffer(file);
  }

  _downloadTemplate() {
    frappe.call({
      method: "ecclesia.api.bulk_importer.download_template",
      args:   { doctype: this.state.doctype },
      callback: (r) => {
        if (!r.message) return;
        const { filename, content } = r.message;
        const link = document.createElement("a");
        link.href     = `data:text/csv;base64,${content}`;
        link.download = filename;
        link.click();
      },
      error: (err) => {
        frappe.show_alert({ message: err.message || "Download failed", indicator: "red" });
      },
    });
  }

  // ── Step 3 — Map fields ───────────────────────────────────────────────────

  _loadMapping() {
    const sheet = this.state.parsedFile?.sheets?.[this.state.activeSheet];
    if (!sheet) return;

    frappe.show_alert({ message: "Auto-mapping fields…", indicator: "blue" });

    // Build { col_header: [sample_val, …] } from preview rows
    const colData = {};
    sheet.headers.forEach((h, i) => {
      colData[h] = (sheet.rows || []).slice(0, 10).map(r => r[i] || "");
    });

    frappe.call({
      method: "ecclesia.api.bulk_importer.auto_map_with_samples",
      args: {
        doctype:          this.state.doctype,
        column_data_json: JSON.stringify(colData),
      },
      callback: (r) => {
        if (!r.message) {
          frappe.show_alert({ message: "Could not load field mapping", indicator: "red" });
          return;
        }
        this.state.mapping = r.message.mapping || {};
        this.state.step    = "map";
        this.render();
        this._loadTemplates();
      },
      error: (err) => {
        frappe.show_alert({ message: err.message || "Auto-map failed", indicator: "red" });
      },
    });
  }

  _renderMapStep() {
    const sheet = this.state.parsedFile?.sheets?.[this.state.activeSheet];
    if (!sheet) return "<p>No file data.</p>";

    return `
      <div class="bi-step">
        <h3 class="bi-step-title">Step 3 — Map Fields</h3>
        <p class="bi-step-desc">
          Map each column in your file to the corresponding
          <strong>${this.state.doctype}</strong> field.
        </p>

        <div class="bi-map-toolbar">
          <div class="bi-map-toolbar-left">
            <select id="bi-template-select" class="form-control form-control-sm"
                    style="width:200px;">
              <option value="">Load template…</option>
            </select>
            <button class="btn btn-default btn-sm" id="bi-save-template">Save template</button>
          </div>
          <div class="bi-map-toolbar-right">
            <label class="bi-label-inline">Duplicate action:</label>
            <select id="bi-dup-action" class="form-control form-control-sm" style="width:140px;">
              <option value="Skip"       ${this.state.duplicateAction === "Skip"       ? "selected" : ""}>Skip</option>
              <option value="Update"     ${this.state.duplicateAction === "Update"     ? "selected" : ""}>Update</option>
              <option value="Create New" ${this.state.duplicateAction === "Create New" ? "selected" : ""}>Create New</option>
            </select>
          </div>
        </div>

        <div id="bi-validation-summary" style="display:none;margin-bottom:16px;"></div>

        <div class="bi-map-list">
          <div class="bi-map-header-row">
            <span>File Column</span>
            <span>Sample Values</span>
            <span>Maps To</span>
          </div>
          ${sheet.headers.map(col => this._renderMapRow(col, sheet)).join("")}
        </div>

        <div class="bi-validate-bar">
          <button class="btn btn-default btn-sm" id="bi-validate-btn">
            ✓ Validate Mapping
          </button>
        </div>
      </div>`;
  }

  _renderMapRow(col, sheet) {
    const mapped  = this.state.mapping[col] || "__ignore__";
    const hasErr  = !!this.state.fieldErrors[col];
    const samples = (sheet.rows || []).slice(0, 3).map(r => {
      const i = sheet.headers.indexOf(col);
      return r[i] || "";
    }).filter(Boolean).join(", ");

    return `
      <div class="bi-map-row${hasErr ? " has-error" : ""}" data-col="${col}">
        <div class="bi-map-col-name">
          ${hasErr ? `<span class="bi-error-indicator" title="${this.state.fieldErrors[col]}">⚠</span>` : ""}
          <span>${col}</span>
        </div>
        <div class="bi-map-samples text-muted">${samples || "—"}</div>
        <div class="bi-map-select-wrap">
          <select class="form-control form-control-sm bi-field-select" data-col="${col}">
            <option value="__ignore__">— Ignore —</option>
            ${this._renderFieldOptions(mapped)}
          </select>
        </div>
      </div>`;
  }

  _renderFieldOptions(selected) {
    // Options are rebuilt from the last auto_map response stored in state.
    // We pull field list from state._fields (set after auto_map_with_samples).
    const fields = this.state._fields || [];
    return fields
      .filter(f => !f.is_child_table)
      .map(f => {
        const sel = selected === f.fieldname ? "selected" : "";
        const req = f.reqd ? " *" : "";
        return `<option value="${f.fieldname}" ${sel}>${f.label}${req}</option>`;
      })
      .join("");
  }

  _loadTemplates() {
    frappe.call({
      method: "ecclesia.api.bulk_importer.get_templates",
      args:   { doctype: this.state.doctype },
      callback: (r) => {
        if (!r.message?.length) return;
        const sel = document.getElementById("bi-template-select");
        if (!sel) return;
        r.message.forEach(t => {
          const opt   = document.createElement("option");
          opt.value   = JSON.stringify(t);
          opt.textContent = t.template_name + (t.is_default ? " (default)" : "");
          sel.appendChild(opt);
        });
      },
    });
  }

  _bindMapEvents() {
    // Field select changes
    document.querySelectorAll(".bi-field-select").forEach(sel => {
      sel.addEventListener("change", (e) => {
        const col = e.target.dataset.col;
        this.state.mapping[col] = e.target.value;
        delete this.state.fieldErrors[col];
        const row = e.target.closest(".bi-map-row");
        if (row) row.classList.remove("has-error");
      });
    });

    // Duplicate action
    const dupSel = document.getElementById("bi-dup-action");
    if (dupSel) {
      dupSel.addEventListener("change", () => {
        this.state.duplicateAction = dupSel.value;
      });
    }

    // Validate button
    const valBtn = document.getElementById("bi-validate-btn");
    if (valBtn) {
      valBtn.addEventListener("click", () => {
        this.state.fieldErrors = {};
        this._validateMapping();
      });
    }

    // Template select
    const tplSel = document.getElementById("bi-template-select");
    if (tplSel) {
      tplSel.addEventListener("change", () => {
        if (!tplSel.value) return;
        try {
          const t = JSON.parse(tplSel.value);
          this.state.mapping         = JSON.parse(t.field_mapping || "{}");
          this.state.duplicateAction = t.duplicate_action || "Skip";
          this.state.dateFormat      = t.date_format      || "YYYY-MM-DD";
          this.render();
        } catch (e) {
          console.error("Template parse error:", e);
        }
      });
    }

    // Save template
    const saveTplBtn = document.getElementById("bi-save-template");
    if (saveTplBtn) {
      saveTplBtn.addEventListener("click", () => {
        const name = prompt("Template name:");
        if (!name) return;
        frappe.call({
          method: "ecclesia.api.bulk_importer.save_template",
          args: {
            doctype:          this.state.doctype,
            template_name:    name,
            mapping_json:     JSON.stringify(this.state.mapping),
            duplicate_action: this.state.duplicateAction,
            date_format:      this.state.dateFormat,
          },
          callback: () => frappe.show_alert({ message: "Template saved", indicator: "green" }),
          error:    (err) => frappe.show_alert({ message: err.message || "Save failed", indicator: "red" }),
        });
      });
    }
  }

  // ── validate_import ────────────────────────────────────────────────────────
  // Passes data directly — no Bulk Import Log round-trip.

  _validateMapping() {
    const sheet = this.state.parsedFile?.sheets?.[this.state.activeSheet];
    if (!sheet) return;

    frappe.show_alert({ message: "Validating data…", indicator: "blue" });

    // rows_raw is the full list-of-dicts for JSON; rows is list-of-lists for CSV/XLSX
    const importRows = sheet.rows_raw || sheet.rows || [];

    frappe.call({
      method: "ecclesia.api.bulk_importer.validate_import",
      args: {
        doctype:      this.state.doctype,
        mapping_json: JSON.stringify(this.state.mapping),
        rows_json:    JSON.stringify(importRows),
      },
      callback: (r) => {
        frappe.show_alert({ message: "Validation complete", indicator: "green" });
        this._displayValidationResults(r.message);
      },
      error: (err) => {
        const msg = err.message || "Server error during validation";
        frappe.show_alert({ message: msg, indicator: "red" });
        this._displayValidationResults({
          status: "error", message: msg,
          details: { blockers: [], rows_with_errors: 0 },
        });
      },
    });
  }

  _validateBeforeImport() {
    const sheet = this.state.parsedFile?.sheets?.[this.state.activeSheet];
    if (!sheet) return;

    frappe.show_alert({ message: "Preparing import…", indicator: "blue" });

    const importRows = sheet.rows_raw || sheet.rows || [];

    frappe.call({
      method: "ecclesia.api.bulk_importer.validate_import",
      args: {
        doctype:      this.state.doctype,
        mapping_json: JSON.stringify(this.state.mapping),
        rows_json:    JSON.stringify(importRows),
      },
      callback: (vr) => {
        const result      = vr.message;
        const hasBlockers = result?.details?.blockers?.length > 0;
        const hasErrors   = result?.details?.rows_with_errors > 0;

        if (!result || result.status === "error" || hasBlockers || hasErrors) {
          this._displayValidationResults(result || {
            status: "error",
            message: "No response from validation server",
            details: { blockers: [], rows_with_errors: 0 },
          });
          frappe.show_alert({
            message: "Please fix validation errors before proceeding",
            indicator: "red",
          });
        } else {
          // Cache rows so _runImport doesn't need to re-read from sheet
          this.state._importRows = importRows;
          this.state.step        = "import";
          this.render();
        }
      },
      error: (err) => {
        const msg = err.message || "Server error during validation";
        frappe.show_alert({ message: msg, indicator: "red" });
        this._displayValidationResults({
          status: "error", message: msg,
          details: { blockers: [], rows_with_errors: 0 },
        });
      },
    });
  }

  _displayValidationResults(result) {
    const summaryDiv = document.getElementById("bi-validation-summary");
    if (!summaryDiv) return;

    if (!result) {
      summaryDiv.innerHTML = `
        <div class="bi-error-banner">
          <span class="bi-error-icon">⚠</span>
          <div>Validation failed: no response from server.</div>
        </div>`;
      summaryDiv.style.display = "block";
      return;
    }

    const details  = result.details || {};
    const blockers = details.blockers || [];

    if (result.status === "error" || blockers.length > 0) {
      if (blockers.length > 0) {
        let html = `
          <div class="bi-error-banner">
            <span class="bi-error-icon">🚫</span>
            <div><strong>Missing Required Fields:</strong>
            <ul style="margin-top:8px;margin-bottom:0;">`;
        blockers.forEach(b => {
          html += `<li>${b.label || b.field} (${b.fieldtype}) — ${b.message || "Required field not mapped"}</li>`;
          const col = Object.keys(this.state.mapping).find(k => this.state.mapping[k] === b.field);
          if (col) this.state.fieldErrors[col] = b.message || "Required field not mapped";
        });
        html += `</ul></div></div>`;
        summaryDiv.innerHTML = html;
      } else {
        summaryDiv.innerHTML = `
          <div class="bi-error-banner">
            <span class="bi-error-icon">⚠</span>
            <div>Validation error: ${result.message || details.message || "Unknown error"}</div>
          </div>`;
      }
      summaryDiv.style.display = "block";

    } else if (details.rows_with_errors > 0) {
      let html = `
        <div class="bi-error-banner">
          <span class="bi-error-icon">⚠</span>
          <div><strong>Found ${details.rows_with_errors} rows with validation errors:</strong>
          <ul style="margin-top:8px;max-height:200px;overflow-y:auto;">`;
      let shown = 0;
      for (const [rowNum, issues] of Object.entries(details.row_issues || {})) {
        if (shown >= 5) break;
        (issues.errors || []).forEach(e => {
          html += `<li>Row ${rowNum} — ${e.label || e.field}: ${e.message}</li>`;
          shown++;
        });
      }
      if (details.rows_with_errors > 5) {
        html += `<li>… and ${details.rows_with_errors - 5} more rows</li>`;
      }
      html += `</ul></div></div>`;
      summaryDiv.innerHTML = html;
      summaryDiv.style.display = "block";

    } else {
      summaryDiv.innerHTML = `
        <div class="bi-success-banner">
          <span style="font-size:20px;">✓</span>
          <div><strong>Validation Passed!</strong> All ${details.total_rows || 0} rows are valid.</div>
        </div>`;
      summaryDiv.style.display = "block";
    }

    // Refresh error indicators on map rows
    document.querySelectorAll(".bi-map-row").forEach(row => {
      const col = row.dataset.col;
      if (this.state.fieldErrors[col]) {
        row.classList.add("has-error");
        const ind = row.querySelector(".bi-error-indicator");
        if (ind) ind.title = this.state.fieldErrors[col];
      } else {
        row.classList.remove("has-error");
      }
    });
  }

  // ── Step 4 — Import ───────────────────────────────────────────────────────

  _renderImportStep() {
    const sheet = this.state.parsedFile?.sheets?.[this.state.activeSheet];
    const total = sheet?.total || 0;

    return `
      <div class="bi-step">
        <h3 class="bi-step-title">Step 4 — Import</h3>
        <p class="bi-step-desc">
          Ready to import <strong>${total}</strong> rows into
          <strong>${this.state.doctype}</strong>.
          Duplicate action: <strong>${this.state.duplicateAction}</strong>.
        </p>

        <div class="bi-checklist">
          <div class="bi-check-item" id="check-0">
            <span class="bi-check-dot">○</span> Parsing rows
          </div>
          <div class="bi-check-item" id="check-1">
            <span class="bi-check-dot">○</span> Applying field mapping
          </div>
          <div class="bi-check-item" id="check-2">
            <span class="bi-check-dot">○</span> Validating values
          </div>
          <div class="bi-check-item" id="check-3">
            <span class="bi-check-dot">○</span> Inserting records
          </div>
          <div class="bi-check-item" id="check-4">
            <span class="bi-check-dot">○</span> Saving audit log
          </div>
        </div>

        <div class="bi-progress-wrap">
          <div class="bi-progress-bar">
            <div class="bi-progress-fill" id="bi-progress-fill" style="width:0%"></div>
          </div>
          <span class="bi-progress-label" id="bi-progress-label">0%</span>
        </div>

        <div id="bi-import-error" style="display:none;margin-top:16px;"></div>
      </div>`;
  }

  _setProgress(pct) {
    const fill  = document.getElementById("bi-progress-fill");
    const label = document.getElementById("bi-progress-label");
    if (fill)  fill.style.width = pct + "%";
    if (label) label.textContent = pct + "%";
  }

  _showImportErrors(response) {
    const errDiv = document.getElementById("bi-import-error");
    if (!errDiv) return;

    const details = response.details || {};
    const errors  = details.error_details || [];

    let html = `
      <div class="bi-error-banner">
        <span class="bi-error-icon">⚠</span>
        <div>
          <strong>Import completed with errors.</strong>
          ${details.success  !== undefined ? `<br>✓ ${details.success} inserted` : ""}
          ${details.skipped  !== undefined ? `, ${details.skipped} skipped` : ""}
          ${details.errors   !== undefined ? `, ${details.errors} errors` : ""}
          ${response.message ? `<br><em>${response.message}</em>` : ""}`;

    if (errors.length) {
      html += `<ul style="margin-top:8px;max-height:200px;overflow-y:auto;">`;
      errors.slice(0, 20).forEach(e => {
        html += `<li>Row ${e.row}: ${e.message}</li>`;
      });
      if (errors.length > 20) html += `<li>…and ${errors.length - 20} more</li>`;
      html += `</ul>`;
    }

    html += `</div></div>`;
    errDiv.innerHTML = html;
    errDiv.style.display = "block";
  }

  // ── run_import ─────────────────────────────────────────────────────────────
  // Passes data directly — no Bulk Import Log round-trip.

  _runImport() {
    const sheet      = this.state.parsedFile?.sheets?.[this.state.activeSheet];
    const importRows = this.state._importRows
      || (sheet ? (sheet.rows_raw || sheet.rows || []) : []);

    if (!importRows.length) {
      frappe.msgprint("No data to import. Please go back and re-upload your file.");
      this.state.step = "upload";
      this.render();
      return;
    }

    let checkIdx = 0;
    const interval = setInterval(() => {
      if (checkIdx < 4) {
        const el = document.getElementById(`check-${checkIdx}`);
        if (el) {
          el.querySelector(".bi-check-dot").textContent = "✓";
          el.classList.add("done");
        }
        checkIdx++;
        this._setProgress(Math.round((checkIdx / 5) * 75));
      }
    }, 700);

    frappe.call({
      method: "ecclesia.api.bulk_importer.run_import",
      args: {
        doctype:          this.state.doctype,
        mapping_json:     JSON.stringify(this.state.mapping),
        rows_json:        JSON.stringify(importRows),
        duplicate_action: this.state.duplicateAction,
        date_format:      this.state.dateFormat,
        file_name:        this.state.fileName || "import.csv",
      },
      callback: (r) => {
        clearInterval(interval);
        for (let i = 0; i < 5; i++) {
          const el = document.getElementById(`check-${i}`);
          if (el) {
            el.querySelector(".bi-check-dot").textContent = "✓";
            el.classList.add("done");
          }
        }
        this._setProgress(100);

        setTimeout(() => {
          if (!r.message) {
            this._showImportErrors({ status: "error", message: "No response from server." });
            return;
          }
          const resp = r.message;
          if (resp.status === "error") {
            this._showImportErrors(resp);
            return;
          }
          // Partial success (some errors) still navigates to done
          this.state.importResult = resp.details || resp;
          this.state.step         = "done";
          this.render();
        }, 500);
      },
      error: (err) => {
        clearInterval(interval);
        this._showImportErrors({
          status: "error",
          message: err.message || "Unknown error occurred",
          details: { error_details: [] },
        });
      },
    });
  }

  // ── Step 5 — Done ─────────────────────────────────────────────────────────

  _renderDoneStep() {
    const r = this.state.importResult || {};
    return `
      <div class="bi-step bi-done-step">
        <div class="bi-done-icon">🎉</div>
        <h3 class="bi-step-title">Import Complete</h3>

        <div class="bi-done-stats">
          <div class="bi-stat-card bi-stat-success">
            <div class="bi-stat-num">${r.success ?? 0}</div>
            <div class="bi-stat-label">Inserted</div>
          </div>
          <div class="bi-stat-card bi-stat-skip">
            <div class="bi-stat-num">${r.skipped ?? 0}</div>
            <div class="bi-stat-label">Skipped</div>
          </div>
          <div class="bi-stat-card bi-stat-error">
            <div class="bi-stat-num">${r.errors ?? 0}</div>
            <div class="bi-stat-label">Errors</div>
          </div>
          <div class="bi-stat-card bi-stat-time">
            <div class="bi-stat-num">${r.time_taken ?? 0}s</div>
            <div class="bi-stat-label">Time</div>
          </div>
        </div>

        ${r.errors > 0 ? `
        <div class="bi-error-banner" style="margin-top:16px;">
          <span class="bi-error-icon">⚠</span>
          <div>
            <strong>${r.errors} rows had errors:</strong>
            <ul style="margin-top:8px;max-height:200px;overflow-y:auto;">
              ${(r.error_details || []).slice(0, 20).map(e =>
                `<li>Row ${e.row}: ${e.message}</li>`
              ).join("")}
              ${r.errors > 20 ? `<li>…and ${r.errors - 20} more</li>` : ""}
            </ul>
          </div>
        </div>` : ""}

        ${r.import_log_name ? `
        <p class="text-muted" style="margin-top:12px;">
          Audit log: <a href="/app/bulk-import-log/${r.import_log_name}">${r.import_log_name}</a>
        </p>` : ""}
      </div>`;
  }

  // ── Event binding router ──────────────────────────────────────────────────

  _bindEvents() {
    switch (this.state.step) {
      case "doctype": this._bindDoctypeEvents(); break;
      case "upload":  this._bindUploadEvents();  break;
      case "map":     this._bindMapEvents();     break;
    }
  }

  // ── Styles ────────────────────────────────────────────────────────────────

  _injectStyles() {
    if (document.getElementById("bi-styles")) return;
    const style = document.createElement("style");
    style.id = "bi-styles";
    style.textContent = BI_CSS;
    document.head.appendChild(style);
  }
}


// ═══════════════════════════════════════════════════════════════════════════
// Styles
// ═══════════════════════════════════════════════════════════════════════════

const BI_CSS = `
.bi-wizard-wrapper { max-width: 900px; margin: 24px auto; padding: 0 16px; }

.bi-step { background: #fff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 28px 32px; }
.bi-step-title { font-size: 18px; font-weight: 600; margin-bottom: 6px; color: #1e293b; }
.bi-step-desc  { color: #64748b; margin-bottom: 20px; }

/* Upload */
.bi-upload-area {
  border: 2px dashed #cbd5e1; border-radius: 8px; padding: 40px 20px;
  text-align: center; cursor: pointer; transition: background .2s;
  background: #f8fafc;
}
.bi-upload-area:hover, .bi-upload-area.drag-over { background: #eff6ff; border-color: #93c5fd; }
.bi-upload-icon { font-size: 36px; margin-bottom: 8px; }
.bi-upload-text { font-size: 15px; font-weight: 500; color: #334155; }
.bi-upload-sub  { font-size: 12px; color: #94a3b8; margin-top: 4px; }

.bi-preview-box { margin-top: 16px; border: 1px solid #e2e8f0; border-radius: 6px; overflow: hidden; }
.bi-preview-header {
  background: #f1f5f9; padding: 8px 14px; display: flex;
  justify-content: space-between; font-size: 13px;
}
.bi-preview-table-wrap { overflow-x: auto; max-height: 180px; }
.bi-preview-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.bi-preview-table th, .bi-preview-table td {
  padding: 5px 10px; border-bottom: 1px solid #f1f5f9; white-space: nowrap;
}
.bi-preview-table th { background: #f8fafc; font-weight: 600; }

.bi-sidebar-action { margin-top: 14px; }

/* Mapping */
.bi-map-toolbar {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 16px; gap: 8px; flex-wrap: wrap;
}
.bi-map-toolbar-left, .bi-map-toolbar-right { display: flex; align-items: center; gap: 8px; }
.bi-label-inline { font-size: 13px; white-space: nowrap; }

.bi-map-list { border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; }
.bi-map-header-row {
  display: grid; grid-template-columns: 1fr 1fr 1fr;
  background: #f8fafc; padding: 8px 14px; font-size: 12px;
  font-weight: 600; color: #64748b; border-bottom: 1px solid #e2e8f0;
}
.bi-map-row {
  display: grid; grid-template-columns: 1fr 1fr 1fr;
  padding: 8px 14px; border-bottom: 1px solid #f1f5f9;
  align-items: center; transition: background .15s;
}
.bi-map-row:hover { background: #f8fafc; }
.bi-map-row.has-error { background: #fff5f5; }
.bi-map-col-name { display: flex; align-items: center; gap: 6px; font-size: 13px; }
.bi-map-samples  { font-size: 11px; color: #94a3b8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.bi-error-indicator { color: #ef4444; cursor: help; font-size: 14px; }

.bi-validate-bar { margin-top: 14px; }

/* Progress */
.bi-checklist { margin: 16px 0; }
.bi-check-item {
  display: flex; align-items: center; gap: 10px;
  padding: 6px 0; font-size: 14px; color: #64748b;
}
.bi-check-item.done { color: #22c55e; }
.bi-check-dot { font-size: 16px; width: 20px; text-align: center; }

.bi-progress-wrap { display: flex; align-items: center; gap: 12px; margin-top: 8px; }
.bi-progress-bar  { flex: 1; height: 10px; background: #e2e8f0; border-radius: 99px; overflow: hidden; }
.bi-progress-fill { height: 100%; background: #3b82f6; border-radius: 99px; transition: width .4s ease; }
.bi-progress-label { font-size: 13px; color: #64748b; width: 36px; text-align: right; }

/* Banners */
.bi-error-banner, .bi-success-banner {
  display: flex; align-items: flex-start; gap: 12px;
  padding: 14px 16px; border-radius: 8px; font-size: 13px;
}
.bi-error-banner   { background: #fff5f5; border: 1px solid #fecaca; color: #b91c1c; }
.bi-success-banner { background: #f0fdf4; border: 1px solid #bbf7d0; color: #15803d; }
.bi-error-icon { font-size: 18px; margin-top: 1px; }
.bi-error-banner ul, .bi-success-banner ul { margin: 6px 0 0; padding-left: 20px; }
.bi-error-banner li, .bi-success-banner li { margin-bottom: 3px; }

/* Done */
.bi-done-step { text-align: center; padding: 40px 32px; }
.bi-done-icon { font-size: 48px; margin-bottom: 8px; }
.bi-done-stats {
  display: flex; justify-content: center; gap: 16px; margin: 24px 0; flex-wrap: wrap;
}
.bi-stat-card {
  min-width: 100px; padding: 16px 20px; border-radius: 10px; text-align: center;
}
.bi-stat-num   { font-size: 28px; font-weight: 700; }
.bi-stat-label { font-size: 12px; margin-top: 2px; opacity: .8; }
.bi-stat-success { background: #f0fdf4; color: #16a34a; }
.bi-stat-skip    { background: #fffbeb; color: #b45309; }
.bi-stat-error   { background: #fff5f5; color: #dc2626; }
.bi-stat-time    { background: #eff6ff; color: #2563eb; }

/* Field row */
.bi-field-row { margin-bottom: 16px; }
.bi-label { display: block; font-size: 13px; font-weight: 500; margin-bottom: 4px; }
`;


if (typeof module !== "undefined" && module.exports) {
  module.exports = BulkImporter;
}