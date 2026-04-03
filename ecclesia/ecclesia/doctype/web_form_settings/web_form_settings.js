// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

// doctype/web_form_settings/web_form_settings.js

frappe.ui.form.on("Web Form Settings", {

  refresh(frm) {
    // ── Status indicator ─────────────────────────────────────
    frm.set_indicator_formatter("is_active",
      () => frm.doc.is_active ? "green" : "grey"
    );

    if (!frm.is_new()) {

      // ── Copy snippet button ──────────────────────────────
      frm.add_custom_button(__("Copy Embed Snippet"), () => {
        const erpnext_url = frappe.urllib.get_base_url();
        const snippet =
`<!-- Web Form: ${frm.doc.form_label} -->
<script>
  window.WF_KEY = "${frm.doc.form_key}";
  window.WF_HOST = "${erpnext_url}";
<\/script>
<script src="${erpnext_url}/files/contact-form.js" defer><\/script>
<div id="wf-contact-form"></div>`;

        frappe.utils.copy_to_clipboard(snippet);
        frappe.show_alert({ message: "Embed snippet copied to clipboard!", indicator: "green" }, 4);
      }, __("Tools"));

      // ── Preview API response button ──────────────────────
      frm.add_custom_button(__("Preview Config API"), () => {
        const url = `${frappe.urllib.get_base_url()}/api/method/ecclesia.api.contact_intake.get_form_config?key=${frm.doc.form_key}`;
        frappe.msgprint({
          title: "Config API URL",
          message: `<code style="word-break:break-all;font-size:12px">${url}</code>
            <br><br>
            <a href="${url}" target="_blank" class="btn btn-xs btn-default">Open in browser →</a>`,
          indicator: "blue",
        });
      }, __("Tools"));

      // ── Test submission button ───────────────────────────
      frm.add_custom_button(__("Send Test Submission"), () => {
        frappe.confirm(
          `Send a test Contact Us submission through the <b>${frm.doc.form_label}</b> form config?`,
          () => {
            frappe.call({
              method: "ecclesia.api.contact_intake.test_form_submission",
              args: { form_key: frm.doc.form_key },
              freeze: true,
              freeze_message: "Sending test submission…",
              callback(r) {
                if (r.message && r.message.success) {
                  frappe.msgprint({
                    title: "Test Submission Successful",
                    message: `
                      <b>Reference:</b> ${r.message.reference}<br>
                      <b>Assigned to:</b> ${r.message.assigned_to || "—"}<br>
                      <b>Priority:</b> ${r.message.priority || "—"}<br>
                      <b>AI Reasoning:</b> <em>${r.message.reasoning || "—"}</em>
                    `,
                    indicator: "green",
                  });
                } else {
                  frappe.msgprint({
                    title: "Test Failed",
                    message: r.message?.error || "Unknown error",
                    indicator: "red",
                  });
                }
              },
            });
          }
        );
      }, __("Tools"));
    }

    // ── Inline field visibility hints ────────────────────
    _update_field_hints(frm);
  },

  assignment_strategy(frm) {
    _update_field_hints(frm);
  },

  form_key(frm) {
    // Enforce slug format
    if (frm.doc.form_key) {
      const slug = frm.doc.form_key
        .toLowerCase()
        .replace(/\s+/g, "-")
        .replace(/[^a-z0-9\-]/g, "");
      if (slug !== frm.doc.form_key) {
        frm.set_value("form_key", slug);
        frappe.show_alert({ message: "Form key auto-formatted to slug.", indicator: "blue" }, 3);
      }
    }
  },

  brand_color(frm) {
    // Live preview swatch in the form
    const color = frm.doc.brand_color || "#c8972a";
    frm.set_df_property("brand_color", "description",
      `<div style="display:flex;align-items:center;gap:8px;margin-top:4px">
        <div style="width:20px;height:20px;border-radius:50%;background:${color};border:1px solid rgba(0,0,0,0.15)"></div>
        <span style="font-size:12px;color:#888">Progress pills, focus rings, and accent buttons will use this colour.</span>
      </div>`
    );
  },
});


function _update_field_hints(frm) {
  const strategy = frm.doc.assignment_strategy;
  const isAI = strategy === "AI + Load Balancing";

  frm.set_df_property("ai_provider", "hidden", !isAI ? 1 : 0);

  if (strategy === "Fixed Salesperson") {
    frm.set_df_property("target_salesperson_role", "label", "Fixed Salesperson (User)");
    frm.set_df_property("target_salesperson_role", "description",
      "This specific user will receive every submission from this form."
    );
  } else {
    frm.set_df_property("target_salesperson_role", "label", "Restrict Assignment to Role");
    frm.set_df_property("target_salesperson_role", "description",
      "Only users with this role will be considered for assignment. Leave blank to use all Sales Users."
    );
  }
}