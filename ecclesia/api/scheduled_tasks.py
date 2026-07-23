# ecclesia/ecclesia/scheduled_tasks.py
# -*- coding: utf-8 -*-
# Copyright (c) 2024, Ecclesia and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, add_days, now_datetime
from frappe import _

def update_agent_performance():
    """Scheduled task to update agent performance metrics (runs daily)"""
    try:
        frappe.log_error("Starting agent performance update", "Scheduled Tasks")
        
        # Get all active agents
        agents = frappe.get_all("Telephony Agent", 
            filters={"status": ["!=", "Offline"]},
            pluck="name"
        )
        
        updated_count = 0
        for agent_name in agents:
            try:
                agent = frappe.get_doc("Telephony Agent", agent_name)
                agent.update_performance_metrics()
                agent.save(ignore_permissions=True)
                updated_count += 1
            except Exception as e:
                frappe.log_error(
                    message=f"Failed to update agent {agent_name}: {str(e)}",
                    title="Agent Performance Update Error"
                )
        
        frappe.log_error(
            message=f"Updated performance metrics for {updated_count} agents",
            title="Agent Performance Update Complete"
        )
        
    except Exception as e:
        frappe.log_error(
            message=f"Agent performance update failed: {str(e)}",
            title="Scheduled Task Error"
        )

def update_queue_metrics():
    """Scheduled task to update queue metrics (runs hourly)"""
    try:
        frappe.log_error("Starting queue metrics update", "Scheduled Tasks")
        
        # Get all queues
        queues = frappe.get_all("Telephony Queue", pluck="name")
        
        updated_count = 0
        for queue_name in queues:
            try:
                queue = frappe.get_doc("Telephony Queue", queue_name)
                queue.update_metrics()
                queue.save(ignore_permissions=True)
                updated_count += 1
            except Exception as e:
                frappe.log_error(
                    message=f"Failed to update queue {queue_name}: {str(e)}",
                    title="Queue Metrics Update Error"
                )
        
        frappe.log_error(
            message=f"Updated metrics for {updated_count} queues",
            title="Queue Metrics Update Complete"
        )
        
    except Exception as e:
        frappe.log_error(
            message=f"Queue metrics update failed: {str(e)}",
            title="Scheduled Task Error"
        )

def check_upcoming_agent_training():
    """Scheduled task to check for upcoming agent training (runs daily)"""
    try:
        frappe.log_error("Checking upcoming agent training", "Scheduled Tasks")
        
        # Check for agents who need training (example logic)
        # You can customize this based on your actual training doctype
        agents_needing_training = frappe.db.sql("""
            SELECT 
                ta.name,
                ta.full_name,
                ta.user
            FROM `tabTelephony Agent` ta
            LEFT JOIN `tabTraining Record` tr ON tr.agent = ta.name 
                AND tr.completion_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            WHERE tr.name IS NULL
            AND ta.status != 'Offline'
        """, as_dict=True)
        
        for agent in agents_needing_training:
            # Send notification to agent
            if agent.get('user'):
                frappe.publish_realtime(
                    event='training_reminder',
                    message={
                        'agent': agent.full_name,
                        'message': _('Please complete your required training')
                    },
                    user=agent.user
                )
                
                # Send email
                frappe.sendmail(
                    recipients=[agent.user],
                    subject=_('Training Reminder'),
                    message=f"""
                        <h3>Training Required</h3>
                        <p>Dear {agent.full_name},</p>
                        <p>You have upcoming training requirements that need attention.</p>
                        <p>Please check your training dashboard for more details.</p>
                    """
                )
        
        frappe.log_error(
            message=f"Sent training reminders to {len(agents_needing_training)} agents",
            title="Training Check Complete"
        )
        
    except Exception as e:
        frappe.log_error(
            message=f"Training check failed: {str(e)}",
            title="Scheduled Task Error"
        )

def cleanup_old_call_logs():
    """Clean up old call logs based on retention policy (runs daily)"""
    try:
        # Get retention days from settings
        settings = frappe.get_single("Telephony Settings")
        retention_days = settings.call_log_retention_days or 365
        
        cutoff_date = add_days(getdate(), -retention_days)
        cutoff_datetime = f"{cutoff_date} 00:00:00"
        
        # Delete old call logs
        old_logs = frappe.db.sql("""
            SELECT name 
            FROM `tabTelephony Call Log`
            WHERE start_time < %s
        """, cutoff_datetime, as_dict=True)
        
        deleted_count = 0
        for log in old_logs:
            try:
                frappe.delete_doc("Telephony Call Log", log.name, ignore_permissions=True)
                deleted_count += 1
            except Exception as e:
                frappe.log_error(
                    message=f"Failed to delete call log {log.name}: {str(e)}",
                    title="Cleanup Error"
                )
        
        frappe.log_error(
            message=f"Cleaned up {deleted_count} old call logs",
            title="Cleanup Complete"
        )
        
    except Exception as e:
        frappe.log_error(
            message=f"Cleanup failed: {str(e)}",
            title="Scheduled Task Error"
        )

def send_daily_call_summary():
    """Send daily call summary to agents (runs daily at end of day)"""
    try:
        today = getdate()
        today_start = f"{today} 00:00:00"
        today_end = f"{today} 23:59:59"
        
        # Get all agents
        agents = frappe.get_all("Telephony Agent", 
            fields=["name", "full_name", "user"]
        )
        
        for agent in agents:
            if not agent.user:
                continue
            
            # Get agent's call stats for today
            stats = frappe.db.sql("""
                SELECT 
                    COUNT(*) as total_calls,
                    SUM(CASE WHEN status = 'Connected' THEN 1 ELSE 0 END) as connected,
                    SUM(CASE WHEN status = 'Missed' THEN 1 ELSE 0 END) as missed,
                    AVG(duration) as avg_duration,
                    SUM(duration) as total_duration
                FROM `tabTelephony Call Log`
                WHERE agent = %s
                AND start_time BETWEEN %s AND %s
            """, (agent.name, today_start, today_end), as_dict=True)
            
            if stats and stats[0].total_calls > 0:
                # Send email summary
                frappe.sendmail(
                    recipients=[agent.user],
                    subject=_('Daily Call Summary - {0}').format(today),
                    message=f"""
                        <h3>Daily Call Summary for {agent.full_name}</h3>
                        <p><strong>Date:</strong> {today}</p>
                        <hr>
                        <table style="width:100%; border-collapse: collapse;">
                            <tr>
                                <td><strong>Total Calls:</strong></td>
                                <td>{stats[0].total_calls}</td>
                            </tr>
                            <tr>
                                <td><strong>Connected Calls:</strong></td>
                                <td>{stats[0].connected}</td>
                            </tr>
                            <tr>
                                <td><strong>Missed Calls:</strong></td>
                                <td>{stats[0].missed}</td>
                            </tr>
                            <tr>
                                <td><strong>Average Duration:</strong></td>
                                <td>{stats[0].avg_duration:.1f} minutes</td>
                            </tr>
                            <tr>
                                <td><strong>Total Talk Time:</strong></td>
                                <td>{stats[0].total_duration:.1f} minutes</td>
                            </tr>
                        </table>
                    """
                )
        
        frappe.log_error(
            message=f"Sent daily summaries to {len(agents)} agents",
            title="Daily Summary Complete"
        )
        
    except Exception as e:
        frappe.log_error(
            message=f"Daily summary failed: {str(e)}",
            title="Scheduled Task Error"
        )
        


# your_app/api/scheduled_tasks.py

import frappe
from frappe.utils import nowdate, add_days
from datetime import datetime

@frappe.whitelist()
def auto_code_unprocessed_payments():
    """Scheduled job to auto-code unprocessed payments"""
    
    # Get payments created in the last 7 days that haven't been auto-coded
    date_filter = add_days(nowdate(), -7)
    
    payments = frappe.get_all(
        "Payment",
        filters={
            "creation": [">=", date_filter],
            "auto_coded_account": ["in", ["", None]],
            "docstatus": 0  # Only draft payments
        },
        pluck="name"
    )
    
    if not payments:
        frappe.log_error("No unprocessed payments found", "Auto Coding Info")
        return
    
    from your_app.api.auto_coding import PaymentAutoCoder
    
    coder = PaymentAutoCoder()
    results = coder.code_multiple_payments(payments)
    
    # Log the results
    frappe.log_error(
        f"Auto-coded {results['success']} out of {len(payments)} payments. "
        f"Failed: {results['failed']}",
        "Auto Coding Schedule Result"
    )
    
    return results


def create_scheduled_job():
    """Create the scheduled job in ERPNext (run once)"""
    
    # Check if job already exists
    existing = frappe.db.exists("Scheduled Job Type", "auto_code_unprocessed_payments")
    
    if not existing:
        job = frappe.get_doc({
            "doctype": "Scheduled Job Type",
            "method": "your_app.api.scheduled_tasks.auto_code_unprocessed_payments",
            "frequency": "Daily",  # Options: Hourly, Daily, Weekly, Monthly
            "server_script": 0,
            "status": "Enabled"
        })
        job.insert(ignore_permissions=True)
        frappe.db.commit()