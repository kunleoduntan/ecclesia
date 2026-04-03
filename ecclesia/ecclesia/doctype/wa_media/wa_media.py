# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document

class WAMedia(Document):
    """
    Manages media files (images, documents, audio, video) exchanged
    via WhatsApp. Stores the media ID from WhatsApp API and local file path.
    """

    SUPPORTED_TYPES = {
        "image": ["image/jpeg", "image/png", "image/webp"],
        "document": ["application/pdf", "application/msword", "text/plain"],
        "audio": ["audio/mpeg", "audio/ogg", "audio/wav"],
        "video": ["video/mp4", "video/3gpp"],
        "sticker": ["image/webp"],
    }

    def validate(self):
        self.validate_media_type()
        self.validate_file_size()

    def validate_media_type(self):
        if self.media_type and self.mime_type:
            allowed = self.SUPPORTED_TYPES.get(self.media_type, [])
            if allowed and self.mime_type not in allowed:
                frappe.throw(
                    frappe._("MIME type '{0}' is not valid for media type '{1}'").format(
                        self.mime_type, self.media_type
                    )
                )

    def validate_file_size(self):
        """WhatsApp enforces file size limits per media type (in MB)."""
        limits = {"image": 5, "document": 100, "audio": 16, "video": 16, "sticker": 0.1}
        if self.file_size and self.media_type:
            limit_mb = limits.get(self.media_type, 100)
            file_size_mb = self.file_size / (1024 * 1024)
            if file_size_mb > limit_mb:
                frappe.throw(
                    frappe._("File size {0:.2f} MB exceeds the {1} MB limit for {2}").format(
                        file_size_mb, limit_mb, self.media_type
                    )
                )

    def get_download_url(self) -> str:
        """Return the local file URL for this media."""
        if self.file_url:
            return frappe.utils.get_url(self.file_url)
        return ""
