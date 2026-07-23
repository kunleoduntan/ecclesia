# Copyright (c) 2026, Value Impacts Consulting


import frappe
from frappe import _
from frappe.model.document import Document


class CRMPipeline(Document):
    
    def validate(self):
        """Validate pipeline data"""
        self.validate_default_pipeline()
        self.validate_unique_pipeline_name()
        
    def validate_default_pipeline(self):
        """Ensure only one default pipeline per company"""
        if self.is_default:
            # Clear default flag from other pipelines in same company
            filters = {"is_default": 1}
            if self.company:
                filters["company"] = self.company
            else:
                filters["company": ["is", "not set"]]
                
            frappe.db.sql("""
                UPDATE `tabCRM Pipeline`
                SET is_default = 0
                WHERE name != %s
                AND is_default = 1
                AND IFNULL(company, '') = IFNULL(%s, '')
            """, (self.name, self.company))
            
    def validate_unique_pipeline_name(self):
        """Ensure pipeline name is unique (case-insensitive)"""
        existing = frappe.db.get_value(
            "CRM Pipeline",
            {"pipeline_name": self.pipeline_name, "name": ["!=", self.name]},
            "name"
        )
        if existing:
            frappe.throw(_("Pipeline name '{0}' already exists. Please use a unique name.").format(self.pipeline_name))
    
    def on_update(self):
        """After saving, update stages that reference this pipeline"""
        self.update_related_stages()
        
    def update_related_stages(self):
        """Update pipeline_name in related stages if changed"""
        if self.get_doc_before_save() and self.get_doc_before_save().pipeline_name != self.pipeline_name:
            frappe.db.sql("""
                UPDATE `tabCRM Stage`
                SET pipeline_name = %s
                WHERE pipeline = %s
            """, (self.pipeline_name, self.name))
            
    def on_trash(self):
        """Prevent deletion of default pipeline or pipeline with stages"""
        if self.is_default:
            frappe.throw(_("Cannot delete the default pipeline. Please set another pipeline as default first."))
            
        # Check if pipeline has any stages
        stages_count = frappe.db.count("CRM Stage", {"pipeline": self.name})
        if stages_count > 0:
            frappe.throw(_("Cannot delete pipeline '{0}' as it has {1} stage(s) associated. Please delete or reassign stages first.").format(self.pipeline_name, stages_count))

# API Methods for Dashboard
@frappe.whitelist()
def get_pipeline_analytics(pipeline_name=None):
    """Return pipeline analytics including stage distribution and performance metrics"""
    
    # Get all pipelines if none specified
    if not pipeline_name:
        pipelines = frappe.get_all("CRM Pipeline", fields=["name", "pipeline_name", "is_default", "company"])
    else:
        pipelines = [frappe.get_doc("CRM Pipeline", pipeline_name)]
    
    analytics_data = []
    
    for pipeline in pipelines:
        # Get stages for this pipeline
        stages = frappe.get_all(
            "CRM Stage",
            filters={"pipeline": pipeline.name},
            fields=["name", "stage_name", "probability", "order"],
            order_by="order asc"
        )
        
        # Get deals/opportunities in each stage
        stage_stats = []
        total_deals = 0
        total_value = 0
        
        for stage in stages:
            # Count deals in this stage (assuming CRM Deal doctype)
            deals = frappe.db.sql("""
                SELECT 
                    COUNT(*) as deal_count,
                    COALESCE(SUM(deal_value), 0) as total_value
                FROM `tabCRM Deal`
                WHERE pipeline_stage = %s
                AND docstatus = 0
            """, stage.name, as_dict=1)
            
            deal_count = deals[0].deal_count if deals else 0
            stage_value = deals[0].total_value if deals else 0
            
            stage_stats.append({
                "stage_name": stage.stage_name,
                "probability": stage.probability,
                "order": stage.order,
                "deal_count": deal_count,
                "total_value": stage_value
            })
            
            total_deals += deal_count
            total_value += stage_value
        
        # Calculate weighted pipeline value
        weighted_value = sum([s["total_value"] * (s["probability"] / 100) for s in stage_stats])
        
        analytics_data.append({
            "pipeline_name": pipeline.pipeline_name,
            "pipeline_id": pipeline.name,
            "is_default": pipeline.is_default,
            "company": pipeline.company,
            "total_stages": len(stages),
            "total_deals": total_deals,
            "total_pipeline_value": total_value,
            "weighted_pipeline_value": weighted_value,
            "stage_breakdown": stage_stats,
            "completion_rate": (stage_stats[-1]["deal_count"] / total_deals * 100) if total_deals > 0 else 0
        })
    
    return analytics_data if len(analytics_data) > 1 else analytics_data[0] if analytics_data else {}

@frappe.whitelist()
def get_default_pipeline(company=None):
    """Get the default pipeline for a company"""
    filters = {"is_default": 1}
    if company:
        filters["company"] = company
    else:
        filters["company": ["in", [None, ""]]]
    
    pipeline = frappe.db.get_value("CRM Pipeline", filters, ["name", "pipeline_name"], as_dict=1)
    return pipeline or {}

@frappe.whitelist()
def set_default_pipeline(pipeline_name, company=None):
    """Set a pipeline as default"""
    pipeline = frappe.get_doc("CRM Pipeline", pipeline_name)
    pipeline.is_default = 1
    pipeline.save()
    frappe.db.commit()
    return {"success": True, "message": _("Default pipeline set successfully")}