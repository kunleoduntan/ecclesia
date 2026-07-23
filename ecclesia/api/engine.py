"""
Ecclesia WFH – Activity Engine  (ecclesia/api/engine.py)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Complete Activity Tracking Engine:
  1. Tracks all DocType events (Submit, Cancel, Update, Create)
  2. Creates Work Activity Log entries automatically
  3. Auto-creates fallback Work Session if none exists
  4. Validates sessions before using them
  5. Handles missing/invalid sessions gracefully
  6. Applies scoring with dampening and daily caps
  7. Updates session heartbeats
"""

import frappe
from frappe.utils import now_datetime, nowdate, flt, get_datetime
from datetime import timedelta

from ecclesia.ecclesia.doctype.wfh_activity_mapping.wfh_activity_mapping import (
    get_active_mappings,
)


# ── Public entry point ─────────────────────────────────────────────────────────

def log_activity(doc, method):
    """
    Universal hook for all DocType events.
    Wired via hooks.py doc_events.
    
    Complete flow:
    1. Check mapping table → exit if not tracked
    2. Check event enabled → exit if not
    3. Resolve employee → exit if none
    4. Find or create session → auto-creates if missing
    5. Get scoring config
    6. Calculate scores
    7. Write Work Activity Log (validates session)
    8. Update session heartbeat (validates session)
    """
    try:
        # Step 1: Check if this DocType is tracked
        mappings = get_active_mappings()
        if not mappings:
            return

        doctype_cfg = mappings.get(doc.doctype)
        if not doctype_cfg:
            return

        # Step 2: Check if this event is enabled
        method_key = _normalise_method(method)
        if not doctype_cfg.get(method_key):
            return

        # Step 3: Resolve employee
        employee = _resolve_employee()
        if not employee:
            return

        # Step 4: Find or create session (always returns valid session or None)
        session = _find_or_create_session(employee)
        
        # Step 5: Get Activity Configuration
        config = _get_config(doc.doctype)
        
        # Step 6: Calculate scores
        business_value = _extract_value(doc, config) if config else 0.0
        raw_score = _calculate_raw_score(config, business_value)
        dampened, is_dampened = _apply_dampening(config, employee, raw_score)
        final = _apply_daily_cap(config, employee, doc.doctype, dampened)

        # Step 7: Write Work Activity Log (validates session internally)
        _write_log(
            employee=employee,
            doc=doc,
            action=_map_method_to_action(method),
            module=doctype_cfg.get("module", ""),
            config=config,
            session=session,
            business_value=business_value,
            raw_score=raw_score,
            dampened_points=dampened,
            final_points=final,
            is_dampened=is_dampened,
        )

        # Step 8: Update session heartbeat (validates session internally)
        if session:
            _update_heartbeat(session)

    except Exception as e:
        frappe.log_error(
            title="WFH Activity Engine Error",
            message=(
                f"DocType: {getattr(doc,'doctype','?')} | "
                f"Method: {method} | Name: {getattr(doc,'name','?')}\n"
                f"Error: {str(e)}\n"
                f"Traceback: {frappe.get_traceback()}"
            ),
        )


# ── Helper Functions ───────────────────────────────────────────────────────────

def _normalise_method(method):
    """Normalize method names to standard event names."""
    mapping = {
        "on_submit": "on_submit",
        "on_cancel": "on_cancel",
        "on_update": "on_update",
        "on_save": "on_update",
        "after_insert": "after_insert",
        "before_insert": "after_insert",
        "on_trash": "on_cancel",
        "validate": "on_update",
        "before_save": "on_update",
    }
    return mapping.get(method, method)


def _map_method_to_action(method):
    """Map method names to human-readable actions."""
    mapping = {
        "on_submit": "Submit",
        "on_cancel": "Cancel",
        "on_update": "Update",
        "on_save": "Update",
        "after_insert": "Create",
        "before_insert": "Create",
        "on_trash": "Cancel",
        "validate": "Update",
        "before_save": "Update",
    }
    return mapping.get(method, "Update")


def _resolve_employee():
    """
    Get employee record for current session user.
    Returns None if no employee record exists.
    """
    try:
        if not frappe.session or not frappe.session.user:
            return None
        
        user = frappe.session.user
        
        # Skip guest users
        if user == "Guest":
            return None
        
        # Get employee (Administrator can also have employee record)
        return frappe.db.get_value(
            "Employee",
            {"user_id": user, "status": "Active"},
            "name",
        )
    except Exception:
        return None


def _find_or_create_session(employee):
    """
    Find open session or create a fallback Work Session.
    
    Priority:
    1. Existing open Work Session
    2. Existing open WFH Session
    3. Auto-create fallback Work Session
    
    Always validates that the session actually exists in the database.
    Never returns an invalid session name.
    """
    if not employee:
        return None
    
    try:
        # Check Work Session first (new system)
        session = frappe.db.get_value(
            "Work Session",
            {
                "employee": employee,
                "date": nowdate(),
                "status": ("in", ["Open", "Flagged"]),
                "docstatus": ("!=", 2),
            },
            "name",
            order_by="check_in_time desc"
        )
        if session:
            # Verify it actually exists in the database
            if frappe.db.exists("Work Session", session):
                return session
            else:
                frappe.log_error(
                    f"Found session name {session} in query but it doesn't exist in Work Session table",
                    "WFH Engine Session Mismatch"
                )

        # Check WFH Session (legacy)
        session = frappe.db.get_value(
            "WFH Session",
            {
                "employee": employee,
                "date": nowdate(),
                "status": "Open",
                "docstatus": ("!=", 2),
            },
            "name",
            order_by="check_in_time desc"
        )
        if session:
            # Verify it actually exists in the database
            if frappe.db.exists("WFH Session", session):
                return session
            else:
                frappe.log_error(
                    f"Found session name {session} in query but it doesn't exist in WFH Session table",
                    "WFH Engine Session Mismatch"
                )
        
        # No valid session exists - create fallback
        return _create_fallback_session(employee)
        
    except Exception as e:
        frappe.log_error(
            f"Session lookup error for employee {employee}: {str(e)}",
            "WFH Engine Session"
        )
        # Last resort - try to create a session
        try:
            return _create_fallback_session(employee)
        except Exception:
            return None


def _create_fallback_session(employee):
    """
    Create a fallback Work Session when no session exists.
    This ensures activity tracking always works.
    """
    try:
        # Detect work mode
        work_mode = _detect_work_mode(employee)
        
        # Get employee details
        employee_name = frappe.db.get_value("Employee", employee, "employee_name")
        
        # Create Work Session
        session = frappe.new_doc("Work Session")
        session.employee      = employee
        session.employee_name = employee_name
        session.date          = nowdate()
        session.check_in_time = now_datetime()
        session.work_mode     = work_mode
        session.status        = "Open"
        session.auto_created  = 1
        session.source        = "Auto-created by Activity Engine (fallback)"
        
        # Capture device info if available
        try:
            if hasattr(frappe.local, 'request_ip'):
                session.ip_address = frappe.local.request_ip
            if frappe.request and hasattr(frappe.request, 'headers'):
                user_agent = frappe.request.headers.get("User-Agent") or ""
                session.device_info = user_agent[:200]
        except Exception:
            pass
        
        session.insert(ignore_permissions=True)
        frappe.db.commit()
        
        return session.name
        
    except Exception as e:
        frappe.log_error(
            f"Failed to create fallback session for {employee}: {str(e)}\n{frappe.get_traceback()}",
            "WFH Engine Fallback Error"
        )
        return None


def _detect_work_mode(employee):
    """
    Detect work mode (WFH/WFO) for an employee.
    Checks: WFH Schedule → WFH Request → WFO Schedule → Default WFH
    """
    try:
        today = nowdate()
        
        # Check WFH Schedule
        wfh_schedule = frappe.db.sql("""
            SELECT wfh_status 
            FROM `tabWFH Schedule`
            WHERE employee = %s
              AND date = %s
              AND docstatus = 1
            LIMIT 1
        """, (employee, today), as_dict=True)
        
        if wfh_schedule:
            status = wfh_schedule[0].wfh_status
            if status in ("WFH", "Work From Home"):
                return "WFH"
            elif status in ("WFO", "Work From Office"):
                return "WFO"
        
        # Check WFH Request (approved WFH for today)
        wfh_request = frappe.db.sql("""
            SELECT name 
            FROM `tabWFH Request`
            WHERE employee = %s
              AND status = 'Approved'
              AND from_date <= %s
              AND to_date >= %s
              AND docstatus = 1
            LIMIT 1
        """, (employee, today, today), as_dict=True)
        
        if wfh_request:
            return "WFH"
        
        # Check WFO Schedule
        wfo_schedule = frappe.db.get_value(
            "WFO Schedule",
            {"employee": employee, "date": today, "docstatus": 1},
            "name"
        )
        
        if wfo_schedule:
            return "WFO"
        
        # Default: WFH
        return "WFH"
        
    except Exception as e:
        frappe.log_error(
            f"Error detecting work mode for {employee}: {str(e)}",
            "WFH Engine Mode Detection"
        )
        return "WFH"


def _get_config(doctype):
    """
    Get Activity Configuration for a DocType.
    Returns config document or None.
    """
    try:
        name = frappe.db.get_value(
            "Activity Configuration",
            {"doctype_name": doctype, "is_active": 1},
            "name",
        )
        if name:
            return frappe.get_doc("Activity Configuration", name)
        return None
    except Exception:
        return None


def _extract_value(doc, config):
    """
    Extract business value from document based on config.
    """
    if not config or not config.value_field:
        return 0.0
    
    try:
        value = getattr(doc, config.value_field, 0)
        return flt(value or 0)
    except Exception:
        return 0.0


def _calculate_raw_score(config, business_value):
    """
    Calculate raw score based on Activity Configuration rules.
    Returns default 5 points if no config exists.
    """
    if not config:
        return 5.0

    try:
        if config.points_rule == "Fixed":
            raw = flt(config.base_points)
            
        elif config.points_rule == "Percentage of Value":
            raw = flt(config.base_points) + (business_value * flt(config.base_points) / 100)
            
        else:  # Formula
            raw = flt(config.base_points)
            if config.value_multiplier_enabled and flt(config.value_divisor):
                bonus = min(
                    business_value / flt(config.value_divisor),
                    flt(config.max_value_bonus or 50)
                )
                raw += bonus

        # Apply role-based weight multiplier
        raw = _apply_role_weight(config, raw)
        
        return round(raw, 4)
        
    except Exception as e:
        frappe.log_error(
            f"Error calculating raw score for {config.doctype_name}: {str(e)}",
            "WFH Engine Scoring"
        )
        return 5.0


def _apply_role_weight(config, raw):
    """
    Apply role-based weight multiplier to score.
    """
    if not config or not hasattr(config, 'role_weights') or not config.role_weights:
        return raw
    
    try:
        user_roles = frappe.get_roles(frappe.session.user)
        for row in config.role_weights:
            if row.role in user_roles:
                return round(raw * flt(row.weight_multiplier or 1.0), 4)
    except Exception:
        pass
    
    return raw


def _apply_dampening(config, employee, raw):
    """
    Apply frequency dampening to prevent gaming.
    Returns (score, is_dampened).
    """
    if not config or not config.frequency_dampening_enabled:
        return raw, False
    
    try:
        window = int(config.dampening_window_minutes or 30)
        threshold = 3
        since = get_datetime(now_datetime()) - timedelta(minutes=window)
        
        count = frappe.db.count(
            "Work Activity Log",
            {
                "employee": employee,
                "reference_doctype": config.doctype_name,
                "timestamp": (">=", since),
            },
        )
        
        if count >= threshold:
            multiplier = flt(config.dampening_multiplier or 0.5)
            return round(raw * multiplier, 4), True
        
        return raw, False
        
    except Exception as e:
        frappe.log_error(
            f"Error applying dampening: {str(e)}",
            "WFH Engine Dampening"
        )
        return raw, False


def _apply_daily_cap(config, employee, doctype, score):
    """
    Apply daily point cap per DocType.
    """
    try:
        if config and config.daily_cap_points:
            cap = flt(config.daily_cap_points)
        else:
            # Try to get global default from WFH Activity Mapping
            try:
                # Use the default record name
                cap = flt(
                    frappe.db.get_value("WFH Activity Mapping", "Default", "default_daily_cap") or 200
                )
            except Exception:
                cap = 200
    except Exception:
        cap = 200
    
    try:
        # Calculate points already earned today for this DocType
        earned = frappe.db.sql(
            """
            SELECT COALESCE(SUM(points), 0) 
            FROM `tabWork Activity Log` 
            WHERE employee = %s 
              AND reference_doctype = %s 
              AND date = %s
            """,
            (employee, doctype, nowdate()),
        )[0][0]
        
        # Return remaining points under cap
        return round(max(0, min(score, cap - flt(earned))), 4)
        
    except Exception as e:
        frappe.log_error(
            f"Error applying daily cap: {str(e)}",
            "WFH Engine Daily Cap"
        )
        return round(score, 4)


def _write_log(employee, doc, action, module, config, session,
               business_value, raw_score, dampened_points, final_points, is_dampened):
    """
    Create Work Activity Log document.
    Validates session exists before using it.
    If session is invalid, tries to find/create a valid one.
    """
    try:
        # Validate session if provided
        valid_session = None
        if session:
            # Check if session actually exists in either Work Session or WFH Session
            session_exists = frappe.db.exists("Work Session", session) or frappe.db.exists("WFH Session", session)
            
            if session_exists:
                valid_session = session
            else:
                # Session doesn't exist - log error and try to find/create a new one
                frappe.log_error(
                    f"Invalid session {session} referenced for employee {employee}. Creating new session.",
                    "WFH Engine Invalid Session"
                )
                valid_session = _find_or_create_session(employee)
        
        # Get employee details
        employee_name = frappe.db.get_value("Employee", employee, "employee_name")
        department = frappe.db.get_value("Employee", employee, "department")
        
        # Create Work Activity Log
        log = frappe.new_doc("Work Activity Log")
        log.employee          = employee
        log.employee_name     = employee_name
        log.department        = department
        log.timestamp         = now_datetime()
        log.date              = nowdate()
        log.session           = valid_session or ""  # Use validated session or empty string
        log.reference_doctype = doc.doctype
        log.reference_name    = doc.name
        log.action            = action
        log.module            = module
        log.business_value    = business_value
        log.currency          = getattr(doc, "currency", None) or ""
        log.raw_score         = raw_score
        log.dampened_points   = dampened_points
        log.points            = final_points
        log.is_dampened       = 1 if is_dampened else 0
        log.config_ref        = config.name if config else ""
        
        log.insert(ignore_permissions=True)
        frappe.db.commit()
        
    except Exception as e:
        frappe.log_error(
            f"Error writing Work Activity Log: {str(e)}\n"
            f"Employee: {employee}, DocType: {doc.doctype}, Action: {action}\n"
            f"Traceback: {frappe.get_traceback()}",
            "WFH Engine Write Log"
        )


def _update_heartbeat(session_name):
    """
    Update last_activity_time on the session document.
    Validates session exists before updating.
    Handles missing sessions gracefully.
    """
    if not session_name:
        return
    
    try:
        # Check which doctype the session belongs to and update
        if frappe.db.exists("Work Session", session_name):
            frappe.db.set_value(
                "Work Session", session_name,
                {
                    "last_activity_time": now_datetime(),
                    "inactivity_flag": 0,
                    "status": "Open"
                },
                update_modified=False,
            )
            return
            
        if frappe.db.exists("WFH Session", session_name):
            frappe.db.set_value(
                "WFH Session", session_name,
                {
                    "last_activity_time": now_datetime(),
                    "inactivity_flag": 0,
                    "status": "Open"
                },
                update_modified=False,
            )
            return
            
        # Session doesn't exist in either doctype
        frappe.log_error(
            f"Heartbeat failed: Session '{session_name}' not found in Work Session or WFH Session tables",
            "WFH Engine Missing Session"
        )
            
    except Exception as e:
        frappe.log_error(
            f"Error updating heartbeat for session {session_name}: {str(e)}",
            "WFH Engine Heartbeat"
        )


# ── Whitelisted API ────────────────────────────────────────────────────────────

@frappe.whitelist()
def preview_score(config_name, employee, business_value=0):
    """
    Preview scoring calculation for an Activity Configuration.
    """
    try:
        config = frappe.get_doc("Activity Configuration", config_name)
        bv = flt(business_value)
        raw = _calculate_raw_score(config, bv)
        d, di = _apply_dampening(config, employee, raw)
        final = _apply_daily_cap(config, employee, config.doctype_name, d)
        
        return {
            "raw_score": round(raw, 4),
            "dampened": round(d, 4),
            "final": round(final, 4),
            "is_dampened": di,
        }
    except Exception as e:
        frappe.log_error(f"Error previewing score: {str(e)}", "WFH Engine Preview")
        return {"error": str(e)}


@frappe.whitelist()
def seed_default_configurations():
    """
    Seed both mappings and scoring configurations.
    One-click setup for the entire WFH Activity Tracking system.
    """
    try:
        from ecclesia.ecclesia.doctype.wfh_activity_mapping.wfh_activity_mapping import (
            seed_default_mappings, ensure_default_record
        )
        
        # Create default mapping record
        ensure_default_record()
        
        # Seed default mappings
        mapping_result = seed_default_mappings()

        # Create default Activity Configurations
        configs = [
            ("Sales Invoice", "Sales", "Formula", 10, "grand_total", 1, 100000, 50, 1, 30, 0.5, 200),
            ("Sales Order", "Sales", "Formula", 8, "grand_total", 1, 200000, 30, 1, 30, 0.5, 150),
            ("Quotation", "Sales", "Formula", 5, "grand_total", 1, 500000, 20, 1, 30, 0.5, 100),
            ("Delivery Note", "Sales", "Fixed", 4, "", 0, 0, 0, 1, 30, 0.5, 80),
            ("Lead", "CRM", "Fixed", 3, "", 0, 0, 0, 1, 15, 0.4, 60),
            ("Opportunity", "CRM", "Fixed", 5, "", 0, 0, 0, 1, 20, 0.5, 80),
            ("Customer", "CRM", "Fixed", 3, "", 0, 0, 0, 1, 15, 0.4, 40),
            ("Payment Entry", "Accounts", "Formula", 8, "paid_amount", 1, 100000, 40, 1, 60, 0.3, 120),
            ("Journal Entry", "Accounts", "Fixed", 6, "", 0, 0, 0, 1, 30, 0.4, 100),
            ("Purchase Invoice", "Accounts", "Formula", 6, "grand_total", 1, 200000, 25, 1, 30, 0.5, 100),
            ("Purchase Order", "Buying", "Formula", 7, "grand_total", 1, 200000, 25, 1, 30, 0.5, 120),
            ("Supplier Quotation", "Buying", "Fixed", 4, "", 0, 0, 0, 1, 20, 0.5, 80),
            ("Stock Entry", "Stock", "Fixed", 4, "", 0, 0, 0, 1, 30, 0.4, 80),
            ("Material Request", "Stock", "Fixed", 3, "", 0, 0, 0, 1, 30, 0.4, 60),
        ]
        
        created = 0
        for dt, mod, rule, base, vf, vme, vd, mvb, fde, dw, dm, cap in configs:
            if frappe.db.exists("Activity Configuration", {"doctype_name": dt}):
                continue
                
            d = frappe.new_doc("Activity Configuration")
            d.doctype_name = dt
            d.module = mod
            d.points_rule = rule
            d.base_points = base
            d.value_field = vf
            d.value_multiplier_enabled = vme
            d.value_divisor = vd
            d.max_value_bonus = mvb
            d.frequency_dampening_enabled = fde
            d.dampening_window_minutes = dw
            d.dampening_multiplier = dm
            d.daily_cap_points = cap
            d.is_active = 1
            d.track_only_on_wfh = 1
            
            d.insert(ignore_permissions=True)
            created += 1
        
        frappe.db.commit()
        
        return (
            f"✅ Setup complete!\n"
            f"• Mappings: {mapping_result}\n"
            f"• Activity Configurations created: {created}\n"
            f"• The engine is now tracking activities with full scoring.\n"
            f"• Fallback sessions will be auto-created when needed."
        )
        
    except Exception as e:
        frappe.log_error(f"Error seeding configurations: {str(e)}\n{frappe.get_traceback()}", "WFH Engine Seed")
        return f"❌ Error: {str(e)}"


# ── Data Cleanup Utility ──────────────────────────────────────────────────────

@frappe.whitelist()
def cleanup_broken_references():
    """
    Clean up Work Activity Logs with broken session references.
    Run this once to fix any existing data issues.
    """
    try:
        # Find all Work Activity Logs with invalid session references
        broken_logs = frappe.db.sql("""
            SELECT wal.name, wal.session
            FROM `tabWork Activity Log` wal
            WHERE wal.session IS NOT NULL 
            AND wal.session != ''
            AND NOT EXISTS (
                SELECT 1 FROM `tabWFH Session` wfs WHERE wfs.name = wal.session
            )
            AND NOT EXISTS (
                SELECT 1 FROM `tabWork Session` ws WHERE ws.name = wal.session
            )
        """, as_dict=True)
        
        if not broken_logs:
            return "✅ No broken references found. Data is clean."
        
        # Clear broken session references
        broken_sessions = list(set([log.session for log in broken_logs]))
        
        for session in broken_sessions:
            frappe.db.sql("""
                UPDATE `tabWork Activity Log`
                SET session = ''
                WHERE session = %s
            """, session)
        
        frappe.db.commit()
        
        return (
            f"✅ Cleaned up {len(broken_logs)} Work Activity Log(s) "
            f"referencing {len(broken_sessions)} invalid session(s).\n"
            f"Broken sessions: {', '.join(broken_sessions)}"
        )
        
    except Exception as e:
        frappe.log_error(f"Cleanup error: {str(e)}", "WFH Engine Cleanup")
        return f"❌ Cleanup failed: {str(e)}"