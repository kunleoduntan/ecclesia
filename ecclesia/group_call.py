"""
ecclesia/ecclesia/group_call.py
================================
Server-side API for Ecclesia Group Calls.

Group calls use a mesh WebRTC topology:
  - Each participant creates a direct peer connection to every other participant.
  - Works well for 2-6 people on a local/office network.
  - Internal (WebRTC) only — external provider conference calls are out of scope.

API surface (all whitelisted):
  create_group_call(room_name, invitees)  → {gc_name, room_name}
  join_group_call(gc_name)               → {gc_name, room_name, participants[]}
  leave_group_call(gc_name)              → {status}
  invite_to_group_call(gc_name, users)   → {status}
  group_call_signal(gc_name, target_user, signal_type, data) → {status}
  end_group_call(gc_name)               → {status}  [host only]
  get_active_group_calls()              → [{gc_name, room_name, host, participant_count}]
"""

import json
import frappe
from frappe.utils import now_datetime


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_display_name(user):
    return frappe.db.get_value("User", user, "full_name") or user


def _assert_participant(gc_name):
    """Raise PermissionError if current user is not in the call."""
    user = frappe.session.user
    doc = frappe.get_doc("Telephone Group Call", gc_name)
    names = [p.user for p in doc.participants]
    if user not in names:
        frappe.throw("You are not a participant in this group call.", frappe.PermissionError)
    return doc


def _publish_room(gc_name, event, message):
    """Publish a realtime event to every participant of a group call."""
    doc = frappe.get_doc("Telephone Group Call", gc_name)
    for p in doc.participants:
        if p.status in ("Joined", "Invited"):
            frappe.publish_realtime(
                event=event,
                room="user:" + p.user,
                message=message,
                after_commit=True,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CREATE
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def create_group_call(room_name, invitees):
    """
    Create a new group call room and invite users.
    invitees: JSON array of Frappe usernames, e.g. ["user1@site.com", "user2@site.com"]
    Returns: {gc_name, room_name}
    """
    host = frappe.session.user
    if isinstance(invitees, str):
        invitees = json.loads(invitees)

    # Deduplicate and ensure host is included
    all_users = list({host} | set(invitees))

    # Validate all invitees are valid Frappe users
    for u in all_users:
        if not frappe.db.exists("User", u):
            frappe.throw(f"User not found: {u}")

    # Create the group call document
    doc = frappe.new_doc("Telephone Group Call")
    doc.room_name  = room_name or "Group Call"
    doc.host_user  = host
    doc.status     = "Active"
    doc.started_at = now_datetime()

    for u in all_users:
        doc.append("participants", {
            "user":         u,
            "display_name": _get_display_name(u),
            "joined_at":    now_datetime() if u == host else None,
            "status":       "Joined" if u == host else "Invited",
        })

    doc.insert(ignore_permissions=True)

    # Notify all invitees (not the host)
    for u in invitees:
        if u == host:
            continue
        frappe.publish_realtime(
            event="ecclesia_group_call_invite",
            room="user:" + u,
            message={
                "gc_name":    doc.name,
                "room_name":  doc.room_name,
                "host":       host,
                "host_name":  _get_display_name(host),
                "participants": [
                    {"user": p.user, "display_name": p.display_name}
                    for p in doc.participants
                ],
            },
            after_commit=True,
        )

    return {"gc_name": doc.name, "room_name": doc.room_name}


# ═══════════════════════════════════════════════════════════════════════════════
# 2. JOIN
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def join_group_call(gc_name):
    """
    Mark current user as Joined and return current participant list.
    The frontend uses this list to initiate WebRTC peer connections to everyone.
    Returns: {gc_name, room_name, participants: [{user, display_name}]}
    """
    user = frappe.session.user
    doc  = frappe.get_doc("Telephone Group Call", gc_name)

    if doc.status != "Active":
        frappe.throw("This group call has ended.")

    # Update participant row
    joined = False
    for p in doc.participants:
        if p.user == user:
            p.status    = "Joined"
            p.joined_at = now_datetime()
            joined = True
            break

    if not joined:
        # Allow joining even if not originally invited (open room)
        doc.append("participants", {
            "user":         user,
            "display_name": _get_display_name(user),
            "joined_at":    now_datetime(),
            "status":       "Joined",
        })

    doc.save(ignore_permissions=True)

    # Tell all other active participants someone new joined
    active = [p for p in doc.participants if p.status == "Joined" and p.user != user]
    for p in active:
        frappe.publish_realtime(
            event="ecclesia_group_call_peer_joined",
            room="user:" + p.user,
            message={
                "gc_name":      gc_name,
                "new_user":     user,
                "display_name": _get_display_name(user),
            },
            after_commit=True,
        )

    return {
        "gc_name":    gc_name,
        "room_name":  doc.room_name,
        "host":       doc.host_user,
        "participants": [
            {"user": p.user, "display_name": p.display_name, "status": p.status}
            for p in doc.participants
            if p.status == "Joined" and p.user != user
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 3. LEAVE
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def leave_group_call(gc_name):
    """Mark current user as Left and notify remaining participants."""
    user = frappe.session.user
    doc  = frappe.get_doc("Telephone Group Call", gc_name)

    for p in doc.participants:
        if p.user == user:
            p.status  = "Left"
            p.left_at = now_datetime()
            break

    # If host leaves and others remain, transfer host to first active participant
    remaining = [p for p in doc.participants if p.status == "Joined" and p.user != user]
    if doc.host_user == user and remaining:
        doc.host_user = remaining[0].user

    # If nobody left, end the call
    if not remaining:
        doc.status   = "Ended"
        doc.ended_at = now_datetime()
        _set_duration(doc)

    doc.save(ignore_permissions=True)

    # Notify remaining participants
    for p in remaining:
        frappe.publish_realtime(
            event="ecclesia_group_call_peer_left",
            room="user:" + p.user,
            message={
                "gc_name":      gc_name,
                "left_user":    user,
                "display_name": _get_display_name(user),
                "new_host":     doc.host_user,
            },
            after_commit=True,
        )

    return {"status": "left", "call_ended": doc.status == "Ended"}


# ═══════════════════════════════════════════════════════════════════════════════
# 4. INVITE MORE PEOPLE
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def invite_to_group_call(gc_name, users):
    """Add more participants to an active call and notify them."""
    if isinstance(users, str):
        users = json.loads(users)

    doc = _assert_participant(gc_name)
    if doc.status != "Active":
        frappe.throw("This group call has ended.")

    existing = {p.user for p in doc.participants}
    host     = frappe.session.user

    for u in users:
        if u in existing:
            continue
        if not frappe.db.exists("User", u):
            continue
        doc.append("participants", {
            "user":         u,
            "display_name": _get_display_name(u),
            "status":       "Invited",
        })
        frappe.publish_realtime(
            event="ecclesia_group_call_invite",
            room="user:" + u,
            message={
                "gc_name":    gc_name,
                "room_name":  doc.room_name,
                "host":       host,
                "host_name":  _get_display_name(host),
                "participants": [
                    {"user": p.user, "display_name": p.display_name}
                    for p in doc.participants if p.status == "Joined"
                ],
            },
            after_commit=True,
        )

    doc.save(ignore_permissions=True)
    return {"status": "invited"}


# ═══════════════════════════════════════════════════════════════════════════════
# 5. WEBRTC SIGNALING (mesh — send to one peer at a time)
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def group_call_signal(gc_name, target_user, signal_type, data):
    """
    Relay a WebRTC signaling message from the current user to one specific peer.
    signal_type: offer | answer | ice_candidate | hang_up
    The frontend calls this once per peer to build the mesh.
    """
    allowed = ["offer", "answer", "ice_candidate", "hang_up"]
    if signal_type not in allowed:
        frappe.throw(f"Invalid signal type: {signal_type}")

    sender = frappe.session.user
    payload = data if isinstance(data, dict) else json.loads(data)

    frappe.publish_realtime(
        event="ecclesia_group_call_signal",
        room="user:" + target_user,
        message={
            "gc_name":      gc_name,
            "signal_type":  signal_type,
            "from_user":    sender,
            "display_name": _get_display_name(sender),
            "payload":      payload,
        },
        after_commit=True,
    )
    return {"status": "sent"}


# ═══════════════════════════════════════════════════════════════════════════════
# 6. END CALL (host only)
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def end_group_call(gc_name):
    """End the call for everyone. Only the host or System Manager may do this."""
    user = frappe.session.user
    doc  = frappe.get_doc("Telephone Group Call", gc_name)

    if doc.host_user != user and "System Manager" not in frappe.get_roles(user):
        frappe.throw("Only the call host can end the call.", frappe.PermissionError)

    doc.status   = "Ended"
    doc.ended_at = now_datetime()
    _set_duration(doc)

    for p in doc.participants:
        if p.status == "Joined":
            p.status  = "Left"
            p.left_at = now_datetime()

    doc.save(ignore_permissions=True)

    # Notify all participants the call is over
    _publish_room(gc_name, "ecclesia_group_call_ended", {
        "gc_name":   gc_name,
        "ended_by":  user,
        "ended_name": _get_display_name(user),
    })

    return {"status": "ended"}


# ═══════════════════════════════════════════════════════════════════════════════
# 7. LIST ACTIVE CALLS
# ═══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_active_group_calls():
    """Return all active group calls the current user is part of."""
    user = frappe.session.user

    # Get all active calls
    calls = frappe.get_all(
        "Telephone Group Call",
        filters={"status": "Active"},
        fields=["name", "room_name", "host_user", "started_at"],
    )

    result = []
    for c in calls:
        participants = frappe.get_all(
            "Telephone Group Call Participant",
            filters={"parent": c.name, "parenttype": "Telephone Group Call"},
            fields=["user", "display_name", "status"],
        )
        user_names = [p.user for p in participants]
        if user in user_names:
            result.append({
                "gc_name":           c.name,
                "room_name":         c.room_name,
                "host":              c.host_user,
                "host_name":         _get_display_name(c.host_user),
                "started_at":        str(c.started_at),
                "participant_count": len([p for p in participants if p.status == "Joined"]),
                "participants":      participants,
            })

    return result


# ── Duration helper ───────────────────────────────────────────────────────────

def _set_duration(doc):
    if doc.started_at and doc.ended_at:
        delta = doc.ended_at - doc.started_at
        secs  = int(delta.total_seconds())
        m, s  = divmod(secs, 60)
        h, m  = divmod(m, 60)
        if h:
            doc.duration_formatted = f"{h}h {m}m {s}s"
        else:
            doc.duration_formatted = f"{m}m {s}s"