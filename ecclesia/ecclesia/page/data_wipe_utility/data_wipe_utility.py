import frappe
from frappe import _
import json


def get_context(context):
	frappe.only_for("System Manager")
	context.no_breadcrumbs = True
	context.title = "Data Wipe Utility"