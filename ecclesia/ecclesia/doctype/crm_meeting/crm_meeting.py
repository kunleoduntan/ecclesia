# Copyright (c) 2026, Value Impacts Consulting
# For license information, please see license.txt
import frappe
from frappe import _
from frappe.utils import flt, getdate, add_months, add_days, nowdate, get_last_day, get_first_day
from frappe.model.document import Document


class CRMMeeting(Document):
    
    def before_save(self):
        """Set defaults and validate before saving"""
        if not self.meeting_title and self.lead:
            lead_name = frappe.db.get_value("CRM Lead", self.lead, "lead_name")
            if lead_name:
                self.meeting_title = f"Meeting with {lead_name}"
        
        if self.meeting_date and not self.duration_mins:
            self.duration_mins = 30  # default duration
            
    def validate(self):
        """Validate meeting data"""
        self.validate_dates()
        self.validate_links()
        
    def validate_dates(self):
        """Prevent meetings in the past (optional)"""
        from frappe.utils import now_datetime, get_datetime
        if self.meeting_date and self.is_new():
            meeting_dt = get_datetime(self.meeting_date)
            if meeting_dt < now_datetime():
                frappe.msgprint(_("Warning: Meeting date is in the past."), alert=True)
                
    def validate_links(self):
        """Ensure at least one reference (Lead, Opportunity, or Deal) is selected"""
        if not (self.lead or self.opportunity or self.deal):
            frappe.throw(_("Please link at least one of Lead, Opportunity, or Deal."))
            
    def on_update(self):
        """After saving, update the parent document's last meeting field if applicable"""
        self.update_parent_last_meeting()
        
    def update_parent_last_meeting(self):
        """Update the 'Last Meeting' field on the linked Lead/Opportunity/Deal"""
        parent_doctype = None
        parent_name = None
        
        if self.lead:
            parent_doctype = "CRM Lead"
            parent_name = self.lead
        elif self.opportunity:
            parent_doctype = "CRM Opportunity"
            parent_name = self.opportunity
        elif self.deal:
            parent_doctype = "CRM Deal"
            parent_name = self.deal
            
        if parent_doctype and parent_name:
            frappe.db.set_value(parent_doctype, parent_name, "last_meeting_date", self.meeting_date)
            
    def on_submit(self):
        """When meeting is submitted (if workflow exists), mark as Completed"""
        if self.status == "Scheduled":
            self.status = "Completed"
            self.save()
            
    def get_meeting_duration_in_hours(self):
        """Helper: return duration in hours for analytics"""
        return self.duration_mins / 60.0

# Dashboard Analytics API
@frappe.whitelist()
def get_meeting_analytics():
    """Return meeting KPIs and chart data for the HTML dashboard"""
    from frappe.utils import getdate, add_days, nowdate
    
    today = getdate(nowdate())
    week_ago = add_days(today, -7)
    month_ago = add_days(today, -30)
    
    # KPI: Total meetings (last 30 days)
    total_meetings = frappe.db.count("CRM Meeting", {
        "meeting_date": [">=", month_ago],
        "docstatus": 0
    })
    
    # Completed vs Cancelled vs No-show
    status_counts = frappe.db.sql("""
        SELECT status, COUNT(*) as count
        FROM `tabCRM Meeting`
        WHERE meeting_date >= %s AND docstatus = 0
        GROUP BY status
    """, month_ago, as_dict=1)
    
    # Meetings by type
    type_counts = frappe.db.sql("""
        SELECT meeting_type, COUNT(*) as count
        FROM `tabCRM Meeting`
        WHERE meeting_date >= %s AND meeting_type IS NOT NULL
        GROUP BY meeting_type
    """, month_ago, as_dict=1)
    
    # Upcoming meetings (next 7 days)
    upcoming = frappe.db.get_list("CRM Meeting",
        filters={
            "meeting_date": [">=", today],
            "meeting_date": ["<=", add_days(today, 7)],
            "status": "Scheduled",
            "docstatus": 0
        },
        fields=["name", "meeting_title", "meeting_date", "meeting_type"],
        order_by="meeting_date ASC"
    )
    
    return {
        "total_meetings_last_30d": total_meetings,
        "status_breakdown": status_counts,
        "type_breakdown": type_counts,
        "upcoming_meetings": upcoming,
        "completion_rate": _calculate_rate(status_counts, "Completed")
    }
    
def _calculate_rate(status_counts, status_name):
    total = sum([item["count"] for item in status_counts])
    if total == 0:
        return 0
    completed = next((item["count"] for item in status_counts if item["status"] == status_name), 0)
    return round((completed / total) * 100, 1)