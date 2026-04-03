// =============================================================
//  ECCLESIA POS  ·  Professional UI Version
//  Page    : ecc-pos
//  Module  : Ecclesia
//  DocType : ECC POS Settings
// =============================================================

frappe.pages['ecc-pos'].on_page_load = function(wrapper) {
    frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Ecclesia POS',
        single_column: true
    });
    frappe.after_ajax(() => new EcclesiaPOS(wrapper));
};

class EcclesiaPOS {
    constructor(wrapper) {
        this._wrapper = wrapper;
        this.cfg = null;
        this.session = null;
        this.cart = [];
        this.customer = null;
        this.products = [];
        this.categories = [];
        this.payMode = 'Cash';
        this.discPct = 0;
        this.held = JSON.parse(localStorage.getItem('ecc_held') || '[]');
        this.user = frappe.session.user_fullname || frappe.session.user;
        this._grand = 0;
        this._vatAmt = 0;
        this._discAmt = 0;
        this._reportData = null;

        this._render();
        this._bind();
        this._boot();
    }

    _render() {
        const body = this._wrapper.querySelector('.layout-main-section')
                  || this._wrapper.querySelector('.page-content')
                  || this._wrapper;

        body.innerHTML = `
<style>
/* Professional POS Styling */
.ecc-pos-container {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    padding: 8px;
}

/* Header */
.pos-header {
    background: white;
    padding: 15px 20px;
    border-radius: 12px;
    margin-bottom: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.header-left {
    display: flex;
    align-items: center;
    gap: 15px;
}

.brand-icon {
    background: linear-gradient(135deg, #667eea, #764ba2);
    width: 50px;
    height: 50px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 24px;
    box-shadow: 0 4px 10px rgba(102, 126, 234, 0.4);
}

.brand-info h2 {
    margin: 0;
    font-size: 20px;
    color: #2d3748;
}

.brand-info small {
    color: #718096;
    font-size: 12px;
}

.header-center {
    flex: 1;
    max-width: 400px;
    margin: 0 20px;
}

.outlet-select {
    width: 100%;
    padding: 12px 16px;
    border: 2px solid #e2e8f0;
    border-radius: 10px;
    font-size: 14px;
    background: white;
    cursor: pointer;
    transition: all 0.3s;
}

.outlet-select:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.header-right {
    display: flex;
    gap: 8px;
}

.header-btn {
    background: white;
    border: 2px solid #e2e8f0;
    border-radius: 10px;
    padding: 10px 16px;
    font-size: 14px;
    font-weight: 600;
    color: #4a5568;
    cursor: pointer;
    transition: all 0.3s;
    display: flex;
    align-items: center;
    gap: 6px;
}

.header-btn:hover {
    border-color: #667eea;
    color: #667eea;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
}

/* Session Pill */
.session-pill {
    background: #f7fafc;
    border: 2px solid #e2e8f0;
    border-radius: 20px;
    padding: 6px 14px;
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
}

.session-pill.active {
    background: #c6f6d5;
    border-color: #48bb78;
    color: #22543d;
}

.session-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #48bb78;
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(1.2); }
    100% { opacity: 1; transform: scale(1); }
}

/* Main Layout */
.pos-main {
    display: grid;
    grid-template-columns: 1fr 420px;
    gap: 8px;
    height: calc(100vh - 100px);
}

/* Products Panel */
.products-panel {
    background: white;
    border-radius: 12px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.panel-header {
    margin-bottom: 16px;
}

.panel-header h3 {
    margin: 0 0 12px 0;
    color: #2d3748;
    font-size: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.search-wrapper {
    position: relative;
    margin-bottom: 12px;
}

.search-icon {
    position: absolute;
    left: 14px;
    top: 50%;
    transform: translateY(-50%);
    color: #a0aec0;
    font-size: 16px;
}

.search-input {
    width: 100%;
    padding: 12px 12px 12px 42px;
    border: 2px solid #e2e8f0;
    border-radius: 10px;
    font-size: 14px;
    transition: all 0.3s;
    background: #f7fafc;
}

.search-input:focus {
    outline: none;
    border-color: #667eea;
    background: white;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

/* Categories */
.categories-strip {
    display: flex;
    gap: 8px;
    overflow-x: auto;
    padding: 4px 0 12px 0;
}

.categories-strip::-webkit-scrollbar {
    height: 4px;
}

.categories-strip::-webkit-scrollbar-track {
    background: #edf2f7;
    border-radius: 2px;
}

.categories-strip::-webkit-scrollbar-thumb {
    background: #cbd5e0;
    border-radius: 2px;
}

.category-chip {
    padding: 8px 16px;
    border: 2px solid #e2e8f0;
    border-radius: 20px;
    background: white;
    cursor: pointer;
    transition: all 0.3s;
    white-space: nowrap;
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    color: #4a5568;
}

.category-chip:hover {
    border-color: #667eea;
    background: #f7fafc;
    transform: translateY(-1px);
}

.category-chip.active {
    background: linear-gradient(135deg, #667eea, #764ba2);
    border-color: transparent;
    color: white;
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

/* Products Grid */
.products-grid {
    flex: 1;
    overflow-y: auto;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 12px;
    padding: 4px;
}

.products-grid::-webkit-scrollbar {
    width: 6px;
}

.products-grid::-webkit-scrollbar-track {
    background: #edf2f7;
    border-radius: 3px;
}

.products-grid::-webkit-scrollbar-thumb {
    background: #cbd5e0;
    border-radius: 3px;
}

/* Product Card */
.product-card {
    background: white;
    border: 2px solid #e2e8f0;
    border-radius: 12px;
    padding: 12px;
    cursor: pointer;
    transition: all 0.3s;
    position: relative;
}

.product-card:hover {
    transform: translateY(-3px);
    border-color: #667eea;
    box-shadow: 0 8px 16px rgba(102, 126, 234, 0.15);
}

.product-card.out-of-stock {
    opacity: 0.5;
    cursor: not-allowed;
}

.product-card.out-of-stock:hover {
    transform: none;
    border-color: #e2e8f0;
    box-shadow: none;
}

.product-image {
    width: 100%;
    height: 100px;
    background: linear-gradient(135deg, #667eea, #764ba2);
    border-radius: 8px;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 36px;
}

.product-name {
    font-weight: 600;
    font-size: 13px;
    color: #2d3748;
    margin: 0 0 6px 0;
    min-height: 32px;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.product-price {
    font-size: 16px;
    font-weight: 700;
    color: #48bb78;
    margin: 0 0 4px 0;
}

.product-stock {
    font-size: 11px;
    color: #718096;
    margin: 0;
}

.stock-low {
    color: #e53e3e;
}

.stock-ok {
    color: #48bb78;
}

.vat-badge {
    position: absolute;
    top: 8px;
    right: 8px;
    background: #48bb78;
    color: white;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 9px;
    font-weight: 600;
}

/* Checkout Panel */
.checkout-panel {
    background: white;
    border-radius: 12px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    overflow-y: auto;
}

.checkout-panel::-webkit-scrollbar {
    width: 6px;
}

.checkout-panel::-webkit-scrollbar-track {
    background: #edf2f7;
    border-radius: 3px;
}

.checkout-panel::-webkit-scrollbar-thumb {
    background: #cbd5e0;
    border-radius: 3px;
}

/* Customer Section */
.customer-section {
    border: 2px solid #e2e8f0;
    border-radius: 10px;
    padding: 12px;
}

.section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
}

.section-header h4 {
    margin: 0;
    font-size: 14px;
    color: #2d3748;
    display: flex;
    align-items: center;
    gap: 6px;
}

.customer-search {
    display: flex;
    gap: 8px;
    margin-bottom: 10px;
}

.customer-search input {
    flex: 1;
    padding: 8px 12px;
    border: 2px solid #e2e8f0;
    border-radius: 8px;
    font-size: 13px;
}

.customer-search button {
    padding: 8px 16px;
    background: linear-gradient(135deg, #667eea, #764ba2);
    border: none;
    border-radius: 8px;
    color: white;
    font-weight: 600;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.3s;
}

.customer-search button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.customer-display {
    padding: 10px;
    background: #f7fafc;
    border-radius: 8px;
    border-left: 4px solid #48bb78;
    font-size: 13px;
}

.customer-actions {
    display: flex;
    gap: 8px;
    margin-top: 10px;
}

.customer-actions button {
    flex: 1;
    padding: 8px;
    border: 2px solid #e2e8f0;
    border-radius: 8px;
    background: white;
    cursor: pointer;
    transition: all 0.3s;
    font-size: 12px;
    font-weight: 600;
}

.customer-actions button:hover {
    border-color: #667eea;
    color: #667eea;
}

/* Cart Section */
.cart-section {
    border: 2px solid #e2e8f0;
    border-radius: 10px;
    padding: 12px;
}

.cart-items {
    max-height: 250px;
    overflow-y: auto;
    margin-bottom: 12px;
}

.cart-items::-webkit-scrollbar {
    width: 4px;
}

.cart-items::-webkit-scrollbar-track {
    background: #edf2f7;
}

.cart-items::-webkit-scrollbar-thumb {
    background: #cbd5e0;
    border-radius: 2px;
}

.cart-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 0;
    border-bottom: 1px solid #edf2f7;
}

.cart-item:last-child {
    border-bottom: none;
}

.item-info {
    flex: 1;
}

.item-name {
    font-weight: 600;
    font-size: 13px;
    color: #2d3748;
    margin: 0 0 4px 0;
}

.item-meta {
    font-size: 11px;
    color: #718096;
    margin: 0;
}

.item-controls {
    display: flex;
    align-items: center;
    gap: 8px;
}

.qty-control {
    display: flex;
    align-items: center;
    gap: 2px;
    background: #f7fafc;
    border-radius: 6px;
    padding: 2px;
}

.qty-btn {
    width: 24px;
    height: 24px;
    border: 1px solid #e2e8f0;
    background: white;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.3s;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
}

.qty-btn:hover {
    background: #667eea;
    color: white;
    border-color: #667eea;
}

.qty-input {
    width: 40px;
    text-align: center;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    padding: 4px 0;
    font-size: 12px;
}

.item-total {
    font-weight: 600;
    color: #48bb78;
    min-width: 70px;
    text-align: right;
    font-size: 13px;
}

.remove-btn {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 16px;
    color: #a0aec0;
    transition: all 0.3s;
}

.remove-btn:hover {
    color: #e53e3e;
    transform: scale(1.2);
}

.empty-cart {
    text-align: center;
    padding: 30px 15px;
    color: #a0aec0;
}

.empty-icon {
    font-size: 40px;
    margin-bottom: 10px;
    opacity: 0.5;
}

/* Totals */
.totals {
    border-top: 2px solid #e2e8f0;
    padding-top: 12px;
}

.total-row {
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    font-size: 13px;
}

.discount-row {
    align-items: center;
}

.discount-field {
    display: flex;
    align-items: center;
    gap: 6px;
}

.discount-field input {
    width: 50px;
    padding: 4px 6px;
    border: 2px solid #e2e8f0;
    border-radius: 6px;
    text-align: center;
    font-size: 12px;
}

.discount-field input:focus {
    outline: none;
    border-color: #667eea;
}

.grand-total {
    font-weight: 700;
    font-size: 16px;
    color: #48bb78;
    padding-top: 8px;
    margin-top: 8px;
    border-top: 2px solid #e2e8f0;
}

/* Payment Section */
.payment-section {
    border: 2px solid #e2e8f0;
    border-radius: 10px;
    padding: 12px;
}

.payment-modes {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
    margin-bottom: 12px;
}

.payment-btn {
    padding: 12px 8px;
    border: 2px solid #e2e8f0;
    border-radius: 8px;
    background: white;
    cursor: pointer;
    transition: all 0.3s;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    font-size: 11px;
    font-weight: 600;
}

.payment-btn .icon {
    font-size: 18px;
}

.payment-btn:hover {
    border-color: #667eea;
    transform: translateY(-1px);
}

.payment-btn.active {
    background: linear-gradient(135deg, #667eea, #764ba2);
    border-color: transparent;
    color: white;
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.amount-input {
    width: 100%;
    padding: 12px;
    border: 2px solid #e2e8f0;
    border-radius: 8px;
    font-size: 16px;
    font-weight: 600;
    text-align: center;
    margin-bottom: 10px;
}

.amount-input:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.quick-amounts {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 6px;
    margin-bottom: 10px;
}

.quick-amt {
    padding: 8px 4px;
    border: 2px solid #e2e8f0;
    border-radius: 6px;
    background: white;
    cursor: pointer;
    transition: all 0.3s;
    font-size: 11px;
    font-weight: 600;
}

.quick-amt:hover {
    background: #667eea;
    color: white;
    border-color: #667eea;
}

.change-box {
    padding: 10px;
    border-radius: 6px;
    text-align: center;
    font-weight: 600;
    font-size: 13px;
    display: none;
}

.change-box.positive {
    display: block;
    background: #c6f6d5;
    color: #22543d;
    border: 1px solid #9ae6b4;
}

.change-box.negative {
    display: block;
    background: #fed7d7;
    color: #742a2a;
    border: 1px solid #feb2b2;
}

/* Action Buttons */
.action-buttons {
    display: grid;
    grid-template-columns: 1fr 1fr 2fr;
    gap: 8px;
    margin-top: 8px;
}

.action-btn {
    padding: 12px 16px;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.3s;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
}

.action-btn.secondary {
    background: #edf2f7;
    color: #4a5568;
    border: 2px solid #e2e8f0;
}

.action-btn.secondary:hover {
    background: #e2e8f0;
    transform: translateY(-1px);
}

.action-btn.primary {
    background: linear-gradient(135deg, #48bb78, #38a169);
    color: white;
    box-shadow: 0 4px 12px rgba(72, 187, 120, 0.3);
}

.action-btn.primary:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 16px rgba(72, 187, 120, 0.4);
}

.action-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    transform: none;
}

/* Modal Styles */
.ecc-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0,0,0,0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
}

.ecc-modal {
    background: white;
    border-radius: 12px;
    min-width: 450px;
    max-width: 600px;
    max-height: 80vh;
    overflow: hidden;
    box-shadow: 0 20px 40px rgba(0,0,0,0.2);
}

.modal-header {
    padding: 16px 20px;
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.modal-header h3 {
    margin: 0;
    font-size: 18px;
}

.modal-close {
    background: none;
    border: none;
    color: white;
    font-size: 20px;
    cursor: pointer;
    opacity: 0.8;
    transition: all 0.3s;
}

.modal-close:hover {
    opacity: 1;
    transform: scale(1.1);
}

.modal-body {
    padding: 20px;
    max-height: calc(80vh - 120px);
    overflow-y: auto;
}

.modal-footer {
    padding: 16px 20px;
    background: #f7fafc;
    display: flex;
    gap: 10px;
    justify-content: flex-end;
}

.modal-btn {
    padding: 10px 20px;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s;
}

.modal-btn.primary {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
}

.modal-btn.primary:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.modal-btn.secondary {
    background: #edf2f7;
    color: #4a5568;
}

.modal-btn.secondary:hover {
    background: #e2e8f0;
}

/* Receipt Styles */
.receipt-box {
    background: #f7fafc;
    border-radius: 8px;
    padding: 16px;
    margin: 10px 0;
}

.receipt-item {
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    border-bottom: 1px dashed #e2e8f0;
    font-size: 13px;
}

.receipt-item:last-child {
    border-bottom: none;
}

.receipt-total {
    font-weight: 700;
    color: #48bb78;
    font-size: 16px;
    padding-top: 8px;
    margin-top: 8px;
    border-top: 2px solid #e2e8f0;
}

/* Held Sales */
.held-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px;
    border: 2px solid #e2e8f0;
    border-radius: 8px;
    margin-bottom: 8px;
    cursor: pointer;
    transition: all 0.3s;
}

.held-item:hover {
    border-color: #667eea;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.1);
}

.held-info {
    flex: 1;
}

.held-info h4 {
    margin: 0 0 4px 0;
    font-size: 14px;
    color: #2d3748;
}

.held-info p {
    margin: 0;
    font-size: 11px;
    color: #718096;
}

.held-total {
    font-weight: 700;
    color: #48bb78;
    font-size: 16px;
}

/* Report Stats */
.report-stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin-bottom: 20px;
}

.stat-card {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    padding: 15px;
    border-radius: 10px;
    text-align: center;
}

.stat-value {
    font-size: 24px;
    font-weight: 700;
    margin: 0 0 5px 0;
}

.stat-label {
    font-size: 12px;
    opacity: 0.9;
}

.report-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
}

.report-table th {
    background: #f7fafc;
    padding: 8px;
    text-align: left;
    border-bottom: 2px solid #e2e8f0;
}

.report-table td {
    padding: 6px 8px;
    border-bottom: 1px solid #e2e8f0;
}

/* Loading States */
.loading-spinner {
    text-align: center;
    padding: 40px;
    color: #718096;
}

.spinner {
    width: 35px;
    height: 35px;
    border: 3px solid #e2e8f0;
    border-top: 3px solid #667eea;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto 12px auto;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

.empty-state {
    text-align: center;
    padding: 40px;
    color: #a0aec0;
}
</style>

<div class="ecc-pos-container">
    <!-- Header -->
    <div class="pos-header">
        <div class="header-left">
            <div class="brand-icon">✦</div>
            <div class="brand-info">
                <h2>Ecclesia POS</h2>
                <small>Point of Sale System</small>
            </div>
        </div>
        
        <div class="header-center">
            <select class="outlet-select" id="J-terminal">
                <option value="">Select Terminal</option>
            </select>
        </div>
        
        <div class="header-right">
            <div class="session-pill" id="J-sess-pill">
                <span class="session-dot"></span>
                <span id="J-sess-lbl">No Session</span>
            </div>
            <button class="header-btn" id="J-session">⏱ Session</button>
            <button class="header-btn" id="J-reports">📊 Reports</button>
            <button class="header-btn" id="J-settings">⚙ Settings</button>
        </div>
    </div>
    
    <!-- Main Content -->
    <div class="pos-main">
        <!-- Products Panel -->
        <div class="products-panel">
            <div class="panel-header">
                <h3><span>📦</span> Products</h3>
                <div class="search-wrapper">
                    <span class="search-icon">🔍</span>
                    <input type="text" class="search-input" id="J-search" placeholder="Search products...">
                </div>
                <div class="categories-strip" id="J-cats">
                    <button class="category-chip active" data-cat="">⭐ All Items</button>
                </div>
            </div>
            
            <div class="products-grid" id="J-grid">
                <div class="empty-state">
                    <div class="empty-icon">🏪</div>
                    <p>Select a terminal to begin</p>
                </div>
            </div>
        </div>
        
        <!-- Checkout Panel -->
        <div class="checkout-panel">
            <!-- Customer Section -->
            <div class="customer-section">
                <div class="section-header">
                    <h4><span>👤</span> Customer</h4>
                </div>
                <div class="customer-search">
                    <input type="text" id="J-cust-search" placeholder="Search customer...">
                    <button id="J-search-customer">Search</button>
                </div>
                <div class="customer-display" id="J-cust-val">
                    Walk-In Customer
                </div>
                <div class="customer-actions">
                    <button id="J-cust-new">👤 New Customer</button>
                    <button id="J-cust-clear" style="display:none;">✕ Clear</button>
                </div>
            </div>
            
            <!-- Cart Section -->
            <div class="cart-section">
                <div class="section-header">
                    <h4><span>🛒</span> Cart <span class="badge" id="J-cart-ct">0</span></h4>
                    <button class="header-btn" id="J-clear-cart" style="padding:5px 10px;">Clear</button>
                </div>
                
                <div class="cart-items" id="J-cart">
                    <div class="empty-cart">
                        <div class="empty-icon">🛒</div>
                        <p>Cart is empty</p>
                    </div>
                </div>
                
                <div class="totals">
                    <div class="total-row">
                        <span>Subtotal:</span>
                        <span id="J-sub">₦0.00</span>
                    </div>
                    <div class="total-row discount-row">
                        <span class="discount-field">
                            <span>Discount:</span>
                            <input type="number" id="J-disc" value="0" min="0" max="100" step="0.5">
                            <span>%</span>
                        </span>
                        <span id="J-disc-amt">₦0.00</span>
                    </div>
                    <div class="total-row">
                        <span>VAT (<span id="J-vat-r">0</span>%):</span>
                        <span id="J-vat-amt">₦0.00</span>
                    </div>
                    <div class="total-row grand-total">
                        <span>GRAND TOTAL:</span>
                        <span id="J-grand">₦0.00</span>
                    </div>
                </div>
            </div>
            
            <!-- Payment Section -->
            <div class="payment-section">
                <div class="section-header">
                    <h4><span>💳</span> Payment</h4>
                </div>
                
                <div class="payment-modes" id="J-pay-grid">
                    <button class="payment-btn active" data-mode="Cash">
                        <span class="icon">💵</span>
                        <span>Cash</span>
                    </button>
                    <button class="payment-btn" data-mode="Card">
                        <span class="icon">💳</span>
                        <span>Card</span>
                    </button>
                    <button class="payment-btn" data-mode="Transfer">
                        <span class="icon">🏦</span>
                        <span>Transfer</span>
                    </button>
                    <button class="payment-btn" data-mode="Credit">
                        <span class="icon">📝</span>
                        <span>Credit</span>
                    </button>
                </div>
                
                <div class="payment-amount" id="J-amt-wrap">
                    <input type="number" class="amount-input" id="J-received" placeholder="Amount Received" step="0.01">
                    <div class="quick-amounts" id="J-quick">
                        <button class="quick-amt" data-amt="500">₦500</button>
                        <button class="quick-amt" data-amt="1000">₦1K</button>
                        <button class="quick-amt" data-amt="2000">₦2K</button>
                        <button class="quick-amt" data-amt="5000">₦5K</button>
                        <button class="quick-amt" data-amt="10000">₦10K</button>
                        <button class="quick-amt" data-amt="20000">₦20K</button>
                    </div>
                    <div class="change-box" id="J-change"></div>
                </div>
            </div>
            
            <!-- Action Buttons -->
            <div class="action-buttons">
                <button class="action-btn secondary" id="J-hold2"><span>⏸</span> Hold</button>
                <button class="action-btn secondary" id="J-recall2"><span>📋</span> Recall</button>
                <button class="action-btn primary" id="J-complete"><span>✨</span> Complete Sale</button>
            </div>
        </div>
    </div>
</div>`;
    }

    // Shorthand methods
    $(id) { return document.getElementById(id); }
    $$(sel) { return document.querySelector(sel); }
    $$all(sel) { return document.querySelectorAll(sel); }

    _bind() {
        const d = document;

        // Terminal selection
        d.addEventListener('change', e => {
            if (e.target.id === 'J-terminal') this._onTerminal(e.target.value);
            if (e.target.id === 'J-disc') { 
                this.discPct = parseFloat(e.target.value) || 0; 
                this._totals(); 
            }
            if (e.target.id === 'J-received') this._change();
            
            // Cart UOM change
            if (e.target.classList.contains('ci-uom')) {
                const idx = +e.target.closest('.cart-item').dataset.idx;
                this._changeCartUOM(idx, e.target.value);
            }
            
            // Cart qty input change
            if (e.target.classList.contains('qty-input')) {
                const idx = +e.target.closest('.cart-item').dataset.idx;
                const v = parseFloat(e.target.value);
                if (v > 0) { 
                    this.cart[idx].qty = v; 
                    this.cart[idx].amount = v * this.cart[idx].rate; 
                    this._renderCart(); 
                }
            }
        });

        // Search debounce
        let st;
        d.addEventListener('input', e => {
            if (e.target.id === 'J-search') { 
                clearTimeout(st); 
                st = setTimeout(() => this._filter(), 300); 
            }
        });

        // Category chips
        d.addEventListener('click', e => {
            const chip = e.target.closest('.category-chip');
            if (chip) {
                this.$$all('.category-chip').forEach(c => c.classList.remove('active'));
                chip.classList.add('active');
                this._filter(chip.dataset.cat);
            }
        });

        // Product card click
        d.addEventListener('click', e => {
            const card = e.target.closest('.product-card:not(.out-of-stock)');
            if (card && !e.target.classList.contains('ci-uom')) {
                this._addToCart(card.dataset);
            }
        });

        // Cart controls
        d.addEventListener('click', e => {
            if (e.target.closest('.qty-btn.minus')) { 
                const i = +e.target.closest('.cart-item').dataset.idx; 
                this._qty(i, -1); 
            }
            if (e.target.closest('.qty-btn.plus')) { 
                const i = +e.target.closest('.cart-item').dataset.idx; 
                this._qty(i, +1); 
            }
            if (e.target.closest('.remove-btn')) { 
                const i = +e.target.closest('.cart-item').dataset.idx; 
                this.cart.splice(i,1); 
                this._renderCart(); 
            }
        });

        // Payment mode buttons
        d.addEventListener('click', e => {
            const pm = e.target.closest('.payment-btn');
            if (pm) {
                this.$$all('.payment-btn').forEach(b => b.classList.remove('active'));
                pm.classList.add('active');
                this.payMode = pm.dataset.mode;
                this._toggleCashFields();
                this._change();
            }
        });

        // Quick amount buttons
        d.addEventListener('click', e => {
            const qa = e.target.closest('.quick-amt');
            if (qa) { 
                this.$('J-received').value = qa.dataset.amt; 
                this._change(); 
            }
        });

        // Customer buttons
        d.addEventListener('click', e => {
            if (e.target.id === 'J-cust-val' || e.target.id === 'J-search-customer') this._searchCustomer();
            if (e.target.id === 'J-cust-new') this._newCustomer();
            if (e.target.id === 'J-cust-clear') this._clearCustomer();
            if (e.target.id === 'J-clear-cart') this._clearCart();
            if (e.target.id === 'J-hold2') this._hold();
            if (e.target.id === 'J-recall2') this._recall();
            if (e.target.id === 'J-session') this._sessionModal();
            if (e.target.id === 'J-reports') this._reports();
            if (e.target.id === 'J-settings') frappe.set_route('List', 'ECC POS Settings');
            if (e.target.id === 'J-complete') this._complete();
        });
    }

    _toggleCashFields() {
        const show = this.payMode === 'Cash';
        const amtWrap = this.$('J-amt-wrap');
        if (amtWrap) {
            amtWrap.style.display = show ? 'block' : 'none';
        }
    }

    _change() {
        const box = this.$('J-change');
        if (this.payMode !== 'Cash') { 
            box.className = 'change-box'; 
            return; 
        }
        const recv = parseFloat(this.$('J-received')?.value) || 0;
        if (!recv) { 
            box.className = 'change-box'; 
            return; 
        }
        const diff = recv - this._grand;
        if (diff >= 0) {
            box.className = 'change-box positive';
            box.innerHTML = `<strong>Change:</strong> ₦${this._fmt(diff)}`;
        } else {
            box.className = 'change-box negative';
            box.innerHTML = `<strong>Short:</strong> ₦${this._fmt(Math.abs(diff))}`;
        }
    }

    _renderPayModes() {
        const modes = this.cfg.payment_modes || [];
        if (!modes.length) return;

        const icons = { 
            Cash:'💵', Card:'💳', 'Credit Card':'💳', Transfer:'🏦',
            'Bank Transfer':'🏦', Cheque:'🧾', Credit:'📝',
            Online:'📱', 'Mobile Money':'📱', POS:'💳' 
        };

        this.$('J-pay-grid').innerHTML = modes.map((m, i) => `
            <button class="payment-btn ${i===0?'active':''}" data-mode="${m.mode}">
                <span class="icon">${m.icon || icons[m.mode] || '💰'}</span>
                <span>${m.mode}</span>
            </button>
        `).join('');

        this.payMode = modes[0]?.mode || 'Cash';
        this._toggleCashFields();
    }

    _pillOn() {
        const p = this.$('J-sess-pill');
        p.classList.add('active');
        p.querySelector('.session-dot').style.animation = 'pulse 2s infinite';
        this.$('J-sess-lbl').textContent = `Session: ${this.session.name}`;
    }

    _pillOff() {
        const p = this.$('J-sess-pill');
        p.classList.remove('active');
        p.querySelector('.session-dot').style.animation = 'none';
        this.$('J-sess-lbl').textContent = 'No Session';
    }

    async _boot() {
        const r = await this._api('get_user_terminals');
        if (!r.success) return this._alert(r.error, 'red');

        const sel = this.$('J-terminal');
        (r.terminals || []).forEach(t => {
            const opt = document.createElement('option');
            opt.value = t.name;
            opt.textContent = `${t.pos_name}${t.branch ? ' · ' + t.branch : ''} — ${t.company}`;
            sel.appendChild(opt);
        });

        if (r.terminals && r.terminals.length === 1) {
            sel.value = r.terminals[0].name;
            await this._onTerminal(r.terminals[0].name);
        }
    }

    async _onTerminal(name) {
        if (!name) { this.cfg = null; return; }

        const r = await this._api('get_terminal_config', { settings_name: name });
        if (!r.success) return this._alert(r.error, 'red');

        this.cfg = r.config;
        this.$('J-vat-r').textContent = this.cfg.vat_rate;
        this._renderPayModes();

        const sr = await this._api('get_active_session');
        if (sr.has_session) {
            this.session = sr.session;
            this._pillOn();
        } else {
            this._openSessionModal();
        }

        await this._loadProducts();
    }

    async _loadProducts(group = '') {
        this.$('J-grid').innerHTML = `<div class="loading-spinner"><div class="spinner"></div> Loading products...</div>`;
        const r = await this._api('get_products', {
            settings_name: this.cfg.settings_name,
            item_group: group
        });
        if (!r.success) {
            this.$('J-grid').innerHTML = `<div class="empty-state"><div class="empty-icon">❌</div><p>${r.error}</p></div>`;
            return;
        }
        this.products = r.items || [];
        this.categories = r.categories || [];
        this._renderCats();
        this._renderGrid(this.products);
        this._alert(`${this.products.length} products loaded`, 'green');
    }

    _renderCats() {
        const bar = this.$('J-cats');
        bar.innerHTML = `<button class="category-chip active" data-cat="">⭐ All Items</button>` +
            this.categories.map(c => `<button class="category-chip" data-cat="${c}">📦 ${c}</button>`).join('');
    }

    _filter(cat = null) {
        const term = (this.$('J-search')?.value || '').toLowerCase();
        const activeCat = cat !== null ? cat : (this.$$('.category-chip.active')?.dataset.cat || '');
        let list = this.products;
        if (activeCat) list = list.filter(p => p.item_group === activeCat);
        if (term) list = list.filter(p =>
            p.item_name.toLowerCase().includes(term) ||
            p.item_code.toLowerCase().includes(term)
        );
        this._renderGrid(list);
    }

    _renderGrid(list) {
        const grid = this.$('J-grid');
        const showStock = this.cfg?.show_stock_qty;

        if (!list.length) {
            grid.innerHTML = `<div class="empty-state"><div class="empty-icon">🔍</div><p>No products found</p></div>`;
            return;
        }

        grid.innerHTML = list.map(p => {
            const qty = parseFloat(p.available_qty || 0);
            const price = parseFloat(p.price || 0);
            const oos = qty <= 0 && showStock;
            const stockClass = qty <= 0 ? 'out-of-stock' : '';
            const stockText = showStock ? (qty <= 0 ? 'Out of stock' : `${qty} available`) : '';
            const stockColor = qty <= 0 ? 'stock-low' : qty < 5 ? 'stock-low' : 'stock-ok';
            const uomLabel = p.default_uom || p.stock_uom || '';

            const icon = p.image
                ? `<img src="${p.image}" alt="" style="max-width:100%;max-height:100%;object-fit:contain">`
                : this._emoji(p.item_name);

            return `
            <div class="product-card ${oos ? 'out-of-stock' : ''}" 
                 data-code="${p.item_code}"
                 data-name="${p.item_name.replace(/"/g,'&quot;')}"
                 data-price="${price}"
                 data-stock="${qty}"
                 data-stock-uom="${p.stock_uom}"
                 data-default-uom="${p.default_uom || p.stock_uom}"
                 data-uom-opts='${JSON.stringify(p.uom_options || [])}'>
                <div class="product-image">${icon}</div>
                <div class="product-name">${p.item_name}</div>
                <div class="product-price">₦${this._fmt(price)}</div>
                ${showStock ? `<div class="product-stock ${stockColor}">${stockText}</div>` : ''}
                <div class="product-stock">${uomLabel}</div>
            </div>`;
        }).join('');
    }

    _emoji(n) {
        const s = n.toLowerCase();
        const m = { 
            pizza:'🍕', burger:'🍔', coffee:'☕', tea:'🍵', cake:'🍰',
            ice:'🍦', drink:'🥤', soda:'🥤', wine:'🍷', beer:'🍺',
            juice:'🧃', water:'💧', salad:'🥗', chicken:'🍗', fish:'🐟',
            rice:'🍚', pasta:'🍝', bread:'🍞', sandwich:'🥪', fries:'🍟',
            egg:'🥚', milk:'🥛', cheese:'🧀', fruit:'🍎', soap:'🧼',
            phone:'📱', laptop:'💻', book:'📚', drug:'💊', med:'💊' 
        };
        for (const [k,v] of Object.entries(m)) if (s.includes(k)) return v;
        return '📦';
    }

    _addToCart(data) {
        if (!this.session) { this._alert('Open a session first', 'orange'); return; }
        const code = data.code;
        const name = data.name;
        const price = parseFloat(data.price);
        const stock = parseFloat(data.stock);
        const stockUom = data.stockUom || data['stock-uom'] || '';
        const defaultUom = data.defaultUom || data['default-uom'] || stockUom;
        let uomOpts = [];
        try { uomOpts = JSON.parse(data.uomOpts || data['uom-opts'] || '[]'); } catch(_) {}
        if (!uomOpts.length) uomOpts = [{ uom: stockUom, conversion_factor: 1 }];

        const defaultOpt = uomOpts.find(o => o.uom === defaultUom) || uomOpts[0];
        const cf = parseFloat(defaultOpt.conversion_factor) || 1;

        const existing = this.cart.find(i => i.item_code === code && i.uom === defaultOpt.uom);
        if (existing) {
            const newQty = existing.qty + 1;
            if (stock > 0 && newQty * cf > stock) { 
                this._alert('Insufficient stock', 'orange'); 
                return; 
            }
            existing.qty = newQty;
            existing.amount = newQty * existing.rate;
        } else {
            this.cart.push({
                item_code: code,
                item_name: name,
                rate: price,
                qty: 1,
                amount: price,
                uom: defaultOpt.uom,
                stock_uom: stockUom,
                conversion_factor: cf,
                uom_options: uomOpts,
                stock
            });
        }
        this._renderCart();
    }

    _qty(idx, delta) {
        const item = this.cart[idx];
        if (!item) return;
        const nq = item.qty + delta;
        if (nq <= 0) { 
            this.cart.splice(idx, 1); 
        } else {
            const stockNeeded = nq * item.conversion_factor;
            if (delta > 0 && item.stock > 0 && stockNeeded > item.stock) {
                this._alert('Insufficient stock', 'orange'); 
                return;
            }
            item.qty = nq;
            item.amount = nq * item.rate;
        }
        this._renderCart();
    }

    _changeCartUOM(idx, newUom) {
        const item = this.cart[idx];
        if (!item) return;
        const opt = item.uom_options.find(o => o.uom === newUom);
        if (!opt) return;

        item.uom = newUom;
        item.conversion_factor = parseFloat(opt.conversion_factor) || 1;
        this._renderCart();
    }

    _renderCart() {
        const el = this.$('J-cart');
        const count = this.cart.length;
        this.$('J-cart-ct').textContent = count;

        if (!count) {
            el.innerHTML = `<div class="empty-cart"><div class="empty-icon">🛒</div><p>Cart is empty</p></div>`;
            this._totals();
            return;
        }

        el.innerHTML = this.cart.map((item, i) => {
            const uomOpts = (item.uom_options || []).map(o =>
                `<option value="${o.uom}" ${o.uom === item.uom ? 'selected' : ''}>${o.uom}</option>`
            ).join('');
            const showUomSel = item.uom_options && item.uom_options.length > 1;

            return `
            <div class="cart-item" data-idx="${i}">
                <div class="item-info">
                    <div class="item-name">${item.item_name}</div>
                    <div class="item-meta">
                        ₦${this._fmt(item.rate)} / ${item.uom}
                        ${item.uom !== item.stock_uom ? ` (CF:${item.conversion_factor})` : ''}
                    </div>
                    ${showUomSel ? `<select class="ci-uom">${uomOpts}</select>` : ''}
                </div>
                <div class="item-controls">
                    <div class="qty-control">
                        <button class="qty-btn minus">−</button>
                        <input type="number" class="qty-input" value="${item.qty}" min="1" max="${item.stock}">
                        <button class="qty-btn plus">+</button>
                    </div>
                    <div class="item-total">₦${this._fmt(item.amount)}</div>
                    <button class="remove-btn">🗑️</button>
                </div>
            </div>`;
        }).join('');

        this._totals();
    }

    _clearCart() {
        if (!this.cart.length) return;
        this.cart = [];
        this._renderCart();
    }

    _totals() {
        const sub = this.cart.reduce((s, i) => s + i.amount, 0);
        const disc = sub * (this.discPct / 100);
        const after = sub - disc;
        const vr = this.cfg ? parseFloat(this.cfg.vat_rate || 0) : 0;
        const vat = (this.cfg?.enable_vat && vr > 0) ? after * vr / 100 : 0;
        const grand = after + vat;

        this.$('J-sub').textContent = `₦${this._fmt(sub)}`;
        this.$('J-disc-amt').textContent = disc > 0 ? `-₦${this._fmt(disc)}` : '₦0.00';
        this.$('J-vat-amt').textContent = `₦${this._fmt(vat)}`;
        this.$('J-grand').textContent = `₦${this._fmt(grand)}`;

        this._grand = grand;
        this._discAmt = disc;
        this._vatAmt = vat;
        this._change();
    }

    async _complete() {
        if (!this.session) { this._alert('No active session', 'red'); return; }
        if (!this.cart.length) { this._alert('Cart is empty', 'orange'); return; }

        if (this.discPct > 0) {
            if (!this.cfg.can_apply_discount) {
                this._alert('You are not permitted to apply discounts', 'red'); 
                return;
            }
            const max = this.cfg.max_discount_pct;
            if (max > 0 && this.discPct > max) {
                this._alert(`Max discount allowed: ${max}%`, 'red'); 
                return;
            }
        }

        if (this.payMode === 'Cash') {
            const recv = parseFloat(this.$('J-received')?.value) || 0;
            if (recv < this._grand) { 
                this._alert('Amount received is less than total', 'orange'); 
                return; 
            }
        }

        const btn = this.$('J-complete');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner" style="width:16px;height:16px;border-width:2px;"></span> Processing...';

        try {
            const paidAmt = this.payMode === 'Cash'
                ? parseFloat(this.$('J-received')?.value) || this._grand
                : this._grand;

            const payload = {
                settings_name: this.cfg.settings_name,
                session_name: this.session.name,
                customer: this.customer?.name || null,
                items: this.cart.map(i => ({
                    item_code: i.item_code,
                    item_name: i.item_name,
                    qty: i.qty,
                    rate: i.rate,
                    uom: i.uom,
                    stock_uom: i.stock_uom,
                    conversion_factor: i.conversion_factor
                })),
                discount_type: this.discPct > 0 ? 'Percentage' : '',
                discount_value: this.discPct,
                payment_mode: this.payMode,
                paid_amount: paidAmt
            };

            const r = await this._api('create_invoice', { payload: JSON.stringify(payload) });
            if (r.success) {
                this._successModal(r);
                this._resetPOS();
            } else {
                this._alert(r.error || 'Failed to create invoice', 'red');
            }
        } catch (err) {
            this._alert(err.message || 'Unexpected error', 'red');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<span>✨</span> Complete Sale';
        }
    }

    _successModal(r) {
        const sub = this.cart.reduce((s, i) => s + i.amount, 0);
        const chng = r.change || 0;

        const itemsHtml = this.cart.map(i => `
            <div class="receipt-item">
                <span>${i.item_name} x${i.qty} ${i.uom}</span>
                <span>₦${this._fmt(i.amount)}</span>
            </div>
        `).join('');

        this._modal('✅ Sale Completed', `
            <div style="text-align:center;margin-bottom:15px;">
                <div style="font-size:48px;color:#48bb78;margin-bottom:10px;">✨</div>
                <h3 style="margin:0;color:#2d3748;">Transaction Successful</h3>
            </div>
            
            <div class="receipt-box">
                <div class="receipt-item">
                    <span>Invoice:</span>
                    <span><strong>${r.invoice}</strong></span>
                </div>
                ${itemsHtml}
                <div class="receipt-item" style="border-top:2px solid #e2e8f0;margin-top:8px;padding-top:8px;">
                    <span>Subtotal:</span>
                    <span>₦${this._fmt(sub)}</span>
                </div>
                ${this._discAmt > 0 ? `
                <div class="receipt-item">
                    <span>Discount (${this.discPct}%):</span>
                    <span style="color:#e53e3e;">-₦${this._fmt(this._discAmt)}</span>
                </div>
                ` : ''}
                <div class="receipt-item">
                    <span>VAT (${this.cfg.vat_rate}%):</span>
                    <span>₦${this._fmt(r.vat_amount || 0)}</span>
                </div>
                <div class="receipt-total">
                    <span>GRAND TOTAL:</span>
                    <span>₦${this._fmt(r.grand_total)}</span>
                </div>
                ${chng > 0 ? `
                <div class="receipt-item" style="color:#48bb78;">
                    <span>Change:</span>
                    <span>₦${this._fmt(chng)}</span>
                </div>
                ` : ''}
            </div>
        `, [
            { label: '🖨 Print Receipt', cls: 'primary', cb: () => this._print(r) },
            { label: 'Close', cls: 'secondary', cb: null }
        ]);
    }

    _print(r) {
        const cfg = this.cfg;
        const now = new Date();
        const cust = this.customer?.customer_name || 'Walk-In Customer';
        const sub = this.cart.reduce((s, i) => s + i.amount, 0);

        const w = window.open('', '_blank', 'width=380,height=600');
        if (!w) { this._alert('Allow popups to print', 'orange'); return; }

        const itemsHtml = this.cart.map(i => `
            <tr>
                <td>${i.item_name}</td>
                <td style="text-align:center">${i.qty}</td>
                <td style="text-align:center">${i.uom}</td>
                <td style="text-align:right">₦${this._fmt(i.rate)}</td>
                <td style="text-align:right">₦${this._fmt(i.amount)}</td>
            </tr>
        `).join('');

        w.document.write(`
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Receipt - ${r.invoice}</title>
                <style>
                    * { box-sizing: border-box; margin: 0; padding: 0; }
                    body { 
                        font-family: 'Courier New', monospace; 
                        font-size: 12px; 
                        padding: 15px; 
                        max-width: 80mm; 
                        margin: 0 auto;
                        color: #2d3748;
                    }
                    .header { 
                        text-align: center; 
                        margin-bottom: 15px; 
                        border-bottom: 2px dashed #a0aec0;
                        padding-bottom: 10px;
                    }
                    .header h2 { 
                        margin: 0 0 5px 0; 
                        font-size: 18px;
                        color: #4a5568;
                    }
                    .header p { 
                        margin: 0; 
                        font-size: 11px; 
                        color: #718096;
                    }
                    .info { 
                        margin-bottom: 15px; 
                        border-bottom: 1px solid #e2e8f0;
                        padding-bottom: 8px;
                    }
                    .info-row { 
                        display: flex; 
                        justify-content: space-between; 
                        margin: 3px 0;
                    }
                    table { 
                        width: 100%; 
                        border-collapse: collapse; 
                        margin: 12px 0;
                        font-size: 11px;
                    }
                    th { 
                        border-bottom: 2px solid #4a5568; 
                        padding: 6px 2px; 
                        text-align: left;
                    }
                    td { 
                        padding: 4px 2px; 
                        border-bottom: 1px dotted #e2e8f0;
                    }
                    .totals { 
                        margin-top: 12px; 
                        border-top: 2px solid #4a5568;
                        padding-top: 8px;
                    }
                    .total-row { 
                        display: flex; 
                        justify-content: space-between; 
                        margin: 4px 0;
                    }
                    .grand-total { 
                        font-weight: bold; 
                        font-size: 14px;
                        margin-top: 8px;
                        padding-top: 8px;
                        border-top: 2px solid #4a5568;
                        color: #48bb78;
                    }
                    .footer { 
                        text-align: center; 
                        margin-top: 20px; 
                        padding-top: 12px; 
                        border-top: 2px dashed #a0aec0;
                        font-size: 11px;
                        color: #718096;
                    }
                    @media print {
                        body { margin: 0; padding: 10px; }
                    }
                </style>
            </head>
            <body onload="window.print();setTimeout(()=>window.close(),1000)">
                <div class="header">
                    <h2>${cfg?.company_name || 'Ecclesia POS'}</h2>
                    ${cfg?.branch ? `<p>${cfg.branch}</p>` : ''}
                    <p>SALES RECEIPT</p>
                </div>
                
                <div class="info">
                    <div class="info-row">
                        <span>Invoice:</span>
                        <span><strong>${r.invoice}</strong></span>
                    </div>
                    <div class="info-row">
                        <span>Date:</span>
                        <span>${now.toLocaleDateString()} ${now.toLocaleTimeString()}</span>
                    </div>
                    <div class="info-row">
                        <span>Cashier:</span>
                        <span>${this.user}</span>
                    </div>
                    <div class="info-row">
                        <span>Customer:</span>
                        <span>${cust}</span>
                    </div>
                </div>
                
                <table>
                    <thead>
                        <tr>
                            <th>Item</th>
                            <th style="text-align:center">Qty</th>
                            <th style="text-align:center">UOM</th>
                            <th style="text-align:right">Rate</th>
                            <th style="text-align:right">Amount</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${itemsHtml}
                    </tbody>
                </table>
                
                <div class="totals">
                    <div class="total-row">
                        <span>Subtotal:</span>
                        <span>₦${this._fmt(sub)}</span>
                    </div>
                    ${this._discAmt > 0 ? `
                    <div class="total-row">
                        <span>Discount (${this.discPct}%):</span>
                        <span>-₦${this._fmt(this._discAmt)}</span>
                    </div>
                    ` : ''}
                    <div class="total-row">
                        <span>VAT (${cfg?.vat_rate||0}%):</span>
                        <span>₦${this._fmt(r.vat_amount||0)}</span>
                    </div>
                </div>
                
                <div class="grand-total">
                    <span>GRAND TOTAL:</span>
                    <span>₦${this._fmt(r.grand_total)}</span>
                </div>
                
                <div class="info" style="margin-top:12px;">
                    <div class="info-row">
                        <span>Payment:</span>
                        <span><strong>${this.payMode}</strong></span>
                    </div>
                    ${this.payMode === 'Cash' && r.change > 0 ? `
                    <div class="info-row" style="color:#48bb78;">
                        <span>Change:</span>
                        <span>₦${this._fmt(r.change)}</span>
                    </div>
                    ` : ''}
                </div>
                
                <div class="footer">
                    <p>Thank you for your patronage!</p>
                    <p style="margin-top:4px;">✦ Ecclesia POS ✦</p>
                </div>
            </body>
            </html>
        `);
        w.document.close();
    }

    _searchCustomer() {
        this._modal('Search Customer', `
            <span style="display:block;margin-bottom:8px;font-size:12px;color:#718096;">Name, Mobile or Email</span>
            <input class="search-input" id="M-cust-inp" placeholder="Type to search..." autofocus style="margin-bottom:12px;">
            <div id="M-cust-res"></div>
        `, [
            { label: '🔍 Search', cls: 'primary', noClose: true, cb: () => this._doSearch() },
            { label: 'Cancel', cls: 'secondary', cb: null }
        ]);
        
        setTimeout(() => {
            const i = document.getElementById('M-cust-inp');
            if (i) i.addEventListener('keydown', e => { if (e.key === 'Enter') this._doSearch(); });
        }, 80);
    }

    async _doSearch() {
        const term = document.getElementById('M-cust-inp')?.value?.trim();
        if (!term) return;
        
        const res = document.getElementById('M-cust-res');
        if (res) res.innerHTML = '<div style="color:#718096;font-size:12px;">Searching...</div>';
        
        const r = await this._api('search_customers', { search_term: term, company: this.cfg?.company });
        if (!r.success || !r.customers?.length) {
            if (res) res.innerHTML = '<div style="color:#e53e3e;font-size:12px;">No customers found.</div>';
            return;
        }
        
        if (res) {
            res.innerHTML = r.customers.map(c => `
                <div class="held-item" data-customer='${JSON.stringify(c).replace(/'/g,"&#39;")}' style="cursor:pointer;">
                    <div class="held-info">
                        <h4>${c.customer_name}</h4>
                        <p>${[c.mobile_no, c.email_id].filter(Boolean).join(' · ')}</p>
                    </div>
                </div>
            `).join('');
            
            res.querySelectorAll('[data-customer]').forEach(el => {
                el.addEventListener('click', () => {
                    this._setCustomer(JSON.parse(el.dataset.customer.replace(/&#39;/g,"'")));
                    this._closeModal();
                });
            });
        }
    }

    _newCustomer() {
        this._modal('Create New Customer', `
            <span style="display:block;margin-bottom:5px;font-size:12px;color:#718096;">Full Name *</span>
            <input class="search-input" id="M-nc-name" placeholder="Customer name" autofocus style="margin-bottom:12px;">
            
            <span style="display:block;margin-bottom:5px;font-size:12px;color:#718096;">Mobile Number</span>
            <input class="search-input" id="M-nc-mob" placeholder="08012345678" style="margin-bottom:12px;">
            
            <span style="display:block;margin-bottom:5px;font-size:12px;color:#718096;">Email Address</span>
            <input class="search-input" id="M-nc-email" placeholder="email@domain.com" style="margin-bottom:12px;">
        `, [
            {
                label: '✅ Create', cls: 'primary', noClose: true, cb: async () => {
                    const name = document.getElementById('M-nc-name')?.value?.trim();
                    if (!name) { this._alert('Name is required', 'red'); return; }
                    
                    const r = await this._api('create_customer', {
                        customer_name: name,
                        mobile_no: document.getElementById('M-nc-mob')?.value || '',
                        email: document.getElementById('M-nc-email')?.value || '',
                        company: this.cfg?.company
                    });
                    
                    if (r.success) {
                        this._setCustomer({ name: r.customer, customer_name: r.customer_name });
                        this._closeModal();
                        this._alert('Customer created', 'green');
                    } else this._alert(r.error, 'red');
                }
            },
            { label: 'Cancel', cls: 'secondary', cb: null }
        ]);
    }

    _setCustomer(c) {
        this.customer = c;
        const custVal = this.$('J-cust-val');
        custVal.innerHTML = `<strong>${c.customer_name}</strong>`;
        this.$('J-cust-clear').style.display = 'inline-block';
    }

    _clearCustomer() {
        this.customer = null;
        this.$('J-cust-val').innerHTML = 'Walk-In Customer';
        this.$('J-cust-clear').style.display = 'none';
    }

    _openSessionModal() {
        if (!this.cfg) return;
        this._modal('Open Session', `
            <div style="background:#f7fafc;padding:12px;border-radius:8px;margin-bottom:15px;">
                <p style="margin:0 0 5px 0;"><strong>Terminal:</strong> ${this.cfg.pos_name}</p>
                ${this.cfg.branch ? `<p style="margin:0;"><strong>Branch:</strong> ${this.cfg.branch}</p>` : ''}
            </div>
            
            <span style="display:block;margin-bottom:5px;font-size:12px;color:#718096;">Opening Cash Balance</span>
            <input class="search-input" id="M-open-bal" type="number" value="0" min="0" step="0.01" style="margin-bottom:12px;">
        `, [
            {
                label: '▶ Open Session', cls: 'primary', noClose: true, cb: async () => {
                    const bal = parseFloat(document.getElementById('M-open-bal')?.value) || 0;
                    const r = await this._api('open_session', {
                        settings_name: this.cfg.settings_name,
                        opening_cash: bal
                    });
                    
                    if (r.success) {
                        this.session = { name: r.session };
                        this._pillOn();
                        this._closeModal();
                        this._alert(r.restored ? 'Existing session restored' : 'Session opened', 'green');
                    } else this._alert(r.error, 'red');
                }
            },
            { label: 'Skip', cls: 'secondary', cb: null }
        ]);
    }

    _sessionModal() {
        if (!this.session) { this._openSessionModal(); return; }
        
        this._modal('Session Management', `
            <div class="receipt-box" style="margin-bottom:15px;">
                <div class="receipt-item">
                    <span>Session:</span>
                    <span><strong>${this.session.name}</strong></span>
                </div>
                <div class="receipt-item">
                    <span>Terminal:</span>
                    <span>${this.cfg?.pos_name || ''}</span>
                </div>
                <div class="receipt-item">
                    <span>Status:</span>
                    <span style="color:#48bb78;">● Active</span>
                </div>
            </div>
            
            <span style="display:block;margin-bottom:5px;font-size:12px;color:#718096;">Closing Cash Balance</span>
            <input class="search-input" id="M-close-bal" type="number" value="0" min="0" step="0.01">
        `, [
            {
                label: '⏹ Close Session', cls: 'primary', noClose: true, cb: async () => {
                    const bal = parseFloat(document.getElementById('M-close-bal')?.value) || 0;
                    const r = await this._api('close_session', {
                        session_name: this.session.name,
                        closing_cash: bal
                    });
                    
                    if (r.success) {
                        this._alert(`Closed · ${r.total_invoices} invoices · ₦${this._fmt(r.total_sales)}`, 'green');
                        this.session = null;
                        this._pillOff();
                        this._closeModal();
                    } else this._alert(r.error, 'red');
                }
            },
            { label: 'Cancel', cls: 'secondary', cb: null }
        ]);
    }

    async _reports() {
        if (!this.cfg?.can_view_reports) { this._alert('Access denied', 'red'); return; }
        const today = new Date().toISOString().split('T')[0];

        this._modal('Daily Report', `
            <div style="display:flex;gap:8px;margin-bottom:15px;">
                <input type="date" class="search-input" id="M-rpt-date" value="${today}" style="flex:1;">
                <button class="action-btn primary" id="M-rpt-load" style="width:auto;">Load</button>
            </div>
            <div id="M-rpt-body" style="color:#718096;">Select a date and click Load.</div>
        `, [
            { label: '⬇ Export CSV', cls: 'secondary', noClose: true, cb: () => this._exportCSV() },
            { label: 'Close', cls: 'secondary', cb: null }
        ], true);

        setTimeout(() => {
            const btn = document.getElementById('M-rpt-load');
            if (btn) btn.addEventListener('click', () => this._loadReport());
        }, 80);
    }

    async _loadReport() {
        const date = document.getElementById('M-rpt-date')?.value;
        const body = document.getElementById('M-rpt-body');
        if (!body) return;
        
        body.innerHTML = '<div class="loading-spinner"><div class="spinner"></div> Loading...</div>';

        const r = await this._api('get_daily_report', {
            settings_name: this.cfg.settings_name,
            report_date: date
        });
        
        if (!r.success) { 
            body.innerHTML = `<p style="color:#e53e3e;">${r.error}</p>`; 
            return; 
        }

        this._reportData = r;
        const s = r.summary;

        body.innerHTML = `
            <div class="report-stats">
                <div class="stat-card">
                    <div class="stat-value">${s.total_invoices}</div>
                    <div class="stat-label">Invoices</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">₦${this._fmt(s.total_sales)}</div>
                    <div class="stat-label">Total Sales</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">₦${this._fmt(s.average_order)}</div>
                    <div class="stat-label">Avg Order</div>
                </div>
            </div>
            
            ${r.by_payment.length ? `
                <h4 style="margin:15px 0 8px 0;">Payment Breakdown</h4>
                ${r.by_payment.map(p => `
                    <div class="receipt-item">
                        <span>${p.mode_of_payment}</span>
                        <span>₦${this._fmt(p.total)}</span>
                    </div>
                `).join('')}
            ` : ''}
            
            ${r.top_items.length ? `
                <h4 style="margin:15px 0 8px 0;">Top Items</h4>
                <table class="report-table">
                    <thead>
                        <tr>
                            <th>Item</th>
                            <th style="text-align:center">Qty</th>
                            <th style="text-align:right">Amount</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${r.top_items.map(i => `
                            <tr>
                                <td>${i.item_name}</td>
                                <td style="text-align:center">${this._fmt(i.total_qty)}</td>
                                <td style="text-align:right">₦${this._fmt(i.total_amount)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            ` : ''}
            
            ${r.invoices.length ? `
                <h4 style="margin:15px 0 8px 0;">Transactions</h4>
                <table class="report-table">
                    <thead>
                        <tr>
                            <th>Invoice</th>
                            <th>Customer</th>
                            <th>Payment</th>
                            <th style="text-align:right">Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${r.invoices.map(i => `
                            <tr>
                                <td>${i.name}</td>
                                <td>${i.customer || 'Walk-In'}</td>
                                <td>${i.payment_modes || '—'}</td>
                                <td style="text-align:right">₦${this._fmt(i.grand_total)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            ` : '<p style="margin-top:10px;">No transactions for this date.</p>'}
        `;
    }

    _exportCSV() {
        if (!this._reportData?.invoices?.length) { this._alert('No data to export', 'orange'); return; }
        
        const rows = [['Invoice','Customer','Payment','Subtotal','VAT','Discount','Grand Total']];
        this._reportData.invoices.forEach(i =>
            rows.push([i.name, i.customer||'Walk-In', i.payment_modes||'',
                this._fmt(i.subtotal), this._fmt(i.vat_amount),
                this._fmt(i.discount_amount), this._fmt(i.grand_total)])
        );
        
        const csv = rows.map(r => r.join(',')).join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; 
        a.download = `ecc_pos_${this._reportData.date}.csv`;
        a.click(); 
        URL.revokeObjectURL(url);
        this._alert('CSV exported', 'green');
    }

    _hold() {
        if (!this.cart.length) { this._alert('Cart is empty', 'orange'); return; }
        
        this.held.push({
            cart: JSON.parse(JSON.stringify(this.cart)),
            customer: this.customer,
            disc: this.discPct,
            total: this._grand,
            ts: new Date().toISOString()
        });
        
        localStorage.setItem('ecc_held', JSON.stringify(this.held));
        this._resetPOS();
        this._alert(`Sale held (${this.held.length} held)`, 'green');
    }

    _recall() {
        if (!this.held.length) { this._alert('No held sales', 'orange'); return; }
        
        this._modal('Recall Sale', `
            <div>
                ${this.held.map((h, i) => `
                    <div class="held-item" data-idx="${i}">
                        <div class="held-info">
                            <h4>${h.cart.length} items ${h.customer ? '· ' + h.customer.customer_name : ''}</h4>
                            <p>${new Date(h.ts).toLocaleString()}</p>
                        </div>
                        <div class="held-total">₦${this._fmt(h.total)}</div>
                    </div>
                `).join('')}
            </div>
        `, [
            { label: 'Cancel', cls: 'secondary', cb: null }
        ]);

        setTimeout(() => {
            document.querySelectorAll('.held-item').forEach(el => {
                el.addEventListener('click', () => {
                    const h = this.held[+el.dataset.idx];
                    this.cart = h.cart;
                    this.discPct = h.disc || 0;
                    if (h.customer) this._setCustomer(h.customer);
                    
                    const di = this.$('J-disc');
                    if (di) di.value = this.discPct;
                    
                    this.held.splice(+el.dataset.idx, 1);
                    localStorage.setItem('ecc_held', JSON.stringify(this.held));
                    this._renderCart();
                    this._closeModal();
                    this._alert('Sale recalled', 'green');
                });
            });
        }, 80);
    }

    _resetPOS() {
        this.cart = [];
        this.discPct = 0;
        this._clearCustomer();
        
        const di = this.$('J-disc');
        const ai = this.$('J-received');
        if (di) di.value = 0;
        if (ai) ai.value = '';
        
        const cb = this.$('J-change');
        if (cb) cb.className = 'change-box';
        
        this.$$all('.payment-btn').forEach((b, i) => b.classList.toggle('active', i === 0));
        this.payMode = this.cfg?.payment_modes?.[0]?.mode || 'Cash';
        this._toggleCashFields();
        this._renderCart();
    }

    _modal(title, bodyHTML, actions = [], wide = false) {
        this._closeModal();
        
        const ov = document.createElement('div');
        ov.className = 'ecc-overlay';
        ov.id = 'ECC-OV';
        
        ov.innerHTML = `
            <div class="ecc-modal" style="${wide ? 'min-width:600px;' : ''}">
                <div class="modal-header">
                    <h3>${title}</h3>
                    <button class="modal-close" id="ECC-MX">✕</button>
                </div>
                <div class="modal-body">${bodyHTML}</div>
                <div class="modal-footer">
                    ${actions.map((a, i) => 
                        `<button class="modal-btn ${a.cls}" data-ai="${i}">${a.label}</button>`
                    ).join('')}
                </div>
            </div>
        `;
        
        document.body.appendChild(ov);
        
        ov.querySelector('#ECC-MX').addEventListener('click', () => this._closeModal());
        ov.addEventListener('click', e => { if (e.target === ov) this._closeModal(); });
        
        ov.querySelectorAll('[data-ai]').forEach(btn => {
            btn.addEventListener('click', () => {
                const a = actions[+btn.dataset.ai];
                if (a?.cb) a.cb();
                if (!a?.noClose) this._closeModal();
            });
        });
    }

    _closeModal() {
        document.getElementById('ECC-OV')?.remove();
    }

    async _api(method, args = {}) {
        try {
            const r = await frappe.call({
                method: `ecclesia.ecclesia.page.ecc_pos.ecc_pos.${method}`,
                args
            });
            return r.message || {};
        } catch (e) {
            console.error(`ECC POS API [${method}]:`, e);
            return { success: false, error: e.message || 'API error' };
        }
    }

    _fmt(n) {
        return parseFloat(n || 0).toLocaleString('en-NG', {
            minimumFractionDigits: 2, 
            maximumFractionDigits: 2
        });
    }

    _alert(msg, indicator = 'blue') {
        frappe.show_alert({ message: msg, indicator }, 3);
    }
}

console.log('✦ Ecclesia POS - Professional Version Loaded');