"""
Frappe www page controller for /erequest-portal
Requires login — redirect to login page if not authenticated.
"""
import frappe

no_cache  = 1
no_sitemap = 1

def get_context(context):
    # Redirect unauthenticated users to Frappe's login page
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = (
            f"/login?redirect-to=/erequest-portal"
        )
        raise frappe.Redirect

    context.no_header  = True
    context.no_footer  = True
    context.title      = "eRequest Portal"
    context.site_url   = frappe.utils.get_url()
    context.csrf_token = frappe.sessions.get_csrf_token()
    return context
