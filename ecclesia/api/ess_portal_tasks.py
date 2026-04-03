# Copyright (c) 2026, Ecclesia Enterprise — License: MIT
# ess_portal_tasks.py
"""
ESS Portal — Task Management + Notification Hooks

ESS Task is a custom doctype (ships with this app).
It is the central coordination layer — every module (eRequest, Loan,
Appraisal, Leave, Documents) creates tasks here so the employee has
one unified inbox on the ESS dashboard.

Fields on ESS Task (custom doctype, no standard doctype touched):
  assigned_to (Link→Employee), assigned_by (Link→Employee),
  assigned_by_name (Data), title (Data), description (Text Editor),
  status (Select: Open/In Progress/Completed/Cancelled),
  priority (Select: Critical/High/Medium/Low),
  due_date (Date), assigned_on (Date), completed_on (Datetime),
  task_category (Select: Onboarding/Compliance/HR/Document/Approval/Finance/Other),
  linked_doctype (Data), linked_docname (Dynamic Link)
"""

import frappe
from frappe.utils import now_datetime, today, add_days


# ─────────────────────────────────────────────────────────────────
# SECTION 1 — EMPLOYEE READ
# ─────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_my_tasks(status_filter: str = None, category: str = None):
    """
    Return all ESS Tasks for the current employee, grouped by status.

    Args:
        status_filter : "Open" | "In Progress" | "Completed" | "Overdue" | None
        category      : "Onboarding" | "Compliance" | "HR" | "Approval" | "Finance" | None

    Returns:
        { tasks: { overdue, open, in_progress, completed }, summary: {...} }
    """
    from datetime import date
    emp = _resolve_employee()
    if not emp:
        frappe.throw("No Employee record linked to your account.")

    filters = {"assigned_to": emp, "status": ["!=", "Cancelled"]}
    if category:
        filters["task_category"] = category
    if status_filter and status_filter not in ("All", "Overdue"):
        filters["status"] = status_filter

    tasks = frappe.get_all(
        "ESS Task",
        filters=filters,
        fields=[
            "name", "title", "description", "status", "priority",
            "due_date", "assigned_by", "assigned_by_name", "assigned_on",
            "completed_on", "linked_doctype", "linked_docname",
            "task_category",
        ],
        order_by="priority asc, due_date asc",
    )

    today_date = date.today()

    for t in tasks:
        if t.due_date and t.status not in ("Completed",):
            t["is_overdue"]     = t.due_date < today_date
            t["days_overdue"]   = (today_date - t.due_date).days if t["is_overdue"] else 0
            t["days_remaining"] = (t.due_date - today_date).days if not t["is_overdue"] else 0
        else:
            t["is_overdue"]     = False
            t["days_overdue"]   = 0
            t["days_remaining"] = None

    if status_filter == "Overdue":
        tasks = [t for t in tasks if t["is_overdue"]]

    grouped = {
        "overdue":     [t for t in tasks if t["is_overdue"]],
        "open":        [t for t in tasks if not t["is_overdue"] and t.status == "Open"],
        "in_progress": [t for t in tasks if t.status == "In Progress"],
        "completed":   [t for t in tasks if t.status == "Completed"],
    }

    return {
        "tasks": grouped,
        "summary": {
            "total":       len(tasks),
            "overdue":     len(grouped["overdue"]),
            "open":        len(grouped["open"]),
            "in_progress": len(grouped["in_progress"]),
            "completed":   len(grouped["completed"]),
        },
    }


@frappe.whitelist()
def update_task_status(task_name: str, new_status: str, notes: str = None):
    """
    Employee updates status of their own task.

    new_status: "Open" | "In Progress" | "Completed"
    """
    emp  = _resolve_employee()
    task = frappe.get_doc("ESS Task", task_name)

    if task.assigned_to != emp:
        frappe.throw("You can only update your own tasks.", frappe.PermissionError)

    allowed = ("Open", "In Progress", "Completed")
    if new_status not in allowed:
        frappe.throw(f"Status must be one of: {', '.join(allowed)}")

    task.status = new_status
    if new_status == "Completed":
        task.completed_on = now_datetime()

    task.save(ignore_permissions=True)

    if new_status == "Completed":
        _notify_task_assigner(task)

    return {"status": "success", "new_status": new_status}


# ─────────────────────────────────────────────────────────────────
# SECTION 2 — MANAGER / HR CREATE
# ─────────────────────────────────────────────────────────────────

@frappe.whitelist()
def create_task(
    assigned_to:    str,
    title:          str,
    description:    str   = None,
    priority:       str   = "Medium",
    due_date:       str   = None,
    task_category:  str   = "Other",
    linked_doctype: str   = None,
    linked_docname: str   = None,
    send_notification: bool = True,
):
    """Create and assign a task to an employee."""
    assigner     = _resolve_employee()
    assigner_name = frappe.db.get_value("Employee", assigner, "employee_name") if assigner \
                    else frappe.session.user

    task = frappe.get_doc({
        "doctype":          "ESS Task",
        "assigned_to":      assigned_to,
        "assigned_by":      assigner,
        "assigned_by_name": assigner_name,
        "title":            title,
        "description":      description,
        "priority":         priority,
        "due_date":         due_date,
        "task_category":    task_category,
        "linked_doctype":   linked_doctype,
        "linked_docname":   linked_docname,
        "status":           "Open",
        "assigned_on":      today(),
    })
    task.insert()

    if send_notification:
        _notify_new_task(task)

    return {"status": "success", "task": task.name}


@frappe.whitelist()
def bulk_create_tasks(employees: list, title: str, **kwargs):
    """Assign identical task to multiple employees at once."""
    results = []
    for emp in employees:
        r = create_task(assigned_to=emp, title=title, **kwargs)
        results.append({"employee": emp, "task": r.get("task")})
    return {"status": "success", "count": len(results), "tasks": results}


# ─────────────────────────────────────────────────────────────────
# SECTION 3 — PERMISSION GUARDS
# ─────────────────────────────────────────────────────────────────

def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user
    privileged = {"HR Manager", "HR User", "System Manager"}
    if set(frappe.get_roles(user)) & privileged:
        return ""
    emp = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if not emp:
        return "1=0"
    return f"`tabESS Task`.`assigned_to` = {frappe.db.escape(emp)}"


def has_permission(doc, ptype, user):
    emp = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if doc.assigned_to == emp:
        return True
    privileged = {"HR Manager", "HR User", "System Manager"}
    return bool(set(frappe.get_roles(user)) & privileged)


# ─────────────────────────────────────────────────────────────────
# SECTION 4 — DOC EVENT HOOKS (called from ess_portal_hooks.py)
# ─────────────────────────────────────────────────────────────────

def notify_leave_decision(doc, method=None):
    """Hook: Leave Application.on_update — notify employee of outcome."""
    if doc.status not in ("Approved", "Rejected"):
        return

    prev = frappe.db.get_value("Leave Application", doc.name, "status")
    if prev == doc.status:
        return  # No change

    emp_user = frappe.db.get_value("Employee", doc.employee, "user_id")
    if not emp_user:
        return

    icon  = "✅" if doc.status == "Approved" else "❌"
    dates = f"{doc.from_date} to {doc.to_date}"

    frappe.sendmail(
        recipients=[emp_user],
        subject=f"[ESS] Leave {doc.status}: {doc.leave_type} ({dates})",
        message=f"""
            <p>{icon} Your <strong>{doc.leave_type}</strong> leave application
            from <strong>{doc.from_date}</strong> to <strong>{doc.to_date}</strong>
            has been <strong>{doc.status.upper()}</strong>.</p>
            {"<p><strong>Reason:</strong> " + doc.reason + "</p>" if doc.get("reason") else ""}
            <p><a href="{frappe.utils.get_url()}/ess">View in ESS Portal →</a></p>
        """,
        now=False,
    )


def notify_expense_decision(doc, method=None):
    """Hook: Expense Claim.on_update — notify employee of approval/rejection."""
    if doc.approval_status not in ("Approved", "Rejected"):
        return

    prev = frappe.db.get_value("Expense Claim", doc.name, "approval_status")
    if prev == doc.approval_status:
        return

    emp_user = frappe.db.get_value("Employee", doc.employee, "user_id")
    if not emp_user:
        return

    frappe.sendmail(
        recipients=[emp_user],
        subject=f"[ESS] Expense Claim {doc.approval_status}: {doc.name}",
        message=f"""
            <p>Your expense claim <strong>{doc.name}</strong>
            (Total: {doc.grand_total:,.2f}) has been
            <strong>{doc.approval_status.upper()}</strong>.</p>
            <p><a href="{frappe.utils.get_url()}/ess">View in ESS Portal →</a></p>
        """,
        now=False,
    )


def create_appraisal_signature_task(doc, method=None):
    """
    Hook: Appraisal.on_submit
    When HR submits an appraisal, create a high-priority ESS Task for the
    employee to review and digitally sign it.
    """
    emp = doc.employee
    if not emp:
        return

    # Due in 7 days
    due = add_days(today(), 7)

    try:
        frappe.get_doc({
            "doctype":        "ESS Task",
            "assigned_to":    emp,
            "assigned_by_name": "HR System",
            "title":          f"Sign Performance Appraisal — {doc.appraisal_template or doc.name}",
            "task_category":  "HR",
            "priority":       "High",
            "status":         "Open",
            "due_date":       due,
            "linked_doctype": "Appraisal",
            "linked_docname": doc.name,
            "assigned_on":    today(),
        }).insert(ignore_permissions=True)
    except Exception as e:
        frappe.logger().warning(f"[ESS Tasks] Could not create appraisal task: {e}")


def get_employee_dashboard_data(app_name):
    """
    Hook: Employee doctype dashboard — adds ESS links panel.
    Registered in hooks.py override_doctype_dashboards.
    """
    return {
        "fieldname": "employee",
        "transactions": [
            {"label": "ESS", "items": ["ESS Task", "Employee Document"]},
        ],
    }


# ─────────────────────────────────────────────────────────────────
# SECTION 5 — SCHEDULED JOBS
# ─────────────────────────────────────────────────────────────────

def send_overdue_task_reminders():
    """Daily: email employees about overdue and due-soon tasks."""
    from datetime import date, timedelta

    today_date  = date.today()
    in_3_days   = today_date + timedelta(days=3)

    # Overdue
    overdue = frappe.get_all(
        "ESS Task",
        filters={"status": ["in", ["Open", "In Progress"]],
                 "due_date": ["<", today_date]},
        fields=["name", "title", "assigned_to", "due_date", "priority"],
    )

    # Due within 3 days
    due_soon = frappe.get_all(
        "ESS Task",
        filters={"status": ["in", ["Open", "In Progress"]],
                 "due_date": ["between", [today_date, in_3_days]]},
        fields=["name", "title", "assigned_to", "due_date", "priority"],
    )

    processed = set()

    for task in overdue + due_soon:
        emp_user = frappe.db.get_value("Employee", task.assigned_to, "user_id")
        if not emp_user or emp_user in processed:
            continue
        processed.add(emp_user)

        tag   = "OVERDUE" if task in overdue else f"DUE {task.due_date}"
        frappe.sendmail(
            recipients=[emp_user],
            subject=f"[ESS] [{tag}] Task: {task.title}",
            message=f"""
                <p>A task assigned to you requires attention:</p>
                <ul>
                    <li><strong>Task:</strong> {task.title}</li>
                    <li><strong>Due:</strong> {task.due_date}</li>
                    <li><strong>Priority:</strong> {task.priority}</li>
                </ul>
                <p><a href="{frappe.utils.get_url()}/ess">Open ESS Portal →</a></p>
            """,
            now=False,
        )


def archive_old_completed_tasks():
    """Monthly: soft-archive completed tasks older than 90 days."""
    from datetime import date, timedelta
    threshold = date.today() - timedelta(days=90)
    old = frappe.get_all(
        "ESS Task",
        filters={"status": "Completed", "completed_on": ["<", threshold]},
        pluck="name",
    )
    for name in old:
        frappe.db.set_value("ESS Task", name, "status", "Archived")

    if old:
        frappe.logger().info(f"[ESS Tasks] Archived {len(old)} old completed tasks.")


# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────

def _resolve_employee():
    return frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")


def _notify_new_task(task):
    emp_user = frappe.db.get_value("Employee", task.assigned_to, "user_id")
    if not emp_user:
        return
    frappe.sendmail(
        recipients=[emp_user],
        subject=f"[ESS] New Task: {task.title}",
        message=f"""
            <p>A new task has been assigned to you:</p>
            <ul>
                <li><strong>Task:</strong> {task.title}</li>
                <li><strong>Priority:</strong> {task.priority}</li>
                <li><strong>Category:</strong> {task.task_category}</li>
                {"<li><strong>Due Date:</strong> " + str(task.due_date) + "</li>" if task.due_date else ""}
                <li><strong>Assigned By:</strong> {task.assigned_by_name or "HR System"}</li>
            </ul>
            <p><a href="{frappe.utils.get_url()}/ess">Open ESS Portal →</a></p>
        """,
        now=False,
    )


def _notify_task_assigner(task):
    if not task.assigned_by:
        return
    assigner_user = frappe.db.get_value("Employee", task.assigned_by, "user_id")
    if not assigner_user:
        return
    emp_name = frappe.db.get_value("Employee", task.assigned_to, "employee_name")
    frappe.sendmail(
        recipients=[assigner_user],
        subject=f"[ESS] Task Completed: {task.title}",
        message=f"<p><strong>{emp_name}</strong> completed: <em>{task.title}</em> — {task.completed_on}</p>",
        now=False,
    )