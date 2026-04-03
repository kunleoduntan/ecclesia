// Copyright (c) 2026, Kunle Oduntan and contributors
// For license information, please see license.txt

// ecclesia/doctype/wa_media/wa_media.js

frappe.ui.form.on("WA Media", {

    refresh(frm) {
        _render_media_preview(frm);

        if (!frm.is_new() && !frm.doc.uploaded_to_wa) {
            frm.add_custom_button(__("☁ Upload to WhatsApp"), () => {
                frappe.show_alert({ message: __("Uploading to WhatsApp..."), indicator: "blue" });
                frappe.call({
                    method: "ecclesia.api.whatsapp.upload_media_doc",
                    args:   { media_name: frm.doc.name },
                    callback(r) {
                        if (r.message && r.message.media_id) {
                            frappe.show_alert({ message: __("Uploaded! Media ID saved."), indicator: "green" });
                            frm.reload_doc();
                        } else {
                            frappe.msgprint({ title: __("Upload Failed"), message: r.message?.error || "Unknown error", indicator: "red" });
                        }
                    }
                });
            });
        }

        if (frm.doc.uploaded_to_wa && frm.doc.wa_media_id) {
            frm.set_intro(`✅ Uploaded to WhatsApp · Media ID: <b>${frm.doc.wa_media_id}</b>`, "green");
        } else {
            frm.set_intro("⚠️ Not yet uploaded to WhatsApp", "orange");
        }
    },

    file(frm) {
        _render_media_preview(frm);
        // Auto-detect media type
        if (frm.doc.file) {
            const ext = frm.doc.file.split(".").pop().toLowerCase();
            const typeMap = {
                jpg: "image", jpeg: "image", png: "image", gif: "image", webp: "image",
                mp4: "video", mov: "video", avi: "video",
                mp3: "audio", ogg: "audio", m4a: "audio", aac: "audio",
                pdf: "document", doc: "document", docx: "document", xls: "document",
                xlsx: "document", ppt: "document", pptx: "document", txt: "document"
            };
            const type = typeMap[ext] || "document";
            frm.set_value("media_type", type);
        }
    }
});


function _render_media_preview(frm) {
    if (!frm.doc.file) return;
    const type = frm.doc.media_type;

    let html = "";
    if (type === "image") {
        html = `<img src="${frm.doc.file}" style="max-width:300px;border-radius:8px;margin-top:8px;display:block;">`;
    } else if (type === "audio") {
        html = `<audio controls src="${frm.doc.file}" style="margin-top:8px;width:100%;max-width:300px;"></audio>`;
    } else if (type === "video") {
        html = `<video controls src="${frm.doc.file}" style="max-width:300px;border-radius:8px;margin-top:8px;display:block;"></video>`;
    }

    if (html) {
        frm.set_df_property("file", "description", html);
        frm.refresh_field("file");
    }
}
