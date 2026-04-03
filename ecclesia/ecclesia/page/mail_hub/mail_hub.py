"""
MailVault — Frappe Page Controller
ecclesia/page/mail_hub/mail_hub.py

All @frappe.whitelist() methods called by the frontend.
Wraps Frappe's native Communication, Email Account, and
Email Queue doctypes — no duplicate data storage.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime, get_datetime, cint, nowdate
from email.utils import parseaddr
import json
import re


# ─────────────────────────────────────────────
# PAGE BOOT — called once on page load
# ─────────────────────────────────────────────

@frappe.whitelist()
def get_boot_data():
    """
    Returns everything the frontend needs on first load:
    - linked email accounts for this user
    - folder counts
    - user labels (using Frappe's built-in tags)
    - user preferences (theme, layout)
    """
    user = frappe.session.user

    accounts = _get_user_email_accounts(user)
    folder_counts = _get_folder_counts(user, accounts)
    labels = _get_user_labels(user)
    prefs = _get_user_prefs(user)

    return {
        "user": frappe.get_value("User", user, ["full_name", "email", "user_image"], as_dict=True),
        "accounts": accounts,
        "folder_counts": folder_counts,
        "labels": labels,
        "prefs": prefs,
    }


# ─────────────────────────────────────────────
# EMAIL ACCOUNTS
# ─────────────────────────────────────────────

def _get_user_email_accounts(user):
    """
    Return Email Account records the current user can access.
    Shared accounts (enable_incoming=1) are visible to all.
    Personal accounts are scoped to the owner.
    """
    accounts = frappe.get_all(
        "Email Account",
        filters={
            "enable_incoming": 1,
            "awaiting_password": 0,
        },
        fields=[
            "name", "email_account_name", "email_id",
            "enable_incoming", "enable_outgoing",
            "append_to", "use_imap", "service",
        ],
        order_by="creation asc",
    )

    # Attach unread counts per account
    for acct in accounts:
        acct["unread_count"] = frappe.db.count(
            "Communication",
            filters={
                "sent_or_received": "Received",
                "email_account": acct["name"],
                "read_by_current_user": 0,
                "communication_medium": "Email",
                "status": ["not in", ["Spam", "Trash"]],
            },
        )

    return accounts


# ─────────────────────────────────────────────
# FOLDER COUNTS
# ─────────────────────────────────────────────

def _get_folder_counts(user, accounts):
    account_names = [a["name"] for a in accounts]

    def _count(filters):
        return frappe.db.count("Communication", filters=filters) if account_names else 0

    base = {
        "communication_medium": "Email",
        "email_account": ["in", account_names],
    }

    inbox_count = _count({**base, "sent_or_received": "Received",
                          "read_by_current_user": 0,
                          "status": ["not in", ["Spam", "Trash", "Archived"]]})

    starred_count = frappe.db.count(
        "Communication",
        filters={**base, "_liked_by": ["like", f"%{user}%"],
                 "status": ["not in", ["Trash"]]},
    ) if account_names else 0

    draft_count = frappe.db.count(
        "Communication",
        filters={**base, "sent_or_received": "Sent",
                 "status": "Draft"},
    ) if account_names else 0

    spam_count = _count({**base, "status": "Spam"})
    trash_count = _count({**base, "status": "Trash"})

    sent_count = frappe.db.count(
        "Communication",
        filters={**base, "sent_or_received": "Sent",
                 "status": ["not in", ["Draft", "Trash"]]},
    ) if account_names else 0

    # Archive count using custom field (will be 0 if field doesn't exist)
    archive_count = 0
    if frappe.db.has_column("Communication", "mail_folder"):
        archive_count = frappe.db.count(
            "Communication",
            filters={**base, "mail_folder": "Archive",
                     "status": ["not in", ["Trash"]]},
        ) if account_names else 0

    return {
        "inbox": inbox_count,
        "starred": starred_count,
        "sent": sent_count,
        "drafts": draft_count,
        "spam": spam_count,
        "trash": trash_count,
        "archive": archive_count,
    }


# ─────────────────────────────────────────────
# FETCH EMAILS (list view)
# ─────────────────────────────────────────────

@frappe.whitelist()
def get_emails(folder="inbox", account=None, label=None,
               search=None, filter_type="all",
               page=0, page_size=40):
    """
    Return paginated email list for the given folder.
    folder: inbox | sent | drafts | starred | spam | trash | archive
    filter_type: all | unread | starred | attachments
    """
    user = frappe.session.user
    page = cint(page)
    page_size = cint(page_size)

    accounts = _get_user_email_accounts(user)
    account_names = [a["name"] for a in accounts]

    if account:
        account_names = [account] if account in account_names else account_names

    if not account_names:
        return {"emails": [], "total": 0}

    filters = {
        "communication_medium": "Email",
        "email_account": ["in", account_names],
    }

    # Folder mapping
    if folder == "inbox":
        filters["sent_or_received"] = "Received"
        filters["status"] = ["not in", ["Spam", "Trash", "Archived"]]
        # exclude custom archived if field exists
        if frappe.db.has_column("Communication", "mail_folder"):
            filters["mail_folder"] = ["!=", "Archive"]
    elif folder == "sent":
        filters["sent_or_received"] = "Sent"
        filters["status"] = ["not in", ["Draft", "Trash"]]
    elif folder == "drafts":
        filters["sent_or_received"] = "Sent"
        filters["status"] = "Draft"
    elif folder == "starred":
        filters["_liked_by"] = ["like", f"%{user}%"]
        filters["status"] = ["not in", ["Trash"]]
    elif folder == "spam":
        filters["status"] = "Spam"
    elif folder == "trash":
        filters["status"] = "Trash"
    elif folder == "archive":
        if frappe.db.has_column("Communication", "mail_folder"):
            filters["mail_folder"] = "Archive"
            filters["status"] = ["not in", ["Trash"]]
        else:
            # If field doesn't exist, return empty
            return {"emails": [], "total": 0}

    # Filter type
    if filter_type == "unread":
        filters["read_by_current_user"] = 0
        filters["sent_or_received"] = "Received"
    elif filter_type == "starred":
        filters["_liked_by"] = ["like", f"%{user}%"]
    elif filter_type == "attachments":
        filters["has_attachment"] = 1

    # Label (using Frappe's tagging system)
    if label:
        # Find communications with this tag
        communications_with_tag = frappe.db.get_all(
            "Tag Link",
            filters={
                "tag": label,
                "document_type": "Communication"
            },
            pluck="document_name"
        )
        if communications_with_tag:
            filters["name"] = ["in", communications_with_tag]
        else:
            return {"emails": [], "total": 0}

    # Search
    or_filters = None
    if search and len(search) >= 2:
        or_filters = {
            "subject": ["like", f"%{search}%"],
            "sender": ["like", f"%{search}%"],
            "content": ["like", f"%{search}%"],
        }

    fields = [
        "name", "subject", "sender", "sender_full_name",
        "recipients", "sent_or_received", "status",
        "communication_date", "email_account",
        "read_by_current_user", "_liked_by",
        "has_attachment", "seen",
    ]

    # Include custom fields if they exist
    if frappe.db.has_column("Communication", "mail_folder"):
        fields.append("mail_folder")

    total = frappe.db.count("Communication", filters=filters)

    emails = frappe.get_all(
        "Communication",
        filters=filters,
        or_filters=or_filters or {},
        fields=fields,
        order_by="communication_date desc",
        limit_start=page * page_size,
        limit_page_length=page_size,
    )

    # Enrich each email
    for e in emails:
        e["sender_name"], e["sender_email"] = _parse_sender(e.get("sender", ""))
        e["preview"] = _get_preview(e["name"])
        e["labels"] = _get_document_tags(e["name"])
        e["mail_starred"] = 1 if e.get("_liked_by") and user in e["_liked_by"] else 0
        e["thread_count"] = frappe.db.count(
            "Communication",
            filters={"reference_doctype": "Communication", "reference_name": e["name"]}
        ) + 1
        e["time_display"] = _format_time(e.get("communication_date"))
        e["avatar_initials"] = _get_initials(e.get("sender_full_name") or e["sender_email"])
        e["avatar_color"] = _email_to_color(e["sender_email"])

    return {"emails": emails, "total": total, "page": page}


# ─────────────────────────────────────────────
# FETCH SINGLE EMAIL THREAD
# ─────────────────────────────────────────────

@frappe.whitelist()
def get_email_thread(communication_name):
    """
    Returns the full thread: the parent + all child communications.
    Also marks all as read.
    """
    parent = frappe.get_doc("Communication", communication_name)

    # Permission check
    _check_email_account_access(parent.email_account)

    # Build thread
    thread = [_serialize_communication(parent)]

    # Find replies (communications that reference this one)
    replies = frappe.get_all(
        "Communication",
        filters={
            "reference_doctype": "Communication",
            "reference_name": communication_name
        },
        fields=["name"],
        order_by="communication_date asc",
    )
    
    for r in replies:
        doc = frappe.get_doc("Communication", r["name"])
        thread.append(_serialize_communication(doc))

    # Mark parent as read
    if not parent.read_by_current_user:
        frappe.db.set_value(
            "Communication", communication_name,
            "read_by_current_user", 1, update_modified=False
        )

    return {"thread": thread, "total": len(thread)}


def _serialize_communication(doc):
    """Convert Communication document to serializable dict"""
    user = frappe.session.user
    return {
        "name": doc.name,
        "subject": doc.subject,
        "sender": doc.sender,
        "sender_full_name": doc.sender_full_name or "",
        "sender_name": _parse_sender(doc.sender or "")[0],
        "sender_email": _parse_sender(doc.sender or "")[1],
        "recipients": doc.recipients or "",
        "cc": doc.cc or "",
        "bcc": doc.bcc or "",
        "content": doc.content or "",
        "text_content": doc.text_content or "",
        "communication_date": str(doc.communication_date),
        "time_display": _format_time(doc.communication_date),
        "sent_or_received": doc.sent_or_received,
        "status": doc.status,
        "email_account": doc.email_account,
        "mail_starred": 1 if doc._liked_by and user in doc._liked_by else 0,
        "labels": _get_document_tags(doc.name),
        "has_attachment": doc.has_attachment or 0,
        "attachments": _get_attachments(doc.name),
        "avatar_initials": _get_initials(doc.sender_full_name or doc.sender or ""),
        "avatar_color": _email_to_color(_parse_sender(doc.sender or "")[1]),
        "read_by_current_user": doc.read_by_current_user or 0,
    }


# ─────────────────────────────────────────────
# SEND EMAIL
# ─────────────────────────────────────────────

@frappe.whitelist()
def send_email(from_account, recipients, subject, content,
               cc="", bcc="", reply_to=None, in_reply_to=None,
               attachments=None):
    """
    Send an email via Frappe's email queue.
    Creates a Communication record and enqueues delivery.
    """
    from_account_doc = frappe.get_doc("Email Account", from_account)
    _check_email_account_access(from_account)

    # Validate recipients
    if not recipients:
        frappe.throw(_("At least one recipient is required"))

    # Parse recipients
    recipient_list = [r.strip() for r in recipients.split(",") if r.strip()]
    cc_list = [c.strip() for c in cc.split(",") if c.strip()] if cc else []
    bcc_list = [b.strip() for b in bcc.split(",") if b.strip()] if bcc else []

    # Build Communication
    comm = frappe.new_doc("Communication")
    comm.communication_type = "Communication"
    comm.communication_medium = "Email"
    comm.sent_or_received = "Sent"
    comm.subject = subject or "(No Subject)"
    comm.content = content
    comm.sender = from_account_doc.email_id
    comm.sender_full_name = frappe.get_value("User", frappe.session.user, "full_name")
    comm.recipients = recipients
    comm.cc = cc
    comm.bcc = bcc
    comm.email_account = from_account
    comm.status = "Open"
    comm.communication_date = now_datetime()

    if in_reply_to:
        comm.in_reply_to = in_reply_to
        parent = frappe.get_doc("Communication", in_reply_to)
        comm.reference_doctype = "Communication"
        comm.reference_name = in_reply_to
        if not subject.startswith("Re:"):
            comm.subject = "Re: " + subject

    comm.insert(ignore_permissions=True)

    # Process attachments if any
    attachment_list = []
    if attachments:
        try:
            attachment_list = json.loads(attachments)
        except:
            pass

    # Enqueue via Frappe's mailer
    try:
        frappe.sendmail(
            recipients=recipient_list,
            cc=cc_list,
            bcc=bcc_list,
            subject=comm.subject,
            message=content,
            email_account=from_account,
            reference_doctype="Communication",
            reference_name=comm.name,
            reply_to=reply_to or from_account_doc.email_id,
            attachments=attachment_list,
            now=False,  # queue it
        )
        
        frappe.db.set_value("Communication", comm.name, "status", "Sent")
        
    except Exception as e:
        frappe.db.set_value("Communication", comm.name, "status", "Error")
        frappe.log_error(f"Email send failed: {str(e)}")
        frappe.throw(_("Failed to send email: {0}").format(str(e)))

    frappe.db.commit()
    return {"name": comm.name, "status": "queued"}


@frappe.whitelist()
def save_draft(from_account, recipients="", subject="",
               content="", cc="", bcc=""):
    """Save an email as Draft Communication."""
    _check_email_account_access(from_account)

    from_account_doc = frappe.get_doc("Email Account", from_account)

    comm = frappe.new_doc("Communication")
    comm.communication_type = "Communication"
    comm.communication_medium = "Email"
    comm.sent_or_received = "Sent"
    comm.subject = subject or "(No Subject)"
    comm.content = content
    comm.sender = from_account_doc.email_id
    comm.recipients = recipients
    comm.cc = cc
    comm.bcc = bcc
    comm.email_account = from_account
    comm.status = "Draft"
    comm.communication_date = now_datetime()
    comm.insert(ignore_permissions=True)
    frappe.db.commit()

    return {"name": comm.name}


# ─────────────────────────────────────────────
# EMAIL ACTIONS
# ─────────────────────────────────────────────

@frappe.whitelist()
def mark_read(names, read=1):
    """Mark one or more communications as read/unread."""
    names = json.loads(names) if isinstance(names, str) else names
    read = cint(read)

    for name in names:
        frappe.db.set_value(
            "Communication", name,
            "read_by_current_user", read,
            update_modified=False,
        )
    frappe.db.commit()
    return {"updated": len(names)}


@frappe.whitelist()
def toggle_star(name):
    """Toggle the starred flag on a communication using Frappe's _liked_by."""
    user = frappe.session.user
    doc = frappe.get_doc("Communication", name)
    
    # Get current liked_by
    liked_by = json.loads(doc._liked_by or "[]")
    
    if user in liked_by:
        liked_by.remove(user)
        starred = 0
    else:
        liked_by.append(user)
        starred = 1
    
    frappe.db.set_value(
        "Communication", name, "_liked_by", json.dumps(liked_by),
        update_modified=False
    )
    frappe.db.commit()
    return {"starred": starred}


@frappe.whitelist()
def move_to_folder(names, folder):
    """
    Move emails to a folder.
    Uses:
    - status for system folders (Spam/Trash)
    - mail_folder custom field for Archive and custom folders
    """
    names = json.loads(names) if isinstance(names, str) else names
    allowed = ["inbox", "archive", "spam", "trash"]

    for name in names:
        if folder == "trash":
            frappe.db.set_value("Communication", name, "status", "Trash",
                                update_modified=False)
            if frappe.db.has_column("Communication", "mail_folder"):
                frappe.db.set_value("Communication", name, "mail_folder", "",
                                    update_modified=False)
        elif folder == "spam":
            frappe.db.set_value("Communication", name, "status", "Spam",
                                update_modified=False)
        elif folder == "archive":
            if frappe.db.has_column("Communication", "mail_folder"):
                frappe.db.set_value("Communication", name, "mail_folder", "Archive",
                                    update_modified=False)
                frappe.db.set_value("Communication", name, "status", "Archived",
                                    update_modified=False)
        elif folder == "inbox":
            frappe.db.set_value("Communication", name, "status", "Open",
                                update_modified=False)
            if frappe.db.has_column("Communication", "mail_folder"):
                frappe.db.set_value("Communication", name, "mail_folder", "",
                                    update_modified=False)
        else:
            # Custom folder - store in mail_folder field
            if frappe.db.has_column("Communication", "mail_folder"):
                frappe.db.set_value("Communication", name, "mail_folder", folder,
                                    update_modified=False)

    frappe.db.commit()
    return {"moved": len(names), "folder": folder}


@frappe.whitelist()
def update_labels(name, labels):
    """
    Update labels on a communication using Frappe's tagging system.
    labels: JSON list of tag names
    """
    if isinstance(labels, str):
        labels = json.loads(labels) if labels.startswith("[") else [labels]
    
    # Clear existing tags
    frappe.db.delete("Tag Link", {
        "document_type": "Communication",
        "document_name": name
    })
    
    # Add new tags
    for label in labels:
        if label.strip():
            tag_link = frappe.get_doc({
                "doctype": "Tag Link",
                "document_type": "Communication",
                "document_name": name,
                "tag": label.strip()
            })
            tag_link.insert(ignore_permissions=True)
    
    frappe.db.commit()
    return {"name": name, "labels": labels}


@frappe.whitelist()
def delete_permanent(names):
    """Permanently delete trashed emails."""
    names = json.loads(names) if isinstance(names, str) else names
    deleted = 0
    for name in names:
        status = frappe.db.get_value("Communication", name, "status")
        if status == "Trash":
            # Delete tag links first
            frappe.db.delete("Tag Link", {
                "document_type": "Communication",
                "document_name": name
            })
            # Delete the document
            frappe.delete_doc("Communication", name, ignore_permissions=True)
            deleted += 1
    frappe.db.commit()
    return {"deleted": deleted}


# ─────────────────────────────────────────────
# USER LABELS (using Frappe's built-in tags)
# ─────────────────────────────────────────────

def _get_user_labels(user):
    """Get all tags used by this user"""
    # Get all unique tags from Tag Link for this user's communications
    tags = frappe.db.sql("""
        SELECT DISTINCT tag 
        FROM `tabTag Link` 
        WHERE document_type = 'Communication'
        ORDER BY tag
    """, as_dict=True)
    
    # Format for frontend
    formatted_tags = []
    for tag in tags:
        formatted_tags.append({
            "name": tag.tag,
            "label_name": tag.tag,
            "color": _get_tag_color(tag.tag)
        })
    
    # Add some default tags if none exist
    if not formatted_tags:
        defaults = ["Finance", "Clients", "HR", "Operations", "Church", "Urgent"]
        for tag in defaults:
            formatted_tags.append({
                "name": tag,
                "label_name": tag,
                "color": _get_tag_color(tag)
            })
    
    return formatted_tags


def _get_tag_color(tag):
    """Generate consistent color for a tag"""
    colors = {
        "Finance": "#26d7a0",
        "Clients": "#c084fc",
        "HR": "#4f9eff",
        "Operations": "#f59e0b",
        "Church": "#e879f9",
        "Urgent": "#f26d6d",
    }
    return colors.get(tag, "#4f9eff")


def _get_document_tags(docname):
    """Get all tags for a document"""
    tags = frappe.db.get_all(
        "Tag Link",
        filters={
            "document_type": "Communication",
            "document_name": docname
        },
        pluck="tag"
    )
    return tags


@frappe.whitelist()
def get_labels():
    """Return all labels available to this user."""
    return _get_user_labels(frappe.session.user)


@frappe.whitelist()
def create_label(label_name, color="#4f9eff"):
    """Create a new user label."""
    # Using Frappe's tagging system, we don't need to create a separate doctype
    # Just return success - the tag will be created when first used
    return {
        "name": label_name,
        "label_name": label_name,
        "color": color
    }


@frappe.whitelist()
def delete_label(label_name):
    """Delete a user label."""
    # Remove tag from all communications
    frappe.db.delete("Tag Link", {
        "document_type": "Communication",
        "tag": label_name
    })
    frappe.db.commit()
    return {"deleted": label_name}


# ─────────────────────────────────────────────
# REAL-TIME: NEW EMAIL POLLING
# ─────────────────────────────────────────────

@frappe.whitelist()
def poll_new_emails(since_datetime, folder="inbox", account=None):
    """
    Return emails received after `since_datetime`.
    Used by frontend's real-time polling (30s interval).
    """
    user = frappe.session.user
    accounts = _get_user_email_accounts(user)
    account_names = [a["name"] for a in accounts]

    if account and account in account_names:
        account_names = [account]

    if not account_names:
        return {"emails": [], "count": 0}

    filters = {
        "communication_medium": "Email",
        "email_account": ["in", account_names],
        "sent_or_received": "Received",
        "status": ["not in", ["Spam", "Trash", "Archived"]],
        "communication_date": [">", since_datetime],
    }

    if folder == "inbox" and frappe.db.has_column("Communication", "mail_folder"):
        filters["mail_folder"] = ["!=", "Archive"]

    emails = frappe.get_all(
        "Communication",
        filters=filters,
        fields=[
            "name", "subject", "sender", "sender_full_name",
            "communication_date", "email_account",
            "read_by_current_user", "has_attachment",
        ],
        order_by="communication_date desc",
        limit=20,
    )

    for e in emails:
        e["sender_name"], e["sender_email"] = _parse_sender(e.get("sender", ""))
        e["preview"] = _get_preview(e["name"])
        e["labels"] = _get_document_tags(e["name"])
        e["time_display"] = _format_time(e.get("communication_date"))
        e["avatar_initials"] = _get_initials(e.get("sender_full_name") or e["sender_email"])
        e["avatar_color"] = _email_to_color(e["sender_email"])
        e["mail_starred"] = 0  # Will be populated by frontend

    return {"emails": emails, "count": len(emails)}


@frappe.whitelist()
def trigger_email_sync():
    """
    Manually trigger an email sync for all enabled accounts.
    """
    accounts = frappe.get_all(
        "Email Account",
        filters={"enable_incoming": 1, "awaiting_password": 0},
        pluck="name",
    )
    for acct in accounts:
        frappe.enqueue(
            "frappe.email.receive.fetch_emails",
            email_account=acct,
            now=False,
            queue="short",
        )
    return {"syncing": len(accounts)}


# ─────────────────────────────────────────────
# SEARCH
# ─────────────────────────────────────────────

@frappe.whitelist()
def search_emails(query, folder=None, account=None,
                  label=None, date_from=None, date_to=None):
    """Full-text search across subject, sender, content."""
    if not query or len(query) < 2:
        return {"emails": [], "total": 0}

    user = frappe.session.user
    accounts = _get_user_email_accounts(user)
    account_names = [a["name"] for a in accounts]

    filters = {
        "communication_medium": "Email",
        "email_account": ["in", account_names],
        "status": ["not in", ["Trash"]],
    }

    if account and account in account_names:
        filters["email_account"] = account

    if date_from:
        filters["communication_date"] = [">=", date_from]
    if date_to:
        filters["communication_date"] = ["<=", date_to + " 23:59:59"]

    # Label filter using tags
    if label:
        communications_with_tag = frappe.db.get_all(
            "Tag Link",
            filters={
                "tag": label,
                "document_type": "Communication"
            },
            pluck="document_name"
        )
        if communications_with_tag:
            filters["name"] = ["in", communications_with_tag]
        else:
            return {"emails": [], "total": 0}

    # Frappe search across multiple fields
    results = frappe.get_all(
        "Communication",
        filters=filters,
        or_filters={
            "subject": ["like", f"%{query}%"],
            "sender": ["like", f"%{query}%"],
            "sender_full_name": ["like", f"%{query}%"],
            "content": ["like", f"%{query}%"],
        },
        fields=[
            "name", "subject", "sender", "sender_full_name",
            "communication_date", "email_account",
            "read_by_current_user", "_liked_by",
            "has_attachment", "status",
        ],
        order_by="communication_date desc",
        limit=50,
    )

    for e in results:
        e["sender_name"], e["sender_email"] = _parse_sender(e.get("sender", ""))
        e["preview"] = _get_preview(e["name"])
        e["labels"] = _get_document_tags(e["name"])
        e["mail_starred"] = 1 if e.get("_liked_by") and user in e["_liked_by"] else 0
        e["time_display"] = _format_time(e.get("communication_date"))
        e["avatar_initials"] = _get_initials(e.get("sender_full_name") or e["sender_email"])
        e["avatar_color"] = _email_to_color(e["sender_email"])

    return {"emails": results, "total": len(results), "query": query}


# ─────────────────────────────────────────────
# USER PREFERENCES
# ─────────────────────────────────────────────

@frappe.whitelist()
def save_preferences(prefs):
    """
    Persist user UI preferences (theme, layout, etc.)
    Stored in User's custom 'mail_vault_prefs' field (JSON).
    """
    if isinstance(prefs, str):
        prefs = json.loads(prefs)

    # Save to cache for quick access
    frappe.cache().set_value(
        f"mail_vault_prefs_{frappe.session.user}",
        json.dumps(prefs),
        expires_in_sec=86400 * 30,  # 30 days
    )
    
    # Save to User document if custom field exists
    if frappe.db.has_column("User", "mail_vault_prefs"):
        frappe.db.set_value("User", frappe.session.user, "mail_vault_prefs", json.dumps(prefs))
    
    return {"saved": True}


def _get_user_prefs(user):
    """Get user preferences from cache or DB"""
    # Try cache first
    cached = frappe.cache().get_value(f"mail_vault_prefs_{user}")
    if cached:
        try:
            return json.loads(cached)
        except Exception:
            pass
    
    # Try DB if custom field exists
    if frappe.db.has_column("User", "mail_vault_prefs"):
        prefs_str = frappe.db.get_value("User", user, "mail_vault_prefs")
        if prefs_str:
            try:
                return json.loads(prefs_str)
            except Exception:
                pass
    
    # Default preferences
    return {"theme": "navy", "sidebar_collapsed": False, "thread_view": True}


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _parse_sender(sender_str):
    """Parse 'Name <email@domain.com>' into (name, email)."""
    if not sender_str:
        return ("Unknown", "")
    name, email = parseaddr(sender_str)
    return (name or email.split("@")[0] if email else "Unknown", email)


def _get_preview(communication_name):
    """Get first 120 chars of plain-text content as preview."""
    content = frappe.db.get_value("Communication", communication_name, "text_content") or \
              frappe.db.get_value("Communication", communication_name, "content") or ""
    # Strip HTML tags
    text = re.sub(r"<[^>]+>", " ", content)
    # Normalize whitespace
    text = " ".join(text.split())
    return text[:120]


def _get_attachments(communication_name):
    """Return file attachments linked to this communication."""
    return frappe.get_all(
        "File",
        filters={"attached_to_doctype": "Communication",
                 "attached_to_name": communication_name},
        fields=["name", "file_name", "file_size", "file_url"],
    )


def _format_time(dt):
    """Return human-friendly time: HH:MM for today, Day for this week, etc."""
    if not dt:
        return ""
    
    from frappe.utils import get_datetime, today, date_diff
    
    try:
        dt_obj = get_datetime(dt)
        now = get_datetime(now_datetime())
        diff_days = date_diff(now.date(), dt_obj.date())

        if diff_days == 0:
            return dt_obj.strftime("%I:%M %p").lstrip("0")
        elif diff_days == 1:
            return "Yesterday"
        elif diff_days < 7:
            return dt_obj.strftime("%a")
        elif diff_days < 365:
            return dt_obj.strftime("%d %b")
        else:
            return dt_obj.strftime("%d/%m/%y")
    except Exception:
        return str(dt)[:10]


def _get_initials(name):
    """Get initials from a name"""
    if not name:
        return "??"
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper()


def _email_to_color(email):
    """Generate a consistent color from an email address hash."""
    PALETTE = [
        "#4f9eff", "#7c6dfa", "#26d7a0", "#f59e0b",
        "#f26d6d", "#c084fc", "#e879f9", "#059669",
        "#0891b2", "#e11d48", "#d97706", "#84cc16",
    ]
    if not email:
        return PALETTE[0]
    h = sum(ord(c) for c in email)
    return PALETTE[h % len(PALETTE)]


def _check_email_account_access(account_name):
    """Ensure the current user has access to the given email account."""
    if not account_name:
        return
    exists = frappe.db.exists(
        "Email Account",
        {"name": account_name, "enable_incoming": 1}
    )
    if not exists:
        frappe.throw(_("Email account '{0}' not found or inaccessible").format(account_name))