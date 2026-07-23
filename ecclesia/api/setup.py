"""
Ecclesia – Setup & Diagnostics  (ecclesia/api/setup.py)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Setup script to initialize all required components:
  1. Create default WFH Activity Mapping
  2. Create default Activity Configurations
  3. Verify DocTypes exist
  4. Test the engine
"""

import frappe
from frappe.utils import nowdate, now_datetime


@frappe.whitelist()
def run_full_setup():
    """
    Complete setup - run this once to initialize everything.
    """
    results = []
    
    # Step 1: Initialize WFH Activity Mapping
    try:
        from ecclesia.ecclesia.doctype.wfh_activity_mapping.wfh_activity_mapping import (
            ensure_default_record, _get_or_create_default_record
        )
        ensure_default_record()
        results.append("✅ WFH Activity Mapping initialized")
    except Exception as e:
        results.append(f"❌ WFH Activity Mapping failed: {str(e)}")
    
    # Step 2: Seed default configurations
    try:
        from ecclesia.api.engine import seed_default_configurations
        config_result = seed_default_configurations()
        results.append(f"✅ Configurations seeded: {config_result}")
    except Exception as e:
        results.append(f"❌ Configurations seeding failed: {str(e)}")
    
    # Step 3: Verify required DocTypes exist
    required_doctypes = [
        "Work Session",
        "WFH Session", 
        "Work Activity Log",
        "Activity Configuration",
        "WFH Activity Mapping",
        "WFH DocType Event Map",
    ]
    
    for dt in required_doctypes:
        if frappe.db.exists("DocType", dt):
            results.append(f"✅ DocType '{dt}' exists")
        else:
            results.append(f"❌ DocType '{dt}' NOT FOUND - Please create it")
    
    # Step 4: Test create a Work Session
    try:
        test_employee = frappe.db.get_value(
            "Employee",
            {"status": "Active"},
            "name",
            order_by="creation asc"
        )
        
        if test_employee:
            # Create test session
            session = frappe.new_doc("Work Session")
            session.employee = test_employee
            session.date = nowdate()
            session.check_in_time = now_datetime()
            session.work_mode = "WFH"
            session.status = "Open"
            session.source = "Setup Test"
            session.insert(ignore_permissions=True)
            
            results.append(f"✅ Test Work Session created: {session.name}")
            
            # Test Work Activity Log
            log = frappe.new_doc("Work Activity Log")
            log.employee = test_employee
            log.timestamp = now_datetime()
            log.date = nowdate()
            log.session = session.name
            log.reference_doctype = "Sales Invoice"
            log.reference_name = "TEST-001"
            log.action = "Submit"
            log.module = "Sales"
            log.business_value = 0
            log.raw_score = 5
            log.dampened_points = 5
            log.points = 5
            log.insert(ignore_permissions=True)
            
            results.append(f"✅ Test Work Activity Log created: {log.name}")
            
            # Clean up test data
            log.delete()
            session.delete()
            frappe.db.commit()
            results.append("✅ Test data cleaned up")
        else:
            results.append("❌ No active employees found")
            
    except Exception as e:
        results.append(f"❌ Test failed: {str(e)}")
    
    # Step 5: Verify engine imports
    try:
        from ecclesia.api.engine import log_activity
        results.append("✅ Engine import successful")
    except Exception as e:
        results.append(f"❌ Engine import failed: {str(e)}")
    
    return "\n".join(results)


@frappe.whitelist()
def debug_engine():
    """
    Debug the engine - check what's configured and working.
    """
    debug_info = []
    
    # Check mappings
    try:
        from ecclesia.ecclesia.doctype.wfh_activity_mapping.wfh_activity_mapping import (
            get_active_mappings
        )
        mappings = get_active_mappings()
        debug_info.append(f"Active mappings: {len(mappings)}")
        debug_info.append(f"Mapped DocTypes: {list(mappings.keys())[:5]}...")
    except Exception as e:
        debug_info.append(f"Mappings error: {str(e)}")
    
    # Check session
    user = frappe.session.user
    debug_info.append(f"Current user: {user}")
    
    employee = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
    debug_info.append(f"Employee: {employee or 'Not found'}")
    
    if employee:
        # Check open sessions
        wfh_session = frappe.db.get_value(
            "WFH Session",
            {"employee": employee, "date": nowdate(), "status": "Open"},
            "name"
        )
        work_session = frappe.db.get_value(
            "Work Session",
            {"employee": employee, "date": nowdate(), "status": "Open"},
            "name"
        )
        debug_info.append(f"WFH Session: {wfh_session or 'None'}")
        debug_info.append(f"Work Session: {work_session or 'None'}")
    
    return "\n".join(debug_info)