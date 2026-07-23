"""
WFH Activity Mapping Controller  —  REGULAR DOCTYPE VERSION
Ecclesia Module

This version works with a REGULAR DocType (not Single).
Creates a default record named "Default" if it doesn't exist.
All functions reference the record by name or get the first active record.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

CACHE_KEY = "wfh_active_mappings"
CACHE_TTL  = 300  # 5 minutes

# Default scoring per DocType  (base_pts, value_field, value_divisor, max_bonus, daily_cap)
_DEFAULT_SCORING = {
    "Sales Invoice":     (10, "grand_total",   100000, 50,  200),
    "Sales Order":       (8,  "grand_total",   200000, 30,  150),
    "Quotation":         (5,  "grand_total",   500000, 20,  100),
    "Delivery Note":     (4,  "",              0,       0,   80),
    "Lead":              (3,  "",              0,       0,   60),
    "Opportunity":       (5,  "",              0,       0,   80),
    "Customer":          (3,  "",              0,       0,   40),
    "Payment Entry":     (8,  "paid_amount",   100000, 40,  120),
    "Journal Entry":     (6,  "",              0,       0,   100),
    "Purchase Invoice":  (6,  "grand_total",   200000, 25,  100),
    "Purchase Order":    (7,  "grand_total",   200000, 25,  120),
    "Supplier Quotation":(4,  "",              0,       0,   80),
    "Stock Entry":       (4,  "",              0,       0,   80),
    "Material Request":  (3,  "",              0,       0,   60),
}

DEFAULT_RECORD_NAME = "Default"


class WFHActivityMapping(Document):

    def validate(self):
        self._check_duplicate_doctypes()
        self._validate_events()
        self._auto_sync_config_links()

    def on_update(self):
        # Auto-create missing Activity Configurations for all active rows
        self._ensure_activity_configs()
        _flush_cache()
        frappe.publish_realtime(
            "wfh_mapping_updated",
            {"message": "Mappings updated — engine reloaded."},
            user=frappe.session.user,
        )

    # ── Validation ──────────────────────────────────────────────────────────────

    def _check_duplicate_doctypes(self):
        seen = set()
        for row in (self.mappings or []):
            if not row.doctype_name:
                continue
            if row.doctype_name in seen:
                frappe.throw(
                    _("Row {0}: <b>{1}</b> appears more than once.").format(
                        row.idx, row.doctype_name)
                )
            seen.add(row.doctype_name)

    def _validate_events(self):
        for row in (self.mappings or []):
            if not row.is_active or not row.doctype_name:
                continue
            if not any([row.on_submit, row.on_cancel, row.on_update, row.after_insert]):
                frappe.throw(
                    _("Row {0} ({1}): select at least one event to track.").format(
                        row.idx, row.doctype_name)
                )

    def _auto_sync_config_links(self):
        """Keep has_activity_config and activity_config fields accurate."""
        for row in (self.mappings or []):
            if not row.doctype_name:
                continue
            config = frappe.db.get_value(
                "Activity Configuration",
                {"doctype_name": row.doctype_name, "is_active": 1},
                "name",
            )
            row.has_activity_config = 1 if config else 0
            row.activity_config     = config or ""

    def _ensure_activity_configs(self):
        """
        Auto-create Activity Configuration for every active mapping row
        that doesn't already have one. Uses sensible defaults.
        No manual configuration needed by the user.
        """
        created = 0
        for row in (self.mappings or []):
            if not row.is_active or not row.doctype_name:
                continue
            if frappe.db.exists("Activity Configuration", {"doctype_name": row.doctype_name}):
                continue
            _create_default_config(row.doctype_name, row.module_tag or "")
            created += 1
        if created:
            frappe.db.commit()
            frappe.msgprint(
                _("Auto-created Activity Configuration for {0} new DocType(s). "
                  "Default scoring applied. You can customise them anytime via "
                  "Activity Configuration list.").format(created),
                alert=True, indicator="green"
            )


# ── Default record creation ────────────────────────────────────────────────────

def _get_or_create_default_record():
    """
    Returns the default WFH Activity Mapping document (named 'Default').
    Creates it with safe defaults if it doesn't exist yet.
    """
    # Try to find an existing record, preferably the "Default" one
    try:
        # First, try to get the document by name
        if frappe.db.exists("WFH Activity Mapping", DEFAULT_RECORD_NAME):
            return frappe.get_doc("WFH Activity Mapping", DEFAULT_RECORD_NAME)
        
        # If no "Default" record, try to get the first active record
        first_record = frappe.db.get_value(
            "WFH Activity Mapping",
            {"is_active": 1, "docstatus": ("!=", 2)},
            "name",
            order_by="creation asc"
        )
        
        if first_record:
            return frappe.get_doc("WFH Activity Mapping", first_record)
        
        # If no record exists at all, create the default one
        return _create_default_record()
        
    except Exception as e:
        frappe.log_error(f"Error in _get_or_create_default_record: {str(e)}", "WFH Mapping")
        # Try to create it
        return _create_default_record()


def _create_default_record():
    """Create the default WFH Activity Mapping record."""
    try:
        doc = frappe.new_doc("WFH Activity Mapping")
        doc.is_active                  = 1
        doc.strict_wfh_only            = 0
        doc.default_daily_cap          = 200
        doc.inactivity_threshold_hours = 3
        
        # Use naming series or manual name
        if hasattr(doc, 'naming_series'):
            doc.naming_series = "WFH-MAP-.#####"
        else:
            # Set the name explicitly if no naming series
            doc.__newname = DEFAULT_RECORD_NAME
        
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        
        # If the name wasn't set to Default, rename it
        if doc.name != DEFAULT_RECORD_NAME:
            frappe.rename_doc("WFH Activity Mapping", doc.name, DEFAULT_RECORD_NAME, ignore_permissions=True)
            frappe.db.commit()
            doc = frappe.get_doc("WFH Activity Mapping", DEFAULT_RECORD_NAME)
        
        return doc
        
    except Exception as e:
        frappe.log_error(f"Error creating default record: {str(e)}", "WFH Mapping")
        raise frappe.ValidationError(
            _("Could not create default WFH Activity Mapping record. Error: {0}").format(str(e))
        )


def ensure_default_record():
    """
    Called by after_install. Creates the default record with settings
    and seeds all mappings + Activity Configurations in one shot.
    """
    doc = _get_or_create_default_record()

    # Set safe defaults if not already configured
    if not doc.is_active:
        doc.is_active = 1
    if not doc.default_daily_cap:
        doc.default_daily_cap = 200
    if not doc.inactivity_threshold_hours:
        doc.inactivity_threshold_hours = 3

    # Seed mappings if table is empty
    if not doc.mappings:
        _add_default_rows(doc)

    doc.save(ignore_permissions=True)
    frappe.db.commit()

    # Auto-create Activity Configurations
    doc._ensure_activity_configs()
    return "WFH Activity Mapping initialised successfully."


def _add_default_rows(doc):
    """Add the 14 standard DocType mappings to the document."""
    defaults = [
        # (doctype,              module,     submit, cancel, update, insert)
        ("Sales Invoice",    "Sales",     1, 1, 0, 0),
        ("Sales Order",      "Sales",     1, 1, 0, 0),
        ("Quotation",        "Sales",     1, 0, 0, 0),
        ("Delivery Note",    "Sales",     1, 0, 0, 0),
        ("Lead",             "CRM",       0, 0, 1, 0),
        ("Opportunity",      "CRM",       0, 0, 1, 0),
        ("Customer",         "CRM",       0, 0, 0, 1),
        ("Payment Entry",    "Accounts",  1, 1, 0, 0),
        ("Journal Entry",    "Accounts",  1, 0, 0, 0),
        ("Purchase Invoice", "Accounts",  1, 0, 0, 0),
        ("Purchase Order",   "Buying",    1, 0, 0, 0),
        ("Supplier Quotation","Buying",   1, 0, 0, 0),
        ("Stock Entry",      "Stock",     1, 0, 0, 0),
        ("Material Request", "Stock",     1, 0, 0, 0),
    ]
    
    # Get existing doctypes to avoid duplicates
    existing = set()
    for row in (doc.mappings or []):
        if row.doctype_name:
            existing.add(row.doctype_name)
    
    # Add new rows
    added = 0
    for dt, mod, sub, can, upd, ins in defaults:
        if dt in existing:
            continue
        doc.append("mappings", {
            "doctype_name": dt, 
            "module_tag": mod, 
            "is_active": 1,
            "on_submit": sub, 
            "on_cancel": can,
            "on_update": upd, 
            "after_insert": ins,
        })
        added += 1
    
    if added > 0:
        frappe.msgprint(
            _("Added {0} new DocType mappings.").format(added),
            alert=True
        )


def _create_default_config(doctype_name, module=""):
    """
    Create a sensible Activity Configuration for a DocType.
    Uses pre-defined defaults where available, otherwise creates
    a simple Fixed 5-point config so tracking works out of the box.
    """
    if not module:
        module = frappe.db.get_value("DocType", doctype_name, "module") or ""

    scoring = _DEFAULT_SCORING.get(doctype_name)

    cfg = frappe.new_doc("Activity Configuration")
    cfg.doctype_name = doctype_name
    cfg.module       = module
    cfg.is_active    = 1
    cfg.track_only_on_wfh = 1

    if scoring:
        base, vf, vd, mvb, cap = scoring
        cfg.points_rule                = "Formula" if vf else "Fixed"
        cfg.base_points                = base
        cfg.value_field                = vf
        cfg.value_multiplier_enabled   = 1 if vf else 0
        cfg.value_divisor              = vd
        cfg.max_value_bonus            = mvb
        cfg.daily_cap_points           = cap
    else:
        cfg.points_rule     = "Fixed"
        cfg.base_points     = 5
        cfg.daily_cap_points = 100

    # Standard dampening for all
    cfg.frequency_dampening_enabled  = 1
    cfg.dampening_window_minutes     = 30
    cfg.dampening_multiplier         = 0.5

    cfg.insert(ignore_permissions=True)
    return cfg.name


# ── Runtime Cache ──────────────────────────────────────────────────────────────

def get_active_mappings():
    """
    Called by the engine on every DocType event (fast Redis cache lookup).
    Uses the first active WFH Activity Mapping record.
    NEVER raises an error — always returns a dict (empty if nothing configured).
    """
    cached = frappe.cache().get_value(CACHE_KEY)
    if cached is not None:
        return cached

    # Get the active mapping record
    record_name = frappe.db.get_value(
        "WFH Activity Mapping",
        {"is_active": 1, "docstatus": ("!=", 2)},
        "name",
        order_by="creation asc"
    )
    
    if not record_name:
        # No active record — try to create default
        try:
            ensure_default_record()
            record_name = DEFAULT_RECORD_NAME
        except Exception as e:
            frappe.log_error(f"WFH Mapping auto-create failed: {e}", "WFH Engine")
            frappe.cache().set_value(CACHE_KEY, {}, expires_in_sec=60)
            return {}

    # Get the rows
    rows = frappe.db.get_all(
        "WFH DocType Event Map",
        filters={
            "parenttype": "WFH Activity Mapping",
            "parent":     record_name,
            "is_active":  1,
        },
        fields=["doctype_name", "module_tag",
                "on_submit", "on_cancel", "on_update", "after_insert"],
    )

    result = {}
    for row in rows:
        if not row.doctype_name:
            continue
        result[row.doctype_name] = {
            "module":       row.module_tag or "",
            "on_submit":    bool(row.on_submit),
            "on_cancel":    bool(row.on_cancel),
            "on_update":    bool(row.on_update),
            "after_insert": bool(row.after_insert),
        }

    frappe.cache().set_value(CACHE_KEY, result, expires_in_sec=CACHE_TTL)
    return result


def _flush_cache():
    frappe.cache().delete_key(CACHE_KEY)


# ── Whitelisted API ────────────────────────────────────────────────────────────

@frappe.whitelist()
def flush_cache():
    _flush_cache()
    return "Cache flushed."


@frappe.whitelist()
def get_mapping_status():
    """Status panel data for the JS form."""
    try:
        # Get the active record
        record_name = frappe.db.get_value(
            "WFH Activity Mapping",
            {"is_active": 1, "docstatus": ("!=", 2)},
            "name",
            order_by="creation asc"
        )
        
        if not record_name:
            return {
                "total":            0,
                "active":           0,
                "with_scoring":     0,
                "without_scoring":  0,
                "globally_active":  False,
                "runtime_mappings": [],
            }
        
        globally_active = bool(
            frappe.db.get_value("WFH Activity Mapping", record_name, "is_active")
        )
        
        all_rows = frappe.db.get_all(
            "WFH DocType Event Map",
            filters={
                "parenttype": "WFH Activity Mapping",
                "parent": record_name
            },
            fields=["doctype_name", "is_active", "has_activity_config"],
        ) or []
        
        mappings = get_active_mappings()
        
        return {
            "total":            len(all_rows),
            "active":           sum(1 for r in all_rows if r.is_active),
            "with_scoring":     sum(1 for r in all_rows if r.has_activity_config),
            "without_scoring":  sum(1 for r in all_rows if r.is_active and not r.has_activity_config),
            "globally_active":  globally_active,
            "runtime_mappings": list(mappings.keys()),
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting mapping status: {str(e)}", "WFH Mapping")
        return {
            "total":            0,
            "active":           0,
            "with_scoring":     0,
            "without_scoring":  0,
            "globally_active":  False,
            "runtime_mappings": [],
        }


@frappe.whitelist()
def seed_default_mappings():
    """
    Called by the Seed Default Mappings button.
    Creates the default record if missing, adds default rows,
    and auto-creates Activity Configurations. Everything in one click.
    """
    try:
        # Get or create the default record
        doc = _get_or_create_default_record()

        # Set defaults if not configured
        if not doc.is_active:
            doc.is_active = 1
        if not doc.default_daily_cap:
            doc.default_daily_cap = 200
        if not doc.inactivity_threshold_hours:
            doc.inactivity_threshold_hours = 3

        # Add missing default rows
        _add_default_rows(doc)

        # Save the document with all mappings
        doc.save(ignore_permissions=True)
        frappe.db.commit()

        # Auto-create Activity Configurations for all rows
        doc._ensure_activity_configs()
        _flush_cache()

        added = len(doc.mappings)
        return (
            f"✅ Setup complete! {added} DocType mapping(s) active. "
            f"Activity Configurations auto-created with default scoring. "
            f"The engine is now live — no further configuration needed."
        )
    except Exception as e:
        frappe.log_error(f"seed_default_mappings error: {str(e)}", "WFH Mapping")
        frappe.throw(_("Setup failed: {0}").format(str(e)))