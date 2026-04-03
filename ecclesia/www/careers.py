# FILE: apps/ecclesia/ecclesia/www/careers.py
# URL: /careers (public, no login required)
import frappe

def get_context(context):
    context.title = "Careers — Open Positions"
    context.no_cache = 1