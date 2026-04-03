frappe.pages['stock-recon'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Stock Reconciliation',
        single_column: true
    });

    new ecclesia.StockRecon(page);
}

ecclesia.StockRecon = class StockRecon {
    constructor(page) {
        this.page = page;
        this.wrapper = $(page.body);
        this.items = [];
        this.submitted_entries = [];
        this.entry_generated = false;
        this.doc_ref = this.generate_ref();
        this.make();
        this.bind_events();
        this.set_default_date();
        this.add_custom_styles();
    }

    add_custom_styles() {
        const style = `
            <style>
                .stock-recon-page .recon-status {
                    background: linear-gradient(135deg, #ffffff 0%, #fef9e8 100%);
                    border-radius: 20px;
                    padding: 12px 24px;
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    margin-bottom: 24px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.03);
                    border: 1px solid #ffe6c7;
                }
                .stock-recon-page .recon-status.draft { background: linear-gradient(135deg, #fff9ef, #fff4e5); border-color: #ffd9a5; }
                .stock-recon-page .recon-status.pending { background: linear-gradient(135deg, #eff6ff, #e8f0fe); border-color: #bdd9ff; }
                .stock-recon-page .recon-status.submitted { background: linear-gradient(135deg, #e8f5ed, #dff0e3); border-color: #b8e0c2; }
                .stock-recon-page .status-dot {
                    width: 12px;
                    height: 12px;
                    border-radius: 50%;
                    background: #f5b042;
                    display: inline-block;
                    box-shadow: 0 0 0 3px #fff0df;
                }
                .stock-recon-page .recon-status.draft .status-dot { background: #f5a623; }
                .stock-recon-page .recon-status.pending .status-dot { background: #3b82f6; }
                .stock-recon-page .recon-status.submitted .status-dot { background: #10b981; }
                .stock-recon-page .status-text { font-weight: 500; font-size: 0.85rem; color: #5a4a2a; }
                .stock-recon-page .doc-ref-badge {
                    margin-left: auto;
                    background: #fff3e0;
                    padding: 4px 14px;
                    border-radius: 40px;
                    font-family: monospace;
                    font-size: 0.75rem;
                    font-weight: 600;
                    color: #c47a2e;
                }
                .stock-recon-page .recon-card {
                    background: #ffffff;
                    border-radius: 24px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.02);
                    border: 1px solid #f0ede5;
                    padding: 24px 28px;
                    margin-bottom: 24px;
                    transition: all 0.2s ease;
                }
                .stock-recon-page .recon-card:hover { box-shadow: 0 8px 24px rgba(0,0,0,0.05); border-color: #ffe0b5; }
                .stock-recon-page .recon-card-title {
                    font-weight: 600;
                    font-size: 1rem;
                    margin-bottom: 20px;
                    color: #4b3b2a;
                    border-left: 4px solid #f5a623;
                    padding-left: 14px;
                }
                .stock-recon-page .recon-form-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
                    gap: 20px 28px;
                }
                .stock-recon-page .recon-field {
                    display: flex;
                    flex-direction: column;
                    gap: 6px;
                }
                .stock-recon-page .recon-field label {
                    font-size: 0.7rem;
                    font-weight: 600;
                    text-transform: uppercase;
                    color: #9b7e5f;
                }
                .stock-recon-page .form-control, 
                .stock-recon-page select.form-control, 
                .stock-recon-page textarea.form-control {
                    border-radius: 14px;
                    border: 1.5px solid #f0e4d4;
                    padding: 10px 14px;
                    font-size: 0.85rem;
                    transition: 0.2s;
                    background: #fefefc;
                }
                .stock-recon-page .form-control:focus, 
                .stock-recon-page select:focus {
                    border-color: #f5a623;
                    outline: none;
                    box-shadow: 0 0 0 3px rgba(245,166,35,0.12);
                }
                .stock-recon-page .upload-zone {
                    position: relative;
                    border: 2px dashed #f0e0cc;
                    border-radius: 28px;
                    background: #fffdf9;
                    padding: 28px 20px;
                    text-align: center;
                    cursor: pointer;
                    transition: 0.2s;
                }
                .stock-recon-page .upload-zone.drag-over { border-color: #f5a623; background: #fff9ef; }
                .stock-recon-page .upload-icon { font-size: 36px; color: #e6b87e; }
                .stock-recon-page .upload-text { font-weight: 500; color: #b48a54; }
                .stock-recon-page .btn {
                    border-radius: 40px;
                    font-weight: 500;
                    padding: 8px 20px;
                    font-size: 0.8rem;
                    transition: all 0.2s;
                    cursor: pointer;
                    border: none;
                }
                .stock-recon-page .btn-primary {
                    background: linear-gradient(135deg, #f5a623, #e8951a);
                    color: white;
                }
                .stock-recon-page .btn-primary:hover { background: linear-gradient(135deg, #e8951a, #dc8510); transform: translateY(-1px); }
                .stock-recon-page .btn-default {
                    background: #fefaf5;
                    color: #7c623f;
                    border: 1px solid #f0e2d2;
                }
                .stock-recon-page .btn-default:hover { background: #fff5e8; }
                .stock-recon-page .btn-success { background: linear-gradient(135deg, #10b981, #0f9a6b); color: white; }
                .stock-recon-page .btn-danger { background: linear-gradient(135deg, #ef4444, #dc2626); color: white; }
                .stock-recon-page .btn-sm { padding: 4px 12px; font-size: 0.7rem; }
                .stock-recon-page .table {
                    width: 100%;
                    font-size: 0.78rem;
                    border-collapse: collapse;
                    background: white;
                    border-radius: 20px;
                    overflow: hidden;
                }
                .stock-recon-page .table th {
                    background: #fefaf5;
                    padding: 14px 10px;
                    font-weight: 600;
                    color: #7c623f;
                    border-bottom: 2px solid #f7ede2;
                }
                .stock-recon-page .table td {
                    padding: 12px 10px;
                    border-bottom: 1px solid #f7f0e8;
                }
                .stock-recon-page .indicator-pill {
                    display: inline-block;
                    padding: 4px 12px;
                    border-radius: 40px;
                    font-size: 0.7rem;
                    font-weight: 600;
                }
                .stock-recon-page .indicator-pill.green { background: #e6f9ef; color: #0f7b46; }
                .stock-recon-page .indicator-pill.blue { background: #feeedb; color: #e67e22; }
                .stock-recon-page .indicator-pill.red { background: #ffe7e5; color: #e25c4a; }
                .stock-recon-page .text-right { text-align: right; }
                .stock-recon-page .text-success { color: #10b981; font-weight: 600; }
                .stock-recon-page .text-danger { color: #ef4444; font-weight: 600; }
                .stock-recon-page .recon-metrics-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 16px;
                }
                .stock-recon-page .recon-metric-card {
                    background: #fffefb;
                    border-radius: 20px;
                    padding: 18px 16px;
                    border: 1px solid #f5e8db;
                }
                .stock-recon-page .metric-value { font-size: 1.6rem; font-weight: 700; color: #5c4a32; }
                .stock-recon-page .entry-ref-badge {
                    background: #f5a623;
                    color: white;
                    padding: 5px 16px;
                    border-radius: 40px;
                    font-size: 0.75rem;
                }
                .stock-recon-page .alert {
                    padding: 12px 18px;
                    border-radius: 20px;
                    margin-bottom: 20px;
                    font-size: 0.8rem;
                }
                .stock-recon-page .alert-warning { background: #fff9ef; border-left: 4px solid #f5a623; }
                .stock-recon-page .alert-success { background: #ecfdf5; border-left: 4px solid #10b981; }
                .stock-recon-page .alert-info { background: #eff6ff; border-left: 4px solid #3b82f6; }
                .stock-recon-page .alert-danger { background: #fef2f2; border-left: 4px solid #ef4444; }
                .loading-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0,0,0,0.5);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 9999;
                }
                .loading-spinner {
                    background: white;
                    padding: 20px 40px;
                    border-radius: 20px;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 12px;
                }
            </style>
        `;
        $('head').append(style);
    }

    generate_ref() {
        const now = new Date();
        const rand = Math.floor(Math.random() * 9000) + 1000;
        return `SRECON-${now.getFullYear()}${String(now.getMonth()+1).padStart(2,'0')}${String(now.getDate()).padStart(2,'0')}-${rand}`;
    }

    set_default_date() {
        const today = frappe.datetime.get_today();
        this.wrapper.find('#reconDate').val(today);
        this.wrapper.find('#docRef').val(this.doc_ref);
    }

    make() {
        this.wrapper.html(`
            <div class="container-fluid stock-recon-page" style="padding: 20px;">
                <div class="recon-status draft" id="statusStrip">
                    <span class="status-dot"></span>
                    <span class="status-text" id="statusText">📋 DRAFT · New reconciliation document</span>
                    <span class="doc-ref-badge" id="docRefBadge">📄 ${this.doc_ref}</span>
                </div>
                <div id="alertArea"></div>

                <div class="recon-card">
                    <div class="recon-card-title">📋 Document Header</div>
                    <div class="recon-form-grid">
                        <div class="recon-field"><label>📅 Reconciliation Date *</label><input type="date" id="reconDate" class="form-control"></div>
                        <div class="recon-field"><label>🏭 Warehouse *</label><select id="warehouse" class="form-control"><option value="">— Select warehouse —</option></select></div>
                        <div class="recon-field"><label>🏢 Company *</label><select id="company" class="form-control"><option value="">— Select company —</option></select></div>
                        <div class="recon-field"><label>📊 Fiscal Period</label><select id="fiscalPeriod" class="form-control"><option value="">— Select period —</option></select></div>
                        <div class="recon-field"><label>👤 Prepared By</label><input type="text" id="preparedBy" class="form-control" placeholder="Staff name"></div>
                        <div class="recon-field"><label>✓ Approved By</label><input type="text" id="approvedBy" class="form-control" placeholder="Supervisor name"></div>
                        <div class="recon-field"><label>💰 Currency</label><select id="currency" class="form-control"><option value="NGN">🇳🇬 NGN</option><option value="USD">🇺🇸 USD</option><option value="GBP">🇬🇧 GBP</option><option value="EUR">🇪🇺 EUR</option></select></div>
                        <div class="recon-field span-2"><label>📝 Remarks</label><textarea id="remarks" class="form-control" rows="2" placeholder="Notes..."></textarea></div>
                        <div class="recon-field"><label>🔖 Reference No.</label><input type="text" id="docRef" class="form-control" readonly></div>
                    </div>
                </div>

                <div class="recon-card">
                    <div class="recon-card-title">📤 Upload Stock Data</div>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;">
                        <div>
                            <div class="upload-zone" id="uploadZone">
                                <div class="upload-icon">📁</div>
                                <div class="upload-text">Drop CSV / TSV or click to browse</div>
                                <div class="upload-hint">Columns: Item Code, Item Name, Physical Count Qty, Valuation Price</div>
                                <input type="file" id="fileInput" accept=".csv,.tsv" style="position:absolute;inset:0;opacity:0;cursor:pointer;width:100%;height:100%;">
                                <div class="upload-file-name" id="uploadedFileName" style="display:none; margin-top:10px;"></div>
                            </div>
                            <div style="margin-top:12px;display:flex;gap:8px;">
                                <button type="button" class="btn btn-default btn-sm" id="loadSampleBtn">📊 Load Sample</button>
                                <button type="button" class="btn btn-default btn-sm" id="downloadTemplateBtn">📥 Template</button>
                                <button type="button" class="btn btn-default btn-sm" id="fetchSystemDataBtn">🔄 Fetch System Data</button>
                            </div>
                        </div>
                        <div>
                            <div class="recon-card-title" style="font-size:11px; margin-bottom:12px;">✏️ Manual Entry</div>
                            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                                <div class="recon-field"><label>Item Code</label><input type="text" id="m_code" class="form-control" placeholder="SKU-001"></div>
                                <div class="recon-field"><label>Item Name</label><input type="text" id="m_name" class="form-control" placeholder="Product"></div>
                                <div class="recon-field"><label>Physical Count</label><input type="number" id="m_physQty" class="form-control" placeholder="0"></div>
                                <div class="recon-field"><label>Valuation Price</label><input type="number" id="m_valPrice" class="form-control" placeholder="0.00"></div>
                            </div>
                            <button type="button" class="btn btn-default btn-sm" id="addRowBtn" style="width:100%;margin-top:12px;">+ Add Row</button>
                        </div>
                    </div>
                </div>

                <div id="tableSection" style="display:none;">
                    <div class="recon-card">
                        <div class="recon-card-title">📊 Reconciliation Lines <span id="rowCountBadge" style="margin-left:auto;background:#fef2e6;padding:2px 12px;border-radius:40px;">0 items</span></div>
                        <div style="display:flex;gap:12px;margin-bottom:12px;flex-wrap:wrap;">
                            <input type="text" id="searchInput" class="form-control" placeholder="🔍 Search..." style="max-width:220px;">
                            <select id="filterStatus" class="form-control" style="max-width:150px;">
                                <option value="all">All items</option>
                                <option value="surplus">📈 Surplus</option>
                                <option value="deficit">📉 Deficit</option>
                                <option value="ok">✅ Match</option>
                            </select>
                            <button type="button" class="btn btn-default btn-sm" id="clearTableBtn">🗑️ Clear</button>
                        </div>
                    </div>
                    <div class="table-responsive">
                        <table class="table" id="reconTable">
                            <thead>
                                <tr>
                                    <th>#</th><th>Item Code</th><th>Item Name</th>
                                    <th class="text-right">System Qty</th><th class="text-right">System Rate</th>
                                    <th class="text-right">System Value</th>
                                    <th class="text-right">Physical Qty</th><th class="text-right">New Rate</th>
                                    <th class="text-right">New Value</th>
                                    <th class="text-right">Qty Diff</th><th class="text-right">Value Diff</th>
                                    <th>Status</th><th>Action</th>
                                </tr>
                            </thead>
                            <tbody id="reconTableBody"></tbody>
                            <tfoot id="reconTableFoot"></tfoot>
                        </table>
                    </div>
                </div>

                <div id="summarySection" style="display:none;">
                    <div class="recon-card">
                        <div class="recon-card-title">📈 Analytics</div>
                        <div class="recon-metrics-grid" id="metricsGrid"></div>
                    </div>
                </div>

                <div id="generateSection" style="display:none;">
                    <div class="recon-card">
                        <div class="recon-card-title">🏭 Create Stock Reconciliation</div>
                        <div class="alert alert-info">Click Generate to review adjustments, then create ERPNext Stock Reconciliation</div>
                        <div style="display:flex;gap:10px;">
                            <button type="button" class="btn btn-primary" id="generateBtn">✨ Generate Reconciliation</button>
                            <button type="button" class="btn btn-default" id="recalcBtn">🔄 Recalculate</button>
                            <button type="button" class="btn btn-default" id="exportBtn">📎 Export CSV</button>
                        </div>
                    </div>
                </div>

                <div id="entrySection" style="display:none;">
                    <div class="recon-card">
                        <div style="display:flex;justify-content:space-between;">
                            <div class="recon-card-title">📄 Stock Reconciliation Preview</div>
                            <span class="entry-ref-badge" id="entryRef"></span>
                        </div>
                        <div id="entryMeta" style="margin:16px 0;padding:12px;background:#fefaf5;border-radius:16px;"></div>
                        <div class="table-responsive">
                            <table class="table" id="entryTable">
                                <thead>
                                    <tr>
                                        <th>#</th><th>Item Code</th><th>Item Name</th>
                                        <th class="text-right">Current Qty (System)</th>
                                        <th class="text-right">Current Rate</th>
                                        <th class="text-right">Physical Qty</th>
                                        <th class="text-right">New Rate</th>
                                        <th class="text-right">Qty Difference</th>
                                        <th class="text-right">Value Difference</th>
                                        <th>Type</th>
                                    </tr>
                                </thead>
                                <tbody id="entryTableBody"></tbody>
                                <tfoot id="entryTableFoot"></tfoot>
                            </table>
                        </div>
                        <div class="alert alert-warning" id="submitWarning">⚠️ Review carefully. Submitting will create ERPNext Stock Reconciliation in DRAFT mode.</div>
                        <div style="display:flex;gap:10px;">
                            <button type="button" class="btn btn-success" id="submitBtn">✅ Create Stock Reconciliation in ERPNext</button>
                            <button type="button" class="btn btn-danger" id="voidBtn">🗑️ Void</button>
                        </div>
                    </div>
                </div>
            </div>
        `);
        this.load_warehouses();
        this.load_companies();
        this.load_fiscal_periods();
    }

    load_warehouses() {
        frappe.call({
            method: 'frappe.client.get_list',
            args: { doctype: 'Warehouse', fields: ['name'], limit_page_length: 100 },
            callback: (r) => {
                if (r.message && r.message.length) {
                    const sel = this.wrapper.find('#warehouse');
                    r.message.forEach(w => sel.append(`<option value="${w.name}">🏭 ${w.name}</option>`));
                }
            }
        });
    }

    load_companies() {
        frappe.call({
            method: 'frappe.client.get_list',
            args: { doctype: 'Company', fields: ['name'], limit_page_length: 100 },
            callback: (r) => {
                if (r.message && r.message.length) {
                    const sel = this.wrapper.find('#company');
                    r.message.forEach(c => sel.append(`<option value="${c.name}">🏢 ${c.name}</option>`));
                    const default_company = frappe.defaults.get_default('company');
                    if (default_company) sel.val(default_company);
                }
            }
        });
    }

    load_fiscal_periods() {
        frappe.call({
            method: 'frappe.client.get_list',
            args: { doctype: 'Fiscal Year', fields: ['name'], limit_page_length: 20 },
            callback: (r) => {
                if (r.message && r.message.length) {
                    const sel = this.wrapper.find('#fiscalPeriod');
                    r.message.forEach(f => sel.append(`<option value="${f.name}">📅 ${f.name}</option>`));
                }
            }
        });
    }

    bind_events() {
        this.wrapper.find('#fileInput').off('change').on('change', (e) => this.handle_file_upload(e));
        this.wrapper.find('#loadSampleBtn').off('click').on('click', () => this.load_sample_data());
        this.wrapper.find('#fetchSystemDataBtn').off('click').on('click', () => this.fetch_system_data());
        this.wrapper.find('#downloadTemplateBtn').off('click').on('click', () => this.download_template());
        this.wrapper.find('#addRowBtn').off('click').on('click', () => this.add_manual_row());
        this.wrapper.find('#searchInput').off('input').on('input', () => this.render_table());
        this.wrapper.find('#filterStatus').off('change').on('change', () => this.render_table());
        this.wrapper.find('#clearTableBtn').off('click').on('click', () => this.clear_table());
        this.wrapper.find('#recalcBtn').off('click').on('click', () => this.recalculate());
        this.wrapper.find('#exportBtn').off('click').on('click', () => this.export_csv());
        this.wrapper.find('#generateBtn').off('click').on('click', () => this.generate_stock_reconciliation());
        this.wrapper.find('#submitBtn').off('click').on('click', () => this.create_stock_reconciliation_in_erpnext());
        this.wrapper.find('#voidBtn').off('click').on('click', () => this.void_entry());

        const zone = this.wrapper.find('#uploadZone')[0];
        if (zone) {
            zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('drag-over'); });
            zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
            zone.addEventListener('drop', (e) => {
                e.preventDefault();
                zone.classList.remove('drag-over');
                const file = e.dataTransfer.files[0];
                if (file) this.process_file(file);
            });
        }
    }

    async fetch_system_data() {
        if (!this.wrapper.find('#warehouse').val()) {
            frappe.msgprint('Please select a warehouse first');
            return;
        }
        
        const warehouse = this.wrapper.find('#warehouse').val();
        const item_codes = this.items.map(i => i.code);
        
        if (item_codes.length === 0) {
            frappe.msgprint('No items to fetch data for');
            return;
        }
        
        this.show_loading('Fetching current system data...');
        
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Bin',
                filters: {
                    warehouse: warehouse,
                    item_code: ['in', item_codes]
                },
                fields: ['item_code', 'actual_qty', 'valuation_rate']
            },
            callback: (r) => {
                this.hide_loading();
                if (r.message) {
                    const system_data = {};
                    r.message.forEach(bin => {
                        system_data[bin.item_code] = {
                            current_qty: bin.actual_qty || 0,
                            current_rate: bin.valuation_rate || 0
                        };
                    });
                    
                    // Update items with system data
                    this.items = this.items.map(item => {
                        const sys = system_data[item.code] || { current_qty: 0, current_rate: 0 };
                        item.current_qty = sys.current_qty;
                        item.current_rate = sys.current_rate;
                        item.sysVal = this.round2(sys.current_qty * sys.current_rate);
                        item.curQty = sys.current_qty;
                        item.curPrice = sys.current_rate;
                        
                        // Recalculate differences
                        const diffQty = this.round2(item.physQty - sys.current_qty);
                        const diffValue = this.round2((item.physQty * item.valPrice) - (sys.current_qty * sys.current_rate));
                        item.diffQty = diffQty;
                        item.netAdjQty = diffQty;
                        item.netAdjAmt = diffValue;
                        item.status = Math.abs(diffQty) < 0.001 ? 'ok' : (diffQty > 0 ? 'surplus' : 'deficit');
                        
                        return item;
                    });
                    
                    this.render_table();
                    this.render_metrics();
                    frappe.show_alert({ message: 'System data fetched successfully', indicator: 'green' });
                }
            }
        });
    }

    handle_file_upload(e) {
        const file = e.target.files[0];
        if (file) this.process_file(file);
    }

    process_file(file) {
        const ext = file.name.split('.').pop().toLowerCase();
        if (!['csv', 'tsv'].includes(ext)) {
            this.show_alert('warn', 'Unsupported file type. Please upload CSV or TSV.');
            return;
        }
        this.wrapper.find('#uploadedFileName').html(`📄 ${file.name}`).show();
        
        const reader = new FileReader();
        reader.onload = (evt) => {
            const sep = ext === 'tsv' ? '\t' : this.detect_separator(evt.target.result);
            const rows = this.parse_csv(evt.target.result, sep);
            this.process_rows(rows, file.name);
        };
        reader.readAsText(file);
    }

    detect_separator(csv) {
        const line = csv.split('\n')[0];
        const tabs = (line.match(/\t/g) || []).length;
        const commas = (line.match(/,/g) || []).length;
        return tabs >= commas ? '\t' : ',';
    }

    parse_csv(text, sep) {
        const lines = text.trim().split('\n').filter(l => l.trim());
        if (!lines.length) return [];
        const headers = lines[0].split(sep).map(h => h.trim().replace(/"/g, ''));
        return lines.slice(1).map(line => {
            const vals = line.split(sep).map(v => v.trim().replace(/"/g, ''));
            const obj = {};
            headers.forEach((h, i) => obj[h] = vals[i] || '');
            return obj;
        });
    }

    process_rows(rows, filename) {
        if (!rows.length) {
            this.show_alert('warn', 'File appears empty.');
            return;
        }
        
        const colMap = this.build_column_map(Object.keys(rows[0]));
        const parsed = rows.map((row, idx) => {
            const physQty = this.parse_num(row[colMap.physQty]);
            const valPrice = this.parse_num(row[colMap.valPrice]);
            return {
                id: idx + 1,
                code: row[colMap.code] || `ITEM-${String(idx+1).padStart(3, '0')}`,
                name: row[colMap.name] || 'Unknown Item',
                current_qty: 0,
                current_rate: 0,
                curQty: 0,
                curPrice: 0,
                sysVal: 0,
                physQty: physQty,
                valPrice: valPrice,
                valNow: this.round2(physQty * valPrice),
                diffQty: 0,
                netAdjQty: 0,
                netAdjAmt: 0,
                status: 'pending'
            };
        });
        
        this.items = parsed;
        this.render_table();
        this.render_metrics();
        this.clear_alerts();
        
        // Prompt to fetch system data
        if (this.wrapper.find('#warehouse').val()) {
            frappe.confirm('Do you want to fetch current system data for these items?', () => {
                this.fetch_system_data();
            });
        }
        
        frappe.show_alert({ message: `✅ Loaded ${parsed.length} items from ${filename}`, indicator: 'green' });
        this.set_status('draft');
    }

    build_column_map(headers) {
        const lower = headers.map(h => h.toLowerCase());
        const find = (...keys) => {
            for (const k of keys) {
                const i = lower.findIndex(h => h.includes(k));
                if (i >= 0) return headers[i];
            }
            return headers[0];
        };
        return {
            code: find('code', 'sku', 'id', 'item code'),
            name: find('name', 'description', 'product', 'item name'),
            physQty: find('physical', 'count', 'phys qty', 'physqty', 'counted', 'qty'),
            valPrice: find('valuation price', 'val price', 'val_price', 'new price', 'rate', 'price')
        };
    }

    round2(n) { return Math.round(n * 100) / 100; }
    parse_num(v) { if (!v && v !== 0) return 0; const n = parseFloat(String(v).replace(/[^0-9.\-]/g, '')); return isNaN(n) ? 0 : n; }
    fmt(n) { return Number(n).toLocaleString('en-NG', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
    fmt_qty(n) { return Number(n).toLocaleString('en-NG', { minimumFractionDigits: 0, maximumFractionDigits: 4 }); }

    apply_filter() {
        const q = this.wrapper.find('#searchInput').val().toLowerCase();
        const f = this.wrapper.find('#filterStatus').val();
        return this.items.filter(item => {
            const mq = !q || item.code.toLowerCase().includes(q) || item.name.toLowerCase().includes(q);
            const mf = f === 'all' || item.status === f;
            return mq && mf;
        });
    }

    render_table() {
        const filtered = this.apply_filter();
        const tbody = this.wrapper.find('#reconTableBody');
        
        if (filtered.length === 0) {
            tbody.html('<tr><td colspan="13" class="text-center">No items to display</td></tr>');
        } else {
            tbody.html(filtered.map((item, idx) => {
                const qtyDiff = this.round2(item.physQty - (item.current_qty || 0));
                const valueDiff = this.round2((item.physQty * item.valPrice) - ((item.current_qty || 0) * (item.current_rate || 0)));
                const badge = item.status === 'ok' ? '<span class="indicator-pill green">✓ Match</span>' : 
                              (item.status === 'surplus' ? '<span class="indicator-pill blue">📈 Surplus</span>' : 
                              '<span class="indicator-pill red">📉 Deficit</span>');
                return `<tr>
                    <td>${idx + 1}</td>
                    <td><code>${item.code}</code></td>
                    <td>${item.name}</td>
                    <td class="text-right">${this.fmt_qty(item.current_qty || 0)}</td>
                    <td class="text-right">${this.fmt(item.current_rate || 0)}</td>
                    <td class="text-right">${this.fmt((item.current_qty || 0) * (item.current_rate || 0))}</td>
                    <td class="text-right">${this.fmt_qty(item.physQty)}</td>
                    <td class="text-right">${this.fmt(item.valPrice)}</td>
                    <td class="text-right">${this.fmt(item.physQty * item.valPrice)}</td>
                    <td class="text-right ${qtyDiff > 0 ? 'text-success' : qtyDiff < 0 ? 'text-danger' : ''}">${qtyDiff > 0 ? '+' : ''}${this.fmt_qty(qtyDiff)}</td>
                    <td class="text-right ${valueDiff > 0 ? 'text-success' : valueDiff < 0 ? 'text-danger' : ''}">${valueDiff > 0 ? '+' : ''}${this.fmt(valueDiff)}</td>
                    <td class="text-center">${badge}</td>
                    <td class="text-center">
                        <button class="btn btn-default btn-sm edit-row" data-id="${item.id}">✏️</button>
                        <button class="btn btn-danger btn-sm remove-row" data-id="${item.id}">🗑️</button>
                    </td>
                 </tr>`;
            }).join(''));
        }
        
        this.wrapper.find('#rowCountBadge').text(`${filtered.length} items`);
        this.wrapper.find('#tableSection').show();
        this.wrapper.find('#summarySection').show();
        this.wrapper.find('#generateSection').show();
        
        this.wrapper.find('.edit-row').off('click').on('click', (e) => {
            const id = parseInt($(e.currentTarget).data('id'));
            this.edit_row(id);
        });
        this.wrapper.find('.remove-row').off('click').on('click', (e) => {
            const id = parseInt($(e.currentTarget).data('id'));
            this.remove_row(id);
        });
    }

    edit_row(id) {
        const item = this.items.find(i => i.id === id);
        if (!item) return;
        
        const newPhysQty = prompt(`Edit Physical Qty for ${item.name}:`, item.physQty);
        if (newPhysQty !== null) {
            item.physQty = this.parse_num(newPhysQty);
            const newValPrice = prompt(`Edit Valuation Price:`, item.valPrice);
            if (newValPrice !== null) {
                item.valPrice = this.parse_num(newValPrice);
            }
            item.valNow = this.round2(item.physQty * item.valPrice);
            
            const qtyDiff = this.round2(item.physQty - (item.current_qty || 0));
            const valueDiff = this.round2((item.physQty * item.valPrice) - ((item.current_qty || 0) * (item.current_rate || 0)));
            item.diffQty = qtyDiff;
            item.netAdjQty = qtyDiff;
            item.netAdjAmt = valueDiff;
            item.status = Math.abs(qtyDiff) < 0.001 ? 'ok' : (qtyDiff > 0 ? 'surplus' : 'deficit');
            
            this.render_table();
            this.render_metrics();
            if (this.entry_generated) {
                this.entry_generated = false;
                this.wrapper.find('#entrySection').hide();
                this.show_alert('warn', 'Data changed — please regenerate.');
            }
        }
    }

    remove_row(id) {
        this.items = this.items.filter(i => i.id !== id);
        if (this.items.length) {
            this.render_table();
            this.render_metrics();
        } else {
            this.clear_table();
        }
        if (this.entry_generated) {
            this.entry_generated = false;
            this.wrapper.find('#entrySection').hide();
        }
    }

    render_metrics() {
        const items = this.items;
        const totalSystemQty = items.reduce((a, i) => a + (i.current_qty || 0), 0);
        const totalPhysicalQty = items.reduce((a, i) => a + i.physQty, 0);
        const totalSystemValue = items.reduce((a, i) => a + ((i.current_qty || 0) * (i.current_rate || 0)), 0);
        const totalPhysicalValue = items.reduce((a, i) => a + (i.physQty * i.valPrice), 0);
        const qtyDiff = totalPhysicalQty - totalSystemQty;
        const valueDiff = totalPhysicalValue - totalSystemValue;
        
        this.wrapper.find('#metricsGrid').html(`
            <div class="recon-metric-card">
                <div class="metric-label">Total Items</div>
                <div class="metric-value">${items.length}</div>
                <div class="metric-sub">${items.filter(i => i.status !== 'ok').length} adjusted</div>
            </div>
            <div class="recon-metric-card">
                <div class="metric-label">System vs Physical</div>
                <div class="metric-value">${this.fmt_qty(totalSystemQty)} → ${this.fmt_qty(totalPhysicalQty)}</div>
                <div class="metric-sub">Qty Diff: ${qtyDiff > 0 ? '+' : ''}${this.fmt_qty(qtyDiff)}</div>
            </div>
            <div class="recon-metric-card">
                <div class="metric-label">Value Difference</div>
                <div class="metric-value ${valueDiff > 0 ? 'text-success' : valueDiff < 0 ? 'text-danger' : ''}">${valueDiff > 0 ? '+' : ''}${this.fmt(valueDiff)}</div>
                <div class="metric-sub">System: ${this.fmt(totalSystemValue)}</div>
            </div>
        `);
    }

    recalculate() {
        this.items = this.items.map(item => {
            const qtyDiff = this.round2(item.physQty - (item.current_qty || 0));
            const valueDiff = this.round2((item.physQty * item.valPrice) - ((item.current_qty || 0) * (item.current_rate || 0)));
            item.diffQty = qtyDiff;
            item.netAdjQty = qtyDiff;
            item.netAdjAmt = valueDiff;
            item.status = Math.abs(qtyDiff) < 0.001 ? 'ok' : (qtyDiff > 0 ? 'surplus' : 'deficit');
            return item;
        });
        this.render_table();
        this.render_metrics();
        if (this.entry_generated) {
            this.entry_generated = false;
            this.wrapper.find('#entrySection').hide();
            this.show_alert('warn', 'Data changed — please regenerate.');
        }
        frappe.show_alert({ message: '🔄 Recalculated', indicator: 'blue' });
    }

    generate_stock_reconciliation() {
        if (!this.validate_header()) return;
        
        const items_with_changes = this.items.filter(i => i.status !== 'ok');
        if (!items_with_changes.length) {
            this.show_alert('warn', 'No changes detected. Nothing to reconcile.');
            return;
        }
        
        const warehouse = this.wrapper.find('#warehouse').val();
        const date = this.wrapper.find('#reconDate').val();
        const company = this.wrapper.find('#company').val();
        
        this.wrapper.find('#entryRef').text(this.doc_ref);
        this.wrapper.find('#entryMeta').html(`
            <div><span>📅 Date:</span> <strong>${date}</strong></div>
            <div><span>🏭 Warehouse:</span> <strong>${warehouse}</strong></div>
            <div><span>🏢 Company:</span> <strong>${company}</strong></div>
            <div><span>📦 Changed Items:</span> <strong>${items_with_changes.length}</strong></div>
        `);
        
        this.wrapper.find('#entryTableBody').html(items_with_changes.map((item, idx) => {
            const qtyDiff = this.round2(item.physQty - (item.current_qty || 0));
            const valueDiff = this.round2((item.physQty * item.valPrice) - ((item.current_qty || 0) * (item.current_rate || 0)));
            const badge = item.status === 'surplus' ? '<span class="indicator-pill blue">Surplus (+)</span>' : '<span class="indicator-pill red">Deficit (-)</span>';
            return `技术上
                <td>${idx + 1}</td>
                <td><code>${item.code}</code></td>
                <td>${item.name}</td>
                <td class="text-right">${this.fmt_qty(item.current_qty || 0)}</td>
                <td class="text-right">${this.fmt(item.current_rate || 0)}</td>
                <td class="text-right">${this.fmt_qty(item.physQty)}</td>
                <td class="text-right">${this.fmt(item.valPrice)}</td>
                <td class="text-right ${qtyDiff > 0 ? 'text-success' : 'text-danger'}">${qtyDiff > 0 ? '+' : ''}${this.fmt_qty(qtyDiff)}</td>
                <td class="text-right ${valueDiff > 0 ? 'text-success' : 'text-danger'}">${valueDiff > 0 ? '+' : ''}${this.fmt(valueDiff)}</td>
                <td class="text-center">${badge}</td>
             </tr>`;
        }).join(''));
        
        this.entry_generated = true;
        this.wrapper.find('#entrySection').show();
        this.wrapper.find('#entrySection')[0].scrollIntoView({ behavior: 'smooth' });
        this.set_status('pending');
        frappe.show_alert({ message: `✨ Preview created — ${items_with_changes.length} items with changes`, indicator: 'green' });
    }

    create_stock_reconciliation_in_erpnext() {
        if (!this.validate_header()) return;
        
        const items_with_changes = this.items.filter(i => i.status !== 'ok');
        if (!items_with_changes.length) {
            this.show_alert('warn', 'No changes to submit');
            return;
        }
        
        const key = `${this.wrapper.find('#reconDate').val()}__${this.wrapper.find('#warehouse').val()}`;
        if (this.submitted_entries.includes(key)) {
            this.show_alert('danger', '⛔ Duplicate! A reconciliation for this warehouse and date has already been submitted.');
            return;
        }
        
        // Prepare data exactly as backend expects
        const reconciliation_data = {
            company: this.wrapper.find('#company').val(),
            posting_date: this.wrapper.find('#reconDate').val(),
            posting_time: frappe.datetime.now_time(),
            warehouse: this.wrapper.find('#warehouse').val(),
            remarks: `Stock Reconciliation: ${this.doc_ref}\n${this.wrapper.find('#remarks').val() || ''}`,
            items: items_with_changes.map(item => ({
                item_code: item.code,
                item_name: item.name,
                qty: item.physQty,
                valuation_rate: item.valPrice,
                current_qty: item.current_qty || 0,
                current_valuation_rate: item.current_rate || 0,
                amount: item.physQty * item.valPrice,
                current_amount: (item.current_qty || 0) * (item.current_rate || 0)
            }))
        };
        
        this.show_loading('Creating Stock Reconciliation in ERPNext...');
        
        frappe.call({
            method: 'ecclesia.ecclesia.page.stock_recon.stock_recon.create_stock_reconciliation',
            args: {
                data: reconciliation_data,
                reconciliation_ref: this.doc_ref
            },
            callback: (response) => {
                this.hide_loading();
                if (response.message && response.message.success) {
                    this.submitted_entries.push(key);
                    this.show_alert('success', `✅ Stock Reconciliation Created!<br>Document: ${response.message.name}`);
                    this.set_status('submitted');
                    this.wrapper.find('#submitBtn').prop('disabled', true);
                    this.wrapper.find('#generateBtn').prop('disabled', true);
                } else if (response.message && response.message.error) {
                    this.show_alert('danger', `❌ Error: ${response.message.error}`);
                } else {
                    this.show_alert('danger', '❌ Failed to create Stock Reconciliation.');
                }
            },
            error: (err) => {
                this.hide_loading();
                this.show_alert('danger', `❌ Server Error: ${err.message || 'Unknown error'}`);
            }
        });
    }

    add_manual_row() {
        const code = this.wrapper.find('#m_code').val().trim() || `ITEM-${String(this.items.length + 1).padStart(3, '0')}`;
        const name = this.wrapper.find('#m_name').val().trim() || 'Manual Item';
        const physQty = this.parse_num(this.wrapper.find('#m_physQty').val());
        const valPrice = this.parse_num(this.wrapper.find('#m_valPrice').val()) || 0;
        
        const item = {
            id: this.items.length + 1,
            code: code,
            name: name,
            current_qty: 0,
            current_rate: 0,
            curQty: 0,
            curPrice: 0,
            sysVal: 0,
            physQty: physQty,
            valPrice: valPrice,
            valNow: this.round2(physQty * valPrice),
            diffQty: 0,
            netAdjQty: 0,
            netAdjAmt: 0,
            status: 'pending'
        };
        
        this.items.push(item);
        this.render_table();
        this.render_metrics();
        
        ['#m_code', '#m_name', '#m_physQty', '#m_valPrice'].forEach(id => {
            this.wrapper.find(id).val('');
        });
        
        frappe.show_alert({ message: `➕ Added: ${name}`, indicator: 'green' });
        
        if (this.entry_generated) {
            this.entry_generated = false;
            this.wrapper.find('#entrySection').hide();
        }
    }

    load_sample_data() {
        const sample = [
            { code: 'ITM-001', name: 'A4 Paper (Ream 500)', physQty: 118, valPrice: 1500 },
            { code: 'ITM-002', name: 'Toner Cartridge HP-85A', physQty: 30, valPrice: 13000 },
            { code: 'ITM-003', name: 'Stapler Heavy Duty', physQty: 18, valPrice: 2200 },
            { code: 'ITM-004', name: 'Writing Pad 50 Leaves', physQty: 215, valPrice: 350 },
            { code: 'ITM-005', name: 'Ballpoint Pen Box of 50', physQty: 22, valPrice: 1800 }
        ];
        
        this.items = sample.map((s, idx) => ({
            id: idx + 1,
            code: s.code,
            name: s.name,
            current_qty: 0,
            current_rate: 0,
            curQty: 0,
            curPrice: 0,
            sysVal: 0,
            physQty: s.physQty,
            valPrice: s.valPrice,
            valNow: this.round2(s.physQty * s.valPrice),
            diffQty: 0,
            netAdjQty: 0,
            netAdjAmt: 0,
            status: 'pending'
        }));
        
        this.render_table();
        this.render_metrics();
        
        if (this.wrapper.find('#warehouse').val()) {
            frappe.confirm('Fetch current system data for these items?', () => {
                this.fetch_system_data();
            });
        }
        
        frappe.show_alert({ message: '📊 Sample data loaded — 5 items', indicator: 'green' });
    }

    export_csv() {
        if (!this.items.length) {
            frappe.show_alert({ message: 'No data to export', indicator: 'orange' });
            return;
        }
        
        const headers = ['#', 'Item Code', 'Item Name', 'System Qty', 'System Rate', 'System Value', 'Physical Qty', 'New Rate', 'New Value', 'Qty Difference', 'Value Difference', 'Status'];
        const rows = this.items.map((i, idx) => [
            idx + 1, i.code, `"${i.name}"`, 
            i.current_qty || 0, i.current_rate || 0, 
            ((i.current_qty || 0) * (i.current_rate || 0)).toFixed(2),
            i.physQty, i.valPrice, (i.physQty * i.valPrice).toFixed(2),
            (i.physQty - (i.current_qty || 0)).toFixed(4),
            ((i.physQty * i.valPrice) - ((i.current_qty || 0) * (i.current_rate || 0))).toFixed(2),
            i.status
        ]);
        
        const csv = [headers, ...rows].map(r => r.join(',')).join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `ecclesia_recon_${this.doc_ref}.csv`;
        a.click();
    }

    download_template() {
        const csv = 'Item Code,Item Name,Physical Count Qty,Valuation Price\nITM-001,Sample Product A,98,1500\nITM-002,Sample Product B,50,2600';
        const blob = new Blob([csv], { type: 'text/csv' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'ecclesia_recon_template.csv';
        a.click();
    }

    clear_table() {
        this.items = [];
        this.entry_generated = false;
        this.wrapper.find('#tableSection, #summarySection, #generateSection, #entrySection').hide();
        this.wrapper.find('#uploadedFileName').hide();
        frappe.show_alert({ message: '🗑️ All data cleared', indicator: 'blue' });
    }

    void_entry() {
        this.entry_generated = false;
        this.wrapper.find('#entrySection').hide();
        this.set_status('draft');
        frappe.show_alert({ message: 'Entry voided', indicator: 'orange' });
    }

    validate_header() {
        const date = this.wrapper.find('#reconDate').val();
        const warehouse = this.wrapper.find('#warehouse').val();
        const company = this.wrapper.find('#company').val();
        
        if (!date) { frappe.msgprint('Please select a reconciliation date.'); return false; }
        if (!warehouse) { frappe.msgprint('Please select a warehouse.'); return false; }
        if (!company) { frappe.msgprint('Please select a company.'); return false; }
        if (!this.items.length) { frappe.msgprint('No items loaded.'); return false; }
        return true;
    }

    set_status(mode) {
        const msgs = {
            draft: '📋 DRAFT · New reconciliation document',
            pending: `⏳ PENDING · Reconciliation ${this.doc_ref} ready for submission`,
            submitted: `✅ SUBMITTED · Reconciliation ${this.doc_ref} finalised`
        };
        this.wrapper.find('#statusStrip').attr('class', `recon-status ${mode}`);
        this.wrapper.find('#statusText').text(msgs[mode] || '');
    }

    show_alert(type, msg) {
        const cls = { warn: 'alert-warning', danger: 'alert-danger', success: 'alert-success', info: 'alert-info' };
        this.wrapper.find('#alertArea').html(`<div class="alert ${cls[type] || 'alert-info'}">${msg}</div>`);
        setTimeout(() => this.clear_alerts(), 5000);
    }

    clear_alerts() { this.wrapper.find('#alertArea').html(''); }

    show_loading(message) {
        const overlay = $(`
            <div class="loading-overlay">
                <div class="loading-spinner">
                    <div class="spinner-border text-primary" role="status"><span class="sr-only">Loading...</span></div>
                    <div>${message}</div>
                </div>
            </div>
        `);
        $('body').append(overlay);
    }

    hide_loading() { $('.loading-overlay').remove(); }
}