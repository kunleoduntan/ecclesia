/**
 * universal_excel_export_extended.js
 * ====================================
 * Drop into: <your_app>/public/js/universal_excel_export_extended.js
 * Register AFTER universal_excel_export.js in hooks.py app_include_js
 *
 * Adds:
 *  1. Large-dataset chunked fetching with progress bar
 *  2. Drag-to-reorder columns in the dialog
 *  3. Ecclesia / ERPNext custom toolbar button integration
 *  4. "Quick Export" (no dialog) via Shift+Click on the button
 *  5. LocalStorage memory of last-used column selection per DocType
 *  6. Column order persistence across sessions
 */

// ─── Constants ─────────────────────────────────────────────────────────────────
const UEE_CHUNK_SIZE   = 500;    // rows fetched per API call for large exports
const UEE_LARGE_LIMIT  = 1000;  // row count above which chunking kicks in
const UEE_STORAGE_KEY  = "uee_col_prefs_v1";

// ─── LocalStorage helpers ──────────────────────────────────────────────────────
const UEEPrefs = {
    _get() {
        try { return JSON.parse(localStorage.getItem(UEE_STORAGE_KEY) || "{}"); }
        catch { return {}; }
    },
    _set(obj) {
        try { localStorage.setItem(UEE_STORAGE_KEY, JSON.stringify(obj)); } catch {}
    },
    getForDoctype(doctype) {
        return this._get()[doctype] || null;
    },
    saveForDoctype(doctype, selectedFieldnames, orderedFieldnames) {
        const prefs = this._get();
        prefs[doctype] = { selected: selectedFieldnames, order: orderedFieldnames, ts: Date.now() };
        this._set(prefs);
    },
    clearForDoctype(doctype) {
        const prefs = this._get();
        delete prefs[doctype];
        this._set(prefs);
    },
};

// ─── Progress bar overlay ──────────────────────────────────────────────────────
const UEEProgress = {
    _el: null,
    _bar: null,
    _label: null,

    show(message = "Preparing…") {
        if (this._el) this.hide();
        this._el = document.createElement("div");
        this._el.style.cssText = `
            position:fixed; top:0; left:0; right:0; z-index:9999;
            background:#1A2E4A; color:#fff; font-family:'Nunito Sans',sans-serif;
            padding:10px 20px; display:flex; align-items:center; gap:16px;
            box-shadow:0 2px 12px rgba(0,0,0,.3); font-size:13px; font-weight:600;`;
        this._el.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#E8A020"
                 stroke-width="2.5" style="flex-shrink:0">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            <div style="flex:1">
                <div id="_uee_progress_label" style="margin-bottom:4px">${frappe.utils.escape_html(message)}</div>
                <div style="background:rgba(255,255,255,.15);border-radius:4px;height:5px;overflow:hidden">
                    <div id="_uee_progress_bar" style="background:#E8A020;height:100%;width:0%;
                         transition:width .3s ease;border-radius:4px"></div>
                </div>
            </div>
            <button id="_uee_progress_cancel" style="background:rgba(255,255,255,.15);border:none;
                color:#fff;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px">
                Cancel
            </button>`;
        document.body.appendChild(this._el);
        this._bar   = document.getElementById("_uee_progress_bar");
        this._label = document.getElementById("_uee_progress_label");
        this._cancelled = false;

        document.getElementById("_uee_progress_cancel").addEventListener("click", () => {
            this._cancelled = true;
            this.hide();
            frappe.show_alert({ message: "Export cancelled", indicator: "orange" }, 3);
        });
    },

    update(pct, message) {
        if (!this._bar) return;
        this._bar.style.width = `${Math.min(100, pct)}%`;
        if (message && this._label) this._label.textContent = message;
    },

    hide() {
        if (this._el) { this._el.remove(); this._el = null; }
    },

    get cancelled() { return this._cancelled; },
};

// ─── Chunked data fetcher ──────────────────────────────────────────────────────
async function fetchAllRows(doctype, fieldnames, filters, rowLimit) {
    const allRows = [];
    let start = 0;
    const chunkSize = UEE_CHUNK_SIZE;

    while (start < rowLimit) {
        if (UEEProgress.cancelled) return null;

        const limit = Math.min(chunkSize, rowLimit - start);
        const pct   = (start / rowLimit) * 70;  // first 70% = fetching
        UEEProgress.update(pct, `Fetching rows ${start + 1}–${Math.min(start + limit, rowLimit)}…`);

        const result = await new Promise((resolve, reject) => {
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype,
                    fields:           fieldnames,
                    filters:          filters || [],
                    limit_start:      start,
                    limit_page_length: limit,
                    order_by:         "creation desc",
                },
                callback: (r) => resolve(r),
                error:    (e) => reject(e),
            });
        });

        if (!result || result.exc) {
            frappe.msgprint({ title: "Fetch Error", message: result?.exc || "API error", indicator: "red" });
            return null;
        }

        const rows = result.message || [];
        allRows.push(...rows);

        if (rows.length < limit) break;   // no more data
        start += limit;
    }

    return allRows;
}

// ─── Main export orchestrator (replaces triggerExport in base JS) ──────────────
async function triggerExportFull(listView, fields, selections) {
    const { selectedFields, orderedFields, scope, includeHeader, freezeHeader, rowLimit } = selections;

    if (!selectedFields || selectedFields.length === 0) {
        frappe.msgprint({ title: "No Columns", message: "Please select at least one column.", indicator: "orange" });
        return;
    }

    // Save prefs
    UEEPrefs.saveForDoctype(
        listView.doctype,
        selectedFields.map(f => f.fieldname),
        (orderedFields || selectedFields).map(f => f.fieldname)
    );

    const filters = scope === "filtered"
        ? _getFilters(listView)
        : [];

    const fieldnames = (orderedFields || selectedFields).map(f => f.fieldname);

    UEEProgress.show("Starting export…");

    try {
        // ── Fetch ──────────────────────────────────────────────────────────
        let rows;
        if (rowLimit > UEE_LARGE_LIMIT) {
            rows = await fetchAllRows(listView.doctype, fieldnames, filters, rowLimit);
        } else {
            UEEProgress.update(10, "Fetching data…");
            const r = await new Promise((res) => {
                frappe.call({
                    method: "frappe.client.get_list",
                    args: {
                        doctype:          listView.doctype,
                        fields:           fieldnames,
                        filters:          filters,
                        limit_page_length: rowLimit,
                        order_by:         "creation desc",
                    },
                    callback: res,
                });
            });
            rows = r?.message || [];
        }

        if (rows === null) return;  // cancelled
        if (rows.length === 0) {
            UEEProgress.hide();
            frappe.msgprint({ title: "No Data", message: "No records found for the selected filters.", indicator: "blue" });
            return;
        }

        // ── Generate Excel ─────────────────────────────────────────────────
        UEEProgress.update(75, `Building Excel workbook (${rows.length} rows)…`);

        const fieldsForExport = (orderedFields || selectedFields);

        const res = await new Promise((resolve) => {
            frappe.call({
                method: "universal_excel_export.api.excel_export.generate_excel",
                args: {
                    doctype:        listView.doctype,
                    fields:         fieldsForExport.map(f => ({
                                        fieldname: f.fieldname,
                                        label:     f.label,
                                        fieldtype: f.fieldtype,
                                    })),
                    data:           rows,
                    include_header: includeHeader,
                    freeze_header:  freezeHeader,
                },
                callback: resolve,
            });
        });

        if (!res || res.exc || !res.message) {
            UEEProgress.hide();
            frappe.msgprint({ title: "Export Failed", message: res?.exc || "Server error", indicator: "red" });
            return;
        }

        // ── Download ───────────────────────────────────────────────────────
        UEEProgress.update(95, "Preparing download…");
        _downloadBase64xlsx(res.message, listView.doctype, rows.length);
        UEEProgress.update(100, "Done!");

        setTimeout(() => {
            UEEProgress.hide();
            frappe.show_alert({
                message: `<b>${rows.length}</b> row${rows.length !== 1 ? "s" : ""} exported to Excel`,
                indicator: "green",
            }, 5);
        }, 600);

    } catch (err) {
        UEEProgress.hide();
        frappe.msgprint({ title: "Export Error", message: String(err), indicator: "red" });
    }
}

// ─── helpers ───────────────────────────────────────────────────────────────────
function _getFilters(listView) {
    try {
        if (typeof listView.get_filters_for_args === "function") return listView.get_filters_for_args();
        if (listView.filter_area?.get)                           return listView.filter_area.get();
        if (listView.filters)                                    return listView.filters;
    } catch {}
    return [];
}

function _downloadBase64xlsx(b64, doctype, rowCount) {
    const byteStr = atob(b64);
    const ab  = new ArrayBuffer(byteStr.length);
    const ia  = new Uint8Array(ab);
    for (let i = 0; i < byteStr.length; i++) ia[i] = byteStr.charCodeAt(i);
    const blob = new Blob([ab], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
    const safe = doctype.replace(/[^a-zA-Z0-9_]/g, "_");
    const ts   = new Date().toISOString().slice(0, 19).replace(/[T:]/g, "-");
    const a    = document.createElement("a");
    a.href     = URL.createObjectURL(blob);
    a.download = `${safe}_${rowCount}rows_${ts}.xlsx`;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 800);
}

// ─── Drag-to-reorder within the dialog ────────────────────────────────────────
function enableDragReorder(container) {
    let dragging = null;

    container.querySelectorAll(".uee-field-item").forEach((item) => {
        item.setAttribute("draggable", "true");

        item.addEventListener("dragstart", (e) => {
            dragging = item;
            item.style.opacity = "0.4";
            e.dataTransfer.effectAllowed = "move";
        });

        item.addEventListener("dragend", () => {
            dragging = null;
            item.style.opacity = "1";
            container.querySelectorAll(".uee-field-item").forEach(i => i.classList.remove("uee-drag-over"));
        });

        item.addEventListener("dragover", (e) => {
            e.preventDefault();
            if (item === dragging) return;
            container.querySelectorAll(".uee-field-item").forEach(i => i.classList.remove("uee-drag-over"));
            item.classList.add("uee-drag-over");
            const rect   = item.getBoundingClientRect();
            const mid    = rect.top + rect.height / 2;
            const parent = item.parentNode;
            if (e.clientY < mid) {
                parent.insertBefore(dragging, item);
            } else {
                parent.insertBefore(dragging, item.nextSibling);
            }
        });

        item.addEventListener("drop", (e) => {
            e.preventDefault();
        });
    });

    // Add drag-over style once
    if (!document.getElementById("uee-drag-style")) {
        const s = document.createElement("style");
        s.id = "uee-drag-style";
        s.textContent = `.uee-drag-over { outline: 2px dashed #E8A020 !important; background:rgba(232,160,32,.08) !important; }
        .uee-field-item { cursor: grab; }
        .uee-field-item:active { cursor: grabbing; }
        .uee-field-item .uee-drag-handle { color:#C8D0DF; font-size:12px; margin-right:2px; }`;
        document.head.appendChild(s);
    }
}

// ─── Collect ordered selections (respects drag reorder) ───────────────────────
function collectSelectionsExtended(fields) {
    const list      = document.getElementById("uee-field-list");
    const fieldMap  = Object.fromEntries(fields.map(f => [f.fieldname, f]));

    // Walk DOM order (respects drag reorder)
    const orderedItems = [...list.querySelectorAll(".uee-field-item")];
    const orderedFields  = [];
    const selectedFields = [];

    orderedItems.forEach((item) => {
        const fn  = item.dataset.fn;
        const chk = item.querySelector(".uee-chk");
        const f   = fieldMap[fn];
        if (!f) return;
        orderedFields.push(f);
        if (chk?.checked) selectedFields.push(f);
    });

    return {
        selectedFields,
        orderedFields: orderedFields.filter(f => selectedFields.includes(f)),
        scope:         document.querySelector('input[name="uee-scope"]:checked')?.value || "filtered",
        includeHeader: document.getElementById("uee-include-header")?.checked !== false,
        freezeHeader:  document.getElementById("uee-freeze-header")?.checked !== false,
        rowLimit:      parseInt(document.getElementById("uee-row-limit")?.value || "5000", 10),
    };
}

// ─── Restore saved column prefs into the dialog ───────────────────────────────
function restoreColumnPrefs(doctype, fields) {
    const prefs = UEEPrefs.getForDoctype(doctype);
    if (!prefs) return;

    const list = document.getElementById("uee-field-list");
    if (!list) return;

    // First, deselect all
    list.querySelectorAll(".uee-chk").forEach(c => { c.checked = false; });

    // Re-check saved selections
    const selectedSet = new Set(prefs.selected || []);
    list.querySelectorAll(".uee-field-item").forEach(item => {
        if (selectedSet.has(item.dataset.fn)) {
            const chk = item.querySelector(".uee-chk");
            if (chk) chk.checked = true;
        }
    });

    // Re-order items by saved order
    if (prefs.order && prefs.order.length > 0) {
        const orderMap = Object.fromEntries(prefs.order.map((fn, i) => [fn, i]));
        const groups   = list.querySelectorAll(".uee-group");

        groups.forEach(group => {
            const itemsContainer = group.querySelector(".uee-group-items") || group;
            const items = [...itemsContainer.querySelectorAll(".uee-field-item")];
            items.sort((a, b) => {
                const ai = orderMap[a.dataset.fn] ?? 9999;
                const bi = orderMap[b.dataset.fn] ?? 9999;
                return ai - bi;
            });
            items.forEach(item => itemsContainer.appendChild(item));
        });
    }

    // Update counter
    const counter = document.getElementById("uee-selected-count");
    if (counter) counter.textContent = selectedSet.size;
}

// ─── "Remember last selection" toggle ─────────────────────────────────────────
function addMemoryToggle(doctype) {
    const opts = document.querySelector(".uee-options");
    if (!opts) return;

    const prefs   = UEEPrefs.getForDoctype(doctype);
    const hasPrefs = !!prefs;

    const row = document.createElement("div");
    row.className = "uee-options-row";
    row.innerHTML = `
        <label class="uee-opt-item">
            <input type="checkbox" id="uee-remember" ${hasPrefs ? "checked" : ""} />
            <span class="uee-chk-box"></span>
            <span>Remember my column selection</span>
        </label>
        ${hasPrefs
            ? `<button class="uee-btn uee-btn-sm" id="uee-clear-prefs" style="margin-left:auto;
                border-color:#e04040;color:#e04040" title="Reset saved column preferences">
                ✕ Reset saved
               </button>`
            : ""}`;
    opts.appendChild(row);

    if (hasPrefs) {
        document.getElementById("uee-clear-prefs")?.addEventListener("click", () => {
            UEEPrefs.clearForDoctype(doctype);
            // Deselect everything then recheck all
            const list = document.getElementById("uee-field-list");
            list?.querySelectorAll(".uee-chk").forEach(c => { c.checked = true; });
            const counter = document.getElementById("uee-selected-count");
            if (counter) counter.textContent = list?.querySelectorAll(".uee-chk").length || 0;
            row.remove();
            frappe.show_alert({ message: "Saved preferences cleared", indicator: "orange" }, 3);
        });
    }
}

// ─── Override the base openExportDialog to add extended features ───────────────
// We patch in by overwriting the global after base script runs.
document.addEventListener("DOMContentLoaded", () => {
    setTimeout(() => {
        // Patch: intercept the Frappe list-view button click that base JS added,
        // replacing its handler with our extended version.
        _extendListViewPatch();
    }, 1500);
});

function _extendListViewPatch() {
    // Override the prototype patch from base JS — we re-apply with our version
    const _origRefresh = frappe.views.ListView.prototype.refresh;

    frappe.views.ListView.prototype.refresh = function (...args) {
        const result = _origRefresh.apply(this, args);
        setTimeout(() => _patchButtonExtended(this), 400);
        return result;
    };
}

function _patchButtonExtended(listView) {
    // Replace any existing UEE button click with our extended handler
    const $btn = listView.$page?.find?.(".uee-list-btn");
    if (!$btn || !$btn.length) return;

    $btn.off("click").on("click", function (e) {
        // Shift+click = quick export (all fields, current filters, no dialog)
        if (e.shiftKey) {
            _quickExport(listView);
            return;
        }
        _openExportDialogExtended(listView);
    });

    // Update tooltip
    $btn.attr("title", "Export to Excel (Shift+Click for quick export)");
}

// ─── Quick export: no dialog, all fields, current filters ────────────────────
async function _quickExport(listView) {
    const meta = frappe.get_meta(listView.doctype);
    if (!meta) return;

    // Use getExportableFields from base script (global scope)
    const EXCLUDED_FIELDTYPES = new Set([
        "Column Break","Section Break","Tab Break","Image","Attach","Attach Image",
        "MultiSelect","HTML","HTML Editor","Markdown Editor","Code","Geolocation",
        "Fold","Heading","Button","Signature","Color","Barcode","Icon",
    ]);

    const fields = [{ fieldname:"name", label:"ID", fieldtype:"Data" }];
    (meta.fields || []).forEach(f => {
        if (!EXCLUDED_FIELDTYPES.has(f.fieldtype) && !f.hidden && f.fieldname) {
            fields.push({ fieldname:f.fieldname, label:f.label||f.fieldname, fieldtype:f.fieldtype });
        }
    });

    await triggerExportFull(listView, fields, {
        selectedFields: fields,
        orderedFields:  fields,
        scope:          "filtered",
        includeHeader:  true,
        freezeHeader:   true,
        rowLimit:       5000,
    });
}

// ─── Extended dialog opener ───────────────────────────────────────────────────
function _openExportDialogExtended(listView) {
    // Inject drag style + memory toggle CSS additions
    if (!document.getElementById("uee-ext-style")) {
        const s = document.createElement("style");
        s.id = "uee-ext-style";
        s.textContent = `
.uee-pref-badge { font-size:10px; padding:2px 7px; border-radius:10px;
  background:#2EA87E; color:#fff; font-weight:700; margin-left:6px; }`;
        document.head.appendChild(s);
    }

    const meta = frappe.get_meta(listView.doctype);
    if (!meta) {
        frappe.msgprint({ title: "Metadata Missing", message: `Cannot load metadata for ${listView.doctype}` });
        return;
    }

    // getExportableFields is defined in base JS (same global scope)
    const EXCLUDED_FIELDTYPES = new Set([
        "Column Break","Section Break","Tab Break","Image","Attach","Attach Image",
        "MultiSelect","HTML","HTML Editor","Markdown Editor","Code","Geolocation",
        "Fold","Heading","Button","Signature","Color","Barcode","Icon",
    ]);

    const fields = [{ fieldname:"name", label:"ID", fieldtype:"Data" }];
    (meta.fields || []).forEach(f => {
        if (!EXCLUDED_FIELDTYPES.has(f.fieldtype) && !f.hidden && f.fieldname) {
            fields.push({ fieldname:f.fieldname, label:f.label||f.fieldname, fieldtype:f.fieldtype });
        }
    });

    const hasSavedPrefs = !!UEEPrefs.getForDoctype(listView.doctype);

    const dialog = new frappe.ui.Dialog({
        title: "",
        size: "large",
        fields: [
            {
                fieldtype: "HTML",
                fieldname: "column_selector",
                // buildDialogHTML is from base JS
                options: (typeof buildDialogHTML === "function")
                    ? buildDialogHTML(fields, listView.doctype)
                    : `<p>Base script not loaded. Ensure universal_excel_export.js is included first.</p>`,
            },
        ],
        primary_action_label: `<svg width="13" height="13" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" stroke-width="2.5" style="vertical-align:middle;margin-right:5px">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
            </svg>Export Excel`,
        primary_action() {
            const shouldRemember = document.getElementById("uee-remember")?.checked;
            const selections = collectSelectionsExtended(fields);
            if (!shouldRemember) {
                UEEPrefs.clearForDoctype(listView.doctype);
            }
            dialog.hide();
            triggerExportFull(listView, fields, selections);
        },
    });

    // Style primary button
    setTimeout(() => {
        dialog.$wrapper.find(".btn-primary").css({
            background: "#E8A020", borderColor: "#E8A020", fontWeight: "700", fontSize: "13px",
        });
    }, 50);

    dialog.show();

    setTimeout(() => {
        // Wire base events (search, checkboxes, all/none)
        if (typeof wireDialogEvents === "function") wireDialogEvents(fields, fields.length);

        // Enable drag-reorder
        const list = document.getElementById("uee-field-list");
        if (list) enableDragReorder(list);

        // Restore saved prefs
        restoreColumnPrefs(listView.doctype, fields);

        // Add memory toggle
        addMemoryToggle(listView.doctype);

        // Hint badge if prefs exist
        if (hasSavedPrefs) {
            const counter = document.getElementById("uee-counter");
            if (counter) {
                counter.innerHTML += `<span class="uee-pref-badge">✓ Preferences restored</span>`;
            }
        }

        // Add drag hint
        const toolbar = document.querySelector(".uee-toolbar");
        if (toolbar) {
            const hint = document.createElement("div");
            hint.style.cssText = "font-size:10.5px;color:#6b7a99;margin-top:4px;width:100%;";
            hint.textContent = "💡 Drag rows to reorder columns in export";
            toolbar.parentNode.insertBefore(hint, toolbar.nextSibling);
        }
    }, 100);
}