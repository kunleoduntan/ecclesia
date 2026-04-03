# FILE: apps/ecclesia/ecclesia/www/recruitment.py
# URL: /recruitment (HR admin only)
import frappe

def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/recruitment"
        raise frappe.Redirect
    roles = frappe.get_roles(frappe.session.user)
    if not any(r in roles for r in ["HR Manager","HR User","System Manager","Recruitment Manager"]):
        frappe.throw("HR access required", frappe.PermissionError)
    context.title = "Recruitment Dashboard"
    context.no_cache = 1