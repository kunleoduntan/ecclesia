# ecclesia/www/apply.py
import frappe

login_required = False

def get_context(context):
    context.no_cache      = 1
    context.show_sidebar  = False
    context.no_breadcrumbs= True
    context.title         = "Careers"

    # Embed CSRF token so the standalone HTML page can POST without cookie issues
    try:
        context.csrf_token = frappe.local.session.data.get("csrf_token") or \
                             frappe.generate_hash(length=16)
    except Exception:
        context.csrf_token = ""