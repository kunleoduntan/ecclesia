# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import nowdate, getdate, format_date, add_days, date_diff


def post_scheduled_depreciation():
    """Run daily to post due depreciation entries automatically"""
    
    # Get all due schedules
    due_schedules = frappe.db.sql("""
        SELECT 
            dsd.name,
            dsd.parent as asset,
            dsd.schedule_date,
            dsd.depreciation_amount,
            fa.asset_name,
            fa.asset_code,
            fa.company
        FROM `tabDepreciation Schedule Details` dsd
        INNER JOIN `tabFixed Asset` fa ON dsd.parent = fa.name
        WHERE dsd.schedule_date <= %s
        AND (dsd.journal_entry IS NULL OR dsd.journal_entry = '')
        AND dsd.parenttype = 'Fixed Asset'
        AND fa.docstatus = 1
        AND fa.asset_status NOT IN ('Disposed', 'Cancelled', 'Scrapped')
        ORDER BY dsd.schedule_date ASC
    """, (nowdate(),), as_dict=True)
    
    if not due_schedules:
        frappe.logger().info("No due depreciation schedules found")
        return
    
    posted_count = 0
    errors = []
    
    for schedule in due_schedules:
        try:
            from ecclesia.ecclesia.doctype.fixed_asset.fixed_asset import post_depreciation_entry
            
            je_name = post_depreciation_entry(schedule.name)
            posted_count += 1
            frappe.db.commit()
            
            frappe.logger().info(f"Posted depreciation for {schedule.asset_code}: {je_name}")
            
        except Exception as e:
            error_msg = f"{schedule.asset_code}: {str(e)}"
            errors.append(error_msg)
            frappe.log_error(frappe.get_traceback(), 
                           f"Scheduled Depreciation Failed - {schedule.name}")
            frappe.db.rollback()
    
    # Send summary email to System Managers
    if posted_count > 0 or errors:
        send_depreciation_summary(posted_count, errors)
    
    frappe.logger().info(f"Scheduled Depreciation: Posted {posted_count}, Errors {len(errors)}")


def check_upcoming_depreciation():
    """Run weekly to check and notify about upcoming depreciation"""
    
    # Get schedules due in next 7 days
    upcoming_schedules = frappe.db.sql("""
        SELECT 
            dsd.name,
            dsd.parent as asset,
            dsd.schedule_date,
            dsd.depreciation_amount,
            fa.asset_name,
            fa.asset_code,
            fa.company,
            fa.cost_center,
            fa.department
        FROM `tabDepreciation Schedule Details` dsd
        INNER JOIN `tabFixed Asset` fa ON dsd.parent = fa.name
        WHERE dsd.schedule_date BETWEEN %s AND %s
        AND (dsd.journal_entry IS NULL OR dsd.journal_entry = '')
        AND dsd.parenttype = 'Fixed Asset'
        AND fa.docstatus = 1
        AND fa.asset_status NOT IN ('Disposed', 'Cancelled', 'Scrapped')
        ORDER BY dsd.schedule_date ASC
    """, (nowdate(), add_days(nowdate(), 7)), as_dict=True)
    
    if not upcoming_schedules:
        return
    
    # Group by company
    company_schedules = {}
    for schedule in upcoming_schedules:
        company = schedule.company
        if company not in company_schedules:
            company_schedules[company] = []
        company_schedules[company].append(schedule)
    
    # Send notifications per company
    for company, schedules in company_schedules.items():
        send_upcoming_depreciation_notification(company, schedules)
    
    frappe.logger().info(f"Upcoming Depreciation: Notified about {len(upcoming_schedules)} schedules")


def check_warranty_expiry():
    """Run weekly to check and notify about warranty expiries"""
    
    # Get assets with warranties expiring in next 30 days or already expired
    expiring_warranties = frappe.db.sql("""
        SELECT 
            name,
            asset_code,
            asset_name,
            warranty_expiry_date,
            company,
            custodian,
            department,
            current_location
        FROM `tabFixed Asset`
        WHERE warranty_expiry_date IS NOT NULL
        AND warranty_expiry_date <= %s
        AND docstatus = 1
        AND asset_status NOT IN ('Disposed', 'Cancelled', 'Scrapped')
        AND (
            warranty_expiry_date >= %s  -- Expiring in next 30 days
            OR warranty_expiry_date >= %s -- Or expired in last 7 days
        )
        ORDER BY warranty_expiry_date ASC
    """, (add_days(nowdate(), 30), nowdate(), add_days(nowdate(), -7)), as_dict=True)
    
    if not expiring_warranties:
        return
    
    # Categorize warranties
    expired = []
    expiring_soon = []
    
    for asset in expiring_warranties:
        days_diff = date_diff(asset.warranty_expiry_date, nowdate())
        
        if days_diff < 0:
            asset['days_status'] = f"Expired {abs(days_diff)} days ago"
            expired.append(asset)
        else:
            asset['days_status'] = f"Expiring in {days_diff} days"
            expiring_soon.append(asset)
    
    # Send notification
    if expired or expiring_soon:
        send_warranty_expiry_notification(expired, expiring_soon)
    
    frappe.logger().info(f"Warranty Check: {len(expired)} expired, {len(expiring_soon)} expiring soon")


def check_insurance_expiry():
    """Run weekly to check and notify about insurance expiries"""
    
    # Get assets with insurance expiring in next 30 days or already expired
    expiring_insurance = frappe.db.sql("""
        SELECT 
            name,
            asset_code,
            asset_name,
            insurance_expiry_date,
            insurance_company,
            insurance_value,
            company,
            custodian,
            department,
            current_location
        FROM `tabFixed Asset`
        WHERE insurance_expiry_date IS NOT NULL
        AND insurance_expiry_date <= %s
        AND docstatus = 1
        AND asset_status NOT IN ('Disposed', 'Cancelled', 'Scrapped')
        AND (
            insurance_expiry_date >= %s  -- Expiring in next 30 days
            OR insurance_expiry_date >= %s -- Or expired in last 7 days
        )
        ORDER BY insurance_expiry_date ASC
    """, (add_days(nowdate(), 30), nowdate(), add_days(nowdate(), -7)), as_dict=True)
    
    if not expiring_insurance:
        return
    
    # Categorize insurance
    expired = []
    expiring_soon = []
    critical = []  # High value assets
    
    for asset in expiring_insurance:
        days_diff = date_diff(asset.insurance_expiry_date, nowdate())
        
        if days_diff < 0:
            asset['days_status'] = f"Expired {abs(days_diff)} days ago"
            expired.append(asset)
        else:
            asset['days_status'] = f"Expiring in {days_diff} days"
            expiring_soon.append(asset)
        
        # Flag high value assets (>100,000)
        if asset.insurance_value and asset.insurance_value > 100000:
            critical.append(asset)
    
    # Send notification
    if expired or expiring_soon:
        send_insurance_expiry_notification(expired, expiring_soon, critical)
    
    frappe.logger().info(f"Insurance Check: {len(expired)} expired, {len(expiring_soon)} expiring soon, {len(critical)} critical")


def send_depreciation_summary(posted, errors):
    """Send email summary for posted depreciation"""
    
    recipients = frappe.get_all("Has Role", 
        filters={"role": "System Manager", "parenttype": "User"},
        pluck="parent"
    )
    
    if not recipients:
        return
    
    message = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px;">
        <h2 style="color: #2c3e50;">📊 Automated Depreciation Posting Summary</h2>
        <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <p><b>Date:</b> {format_date(nowdate())}</p>
            <p><b>✅ Successfully Posted:</b> <span style="color: green; font-size: 18px;">{posted}</span> entries</p>
            <p><b>❌ Errors:</b> <span style="color: red; font-size: 18px;">{len(errors)}</span></p>
        </div>
    """
    
    if errors:
        message += """
        <div style="background: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 20px 0;">
            <h4 style="color: #856404; margin-top: 0;">⚠️ Errors Encountered:</h4>
            <ul style="color: #856404;">
        """
        for error in errors[:20]:
            message += f"<li>{error}</li>"
        if len(errors) > 20:
            message += f"<li><i>... and {len(errors) - 20} more errors. Check Error Log for details.</i></li>"
        message += "</ul></div>"
    
    message += """
        <p style="margin-top: 20px; color: #6c757d; font-size: 12px;">
            This is an automated notification from the Fixed Asset Management System.
        </p>
    </div>
    """
    
    frappe.sendmail(
        recipients=recipients,
        subject=f"✅ Depreciation Posting Summary - {format_date(nowdate())}",
        message=message
    )


def send_upcoming_depreciation_notification(company, schedules):
    """Send notification about upcoming depreciation schedules"""
    
    # Get recipients - Accounts Manager and System Manager
    recipients = frappe.get_all("Has Role", 
        filters={
            "role": ["in", ["Accounts Manager", "System Manager"]],
            "parenttype": "User"
        },
        pluck="parent"
    )
    
    if not recipients:
        recipients = frappe.get_all("Has Role", 
            filters={"role": "System Manager", "parenttype": "User"},
            pluck="parent"
        )
    
    if not recipients:
        return
    
    total_amount = sum(schedule.depreciation_amount for schedule in schedules)
    
    message = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px;">
        <h2 style="color: #2c3e50;">📅 Upcoming Depreciation Schedule</h2>
        <div style="background: #e3f2fd; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <p><b>Company:</b> {company}</p>
            <p><b>Period:</b> Next 7 days</p>
            <p><b>Assets:</b> {len(schedules)}</p>
            <p><b>Total Amount:</b> {frappe.format_value(total_amount, {'fieldtype': 'Currency'})}</p>
        </div>
        
        <h3>Depreciation Schedule:</h3>
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <thead>
                <tr style="background: #f8f9fa;">
                    <th style="padding: 10px; border: 1px solid #dee2e6; text-align: left;">Date</th>
                    <th style="padding: 10px; border: 1px solid #dee2e6; text-align: left;">Asset Code</th>
                    <th style="padding: 10px; border: 1px solid #dee2e6; text-align: left;">Asset Name</th>
                    <th style="padding: 10px; border: 1px solid #dee2e6; text-align: right;">Amount</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for schedule in schedules[:50]:  # Limit to 50 for email size
        message += f"""
                <tr>
                    <td style="padding: 8px; border: 1px solid #dee2e6;">{format_date(schedule.schedule_date)}</td>
                    <td style="padding: 8px; border: 1px solid #dee2e6;">{schedule.asset_code}</td>
                    <td style="padding: 8px; border: 1px solid #dee2e6;">{schedule.asset_name}</td>
                    <td style="padding: 8px; border: 1px solid #dee2e6; text-align: right;">{frappe.format_value(schedule.depreciation_amount, {'fieldtype': 'Currency'})}</td>
                </tr>
        """
    
    if len(schedules) > 50:
        message += f"""
                <tr>
                    <td colspan="4" style="padding: 8px; border: 1px solid #dee2e6; text-align: center; font-style: italic;">
                        ... and {len(schedules) - 50} more schedules
                    </td>
                </tr>
        """
    
    message += """
            </tbody>
        </table>
        
        <p style="margin-top: 20px; color: #6c757d; font-size: 12px;">
            This is an automated weekly notification from the Fixed Asset Management System.
        </p>
    </div>
    """
    
    frappe.sendmail(
        recipients=recipients,
        subject=f"📅 Upcoming Depreciation - {company} - Next 7 Days",
        message=message
    )


def send_warranty_expiry_notification(expired, expiring_soon):
    """Send notification about warranty expiries"""
    
    # Get recipients
    recipients = frappe.get_all("Has Role", 
        filters={
            "role": ["in", ["Asset Manager", "System Manager"]],
            "parenttype": "User"
        },
        pluck="parent"
    )
    
    if not recipients:
        recipients = frappe.get_all("Has Role", 
            filters={"role": "System Manager", "parenttype": "User"},
            pluck="parent"
        )
    
    if not recipients:
        return
    
    message = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px;">
        <h2 style="color: #2c3e50;">⚠️ Warranty Expiry Alert</h2>
        <div style="background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <p><b>Date:</b> {format_date(nowdate())}</p>
            <p><b>🔴 Expired:</b> {len(expired)}</p>
            <p><b>🟡 Expiring Soon:</b> {len(expiring_soon)}</p>
        </div>
    """
    
    if expired:
        message += """
        <h3 style="color: #dc3545;">🔴 Expired Warranties</h3>
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <thead>
                <tr style="background: #f8d7da;">
                    <th style="padding: 10px; border: 1px solid #dee2e6; text-align: left;">Asset Code</th>
                    <th style="padding: 10px; border: 1px solid #dee2e6; text-align: left;">Asset Name</th>
                    <th style="padding: 10px; border: 1px solid #dee2e6; text-align: left;">Expiry Date</th>
                    <th style="padding: 10px; border: 1px solid #dee2e6; text-align: left;">Status</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for asset in expired[:30]:
            message += f"""
                <tr>
                    <td style="padding: 8px; border: 1px solid #dee2e6;">{asset.asset_code}</td>
                    <td style="padding: 8px; border: 1px solid #dee2e6;">{asset.asset_name}</td>
                    <td style="padding: 8px; border: 1px solid #dee2e6;">{format_date(asset.warranty_expiry_date)}</td>
                    <td style="padding: 8px; border: 1px solid #dee2e6; color: #dc3545;">{asset.days_status}</td>
                </tr>
            """
        
        message += "</tbody></table>"
    
    if expiring_soon:
        message += """
        <h3 style="color: #ffc107;">🟡 Warranties Expiring Soon (Next 30 Days)</h3>
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <thead>
                <tr style="background: #fff3cd;">
                    <th style="padding: 10px; border: 1px solid #dee2e6; text-align: left;">Asset Code</th>
                    <th style="padding: 10px; border: 1px solid #dee2e6; text-align: left;">Asset Name</th>
                    <th style="padding: 10px; border: 1px solid #dee2e6; text-align: left;">Expiry Date</th>
                    <th style="padding: 10px; border: 1px solid #dee2e6; text-align: left;">Status</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for asset in expiring_soon[:30]:
            message += f"""
                <tr>
                    <td style="padding: 8px; border: 1px solid #dee2e6;">{asset.asset_code}</td>
                    <td style="padding: 8px; border: 1px solid #dee2e6;">{asset.asset_name}</td>
                    <td style="padding: 8px; border: 1px solid #dee2e6;">{format_date(asset.warranty_expiry_date)}</td>
                    <td style="padding: 8px; border: 1px solid #dee2e6; color: #856404;">{asset.days_status}</td>
                </tr>
            """
        
        message += "</tbody></table>"
    
    message += """
        <p style="margin-top: 20px; color: #6c757d; font-size: 12px;">
            This is an automated weekly notification from the Fixed Asset Management System.
        </p>
    </div>
    """
    
    frappe.sendmail(
        recipients=recipients,
        subject=f"⚠️ Warranty Expiry Alert - {format_date(nowdate())}",
        message=message
    )


def send_insurance_expiry_notification(expired, expiring_soon, critical):
    """Send notification about insurance expiries"""
    
    # Get recipients
    recipients = frappe.get_all("Has Role", 
        filters={
            "role": ["in", ["Asset Manager", "Accounts Manager", "System Manager"]],
            "parenttype": "User"
        },
        pluck="parent"
    )
    
    if not recipients:
        recipients = frappe.get_all("Has Role", 
            filters={"role": "System Manager", "parenttype": "User"},
            pluck="parent"
        )
    
    if not recipients:
        return
    
    message = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px;">
        <h2 style="color: #2c3e50;">🚨 Insurance Expiry Alert</h2>
        <div style="background: #f8d7da; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #dc3545;">
            <p><b>Date:</b> {format_date(nowdate())}</p>
            <p><b>🔴 Expired:</b> {len(expired)}</p>
            <p><b>🟡 Expiring Soon:</b> {len(expiring_soon)}</p>
            <p><b>⚡ Critical (High Value):</b> {len(critical)}</p>
        </div>
    """
    
    if critical:
        total_critical_value = sum(asset.insurance_value or 0 for asset in critical)
        message += f"""
        <div style="background: #dc3545; color: white; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3 style="margin-top: 0;">⚡ CRITICAL: High Value Assets</h3>
            <p><b>Assets at Risk:</b> {len(critical)}</p>
            <p><b>Total Insured Value:</b> {frappe.format_value(total_critical_value, {'fieldtype': 'Currency'})}</p>
        </div>
        """
    
    if expired:
        message += """
        <h3 style="color: #dc3545;">🔴 Expired Insurance</h3>
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <thead>
                <tr style="background: #f8d7da;">
                    <th style="padding: 10px; border: 1px solid #dee2e6; text-align: left;">Asset Code</th>
                    <th style="padding: 10px; border: 1px solid #dee2e6; text-align: left;">Asset Name</th>
                    <th style="padding: 10px; border: 1px solid #dee2e6; text-align: left;">Company</th>
                    <th style="padding: 10px; border: 1px solid #dee2e6; text-align: right;">Insured Value</th>
                    <th style="padding: 10px; border: 1px solid #dee2e6; text-align: left;">Status</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for asset in expired[:30]:
            message += f"""
                <tr>
                    <td style="padding: 8px; border: 1px solid #dee2e6;">{asset.asset_code}</td>
                    <td style="padding: 8px; border: 1px solid #dee2e6;">{asset.asset_name}</td>
                    <td style="padding: 8px; border: 1px solid #dee2e6;">{asset.insurance_company or 'N/A'}</td>
                    <td style="padding: 8px; border: 1px solid #dee2e6; text-align: right;">{frappe.format_value(asset.insurance_value, {'fieldtype': 'Currency'})}</td>
                    <td style="padding: 8px; border: 1px solid #dee2e6; color: #dc3545;">{asset.days_status}</td>
                </tr>
            """
        
        message += "</tbody></table>"
    
    if expiring_soon:
        message += """
        <h3 style="color: #ffc107;">🟡 Insurance Expiring Soon (Next 30 Days)</h3>
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <thead>
                <tr style="background: #fff3cd;">
                    <th style="padding: 10px; border: 1px solid #dee2e6; text-align: left;">Asset Code</th>
                    <th style="padding: 10px; border: 1px solid #dee2e6; text-align: left;">Asset Name</th>
                    <th style="padding: 10px; border: 1px solid #dee2e6; text-align: left;">Company</th>
                    <th style="padding: 10px; border: 1px solid #dee2e6; text-align: right;">Insured Value</th>
                    <th style="padding: 10px; border: 1px solid #dee2e6; text-align: left;">Status</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for asset in expiring_soon[:30]:
            message += f"""
                <tr>
                    <td style="padding: 8px; border: 1px solid #dee2e6;">{asset.asset_code}</td>
                    <td style="padding: 8px; border: 1px solid #dee2e6;">{asset.asset_name}</td>
                    <td style="padding: 8px; border: 1px solid #dee2e6;">{asset.insurance_company or 'N/A'}</td>
                    <td style="padding: 8px; border: 1px solid #dee2e6; text-align: right;">{frappe.format_value(asset.insurance_value, {'fieldtype': 'Currency'})}</td>
                    <td style="padding: 8px; border: 1px solid #dee2e6; color: #856404;">{asset.days_status}</td>
                </tr>
            """
        
        message += "</tbody></table>"
    
    message += """
        <div style="background: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 20px 0;">
            <p><b>⚠️ Action Required:</b> Please review and renew insurance policies for the assets listed above to avoid coverage gaps.</p>
        </div>
        
        <p style="margin-top: 20px; color: #6c757d; font-size: 12px;">
            This is an automated weekly notification from the Fixed Asset Management System.
        </p>
    </div>
    """
    
    frappe.sendmail(
        recipients=recipients,
        subject=f"🚨 URGENT: Insurance Expiry Alert - {format_date(nowdate())}",
        message=message,
        priority=1  # High priority
    )
    
    
