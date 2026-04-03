/**
 * MailVault — Frappe Page Controller
 * ecclesia/page/mail_hub/mail_hub.js
 *
 * Page registration: frappe.pages["mail_hub"] — key matches page.json `name` exactly.
 *
 * Backend API calls go to ecclesia/api/mail_hub.py (NOT page/mail_hub/mail_hub.py).
 * Reason: the `page/` directory has no __init__.py so Python cannot import it as a
 * module. All @frappe.whitelist() methods live in ecclesia/api/mail_hub.py and are
 * called as:  ecclesia.api.mail_hub.<method_name>
 */

frappe.pages["mail_hub"].on_page_load = function (wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "MailVault",
        single_column: true,
    });

    // Stash page ref on wrapper so on_page_show/hide can access it
    wrapper._mv_page = page;

    // Mount CSS first
    MailVault.injectCSS();

    // page.body is the jQuery object Frappe exposes for page content area
    page.body.html(MailVault.getHTML());

    // Boot the app
    MailVault.init(wrapper, page);
};

frappe.pages["mail_hub"].on_page_show = function (wrapper) {
    MailVault.onShow();
};

frappe.pages["mail_hub"].on_page_hide = function (wrapper) {
    MailVault.onHide();
};

// ─────────────────────────────────────────────────────────────
// MAILVAULT NAMESPACE
// ─────────────────────────────────────────────────────────────
window.MailVault = {

    // ── State ──────────────────────────────────────────────
    state: {
        accounts: [],
        labels: [],
        folderCounts: {},
        prefs: {},
        activeFolder: "inbox",
        activeAccount: null,
        activeEmailName: null,
        selectedNames: new Set(),
        filter: "all",
        searchQuery: "",
        currentPage: 0,
        pageSize: 40,
        totalEmails: 0,
        lastPolled: null,
        pollInterval: null,
        isLoading: false,
        theme: "navy",
        sidebarCollapsed: false,
        emails: [],   // current page cache
    },

    // ── API Wrappers ────────────────────────────────────────
    api: {
        call(method, args = {}) {
            return new Promise((resolve, reject) => {
                frappe.call({
                    method: `ecclesia.api.mail_hub.${method}`,
                    args,
                    callback: (r) => resolve(r.message || {}),
                    error: (err) => {
                        frappe.msgprint({
                            title: __("MailVault Error"),
                            message: err.message || __("An error occurred"),
                            indicator: "red",
                        });
                        reject(err);
                    },
                });
            });
        },
    },

    // ── Init ───────────────────────────────────────────────
    async init(wrapper, page) {
        this._wrapper = wrapper;
        this._page = page;

        // Load user preferences first (theme, etc.)
        this.loadPrefsFromStorage();

        // Small defer so DOM is painted before we touch it
        await new Promise(r => setTimeout(r, 0));

        // Show skeleton
        this.showSkeleton();

        try {
            // Boot data: accounts, labels, folder counts
            const boot = await this.api.call("get_boot_data");
            this.state.accounts     = boot.accounts    || [];
            this.state.labels       = boot.labels      || [];
            this.state.folderCounts = boot.folder_counts || {};
            this.state.prefs        = boot.prefs       || {};

            // Apply saved theme
            if (this.state.prefs.theme) {
                this.applyTheme(this.state.prefs.theme, false);
            }

            // Render sidebar chrome
            this.renderAccounts();
            this.renderFolderNav();
            this.renderLabelNav();
            this.renderThemeSwitcher();

            // Load inbox
            await this.loadEmails();

            // Set up real-time
            this.initRealtime();
            this.startPolling();

            // Welcome toast
            const unread = this.state.folderCounts.inbox || 0;
            this.toast("MailVault connected", "🔗",
                       `${unread} unread message${unread !== 1 ? "s" : ""}`);

        } catch (e) {
            console.error("MailVault boot error:", e);
            this.toast("Could not connect to mail server", "⚠️", e.message);
        }

        // Keyboard shortcuts
        this.bindKeyboard();
    },

    onShow() {
        // Resume polling
        if (!this.state.pollInterval) this.startPolling();
        frappe.breadcrumbs.add("Ecclesia", "mail-vault");
    },

    onHide() {
        // Pause polling to save resources
        if (this.state.pollInterval) {
            clearInterval(this.state.pollInterval);
            this.state.pollInterval = null;
        }
    },

    // ── Real-time ──────────────────────────────────────────

    initRealtime() {
        frappe.realtime.on("new_email", (data) => {
            this.handleNewEmailEvent(data);
        });

        frappe.realtime.on("email_sync_complete", (data) => {
            this.handleSyncComplete(data);
        });
    },

    handleNewEmailEvent(data) {
        const accounts = this.state.accounts.map(a => a.name);
        if (!accounts.includes(data.email_account)) return;

        const acct = this.state.accounts.find(a => a.name === data.email_account);
        if (acct) acct.unread_count = (acct.unread_count || 0) + 1;
        this.renderAccounts();

        this._pendingNewCount = (this._pendingNewCount || 0) + 1;
        this.showRefreshBar(this._pendingNewCount);

        this.toast(data.sender_name || "New message", "📬", data.subject);
        this.setRTStatus("live");
    },

    handleSyncComplete(data) {
        if (data.new_count > 0) {
            this._pendingNewCount = (this._pendingNewCount || 0) + data.new_count;
            this.showRefreshBar(this._pendingNewCount);
        }
        this.setRTStatus("live");
    },

    startPolling() {
        this.state.lastPolled = frappe.datetime.now_datetime();
        this.state.pollInterval = setInterval(async () => {
            await this.pollForNewEmails();
        }, 30000);
    },

    async pollForNewEmails() {
        if (this.state.isLoading) return;

        try {
            const result = await this.api.call("poll_new_emails", {
                since_datetime: this.state.lastPolled,
                folder: this.state.activeFolder,
                account: this.state.activeAccount || "",
            });

            this.state.lastPolled = frappe.datetime.now_datetime();
            this.setRTStatus("live");

            if (result.count > 0) {
                this._pendingNewCount = (this._pendingNewCount || 0) + result.count;
                this.showRefreshBar(this._pendingNewCount);
                this.state.folderCounts.inbox =
                    (this.state.folderCounts.inbox || 0) + result.count;
                this.renderFolderNav();
            }
        } catch (e) {
            this.setRTStatus("offline");
        }
    },

    showRefreshBar(count) {
        const bar = document.getElementById("mv-refresh-bar");
        if (!bar) return;
        bar.classList.add("visible");
        const text = document.getElementById("mv-refresh-text");
        if (text) text.textContent =
            `${count} new message${count > 1 ? "s" : ""} — click to load`;
    },

    async loadNewEmails() {
        this._pendingNewCount = 0;
        const bar = document.getElementById("mv-refresh-bar");
        if (bar) bar.classList.remove("visible");
        await this.loadEmails(true);
    },

    setRTStatus(status) {
        const dot   = document.getElementById("mv-rt-dot");
        const label = document.getElementById("mv-rt-label");
        if (!dot || !label) return;

        if (status === "live") {
            dot.style.background = "var(--accent3)";
            label.textContent    = "Live";
            this._lastRefresh    = new Date();
        } else if (status === "offline") {
            dot.style.background = "var(--accent-danger)";
            label.textContent    = "Offline";
        } else {
            dot.style.background = "var(--accent-warn)";
            label.textContent    = "Syncing…";
        }
    },

    // ── Load Emails ────────────────────────────────────────

    async loadEmails(animate = false) {
        this.state.isLoading = true;
        this.showListSkeleton();

        try {
            const result = await this.api.call("get_emails", {
                folder: this.state.activeFolder,
                account: this.state.activeAccount || "",
                label: "",
                search: this.state.searchQuery,
                filter_type: this.state.filter,
                page: this.state.currentPage,
                page_size: this.state.pageSize,
            });

            this.state.emails      = result.emails || [];
            this.state.totalEmails = result.total  || 0;
            this.renderEmailList(animate);

        } catch (e) {
            console.error("Load emails error:", e);
            this.showListError();
        } finally {
            this.state.isLoading = false;
        }
    },

    // ── Select / Open Email ────────────────────────────────

    async selectEmail(name) {
        if (this.state.activeEmailName === name) return;
        this.state.activeEmailName = name;

        document.querySelectorAll(".mv-email-row").forEach(r => r.classList.remove("selected"));
        const row = document.getElementById(`mv-row-${name}`);
        if (row) {
            row.classList.add("selected");
            row.classList.remove("unread");
            const dot = row.querySelector(".mv-unread-dot");
            if (dot) dot.remove();
        }

        this.showDetailLoading();

        try {
            const result = await this.api.call("get_email_thread", {
                communication_name: name,
            });
            this.renderDetail(result.thread || []);
            this.updateFolderCounts();

        } catch (e) {
            this.showDetailError();
        }
    },

    // ── Email Actions ──────────────────────────────────────

    async toggleStar(name, el) {
        try {
            const result = await this.api.call("toggle_star", { name });
            const isStarred = result.starred;
            if (el) {
                el.textContent = isStarred ? "★" : "☆";
                el.classList.toggle("starred", !!isStarred);
            }
            const email = this.state.emails.find(e => e.name === name);
            if (email) email.mail_starred = isStarred;
        } catch (e) {
            console.error("Toggle star error:", e);
        }
    },

    async markRead(names, read = 1) {
        names = Array.isArray(names) ? names : [names];
        try {
            await this.api.call("mark_read", {
                names: JSON.stringify(names),
                read,
            });
            names.forEach(n => {
                const row = document.getElementById(`mv-row-${n}`);
                if (row) row.classList.toggle("unread", !read);
                const email = this.state.emails.find(e => e.name === n);
                if (email) email.read_by_current_user = read;
            });
            this.updateFolderCounts();
        } catch (e) {
            console.error("Mark read error:", e);
        }
    },

    async moveToFolder(names, folder) {
        names = Array.isArray(names) ? names : [names];
        try {
            await this.api.call("move_to_folder", {
                names: JSON.stringify(names),
                folder,
            });
            names.forEach(n => {
                this.state.emails = this.state.emails.filter(e => e.name !== n);
                const row = document.getElementById(`mv-row-${n}`);
                if (row) {
                    row.style.transition = "opacity 0.3s, transform 0.3s";
                    row.style.opacity    = "0";
                    row.style.transform  = "translateX(-20px)";
                    setTimeout(() => row.remove(), 300);
                }
            });

            if (names.includes(this.state.activeEmailName)) {
                this.showDetailEmpty();
            }

            this.toast(`Moved to ${folder}`, "📁", null, true);
            this.updateFolderCounts();
            this.closeModal("mv-move-modal");

        } catch (e) {
            this.toast("Move failed", "⚠️", e.message);
        }
    },

    async updateLabels(name, labels) {
        try {
            await this.api.call("update_labels", {
                name,
                labels: JSON.stringify(labels),
            });
            const email = this.state.emails.find(e => e.name === name);
            if (email) {
                email.labels     = labels;
                email.mail_label = labels.join(",");
            }
            this.closeModal("mv-label-modal");
            this.toast("Labels updated", "🏷");
            this.renderEmailList();
        } catch (e) {
            this.toast("Label update failed", "⚠️");
        }
    },

    async sendEmail(opts) {
        try {
            this.setBtn("mv-send-btn", "Sending…", true);
            await this.api.call("send_email", opts);
            this.closeModal("mv-compose-modal");
            this.clearCompose();
            this.toast("Message sent", "✅");
            this.state.folderCounts.sent = (this.state.folderCounts.sent || 0) + 1;
            this.renderFolderNav();
        } catch (e) {
            this.toast("Send failed", "⚠️", e.message);
        } finally {
            this.setBtn("mv-send-btn", "Send →", false);
        }
    },

    async saveDraft() {
        const opts = this.getComposeValues();
        try {
            await this.api.call("save_draft", opts);
            this.closeModal("mv-compose-modal");
            this.toast("Draft saved", "📝");
            this.state.folderCounts.drafts = (this.state.folderCounts.drafts || 0) + 1;
            this.renderFolderNav();
        } catch (e) {
            this.toast("Could not save draft", "⚠️");
        }
    },

    async sendReply() {
        const textarea = document.getElementById("mv-reply-textarea");
        const content  = textarea ? textarea.value.trim() : "";

        if (!content) {
            this.toast("Write a reply first", "⚠️");
            return;
        }

        const modeEl      = document.querySelector(".mv-rmode-tab.active");
        const mode        = modeEl ? modeEl.dataset.mode : "reply";
        const activeEmail = this.state.emails.find(e => e.name === this.state.activeEmailName);
        const fromAccount = activeEmail
            ? activeEmail.email_account
            : (this.state.accounts[0] ? this.state.accounts[0].name : "");

        let recipients = "";
        if (mode === "reply-all" && activeEmail) {
            recipients = [activeEmail.sender, activeEmail.recipients].filter(Boolean).join(",");
        } else if (activeEmail) {
            recipients = activeEmail.sender || "";
        }

        try {
            this.setBtn("mv-reply-send-btn", "Sending…", true);
            await this.api.call("send_email", {
                from_account: fromAccount,
                recipients,
                subject: "Re: " + (activeEmail ? activeEmail.subject : ""),
                content: `<p>${content}</p>`,
                in_reply_to: this.state.activeEmailName,
            });

            if (textarea) textarea.value = "";
            this.toast("Reply sent", "✅");
            await this.selectEmail(this.state.activeEmailName);

        } catch (e) {
            this.toast("Reply failed", "⚠️");
        } finally {
            this.setBtn("mv-reply-send-btn", "Send →", false);
        }
    },

    async deleteEmail(name) {
        const email = this.state.emails.find(e => e.name === name);
        if (email && email.status === "Trash") {
            frappe.confirm(__("Permanently delete this message?"), async () => {
                await this.api.call("delete_permanent", { names: JSON.stringify([name]) });
                this.state.emails = this.state.emails.filter(e => e.name !== name);
                this.renderEmailList();
                if (this.state.activeEmailName === name) this.showDetailEmpty();
                this.toast("Permanently deleted", "🗑");
            });
        } else {
            await this.moveToFolder([name], "trash");
        }
    },

    // ── Folder & Account Selection ─────────────────────────

    async selectFolder(id) {
        this.state.activeFolder    = id;
        this.state.activeEmailName = null;
        this.state.currentPage     = 0;
        this.state.searchQuery     = "";
        const searchEl = document.getElementById("mv-search");
        if (searchEl) searchEl.value = "";

        this.clearSelection();
        this.renderFolderNav();
        this.showDetailEmpty();
        await this.loadEmails();

        const folder = this.state.activeFolder.charAt(0).toUpperCase()
                     + this.state.activeFolder.slice(1);
        document.getElementById("mv-list-title").textContent = folder;
    },

    selectAccount(id) {
        this.state.activeAccount = this.state.activeAccount === id ? null : id;
        this.state.currentPage   = 0;
        this.renderAccounts();
        this.loadEmails();
    },

    setFilter(filter, el) {
        this.state.filter      = filter;
        this.state.currentPage = 0;
        document.querySelectorAll(".mv-ftab").forEach(t => t.classList.remove("active"));
        if (el) el.classList.add("active");
        this.loadEmails();
    },

    onSearch(val) {
        this.state.searchQuery = val;
        this.state.currentPage = 0;
        clearTimeout(this._searchTimer);
        this._searchTimer = setTimeout(() => this.loadEmails(), 350);
    },

    // ── Bulk Actions ───────────────────────────────────────

    toggleSelect(name, checked) {
        if (checked) this.state.selectedNames.add(name);
        else this.state.selectedNames.delete(name);
        this.updateBulkBar();
    },

    selectAll() {
        const all = this.state.emails.map(e => e.name);
        if (this.state.selectedNames.size === all.length) {
            this.clearSelection();
        } else {
            all.forEach(n => this.state.selectedNames.add(n));
            document.querySelectorAll(".mv-er-check").forEach(cb => cb.checked = true);
            this.updateBulkBar();
        }
    },

    clearSelection() {
        this.state.selectedNames.clear();
        document.querySelectorAll(".mv-er-check").forEach(cb => cb.checked = false);
        this.updateBulkBar();
    },

    updateBulkBar() {
        const bar = document.getElementById("mv-bulk-bar");
        if (!bar) return;
        const count = this.state.selectedNames.size;
        bar.classList.toggle("visible", count > 0);
        const countEl = document.getElementById("mv-bulk-count");
        if (countEl) countEl.textContent = `${count} selected`;
    },

    bulkMarkRead() {
        const names = [...this.state.selectedNames];
        this.markRead(names, 1);
        this.clearSelection();
        this.toast(`${names.length} marked as read`, "✅");
    },

    bulkMove() {
        this._bulkMoveMode = true;
        this.openMoveModal();
    },

    bulkDelete() {
        const names = [...this.state.selectedNames];
        frappe.confirm(`Delete ${names.length} message(s)?`, async () => {
            await this.moveToFolder(names, "trash");
            this.clearSelection();
        });
    },

    // ── Update Folder Counts ───────────────────────────────

    async updateFolderCounts() {
        try {
            const boot = await this.api.call("get_boot_data");
            this.state.folderCounts = boot.folder_counts || {};
            this.state.accounts     = boot.accounts      || [];
            this.renderFolderNav();
            this.renderAccounts();
        } catch (e) {}
    },

    // ── Theme ──────────────────────────────────────────────

    applyTheme(theme, save = true) {
        this.state.theme = theme;
        document.body.setAttribute("data-theme", theme);
        this.renderThemeSwitcher();
        if (save) {
            this.state.prefs.theme = theme;
            this.api.call("save_preferences", {
                prefs: JSON.stringify(this.state.prefs),
            }).catch(() => {});
            try { localStorage.setItem("mv_theme", theme); } catch (e) {}
        }
    },

    loadPrefsFromStorage() {
        try {
            const t = localStorage.getItem("mv_theme");
            if (t) this.applyTheme(t, false);
        } catch (e) {}
    },

    // ── Keyboard ───────────────────────────────────────────

    bindKeyboard() {
        // Guard: only bind once
        if (this._keyboardBound) return;
        this._keyboardBound = true;

        document.addEventListener("keydown", (e) => {
            if (["INPUT", "TEXTAREA", "SELECT"].includes(e.target.tagName)) return;

            if (e.key === "c" || e.key === "C") {
                this.openModal("mv-compose-modal");
            } else if (e.key === "r" || e.key === "R") {
                if (this.state.activeEmailName) this.focusReply();
            } else if (e.key === "Escape") {
                document.querySelectorAll(".mv-modal-overlay.open")
                        .forEach(m => m.classList.remove("open"));
            } else if (e.key === "ArrowDown") {
                this._navigateEmail(1);
            } else if (e.key === "ArrowUp") {
                this._navigateEmail(-1);
            } else if (e.key === "?" || e.key === "/") {
                const el = document.getElementById("mv-search");
                if (el) { el.focus(); e.preventDefault(); }
            } else if (e.key === "e" || e.key === "E") {
                if (this.state.activeEmailName) {
                    this.moveToFolder([this.state.activeEmailName], "archive");
                }
            } else if (e.key === "Delete") {
                if (this.state.activeEmailName) {
                    this.deleteEmail(this.state.activeEmailName);
                }
            }
        });
    },

    _navigateEmail(dir) {
        const emails = this.state.emails;
        const idx    = emails.findIndex(e => e.name === this.state.activeEmailName);
        const next   = idx + dir;
        if (next >= 0 && next < emails.length) {
            this.selectEmail(emails[next].name);
        }
    },

    // ── Compose ────────────────────────────────────────────

    getComposeValues() {
        return {
            from_account: document.getElementById("mv-compose-from")?.value   || "",
            recipients:   document.getElementById("mv-compose-to")?.value     || "",
            cc:           document.getElementById("mv-compose-cc")?.value     || "",
            bcc:          document.getElementById("mv-compose-bcc")?.value    || "",
            subject:      document.getElementById("mv-compose-subject")?.value || "",
            content:      document.getElementById("mv-compose-body")?.value   || "",
        };
    },

    clearCompose() {
        ["mv-compose-to","mv-compose-cc","mv-compose-bcc",
         "mv-compose-subject","mv-compose-body"].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = "";
        });
    },

    submitCompose() {
        const opts = this.getComposeValues();
        if (!opts.recipients) {
            this.toast("Enter at least one recipient", "⚠️");
            return;
        }
        if (!opts.subject) {
            frappe.confirm("Send without a subject?", () => this.sendEmail(opts));
        } else {
            this.sendEmail(opts);
        }
    },

    focusReply() {
        const container = document.getElementById("mv-reply-container");
        if (container) container.style.display = "block";
        const textarea  = document.getElementById("mv-reply-textarea");
        if (textarea) textarea.focus();
    },

    setReplyMode(mode, el) {
        document.querySelectorAll(".mv-rmode-tab").forEach(t => t.classList.remove("active"));
        if (el) el.classList.add("active");
        const activeEmail = this.state.emails.find(e => e.name === this.state.activeEmailName);
        if (!activeEmail) return;
        const chip = document.getElementById("mv-reply-to-chip");
        if (chip) {
            if (mode === "forward")   chip.textContent = "(enter recipients)";
            else if (mode === "reply-all") chip.textContent =
                [activeEmail.sender, activeEmail.recipients].filter(Boolean).join(", ");
            else chip.textContent = activeEmail.sender || "";
        }
    },

    // ── Sidebar Toggle ─────────────────────────────────────

    toggleSidebar() {
        this.state.sidebarCollapsed = !this.state.sidebarCollapsed;
        const app = document.getElementById("mv-app");
        if (app) app.classList.toggle("sidebar-collapsed", this.state.sidebarCollapsed);
        const btn = document.getElementById("mv-sidebar-toggle");
        if (btn) btn.textContent = this.state.sidebarCollapsed ? "▶" : "◀";
        this.state.prefs.sidebar_collapsed = this.state.sidebarCollapsed;
    },

    // ── Modals ─────────────────────────────────────────────

    openModal(id) {
        const el = document.getElementById(id);
        if (el) el.classList.add("open");
    },

    closeModal(id) {
        const el = document.getElementById(id);
        if (el) el.classList.remove("open");
    },

    openMoveModal() {
        const list = document.getElementById("mv-folder-list");
        if (list) {
            list.innerHTML = [
                { id:"inbox",   label:"Inbox",   icon:"📥" },
                { id:"archive", label:"Archive", icon:"🗂" },
                { id:"spam",    label:"Spam",    icon:"🚫" },
                { id:"trash",   label:"Trash",   icon:"🗑" },
            ].map(f => `
              <div class="mv-folder-option ${f.id === this.state.activeFolder ? "selected" : ""}"
                   onclick="MailVault._moveTarget='${f.id}';
                            document.querySelectorAll('.mv-folder-option').forEach(x=>x.classList.remove('selected'));
                            this.classList.add('selected')">
                <span>${f.icon}</span><span>${f.label}</span>
              </div>
            `).join("");
        }
        this._moveTarget = "";
        this.openModal("mv-move-modal");
    },

    confirmMove() {
        if (!this._moveTarget) {
            this.toast("Select a folder first", "⚠️");
            return;
        }
        const names = this._bulkMoveMode
            ? [...this.state.selectedNames]
            : this.state.activeEmailName
                ? [this.state.activeEmailName]
                : [];

        if (!names.length) {
            this.closeModal("mv-move-modal");
            return;
        }
        this._bulkMoveMode = false;
        this.moveToFolder(names, this._moveTarget);
    },

    openLabelModal() {
        const activeEmail    = this.state.emails.find(e => e.name === this.state.activeEmailName);
        const currentLabels  = activeEmail ? (activeEmail.labels || []) : [];
        const body           = document.getElementById("mv-label-list-body");
        if (body) {
            body.innerHTML = this.state.labels.map(l => `
              <div class="mv-label-toggle-row"
                   onclick="MailVault._toggleLabelCheck('${l.label_name}', this)">
                <div style="width:10px;height:10px;border-radius:50%;background:${l.color};flex-shrink:0"></div>
                <span class="mv-label-name">${l.label_name}</span>
                <span class="mv-label-check" style="color:var(--accent)">
                  ${currentLabels.includes(l.label_name) ? "✓" : ""}
                </span>
              </div>
            `).join("");
        }
        this._pendingLabels = [...currentLabels];
        this.openModal("mv-label-modal");
    },

    _toggleLabelCheck(labelName, el) {
        const check = el.querySelector(".mv-label-check");
        const idx   = this._pendingLabels.indexOf(labelName);
        if (idx > -1) {
            this._pendingLabels.splice(idx, 1);
            check.textContent = "";
        } else {
            this._pendingLabels.push(labelName);
            check.textContent = "✓";
        }
    },

    applyLabels() {
        if (this.state.activeEmailName) {
            this.updateLabels(this.state.activeEmailName, this._pendingLabels);
        }
    },

    // ── Context Menu ───────────────────────────────────────

    showContextMenu(e, name) {
        e.preventDefault();
        this._ctxEmailName = name;
        const menu = document.getElementById("mv-context-menu");
        if (!menu) return;
        menu.classList.add("visible");
        menu.style.left = Math.min(e.clientX, window.innerWidth  - 210) + "px";
        menu.style.top  = Math.min(e.clientY, window.innerHeight - 250) + "px";
    },

    handleCtxAction(action) {
        const menu = document.getElementById("mv-context-menu");
        if (menu) menu.classList.remove("visible");
        const name = this._ctxEmailName;
        if (!name) return;

        if (action === "reply")   { this.selectEmail(name).then(() => this.focusReply()); }
        if (action === "forward") { this.selectEmail(name).then(() => this.focusReply()); }
        if (action === "read")    { this.markRead([name], 1); }
        if (action === "unread")  { this.markRead([name], 0); }
        if (action === "star")    { this.toggleStar(name, null); }
        if (action === "move")    { this.state.activeEmailName = name; this.openMoveModal(); }
        if (action === "label")   { this.state.activeEmailName = name; this.openLabelModal(); }
        if (action === "delete")  { this.deleteEmail(name); }
        if (action === "archive") { this.moveToFolder([name], "archive"); }
    },

    // ── Toast ──────────────────────────────────────────────

    toast(title, icon = "📬", body = null, hasUndo = false) {
        const container = document.getElementById("mv-toast-container");
        if (!container) return;
        const id = "mv-toast-" + Date.now();
        const el = document.createElement("div");
        el.className = "mv-toast";
        el.id = id;
        el.innerHTML = `
          <div class="mv-toast-icon">${icon}</div>
          <div class="mv-toast-content">
            <div class="mv-toast-title">${frappe.utils.escape_html(title)}</div>
            ${body ? `<div class="mv-toast-body">${frappe.utils.escape_html(body)}</div>` : ""}
            ${hasUndo ? `<div style="margin-top:4px">
              <button onclick="MailVault.undoLast('${id}')"
                      style="font-size:10px;padding:2px 8px;border-radius:5px;
                             border:1px solid var(--border-mid);background:transparent;
                             color:var(--accent);cursor:pointer;">
                ↩ Undo
              </button></div>` : ""}
            <div class="mv-toast-progress"></div>
          </div>
          <span onclick="MailVault.removeToast('${id}')"
                style="font-size:16px;color:var(--text-muted);cursor:pointer;flex-shrink:0;line-height:1">×</span>
        `;
        container.appendChild(el);
        setTimeout(() => this.removeToast(id), 4500);
    },

    removeToast(id) {
        const el = document.getElementById(id);
        if (el) {
            el.style.animation = "mv-toast-out 0.3s ease forwards";
            setTimeout(() => el.remove(), 300);
        }
    },

    undoLast(toastId) {
        this.removeToast(toastId);
        this.toast("Action undone", "↩");
    },

    // ── Helpers ────────────────────────────────────────────

    setBtn(id, text, disabled) {
        const el = document.getElementById(id);
        if (el) { el.textContent = text; el.disabled = disabled; }
    },

    showSkeleton() {
        const rows = document.getElementById("mv-email-rows");
        if (rows) rows.innerHTML = [1,2,3,4,5].map(() => `
          <div class="mv-skeleton-row">
            <div class="mv-skeleton-line" style="width:40%;"></div>
            <div class="mv-skeleton-line" style="width:70%;margin-top:6px;"></div>
            <div class="mv-skeleton-line" style="width:90%;margin-top:4px;height:8px;"></div>
          </div>
        `).join("");
    },

    showListSkeleton() {
        const rows = document.getElementById("mv-email-rows");
        if (rows) rows.innerHTML = [1,2,3,4,5].map(() => `
          <div class="mv-skeleton-row">
            <div class="mv-skeleton-line" style="width:35%;"></div>
            <div class="mv-skeleton-line" style="width:65%;"></div>
            <div class="mv-skeleton-line" style="width:85%;height:7px;"></div>
          </div>
        `).join("");
    },

    showListError() {
        const rows = document.getElementById("mv-email-rows");
        if (rows) rows.innerHTML = `
          <div class="mv-empty-state">
            <div class="mv-empty-icon">⚠️</div>
            <div class="mv-empty-title">Could not load emails</div>
            <div class="mv-empty-sub">Check your email account configuration in ERPNext settings</div>
          </div>`;
    },

    showDetailEmpty() {
        this.state.activeEmailName = null;
        const scroll = document.getElementById("mv-detail-scroll");
        if (scroll) scroll.innerHTML = `
          <div class="mv-empty-state">
            <div class="mv-empty-icon">📬</div>
            <div class="mv-empty-title">Select a conversation</div>
            <div class="mv-empty-sub">Choose an email from the list to read it here</div>
          </div>`;
        const reply = document.getElementById("mv-reply-container");
        if (reply) reply.style.display = "none";
        const tags = document.getElementById("mv-detail-tags");
        if (tags) tags.innerHTML = "";
        const actions = document.getElementById("mv-detail-actions");
        if (actions) actions.innerHTML = "";
    },

    showDetailLoading() {
        const scroll = document.getElementById("mv-detail-scroll");
        if (scroll) scroll.innerHTML = `
          <div class="mv-empty-state">
            <div class="mv-empty-icon mv-spin-icon">↻</div>
            <div class="mv-empty-title">Loading…</div>
          </div>`;
    },

    showDetailError() {
        const scroll = document.getElementById("mv-detail-scroll");
        if (scroll) scroll.innerHTML = `
          <div class="mv-empty-state">
            <div class="mv-empty-icon">⚠️</div>
            <div class="mv-empty-title">Could not load this email</div>
          </div>`;
    },

    _labelColor(labelName) {
        const l = this.state.labels.find(x => x.label_name === labelName);
        return l ? l.color : "#8a95a8";
    },

    _avatarColor(email) {
        const PALETTE = [
            "#4f9eff","#7c6dfa","#26d7a0","#f59e0b",
            "#f26d6d","#c084fc","#e879f9","#059669",
            "#0891b2","#e11d48","#d97706","#84cc16",
        ];
        if (!email) return PALETTE[0];
        const h = [...email].reduce((a, c) => a + c.charCodeAt(0), 0);
        return PALETTE[h % PALETTE.length];
    },

    // ── Render: Account List ────────────────────────────────

    renderAccounts() {
        const list = document.getElementById("mv-account-list");
        if (!list) return;
        list.innerHTML = this.state.accounts.map(a => {
            const initials = a.email_account_name
                ? a.email_account_name.split(" ").map(w => w[0]).join("").slice(0,2).toUpperCase()
                : (a.email_id || "").slice(0,2).toUpperCase();
            const color  = this._avatarColor(a.email_id);
            const unread = a.unread_count || 0;
            const active = this.state.activeAccount === a.name;
            return `
              <div class="mv-account-item ${active ? "active" : ""}"
                   onclick="MailVault.selectAccount('${a.name}')">
                <div class="mv-acct-avatar" style="background:${color}">${initials}</div>
                <div class="mv-acct-info">
                  <div class="mv-acct-name">${frappe.utils.escape_html(a.email_account_name || a.email_id)}</div>
                  <div class="mv-acct-addr">${frappe.utils.escape_html(a.email_id)}</div>
                </div>
                <div class="mv-acct-badge ${unread > 0 ? "has-unread" : ""}">${unread > 0 ? unread : "0"}</div>
              </div>`;
        }).join("");
    },

    // ── Render: Folder Nav ─────────────────────────────────

    renderFolderNav() {
        const nav = document.getElementById("mv-folder-nav");
        if (!nav) return;
        const FOLDERS = [
            { id:"inbox",   label:"Inbox",   icon:"📥", countKey:"inbox",   type:"unread" },
            { id:"starred", label:"Starred", icon:"⭐", countKey:"starred", type:"muted"  },
            { id:"sent",    label:"Sent",    icon:"📤", countKey:"sent",    type:"muted"  },
            { id:"drafts",  label:"Drafts",  icon:"📝", countKey:"drafts",  type:"warn"   },
            { id:"spam",    label:"Spam",    icon:"🚫", countKey:"spam",    type:"muted"  },
            { id:"archive", label:"Archive", icon:"🗂", countKey:"archive", type:"muted"  },
            { id:"trash",   label:"Trash",   icon:"🗑", countKey:"trash",   type:"muted"  },
        ];
        const fc = this.state.folderCounts;
        nav.innerHTML = FOLDERS.map(f => {
            const count = fc[f.countKey] || 0;
            const badgeStyle = f.type === "warn"
                ? "background:var(--accent-warn);color:#fff;"
                : f.type === "unread"
                    ? "background:var(--badge-unread);color:#fff;"
                    : "";
            const countHTML = count > 0
                ? `<span class="mv-nav-count" id="mv-badge-${f.id}" style="${badgeStyle}">${count}</span>`
                : "";
            return `
              <div class="mv-nav-item ${this.state.activeFolder === f.id ? "active" : ""}"
                   onclick="MailVault.selectFolder('${f.id}')">
                <span class="mv-nav-icon">${f.icon}</span>
                <span class="mv-nav-label">${f.label}</span>
                ${countHTML}
              </div>`;
        }).join("");
    },

    // ── Render: Label Nav ──────────────────────────────────

    renderLabelNav() {
        const nav = document.getElementById("mv-label-nav");
        if (!nav) return;
        nav.innerHTML = this.state.labels.map(l => `
          <div class="mv-nav-item" onclick="MailVault.filterByLabel('${l.label_name}')">
            <span class="mv-label-dot" style="background:${l.color};width:8px;height:8px;border-radius:50%;flex-shrink:0"></span>
            <span class="mv-nav-label">${frappe.utils.escape_html(l.label_name)}</span>
          </div>
        `).join("");
    },

    // ── Render: Theme Switcher ─────────────────────────────

    renderThemeSwitcher() {
        const el = document.getElementById("mv-theme-switcher");
        if (!el) return;
        const themes = [
            { id:"navy",   label:"Deep Navy"        },
            { id:"galaxy", label:"Midnight Galaxy"  },
            { id:"teal",   label:"Forest Teal"      },
            { id:"rose",   label:"Rose Gold"        },
            { id:"arctic", label:"Arctic Blue"      },
        ];
        el.innerHTML = themes.map(t => `
          <div class="mv-theme-dot ${this.state.theme === t.id ? "active" : ""}"
               data-t="${t.id}" title="${t.label}"
               onclick="MailVault.applyTheme('${t.id}')"></div>
        `).join("");
    },

    // ── Render: Email List ─────────────────────────────────

    renderEmailList(animate = false) {
        const container = document.getElementById("mv-email-rows");
        if (!container) return;

        const emails = this.state.emails;

        if (!emails.length) {
            container.innerHTML = `
              <div class="mv-empty-state">
                <div class="mv-empty-icon">🔍</div>
                <div class="mv-empty-title">No messages found</div>
                <div class="mv-empty-sub">Try a different folder, account, or search term</div>
              </div>`;
            return;
        }

        container.innerHTML = emails.map((e, i) => {
            const isSelected = this.state.selectedNames.has(e.name);
            const animClass  = (animate && i === 0) ? "mv-new-arrival" : "";
            const labels     = e.labels || [];
            return `
              <div class="mv-email-row ${e.read_by_current_user ? "" : "unread"}
                          ${e.name === this.state.activeEmailName ? "selected" : ""}
                          ${animClass}"
                   id="mv-row-${e.name}"
                   onclick="MailVault.selectEmail('${e.name}')"
                   oncontextmenu="MailVault.showContextMenu(event,'${e.name}')">
                ${!e.read_by_current_user ? '<div class="mv-unread-dot"></div>' : ''}
                <input type="checkbox" class="mv-er-check" ${isSelected ? "checked" : ""}
                       onclick="event.stopPropagation();MailVault.toggleSelect('${e.name}',this.checked)">
                <div class="mv-er-avatar-col">
                  <div class="mv-er-avatar" style="background:${e.avatar_color || "#4f9eff"}">${e.avatar_initials || "??"}</div>
                </div>
                <div class="mv-er-content">
                  <div class="mv-er-top">
                    <span class="mv-er-sender">${frappe.utils.escape_html(e.sender_name || e.sender || "")}</span>
                    <span class="mv-er-time">${e.time_display || ""}</span>
                  </div>
                  <div class="mv-er-subject">${frappe.utils.escape_html(e.subject || "(No subject)")}</div>
                  <div class="mv-er-preview">${frappe.utils.escape_html(e.preview || "")}</div>
                  <div class="mv-er-bottom">
                    ${labels.map(l => `<span class="mv-er-tag" style="background:${this._labelColor(l)}22;color:${this._labelColor(l)}">${frappe.utils.escape_html(l)}</span>`).join("")}
                    ${e.has_attachment ? '<span class="mv-attach-icon">📎</span>' : ""}
                    ${(e.thread_count || 1) > 1 ? `<span class="mv-thread-count">${e.thread_count}</span>` : ""}
                  </div>
                </div>
                <button class="mv-star-btn ${e.mail_starred ? "starred" : ""}"
                        onclick="event.stopPropagation();MailVault.toggleStar('${e.name}',this)">
                  ${e.mail_starred ? "★" : "☆"}
                </button>
              </div>`;
        }).join("");

        const folder  = this.state.activeFolder.charAt(0).toUpperCase() + this.state.activeFolder.slice(1);
        const titleEl = document.getElementById("mv-list-title");
        if (titleEl) titleEl.textContent = `${folder} (${this.state.totalEmails})`;
    },

    // ── Render: Detail Thread ─────────────────────────────

    renderDetail(thread) {
        if (!thread.length) {
            this.showDetailEmpty();
            return;
        }

        const first = thread[0];
        const email = this.state.emails.find(e => e.name === this.state.activeEmailName);

        const tagsEl = document.getElementById("mv-detail-tags");
        if (tagsEl && email) {
            tagsEl.innerHTML = (email.labels || []).map(l =>
                `<span class="mv-er-tag" style="background:${this._labelColor(l)}22;color:${this._labelColor(l)}">${frappe.utils.escape_html(l)}</span>`
            ).join("") + (first.has_attachment ?
                '<span style="font-size:10px;color:var(--text-muted);margin-left:4px">📎 Attachment</span>' : "");
        }

        const actEl = document.getElementById("mv-detail-actions");
        if (actEl) {
            actEl.innerHTML = `
              <button class="mv-toolbar-btn" onclick="MailVault.openMoveModal()">📁 <span>Move</span></button>
              <button class="mv-toolbar-btn" onclick="MailVault.openLabelModal()">🏷 <span>Label</span></button>
              <button class="mv-toolbar-btn" onclick="MailVault.moveToFolder(['${this.state.activeEmailName}'],'archive')">🗂 <span>Archive</span></button>
              <button class="mv-toolbar-btn" onclick="MailVault.deleteEmail('${this.state.activeEmailName}')">🗑</button>
              <button class="mv-toolbar-btn mv-toolbar-primary" onclick="MailVault.focusReply()">↩ <span>Reply</span></button>
            `;
        }

        const bc = document.getElementById("mv-breadcrumb-name");
        if (bc) bc.textContent = first.sender_name || first.sender_email || "Thread";

        const chip = document.getElementById("mv-reply-to-chip");
        if (chip) chip.textContent = first.sender || first.sender_email || "";

        const scroll = document.getElementById("mv-detail-scroll");
        if (!scroll) return;

        scroll.innerHTML = `
          <div>
            <div class="mv-subject-header">
              <div class="mv-subject-title">${frappe.utils.escape_html(first.subject || "(No subject)")}</div>
              <div class="mv-subject-meta">
                <span class="mv-meta-pill">📅 ${first.time_display || ""}</span>
                <span class="mv-meta-pill">💬 ${thread.length} message${thread.length !== 1 ? "s" : ""}</span>
                ${first.has_attachment ? '<span class="mv-meta-pill">📎 Attachment</span>' : ""}
              </div>
            </div>
            <div class="mv-email-thread">
              ${thread.map((msg, i) => `
                <div class="mv-thread-msg" style="animation:mv-fade-in 0.3s ease ${i * 0.08}s both">
                  <div class="mv-thread-msg-header" onclick="MailVault._toggleMsgBody(${i})">
                    <div class="mv-tm-avatar" style="background:${msg.avatar_color || "#4f9eff"}">${msg.avatar_initials || "??"}</div>
                    <div class="mv-tm-info">
                      <div class="mv-tm-name">${frappe.utils.escape_html(msg.sender_name || msg.sender_full_name || "")}</div>
                      <div class="mv-tm-email">${frappe.utils.escape_html(msg.sender_email || msg.sender || "")}</div>
                    </div>
                    <div class="mv-tm-time">${msg.time_display || ""}</div>
                  </div>
                  <div class="mv-thread-msg-body" id="mv-msg-body-${i}">
                    ${msg.content || msg.text_content || "(empty)"}
                  </div>
                  <div class="mv-thread-msg-actions">
                    <button class="mv-thread-action-btn" onclick="MailVault.focusReply()">↩ Reply</button>
                    <button class="mv-thread-action-btn" onclick="MailVault.setReplyMode('forward', document.querySelector('[data-mode=forward]'))">↪ Forward</button>
                    ${msg.attachments && msg.attachments.length ? `
                      ${msg.attachments.map(att => `
                        <button class="mv-thread-action-btn" onclick="window.open('${att.file_url}')">
                          📎 ${frappe.utils.escape_html(att.file_name)}
                        </button>`).join("")}` : ""}
                  </div>
                </div>
              `).join("")}
            </div>
          </div>
        `;

        thread.forEach((_, i) => {
            if (i > 0 && i < thread.length - 1) {
                const body = document.getElementById(`mv-msg-body-${i}`);
                if (body) body.style.display = "none";
            }
        });

        scroll.scrollTop = 0;

        const reply = document.getElementById("mv-reply-container");
        if (reply) reply.style.display = "block";
    },

    _toggleMsgBody(i) {
        const body = document.getElementById(`mv-msg-body-${i}`);
        if (body) body.style.display = body.style.display === "none" ? "block" : "none";
    },

    filterByLabel(labelName) {
        this.state.searchQuery = "";
        const searchEl = document.getElementById("mv-search");
        if (searchEl) searchEl.value = "";
        this.state.activeFolder = "inbox";
        this.state.currentPage  = 0;
        this.renderFolderNav();
        frappe.call({
            method: "ecclesia.api.mail_hub.search_emails",
            args: { query: "", label: labelName },
            callback: (r) => {
                if (r.message) {
                    this.state.emails      = r.message.emails || [];
                    this.state.totalEmails = r.message.total  || 0;
                    this.renderEmailList();
                    const titleEl = document.getElementById("mv-list-title");
                    if (titleEl) titleEl.textContent = `${labelName} (${this.state.totalEmails})`;
                }
            }
        });
    },

    // ── HTML Template ──────────────────────────────────────

    getHTML() {
        const accountOptions = `<option value="">Select account…</option>`;
        return `
<div id="mv-toast-container" style="position:fixed;top:16px;right:16px;display:flex;flex-direction:column;gap:8px;z-index:9999;pointer-events:none;"></div>

<div id="mv-context-menu">
  <div class="mv-ctx-item" onclick="MailVault.handleCtxAction('reply')">↩ Reply</div>
  <div class="mv-ctx-item" onclick="MailVault.handleCtxAction('forward')">↪ Forward</div>
  <div class="mv-ctx-divider"></div>
  <div class="mv-ctx-item" onclick="MailVault.handleCtxAction('read')">◎ Mark as read</div>
  <div class="mv-ctx-item" onclick="MailVault.handleCtxAction('unread')">● Mark as unread</div>
  <div class="mv-ctx-item" onclick="MailVault.handleCtxAction('star')">★ Star / Unstar</div>
  <div class="mv-ctx-item" onclick="MailVault.handleCtxAction('move')">📁 Move to folder</div>
  <div class="mv-ctx-item" onclick="MailVault.handleCtxAction('label')">🏷 Add label</div>
  <div class="mv-ctx-item" onclick="MailVault.handleCtxAction('archive')">🗂 Archive</div>
  <div class="mv-ctx-divider"></div>
  <div class="mv-ctx-item mv-ctx-danger" onclick="MailVault.handleCtxAction('delete')">🗑 Delete</div>
</div>

<!-- COMPOSE MODAL -->
<div class="mv-modal-overlay" id="mv-compose-modal">
  <div class="mv-modal">
    <div class="mv-modal-header">
      <span class="mv-modal-title">✏ New Message</span>
      <button class="mv-modal-close" onclick="MailVault.closeModal('mv-compose-modal')">×</button>
    </div>
    <div class="mv-modal-body">
      <div class="mv-field-row">
        <div class="mv-field-label">From</div>
        <select class="mv-field-input" id="mv-compose-from">${accountOptions}</select>
      </div>
      <div class="mv-field-row">
        <div class="mv-field-label">To</div>
        <input class="mv-field-input" id="mv-compose-to" placeholder="recipient@example.com" type="email">
      </div>
      <div class="mv-field-row">
        <div class="mv-field-label">CC</div>
        <input class="mv-field-input" id="mv-compose-cc" placeholder="Optional…" type="email">
      </div>
      <div class="mv-field-row">
        <div class="mv-field-label">BCC</div>
        <input class="mv-field-input" id="mv-compose-bcc" placeholder="Optional…" type="email">
      </div>
      <div class="mv-field-row">
        <div class="mv-field-label">Subject</div>
        <input class="mv-field-input" id="mv-compose-subject" placeholder="Email subject">
      </div>
      <div class="mv-field-row">
        <div class="mv-field-label">Message</div>
        <textarea class="mv-field-input" id="mv-compose-body" placeholder="Write your message…" style="min-height:120px;resize:vertical"></textarea>
      </div>
      <div style="display:flex;gap:6px;margin-top:4px;flex-wrap:wrap;">
        <button class="mv-btn-secondary">📎 Attach</button>
        <button class="mv-btn-secondary">⏰ Schedule</button>
        <button class="mv-btn-secondary">🔒 Encrypt</button>
      </div>
    </div>
    <div class="mv-modal-footer">
      <button class="mv-btn-secondary" onclick="MailVault.closeModal('mv-compose-modal')">Cancel</button>
      <button class="mv-btn-secondary" onclick="MailVault.saveDraft()">Save Draft</button>
      <button class="mv-btn-primary" id="mv-send-btn" onclick="MailVault.submitCompose()">Send Message →</button>
    </div>
  </div>
</div>

<!-- MOVE MODAL -->
<div class="mv-modal-overlay" id="mv-move-modal">
  <div class="mv-modal" style="max-width:340px">
    <div class="mv-modal-header">
      <span class="mv-modal-title">📁 Move to Folder</span>
      <button class="mv-modal-close" onclick="MailVault.closeModal('mv-move-modal')">×</button>
    </div>
    <div class="mv-modal-body">
      <div class="mv-folder-list" id="mv-folder-list"></div>
    </div>
    <div class="mv-modal-footer">
      <button class="mv-btn-secondary" onclick="MailVault.closeModal('mv-move-modal')">Cancel</button>
      <button class="mv-btn-primary" onclick="MailVault.confirmMove()">Move →</button>
    </div>
  </div>
</div>

<!-- LABEL MODAL -->
<div class="mv-modal-overlay" id="mv-label-modal">
  <div class="mv-modal" style="max-width:340px">
    <div class="mv-modal-header">
      <span class="mv-modal-title">🏷 Labels</span>
      <button class="mv-modal-close" onclick="MailVault.closeModal('mv-label-modal')">×</button>
    </div>
    <div class="mv-modal-body" id="mv-label-list-body"></div>
    <div class="mv-modal-footer">
      <button class="mv-btn-secondary" onclick="MailVault.closeModal('mv-label-modal')">Cancel</button>
      <button class="mv-btn-primary" onclick="MailVault.applyLabels()">Apply Labels</button>
    </div>
  </div>
</div>

<!-- MAIN APP -->
<div id="mv-app">
  <!-- SIDEBAR -->
  <div id="mv-sidebar">
    <button class="mv-sidebar-toggle" id="mv-sidebar-toggle" onclick="MailVault.toggleSidebar()">◀</button>
    <div class="mv-sidebar-top">
      <div class="mv-brand">
        <div class="mv-brand-icon">📬</div>
        <div class="mv-brand-text">
          <div class="mv-brand-name">MailVault</div>
          <div class="mv-brand-sub">Ecclesia · Comm Hub</div>
        </div>
      </div>
      <button class="mv-compose-btn" onclick="MailVault.openModal('mv-compose-modal')">
        <span>✏</span><span>Compose</span>
      </button>
    </div>
    <div class="mv-sidebar-scroll">
      <div class="mv-section-label">Accounts</div>
      <div id="mv-account-list"></div>
      <div class="mv-section-label">Folders</div>
      <div id="mv-folder-nav"></div>
      <div class="mv-section-label">Labels</div>
      <div id="mv-label-nav"></div>
    </div>
  </div>

  <!-- EMAIL LIST -->
  <div id="mv-email-list">
    <div class="mv-list-header">
      <div class="mv-list-title-row">
        <span class="mv-list-title" id="mv-list-title">Inbox</span>
        <div class="mv-list-actions">
          <button class="mv-icon-btn" title="Refresh" onclick="MailVault.loadNewEmails()">↻</button>
          <button class="mv-icon-btn" title="Select all" onclick="MailVault.selectAll()">☐</button>
          <button class="mv-icon-btn" title="Sync accounts" onclick="MailVault.syncAccounts()">⟳</button>
        </div>
      </div>
      <div class="mv-search-box">
        <span class="mv-search-icon">🔍</span>
        <input class="mv-search-input" id="mv-search" placeholder="Search mail…" oninput="MailVault.onSearch(this.value)">
      </div>
      <div class="mv-filter-tabs">
        <div class="mv-ftab active" onclick="MailVault.setFilter('all',this)">All</div>
        <div class="mv-ftab" onclick="MailVault.setFilter('unread',this)">Unread</div>
        <div class="mv-ftab" onclick="MailVault.setFilter('starred',this)">Starred</div>
        <div class="mv-ftab" onclick="MailVault.setFilter('attachments',this)">Attachments</div>
      </div>
    </div>
    <div class="mv-bulk-bar" id="mv-bulk-bar">
      <span id="mv-bulk-count">0 selected</span>
      <button class="mv-bulk-btn" onclick="MailVault.bulkMarkRead()">Mark read</button>
      <button class="mv-bulk-btn" onclick="MailVault.bulkMove()">Move</button>
      <button class="mv-bulk-btn mv-bulk-danger" onclick="MailVault.bulkDelete()">Delete</button>
      <button class="mv-bulk-btn" style="margin-left:auto" onclick="MailVault.clearSelection()">✕</button>
    </div>
    <div class="mv-refresh-bar" id="mv-refresh-bar" onclick="MailVault.loadNewEmails()">
      <span style="display:inline-block;animation:mv-spin 1s linear infinite">↻</span>
      <span id="mv-refresh-text">New messages — click to load</span>
    </div>
    <div class="mv-email-rows" id="mv-email-rows"></div>
  </div>

  <!-- DETAIL PANEL -->
  <div id="mv-email-detail">
    <div id="mv-detail-header-bar">
      <div class="mv-detail-breadcrumb">
        Inbox / <span id="mv-breadcrumb-name">—</span>
      </div>
      <div class="mv-rt-status">
        <div class="mv-rt-dot mv-rt-live" id="mv-rt-dot"></div>
        <span id="mv-rt-label">Live</span>
      </div>
      <div style="margin-left:12px;display:flex;align-items:center;gap:6px;">
        <span class="mv-theme-label">Theme</span>
        <div class="mv-theme-switcher" id="mv-theme-switcher"></div>
      </div>
    </div>
    <div class="mv-detail-topbar" id="mv-detail-topbar">
      <div class="mv-detail-topbar-left">
        <div id="mv-detail-tags"></div>
      </div>
      <div class="mv-detail-topbar-right" id="mv-detail-actions"></div>
    </div>
    <div class="mv-detail-scroll" id="mv-detail-scroll">
      <div class="mv-empty-state">
        <div class="mv-empty-icon">📬</div>
        <div class="mv-empty-title">Select a conversation</div>
        <div class="mv-empty-sub">Choose an email from the list to read it here</div>
      </div>
    </div>
    <div class="mv-reply-container" id="mv-reply-container" style="display:none">
      <div class="mv-reply-header">
        <span class="mv-reply-label">Reply</span>
        <div class="mv-reply-mode-tabs">
          <div class="mv-rmode-tab active" data-mode="reply" onclick="MailVault.setReplyMode('reply',this)">Reply</div>
          <div class="mv-rmode-tab" data-mode="reply-all" onclick="MailVault.setReplyMode('reply-all',this)">Reply All</div>
          <div class="mv-rmode-tab" data-mode="forward" onclick="MailVault.setReplyMode('forward',this)">Forward</div>
        </div>
      </div>
      <div class="mv-reply-to-row">
        <span class="mv-reply-to-label">To:</span>
        <span class="mv-reply-to-chip" id="mv-reply-to-chip">—</span>
      </div>
      <textarea class="mv-reply-textarea" id="mv-reply-textarea" placeholder="Write your reply…"></textarea>
      <div class="mv-reply-footer">
        <div class="mv-reply-tools">
          <button class="mv-reply-tool-btn" title="Attach file">📎</button>
          <button class="mv-reply-tool-btn" title="Emoji">😊</button>
          <button class="mv-reply-tool-btn" title="Format">Aa</button>
          <button class="mv-reply-tool-btn" title="Schedule send">⏰</button>
          <button class="mv-reply-tool-btn" title="Templates">📋</button>
        </div>
        <button class="mv-reply-send-btn" id="mv-reply-send-btn"
                onclick="MailVault.sendReply()">Send →</button>
      </div>
    </div>
  </div>
</div>
        `;
    },

    // ── CSS Injection ──────────────────────────────────────

    injectCSS() {
        if (document.getElementById("mv-styles")) return;
        const link = document.createElement("link");
        link.id   = "mv-styles";
        link.rel  = "stylesheet";
        link.href = "/assets/ecclesia/css/mail_hub.css";
        document.head.appendChild(link);

        const font = document.createElement("link");
        font.rel  = "stylesheet";
        font.href = "https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=Crimson+Pro:wght@300;400;600&family=JetBrains+Mono:wght@400;500&display=swap";
        document.head.appendChild(font);
    },

    // ── Sync Accounts ──────────────────────────────────────

    async syncAccounts() {
        try {
            const r = await this.api.call("trigger_email_sync");
            this.toast(`Syncing ${r.syncing} account${r.syncing !== 1 ? "s" : ""}…`, "⟳");
            this.setRTStatus("syncing");
            setTimeout(() => this.pollForNewEmails(), 10000);
        } catch (e) {
            this.toast("Sync failed", "⚠️");
        }
    },
};

// Close context menu on click outside
document.addEventListener("click", () => {
    const menu = document.getElementById("mv-context-menu");
    if (menu) menu.classList.remove("visible");
});