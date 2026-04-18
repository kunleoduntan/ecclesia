"""
ecclesia/api/internal_chat.py
Internal Team Chat backend.
All @frappe.whitelist() methods called by internal_chat.js.
"""

import json
import base64
import frappe
from frappe import _
from frappe.utils import now_datetime, cstr


# ─────────────────────────────────────────────────────────────────────────────
# CONVERSATIONS
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_my_conversations() -> list:
    """Return all conversations the current user is a member of."""
    user = frappe.session.user

    # Get chats where user is a member (via child table)
    member_chats = frappe.db.sql("""
        SELECT DISTINCT m.parent
        FROM `tabWA Internal Chat Member` m
        WHERE m.user = %s
          AND m.parenttype = 'WA Internal Chat'
    """, user, as_dict=True)

    chat_names = [r.parent for r in member_chats]
    if not chat_names:
        return []

    chats = frappe.get_all(
        "WA Internal Chat",
        filters={"name": ("in", chat_names), "is_active": 1, "is_archived": 0},
        fields=["name", "chat_type", "chat_name", "last_message_at",
                "last_message_preview", "member_count", "linked_doctype",
                "linked_docname", "is_pinned"],
        order_by="is_pinned desc, last_message_at desc",
        limit=100
    )

    # Attach unread count and members per chat
    for chat in chats:
        member = frappe.db.get_value(
            "WA Internal Chat Member",
            {"parent": chat.name, "user": user, "parenttype": "WA Internal Chat"},
            ["unread_count", "last_read_at"],
            as_dict=True
        )
        chat.unread_count = member.unread_count if member else 0

        # For DMs: store other user's email for online status
        if chat.chat_type == "Direct Message":
            members = frappe.get_all(
                "WA Internal Chat Member",
                filters={"parent": chat.name, "parenttype": "WA Internal Chat"},
                fields=["user", "full_name"]
            )
            other = next((m for m in members if m.user != user), None)
            chat._other_user = other.user if other else None
            chat.chat_name   = other.full_name or other.user if other else chat.chat_name

        # Attach member list (lightweight)
        chat.members = frappe.get_all(
            "WA Internal Chat Member",
            filters={"parent": chat.name, "parenttype": "WA Internal Chat"},
            fields=["user", "full_name", "role"]
        )

    return chats


@frappe.whitelist()
def get_or_create_conversation(chat_type: str, members: str, chat_name: str = None) -> dict:
    """
    Get existing DM or create a new conversation.
    members: JSON array of user email strings
    """
    members_list = frappe.parse_json(members) if isinstance(members, str) else members
    current_user = frappe.session.user

    # Include current user
    all_members = list(set(members_list + [current_user]))

    # For DM: check if conversation already exists between these two users
    if chat_type == "Direct Message" and len(all_members) == 2:
        existing = _find_existing_dm(all_members[0], all_members[1])
        if existing:
            return frappe.get_doc("WA Internal Chat", existing).as_dict()

    # Determine chat name
    if not chat_name:
        if chat_type == "Direct Message":
            other = next((m for m in all_members if m != current_user), "")
            chat_name = frappe.db.get_value("User", other, "full_name") or other
        else:
            chat_name = "New Group"

    # Create conversation
    chat = frappe.get_doc({
        "doctype":      "WA Internal Chat",
        "chat_type":    chat_type,
        "chat_name":    chat_name,
        "is_active":    1,
        "created_by":   current_user,
        "member_count": len(all_members),
        "members": [
            {
                "user":        m,
                "full_name":   frappe.db.get_value("User", m, "full_name") or m,
                "role":        "Owner" if m == current_user else "Member",
                "joined_at":   now_datetime()
            }
            for m in all_members
        ]
    })
    chat.insert(ignore_permissions=True)

    # Post system message
    _post_system_message(chat.name, f"Chat created by {frappe.session.user}")
    frappe.db.commit()

    result = chat.as_dict()
    result._other_user = next((m for m in all_members if m != current_user), None)
    return result


def _find_existing_dm(user1: str, user2: str) -> str | None:
    """Find an existing DM chat between exactly two users."""
    chats_user1 = set(frappe.db.sql("""
        SELECT parent FROM `tabWA Internal Chat Member`
        WHERE user=%s AND parenttype='WA Internal Chat'
    """, user1, as_list=True) or [])

    chats_user2 = set(frappe.db.sql("""
        SELECT parent FROM `tabWA Internal Chat Member`
        WHERE user=%s AND parenttype='WA Internal Chat'
    """, user2, as_list=True) or [])

    common = {c[0] for c in chats_user1} & {c[0] for c in chats_user2}
    for chat_name in common:
        chat = frappe.db.get_value(
            "WA Internal Chat",
            {"name": chat_name, "chat_type": "Direct Message"},
            "name"
        )
        if chat:
            return chat
    return None


# ─────────────────────────────────────────────────────────────────────────────
# MESSAGES
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_messages(chat_name: str, page: int = 0, page_size: int = 30) -> dict:
    """Paginated message fetch for a conversation."""
    _assert_member(chat_name)

    page     = int(page)
    page_size= int(page_size)
    offset   = page * page_size

    messages = frappe.get_all(
        "WA Internal Chat Message",
        filters={"chat": chat_name, "is_deleted": 0},
        fields=["name", "sender", "sender_name", "message_type", "body",
                "body_html", "timestamp", "is_edited", "edited_at",
                "reply_to", "reactions", "is_pinned", "ref_doctype",
                "ref_docname", "system_event", "poll_question", "poll_options",
                "poll_votes", "location_lat", "location_lng", "location_name"],
        order_by="timestamp desc",
        limit=page_size,
        start=offset
    )

    # Reverse so oldest first
    messages = list(reversed(messages))

    # Attach attachments for each message
    for msg in messages:
        msg.attachments = frappe.get_all(
            "WA Internal Chat Attachment",
            filters={"parent": msg.name, "parenttype": "WA Internal Chat Message"},
            fields=["file", "filename", "file_type", "mime_type",
                    "file_size", "thumbnail_url", "duration_seconds"]
        )

    total = frappe.db.count("WA Internal Chat Message",
                             {"chat": chat_name, "is_deleted": 0})
    has_more = (offset + page_size) < total

    return {"messages": messages, "has_more": has_more, "total": total}


@frappe.whitelist()
def send_message(chat_name: str, message_type: str = "text", body: str = None,
                  reply_to: str = None, media_url: str = None,
                  media_filename: str = None, media_file_size: int = None,
                  mime_type: str = None, ref_doctype: str = None,
                  ref_docname: str = None) -> dict:
    """Create a new internal chat message and broadcast via realtime."""
    _assert_member(chat_name)
    user = frappe.session.user

    msg = frappe.get_doc({
        "doctype":       "WA Internal Chat Message",
        "chat":          chat_name,
        "sender":        user,
        "sender_name":   frappe.db.get_value("User", user, "full_name") or user,
        "message_type":  message_type,
        "body":          body,
        "timestamp":     now_datetime(),
        "reply_to":      reply_to,
        "ref_doctype":   ref_doctype,
        "ref_docname":   ref_docname,
        "reactions":     None
    })

    # Attach file if media
    if media_url and message_type in ("image", "video", "audio", "document"):
        msg.append("attachments", {
            "file":       media_url,
            "filename":   media_filename or "",
            "file_type":  message_type,
            "mime_type":  mime_type or "",
            "file_size":  media_file_size or 0
        })

    # Extract @mentions
    if body:
        msg.mentions = _extract_mentions(body)

    msg.insert(ignore_permissions=True)

    # Update conversation counters
    frappe.db.set_value("WA Internal Chat", chat_name, {
        "last_message_at":      str(now_datetime()),
        "last_message_preview": _preview_text(message_type, body),
        "total_messages":       (frappe.db.get_value("WA Internal Chat", chat_name,
                                                      "total_messages") or 0) + 1
    })

    # Increment unread for all members except sender
    _increment_member_unreads(chat_name, user)
    frappe.db.commit()

    # Realtime broadcast
    msg_dict = msg.as_dict()
    msg_dict.attachments = frappe.get_all(
        "WA Internal Chat Attachment",
        filters={"parent": msg.name, "parenttype": "WA Internal Chat Message"},
        fields=["file", "filename", "file_type", "mime_type", "file_size"]
    )

    frappe.publish_realtime(
        "ic_new_message",
        {**msg_dict, "chat_name": chat_name},
        after_commit=True
    )

    # Push notification to mentioned users
    if body and msg.mentions:
        _notify_mentions(chat_name, msg.mentions, body, user)

    return msg_dict


@frappe.whitelist()
def edit_message(message_name: str, new_body: str) -> dict:
    msg = frappe.get_doc("WA Internal Chat Message", message_name)
    if msg.sender != frappe.session.user:
        frappe.throw(_("You can only edit your own messages."))

    msg.body     = new_body
    msg.is_edited= 1
    msg.edited_at= now_datetime()
    msg.save(ignore_permissions=True)
    frappe.db.commit()

    frappe.publish_realtime("ic_message_edited", {
        "message_name": message_name,
        "new_body":     new_body,
        "chat_name":    msg.chat
    }, after_commit=True)

    return msg.as_dict()


@frappe.whitelist()
def delete_message(message_name: str):
    msg = frappe.get_doc("WA Internal Chat Message", message_name)
    if msg.sender != frappe.session.user:
        # Allow admins
        if "System Manager" not in frappe.get_roles():
            frappe.throw(_("You can only delete your own messages."))

    frappe.db.set_value("WA Internal Chat Message", message_name, {
        "is_deleted": 1,
        "deleted_at": now_datetime()
    })
    frappe.db.commit()

    frappe.publish_realtime("ic_message_deleted", {
        "message_name": message_name,
        "chat_name":    msg.chat
    }, after_commit=True)


@frappe.whitelist()
def react_to_message(message_name: str, emoji: str) -> dict:
    """Toggle a reaction on a message. Returns updated reactions."""
    user = frappe.session.user
    raw  = frappe.db.get_value("WA Internal Chat Message", message_name, "reactions")
    reactions = json.loads(raw) if raw else {}

    users_for_emoji = reactions.get(emoji, [])
    if user in users_for_emoji:
        users_for_emoji.remove(user)      # toggle off
    else:
        users_for_emoji.append(user)      # toggle on

    if users_for_emoji:
        reactions[emoji] = users_for_emoji
    else:
        reactions.pop(emoji, None)

    new_raw = json.dumps(reactions)
    frappe.db.set_value("WA Internal Chat Message", message_name, "reactions", new_raw)
    frappe.db.commit()

    chat_name = frappe.db.get_value("WA Internal Chat Message", message_name, "chat")
    frappe.publish_realtime("ic_message_reaction", {
        "message_name": message_name,
        "reactions":    new_raw,
        "chat_name":    chat_name
    }, after_commit=True)

    return {"reactions": new_raw}


@frappe.whitelist()
def pin_message(message_name: str, pinned: bool = True):
    msg = frappe.get_doc("WA Internal Chat Message", message_name)
    _assert_admin(msg.chat)
    frappe.db.set_value("WA Internal Chat Message", message_name, {
        "is_pinned": 1 if pinned else 0,
        "pinned_by": frappe.session.user if pinned else None
    })
    frappe.db.commit()


@frappe.whitelist()
def get_pinned_messages(chat_name: str) -> list:
    _assert_member(chat_name)
    return frappe.get_all(
        "WA Internal Chat Message",
        filters={"chat": chat_name, "is_pinned": 1, "is_deleted": 0},
        fields=["name", "sender_name", "body", "message_type", "timestamp"]
    )


# ─────────────────────────────────────────────────────────────────────────────
# MARK READ
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def mark_as_read(chat_name: str):
    user = frappe.session.user
    frappe.db.set_value(
        "WA Internal Chat Member",
        {"parent": chat_name, "user": user, "parenttype": "WA Internal Chat"},
        {"unread_count": 0, "last_read_at": now_datetime()}
    )
    frappe.db.commit()

    # Notify sender(s) of read receipt
    frappe.publish_realtime("ic_message_read", {
        "chat_name": chat_name,
        "read_by":   user
    }, after_commit=True)


# ─────────────────────────────────────────────────────────────────────────────
# TYPING INDICATOR
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def broadcast_typing(chat_name: str, is_typing: bool):
    user = frappe.session.user
    if isinstance(is_typing, str):
        is_typing = is_typing.lower() in ("1", "true", "yes")
    frappe.publish_realtime("ic_typing", {
        "chat_name": chat_name,
        "user":      user,
        "user_name": frappe.db.get_value("User", user, "full_name") or user,
        "is_typing": is_typing
    })

# ─────────────────────────────────────────────────────────────────────────────
# ONLINE STATUS
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def set_online_status(online: bool):
    user = frappe.session.user
    if isinstance(online, str):
        online = online.lower() in ("1", "true", "yes")
    frappe.cache().set_value(f"ic_online:{user}", 1 if online else 0, expires_in_sec=60)
    frappe.publish_realtime("ic_user_online", {"user": user, "online": bool(online)})


@frappe.whitelist()
def get_online_users() -> list:
    users = frappe.get_all("User", filters={"enabled": 1}, fields=["name"])
    online = []
    for u in users:
        if frappe.cache().get_value(f"ic_online:{u.name}"):
            online.append(u.name)
    return online


# ─────────────────────────────────────────────────────────────────────────────
# USER SEARCH
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def search_users(query: str = "", exclude: str = None) -> list:
    exclude_list = frappe.parse_json(exclude) if isinstance(exclude, str) else (exclude or [])

    filters = {"enabled": 1, "name": ("not in", ["Guest"] + exclude_list)}
    if query:
        filters["full_name"] = ("like", f"%{query}%")

    users = frappe.get_all(
        "User",
        filters=filters,
        fields=["name as email", "full_name", "user_image"],
        limit=20,
        order_by="full_name asc"
    )

    # Attach online status
    for u in users:
        u.online = bool(frappe.cache().get_value(f"ic_online:{u.email}"))

    return users


# ─────────────────────────────────────────────────────────────────────────────
# FILE UPLOAD
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def upload_chat_file(chat_name: str, filename: str, file_data: str,
                      mime_type: str = "application/octet-stream") -> dict:
    """Receive base64 file, save via Frappe file manager, return URL."""
    _assert_member(chat_name)

    decoded = base64.b64decode(file_data)
    file_doc = frappe.get_doc({
        "doctype":    "File",
        "file_name":  filename,
        "content":    decoded,
        "is_private": 0
    })
    file_doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "file_url": file_doc.file_url,
        "file_name": file_doc.file_name,
        "file_size": len(decoded)
    }


# ─────────────────────────────────────────────────────────────────────────────
# MEMBERS MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def add_member(chat_name: str, user: str):
    _assert_admin(chat_name)
    chat = frappe.get_doc("WA Internal Chat", chat_name)
    chat.append("members", {
        "user":      user,
        "full_name": frappe.db.get_value("User", user, "full_name") or user,
        "role":      "Member",
        "joined_at": now_datetime()
    })
    chat.member_count = len(chat.members)
    chat.save(ignore_permissions=True)
    _post_system_message(chat_name, f"{user} was added to the chat")
    frappe.db.commit()


@frappe.whitelist()
def remove_member(chat_name: str, user: str):
    _assert_admin(chat_name)
    chat = frappe.get_doc("WA Internal Chat", chat_name)
    chat.members = [m for m in chat.members if m.user != user]
    chat.member_count = len(chat.members)
    chat.save(ignore_permissions=True)
    _post_system_message(chat_name, f"{user} was removed from the chat")
    frappe.db.commit()


@frappe.whitelist()
def leave_chat(chat_name: str):
    user = frappe.session.user
    chat = frappe.get_doc("WA Internal Chat", chat_name)
    chat.members = [m for m in chat.members if m.user != user]
    chat.member_count = len(chat.members)
    chat.save(ignore_permissions=True)
    _post_system_message(chat_name, f"{user} left the chat")
    frappe.db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _assert_member(chat_name: str):
    user = frappe.session.user
    is_member = frappe.db.exists(
        "WA Internal Chat Member",
        {"parent": chat_name, "user": user, "parenttype": "WA Internal Chat"}
    )
    if not is_member and "System Manager" not in frappe.get_roles():
        frappe.throw(_("You are not a member of this chat."), frappe.PermissionError)


def _assert_admin(chat_name: str):
    user = frappe.session.user
    role = frappe.db.get_value(
        "WA Internal Chat Member",
        {"parent": chat_name, "user": user, "parenttype": "WA Internal Chat"},
        "role"
    )
    if role not in ("Admin", "Owner") and "System Manager" not in frappe.get_roles():
        frappe.throw(_("Only admins can perform this action."), frappe.PermissionError)


def _increment_member_unreads(chat_name: str, exclude_user: str):
    frappe.db.sql("""
        UPDATE `tabWA Internal Chat Member`
        SET unread_count = COALESCE(unread_count, 0) + 1
        WHERE parent = %s
          AND user != %s
          AND parenttype = 'WA Internal Chat'
    """, (chat_name, exclude_user))


def _post_system_message(chat_name: str, text: str):
    msg = frappe.get_doc({
        "doctype":      "WA Internal Chat Message",
        "chat":         chat_name,
        "sender":       frappe.session.user or "Administrator",
        "sender_name":  "System",
        "message_type": "system",
        "body":         text,
        "timestamp":    now_datetime(),
        "system_event": text
    })
    msg.insert(ignore_permissions=True)


def _preview_text(message_type: str, body: str) -> str:
    icons = {"image": "📷 Image", "video": "🎥 Video", "audio": "🎵 Audio",
             "document": "📎 Document"}
    if message_type != "text":
        return icons.get(message_type, f"[{message_type}]")
    return cstr(body)[:60] + ("…" if body and len(body) > 60 else "")


def _extract_mentions(body: str) -> str:
    """Extract @username mentions from message body."""
    import re
    mentions = []
    for match in re.finditer(r"@([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", body):
        email = match.group(1)
        if frappe.db.exists("User", email):
            mentions.append({"user": email})
    return json.dumps(mentions) if mentions else None


def _notify_mentions(chat_name: str, mentions_json: str, body: str, sender: str):
    try:
        mentions = json.loads(mentions_json) if mentions_json else []
        for mention in mentions:
            user = mention.get("user")
            if user and user != sender:
                frappe.publish_realtime(
                    "ic_mentioned",
                    {
                        "chat_name": chat_name,
                        "sender":    sender,
                        "body":      body[:100]
                    },
                    user=user
                )
    except Exception:
        pass
