# policy_acknowledgement.py (web page controller)
import frappe

def get_context(context):
    policy_name  = frappe.form_dict.get("policy")
    employee_id  = frappe.form_dict.get("employee")

    if not policy_name or not employee_id:
        frappe.throw("Invalid request.")

    policy = frappe.get_doc("Company Policy", policy_name)
    ack    = frappe.db.get_value(
        "Policy Acknowledgement",
        {"policy": policy_name, "employee": employee_id, "status": "Pending"},
        ["name", "status", "acknowledged_on"],
        as_dict=True
    )

    context.policy   = policy
    context.ack      = ack
    context.employee = frappe.get_doc("Employee", employee_id)
    context.already_acknowledged = (ack and ack.status == "Acknowledged")