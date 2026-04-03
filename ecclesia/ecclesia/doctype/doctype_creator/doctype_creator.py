# Copyright (c) 2025, kunleoduntan and contributors
# For license information, please see license.txt

# Copyright (c) 2025, Value Impacts Consulting and contributors
# For license information, please see license.txt

import json
import frappe
from frappe import _
from frappe.model.document import Document


class DoctypeCreator(Document):
    """Controller for DocType Creator - Single DocType workflow for quick DocType creation."""
    
    def validate(self):
        """Validate before saving."""
        frappe.log_error("VALIDATE METHOD CALLED", "DEBUG")
        frappe.msgprint("Validate method called", indicator="blue")
        
        if self.create_document:
            frappe.log_error(f"create_document is checked: {self.create_document}", "DEBUG")
            frappe.msgprint(f"create_document is checked: {self.create_document}", indicator="blue")
            
            if self.doctype_field_json:
                frappe.log_error("JSON found, validating...", "DEBUG")
                # Validate JSON syntax
                try:
                    json_data = frappe.parse_json(self.doctype_field_json)
                    frappe.msgprint("JSON parsed successfully", indicator="green")
                    
                    # Validate structure
                    structure = self.detect_json_structure(json_data)
                    frappe.msgprint(f"JSON structure detected: {structure}", indicator="green")
                    
                    if structure == "unknown":
                        frappe.throw(_("Unrecognized JSON structure. Please check the format."))
                    
                except frappe.ValidationError:
                    raise
                except Exception as e:
                    frappe.log_error(f"JSON validation error: {str(e)}", "DEBUG")
                    frappe.throw(_("Invalid JSON format: {0}").format(str(e)))
    
    def on_update(self):
        """Create DocType(s) when document is updated and checkbox is checked."""
        frappe.log_error("ON_UPDATE METHOD CALLED", "DEBUG")
        frappe.msgprint("on_update method called", indicator="blue")
        
        if self.create_document:
            frappe.log_error("create_document is TRUE in on_update", "DEBUG")
            frappe.msgprint("create_document is TRUE, starting creation...", indicator="blue")
            
            try:
                self.create_doctypes()
                frappe.db.commit()
                
                frappe.msgprint("DocTypes created successfully! Unchecking box...", indicator="green")
                
                # Auto-uncheck after creation
                frappe.db.set_value('Doctype Creator', self.name, 'create_document', 0, update_modified=False)
                
            except Exception as e:
                frappe.db.rollback()
                error_msg = str(e)
                frappe.log_error(
                    message=f"{error_msg}\n\n{frappe.get_traceback()}",
                    title=f"DocType Creation Failed"
                )
                frappe.msgprint(f"ERROR: {error_msg}", indicator="red")
                frappe.throw(_("Failed to create DocType(s): {0}").format(error_msg))
        else:
            frappe.log_error("create_document is FALSE in on_update", "DEBUG")
            frappe.msgprint("create_document is FALSE - nothing to do", indicator="orange")
    
    def detect_json_structure(self, json_data):
        """Detect the structure of the provided JSON."""
        if isinstance(json_data, dict):
            if "doctypes" in json_data and isinstance(json_data["doctypes"], list):
                return "multiple_doctypes"
            if "name" in json_data or "doctype" in json_data:
                if "fields" in json_data or "module" in json_data:
                    return "single_doctype"
        
        if isinstance(json_data, list):
            if json_data and isinstance(json_data[0], dict):
                if "fieldname" in json_data[0] or "label" in json_data[0]:
                    return "fields_only"
        
        return "unknown"
    
    def create_doctypes(self):
        """Main method to create DocType(s) with intelligent JSON parsing."""
        frappe.log_error("CREATE_DOCTYPES METHOD CALLED", "DEBUG")
        frappe.msgprint("Starting create_doctypes...", indicator="blue")
        
        if not self.doctype_field_json:
            frappe.throw(_("DocType Field JSON is required"))
        
        try:
            json_data = frappe.parse_json(self.doctype_field_json)
            frappe.msgprint("JSON parsed in create_doctypes", indicator="green")
        except Exception as e:
            error_msg = _("Invalid JSON format: {0}").format(str(e))
            frappe.log_error(
                message=f"JSON Parse Error:\n{self.doctype_field_json}\n\nError: {str(e)}",
                title="JSON Parse Failed"
            )
            frappe.throw(error_msg)
        
        json_structure = self.detect_json_structure(json_data)
        frappe.msgprint(f"Structure: {json_structure}", indicator="blue")
        
        created_doctypes = []
        
        if json_structure == "multiple_doctypes":
            frappe.msgprint("Creating multiple doctypes...", indicator="blue")
            created_doctypes = self.create_multiple_doctypes(json_data)
            
        elif json_structure == "single_doctype":
            frappe.msgprint("Creating single doctype...", indicator="blue")
            doctype_name = self.create_doctype_from_definition(json_data)
            created_doctypes = [doctype_name]
            
        elif json_structure == "fields_only":
            frappe.msgprint("Creating from fields array...", indicator="blue")
            doctype_name = self.create_doctype_from_fields_array(json_data)
            created_doctypes = [doctype_name]
        else:
            frappe.throw(_("Unrecognized JSON structure"))
        
        # Success message
        if created_doctypes:
            success_msg = _("Successfully created {0} DocType(s):<br><ul>{1}</ul>").format(
                len(created_doctypes),
                "".join([f"<li>{dt}</li>" for dt in created_doctypes])
            )
            
            frappe.msgprint(
                msg=success_msg,
                title=_("Success"),
                indicator="green"
            )
        
        frappe.log_error(f"DocTypes created: {', '.join(created_doctypes)}", "DEBUG SUCCESS")
    
    def create_multiple_doctypes(self, json_data):
        """Create multiple DocTypes from a JSON structure."""
        doctypes_list = json_data.get("doctypes", [])
        
        if not doctypes_list:
            frappe.throw(_("No doctypes found in JSON"))
        
        frappe.msgprint(f"Found {len(doctypes_list)} doctypes to create", indicator="blue")
        
        created_doctypes = []
        failed_doctypes = []
        
        # Sort to create child tables first
        doctypes_list_sorted = sorted(
            doctypes_list,
            key=lambda x: x.get("istable", 0),
            reverse=True
        )
        
        for idx, doctype_def in enumerate(doctypes_list_sorted, 1):
            doctype_name = doctype_def.get("name", "Unknown")
            frappe.msgprint(f"Creating {idx}/{len(doctypes_list_sorted)}: {doctype_name}", indicator="blue")
            
            try:
                created_name = self.create_doctype_from_definition(doctype_def)
                created_doctypes.append(created_name)
                frappe.msgprint(f"✓ Created: {created_name}", indicator="green")
                
            except Exception as e:
                error_msg = f"Error creating DocType '{doctype_name}': {str(e)}"
                frappe.log_error(
                    message=f"{error_msg}\n\nTraceback:\n{frappe.get_traceback()}",
                    title=f"DocType Creation Error: {doctype_name}"
                )
                frappe.msgprint(error_msg, indicator="red")
                failed_doctypes.append(doctype_name)
                continue
        
        if failed_doctypes:
            frappe.msgprint(
                _("Failed to create {0} DocType(s): {1}").format(
                    len(failed_doctypes),
                    ", ".join(failed_doctypes)
                ),
                indicator="orange"
            )
        
        return created_doctypes
    
    def create_doctype_from_definition(self, doctype_def):
        """Create a DocType from a complete definition dictionary."""
        doctype_name = doctype_def.get("name") or self.get("doctype_name")
        
        frappe.msgprint(f"Processing: {doctype_name}", indicator="blue")
        
        if not doctype_name:
            frappe.throw(_("DocType name is required in JSON or form"))
        
        # Check if DocType already exists
        if frappe.db.exists("DocType", doctype_name):
            frappe.msgprint(
                _("DocType '{0}' already exists - skipping").format(doctype_name),
                indicator="orange"
            )
            return doctype_name
        
        module = doctype_def.get("module") or self.get("module")
        if not module:
            frappe.throw(_("Module is required for DocType '{0}'").format(doctype_name))
        
        fields = doctype_def.get("fields", [])
        if not fields:
            frappe.throw(_("At least one field is required for DocType '{0}'").format(doctype_name))
        
        frappe.msgprint(f"DocType: {doctype_name}, Module: {module}, Fields: {len(fields)}", indicator="blue")
        
        # Extract properties
        is_child = doctype_def.get("istable", self.get("is_child", 0))
        is_single = doctype_def.get("issingle", self.get("is_single", 0))
        is_submittable = doctype_def.get("is_submittable", self.get("is_submittable", 0))
        autoname = doctype_def.get("autoname")
        
        # Build DocType dictionary
        doctype_dict = {
            "doctype": "DocType",
            "name": doctype_name,
            "module": module,
            "track_changes": 1,
            "istable": 1 if is_child else 0,
            "issingle": 1 if is_single else 0,
            "is_submittable": 1 if is_submittable else 0,
            "fields": fields,
            "quick_entry": 1 if not is_child else 0,
        }
        
        if autoname:
            doctype_dict["autoname"] = autoname
        elif not is_single and not is_child:
            doctype_dict["autoname"] = "prompt"
        
        doctype_dict["permissions"] = [{
            "role": "System Manager",
            "read": 1,
            "write": 1,
            "create": 1,
            "delete": 1,
        }]
        
        frappe.msgprint(f"Creating DocType document for: {doctype_name}", indicator="blue")
        
        try:
            new_doctype = frappe.get_doc(doctype_dict)
            new_doctype.insert(ignore_permissions=True)
            
            frappe.msgprint(f"✓ Successfully inserted: {doctype_name}", indicator="green")
            return doctype_name
            
        except Exception as e:
            error_detail = f"Error creating DocType {doctype_name}:\n{str(e)}\n\n{frappe.get_traceback()}"
            frappe.log_error(message=error_detail, title=f"DocType Creation Failed: {doctype_name}")
            frappe.msgprint(f"Failed to create {doctype_name}: {str(e)}", indicator="red")
            raise
    
    def create_doctype_from_fields_array(self, fields):
        """Create DocType from simple fields array."""
        if not self.get("doctype_name"):
            frappe.throw(_("DocType Name is required"))
        
        if not self.get("module"):
            frappe.throw(_("Module is required"))
        
        doctype_name = self.doctype_name
        module = self.module
        
        if frappe.db.exists("DocType", doctype_name):
            frappe.throw(_("DocType '{0}' already exists").format(doctype_name))
        
        doctype_dict = {
            "doctype": "DocType",
            "name": doctype_name,
            "module": module,
            "track_changes": 1,
            "istable": 0,
            "issingle": 0,
            "fields": fields,
            "quick_entry": 1,
            "autoname": "prompt",
            "permissions": [{
                "role": "System Manager",
                "read": 1,
                "write": 1,
                "create": 1,
                "delete": 1,
            }]
        }
        
        try:
            new_doctype = frappe.get_doc(doctype_dict)
            new_doctype.insert(ignore_permissions=True)
            return doctype_name
        except Exception as e:
            frappe.log_error(
                message=f"Error creating DocType {doctype_name}:\n{frappe.get_traceback()}",
                title=f"DocType Creation Failed: {doctype_name}"
            )
            raise


# Standalone whitelisted functions
@frappe.whitelist()
def preview_json_structure(json_str):
    """API endpoint to preview JSON structure without creating."""
    if not json_str:
        return {"error": "No JSON provided", "valid": False}
    
    try:
        json_data = frappe.parse_json(json_str)
        temp_doc = DoctypeCreator()
        structure = temp_doc.detect_json_structure(json_data)
        
        preview = {
            "structure_type": structure,
            "valid": structure != "unknown"
        }
        
        if structure == "multiple_doctypes":
            doctypes_list = json_data.get("doctypes", [])
            preview["doctype_count"] = len(doctypes_list)
            preview["doctype_names"] = [d.get("name") for d in doctypes_list]
            preview["modules"] = list(set([d.get("module") for d in doctypes_list if d.get("module")]))
            total_fields = sum(len(d.get("fields", [])) for d in doctypes_list)
            preview["total_fields"] = total_fields
            child_tables = [d.get("name") for d in doctypes_list if d.get("istable")]
            preview["child_tables"] = child_tables
            
        elif structure == "single_doctype":
            preview["doctype_name"] = json_data.get("name", "Not specified")
            preview["module"] = json_data.get("module", "Not specified")
            preview["field_count"] = len(json_data.get("fields", []))
            preview["is_child"] = bool(json_data.get("istable"))
            preview["is_submittable"] = bool(json_data.get("is_submittable"))
            
        elif structure == "fields_only":
            preview["field_count"] = len(json_data)
            preview["requires_form_data"] = True
            preview["message"] = "DocType Name and Module must be provided in the form"
        else:
            preview["error"] = "Unrecognized JSON structure"
        
        return preview
        
    except Exception as e:
        return {"error": str(e), "valid": False}


@frappe.whitelist()
def validate_json_syntax(json_str):
    """Validate JSON syntax without checking structure."""
    if not json_str:
        return {"valid": False, "error": "No JSON provided"}
    
    try:
        frappe.parse_json(json_str)
        return {"valid": True, "message": "JSON syntax is valid"}
    except Exception as e:
        return {"valid": False, "error": str(e)}