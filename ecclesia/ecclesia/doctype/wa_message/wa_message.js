// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

// ecclesia/doctype/wa_message/wa_message.js

frappe.ui.form.on("WA Message", {

    refresh(frm) {
        _set_status_indicator(frm);
        _render_media_preview(frm);

        // Quick open parent conversation
        if (frm.doc.conversation) {
            frm.add_custom_button(__("Open Conversation"), () => {
                frappe.set_route("Form", "WA Conversation", frm.doc.conversation);
            });
        }
    }
});


function _set_status_indicator(frm) {
    const statusMap = {
        queued:    { color: "grey",   icon: "⏳" },
        sent:      { color: "blue",   icon: "✓" },
        delivered: { color: "blue",   icon: "✓✓" },
        read:      { color: "green",  icon: "✓✓" },
        failed:    { color: "red",    icon: "✕" }
    };
    const s = statusMap[frm.doc.delivery_status] || { color: "grey", icon: "" };

    frm.set_intro(
        `${s.icon} ${frm.doc.delivery_status || "Unknown"} · ${frm.doc.direction} · ${frm.doc.message_type}`,
        s.color
    );

    if (frm.doc.delivery_status === "failed" && frm.doc.error_message) {
        frm.set_intro(
            `❌ Error ${frm.doc.error_code || ""}: ${frm.doc.error_message}`,
            "red"
        );
    }
}


function _render_media_preview(frm) {
    const type = frm.doc.message_type;

    if (type === "image" && frm.doc.media_url) {
        frm.set_df_property("media_url", "description",
            `<img src="${frm.doc.media_url}" style="max-width:320px;border-radius:8px;margin-top:6px;display:block;">`
        );
    } else if (type === "audio" && frm.doc.media_url) {
        frm.set_df_property("media_url", "description",
            `<audio controls src="${frm.doc.media_url}" style="margin-top:6px;width:100%;max-width:300px;"></audio>`
        );
    } else if (type === "video" && frm.doc.media_url) {
        frm.set_df_property("media_url", "description",
            `<video controls src="${frm.doc.media_url}" style="max-width:320px;border-radius:8px;margin-top:6px;display:block;"></video>`
        );
    } else if (type === "document" && frm.doc.media_url) {
        frm.set_df_property("media_url", "description",
            `<a href="${frm.doc.media_url}" target="_blank" class="btn btn-xs btn-default" style="margin-top:6px;">
                📎 Download ${frm.doc.media_filename || "File"}
            </a>`
        );
    } else if (type === "location" && frm.doc.location_latitude) {
        const lat = frm.doc.location_latitude;
        const lng = frm.doc.location_longitude;
        frm.set_df_property("location_name", "description",
            `<a href="https://www.google.com/maps?q=${lat},${lng}" target="_blank" class="btn btn-xs btn-default">
                📍 View on Google Maps
            </a>`
        );
    }
}
