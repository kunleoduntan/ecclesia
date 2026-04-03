/**
 * ecclesia_erequest/public/js/portal.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Employee eRequest Portal — Full SPA
 *
 * AUTH: Uses Frappe's standard /api/method/login endpoint (same as Customer/
 * Supplier portal). Employee enters their ERPNext username + password.
 * Frappe sets a secure httpOnly session cookie. All subsequent API calls to
 * ecclesia_erequest.doctype.erequest.erequest.* are authenticated via that cookie automatically.
 * No OTP, no tokens, no custom password field needed.
 */

'use strict';

const APP_ROOT = document.getElementById('er-app');
const SITE_URL = (APP_ROOT && APP_ROOT.dataset.siteUrl) || '';
const API_BASE = `${SITE_URL}/api/method/ecclesia.doctype.erequest.erequest`;
const PAGE_SIZE = 15;

// ── State ─────────────────────────────────────────────────────────────────────
const S = {
  employee:    null,
  activeTab:   'new',
  requestType: null,
  priority:    'Medium',
  urgency:     '',
  currentPage: 1,
  totalReqs:   0,
  departments: [],
};

// ── DOM helpers ───────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const val = id => { const e = $(id); return e ? e.value.trim() : ''; };
const show = id => { const e = $(id); if (e) e.style.display = ''; };
const hide = id => { const e = $(id); if (e) e.style.display = 'none'; };
const setText = (id, t) => { const e = $(id); if (e) e.textContent = t; };
const esc = s => String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');

// ── Bootstrap ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  renderShell();
  // If the page loaded (not redirected), user is already logged in via Frappe
  // (index.py redirects guests). Fetch the employee profile.
  try {
    const profile = await api('get_employee_profile', {});
    S.employee = profile;
    await loadDepartments();
    enterApp();
  } catch (e) {
    // Session exists but no Employee linked — show informative error
    showLoginError(e.message || 'Your account is not linked to an Employee record. Please contact HR.');
  }
});

// ── Shell ─────────────────────────────────────────────────────────────────────
function renderShell() {
  if (!APP_ROOT) return;
  APP_ROOT.innerHTML = `
    <div id="er-loading">
      <div class="er-load-logo">✦</div>
      <div class="er-load-bar"></div>
    </div>
    <div id="er-error-screen" style="display:none">
      <div class="er-login-bg1"></div><div class="er-login-bg2"></div>
      <div class="er-login-card" style="text-align:center">
        <div class="er-login-logo" style="justify-content:center">
          <div class="er-login-logo-icon">✦</div>
          <div class="er-login-logo-text">e<span>Request</span></div>
        </div>
        <div id="er-error-msg" class="er-alert er-alert-error" style="margin-top:24px"></div>
        <a href="/login?redirect-to=/erequest-portal" class="er-btn er-btn-primary" style="margin-top:16px;display:inline-flex;width:auto;padding:11px 28px">
          ← Back to Login
        </a>
      </div>
    </div>
    <div id="er-app-inner" style="display:none">
      <nav id="er-topbar">
        <a class="er-brand" href="/erequest-portal">
          <div class="er-brand-icon">✦</div>e<span>Request</span>
        </a>
        <div class="er-nav-tabs">
          <button class="er-nav-tab active" id="tab-new"  onclick="switchTab('new',this)">New Request</button>
          <button class="er-nav-tab"         id="tab-list" onclick="switchTab('list',this)">My Requests</button>
        </div>
        <div class="er-topbar-right">
          <div class="er-user-chip" title="Sign out" onclick="signOut()">
            <div class="er-avatar" id="er-avatar">?</div>
            <span id="er-username">…</span>
            <span style="font-size:10px;color:var(--ink-faint)">↗</span>
          </div>
        </div>
      </nav>
      <div id="er-main">
        <div id="er-tab-new"></div>
        <div id="er-tab-list" style="display:none"></div>
      </div>
    </div>
    <div class="er-modal-overlay" id="er-modal" onclick="closeModalBackdrop(event)">
      <div class="er-modal">
        <div class="er-modal-header">
          <h3 id="er-modal-title">Request Detail</h3>
          <button class="er-modal-close" onclick="closeModal()">✕</button>
        </div>
        <div class="er-modal-body" id="er-modal-body">Loading…</div>
      </div>
    </div>`;
}

function showLoginError(msg) {
  hide('er-loading');
  hide('er-app-inner');
  const s = $('er-error-screen');
  if (s) s.style.display = 'flex';
  const m = $('er-error-msg');
  if (m) m.innerHTML = `<span>⚠️</span><span>${esc(msg)}</span>`;
}

// ── Enter App ─────────────────────────────────────────────────────────────────
function enterApp() {
  const tb = $('er-topbar'); if (tb) tb.style.display = 'flex';
  show('er-app-inner');
  const initials = (S.employee.employee_name || 'U').split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();
  setText('er-avatar', initials);
  setText('er-username', S.employee.employee_name || '');
  renderNewRequestTab();
  hideLoading();
}

async function loadDepartments() {
  try {
    const r = await api('get_departments', {});
    S.departments = (r || []).map(d => d.name);
  } catch (_) { S.departments = []; }
}

async function signOut() {
  if (!confirm('Sign out of eRequest?')) return;
  try { await api('portal_logout', {}); } catch (_) {}
  window.location.href = '/login';
}

// ── Tabs ──────────────────────────────────────────────────────────────────────
function switchTab(name, btn) {
  document.querySelectorAll('.er-nav-tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
  S.activeTab = name;
  $('er-tab-new').style.display  = name === 'new'  ? 'block' : 'none';
  $('er-tab-list').style.display = name === 'list' ? 'block' : 'none';
  if (name === 'list') { S.currentPage = 1; loadMyRequests(); }
}

// ── New Request Tab ───────────────────────────────────────────────────────────
function renderNewRequestTab() {
  const tab = $('er-tab-new'); if (!tab) return;
  tab.innerHTML = `
    <div id="er-new-area">
      <div class="er-page-header">
        <h1>New Request</h1>
        <p>Submit a payment or maintenance request for approval.</p>
      </div>
      <div class="er-type-grid">
        <div class="er-type-card" id="card-pay" onclick="selectType('Payment Request',this)">
          <div class="er-type-card-check">✓</div>
          <div class="er-type-icon pay">💰</div>
          <div class="er-type-card-title">Payment Request</div>
          <div class="er-type-card-desc">Vendor payments, reimbursements, utilities, and other financial transactions.</div>
        </div>
        <div class="er-type-card" id="card-maint" onclick="selectType('Maintenance Request',this)">
          <div class="er-type-card-check">✓</div>
          <div class="er-type-icon maint">🔧</div>
          <div class="er-type-card-title">Maintenance Request</div>
          <div class="er-type-card-desc">Facility repairs, inspections, equipment maintenance, and asset issues.</div>
        </div>
      </div>
      <div id="er-the-form" style="display:none"></div>
    </div>
    <div id="er-success-area" style="display:none"></div>`;
}

function selectType(type, card) {
  document.querySelectorAll('.er-type-card').forEach(c => c.classList.remove('active'));
  card.classList.add('active');
  S.requestType = type; S.priority = 'Medium'; S.urgency = '';
  const f = $('er-the-form'); if (!f) return;
  f.style.display = 'block';
  f.innerHTML = buildFormHTML(type);
  f.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ── Form Builder ──────────────────────────────────────────────────────────────
function buildFormHTML(type) {
  const isPay   = type === 'Payment Request';
  const isMaint = type === 'Maintenance Request';
  const deptOpts = S.departments.map(d => `<option value="${esc(d)}">${esc(d)}</option>`).join('');
  const empDept  = S.employee && S.employee.department ? S.employee.department : '';

  return `<div class="er-form-card">
  <!-- BASIC -->
  <div class="er-section">
    <div class="er-section-title">📋 Basic Information</div>
    <div class="er-row">
      <div class="er-form-group">
        <label class="er-label req" for="f-title">Request Title</label>
        <input id="f-title" class="er-input" type="text" placeholder="Brief, descriptive title…"/>
      </div>
      <div class="er-form-group">
        <label class="er-label req" for="f-dept">Department</label>
        <select id="f-dept" class="er-select">
          <option value="">Select department…</option>${deptOpts}
        </select>
      </div>
    </div>
    <div class="er-row">
      <div class="er-form-group">
        <label class="er-label req">Priority</label>
        <div class="er-priority-group">
          ${['Low','Medium','High','Urgent'].map(p =>
            `<button type="button" class="er-priority-pill${p==='Medium'?' sel-Medium':''}"
              data-val="${p}" onclick="setPriority('${p}',this)">${p}</button>`
          ).join('')}
        </div>
        <input type="hidden" id="f-priority" value="Medium"/>
      </div>
      ${isPay
        ? `<div class="er-form-group">
             <label class="er-label req" for="f-due">Payment Due Date</label>
             <input id="f-due" class="er-input" type="date"/>
           </div>`
        : `<div class="er-form-group">
             <label class="er-label" for="f-comp-date">Preferred Completion</label>
             <input id="f-comp-date" class="er-input" type="date"/>
           </div>`}
    </div>
    <div class="er-row">
      <div class="er-form-group">
        <label class="er-label" for="f-proj">Project (optional)</label>
        <input id="f-proj" class="er-input" type="text" placeholder="Project name or code"/>
      </div>
      <div class="er-form-group">
        <label class="er-label" for="f-cc">Cost Center (optional)</label>
        <input id="f-cc" class="er-input" type="text" placeholder="Cost center"/>
      </div>
    </div>
  </div>

  ${isPay   ? buildPaySections()   : ''}
  ${isMaint ? buildMaintSections() : ''}

  <!-- DESCRIPTION -->
  <div class="er-section">
    <div class="er-section-title">📝 Additional Details</div>
    <div class="er-form-group">
      <label class="er-label" for="f-desc">Detailed Description (optional)</label>
      <textarea id="f-desc" class="er-textarea" rows="4"
        placeholder="Any additional context or special instructions…"></textarea>
    </div>
  </div>

  <!-- FOOTER -->
  <div class="er-form-footer">
    <div class="er-form-footer-note">
      Request will be submitted as <strong>Draft</strong> and sent for manager approval.
    </div>
    <div class="er-form-footer-actions">
      <button type="button" class="er-btn er-btn-secondary" onclick="saveDraft()">Save Draft</button>
      <button type="button" class="er-btn er-btn-primary" id="er-submit-btn"
        onclick="submitRequest()" style="width:auto;padding:12px 28px">
        <span id="er-submit-text">Submit Request →</span>
        <span id="er-submit-spin" style="display:none"><span class="er-spinner"></span></span>
      </button>
    </div>
  </div>
</div>`;
}

function buildPaySections() {
  return `
  <div class="er-section">
    <div class="er-section-title">💰 Payment Details</div>
    <div class="er-row">
      <div class="er-form-group">
        <label class="er-label req" for="f-purpose">Payment Purpose</label>
        <input id="f-purpose" class="er-input" type="text" placeholder="What is this payment for?"/>
      </div>
      <div class="er-form-group">
        <label class="er-label" for="f-pay-type">Payment Type</label>
        <select id="f-pay-type" class="er-select">
          <option value="">Select type…</option>
          ${['Vendor Payment','Employee Reimbursement','Utility Payment','Tax Payment','Salary Advance','Petty Cash','Other'].map(o=>`<option>${o}</option>`).join('')}
        </select>
      </div>
    </div>
    <div class="er-row cols-3">
      <div class="er-form-group">
        <label class="er-label req" for="f-amount">Amount (NGN)</label>
        <input id="f-amount" class="er-input" type="number" placeholder="0.00" min="0" step="0.01" oninput="calcTotal()"/>
      </div>
      <div class="er-form-group">
        <label class="er-label" for="f-tax">Tax / Deduction</label>
        <input id="f-tax" class="er-input" type="number" placeholder="0.00" min="0" step="0.01" value="0" oninput="calcTotal()"/>
      </div>
      <div class="er-form-group">
        <label class="er-label" for="f-cat">Category</label>
        <select id="f-cat" class="er-select">
          <option value="">Select…</option>
          ${['Operational Expense','Capital Expenditure','Reimbursement','Salary & Benefits','Taxes','Other'].map(o=>`<option>${o}</option>`).join('')}
        </select>
      </div>
    </div>
    <div class="er-amount-total" id="er-amount-total">
      <div>
        <div class="er-amount-total-label">TOTAL AMOUNT</div>
        <div class="er-amount-total-words" id="er-amount-words">—</div>
      </div>
      <div class="er-amount-total-value" id="er-total-display">₦0.00</div>
    </div>
  </div>

  <div class="er-section">
    <div class="er-section-title">👤 Beneficiary Details</div>
    <div class="er-row">
      <div class="er-form-group">
        <label class="er-label req" for="f-payee-type">Payee Type</label>
        <select id="f-payee-type" class="er-select">
          <option value="">Select…</option>
          <option>Supplier</option><option>Employee</option><option>Other</option>
        </select>
      </div>
      <div class="er-form-group">
        <label class="er-label req" for="f-payee-name">Payee Name</label>
        <input id="f-payee-name" class="er-input" type="text" placeholder="Full name or business name"/>
      </div>
    </div>
    <div class="er-row">
      <div class="er-form-group">
        <label class="er-label" for="f-payee-email">Email</label>
        <input id="f-payee-email" class="er-input" type="email" placeholder="payee@example.com"/>
      </div>
      <div class="er-form-group">
        <label class="er-label" for="f-payee-phone">Phone</label>
        <input id="f-payee-phone" class="er-input" type="text" placeholder="+234 …"/>
      </div>
    </div>
    <div class="er-row">
      <div class="er-form-group">
        <label class="er-label req" for="f-acct-no">Account Number</label>
        <input id="f-acct-no" class="er-input" type="text" placeholder="0123456789" maxlength="20"/>
      </div>
      <div class="er-form-group">
        <label class="er-label req" for="f-acct-name">Account Name</label>
        <input id="f-acct-name" class="er-input" type="text" placeholder="As on bank records"/>
      </div>
    </div>
    <div class="er-row">
      <div class="er-form-group">
        <label class="er-label req" for="f-bank">Bank Name</label>
        <input id="f-bank" class="er-input" type="text" placeholder="e.g. Zenith Bank"/>
      </div>
      <div class="er-form-group">
        <label class="er-label" for="f-pay-method">Payment Method</label>
        <select id="f-pay-method" class="er-select">
          ${['Bank Transfer','Cheque','Cash','Mobile Money','Online Payment'].map(o=>`<option>${o}</option>`).join('')}
        </select>
      </div>
    </div>
  </div>

  <div class="er-section">
    <div class="er-section-title">🧾 Invoice &amp; Attachments</div>
    <div class="er-row">
      <div class="er-form-group">
        <label class="er-label" for="f-inv-ref">Invoice Reference</label>
        <input id="f-inv-ref" class="er-input" type="text" placeholder="INV-0001"/>
      </div>
      <div class="er-form-group">
        <label class="er-label" for="f-inv-date">Invoice Date</label>
        <input id="f-inv-date" class="er-input" type="date"/>
      </div>
    </div>
    <div class="er-row">
      <div class="er-form-group">
        <label class="er-label">Attach Invoice</label>
        <div class="er-file-upload">
          <input type="file" id="f-inv-file" accept=".pdf,.jpg,.jpeg,.png" onchange="showFileName(this,'er-inv-fname')"/>
          <div class="er-file-icon">📄</div>
          <div class="er-file-text"><strong>Click to upload</strong> or drag &amp; drop</div>
          <div class="er-file-text" style="font-size:11px;color:var(--ink-faint)">PDF, JPG, PNG up to 10MB</div>
          <div class="er-file-name" id="er-inv-fname"></div>
        </div>
      </div>
      <div class="er-form-group">
        <label class="er-label">Supporting Documents</label>
        <div class="er-file-upload">
          <input type="file" id="f-sup-file" accept=".pdf,.doc,.docx" onchange="showFileName(this,'er-sup-fname')"/>
          <div class="er-file-icon">📎</div>
          <div class="er-file-text"><strong>Quotations, reports</strong> etc.</div>
          <div class="er-file-text" style="font-size:11px;color:var(--ink-faint)">PDF, DOC up to 10MB</div>
          <div class="er-file-name" id="er-sup-fname"></div>
        </div>
      </div>
    </div>
  </div>`;
}

function buildMaintSections() {
  return `
  <div class="er-section">
    <div class="er-section-title">🔧 Maintenance Details</div>
    <div class="er-row">
      <div class="er-form-group">
        <label class="er-label req" for="f-maint-type">Maintenance Type</label>
        <select id="f-maint-type" class="er-select">
          <option value="">Select type…</option>
          ${['Preventive','Corrective','Emergency','Upgrade','Inspection'].map(o=>`<option>${o}</option>`).join('')}
        </select>
      </div>
      <div class="er-form-group">
        <label class="er-label req" for="f-maint-cat">Category</label>
        <select id="f-maint-cat" class="er-select">
          <option value="">Select category…</option>
          ${['Electrical','Plumbing','HVAC','Carpentry','Painting','IT Equipment','Furniture','Structural','Landscaping','Other'].map(o=>`<option>${o}</option>`).join('')}
        </select>
      </div>
    </div>
    <div class="er-row">
      <div class="er-form-group">
        <label class="er-label req" for="f-loc">Location / Area</label>
        <input id="f-loc" class="er-input" type="text" placeholder="e.g. Block A, 2nd Floor"/>
      </div>
      <div class="er-form-group">
        <label class="er-label" for="f-asset">Asset (if applicable)</label>
        <input id="f-asset" class="er-input" type="text" placeholder="Asset name or code"/>
      </div>
    </div>
    <div class="er-form-group">
      <label class="er-label req" for="f-issue">Describe the Issue</label>
      <textarea id="f-issue" class="er-textarea" rows="4"
        placeholder="Describe the problem in detail — what is happening, when it started, any safety concerns…"></textarea>
    </div>
    <div class="er-row">
      <div class="er-form-group">
        <label class="er-label">Urgency Level</label>
        <div class="er-urgency-grid">
          ${[['low','🟢 Low','Can wait'],['medium','🟡 Medium','Within a week'],
             ['high','🟠 High','Within 48 hours'],['critical','🔴 Critical','Immediate']]
            .map(([k,l,d]) => `
              <button type="button" class="er-urgency-btn" onclick="setUrgency('${k}','${l} - ${d}',this)">
                <div class="er-urgency-label">${l}</div>
                <div class="er-urgency-desc">${d}</div>
              </button>`).join('')}
        </div>
        <input type="hidden" id="f-urgency" value=""/>
      </div>
      <div class="er-form-group">
        <label class="er-label" for="f-est-cost">Estimated Cost (optional)</label>
        <input id="f-est-cost" class="er-input" type="number" placeholder="₦0.00" min="0" step="0.01"/>
        <div class="er-hint">Approximate cost in NGN</div>
      </div>
    </div>
  </div>

  <div class="er-section">
    <div class="er-section-title">📸 Photos &amp; Documents</div>
    <div class="er-row">
      <div class="er-form-group">
        <label class="er-label">Photos of Issue</label>
        <div class="er-file-upload">
          <input type="file" id="f-photos" accept="image/*" multiple onchange="showFileName(this,'er-photos-fname')"/>
          <div class="er-file-icon">📷</div>
          <div class="er-file-text"><strong>Upload photos</strong> of the issue</div>
          <div class="er-file-text" style="font-size:11px;color:var(--ink-faint)">JPG, PNG — multiple allowed</div>
          <div class="er-file-name" id="er-photos-fname"></div>
        </div>
      </div>
      <div class="er-form-group">
        <label class="er-label">Vendor Quotation (optional)</label>
        <div class="er-file-upload">
          <input type="file" id="f-quotation" accept=".pdf,.doc,.docx" onchange="showFileName(this,'er-quot-fname')"/>
          <div class="er-file-icon">📋</div>
          <div class="er-file-text"><strong>Vendor quote</strong> if available</div>
          <div class="er-file-text" style="font-size:11px;color:var(--ink-faint)">PDF, DOC up to 10MB</div>
          <div class="er-file-name" id="er-quot-fname"></div>
        </div>
      </div>
    </div>
    <div class="er-form-group">
      <label class="er-label" for="f-attach-notes">Attachment Notes</label>
      <textarea id="f-attach-notes" class="er-textarea" rows="2"
        placeholder="Notes about the attachments…"></textarea>
    </div>
  </div>`;
}

// ── Form interactions ─────────────────────────────────────────────────────────
function setPriority(v, btn) {
  document.querySelectorAll('.er-priority-pill').forEach(p => p.className = 'er-priority-pill');
  btn.className = `er-priority-pill sel-${v}`;
  const i = $('f-priority'); if (i) i.value = v;
  S.priority = v;
}
function setUrgency(k, v, btn) {
  document.querySelectorAll('.er-urgency-btn').forEach(b => b.className = 'er-urgency-btn');
  btn.className = `er-urgency-btn sel-${k}`;
  const i = $('f-urgency'); if (i) i.value = v;
  S.urgency = v;
}
function calcTotal() {
  const amt = parseFloat($('f-amount')?.value) || 0;
  const tax = parseFloat($('f-tax')?.value)    || 0;
  const tot = amt + tax;
  const box = $('er-amount-total'); if (box) box.style.display = tot > 0 ? 'flex' : 'none';
  const d = $('er-total-display'); if (d) d.textContent = '₦' + tot.toLocaleString('en-NG', {minimumFractionDigits: 2});
  const w = $('er-amount-words');  if (w) w.textContent = tot > 0 ? numToWords(Math.round(tot)) + ' Naira Only' : '—';
}
function showFileName(input, labelId) {
  const l = $(labelId); if (!l || !input.files || !input.files.length) return;
  l.textContent = input.files.length > 1 ? `${input.files.length} files selected` : input.files[0].name;
}

// ── Collect & validate ────────────────────────────────────────────────────────
function collectFormData() {
  const isPay   = S.requestType === 'Payment Request';
  const isMaint = S.requestType === 'Maintenance Request';
  return {
    request_type: S.requestType, priority: S.priority,
    title: val('f-title'), department: val('f-dept'),
    project: val('f-proj'), cost_center: val('f-cc'), description: val('f-desc'),
    ...(isPay && {
      payment_due_date: val('f-due'), payment_purpose: val('f-purpose'),
      payment_type: val('f-pay-type'), payment_category: val('f-cat'),
      currency: 'NGN',
      payment_amount: parseFloat($('f-amount')?.value) || 0,
      tax_amount:     parseFloat($('f-tax')?.value)    || 0,
      payee_type: val('f-payee-type'), payee_name: val('f-payee-name'),
      payee_email: val('f-payee-email'), payee_phone: val('f-payee-phone'),
      payee_account_number: val('f-acct-no'), payee_account_name: val('f-acct-name'),
      payee_bank_name: val('f-bank'), payment_method: val('f-pay-method'),
      invoice_reference: val('f-inv-ref'), invoice_date: val('f-inv-date'),
    }),
    ...(isMaint && {
      maintenance_type: val('f-maint-type'), maintenance_category: val('f-maint-cat'),
      location: val('f-loc'), asset: val('f-asset'),
      issue_description: val('f-issue'), urgency_level: S.urgency,
      preferred_completion_date: val('f-comp-date'),
      estimated_cost: parseFloat($('f-est-cost')?.value) || 0,
      attachment_notes: val('f-attach-notes'),
    }),
  };
}

function validateForm(d) {
  const e = [];
  if (!d.title)      e.push('Request title is required.');
  if (!d.department) e.push('Department is required.');
  if (S.requestType === 'Payment Request') {
    if (!d.payment_due_date)          e.push('Payment due date is required.');
    if (!d.payment_purpose)           e.push('Payment purpose is required.');
    if (!(d.payment_amount > 0))      e.push('Payment amount must be greater than zero.');
    if (!d.payee_type)                e.push('Payee type is required.');
    if (!d.payee_name)                e.push('Payee name is required.');
    if (!d.payee_account_number)      e.push('Account number is required.');
    if (!d.payee_account_name)        e.push('Account name is required.');
    if (!d.payee_bank_name)           e.push('Bank name is required.');
  }
  if (S.requestType === 'Maintenance Request') {
    if (!d.maintenance_type)          e.push('Maintenance type is required.');
    if (!d.maintenance_category)      e.push('Maintenance category is required.');
    if (!d.location)                  e.push('Location is required.');
    if (!d.issue_description)         e.push('Issue description is required.');
  }
  return e;
}

async function submitRequest() { await doSubmit(); }
async function saveDraft()    { await doSubmit(true); }

async function doSubmit(draftOnly = false) {
  const data = collectFormData();
  const errs = validateForm(data);
  if (errs.length) { alert('Please fix the following:\n\n' + errs.join('\n')); return; }

  setBusy('er-submit-btn', 'er-submit-text', 'er-submit-spin', true);
  try {
    const r = await api('submit_request', { data: JSON.stringify(data) });
    if (r.name) await uploadFiles(r.name);
    showSuccess(r.name, !draftOnly);
  } catch (e) {
    alert('Submission failed: ' + (e.message || 'Unknown error. Please try again.'));
  } finally {
    setBusy('er-submit-btn', 'er-submit-text', 'er-submit-spin', false);
  }
}

async function uploadFiles(docname) {
  const uploads = [
    ['f-inv-file',   'attach_invoice'],
    ['f-sup-file',   'attach_supporting_docs'],
    ['f-photos',     'attach_maintenance_photos'],
    ['f-quotation',  'vendor_quotation'],
  ];
  for (const [id, field] of uploads) {
    const inp = $(id); if (!inp || !inp.files || !inp.files.length) continue;
    for (const file of inp.files) {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('docname', docname);
      fd.append('fieldname', field);
      fd.append('csrf_token', window.__csrf || '');
      try {
        await fetch(`${API_BASE}.upload_attachment`, { method: 'POST', body: fd, credentials: 'include' });
      } catch (_) {}
    }
  }
}

function showSuccess(name, submitted) {
  const area = $('er-new-area'), succ = $('er-success-area');
  if (area) area.style.display = 'none';
  if (succ) {
    succ.style.display = 'block';
    succ.innerHTML = `
      <div class="er-success-wrap">
        <div class="er-success-card">
          <div class="er-success-icon">✓</div>
          <h2>${submitted ? 'Request Submitted!' : 'Draft Saved'}</h2>
          <p>${submitted ? 'Your request is pending manager approval.' : 'Your draft has been saved.'}</p>
          <p>Reference number:</p>
          <div class="er-success-ref">${esc(name)}</div>
          <div style="display:flex;gap:10px;justify-content:center;margin-top:12px;flex-wrap:wrap">
            <button class="er-btn er-btn-primary" style="width:auto;padding:12px 24px"
              onclick="resetNewForm()">Submit Another</button>
            <button class="er-btn er-btn-secondary"
              onclick="switchTab('list',document.getElementById('tab-list'))">View My Requests</button>
          </div>
        </div>
      </div>`;
  }
}

function resetNewForm() {
  const a = $('er-new-area'), s = $('er-success-area');
  if (s) s.style.display = 'none';
  if (a) a.style.display = 'block';
  S.requestType = null; S.priority = 'Medium'; S.urgency = '';
  document.querySelectorAll('.er-type-card').forEach(c => c.classList.remove('active'));
  const f = $('er-the-form'); if (f) { f.style.display = 'none'; f.innerHTML = ''; }
}

// ── My Requests ───────────────────────────────────────────────────────────────
async function loadMyRequests() {
  const tab = $('er-tab-list'); if (!tab) return;
  tab.innerHTML = `
    <div class="er-page-header"><h1>My Requests</h1><p>Track the status of all your submitted requests.</p></div>
    <div id="er-list-con"><div class="er-list-loading"><div class="er-list-spinner"></div>Loading your requests…</div></div>`;

  try {
    const r = await api('get_my_requests', { limit: PAGE_SIZE, offset: (S.currentPage - 1) * PAGE_SIZE });
    S.totalReqs = r.total || 0;
    const rows = r.rows || [];
    const con  = $('er-list-con'); if (!con) return;

    if (!rows.length) {
      con.innerHTML = `<div class="er-empty-state"><div class="er-empty-icon">📭</div><h3>No requests yet</h3><p>Your submitted requests will appear here.</p></div>`;
      return;
    }
    con.innerHTML = `<div class="er-request-list" id="er-rlist"></div><div id="er-pgn"></div>`;
    const list = $('er-rlist');

    rows.forEach((row, i) => {
      const isPay = row.request_type === 'Payment Request';
      const state = row.workflow_state || '';
      const sk    = state.includes('Pending') ? 'Pending' : state;
      const item  = document.createElement('div');
      item.className = 'er-request-item';
      item.style.animationDelay = `${i * 0.04}s`;
      item.innerHTML = `
        <div class="er-ri-icon ${isPay ? 'pay' : 'maint'}">${isPay ? '💰' : '🔧'}</div>
        <div class="er-ri-body">
          <div class="er-ri-title">${esc(row.title || '—')}</div>
          <div class="er-ri-meta">
            <span>${esc(row.request_type)}</span>
            <span>${row.request_date || ''}</span>
            ${isPay && row.payment_amount ? `<span>₦${Number(row.payment_amount).toLocaleString('en-NG')}</span>` : ''}
            ${row.urgency_level ? `<span>${esc(row.urgency_level)}</span>` : ''}
          </div>
        </div>
        <div class="er-ri-right">
          <div class="er-ri-ref">${esc(row.name)}</div>
          <span class="er-status er-status-${sk}">${esc(state)}</span>
        </div>`;
      item.addEventListener('click', () => openDetailModal(row.name));
      list.appendChild(item);
    });
    renderPagination();
  } catch (e) {
    const c = $('er-list-con');
    if (c) c.innerHTML = `<div class="er-empty-state"><div class="er-empty-icon">⚠️</div><h3>Could not load requests</h3><p>${esc(e.message)}</p></div>`;
  }
}

function renderPagination() {
  const pages = Math.ceil(S.totalReqs / PAGE_SIZE); if (pages <= 1) return;
  const pg = $('er-pgn'); if (!pg) return;
  let h = `<div class="er-pagination">
    <button class="er-page-btn" onclick="goPage(${S.currentPage-1})" ${S.currentPage===1?'disabled':''}>‹</button>`;
  for (let p = 1; p <= pages; p++)
    h += `<button class="er-page-btn${p===S.currentPage?' active':''}" onclick="goPage(${p})">${p}</button>`;
  h += `<button class="er-page-btn" onclick="goPage(${S.currentPage+1})" ${S.currentPage===pages?'disabled':''}>›</button></div>`;
  pg.innerHTML = h;
}
function goPage(p) {
  const pages = Math.ceil(S.totalReqs / PAGE_SIZE);
  if (p < 1 || p > pages) return;
  S.currentPage = p; loadMyRequests();
}

// ── Detail Modal ──────────────────────────────────────────────────────────────
async function openDetailModal(name) {
  const modal = $('er-modal'), body = $('er-modal-body'), titleEl = $('er-modal-title');
  if (!modal) return;
  if (titleEl) titleEl.textContent = name;
  if (body)    body.innerHTML = '<div class="er-list-loading"><div class="er-list-spinner"></div>Loading…</div>';
  modal.classList.add('open');
  try {
    const doc = await api('get_request_detail', { name });
    if (titleEl) titleEl.textContent = `${name} — ${doc.title || ''}`;
    if (body)    body.innerHTML = buildDetailHTML(doc);
  } catch (e) {
    if (body) body.innerHTML = `<div class="er-alert er-alert-error"><span>⚠️</span><span>${esc(e.message)}</span></div>`;
  }
}

function buildDetailHTML(doc) {
  const isPay   = doc.request_type === 'Payment Request';
  const isMaint = doc.request_type === 'Maintenance Request';
  const state   = doc.workflow_state || '';
  const sk      = state.includes('Pending') ? 'Pending' : state;

  const fields = [
    ['Status',     `<span class="er-status er-status-${sk}">${esc(state)}</span>`],
    ['Type',       doc.request_type], ['Priority', doc.priority],
    ['Date',       doc.request_date], ['Department', doc.department], ['Company', doc.company],
    ...(isPay ? [
      ['Purpose',  doc.payment_purpose],
      ['Amount',   doc.payment_amount ? `₦${Number(doc.payment_amount).toLocaleString('en-NG')}` : '—'],
      ['Tax',      `₦${Number(doc.tax_amount||0).toLocaleString('en-NG')}`],
      ['Total',    doc.total_amount   ? `₦${Number(doc.total_amount).toLocaleString('en-NG')}`   : '—'],
      ['Payee',    doc.payee_name], ['Bank', doc.payee_bank_name],
      ['Account',  doc.payee_account_number], ['Due Date', doc.payment_due_date],
    ] : []),
    ...(isMaint ? [
      ['Maint. Type', doc.maintenance_type], ['Category', doc.maintenance_category],
      ['Location', doc.location], ['Urgency', doc.urgency_level],
    ] : []),
  ];

  const grid = fields.map(([l, v]) => `
    <div class="er-detail-row">
      <div class="er-detail-label">${l}</div>
      <div class="er-detail-value">${v || '—'}</div>
    </div>`).join('');

  const steps = [
    { label: 'Submitted',       user: doc.created_by,       date: doc.created_date,           done: true },
    { label: 'Manager Review',  user: doc.manager_approval,  date: doc.manager_approval_date,  comment: doc.manager_comments,  done: !!doc.manager_approval,  pending: state.includes('Manager') },
    { label: 'Finance Review',  user: doc.finance_approval,  date: doc.finance_approval_date,  comment: doc.finance_comments,  done: !!doc.finance_approval,  pending: state.includes('Finance') },
    { label: 'Final Approval',  user: doc.final_approval,    date: doc.final_approval_date,    comment: doc.final_comments,    done: !!doc.final_approval,    pending: state.includes('Final') },
  ];

  const timeline = steps.map((s, i) => {
    const cls  = s.done ? 'er-tl-done' : s.pending ? 'er-tl-pending' : 'er-tl-waiting';
    const icon = s.done ? '✓' : s.pending ? '●' : String(i + 1);
    return `<div class="er-tl-step ${cls}">
      <div class="er-tl-dot">${icon}</div>
      <div>
        <div class="er-tl-label">${s.label}</div>
        ${s.user    ? `<div class="er-tl-user">${esc(s.user)}</div>` : ''}
        ${s.date    ? `<div class="er-tl-date">${s.date}</div>` : ''}
        ${s.comment ? `<div class="er-tl-comment">"${esc(s.comment)}"</div>` : ''}
      </div>
    </div>`;
  }).join('');

  return `
    <div class="er-detail-grid">${grid}</div>
    ${doc.description ? `<div style="margin-top:16px"><div class="er-detail-label" style="margin-bottom:6px">Description</div>
      <div style="font-size:13.5px;color:var(--ink-soft);line-height:1.6">${esc(doc.description)}</div></div>` : ''}
    <div style="margin-top:20px">
      <div class="er-section-title" style="font-size:10px;letter-spacing:1px;font-weight:700;color:var(--forest-mid);text-transform:uppercase;margin-bottom:8px">Approval Timeline</div>
      <div class="er-timeline-steps">${timeline}</div>
    </div>
    ${doc.rejection_reason ? `<div class="er-alert er-alert-error" style="margin-top:16px">
      <span>⚠️</span><span><strong>Rejection Reason:</strong> ${esc(doc.rejection_reason)}</span></div>` : ''}`;
}

function closeModal()            { const m = $('er-modal'); if (m) m.classList.remove('open'); }
function closeModalBackdrop(e)   { if (e.target === $('er-modal')) closeModal(); }

// ── API helper ────────────────────────────────────────────────────────────────
async function api(method, params = {}) {
  const res = await fetch(`${API_BASE}.${method}`, {
    method:  'POST',
    headers: {
      'Content-Type':       'application/json',
      'Accept':             'application/json',
      'X-Frappe-CSRF-Token': window.__csrf || '',
    },
    credentials: 'include',
    body: JSON.stringify(params),
  });
  const json = await res.json();

  // Parse Frappe error messages
  if (json.exc || json._server_messages) {
    let msg = 'An error occurred.';
    try {
      const msgs = JSON.parse(json._server_messages || '[]');
      const parsed = JSON.parse(msgs[0] || '{}');
      msg = parsed.message || msg;
    } catch (_) {}
    if (!msg || msg === 'An error occurred.') {
      try {
        const lines = JSON.parse(json.exc || '[""]')[0].split('\n').filter(Boolean);
        const last = lines[lines.length - 1] || '';
        msg = last.includes(': ') ? last.split(': ').slice(1).join(': ') : last || msg;
      } catch (_) {}
    }
    throw new Error(msg);
  }
  return json.message !== undefined ? json.message : json;
}

// ── Utility ───────────────────────────────────────────────────────────────────
function hideLoading() { const l = $('er-loading'); if (l) l.classList.add('hidden'); }
function setBusy(btnId, textId, spinId, busy) {
  const b = $(btnId); if (b) b.disabled = busy;
  const t = $(textId); if (t) t.style.display = busy ? 'none' : '';
  const s = $(spinId); if (s) s.style.display = busy ? 'inline' : 'none';
}

function numToWords(n) {
  if (!n) return 'Zero';
  const ones = ['','One','Two','Three','Four','Five','Six','Seven','Eight','Nine','Ten',
                 'Eleven','Twelve','Thirteen','Fourteen','Fifteen','Sixteen','Seventeen','Eighteen','Nineteen'];
  const tens = ['','','Twenty','Thirty','Forty','Fifty','Sixty','Seventy','Eighty','Ninety'];
  function b1k(x) {
    if (!x) return '';
    if (x < 20) return ones[x];
    if (x < 100) return tens[Math.floor(x/10)] + (x%10 ? '-' + ones[x%10] : '');
    return ones[Math.floor(x/100)] + ' Hundred' + (x%100 ? ' and ' + b1k(x%100) : '');
  }
  const bi=Math.floor(n/1e9),r=n%1e9,mi=Math.floor(r/1e6),r2=r%1e6,ti=Math.floor(r2/1e3),ri=r2%1e3;
  return [bi&&b1k(bi)+' Billion', mi&&b1k(mi)+' Million', ti&&b1k(ti)+' Thousand', ri&&b1k(ri)]
    .filter(Boolean).join(' ');
}
