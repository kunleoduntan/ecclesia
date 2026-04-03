# ecclesia/ecclesia/api/dashboard.py
# -*- coding: utf-8 -*-

import frappe
from frappe.utils import getdate, add_days, flt
from frappe import _

@frappe.whitelist()
def get_dashboard_stats(from_date=None, to_date=None):
    """Get dashboard statistics"""
    if not from_date:
        from_date = add_days(getdate(), -30)
    if not to_date:
        to_date = getdate()
    
    from_date_str = f"{from_date} 00:00:00"
    to_date_str = f"{to_date} 23:59:59"
    
    stats = {
        'total_calls': get_total_calls(from_date_str, to_date_str),
        'avg_duration': get_average_duration(from_date_str, to_date_str),
        'missed_calls': get_missed_calls(from_date_str, to_date_str),
        'calls_by_type': get_calls_by_type(from_date_str, to_date_str),
        'calls_by_hour': get_calls_by_hour(from_date_str, to_date_str),
        'top_contacts': get_top_contacts(from_date_str, to_date_str),
        'agent_performance': get_agent_performance(from_date_str, to_date_str)
    }
    
    return stats

def get_total_calls(from_date, to_date):
    """Get total calls count"""
    total = frappe.db.count('Telephony Call Log', {
        'start_time': ['between', [from_date, to_date]]
    })
    
    return {
        'value': total,
        'label': 'Total Calls'
    }

def get_average_duration(from_date, to_date):
    """Get average call duration"""
    result = frappe.db.sql("""
        SELECT AVG(duration) as avg_duration
        FROM `tabTelephony Call Log`
        WHERE start_time BETWEEN %s AND %s
        AND status = 'Connected'
    """, (from_date, to_date), as_dict=True)
    
    avg_duration = flt(result[0].avg_duration) if result and result[0].avg_duration else 0
    
    return {
        'value': f"{avg_duration:.1f}",
        'label': 'Avg Duration (min)'
    }

def get_missed_calls(from_date, to_date):
    """Get missed calls count"""
    missed = frappe.db.count('Telephony Call Log', {
        'start_time': ['between', [from_date, to_date]],
        'status': 'Missed'
    })
    
    return {
        'value': missed,
        'label': 'Missed Calls'
    }

def get_calls_by_type(from_date, to_date):
    """Get calls breakdown by type"""
    result = frappe.db.sql("""
        SELECT 
            call_type,
            COUNT(*) as count
        FROM `tabTelephony Call Log`
        WHERE start_time BETWEEN %s AND %s
        GROUP BY call_type
        ORDER BY count DESC
    """, (from_date, to_date), as_dict=True)
    
    return result

def get_calls_by_hour(from_date, to_date):
    """Get call distribution by hour of day"""
    result = frappe.db.sql("""
        SELECT 
            HOUR(start_time) as hour,
            COUNT(*) as count
        FROM `tabTelephony Call Log`
        WHERE start_time BETWEEN %s AND %s
        GROUP BY HOUR(start_time)
        ORDER BY hour
    """, (from_date, to_date), as_dict=True)
    
    return result

def get_top_contacts(from_date, to_date):
    """Get most called contacts"""
    result = frappe.db.sql("""
        SELECT 
            caller_number,
            caller_name,
            COUNT(*) as call_count,
            SUM(duration) as total_duration
        FROM `tabTelephony Call Log`
        WHERE start_time BETWEEN %s AND %s
        AND caller_name IS NOT NULL
        AND caller_name != ''
        GROUP BY caller_number, caller_name
        ORDER BY call_count DESC
        LIMIT 10
    """, (from_date, to_date), as_dict=True)
    
    return result

def get_agent_performance(from_date, to_date):
    """Get agent performance metrics"""
    result = frappe.db.sql("""
        SELECT 
            ta.full_name as agent_name,
            COUNT(cl.name) as total_calls,
            SUM(CASE WHEN cl.status = 'Connected' THEN 1 ELSE 0 END) as connected_calls,
            AVG(cl.duration) as avg_duration
        FROM `tabTelephony Call Log` cl
        LEFT JOIN `tabTelephony Agent` ta ON ta.name = cl.agent
        WHERE cl.start_time BETWEEN %s AND %s
        AND cl.agent IS NOT NULL
        GROUP BY cl.agent, ta.full_name
        ORDER BY total_calls DESC
    """, (from_date, to_date), as_dict=True)
    
    return result