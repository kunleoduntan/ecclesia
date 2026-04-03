# Copyright (c) 2025, General Biz Apps and contributors
# For license information, please see license.txt


import frappe
from frappe.utils import nowdate, getdate, add_days, add_months, get_first_day
from frappe import _

def send_pending_pension_reminder():
    """
    Daily task - Send reminder for pending pension contributions
    Runs daily to remind users to create pension contributions
    """
    
    # Get all submitted payroll entries from last 15 days
    from_date = add_days(nowdate(), -15)
    
    payroll_entries = frappe.db.sql("""
        SELECT 
            pe.name,
            pe.company,
            pe.start_date,
            pe.end_date,
            pe.posting_date,
            COUNT(ss.name) as total_slips,
            pe.owner
        FROM `tabPayroll Entry` pe
        LEFT JOIN `tabSalary Slip` ss 
            ON ss.payroll_entry = pe.name 
            AND ss.docstatus = 1
        WHERE pe.docstatus = 1
        AND pe.posting_date >= %s
        GROUP BY pe.name
        HAVING total_slips > 0
    """, from_date, as_dict=True)
    
    for pe in payroll_entries:
        # Check if pension contributions created
        period_month = getdate(pe.start_date).strftime("%B")
        period_year = getdate(pe.start_date).year
        
        pension_count = frappe.db.count(
            "Pension Contribution",
            {
                "company": pe.company,
                "period_month": period_month,
                "period_year": period_year,
                "docstatus": 1
            }
        )
        
        if pension_count == 0:
            # Send notification
            send_notification(
                recipients=[pe.owner],
                subject=f"Reminder: Create Pension Contributions for {period_month} {period_year}",
                message=f"""
                    <p>Dear User,</p>
                    <p>You have a payroll entry with {pe.total_slips} salary slips that needs pension contributions created.</p>
                    <p><strong>Payroll Entry:</strong> {pe.name}</p>
                    <p><strong>Period:</strong> {period_month} {period_year}</p>
                    <p><strong>Action Required:</strong> Please create pension contributions before remittance deadline.</p>
                    <p><a href="/app/payroll-entry/{pe.name}">Click here to open Payroll Entry</a></p>
                """
            )


def send_overdue_remittance_alert():
    """
    Daily task - Send alert for overdue pension remittances
    Remittances are due by 10th of following month
    """
    
    today = getdate(nowdate())
    
    # Get overdue remittance schedules
    overdue_schedules = frappe.db.sql("""
        SELECT 
            name,
            company,
            period_month,
            period_year,
            remittance_due_date,
            total_remittance_amount,
            status
        FROM `tabPension Remittance Schedule`
        WHERE docstatus = 1
        AND status NOT IN ('Paid', 'Confirmed')
        AND remittance_due_date < %s
    """, today, as_dict=True)
    
    if not overdue_schedules:
        return
    
    # Group by company
    company_overdue = {}
    for schedule in overdue_schedules:
        company = schedule.company
        if company not in company_overdue:
            company_overdue[company] = []
        company_overdue[company].append(schedule)
    
    # Send alerts
    for company, schedules in company_overdue.items():
        total_overdue_amount = sum(s.total_remittance_amount for s in schedules)
        
        # Get company admins
        recipients = get_company_pension_managers(company)
        
        message = f"""
            <div style="padding: 20px; background-color: #fff3cd; border-left: 4px solid #ffc107;">
                <h4 style="color: #856404;">⚠️ OVERDUE Pension Remittances</h4>
                <p><strong>Company:</strong> {company}</p>
                <p><strong>Overdue Schedules:</strong> {len(schedules)}</p>
                <p><strong>Total Amount:</strong> {frappe.format(total_overdue_amount, {'fieldtype': 'Currency'})}</p>
                <hr>
                <h5>Overdue Items:</h5>
                <ul>
        """
        
        for schedule in schedules:
            days_overdue = (today - getdate(schedule.remittance_due_date)).days
            message += f"""
                <li>
                    <strong>{schedule.period_month} {schedule.period_year}</strong> 
                    - {frappe.format(schedule.total_remittance_amount, {'fieldtype': 'Currency'})}
                    - <span style="color: red;">Overdue by {days_overdue} days</span>
                    - <a href="/app/pension-remittance-schedule/{schedule.name}">View Schedule</a>
                </li>
            """
        
        message += """
                </ul>
                <p style="margin-top: 15px;"><strong>Action Required:</strong> Please process payments immediately to avoid penalties.</p>
            </div>
        """
        
        send_notification(
            recipients=recipients,
            subject=f"URGENT: {len(schedules)} Overdue Pension Remittance(s) - {company}",
            message=message,
            priority=1
        )


def generate_monthly_pension_report():
    """
    Monthly task - Generate and send monthly pension report
    Runs on 1st of every month
    """
    
    # Get previous month
    first_day_this_month = get_first_day(nowdate())
    last_month = add_months(first_day_this_month, -1)
    period_month = last_month.strftime("%B")
    period_year = last_month.year
    
    # Get all companies with pension contributions
    companies = frappe.db.sql("""
        SELECT DISTINCT company
        FROM `tabPension Contribution`
        WHERE period_month = %s
        AND period_year = %s
        AND docstatus = 1
    """, (period_month, period_year), as_dict=True)
    
    for company_row in companies:
        company = company_row.company
        
        # Generate report
        report_data = generate_company_pension_report(company, period_month, period_year)
        
        if report_data:
            # Send to pension managers
            recipients = get_company_pension_managers(company)
            
            send_notification(
                recipients=recipients,
                subject=f"Monthly Pension Report - {period_month} {period_year} - {company}",
                message=format_monthly_report(report_data),
                attachments=[{
                    'fname': f'Pension_Report_{period_month}_{period_year}.pdf',
                    'fcontent': generate_report_pdf(report_data)
                }]
            )


def generate_company_pension_report(company, period_month, period_year):
    """Generate comprehensive pension report for a company"""
    
    # Get summary
    summary = frappe.db.sql("""
        SELECT 
            COUNT(DISTINCT employee) as total_employees,
            SUM(employee_contribution_amount) as total_employee_contrib,
            SUM(employer_contribution_amount) as total_employer_contrib,
            SUM(employee_voluntary_amount) as total_voluntary,
            SUM(total_contribution) as total_contrib
        FROM `tabPension Contribution`
        WHERE company = %s
        AND period_month = %s
        AND period_year = %s
        AND docstatus = 1
    """, (company, period_month, period_year), as_dict=True)
    
    if not summary or not summary[0].total_employees:
        return None
    
    # Get PFA breakdown
    pfa_breakdown = frappe.db.sql("""
        SELECT 
            pension_fund_administrator,
            COUNT(employee) as employee_count,
            SUM(total_contribution) as total_amount
        FROM `tabPension Contribution`
        WHERE company = %s
        AND period_month = %s
        AND period_year = %s
        AND docstatus = 1
        GROUP BY pension_fund_administrator
        ORDER BY total_amount DESC
    """, (company, period_month, period_year), as_dict=True)
    
    # Get remittance status
    remittance_schedule = frappe.db.get_value(
        "Pension Remittance Schedule",
        {
            "company": company,
            "period_month": period_month,
            "period_year": period_year,
            "docstatus": 1
        },
        ["name", "status", "payment_date", "payment_reference"],
        as_dict=True
    )
    
    return {
        "company": company,
        "period_month": period_month,
        "period_year": period_year,
        "summary": summary[0],
        "pfa_breakdown": pfa_breakdown,
        "remittance_schedule": remittance_schedule
    }


def format_monthly_report(data):
    """Format monthly report as HTML"""
    
    summary = data['summary']
    
    html = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #2490ef;">Monthly Pension Report</h2>
            <h3>{data['period_month']} {data['period_year']} - {data['company']}</h3>
            <hr>
            
            <h4>Summary</h4>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr style="background-color: #f8f9fa;">
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>Total Employees</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd; text-align: right;">{summary.total_employees}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Employee Contribution</td>
                    <td style="padding: 10px; border: 1px solid #ddd; text-align: right;">{frappe.format(summary.total_employee_contrib, {'fieldtype': 'Currency'})}</td>
                </tr>
                <tr style="background-color: #f8f9fa;">
                    <td style="padding: 10px; border: 1px solid #ddd;">Employer Contribution</td>
                    <td style="padding: 10px; border: 1px solid #ddd; text-align: right;">{frappe.format(summary.total_employer_contrib, {'fieldtype': 'Currency'})}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Voluntary Contribution</td>
                    <td style="padding: 10px; border: 1px solid #ddd; text-align: right;">{frappe.format(summary.total_voluntary or 0, {'fieldtype': 'Currency'})}</td>
                </tr>
                <tr style="background-color: #d4edda; font-weight: bold;">
                    <td style="padding: 10px; border: 1px solid #ddd;">TOTAL CONTRIBUTION</td>
                    <td style="padding: 10px; border: 1px solid #ddd; text-align: right;">{frappe.format(summary.total_contrib, {'fieldtype': 'Currency'})}</td>
                </tr>
            </table>
            
            <h4>Breakdown by PFA</h4>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <thead>
                    <tr style="background-color: #2490ef; color: white;">
                        <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">PFA</th>
                        <th style="padding: 10px; border: 1px solid #ddd; text-align: center;">Employees</th>
                        <th style="padding: 10px; border: 1px solid #ddd; text-align: right;">Amount</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    for pfa in data['pfa_breakdown']:
        html += f"""
                    <tr>
                        <td style="padding: 10px; border: 1px solid #ddd;">{pfa.pension_fund_administrator}</td>
                        <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">{pfa.employee_count}</td>
                        <td style="padding: 10px; border: 1px solid #ddd; text-align: right;">{frappe.format(pfa.total_amount, {'fieldtype': 'Currency'})}</td>
                    </tr>
        """
    
    html += """
                </tbody>
            </table>
    """
    
    # Remittance status
    if data['remittance_schedule']:
        rs = data['remittance_schedule']
        status_color = 'green' if rs.status == 'Paid' else 'orange'
        
        html += f"""
            <h4>Remittance Status</h4>
            <div style="padding: 15px; background-color: #f8f9fa; border-left: 4px solid {status_color};">
                <p><strong>Status:</strong> <span style="color: {status_color};">{rs.status}</span></p>
        """
        
        if rs.payment_date:
            html += f"<p><strong>Payment Date:</strong> {frappe.format(rs.payment_date, {'fieldtype': 'Date'})}</p>"
        
        if rs.payment_reference:
            html += f"<p><strong>Reference:</strong> {rs.payment_reference}</p>"
        
        html += f"""
                <p><a href="/app/pension-remittance-schedule/{rs.name}">View Remittance Schedule</a></p>
            </div>
        """
    else:
        html += """
            <div style="padding: 15px; background-color: #fff3cd; border-left: 4px solid #ffc107;">
                <p><strong>⚠️ Remittance Schedule Not Created</strong></p>
                <p>Please create the remittance schedule and process payment by 10th of the month.</p>
            </div>
        """
    
    html += "</div>"
    
    return html


def generate_report_pdf(data):
    """Generate PDF version of report - placeholder"""
    # TODO: Implement PDF generation using reportlab or weasyprint
    return None


def get_company_pension_managers(company):
    """Get users who manage pension for a company"""
    
    # Get users with Pension Manager role
    pension_managers = frappe.get_all(
        "Has Role",
        filters={
            "role": "Pension Manager",
            "parenttype": "User"
        },
        fields=["parent"],
        pluck="parent"
    )
    
    # Also get HR Managers for the company
    hr_managers = frappe.get_all(
        "User Permission",
        filters={
            "allow": "Company",
            "for_value": company
        },
        fields=["user"],
        pluck="user"
    )
    
    # Combine and deduplicate
    recipients = list(set(pension_managers + hr_managers))
    
    # If no specific managers, send to System Manager
    if not recipients:
        recipients = frappe.get_all(
            "Has Role",
            filters={
                "role": "System Manager",
                "parenttype": "User"
            },
            fields=["parent"],
            pluck="parent"
        )
    
    return recipients


def send_notification(recipients, subject, message, priority=0, attachments=None):
    """Send email notification"""
    
    if not recipients:
        return
    
    frappe.sendmail(
        recipients=recipients,
        subject=subject,
        message=message,
        now=priority == 1,  # Send immediately if high priority
        attachments=attachments or []
    )
    
    # Also create in-app notification
    for user in recipients:
        notification = frappe.new_doc("Notification Log")
        notification.subject = subject
        notification.for_user = user
        notification.type = "Alert"
        notification.document_type = "Pension Management"
        notification.email_content = message
        notification.insert(ignore_permissions=True)

def on_payroll_submit(doc, method):
    """
    Called when Payroll Entry is submitted
    Optional: Auto-create pension contributions
    """
    
    # Check if auto-creation is enabled in settings
    settings = frappe.get_single("Pension Settings")
    
    if not settings.get("auto_create_pension_on_payroll_submit"):
        # Auto-creation disabled, just notify
        notify_pension_creation_pending(doc)
        return
    
    # Auto-create pension contributions
    try:
        from general.general_biz_apps.doctype.pension_contribution.pension_contribution import bulk_create_from_payroll
        
        result = bulk_create_from_payroll(doc.name)
        
        if result and result.get('created') > 0:
            frappe.msgprint(
                _("Created {0} pension contributions automatically").format(result['created']),
                alert=True,
                indicator='green'
            )
    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(),
            f"Auto Pension Creation Failed: {doc.name}"
        )
        
        frappe.msgprint(
            _("Automatic pension creation failed. Please create manually via 'Pension Management' button."),
            alert=True,
            indicator='orange'
        )


def on_salary_slip_submit(doc, method):
    """
    Called when Salary Slip is submitted
    Check if pension contribution should be created
    """
    
    # Only process if employee has pension enabled
    if not is_employee_pension_applicable(doc.employee):
        return
    
    # Check if pension contribution already exists
    existing = frappe.db.exists(
        "Pension Contribution",
        {
            "salary_slip": doc.name,
            "docstatus": ["!=", 2]
        }
    )
    
    if existing:
        return
    
    # Check if auto-creation is enabled
    settings = frappe.get_single("Pension Settings")
    
    if settings.get("auto_create_pension_on_salary_submit"):
        # Auto-create
        try:
            from general.general_biz_apps.doctype.pension_contribution.pension_contribution import create_from_salary_slip
            
            pension_doc = create_from_salary_slip(doc.name)
            
            frappe.msgprint(
                _("Pension contribution {0} created").format(pension_doc),
                alert=True,
                indicator='green'
            )
        except Exception as e:
            frappe.log_error(
                frappe.get_traceback(),
                f"Auto Pension Creation Failed: {doc.name}"
            )
    else:
        # Just notify
        add_pension_creation_comment(doc)


def notify_pension_creation_pending(payroll_doc):
    """Add comment to payroll entry about pending pension creation"""
    
    # Count pension-applicable employees
    pension_count = frappe.db.count(
        "Salary Slip",
        {
            "payroll_entry": payroll_doc.name,
            "docstatus": 1
        }
    )
    
    if pension_count > 0:
        comment = f"""
            <div style="padding: 10px; background-color: #fff3cd; border-left: 3px solid #ffc107;">
                <strong>⚠️ Pension Contributions Pending</strong><br>
                {pension_count} salary slip(s) require pension contribution creation.<br>
                Click <strong>Pension Management > Create Pension Contributions</strong> to process.
            </div>
        """
        
        payroll_doc.add_comment(
            "Info",
            comment
        )


def add_pension_creation_comment(salary_slip_doc):
    """Add comment to salary slip about pension creation"""
    
    comment = """
        <div style="padding: 10px; background-color: #e6f7ff; border-left: 3px solid #2490ef;">
            <strong>ℹ️ Pension Contribution</strong><br>
            Click <strong>Pension > Create Pension Contribution</strong> to create pension record.
        </div>
    """
    
    salary_slip_doc.add_comment(
        "Info",
        comment
    )


def is_employee_pension_applicable(employee):
    """Check if employee has pension enabled"""
    
    if not employee:
        return False
    
    pension_applicable = frappe.db.get_value(
        "Employee",
        employee,
        "custom_pension_applicable"
    )
    
    return bool(pension_applicable)


@frappe.whitelist()
def get_salary_slip_pension_info(salary_slip_name):
    """
    Get pension-related information from salary slip
    Used by client scripts
    """
    
    salary_slip = frappe.get_doc("Salary Slip", salary_slip_name)
    
    if not salary_slip:
        return None
    
    # Extract pension components
    pension_info = {
        "employee": salary_slip.employee,
        "employee_name": salary_slip.employee_name,
        "posting_date": salary_slip.posting_date,
        "base_salary": salary_slip.base,
        "gross_salary": salary_slip.gross_pay,
        "employee_contribution": 0,
        "employer_contribution": 0,
        "voluntary_contribution": 0,
        "components": []
    }
    
    # Check deductions
    for deduction in salary_slip.deductions:
        component_name = deduction.salary_component.lower()
        if 'pension' in component_name:
            pension_info["components"].append({
                "type": "Deduction",
                "component": deduction.salary_component,
                "amount": deduction.amount
            })
            
            if 'voluntary' in component_name or 'additional' in component_name:
                pension_info["voluntary_contribution"] += deduction.amount
            else:
                pension_info["employee_contribution"] += deduction.amount
    
    # Check earnings
    for earning in salary_slip.earnings:
        component_name = earning.salary_component.lower()
        if 'pension' in component_name and 'employer' in component_name:
            pension_info["components"].append({
                "type": "Earning",
                "component": earning.salary_component,
                "amount": earning.amount
            })
            pension_info["employer_contribution"] += earning.amount
    
    # Calculate rates
    if salary_slip.base:
        pension_info["employee_rate"] = (pension_info["employee_contribution"] / salary_slip.base) * 100
        pension_info["employer_rate"] = (pension_info["employer_contribution"] / salary_slip.base) * 100
    
    pension_info["total_contribution"] = (
        pension_info["employee_contribution"] +
        pension_info["employer_contribution"] +
        pension_info["voluntary_contribution"]
    )
    
    # Check if pension contribution exists
    pension_doc = frappe.db.get_value(
        "Pension Contribution",
        {
            "salary_slip": salary_slip_name,
            "docstatus": ["!=", 2]
        },
        ["name", "remittance_status", "remittance_schedule"],
        as_dict=True
    )
    
    if pension_doc:
        pension_info["pension_contribution"] = pension_doc.name
        pension_info["remittance_status"] = pension_doc.remittance_status
        pension_info["remittance_schedule"] = pension_doc.remittance_schedule
    
    return pension_info


@frappe.whitelist()
def validate_salary_slip_pension_components(salary_slip_name):
    """
    Validate that salary slip has proper pension components
    Returns validation results and warnings
    """
    
    info = get_salary_slip_pension_info(salary_slip_name)
    
    if not info:
        return {
            "valid": False,
            "errors": ["Salary slip not found"]
        }
    
    errors = []
    warnings = []
    
    # Check if employee has pension enabled
    if not is_employee_pension_applicable(info["employee"]):
        errors.append("Employee does not have pension enabled")
        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings
        }
    
    # Check for pension components
    if len(info["components"]) == 0:
        errors.append("No pension components found in salary slip")
    
    # Check employee contribution
    if info["employee_contribution"] <= 0:
        warnings.append("Employee contribution is zero or missing")
    elif info["employee_rate"] < 8:
        warnings.append(f"Employee contribution ({info['employee_rate']:.2f}%) is below statutory minimum (8%)")
    
    # Check employer contribution
    if info["employer_contribution"] <= 0:
        warnings.append("Employer contribution is zero or missing")
    elif info["employer_rate"] < 10:
        warnings.append(f"Employer contribution ({info['employer_rate']:.2f}%) is below statutory minimum (10%)")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "info": info
    }


@frappe.whitelist()
def get_payroll_pension_summary(payroll_entry_name):
    """
    Get pension summary for payroll entry
    Used by client scripts to show statistics
    """
    
    # Get all salary slips
    salary_slips = frappe.get_all(
        "Salary Slip",
        filters={
            "payroll_entry": payroll_entry_name,
            "docstatus": 1
        },
        fields=["name", "employee", "employee_name", "base", "gross_pay"]
    )
    
    summary = {
        "total_employees": len(salary_slips),
        "pension_applicable": 0,
        "pension_created": 0,
        "pension_pending": 0,
        "total_employee_contribution": 0,
        "total_employer_contribution": 0,
        "total_voluntary_contribution": 0,
        "total_contribution": 0,
        "employees": []
    }
    
    for slip in salary_slips:
        # Check if pension applicable
        if not is_employee_pension_applicable(slip.employee):
            continue
        
        summary["pension_applicable"] += 1
        
        # Check if pension contribution created
        pension_doc = frappe.db.get_value(
            "Pension Contribution",
            {
                "salary_slip": slip.name,
                "docstatus": ["!=", 2]
            },
            ["name", "employee_contribution_amount", "employer_contribution_amount", 
             "employee_voluntary_amount", "total_contribution"],
            as_dict=True
        )
        
        if pension_doc:
            summary["pension_created"] += 1
            summary["total_employee_contribution"] += pension_doc.employee_contribution_amount or 0
            summary["total_employer_contribution"] += pension_doc.employer_contribution_amount or 0
            summary["total_voluntary_contribution"] += pension_doc.employee_voluntary_amount or 0
            summary["total_contribution"] += pension_doc.total_contribution or 0
            
            summary["employees"].append({
                "employee": slip.employee,
                "employee_name": slip.employee_name,
                "pension_contribution": pension_doc.name,
                "total_contribution": pension_doc.total_contribution,
                "status": "Created"
            })
        else:
            summary["pension_pending"] += 1
            summary["employees"].append({
                "employee": slip.employee,
                "employee_name": slip.employee_name,
                "pension_contribution": None,
                "total_contribution": 0,
                "status": "Pending"
            })
    
    return summary


@frappe.whitelist()
def check_pension_remittance_due():
    """
    Check if there are any pending pension remittances
    Used for dashboard alerts
    """
    
    today = getdate(nowdate())
    
    # Get overdue remittances
    overdue = frappe.db.count(
        "Pension Remittance Schedule",
        {
            "docstatus": 1,
            "status": ["not in", ["Paid", "Confirmed"]],
            "remittance_due_date": ["<", today]
        }
    )
    
    # Get upcoming remittances (due within 5 days)
    from frappe.utils import add_days
    five_days_later = add_days(today, 5)
    
    upcoming = frappe.db.count(
        "Pension Remittance Schedule",
        {
            "docstatus": 1,
            "status": ["not in", ["Paid", "Confirmed"]],
            "remittance_due_date": ["between", [today, five_days_later]]
        }
    )
    
    return {
        "overdue": overdue,
        "upcoming": upcoming,
        "has_alerts": overdue > 0 or upcoming > 0
    }