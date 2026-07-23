# Copyright (c) 2026, Ecclesia and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, date_diff, nowdate

class CRMQuotaTarget(Document):
    
    def validate(self):
        """Validate quota target data"""
        self.validate_dates()
        self.validate_unique_period()
        self.calculate_achievement_percentages()
        
    def validate_dates(self):
        """Ensure period start is before period end"""
        if self.period_start and self.period_end:
            if getdate(self.period_start) > getdate(self.period_end):
                frappe.throw(_("Period Start date must be before Period End date"))
                
    def validate_unique_period(self):
        """Prevent duplicate quota targets for same rep and period"""
        if self.rep and self.period and self.period_start and self.period_end:
            filters = {
                "rep": self.rep,
                "period": self.period,
                "period_start": self.period_start,
                "period_end": self.period_end,
                "name": ["!=", self.name]
            }
            
            existing = frappe.db.get_value("CRM Quota Target", filters, "name")
            if existing:
                frappe.throw(_("Quota target already exists for {0} for the period {1} ({2} to {3})").format(
                    self.rep, self.period, self.period_start, self.period_end
                ))
            
    def calculate_achievement_percentages(self):
        """Calculate achievement percentages"""
        # Calculate value achievement
        if self.target_value and self.target_value > 0:
            self.value_achievement = ((self.achieved_value or 0) / self.target_value) * 100
        else:
            self.value_achievement = 0
            
        # Calculate deals achievement
        if self.target_deals and self.target_deals > 0:
            self.deals_achievement = ((self.achieved_deals or 0) / self.target_deals) * 100
        else:
            self.deals_achievement = 0
            
    def on_update(self):
        """After saving, update permissions and check alerts"""
        self.update_rep_permissions()
        self.check_threshold_alerts()
        
    def update_rep_permissions(self):
        """Ensure sales rep can view their own quota"""
        if self.rep and not frappe.db.exists("User Permission", {
            "user": self.rep,
            "allow": "CRM Quota Target",
            "for_value": self.name
        }):
            try:
                user_perm = frappe.get_doc({
                    "doctype": "User Permission",
                    "user": self.rep,
                    "allow": "CRM Quota Target",
                    "for_value": self.name,
                    "applicable_for": "CRM Quota Target"
                })
                user_perm.insert(ignore_permissions=True)
            except Exception as e:
                # Log error but don't break the save operation
                frappe.log_error(f"Failed to create user permission for quota {self.name}: {str(e)}")
                
    def check_threshold_alerts(self):
        """Send alerts when achievement reaches certain thresholds"""
        if not self.rep:
            return
            
        if self.value_achievement >= 100 and self.value_achievement < 110:
            self.create_notification(_("Congratulations! You've achieved 100% of your quota!"))
        elif self.value_achievement >= 75 and self.value_achievement < 80:
            self.create_notification(_("Great progress! You're at 75% of your quota target."))
        elif self.value_achievement >= 50 and self.value_achievement < 55:
            self.create_notification(_("Halfway there! Keep pushing to reach your quota."))
            
    def create_notification(self, message):
        """Create a notification for the sales rep"""
        try:
            from frappe.desk.doctype.notification_log.notification_log import make_notification_logs
            
            make_notification_logs({
                "type": "Alert",
                "document_type": self.doctype,
                "document_name": self.name,
                "subject": message,
                "for_user": self.rep
            })
        except Exception as e:
            frappe.log_error(f"Failed to create notification for quota {self.name}: {str(e)}")


# API Methods for Dashboard
@frappe.whitelist()
def get_quota_analytics(rep=None, period=None):
    """Return quota analytics including achievements and trends"""
    
    filters = {"docstatus": 0}
    if rep:
        filters["rep"] = rep
    if period:
        filters["period"] = period
        
    quotas = frappe.get_all("CRM Quota Target", 
        filters=filters,
        fields=["name", "rep", "period", "period_start", "period_end", 
                "target_value", "achieved_value", "target_deals", "achieved_deals",
                "value_achievement", "deals_achievement"]
    )
    
    analytics = []
    for quota in quotas:
        # Get actual performance from deals (cross-check with actual CRM data)
        actual_performance = get_rep_performance(quota.rep, quota.period_start, quota.period_end)
        
        analytics.append({
            "rep_name": frappe.db.get_value("User", quota.rep, "full_name") or quota.rep,
            "rep_email": quota.rep,
            "period": quota.period,
            "period_start": quota.period_start,
            "period_end": quota.period_end,
            "target_value": quota.target_value,
            "achieved_value": max(quota.achieved_value or 0, actual_performance["actual_value"]),
            "value_achievement": max(quota.value_achievement or 0, actual_performance["value_percentage"]),
            "target_deals": quota.target_deals or 0,
            "achieved_deals": max(quota.achieved_deals or 0, actual_performance["actual_deals"]),
            "deals_achievement": max(quota.deals_achievement or 0, actual_performance["deals_percentage"]),
            "days_remaining": calculate_days_remaining(quota.period_end),
            "status": get_quota_status(quota.value_achievement or 0, quota.period_end),
            "actual_deals_data": actual_performance["deals_data"]
        })
    
    # Calculate team aggregates if no specific rep
    if not rep and len(analytics) > 1:
        team_analytics = calculate_team_analytics(analytics)
        return {"individual": analytics, "team": team_analytics}
    
    return analytics[0] if analytics else {}


@frappe.whitelist()
def get_rep_performance(rep, start_date, end_date):
    """Get actual performance data from CRM Deals and Meetings"""
    
    # Check if CRM Deal doctype exists
    deal_data = {"deal_count": 0, "total_value": 0}
    if frappe.db.exists("DocType", "CRM Deal"):
        # Get won deals in the period
        deals = frappe.db.sql("""
            SELECT 
                COUNT(*) as deal_count,
                COALESCE(SUM(deal_value), 0) as total_value
            FROM `tabCRM Deal`
            WHERE 
                owner = %s 
                AND status = 'Won'
                AND closing_date BETWEEN %s AND %s
                AND docstatus = 0
        """, (rep, start_date, end_date), as_dict=1)
        
        if deals:
            deal_data = deals[0]
    
    # Check if CRM Meeting doctype exists
    meetings = 0
    if frappe.db.exists("DocType", "CRM Meeting"):
        meetings = frappe.db.count("CRM Meeting", {
            "owner": rep,
            "status": "Completed",
            "meeting_date": ["between", [start_date, end_date]]
        })
    
    deal_count = deal_data.get("deal_count", 0)
    total_value = deal_data.get("total_value", 0)
    
    return {
        "actual_deals": deal_count,
        "actual_value": total_value,
        "value_percentage": 0,  # Will be calculated in quota context
        "deals_percentage": 0,
        "deals_data": {
            "won_deals": deal_count,
            "completed_meetings": meetings,
            "total_value": total_value
        }
    }


def calculate_days_remaining(end_date):
    """Calculate days remaining in quota period"""
    if not end_date:
        return 0
        
    today = getdate(nowdate())
    end = getdate(end_date)
    
    if today > end:
        return 0
    return date_diff(end, today)


def get_quota_status(achievement_percentage, end_date):
    """Determine quota status based on achievement and timeline"""
    days_left = calculate_days_remaining(end_date)
    
    if achievement_percentage >= 100:
        return {"status": "Achieved", "color": "green", "icon": "✅"}
    elif achievement_percentage >= 75:
        if days_left < 7:
            return {"status": "At Risk", "color": "orange", "icon": "⚠️"}
        return {"status": "On Track", "color": "blue", "icon": "📈"}
    elif achievement_percentage >= 50:
        if days_left < 14:
            return {"status": "Critical", "color": "red", "icon": "🔴"}
        return {"status": "Behind", "color": "yellow", "icon": "📉"}
    else:
        return {"status": "Off Track", "color": "red", "icon": "❌"}


def calculate_team_analytics(individual_data):
    """Calculate team-wide analytics"""
    if not individual_data:
        return {}
    
    total_target = sum([d.get("target_value", 0) for d in individual_data])
    total_achieved = sum([d.get("achieved_value", 0) for d in individual_data])
    total_target_deals = sum([d.get("target_deals", 0) for d in individual_data])
    total_achieved_deals = sum([d.get("achieved_deals", 0) for d in individual_data])
    
    # Find top performer
    top_performer = None
    if individual_data:
        top_performer = max(individual_data, key=lambda x: x.get("value_achievement", 0))
    
    return {
        "total_team_target": total_target,
        "total_team_achieved": total_achieved,
        "team_value_achievement": (total_achieved / total_target * 100) if total_target > 0 else 0,
        "team_deals_achievement": (total_achieved_deals / total_target_deals * 100) if total_target_deals > 0 else 0,
        "active_reps": len(individual_data),
        "reps_achieved_quota": len([d for d in individual_data if d.get("value_achievement", 0) >= 100]),
        "reps_at_risk": len([d for d in individual_data if d.get("status", {}).get("status") == "At Risk"]),
        "top_performer": top_performer
    }


@frappe.whitelist()
def sync_achievements_from_deals():
    """Sync actual achievements from won deals (utility function)"""
    quotas = frappe.get_all("CRM Quota Target", 
        filters={"docstatus": 0},
        fields=["name", "rep", "period_start", "period_end"]
    )
    
    updated = 0
    for quota in quotas:
        performance = get_rep_performance(quota.rep, quota.period_start, quota.period_end)
        
        frappe.db.set_value("CRM Quota Target", quota.name, {
            "achieved_value": performance["actual_value"],
            "achieved_deals": performance["actual_deals"]
        })
        updated += 1
    
    frappe.db.commit()
    return {"updated": updated, "message": f"Updated {updated} quota targets"}


# Helper to ensure fields exist in the doctype
def ensure_additional_fields():
    """Ensure that value_achievement and deals_achievement fields exist"""
    if not frappe.db.exists("DocType", "CRM Quota Target"):
        return
    
    doctype = frappe.get_doc("DocType", "CRM Quota Target")
    fields_to_add = [
        {"fieldname": "value_achievement", "fieldtype": "Percent", "label": "Value Achievement", "read_only": 1},
        {"fieldname": "deals_achievement", "fieldtype": "Percent", "label": "Deals Achievement", "read_only": 1}
    ]
    
    existing_fields = [f.fieldname for f in doctype.fields]
    
    for field in fields_to_add:
        if field["fieldname"] not in existing_fields:
            doctype.append("fields", field)
    
    if any(f["fieldname"] not in existing_fields for f in fields_to_add):
        doctype.save()