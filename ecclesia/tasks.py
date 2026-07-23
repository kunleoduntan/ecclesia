"""
ecclesia/tasks.py
All scheduled background tasks for Ecclesia including WA Engine.
Registered in hooks.py scheduler_events.
"""

import frappe
from frappe.utils import now_datetime, add_days


# =============================================================================
# WHATSAPP ENGINE TASKS
# =============================================================================

def check_all_escalations():
    """Every hour: evaluate all active escalation rules."""
    from ecclesia.api.escalation import check_all_escalations as _run
    _run()


def process_pending_broadcasts():
    """Every hour: send scheduled broadcasts that are due."""
    from ecclesia.api.broadcast import process_pending_broadcasts as _run
    _run()


def expire_pending_actions():
    """Every hour: mark expired WA Pending Actions."""
    from ecclesia.api.approval import expire_pending_actions as _run
    _run()


def retry_failed_messages():
    """Every 15 min: retry outbound WA messages that failed (up to 3 retries)."""
    failed = frappe.get_all(
        "WA Message",
        filters={
            "delivery_status": "failed",
            "direction":       "Outbound",
            "retry_count":     ("<", 3)
        },
        fields=["name", "conversation", "message_type", "body",
                "media_url", "retry_count"],
        limit=20
    )
    for msg in failed:
        try:
            from ecclesia.api.conversation import send_outbound_message
            frappe.db.set_value("WA Message", msg.name, "retry_count",
                                (msg.retry_count or 0) + 1)
            send_outbound_message(
                conv_name=msg.conversation,
                message_type=msg.message_type,
                body=msg.body,
                media_url=msg.media_url
            )
        except Exception:
            frappe.log_error(frappe.get_traceback(),
                             f"Retry Failed: {msg.name}")


def process_message_queue():
    """Every 15 min: placeholder — Frappe's background queue handles dispatches."""
    pass


def send_daily_overdue_digest():
    """Daily: send overdue invoice digest to Accounts Managers via WhatsApp."""
    from ecclesia.utils.helpers import get_settings
    settings = get_settings()
    if not settings.wa_enabled:
        return

    overdue_invoices = frappe.get_all(
        "Sales Invoice",
        filters={"docstatus": 1, "status": "Overdue"},
        fields=["name", "customer_name", "outstanding_amount", "due_date"],
        limit=10
    )
    if not overdue_invoices:
        return

    lines = ["📊 *Daily Overdue Invoice Digest*\n"]
    for inv in overdue_invoices:
        lines.append(
            f"• {inv.name} — {inv.customer_name} — "
            f"₦{inv.outstanding_amount:,.0f} (due {inv.due_date})"
        )
    lines.append(f"\n_Total: {len(overdue_invoices)} overdue invoices_")
    body = "\n".join(lines)

    from ecclesia.api.whatsapp import send_text
    users = frappe.get_all(
        "Has Role",
        filters={"role": "Accounts Manager", "parenttype": "User"},
        fields=["parent"]
    )
    for u in users:
        phone = frappe.db.get_value("User", u.parent, "mobile_no")
        if phone:
            send_text(phone, body)


def cleanup_old_media():
    """Daily: clear expired WhatsApp media URL entries (Meta URLs expire after 30 days)."""
    cutoff = add_days(now_datetime(), -30)
    frappe.db.sql("""
        UPDATE `tabWA Media`
        SET uploaded_to_wa = 0, wa_media_id = NULL
        WHERE wa_media_url_expiry IS NOT NULL
          AND wa_media_url_expiry < %s
    """, cutoff)
    frappe.db.commit()


def archive_old_chat_messages():
    """Daily: soft-delete internal chat messages older than the retention period."""
    from ecclesia.utils.helpers import get_settings
    settings = get_settings()
    retention = settings.chat_retention_days or 365
    cutoff = add_days(now_datetime(), -retention)
    frappe.db.sql("""
        UPDATE `tabWA Internal Chat Message`
        SET is_deleted = 1, deleted_at = %s
        WHERE timestamp < %s
          AND is_deleted = 0
          AND message_type != 'system'
    """, (now_datetime(), cutoff))
    frappe.db.commit()


def refresh_wa_media_urls():
    """Daily: re-fetch download URLs for inbound media (Meta URLs expire)."""
    from ecclesia.utils.helpers import get_settings
    import requests

    settings = get_settings()
    if not settings.wa_enabled:
        return

    stale = frappe.get_all(
        "WA Message",
        filters={
            "message_type": ("in", ["image", "video", "audio", "document"]),
            "media_url":    ("is", "not set"),
            "media_id":     ("is", "set"),
            "direction":    "Inbound"
        },
        fields=["name", "media_id", "media_mime_type"],
        limit=50
    )

    headers = {"Authorization": f"Bearer {settings.get_password('wa_access_token')}"}
    for msg in stale:
        try:
            resp = requests.get(
                f"https://graph.facebook.com/{settings.wa_api_version}/{msg.media_id}",
                headers=headers, timeout=10
            )
            if resp.status_code == 200:
                url = resp.json().get("url")
                if url:
                    frappe.db.set_value("WA Message", msg.name, "media_url", url)
        except Exception:
            pass

    frappe.db.commit()



#=====================company policy==========================

# tasks.py
import frappe
from frappe.utils import today, date_diff, add_days


def send_policy_acknowledgement_reminders():
    """Daily job: remind employees who haven't acknowledged within the reminder interval."""
    pending_acks = frappe.get_all(
        "Policy Acknowledgement",
        filters={"status": "Pending"},
        fields=["name", "policy", "policy_version", "employee", "reminder_count"]
    )

    for ack in pending_acks:
        policy = frappe.db.get_value(
            "Company Policy", ack.policy,
            ["title", "acknowledgement_deadline_days", "reminder_interval_days", "status"],
            as_dict=True
        )
        if not policy or policy.status != "Published":
            continue

        # Only remind up to deadline
        published_date = frappe.db.get_value(
            "Company Policy", ack.policy, "modified"
        )
        days_since = date_diff(today(), str(published_date)[:10])
        deadline_days = policy.acknowledgement_deadline_days or 7
        interval_days = policy.reminder_interval_days or 2

        if days_since > deadline_days:
            # Escalate to department head / HR
            _escalate_overdue_ack(ack, policy)
            continue

        # Check if it's time to send another reminder
        last_reminder = frappe.db.get_value(
            "Policy Reminder Log",
            {"policy": ack.policy, "employee": ack.employee},
            "sent_on",
            order_by="sent_on desc"
        )
        if last_reminder:
            days_since_last = date_diff(today(), str(last_reminder)[:10])
            if days_since_last < interval_days:
                continue

        _send_reminder(ack, policy)
        frappe.get_doc({
            "doctype":        "Policy Reminder Log",
            "policy":         ack.policy,
            "employee":       ack.employee,
            "sent_on":        frappe.utils.now_datetime(),
            "reminder_count": (ack.reminder_count or 0) + 1,
        }).insert(ignore_permissions=True)

        frappe.db.set_value("Policy Acknowledgement", ack.name,
                            "reminder_count", (ack.reminder_count or 0) + 1)

    frappe.db.commit()


def expire_overdue_policies():
    """Daily job: auto-retire policies past their expiry date."""
    expired = frappe.get_all(
        "Company Policy",
        filters={
            "status": "Published",
            "expiry_date": ["<", today()]
        },
        fields=["name", "title"]
    )
    for pol in expired:
        frappe.db.set_value("Company Policy", pol.name, "status", "Retired")
        frappe.logger().info(f"Policy auto-retired: {pol.title}")

    if expired:
        frappe.db.commit()


def _send_reminder(ack, policy):
    user_email = frappe.db.get_value("Employee", ack.employee, "user_id")
    if not user_email:
        return
    portal_link = frappe.utils.get_url(
        f"/policy-acknowledgement?policy={ack.policy}&employee={ack.employee}"
    )
    frappe.sendmail(
        recipients=[user_email],
        subject=f"Reminder: Please acknowledge — {policy.title}",
        message=f"""
            <p>This is a reminder to acknowledge the policy <strong>{policy.title}</strong>.</p>
            <p><a href="{portal_link}">Acknowledge now</a></p>
        """,
        now=False  # Queue, don't block the scheduler
    )


def _escalate_overdue_ack(ack, policy):
    """Notify HR Manager when an employee is past the acknowledgement deadline."""
    hr_users = frappe.get_all(
        "Has Role",
        filters={"role": "HR Manager", "parenttype": "User"},
        fields=["parent"]
    )
    recipients = [r.parent for r in hr_users if r.parent != "Administrator"]
    if not recipients:
        return

    emp_name = frappe.db.get_value("Employee", ack.employee, "employee_name")
    frappe.sendmail(
        recipients=recipients,
        subject=f"Overdue Acknowledgement: {emp_name} — {policy.title}",
        message=f"""
            <p><strong>{emp_name}</strong> has not acknowledged 
            <strong>{policy.title}</strong> and is past the deadline.</p>
            <p>Please follow up directly.</p>
        """,
        now=False
    )
    
#================HANDOVER NOTE==========================

# tasks.py (add to existing file)

def escalate_overdue_handover_tasks():
    """
    Daily job: escalate Critical/High tasks that are past their due date
    and still Pending or In Progress.
    """
    from frappe.utils import today

    overdue = frappe.db.sql("""
        SELECT ht.name, ht.task_description, ht.acting_officer,
               ht.priority, ht.due_date, hn.name AS handover,
               hn.employee, hn.employee_name, hn.supervisor
        FROM   `tabHandover Task` ht
        JOIN   `tabHandover Note` hn ON hn.name = ht.parent
        WHERE  ht.status    IN ('Pending', 'In Progress')
          AND  ht.priority  IN ('Critical', 'High')
          AND  ht.due_date  <  %s
          AND  hn.status    =  'Active'
    """, today(), as_dict=True)

    for task in overdue:
        frappe.db.set_value("Handover Task", task.name, "status", "Escalated")

        # Notify the supervisor
        sup_user = frappe.db.get_value("Employee", task.supervisor, "user_id")
        if sup_user:
            frappe.sendmail(
                recipients=[sup_user],
                subject=f"Escalation: Overdue handover task — {task.employee_name}",
                message=f"""
                    <p>The following handover task is overdue and has been escalated:</p>
                    <ul>
                      <li><strong>Task:</strong> {task.task_description}</li>
                      <li><strong>Priority:</strong> {task.priority}</li>
                      <li><strong>Due Date:</strong> {task.due_date}</li>
                      <li><strong>Acting Officer:</strong> {task.acting_officer}</li>
                    </ul>
                    <p><a href="{frappe.utils.get_url(f'/app/handover-note/{task.handover}')}">
                    View Handover Note</a></p>
                """,
                now=False
            )

    if overdue:
        frappe.db.commit()
        frappe.logger().info(f"[Ecclesia] {len(overdue)} handover tasks escalated.")
        


#================MAIL HUB=====================

# ─────────────────────────────────────────────
# MAILVAULT — paste these into ecclesia/tasks.py
# hooks.py references:
#   "ecclesia.tasks.sync_all_accounts"
#   "ecclesia.tasks.push_unread_counts"
# ─────────────────────────────────────────────

import frappe
from frappe.utils import now_datetime
from email.utils import parseaddr


def sync_all_accounts():
    """
    Enqueue Frappe's email fetcher for all enabled incoming accounts.
    Runs every 5 minutes via cron scheduler.

    hooks.py:
        scheduler_events = {
            "cron": {
                "*/5 * * * *": ["ecclesia.tasks.sync_all_accounts"],
            },
        }
    """
    accounts = frappe.get_all(
        "Email Account",
        filters={"enable_incoming": 1, "awaiting_password": 0},
        pluck="name",
    )

    for account in accounts:
        try:
            frappe.enqueue(
                "frappe.email.receive.fetch_emails",
                email_account=account,
                now=False,
                queue="short",
            )
        except Exception as e:
            frappe.logger().warning(
                f"[MailVault] Could not enqueue sync for {account}: {e}"
            )

    if accounts:
        frappe.logger().info(
            f"[MailVault] Queued email sync for {len(accounts)} account(s)"
        )


def push_unread_counts():
    """
    Push inbox unread counts to all connected desk users via socket.io.
    Runs every 60 seconds (the 'all' scheduler event).

    hooks.py:
        scheduler_events = {
            "all": ["ecclesia.tasks.push_unread_counts"],
        }
    """
    accounts = frappe.get_all(
        "Email Account",
        filters={"enable_incoming": 1, "awaiting_password": 0},
        pluck="name",
    )
    if not accounts:
        return

    try:
        sessions = frappe.db.sql(
            """
            SELECT DISTINCT user
            FROM `tabSessions`
            WHERE status = 'Active'
              AND user != 'Guest'
            """,
            as_dict=True,
        )
    except Exception:
        return

    for session in sessions:
        user = session.get("user")
        if not user:
            continue
        try:
            unread = frappe.db.count(
                "Communication",
                filters={
                    "communication_medium": "Email",
                    "sent_or_received": "Received",
                    "read_by_current_user": 0,
                    "email_account": ["in", accounts],
                    "status": ["not in", ["Spam", "Trash", "Archived"]],
                },
            )
            frappe.publish_realtime(
                event="mail_vault_counts",
                message={
                    "inbox_unread": unread,
                    "timestamp": str(now_datetime()),
                },
                user=user,
            )
        except Exception as e:
            frappe.logger().warning(
                f"[MailVault] push_unread_counts failed for {user}: {e}"
            )


# ─────────────────────────────────────────────
# DOCUMENT EVENT HANDLERS
# Also paste these; update hooks.py doc_events:
#
#   doc_events = {
#       "Communication": {
#           "after_insert": "ecclesia.tasks.on_communication_insert",
#           "on_update":    "ecclesia.tasks.on_communication_update",
#       }
#   }
# ─────────────────────────────────────────────

def on_communication_insert(doc, method=None):
    """Push realtime 'new_email' event when an inbound email arrives."""
    if doc.communication_medium != "Email":
        return
    if doc.sent_or_received != "Received":
        return
    if not doc.email_account:
        return

    name, email = parseaddr(doc.sender or "")
    sender_name = name or (email.split("@")[0] if email else "Unknown")

    frappe.publish_realtime(
        event="new_email",
        message={
            "name":              doc.name,
            "subject":           doc.subject or "(No Subject)",
            "sender":            doc.sender or "",
            "sender_name":       sender_name,
            "sender_email":      email,
            "email_account":     doc.email_account,
            "communication_date": str(doc.communication_date),
        },
    )


def on_communication_update(doc, method=None):
    """Notify clients when a Communication status changes."""
    if doc.communication_medium != "Email":
        return
    frappe.publish_realtime(
        event="email_sync_complete",
        message={"new_count": 0, "updated": True},
    )
    
    
# ecclesia/tasks.py
import frappe
from frappe.utils import today, date_diff, add_days, getdate, get_url


# ══════════════════════════════════════════════════════════════════════
# Doc event hooks (module-level callables for hooks.py doc_events)
# ══════════════════════════════════════════════════════════════════════

def on_employee_update(doc, method):
    """
    doc_events hook for Employee.on_update.
    Triggers leave policy assignment prompt when status → Active.
    """
    if doc.status != "Active":
        return

    prev = doc.get_doc_before_save()
    if prev and prev.status == "Active":
        return  # Already active — not a new transition

    from ecclesia.api.leave_policy import get_policy_for_employee

    policy = get_policy_for_employee(doc)
    if not policy:
        frappe.logger().info(
            f"[Ecclesia] No leave policy matched for {doc.employee_name} "
            f"(gender={doc.gender})"
        )
        return

    year = getdate(today()).year
    existing = frappe.db.exists("Leave Policy Assignment", {
        "employee":       doc.name,
        "effective_from": ["between", [
            f"{year}-01-01", f"{year}-12-31"
        ]],
    })
    if existing:
        return

    frappe.db.set_value(
        "Employee", doc.name,
        "custom_pending_leave_policy_assignment", 1
    )
    frappe.db.commit()
    

def on_employee_update(doc, method):
    """
    Frappe doc_events entry point for Employee.on_update.

    hooks.py references this as:
        "Employee": {
            "on_update": "ecclesia.tasks.on_employee_update"
        }

    Fires on every Employee save. Only acts when the status field
    transitions to Active for the first time — sets a flag that
    triggers the leave policy assignment dialog on next form load.

    Cannot live in doctype/employee/employee.py because Employee
    is a standard ERPNext DocType — custom apps must not create
    that folder.
    """
    if doc.status != "Active":
        return

    # Only act on a genuine Active transition, not every save
    prev = doc.get_doc_before_save()
    if prev and prev.status == "Active":
        return

    from ecclesia.api.leave_policy import get_policy_for_employee
    from frappe.utils import getdate, today

    policy = get_policy_for_employee(doc)
    if not policy:
        frappe.logger().info(
            f"[Ecclesia] No leave policy matched for {doc.employee_name} "
            f"(gender={doc.gender}) — skipping assignment prompt."
        )
        return

    year = getdate(today()).year
    existing = frappe.db.exists("Leave Policy Assignment", {
        "employee":       doc.name,
        "effective_from": ["between", [
            f"{year}-01-01",
            f"{year}-12-31"
        ]],
    })
    if existing:
        return

    frappe.db.set_value(
        "Employee", doc.name,
        "custom_pending_leave_policy_assignment", 1
    )
    frappe.db.commit()
    
    
    
# ══════════════════════════════════════════════════════════════════════
# Policy module
# ══════════════════════════════════════════════════════════════════════

def send_policy_acknowledgement_reminders():
    """
    Daily: remind employees with pending acknowledgements and escalate
    those past their deadline to HR.
    """
    pending_acks = frappe.get_all(
        "Policy Acknowledgement",
        filters={"status": "Pending"},
        fields=["name", "policy", "policy_version",
                "employee", "reminder_count"]
    )

    for ack in pending_acks:
        policy = frappe.db.get_value(
            "Company Policy", ack.policy,
            ["title", "acknowledgement_deadline_days",
             "reminder_interval_days", "status"],
            as_dict=True
        )
        if not policy or policy.status != "Published":
            continue

        published_date = frappe.db.get_value(
            "Company Policy", ack.policy, "modified"
        )
        days_since    = date_diff(today(), str(published_date)[:10])
        deadline_days = policy.acknowledgement_deadline_days or 7
        interval_days = policy.reminder_interval_days or 2

        if days_since > deadline_days:
            _escalate_overdue_ack(ack, policy)
            continue

        last_reminder = frappe.db.get_value(
            "Policy Reminder Log",
            {"policy": ack.policy, "employee": ack.employee},
            "sent_on",
            order_by="sent_on desc"
        )
        if last_reminder:
            if date_diff(today(), str(last_reminder)[:10]) < interval_days:
                continue

        _send_policy_reminder(ack, policy)

        frappe.get_doc({
            "doctype":        "Policy Reminder Log",
            "policy":         ack.policy,
            "employee":       ack.employee,
            "sent_on":        frappe.utils.now_datetime(),
            "reminder_count": (ack.reminder_count or 0) + 1,
        }).insert(ignore_permissions=True)

        frappe.db.set_value(
            "Policy Acknowledgement", ack.name,
            "reminder_count", (ack.reminder_count or 0) + 1
        )

    frappe.db.commit()


def expire_overdue_policies():
    """Daily: auto-retire policies past their expiry date."""
    expired = frappe.get_all(
        "Company Policy",
        filters={"status": "Published", "expiry_date": ["<", today()]},
        fields=["name", "title"]
    )
    for pol in expired:
        frappe.db.set_value("Company Policy", pol.name, "status", "Retired")
        frappe.logger().info(f"[Ecclesia] Policy auto-retired: {pol.title}")
    if expired:
        frappe.db.commit()


def _send_policy_reminder(ack, policy):
    user_email = frappe.db.get_value("Employee", ack.employee, "user_id")
    if not user_email:
        return
    portal_link = get_url(
        f"/policy-acknowledgement?policy={ack.policy}"
        f"&employee={ack.employee}"
    )
    frappe.sendmail(
        recipients=[user_email],
        subject=f"Reminder: Please acknowledge — {policy.title}",
        message=f"""
            <div style="font-family:sans-serif;max-width:600px;padding:24px">
                <p>This is a reminder to acknowledge the policy
                <strong>{policy.title}</strong>.</p>
                <p><a href="{portal_link}"
                      style="padding:10px 20px;background:#534AB7;color:#fff;
                             border-radius:6px;text-decoration:none">
                    Acknowledge now
                </a></p>
            </div>
        """,
        now=False
    )


def _escalate_overdue_ack(ack, policy):
    hr_users = frappe.db.sql_list("""
        SELECT parent FROM `tabHas Role`
        WHERE  role = 'HR Manager' AND parenttype = 'User'
    """)
    recipients = [r for r in hr_users if r != "Administrator"]
    if not recipients:
        return
    emp_name = frappe.db.get_value("Employee", ack.employee, "employee_name")
    frappe.sendmail(
        recipients=recipients,
        subject=f"Overdue Acknowledgement: {emp_name} — {policy.title}",
        message=f"""
            <div style="font-family:sans-serif;max-width:600px;padding:24px">
                <p><strong>{emp_name}</strong> has not acknowledged
                <strong>{policy.title}</strong> and is past the deadline.
                Please follow up directly.</p>
            </div>
        """,
        now=False
    )


# ══════════════════════════════════════════════════════════════════════
# Handover module
# ══════════════════════════════════════════════════════════════════════

def escalate_overdue_handover_tasks():
    """
    Daily: escalate Critical/High handover tasks past their due date
    and notify the supervisor.
    """
    overdue = frappe.db.sql("""
        SELECT ht.name, ht.task_description, ht.acting_officer,
               ht.priority, ht.due_date,
               hn.name        AS handover,
               hn.employee,
               hn.employee_name,
               hn.supervisor
        FROM   `tabHandover Task` ht
        JOIN   `tabHandover Note` hn ON hn.name = ht.parent
        WHERE  ht.status   IN ('Pending', 'In Progress')
          AND  ht.priority IN ('Critical', 'High')
          AND  ht.due_date  < %s
          AND  hn.status    = 'Active'
    """, today(), as_dict=True)

    for task in overdue:
        frappe.db.set_value("Handover Task", task.name, "status", "Escalated")
        sup_user = frappe.db.get_value("Employee", task.supervisor, "user_id")
        if sup_user:
            frappe.sendmail(
                recipients=[sup_user],
                subject=(
                    f"Escalation: Overdue handover task — {task.employee_name}"
                ),
                message=f"""
                    <div style="font-family:sans-serif;max-width:600px;padding:24px">
                        <p>The following handover task is overdue:</p>
                        <ul style="font-size:13px">
                            <li><strong>Task:</strong> {task.task_description}</li>
                            <li><strong>Priority:</strong> {task.priority}</li>
                            <li><strong>Due:</strong> {task.due_date}</li>
                            <li><strong>Acting Officer:</strong>
                                {task.acting_officer}</li>
                        </ul>
                        <p><a href="{get_url(
                            f'/app/handover-note/{task.handover}'
                        )}">View Handover Note</a></p>
                    </div>
                """,
                now=False
            )

    if overdue:
        frappe.db.commit()
        frappe.logger().info(
            f"[Ecclesia] {len(overdue)} handover task(s) escalated."
        )


# ══════════════════════════════════════════════════════════════════════
# Performance module
# ══════════════════════════════════════════════════════════════════════

def performance_cycle_deadline_reminders():
    """
    Daily: remind employees, peers, and managers of approaching
    phase deadlines (at 7, 3, and 1 day intervals).
    """
    active_cycles = frappe.get_all(
        "Performance Cycle",
        filters={"status": ["not in", ("Draft", "Closed", "Results Released")],
                 "docstatus": 1},
        fields=[
            "name", "title", "status",
            "goal_setting_deadline", "self_appraisal_deadline",
            "peer_review_deadline", "manager_review_deadline",
            "calibration_deadline",
        ]
    )

    deadline_field_map = {
        "Goal Setting":   "goal_setting_deadline",
        "Self Appraisal": "self_appraisal_deadline",
        "Peer Review":    "peer_review_deadline",
        "Manager Review": "manager_review_deadline",
        "Calibration":    "calibration_deadline",
    }

    for cycle in active_cycles:
        field = deadline_field_map.get(cycle.status)
        if not field:
            continue
        deadline = cycle.get(field)
        if not deadline:
            continue
        days_left = int(date_diff(deadline, today()))
        if days_left not in (7, 3, 1):
            continue
        _send_phase_reminders(cycle, days_left)


def _send_phase_reminders(cycle, days_left):
    pending = frappe.get_all(
        "Employee Performance Record",
        filters={"cycle": cycle.name},
        fields=["employee"]
    )
    for rec in pending:
        user = frappe.db.get_value("Employee", rec.employee, "user_id")
        if not user:
            continue
        frappe.sendmail(
            recipients=[user],
            subject=(
                f"Reminder: {cycle.status} closes in {days_left} day(s)"
                f" — {cycle.title}"
            ),
            message=f"""
                <div style="font-family:sans-serif;max-width:600px;padding:24px">
                    <p>The <strong>{cycle.status}</strong> phase for
                    <strong>{cycle.title}</strong> closes in
                    <strong>{days_left} day(s)</strong>.
                    Please complete your submission before the deadline.</p>
                    <p><a href="{get_url('/app/employee-performance-record')}">
                        Open your performance record
                    </a></p>
                </div>
            """,
            now=False
        )


def escalate_pending_peer_reviews():
    """
    Weekly: remind reviewers with pending requests and auto-decline
    stale requests from cycles that have moved past Peer Review.
    """
    # Auto-decline orphaned requests
    closed_cycles = frappe.db.sql_list("""
        SELECT name FROM `tabPerformance Cycle`
        WHERE  status NOT IN (
                   'Draft', 'Goal Setting', 'Self Appraisal', 'Peer Review'
               )
          AND  docstatus = 1
    """)

    stale_count = 0
    if closed_cycles:
        stale = frappe.get_all(
            "Peer Review Request",
            filters={
                "cycle":  ["in", closed_cycles],
                "status": ["in", ("Pending", "In Progress")],
            },
            fields=["name"]
        )
        for r in stale:
            frappe.db.set_value(
                "Peer Review Request", r.name, "status", "Declined"
            )
        stale_count = len(stale)
        if stale:
            frappe.db.commit()

    # Remind active reviewers
    active_cycles = frappe.db.sql_list("""
        SELECT name FROM `tabPerformance Cycle`
        WHERE  status = 'Peer Review' AND docstatus = 1
    """)
    if not active_cycles:
        frappe.logger().info(
            f"[Ecclesia] escalate_pending_peer_reviews: "
            f"auto-declined {stale_count} stale request(s), "
            f"no active cycles."
        )
        return

    pending = frappe.db.sql("""
        SELECT
            prr.name,
            prr.reviewer,
            prr.reviewee_name,
            prr.cycle,
            pc.title                AS cycle_title,
            pc.peer_review_deadline AS deadline,
            emp.user_id             AS reviewer_user
        FROM   `tabPeer Review Request` prr
        JOIN   `tabPerformance Cycle`   pc  ON pc.name  = prr.cycle
        JOIN   `tabEmployee`            emp ON emp.name = prr.reviewer
        WHERE  prr.cycle  IN %(cycles)s
          AND  prr.status IN ('Pending', 'In Progress')
          AND  emp.user_id IS NOT NULL
    """, {"cycles": active_cycles}, as_dict=True)

    from collections import defaultdict
    by_reviewer = defaultdict(list)
    for row in pending:
        by_reviewer[row.reviewer].append(row)

    for reviewer_emp, requests in by_reviewer.items():
        user        = requests[0].reviewer_user
        cycle_title = requests[0].cycle_title
        deadline    = requests[0].deadline
        days_left   = int(date_diff(deadline, today())) if deadline else None

        if days_left is not None and days_left <= 0:
            urgency = (
                '<p style="color:#A32D2D;font-weight:500">'
                'The peer review deadline has passed. '
                'Please complete immediately.</p>'
            )
        elif days_left is not None and days_left <= 3:
            urgency = (
                f'<p style="color:#854F0B;font-weight:500">'
                f'Deadline in {days_left} day(s).</p>'
            )
        else:
            urgency = (
                f"<p>Deadline: <strong>{deadline}</strong>"
                f" ({days_left} days remaining).</p>"
                if days_left else ""
            )

        rows_html = "".join(
            f"<li><strong>{r.reviewee_name}</strong> — {r.cycle_title}</li>"
            for r in requests
        )

        frappe.sendmail(
            recipients=[user],
            subject=(
                f"Reminder: {len(requests)} peer review(s) pending"
                f" — {cycle_title}"
            ),
            message=f"""
                <div style="font-family:sans-serif;max-width:600px;padding:24px">
                    <p>You have <strong>{len(requests)}</strong> pending peer
                    review request(s) for <strong>{cycle_title}</strong>.</p>
                    {urgency}
                    <ul style="font-size:13px">{rows_html}</ul>
                    <p>
                        <a href="{get_url(
                            '/app/peer-review-request?status=Pending'
                        )}"
                           style="padding:10px 20px;background:#534AB7;
                                  color:#fff;border-radius:6px;
                                  text-decoration:none;font-weight:500">
                            Complete your reviews
                        </a>
                    </p>
                </div>
            """,
            now=False
        )

    frappe.logger().info(
        f"[Ecclesia] escalate_pending_peer_reviews: "
        f"reminded {len(by_reviewer)} reviewer(s), "
        f"auto-declined {stale_count} stale request(s)."
    )


# ══════════════════════════════════════════════════════════════════════
# Leave policy module
# ══════════════════════════════════════════════════════════════════════

def assign_leave_policies_new_year():
    """
    Cron: midnight on January 1.
    Assigns gender-appropriate leave policies to all active employees
    for the new year, skipping those already assigned.
    """
    from ecclesia.api.leave_policy import (
        get_policy_for_employee,
        create_leave_policy_assignment,
        log_assignment,
    )

    current_year = getdate(today()).year
    frappe.logger().info(
        f"[Ecclesia] New Year leave policy assignment started for {current_year}"
    )

    employees = frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["name", "employee_name", "gender", "department",
                "designation", "employment_type", "grade"]
    )

    results = {"assigned": 0, "skipped": 0, "failed": 0, "errors": []}

    for emp in employees:
        try:
            policy = get_policy_for_employee(emp)
            if not policy:
                results["skipped"] += 1
                continue

            existing = frappe.db.exists("Leave Policy Assignment", {
                "employee":       emp.name,
                "leave_policy":   policy,
                "effective_from": ["between", [
                    f"{current_year}-01-01",
                    f"{current_year}-12-31"
                ]],
            })
            if existing:
                results["skipped"] += 1
                continue

            create_leave_policy_assignment(
                employee=emp.name,
                policy=policy,
                effective_from=f"{current_year}-01-01",
                effective_to=f"{current_year}-12-31",
                carry_forward=1,
            )
            log_assignment(emp.name, policy, "New Year Scheduler", current_year)
            results["assigned"] += 1

        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"{emp.employee_name}: {str(e)}")
            frappe.log_error(
                f"Leave policy assignment failed for {emp.employee_name}: {e}",
                "New Year Leave Policy"
            )

    frappe.db.commit()
    _notify_hr_assignment_summary(results, current_year)
    frappe.logger().info(
        f"[Ecclesia] New Year assignment — "
        f"assigned={results['assigned']}, "
        f"skipped={results['skipped']}, "
        f"failed={results['failed']}"
    )


def _notify_hr_assignment_summary(results, year):
    hr_users = frappe.db.sql_list("""
        SELECT parent FROM `tabHas Role`
        WHERE  role = 'HR Manager' AND parenttype = 'User'
    """)
    if not hr_users:
        return

    error_html = ""
    if results["errors"]:
        rows = "".join(f"<li>{e}</li>" for e in results["errors"])
        error_html = (
            f"<p><strong>Errors:</strong><ul>{rows}</ul></p>"
        )

    frappe.sendmail(
        recipients=hr_users,
        subject=f"Leave Policy Assignment — {year} Batch Complete",
        message=f"""
            <div style="font-family:sans-serif;max-width:600px;padding:24px">
                <h3 style="margin:0 0 16px">
                    New Year Leave Policy Assignment — {year}
                </h3>
                <table style="width:100%;font-size:14px;border-collapse:collapse">
                    <tr>
                        <td style="padding:8px 0;color:#555">Assigned</td>
                        <td style="padding:8px 0;font-weight:500;color:#1D9E75">
                            {results['assigned']}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:8px 0;color:#555">
                            Skipped (already assigned)
                        </td>
                        <td style="padding:8px 0;font-weight:500">
                            {results['skipped']}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:8px 0;color:#555">Failed</td>
                        <td style="padding:8px 0;font-weight:500;
                            color:{'#E24B4A' if results['failed'] else 'inherit'}">
                            {results['failed']}
                        </td>
                    </tr>
                </table>
                {error_html}
            </div>
        """,
        now=False
    )


# ══════════════════════════════════════════════════════════════════════
# Loan module
# ══════════════════════════════════════════════════════════════════════

def mark_overdue_loan_installments():
    """
    Daily: mark installments past their due date as Overdue
    and notify HR and the employee.
    """
    overdue = frappe.db.sql("""
        SELECT
            rs.name,
            rs.parent           AS loan,
            rs.payment_date,
            rs.monthly_amount,
            rs.installment_no,
            ela.employee,
            ela.employee_name,
            ela.loan_type
        FROM   `tabLoan Repayment Schedule` rs
        JOIN   `tabEmployee Loan Application` ela ON ela.name = rs.parent
        WHERE  rs.status       = 'Pending'
          AND  rs.payment_date < %s
          AND  ela.status      IN ('Disbursed', 'Active')
    """, today(), as_dict=True)

    for row in overdue:
        frappe.db.set_value(
            "Loan Repayment Schedule", row.name, "status", "Overdue"
        )
        _notify_overdue_installment(row)

    if overdue:
        frappe.db.commit()
        frappe.logger().info(
            f"[Ecclesia] {len(overdue)} loan installment(s) marked Overdue."
        )


def _notify_overdue_installment(row):
    user = frappe.db.get_value("Employee", row.employee, "user_id")
    recipients = []
    if user:
        recipients.append(user)

    hr_users = frappe.db.sql_list("""
        SELECT parent FROM `tabHas Role`
        WHERE  role       = 'HR Manager'
          AND  parenttype = 'User'
    """)
    recipients += hr_users

    if not recipients:
        return

    frappe.sendmail(
        recipients=list(set(recipients)),
        subject=f"Overdue loan installment — {row.employee_name}",
        message=f"""
            <div style="font-family:sans-serif;max-width:600px;padding:24px">
                <p>Loan installment <strong>#{row.installment_no}</strong>
                for <strong>{row.employee_name}</strong>
                ({row.loan_type}) is overdue.</p>
                <table style="font-size:13px;width:100%;
                              border-collapse:collapse;margin:12px 0">
                    <tr>
                        <td style="padding:6px 0;color:#555">Due date</td>
                        <td style="font-weight:500">{row.payment_date}</td>
                    </tr>
                    <tr>
                        <td style="padding:6px 0;color:#555">Amount due</td>
                        <td style="font-weight:500">
                            ₦{row.monthly_amount:,.2f}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:6px 0;color:#555">Loan ref</td>
                        <td style="font-weight:500">{row.loan}</td>
                    </tr>
                </table>
                <p>
                    <a href="{get_url(
                        f'/app/employee-loan-application/{row.loan}'
                    )}"
                       style="display:inline-block;padding:10px 20px;
                              background:#534AB7;color:#fff;
                              border-radius:6px;text-decoration:none;
                              font-weight:500">
                        View Loan
                    </a>
                </p>
            </div>
        """,
        now=False
    )


def send_upcoming_loan_deduction_reminders():
    """
    Weekly: remind employees of their next deduction due within 7 days.
    """
    window_end = add_days(today(), 7)

    upcoming = frappe.db.sql("""
        SELECT
            rs.installment_no,
            rs.payment_date,
            rs.monthly_amount,
            rs.balance,
            ela.name            AS loan,
            ela.employee,
            ela.employee_name,
            ela.loan_type,
            ela.tenure_months,
            ela.installments_paid
        FROM   `tabLoan Repayment Schedule` rs
        JOIN   `tabEmployee Loan Application` ela ON ela.name = rs.parent
        WHERE  rs.status       = 'Pending'
          AND  rs.payment_date BETWEEN %s AND %s
          AND  ela.status      IN ('Disbursed', 'Active')
    """, (today(), window_end), as_dict=True)

    for row in upcoming:
        user = frappe.db.get_value("Employee", row.employee, "user_id")
        if not user:
            continue

        remaining = (row.tenure_months or 0) - (row.installments_paid or 0)

        frappe.sendmail(
            recipients=[user],
            subject=(
                f"Upcoming loan deduction — "
                f"₦{row.monthly_amount:,.2f} on {row.payment_date}"
            ),
            message=f"""
                <div style="font-family:sans-serif;max-width:600px;padding:24px">
                    <p>Dear {row.employee_name},</p>
                    <p>Your next loan deduction is due soon.</p>
                    <table style="font-size:13px;width:100%;
                                  border-collapse:collapse;margin:12px 0">
                        <tr>
                            <td style="padding:6px 0;color:#555">Loan type</td>
                            <td style="font-weight:500">{row.loan_type}</td>
                        </tr>
                        <tr>
                            <td style="padding:6px 0;color:#555">
                                Instalment #{row.installment_no}
                            </td>
                            <td style="font-weight:500">{row.payment_date}</td>
                        </tr>
                        <tr>
                            <td style="padding:6px 0;color:#555">Amount</td>
                            <td style="font-weight:500">
                                ₦{row.monthly_amount:,.2f}
                            </td>
                        </tr>
                        <tr>
                            <td style="padding:6px 0;color:#555">
                                Remaining balance
                            </td>
                            <td style="font-weight:500">
                                ₦{row.balance:,.2f}
                            </td>
                        </tr>
                        <tr>
                            <td style="padding:6px 0;color:#555">
                                Instalments left
                            </td>
                            <td style="font-weight:500">{remaining}</td>
                        </tr>
                    </table>
                    <p>
                        <a href="{get_url(
                            f'/app/employee-loan-application/{row.loan}'
                        )}"
                           style="display:inline-block;padding:10px 20px;
                                  background:#534AB7;color:#fff;
                                  border-radius:6px;text-decoration:none;
                                  font-weight:500">
                            View Loan Details
                        </a>
                    </p>
                </div>
            """,
            now=False
        )

    if upcoming:
        frappe.logger().info(
            f"[Ecclesia] Loan deduction reminders sent for "
            f"{len(upcoming)} upcoming instalment(s)."
        )
  
  
