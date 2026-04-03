# hooks.py — apps/ecclesia/ecclesia/hooks.py

app_name = "ecclesia"
app_title = "Ecclesia"
app_publisher = "Kunle Oduntan"
app_description = "Ecclesia Platform — Telephony, Finance, Payroll, Audit Intelligence, ESS, Customer & Supplier Self-Service Portals"
app_email = "kunleoduntan@gmail.com"
app_license = "MIT"
app_version = "1.0.0"

app_icon = "octicon octicon-shield"
app_color = "#2c3e50"

required_apps = ["frappe", "erpnext"]


# ───────────────── INSTALL / MIGRATE ─────────────────

# FIX 1: Removed duplicate after_install. Kept the erequest one as it was
# the last defined (and therefore the one that was actually active before).
# If you need both to run, use a list or merge logic into one function.
after_install = "ecclesia.ecclesia.doctype.erequest.erequest.after_install"

before_uninstall = "ecclesia.install.before_uninstall"

after_migrate = [
    "ecclesia.install.after_migrate",
    "ecclesia.api.ess_portal_custom_fields.after_migrate",
    "ecclesia.api.recruitment_portal_custom_fields.after_migrate",
    "ecclesia.api.portal_custom_fields.install",
    "ecclesia.setup_roles.create_roles_if_not_exist",
]

# ─── Website ──────────────────────────────────────────────────────────────────
website_route_rules = [
    {"from_route": "/erequest-portal", "to_route": "erequest_portal"},
]

# ───────────────── DESK ASSETS ─────────────────

app_include_css = [
    "/assets/ecclesia/css/global_form_styles.css",
    "/assets/ecclesia/css/telephone.css",
    "/assets/ecclesia/css/audit_styles.css",
]

app_include_js = [
    "/assets/ecclesia/js/telephone.js",
    "/assets/ecclesia/js/group_call.js",
    "/assets/ecclesia/js/audit_engine.js",
    "/assets/ecclesia/js/internal_chat.js",
    "assets/ecclesia/js/global_item_filter.js",
]


# ───────────────── DESK SIDEBAR APP ─────────────────

# add_to_apps_screen = [
#     {
#         "name": "mail-hub",
#         "logo": "/assets/ecclesia/images/mailvault-icon.svg",
#         "title": "MailVault",
#         "route": "/mail-hub",
#         "has_permission": "ecclesia.page.mail_hub.mail_hub.get_boot_data",
#     }
# ]


# ───────────────── DOCTYPE JS ─────────────────

doctype_js = {
    "Annual Budget": "public/js/annual_budget_manual.min.js",
    "Payments": "public/js/payments_list.min.js",
    "Bank Reconciliation": "public/js/bank_reconciliation_manual.min.js",
    "Payroll Entry": "public/js/payroll_entry_pension.min.js",
    "Salary Slip": "public/js/salary_slip_pension.min.js",
    "Receipts": "doctype/receipts/receipts.js",
    "Sales Invoice": "public/js/sales_invoice_payment.js",
    "Employee": "public/js/employee.js",
}


# ───────────────── DOC EVENTS ─────────────────

doc_events = {

    # TELEPHONY
    "Telephone Call Log": {
        "after_insert": "ecclesia.api.telephone_api.on_telephone_call_log_insert",
    },

    # FINANCE
    "Bank Reconciliation": {
        "validate": "ecclesia.ecclesia.doctype.bank_reconciliation.bank_reconciliation.validate_bank_reconciliation",
    },

    "Accounting Dimension": {
        "after_insert": "ecclesia.ecclesia.utils.accounting_dimensions.auto_add_to_payments",
    },

    "Payments": {
        "validate": "ecclesia.ecclesia.doctype.payments.payments.validate_payment",
        "before_submit": "ecclesia.ecclesia.doctype.payments.payments.before_submit_payment",
        "on_trash": "ecclesia.ecclesia.doctype.payments.payments.on_trash_payment",
    },

    "Batch Bank Transaction": {
        "validate": "ecclesia.ecclesia.doctype.batch_bank_transaction.batch_bank_transaction.validate_party_name",
        "before_save": "ecclesia.ecclesia.doctype.batch_bank_transaction.batch_bank_transaction.update_party_names",
        "on_submit": "ecclesia.ecclesia.doctype.batch_bank_transaction.batch_bank_transaction.on_batch_submit",
        "on_cancel": "ecclesia.ecclesia.doctype.batch_bank_transaction.batch_bank_transaction.on_batch_cancel",
    },

    # PAYROLL
    "Payroll Entry": {
        "on_submit": "ecclesia.pension_mgt_tasks.on_payroll_submit",
    },

    "Salary Slip": {
        "on_submit": [
            "ecclesia.pension_mgt_tasks.on_salary_slip_submit",
            "ecclesia.api.ess_portal_documents.notify_payslip_ready",
        ],
    },

    # COMPANY
    "Company": {
        "on_update": "ecclesia.utils.item_validator.clear_company_item_filter_cache"
    },

    # UNIVERSAL AUDIT + AUDIT ENGINE
    # FIX 2: Merged both "*" blocks into one. Previously the second block
    # was silently overwriting the first, so audit_trail hooks were never firing.
    "*": {
        "after_insert": "ecclesia.utils.audit_engine.log_event",
        "on_update": [
            "ecclesia.utils.audit_trail.on_amend_handler",
            "ecclesia.utils.audit_engine.log_event",
        ],
        "on_trash": "ecclesia.utils.audit_engine.log_delete",
        "on_submit": [
            "ecclesia.utils.audit_trail.on_submit_handler",
            "ecclesia.utils.audit_engine.log_event",
        ],
        "on_cancel": [
            "ecclesia.utils.audit_trail.on_cancel_handler",
            "ecclesia.utils.audit_engine.log_event",
        ],
        "on_update_after_submit": "ecclesia.utils.audit_trail.on_amend_handler",
    },

    "GL Entry": {
        "after_insert": "ecclesia.utils.gl_monitor.track_gl_entry",
        "on_cancel": "ecclesia.utils.gl_monitor.track_gl_cancellation",
    },

    "Journal Entry": {
        "on_submit": "ecclesia.utils.gl_monitor.flag_journal_entry_risks",
    },

    # CUSTOMER PORTAL
    "Quotation": {
        "on_submit": [
            "ecclesia.api.notification.trigger_notification",
            "ecclesia.api.customer_portal_api.on_quotation_submit",
        ],
        "on_cancel": "ecclesia.api.customer_portal_api.on_quotation_cancel",
    },

    "Sales Order": {
        "on_submit": [
            "ecclesia.api.notification.trigger_notification",
            "ecclesia.api.customer_portal_api.on_sales_order_submit",
        ],
        "on_update": "ecclesia.api.customer_portal_api.on_sales_order_update",
        "on_cancel": [
            "ecclesia.api.notification.trigger_notification",
            "ecclesia.api.customer_portal_api.on_sales_order_cancel",
        ],
    },

    "Delivery Note": {
        "on_submit": [
            "ecclesia.api.notification.trigger_notification",
            "ecclesia.api.customer_portal_api.on_delivery_submit",
        ],
    },

    "Sales Invoice": {
        "on_submit": [
            "ecclesia.api.notification.trigger_notification",
            "ecclesia.api.customer_portal_api.on_invoice_submit",
            "ecclesia.payment_gateway.events.on_sales_invoice_submit",
        ],
        "on_cancel": "ecclesia.api.customer_portal_api.on_invoice_cancel",
        "on_update": "ecclesia.api.escalation.check_invoice_overdue",
    },

    "Payment Entry": {
        "on_submit": [
            "ecclesia.api.notification.trigger_notification",
            "ecclesia.api.customer_portal_api.on_payment_submit",
            "ecclesia.api.supplier_portal_api.on_payment_submit",
        ],
    },

    "Issue": {
        "on_update": "ecclesia.api.customer_portal_api.on_issue_update",
    },

    # SUPPLIER PORTAL
    "Request for Quotation": {
        "on_submit": "ecclesia.api.supplier_portal_api.on_rfq_submit",
        "on_cancel": "ecclesia.api.supplier_portal_api.on_rfq_cancel",
    },

    "Purchase Order": {
        "on_submit": [
            "ecclesia.api.notification.trigger_notification",
            "ecclesia.api.approval.request_po_approval",
            "ecclesia.api.supplier_portal_api.on_purchase_order_submit",
        ],
        "on_update": "ecclesia.api.supplier_portal_api.on_purchase_order_update",
        "on_cancel": "ecclesia.api.supplier_portal_api.on_purchase_order_cancel",
    },

    "Purchase Receipt": {
        "on_submit": "ecclesia.api.supplier_portal_api.on_purchase_receipt_submit",
    },

    "Purchase Invoice": {
        "on_submit": "ecclesia.api.supplier_portal_api.on_purchase_invoice_submit",
    },

    "Quality Inspection": {
        "on_submit": "ecclesia.api.supplier_portal_api.on_quality_inspection_submit",
    },

    "Supplier Quotation": {
        "on_update": "ecclesia.api.supplier_portal_api.on_supplier_quotation_order",
    },

    # COMMUNICATION
    "Communication": {
        "after_insert": [
            "ecclesia.api.customer_portal_api.on_communication_insert",
            "ecclesia.tasks.on_communication_insert",
        ],
        "on_update": [
            "ecclesia.page.mail_hub.mail_hub_events.on_communication_update",
            "ecclesia.tasks.on_communication_update",
        ],
    },

    # BIOMETRIC
    "Attendance": {
        "before_insert": "ecclesia.biometric_attendance.events.validate_attendance",
        "before_save": "ecclesia.biometric_attendance.events.validate_attendance",
    },

    "Payment Gateway Log": {
        "before_save": "ecclesia.payment_gateway.events.prevent_manual_edit",
    },

    # RECRUITMENT
    "Job Applicant": {
        "after_insert": "ecclesia.api.recruitment_portal_notifications.on_applicant_insert",
        "on_update": "ecclesia.api.recruitment_portal_notifications.on_applicant_update",
    },

    "Interview": {
        "on_submit": "ecclesia.api.recruitment_portal_notifications.on_interview_submit",
        "on_update": "ecclesia.api.recruitment_portal_notifications.on_interview_update",
    },

    # HR EXTENSIONS
    "Leave Application": {
        "validate": "ecclesia.handover.leave_extension.validate_handover_exists",
        "on_submit": "ecclesia.handover.leave_extension.on_leave_submitted",
        "on_cancel": "ecclesia.handover.leave_extension.on_leave_cancelled",
    },

    # FIX 3: Corrected module paths — was missing inner "ecclesia" package
    "Manager Review": {
        "on_submit": "ecclesia.ecclesia.doctype.manager_review.manager_review.on_submit_hook",
    },

    "Peer Review Request": {
        "on_update": "ecclesia.ecclesia.doctype.peer_review_request.peer_review_request.on_update_hook",
    },

    "Employee Performance Record": {
        "on_update": "ecclesia.ecclesia.doctype.employee_performance_record.employee_performance_record.EmployeePerformanceRecord.on_update",
    },

    "Employee": {
        "on_update": [
            "ecclesia.ecclesia.doctype.employee.employee.on_update_hook",
            "ecclesia.tasks.on_employee_update",
        ]
    },

    "Social Post": {
        "on_update": "ecclesia.social_media.utils.on_post_update",
        "on_trash": "ecclesia.social_media.utils.on_post_delete",
    },

    "eRequest": {
        "on_update": "ecclesia.ecclesia.doctype.erequest.erequest.on_update",
        "on_cancel": "ecclesia.ecclesia.doctype.erequest.erequest.on_cancel",
    },
}


# ───────────────── SCHEDULER ─────────────────

scheduler_events = {

    "hourly": [
        "ecclesia.api.telephone_api.sync_missed_calls",
        "ecclesia.tasks.check_all_escalations",
        "ecclesia.tasks.process_pending_broadcasts",
        "ecclesia.tasks.expire_pending_actions",
        "ecclesia.biometric_attendance.processor.process_pending_logs",
        "ecclesia.social_media.scheduler.sync_platform_metrics",
    ],

    "cron": {
        "*/15 * * * *": [
            "ecclesia.tasks.retry_failed_messages",
            "ecclesia.tasks.process_message_queue",
            "ecclesia.biometric_attendance.sync.auto_sync_all_devices",
            "ecclesia.api.payment.retry_failed_webhooks",
            "ecclesia.api.message_blast_api.process_scheduled_blasts",
        ],

        "*/5 * * * *": [
            "ecclesia.tasks.sync_all_accounts",
        ],

        "0 0 1 1 *": [
            "ecclesia.tasks.assign_leave_policies_new_year",
            "ecclesia.scheduled_tasks.holiday_automation.create_annual_holiday_list",
        ],

        "0 8 * * *": [
            "ecclesia.scheduled_tasks.holiday_automation.send_holiday_greetings",
        ],
    },

    "all": [
        "ecclesia.tasks.push_unread_counts",
        "ecclesia.social_media.scheduler.publish_scheduled_posts",
    ],

    "daily": [
        "ecclesia.utils.ai_engine.run_nightly_anomaly_scan",
        "ecclesia.utils.gl_monitor.reconcile_gl_audit_mappings",
        "ecclesia.tasks.send_daily_overdue_digest",
        "ecclesia.tasks.cleanup_old_media",
        "ecclesia.tasks.archive_old_chat_messages",
        "ecclesia.api.ess_portal_tasks.send_overdue_task_reminders",
        "ecclesia.api.ess_portal_documents.flag_expired_documents",
        "ecclesia.api.customer_portal_api.send_overdue_invoice_reminders",
        "ecclesia.api.supplier_portal_api.send_rfq_expiry_reminders",
        "ecclesia.api.supplier_portal_api.send_po_delivery_reminders",
        "ecclesia.api.recruitment_portal_notifications.send_application_followups",
        "ecclesia.biometric_attendance.sync.mark_absent_employees",
        "ecclesia.tasks.send_policy_acknowledgement_reminders",
        "ecclesia.tasks.expire_overdue_policies",
        "ecclesia.tasks.escalate_overdue_handover_tasks",
        "ecclesia.tasks.performance_cycle_deadline_reminders",
        "ecclesia.tasks.mark_overdue_loan_installments",
        "ecclesia.social_media.scheduler.sync_comments",
        "ecclesia.social_media.scheduler.check_token_expiry",
        "ecclesia.utils.audit_engine.purge_expired_logs",
        "ecclesia.ecclesia.doctype.erequest.erequest.send_pending_approval_reminders",
    ],

    "weekly": [
        "ecclesia.utils.ai_engine.update_risk_scores",
        "ecclesia.utils.ai_engine.refresh_audit_universe_stats",
        "ecclesia.ecclesia.doctype.audit_universe.audit_universe.sync_audit_universe",
        "ecclesia.tasks.escalate_pending_peer_reviews",
        "ecclesia.tasks.send_upcoming_loan_deduction_reminders",
        "ecclesia.api.customer_portal_api.send_weekly_account_summary",
        "ecclesia.api.supplier_portal_api.send_weekly_supplier_summary",
    ],

    "monthly": [
        "ecclesia.utils.ai_engine.generate_monthly_audit_intelligence_report",
        "ecclesia.api.customer_portal_api.send_overdue_invoice_reminders",
    ],
}

# ─── Permission Hook ─────────────────────────────────────────────────────────
has_permission = {
    "eRequest": "ecclesia.ecclesia.doctype.erequest.erequest.has_permission",
}

# Webhook URLs
webhooks = {
    "/api/method/ecclesia.social_media.webhooks.facebook_webhook": "Social Media Webhooks"
}


# ─── Portal Menu ─────────────────────────────────────────────────────────────
standard_portal_menu_items = [
    {
        "title":             "My Requests",
        "route":             "/erequest-portal",
        "reference_doctype": "eRequest",
        "role":              "eRequest Employee",
    }
]


# ─── Fixtures ────────────────────────────────────────────────────────────────
fixtures = [
    {"dt": "Role", "filters": [["name", "in", [
        "eRequest Employee",
        "eRequest Manager",
        "eRequest Finance",
        "eRequest Admin",
    ]]]},
    {"dt": "Email Template", "filters": [["module", "=", "Ecclesia eRequest"]]},
]

# NOTE: Workflow is intentionally NOT a fixture.
# Configure per-company via ERPNext > Setup > Workflow > New Workflow
# Target DocType: eRequest