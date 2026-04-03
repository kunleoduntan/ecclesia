# ecclesia/api/leave_policy.py
import frappe
from frappe.utils import today, getdate


# ── Policy resolution ────────────────────────────────────────────────

def get_policy_for_employee(emp) -> str | None:
    """
    Determine which Leave Policy applies to this employee.

    Resolution order (most specific wins):
      1. Gender + Employment Type match
      2. Gender + Grade match
      3. Gender only
      4. Default policy (no gender filter)
    """
    gender = emp.gender if isinstance(emp, dict) else getattr(emp, "gender", None)
    emp_type = emp.employment_type if isinstance(emp, dict) else getattr(emp, "employment_type", None)
    grade = emp.grade if isinstance(emp, dict) else getattr(emp, "grade", None)

    # Custom fields on Leave Policy: custom_gender, custom_employment_type, custom_grade
    # 1. Gender + Employment Type
    if gender and emp_type:
        policy = frappe.db.get_value("Leave Policy", {
            "custom_gender": gender,
            "custom_employment_type": emp_type,
            "disabled": 0,
        }, "name")
        if policy:
            return policy

    # 2. Gender + Grade
    if gender and grade:
        policy = frappe.db.get_value("Leave Policy", {
            "custom_gender": grade,
            "custom_grade": grade,
            "disabled": 0,
        }, "name")
        if policy:
            return policy

    # 3. Gender only
    if gender:
        policy = frappe.db.get_value("Leave Policy", {
            "custom_gender": gender,
            "disabled": 0,
        }, "name")
        if policy:
            return policy

    # 4. Default (no gender restriction)
    policy = frappe.db.get_value("Leave Policy", {
        "custom_gender": ["in", ("", None)],
        "custom_is_default": 1,
        "disabled": 0,
    }, "name")
    return policy


def create_leave_policy_assignment(
    employee: str,
    policy: str,
    effective_from: str,
    effective_to: str,
    carry_forward: int = 0,
) -> str:
    """
    Create a Leave Policy Assignment and trigger Leave Allocation.
    Returns the name of the created assignment.
    """
    lpa = frappe.get_doc({
        "doctype":       "Leave Policy Assignment",
        "employee":      employee,
        "leave_policy":  policy,
        "effective_from": effective_from,
        "effective_to":   effective_to,
        "carry_forward":  carry_forward,
    })
    lpa.insert(ignore_permissions=True)
    lpa.submit()

    # Frappe's built-in allocation method
    lpa.grant_leave_alloc_for_period()

    frappe.db.commit()
    return lpa.name


def log_assignment(employee: str, policy: str, source: str, year: int):
    """Write an audit entry to Leave Policy Assignment Log."""
    frappe.get_doc({
        "doctype":   "Leave Policy Assignment Log",
        "employee":  employee,
        "policy":    policy,
        "source":    source,
        "year":      year,
        "assigned_on": frappe.utils.now_datetime(),
        "assigned_by": frappe.session.user,
    }).insert(ignore_permissions=True)


# ── Whitelist endpoints ───────────────────────────────────────────────

@frappe.whitelist()
def assign_policy_for_new_employee(employee: str, confirmed: int = 0):
    """
    Called from the Employee JS confirmation dialog.
    confirmed=0  → dry run, returns proposed policy details for display.
    confirmed=1  → actually creates the assignment.
    """
    emp = frappe.get_doc("Employee", employee)

    if emp.status != "Active":
        frappe.throw(
            "Leave policy can only be assigned to Active employees.",
            title="Cannot Assign"
        )

    policy_name = get_policy_for_employee(emp)
    if not policy_name:
        return {
            "policy":       None,
            "policy_label": None,
            "message":      "No matching leave policy found for this employee's gender/type.",
        }

    policy = frappe.get_doc("Leave Policy", policy_name)
    leave_types = [
        {
            "leave_type":        lt.leave_type,
            "annual_allocation": lt.annual_allocation,
        }
        for lt in policy.leave_policy_details
    ]

    if not confirmed:
        return {
            "policy":       policy_name,
            "policy_label": policy.leave_policy_name or policy_name,
            "leave_types":  leave_types,
            "message":      "preview",
        }

    # Check for existing assignment this year
    year = getdate(today()).year
    existing = frappe.db.exists("Leave Policy Assignment", {
        "employee":     employee,
        "leave_policy": policy_name,
        "effective_from": ["between", [f"{year}-01-01", f"{year}-12-31"]],
    })
    if existing:
        return {
            "policy":   policy_name,
            "message":  "already_assigned",
            "existing": existing,
        }

    assignment = create_leave_policy_assignment(
        employee=employee,
        policy=policy_name,
        effective_from=today(),
        effective_to=f"{year}-12-31",
        carry_forward=0,
    )
    log_assignment(employee, policy_name, "New Employee", year)
    _notify_employee_assignment(emp, policy)

    return {
        "policy":     policy_name,
        "assignment": assignment,
        "message":    "assigned",
    }


@frappe.whitelist()
def manual_reassign(employee: str, policy: str, effective_from: str,
                    effective_to: str, carry_forward: int = 0):
    """
    HR-triggered manual reassignment with full audit trail.
    """
    if not frappe.has_permission("Leave Policy Assignment", "create"):
        frappe.throw("Insufficient permissions.", frappe.PermissionError)

    assignment = create_leave_policy_assignment(
        employee, policy, effective_from, effective_to, carry_forward
    )
    log_assignment(employee, policy, "Manual HR Reassignment",
                   getdate(effective_from).year)

    emp = frappe.get_doc("Employee", employee)
    pol = frappe.get_doc("Leave Policy", policy)
    _notify_employee_assignment(emp, pol)

    return {"assignment": assignment, "message": "assigned"}


def _notify_employee_assignment(emp, policy):
    user = frappe.db.get_value("Employee", emp.name, "user_id")
    if not user:
        return
    frappe.sendmail(
        recipients=[user],
        subject=f"Your leave policy has been assigned — {policy.leave_policy_name or policy.name}",
        message=f"""
            <div style="font-family:sans-serif;max-width:600px;padding:24px">
                <p>Dear {emp.employee_name},</p>
                <p>Your leave policy for this year has been set to
                <strong>{policy.leave_policy_name or policy.name}</strong>.</p>
                <p>Your leave allocations have been created and are ready to use.</p>
            </div>
        """,
        now=False
    )