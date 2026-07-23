// ecclesia/doctype/job_board_platform/job_board_platform.js
frappe.ui.form.on("Job Board Platform", {

    refresh(frm) {
        frm.trigger("_status_badge");
        frm.trigger("_render_platform_card");
        frm.trigger("_add_buttons");
    },

    platform_name(frm) {
        frm.trigger("_set_platform_icon");
    },

    _status_badge(frm) {
        const colors = {
            Active:"green", Inactive:"grey",
            Testing:"orange", Connected:"green", Failed:"red"
        };
        const conn = frm.doc.connection_status || "Not Tested";
        frm.page.set_indicator(conn, colors[conn] || "grey");
    },

    _set_platform_icon(frm) {
        const icons = {
            linkedin:"🔷", twitter:"🐦", x:"✖️", facebook:"📘",
            instagram:"📸", whatsapp:"💬", telegram:"✈️",
            indeed:"🔍", glassdoor:"🚪", jobberman:"💼",
        };
        const name = (frm.doc.platform_name || "").toLowerCase();
        const icon = Object.entries(icons).find(([k]) => name.includes(k))?.[1] || "🌐";
        frm.set_df_property("platform_name", "description",
            `<span style="font-size:24px">${icon}</span>`);
    },

    _render_platform_card(frm) {
        if (!frm.doc.platform_name) return;
        const d = frm.doc;
        const connColor = d.connection_status === "Connected" ? "#059669"
            : d.connection_status === "Failed" ? "#DC2626" : "#D97706";

        const specs = [];
        if (d.character_limit) specs.push(`${d.character_limit} char limit`);
        if (d.supports_image)   specs.push("Images ✓");
        if (d.supports_hashtags)specs.push("Hashtags ✓");
        if (d.best_days)        specs.push(`Best days: ${d.best_days}`);
        if (d.best_time_utc)    specs.push(`Best time: ${d.best_time_utc} UTC`);

        const html = `
        <div style="background:var(--surface-1);border:1px solid var(--border);
                    border-radius:10px;padding:14px 16px;display:flex;
                    align-items:center;gap:14px">
          <div style="font-size:36px">
            ${_getPlatformIcon(d.platform_name)}
          </div>
          <div style="flex:1">
            <div style="font-size:14px;font-weight:600;color:var(--text-primary)">
              ${d.platform_name}
              <span style="font-size:11px;font-weight:400;color:var(--text-secondary);
                           margin-left:8px">${d.platform_type || ""}</span>
            </div>
            <div style="font-size:11px;color:var(--text-secondary);margin-top:3px">
              ${specs.join("  ·  ")}
            </div>
          </div>
          <div style="text-align:center">
            <div style="font-size:11px;font-weight:700;color:${connColor};
                        text-transform:uppercase;letter-spacing:.4px">
              ${d.connection_status || "Not Tested"}
            </div>
            ${d.total_posts ? `<div style="font-size:18px;font-weight:800;color:var(--text-primary)">${d.total_posts}</div>
            <div style="font-size:10px;color:var(--text-secondary)">posts</div>` : ""}
          </div>
        </div>`;

        frm.set_df_property("platform_name", "description", html);
        frm.refresh_field("platform_name");

        function _getPlatformIcon(name) {
            if (!name) return "🌐";
            const nl = name.toLowerCase();
            if (nl.includes("linkedin"))  return "🔷";
            if (nl.includes("twitter") || nl.includes("/x")) return "🐦";
            if (nl.includes("facebook"))  return "📘";
            if (nl.includes("instagram")) return "📸";
            if (nl.includes("whatsapp"))  return "💬";
            if (nl.includes("telegram"))  return "✈️";
            if (nl.includes("indeed"))    return "🔍";
            if (nl.includes("glassdoor")) return "🚪";
            if (nl.includes("jobberman")) return "💼";
            return "🌐";
        }
    },

    _add_buttons(frm) {
        if (frm.is_new()) return;

        frm.add_custom_button(__("Test Connection"), () => {
            frappe.show_progress(__("Testing"), 20, 100, __("Connecting to platform API..."));
            frappe.call({
                method: "ecclesia.api.job_post_api.test_platform_connection",
                args:   { platform_name: frm.doc.name },
                callback(r) {
                    frappe.hide_progress();
                    if (r.message?.success) {
                        frappe.show_alert({ message: __("✅ Connection successful!"),
                                           indicator: "green" });
                    } else {
                        frappe.show_alert({
                            message: __("❌ Connection failed: ") + (r.message?.error || "Unknown error"),
                            indicator: "red"
                        }, 8);
                    }
                    frm.reload_doc();
                }
            });
        }, __("Tools")).addClass("btn-primary");

        frm.add_custom_button(__("Message Template Guide"), () => {
            frappe.msgprint({
                title: __("Template Variables"),
                message: `
                <p>Use these Jinja2 variables in your Message Template:</p>
                <table class="table table-bordered table-sm">
                    <thead><tr><th>Variable</th><th>Description</th></tr></thead>
                    <tbody>
                        <tr><td><code>{{ job_title }}</code></td><td>Job title</td></tr>
                        <tr><td><code>{{ company }}</code></td><td>Company name</td></tr>
                        <tr><td><code>{{ location }}</code></td><td>Location display</td></tr>
                        <tr><td><code>{{ work_mode }}</code></td><td>On-site / Hybrid / Remote</td></tr>
                        <tr><td><code>{{ salary }}</code></td><td>Salary display string</td></tr>
                        <tr><td><code>{{ requirements }}</code></td><td>Key requirements bullets</td></tr>
                        <tr><td><code>{{ description }}</code></td><td>Plain text description</td></tr>
                        <tr><td><code>{{ apply_url }}</code></td><td>Application link</td></tr>
                        <tr><td><code>{{ priority }}</code></td><td>Urgent / High / Normal</td></tr>
                    </tbody>
                </table>
                <p><b>Example for LinkedIn:</b></p>
                <pre style="background:#f4f4f4;padding:8px;border-radius:4px">🚀 We're Hiring: {{ job_title }}
Company: {{ company }}
📍 {{ location }} | {{ work_mode }}
💰 {{ salary }}

{{ description[:500] }}

Requirements:
{{ requirements }}

👉 Apply here: {{ apply_url }}</pre>`,
                wide: true
            });
        }, __("Help"));
    },

    character_limit(frm) {
        const limit = frm.doc.character_limit || 0;
        if (limit > 0) {
            frm.set_df_property("character_limit", "description",
                `<small>Tip: Twitter=280 · LinkedIn=3,000 · Facebook=63,206 · Instagram=2,200 · WhatsApp=4,096</small>`);
        }
    }
});
