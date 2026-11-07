import frappe
from frappe import _
from frappe.utils import get_url_to_form, getdate, today

SAVEPOINT = "employee_tax_computation_create"
SSA_SAVEPOINT = "employee_ssa_create"


# ======================================================================
# EMPLOYEE TAX COMPUTATION
# ======================================================================

def _create(emp):
    """Create a Draft Employee Tax Computation for an Employee doc.

    Only Active employees are considered.

    Returns a dict: {"status": "created" | "exists" | "skipped" | "failed", ...}
    Never raises.
    """
    if emp.status != "Active":
        return {"status": "skipped", "reason": _("Employee is not Active")}

    savepoint_set = False

    try:
        from erpnext.accounts.utils import get_fiscal_year

        fiscal_year = get_fiscal_year(today(), company=emp.company, verbose=0)[0]

        existing = frappe.db.exists(
            "Employee Tax Computation",
            {
                "employee": emp.name,
                "fiscal_year": fiscal_year,
                "docstatus": ["!=", 2],
            },
        )
        if existing:
            return {"status": "exists", "name": existing, "fiscal_year": fiscal_year}

        frappe.db.savepoint(SAVEPOINT)
        savepoint_set = True

        etc = frappe.get_doc(
            {
                "doctype": "Employee Tax Computation",
                "employee": emp.name,
                "fiscal_year": fiscal_year,
                "company": emp.company,
                "computation_date": today(),
                "tin": emp.get("tin"),
                "annual_gross_income": 0,
            }
        )
        etc.insert(ignore_permissions=True)

        return {"status": "created", "name": etc.name, "fiscal_year": etc.fiscal_year}

    except Exception as e:
        if savepoint_set:
            try:
                frappe.db.rollback(save_point=SAVEPOINT)
            except Exception:
                pass

        frappe.log_error(
            title=f"Auto Tax Computation failed: {emp.name}"[:140],
            message=frappe.get_traceback(),
        )
        return {"status": "failed", "error": str(e)}


def create_tax_computation(doc, method=None):
    """Employee after_insert hook.

    hooks.py:
        doc_events = {
            "Employee": {
                "after_insert": [
                    "ecclesia.employee_events.create_tax_computation",
                    "ecclesia.employee_events.create_salary_structure_assignment",
                ],
            },
        }
    """
    result = _create(doc)

    if result["status"] == "created":
        link = get_url_to_form("Employee Tax Computation", result["name"])
        frappe.msgprint(
            _(
                "Employee Tax Computation <a href='{0}'><b>{1}</b></a> "
                "(Draft, {2}) has been created for {3}.<br><br>"
                "<b>Next step:</b> open it and update the Annual Gross Income, "
                "Statutory Deductions and Benefits in Kind so that it reflects "
                "the employee's correct tax position."
            ).format(link, result["name"], result["fiscal_year"], frappe.bold(doc.employee_name or doc.name)),
            title=_("Tax Computation Created"),
            indicator="green",
        )

    elif result["status"] == "exists":
        frappe.msgprint(
            _("Employee Tax Computation {0} already exists for {1}.").format(
                frappe.bold(result["name"]), result["fiscal_year"]
            ),
            title=_("Tax Computation"),
            indicator="blue",
        )

    elif result["status"] == "skipped":
        return

    else:
        frappe.msgprint(
            _(
                "Employee {0} was created, but the Employee Tax Computation "
                "could not be created automatically. Please create it manually "
                "(see Error Log for details)."
            ).format(frappe.bold(doc.name)),
            title=_("Tax Computation Not Created"),
            indicator="orange",
        )


@frappe.whitelist()
def create_tax_computation_for(employee):
    """Called from the Employee list view (Check Missing Tax Computation dialog).

    Creates one Draft Employee Tax Computation and returns the result dict.
    No msgprint here, so the client can show its own progress and summary.
    """
    frappe.has_permission("Employee", "write", doc=employee, throw=True)
    emp = frappe.get_doc("Employee", employee)
    return _create(emp)


# ======================================================================
# SALARY STRUCTURE ASSIGNMENT
# ======================================================================

def _get_salary_structure(emp):
    """Pick the Salary Structure for a new employee.

    1. `salary_structure` field on Employee, if you have such a custom field and it is set
    2. the only active, submitted Salary Structure of the employee's company
    Returns None if it cannot be determined unambiguously.
    """
    structure = emp.get("salary_structure")
    if structure:
        return structure

    structures = frappe.get_all(
        "Salary Structure",
        filters={"docstatus": 1, "is_active": "Yes", "company": emp.company},
        pluck="name",
        limit=2,
    )
    return structures[0] if len(structures) == 1 else None


def _create_ssa(emp):
    """Create a Draft Salary Structure Assignment for an Employee doc.

    Only Active employees are considered.

    Returns a dict: {"status": "created" | "exists" | "skipped" | "no_structure" | "failed", ...}
    Never raises.
    """
    if emp.status != "Active":
        return {"status": "skipped"}

    savepoint_set = False

    try:
        existing = frappe.db.exists(
            "Salary Structure Assignment",
            {"employee": emp.name, "docstatus": ["!=", 2]},
        )
        if existing:
            return {"status": "exists", "name": existing}

        salary_structure = _get_salary_structure(emp)
        if not salary_structure:
            return {"status": "no_structure"}

        from_date = getdate(emp.date_of_joining) if emp.date_of_joining else getdate(today())

        frappe.db.savepoint(SSA_SAVEPOINT)
        savepoint_set = True

        ssa = frappe.get_doc(
            {
                "doctype": "Salary Structure Assignment",
                "employee": emp.name,
                "salary_structure": salary_structure,
                "company": emp.company,
                "from_date": from_date,
                "base": 0,
            }
        )
        ssa.insert(ignore_permissions=True)  # stays Draft (docstatus 0)

        return {"status": "created", "name": ssa.name, "salary_structure": salary_structure}

    except Exception as e:
        if savepoint_set:
            try:
                frappe.db.rollback(save_point=SSA_SAVEPOINT)
            except Exception:
                pass

        frappe.log_error(
            title=f"Auto Salary Structure Assignment failed: {emp.name}"[:140],
            message=frappe.get_traceback(),
        )
        return {"status": "failed", "error": str(e)}


def create_salary_structure_assignment(doc, method=None):
    """Employee after_insert hook: create a Draft Salary Structure Assignment."""
    result = _create_ssa(doc)

    if result["status"] == "created":
        link = get_url_to_form("Salary Structure Assignment", result["name"])
        frappe.msgprint(
            _(
                "Salary Structure Assignment <a href='{0}'><b>{1}</b></a> "
                "(Draft, {2}) has been created for {3}.<br><br>"
                "<b>Next step:</b> open it, confirm the Salary Structure and "
                "From Date, set the correct Base, then submit it."
            ).format(link, result["name"], result["salary_structure"], frappe.bold(doc.employee_name or doc.name)),
            title=_("Salary Structure Assignment Created"),
            indicator="green",
        )

    elif result["status"] == "exists":
        frappe.msgprint(
            _("Salary Structure Assignment {0} already exists for this employee.").format(
                frappe.bold(result["name"])
            ),
            title=_("Salary Structure Assignment"),
            indicator="blue",
        )

    elif result["status"] == "skipped":
        return

    elif result["status"] == "no_structure":
        frappe.msgprint(
            _(
                "Employee {0} was created, but no Salary Structure Assignment was "
                "created because a single active Salary Structure could not be "
                "determined for {1}. Please create the assignment manually."
            ).format(frappe.bold(doc.name), frappe.bold(doc.company)),
            title=_("Salary Structure Assignment Not Created"),
            indicator="orange",
        )

    else:
        frappe.msgprint(
            _(
                "Employee {0} was created, but the Salary Structure Assignment "
                "could not be created automatically. Please create it manually "
                "(see Error Log for details)."
            ).format(frappe.bold(doc.name)),
            title=_("Salary Structure Assignment Not Created"),
            indicator="orange",
        )