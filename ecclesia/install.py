"""
ecclesia/install.py
Runs after bench install-app and bench migrate.
"""

import frappe


# ─────────────────────────────────────────────────────────────────────────────
# CRM DOCTYPES — telephone call buttons (existing)
# ─────────────────────────────────────────────────────────────────────────────

CRM_DOCTYPES = {
    "Lead":        [{"field": "mobile_no", "label": "Mobile"}, {"field": "phone", "label": "Phone"}],
    "Contact":     [{"field": "mobile_no", "label": "Mobile"}, {"field": "phone", "label": "Phone"}],
    "Customer":    [{"field": "mobile_no", "label": "Mobile"}],
    "Opportunity": [{"field": "contact_mobile", "label": "Mobile"}],
    "Employee":    [{"field": "cell_number", "label": "Mobile"}, {"field": "company_email", "label": "Internal"}],
}


def _make_script(doctype, fields):
    """
    Frappe Client Scripts run as the body of a frappe.ui.form.on refresh handler.
    The script body must use frappe.ui.form.on() — frm is NOT available as a bare variable.
    """
    field_json = ", ".join(
        '{{"field": "{field}", "label": "{label}"}}'.format(**f)
        for f in fields
    )
    return (
        "// Ecclesia Telephone - Call Buttons for {doctype}\n"
        "frappe.ui.form.on(\"{doctype}\", {{\n"
        "    refresh: function(frm) {{\n"
        "        var _ec_fields = [{field_json}];\n"
        "        _ec_fields.forEach(function(f) {{\n"
        "            var number = frm.doc[f.field];\n"
        "            if (!number) return;\n"
        "            frm.add_custom_button(\n"
        "                String.fromCodePoint(0x1F4DE) + ' ' + f.label + ': ' + number,\n"
        "                function() {{\n"
        "                    if (window.ecclesia_telephone) {{\n"
        "                        ecclesia_telephone.call_number(number, frm.doctype, frm.docname);\n"
        "                    }} else {{\n"
        "                        frappe.show_alert({{message: 'Ecclesia not loaded', indicator: 'orange'}});\n"
        "                    }}\n"
        "                }},\n"
        "                __('Call')\n"
        "            );\n"
        "        }});\n"
        "    }}\n"
        "}});\n"
    ).format(doctype=doctype, field_json=field_json)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINTS
# ─────────────────────────────────────────────────────────────────────────────

def after_install():
    install_client_scripts()
    _create_wa_settings()
    frappe.db.commit()


def after_migrate():
    install_client_scripts()
    _create_wa_settings()
    frappe.db.commit()


def before_uninstall():
    # Remove telephone client scripts
    for doctype in CRM_DOCTYPES:
        name = "Ecclesia Call Buttons - " + doctype
        if frappe.db.exists("Client Script", name):
            frappe.delete_doc("Client Script", name, ignore_permissions=True)

    # Remove WA Settings singleton
    if frappe.db.exists("WA Settings", "WA Settings"):
        frappe.delete_doc("WA Settings", "WA Settings", ignore_permissions=True)

    frappe.db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# TELEPHONE — client script installer (existing, unchanged)
# ─────────────────────────────────────────────────────────────────────────────

def install_client_scripts():
    for doctype, fields in CRM_DOCTYPES.items():
        name = "Ecclesia Call Buttons - " + doctype
        if frappe.db.exists("Client Script", name):
            doc = frappe.get_doc("Client Script", name)
        else:
            doc = frappe.new_doc("Client Script")
            doc.name = name

        doc.dt      = doctype
        doc.script  = _make_script(doctype, fields)
        doc.enabled = 1
        doc.view    = "Form"
        doc.save(ignore_permissions=True)

    frappe.db.commit()
    print("Ecclesia: Client Scripts installed for", list(CRM_DOCTYPES.keys()))


# ─────────────────────────────────────────────────────────────────────────────
# WA ENGINE — default settings record
# ─────────────────────────────────────────────────────────────────────────────

def _create_wa_settings():
    """
    Create the WA Settings singleton with safe defaults if it doesn't
    exist yet. This prevents errors on first desk load before the admin
    has opened the settings form.
    Safe to call repeatedly — skips silently if already exists.
    """
    if not frappe.db.exists("DocType", "WA Settings"):
        # DocType not migrated yet — skip silently
        return

    if frappe.db.exists("WA Settings", "WA Settings"):
        return

    try:
        doc = frappe.new_doc("WA Settings")

        # WhatsApp — off by default until credentials are entered
        doc.wa_enabled            = 0
        doc.wa_api_version        = "v18.0"
        doc.default_country_code  = "234"

        # SMS — off by default
        doc.sms_enabled           = 0

        # Email — off by default
        doc.email_enabled         = 0

        # Internal Chat — on by default, needs no external credentials
        doc.internal_chat_enabled   = 1
        doc.chat_position           = "Bottom Right"
        doc.max_file_size_mb        = 25
        doc.enable_read_receipts    = 1
        doc.enable_typing_indicator = 1
        doc.enable_online_status    = 1
        doc.chat_retention_days     = 365

        doc.insert(ignore_permissions=True)
        print("Ecclesia: WA Settings created with defaults.")

    except Exception as e:
        # Non-fatal — admin can create the record manually via desk
        print(f"Ecclesia: Could not create WA Settings ({e}) — create manually via desk.")


"""
ecclesia_erequest/utils/install.py
Post-install setup: create roles and default settings.
"""
import frappe


ROLES = [
    {"role_name": "eRequest Employee", "desk_access": 0},
    {"role_name": "eRequest Manager",  "desk_access": 1},
    {"role_name": "eRequest Finance",  "desk_access": 1},
    {"role_name": "eRequest Admin",    "desk_access": 1},
]


def after_install():
    _create_roles()
    _create_email_templates()
    frappe.db.commit()
    frappe.logger().info("ecclesia_erequest: after_install completed.")


def _create_roles():
    for r in ROLES:
        if not frappe.db.exists("Role", r["role_name"]):
            doc = frappe.new_doc("Role")
            doc.role_name    = r["role_name"]
            doc.desk_access  = r["desk_access"]
            doc.insert(ignore_permissions=True)
            frappe.logger().info(f"Created role: {r['role_name']}")


def _create_email_templates():
    """Email templates are managed as fixture JSON files; nothing to do here."""
    pass
