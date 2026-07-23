from __future__ import unicode_literals

app_name        = "ecclesia"
app_title       = "Ecclesia"
app_publisher   = "Kunle Oduntan"
app_description = (
    "Ecclesia Platform — Telephony, Finance, Payroll, Audit Intelligence, "
    "ESS, Customer & Supplier Self-Service Portals"
)
app_email   = "kunleoduntan@gmail.com"
app_license = "MIT"
app_version = "2.0.0"
app_icon  = "octicon octicon-shield"
app_color = "#2c3e50"
required_apps = ["frappe", "erpnext"]

after_migrate = [
    "ecclesia.install.after_migrate",
    "ecclesia.api.ess_portal_custom_fields.after_migrate",
    "ecclesia.api.recruitment_portal_custom_fields.after_migrate",
    "ecclesia.api.portal_custom_fields.install",
    "ecclesia.setup_roles.create_roles_if_not_exist",
    "ecclesia.api.compliance.compliance_custom_fields.install",
    "ecclesia.api.recruitment_custom_fields.create_all",
    "ecclesia.ecclesia.setup.ensure_doctypes.ensure_doctypes_exist",
    "ecclesia.ecclesia.custom.employee_ctc.create_employee_ctc_fields",
]

on_login  = "ecclesia.api.session_hooks.on_login"
on_logout = "ecclesia.api.session_hooks.on_logout"

website_route_rules = [
    {"from_route": "/erequest-portal",   "to_route": "erequest_portal"},
    {"from_route": "/ess-portal",        "to_route": "ess-portal"},
    {"from_route": "/performance-hub",   "to_route": "performance_hub"},
    {"from_route": "/apply",             "to_route": "apply"},
]

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
    "/assets/ecclesia/js/global_item_filter.js",
    "/assets/ecclesia/js/universal_listview.js",
    "/assets/ecclesia/js/universal_excel_export.js",
    "/assets/ecclesia/js/universal_listview_download.js",
]

doctype_js = {
    "Annual Budget":       "public/js/annual_budget_manual.min.js",
    "Payments":            "public/js/payments.js",
    "Bank Reconciliation": "public/js/bank_reconciliation_manual.min.js",
    "Payroll Entry":       "public/js/payroll_entry_bank.js",
    "Salary Slip":         "public/js/salary_slip_pension.min.js",
    "Receipts":            "doctype/receipts/receipts.js",
    "Sales Invoice":       "public/js/sales_invoice_payment.js",
    "Employee":            "public/js/employee.js",
    "Employee":            "public/js/employee_ctc.js",
    "Purchase Invoice":    "public/js/purchase_invoice.js",
    "Journal Entry":       "public/js/journal_entry.js",
    "Asset":               "public/js/backdated_depreciation.js",
    "Compliance Liability Ledger":      "doctype/compliance_liability_ledger/compliance_liability_ledger.js",
    "Compliance Filing":                "doctype/compliance_filing/compliance_filing.js",
    "License Management":               "doctype/license_management/license_management.js",
    "Compliance Risk Register":         "doctype/compliance_risk_register/compliance_risk_register.js",
    "Compliance Audit":                 "doctype/compliance_audit/compliance_audit.js",
    "Compliance Rule":                  "doctype/compliance_rule/compliance_rule.js",
    "Compliance Task":                  "doctype/compliance_task/compliance_task.js",
    "Compliance Exception":             "doctype/compliance_exception/compliance_exception.js",
    "Compliance Incident":              "doctype/compliance_incident/compliance_incident.js",
    "Corporate Compliance Register":    "doctype/corporate_compliance_register/corporate_compliance_register.js",
    "Board Resolution":                 "doctype/board_resolution/board_resolution.js",
    "Statutory Register Entry":         "doctype/statutory_register_entry/statutory_register_entry.js",
    "Contract Compliance Record":       "doctype/contract_compliance_record/contract_compliance_record.js",
    "Data Processing Record":           "doctype/data_processing_record/data_processing_record.js",
    "Data Breach Register":             "doctype/data_breach_register/data_breach_register.js",
    "AML KYC Record":                   "doctype/aml_kyc_record/aml_kyc_record.js",
    "Suspicious Transaction Report":    "doctype/suspicious_transaction_report/suspicious_transaction_report.js",
    "Labour Compliance Tracker":        "doctype/labour_compliance_tracker/labour_compliance_tracker.js",
    "Expatriate Permit Register":       "doctype/expatriate_permit_register/expatriate_permit_register.js",
    "Environmental Compliance Record":  "doctype/environmental_compliance_record/environmental_compliance_record.js",
    "Regulatory Return":                "doctype/regulatory_return/regulatory_return.js",
    "Whistleblower Report":             "doctype/whistleblower_report/whistleblower_report.js",
    "Conflict of Interest Declaration": "doctype/conflict_of_interest_declaration/conflict_of_interest_declaration.js",
    "Compliance Training Record":       "doctype/compliance_training_record/compliance_training_record.js",
    "Compliance Training Calendar":     "doctype/compliance_training_calendar/compliance_training_calendar.js",
    "Facility":                         "doctype/facility/facility.js",
    "Facility Maintenance Request":     "doctype/facility_maintenance_request/facility_maintenance_request.js",
    "Maintenance Work Order":           "doctype/maintenance_work_order/maintenance_work_order.js",
    "Meeting Room Booking":             "doctype/meeting_room_booking/meeting_room_booking.js",
    "Company Vehicle":                  "doctype/company_vehicle/company_vehicle.js",
    "Vehicle Request":                  "doctype/vehicle_request/vehicle_request.js",
    "Vehicle Trip Log":                 "doctype/vehicle_trip_log/vehicle_trip_log.js",
    "Fuel Issue":                       "doctype/fuel_issue/fuel_issue.js",
    "Utility Consumption":              "doctype/utility_consumption/utility_consumption.js",
    "Generator Log":                    "doctype/generator_log/generator_log.js",
    "Visitor Register":                 "doctype/visitor_register/visitor_register.js",
    "Security Incident":                "doctype/security_incident/security_incident.js",
    "HSE Inspection":                   "doctype/hse_inspection/hse_inspection.js",
    "Asset Inspection":                 "doctype/asset_inspection/asset_inspection.js",
    "Compliance Register":              "doctype/compliance_register/compliance_register.js",
    "Service Provider":                 "doctype/service_provider/service_provider.js",
    "Service Contract":                 "doctype/service_contract/service_contract.js",
    "Administrative Request":           "doctype/administrative_request/administrative_request.js",
}

_ENGINE = "ecclesia.api.engine.log_activity"

doc_events = {
    "*": {
        "after_insert": [
            "ecclesia.utils.audit_engine.log_event",
            _ENGINE,
        ],
        "on_update": [
            "ecclesia.utils.audit_trail.on_amend_handler",
            "ecclesia.utils.audit_engine.log_event",
            _ENGINE,
        ],
        "on_submit": [
            "ecclesia.utils.audit_trail.on_submit_handler",
            "ecclesia.utils.audit_engine.log_event",
            _ENGINE,
        ],
        "on_cancel": [
            "ecclesia.utils.audit_trail.on_cancel_handler",
            "ecclesia.utils.audit_engine.log_event",
            _ENGINE,
        ],
        "on_trash": "ecclesia.utils.audit_engine.log_delete",
        "on_update_after_submit": "ecclesia.utils.audit_trail.on_amend_handler",
    },
    "Telephone Call Log": {
        "after_insert": "ecclesia.api.telephone_api.on_telephone_call_log_insert",
    },
    "Bank Reconciliation": {
        "validate": (
            "ecclesia.ecclesia.doctype.bank_reconciliation"
            ".bank_reconciliation.validate_bank_reconciliation"
        ),
    },
    "Accounting Dimension": {
        "after_insert": (
            "ecclesia.ecclesia.utils.accounting_dimensions"
            ".auto_add_to_payments"
        ),
    },
    "Asset": {
        "on_submit": "ecclesia.api.backdated_depreciation.make_backdated_depreciation_entries",
    },
    "Payments": {
        "validate":      "ecclesia.ecclesia.doctype.payments.payments.validate_payment",
        "before_submit": "ecclesia.ecclesia.doctype.payments.payments.before_submit_payment",
        "on_trash":      "ecclesia.ecclesia.doctype.payments.payments.on_trash_payment",
        "on_submit": [
            "ecclesia.api.auto_transaction_coding.run_auto_transaction_coding",
            "ecclesia.api.compliance.allocation_engine_v2.on_payments_submit",
        ],
        "on_cancel": [
            "ecclesia.api.compliance.allocation_engine_v2.on_payments_cancel",
        ],
    },
    "Batch Bank Transaction": {
        "validate":    (
            "ecclesia.ecclesia.doctype.batch_bank_transaction"
            ".batch_bank_transaction.validate_party_name"
        ),
        "before_save": (
            "ecclesia.ecclesia.doctype.batch_bank_transaction"
            ".batch_bank_transaction.update_party_names"
        ),
        "on_submit":   (
            "ecclesia.ecclesia.doctype.batch_bank_transaction"
            ".batch_bank_transaction.on_batch_submit"
        ),
        "on_cancel":   (
            "ecclesia.ecclesia.doctype.batch_bank_transaction"
            ".batch_bank_transaction.on_batch_cancel"
        ),
    },
    "GL Entry": {
        "after_insert": "ecclesia.utils.gl_monitor.track_gl_entry",
        "on_cancel":    "ecclesia.utils.gl_monitor.track_gl_cancellation",
    },
    "Journal Entry": {
        "on_submit": [
            "ecclesia.utils.gl_monitor.flag_journal_entry_risks",
            "ecclesia.api.ar_validation.validate_jv_party_required",
        ],
    },
    "Payroll Entry": {
        "on_submit": "ecclesia.pension_mgt_tasks.on_payroll_submit",
    },
    "Salary Slip": {
        "before_submit": [
            "ecclesia.api.loan_payroll.on_salary_slip_before_submit",
        ],
        "on_submit": [
            "ecclesia.pension_mgt_tasks.on_salary_slip_submit",
            "ecclesia.api.ess_portal_documents.notify_payslip_ready",
            "ecclesia.api.loan_payroll.on_salary_slip_on_submit",
            "ecclesia.api.compliance.liability_engine_v2.link_salary_slip_to_cll",
            "ecclesia.api.ess_portal_events.on_salary_slip_submit",
        ],
        "on_cancel": [
            "ecclesia.api.loan_payroll.on_salary_slip_on_cancel",
        ],
    },
    "Company": {
        "on_update": "ecclesia.utils.item_validator.clear_company_item_filter_cache",
    },
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
            "ecclesia.api.item_validation.validate_delivery_note_stock_on_submit",
        ],
        "on_cancel": "ecclesia.api.item_validation.alidate_stock_cancel_integrity",
    },
    "Sales Invoice": {
        "on_submit": [
            "ecclesia.api.notification.trigger_notification",
            "ecclesia.api.customer_portal_api.on_invoice_submit",
            "ecclesia.payment_gateway.events.on_sales_invoice_submit",
            "ecclesia.api.ar_validation.validate_ar_gl_on_submit",
            "ecclesia.api.compliance.liability_engine_v2.generate_vat_liability",
        ],
        "on_cancel": [
            "ecclesia.api.customer_portal_api.on_invoice_cancel",
            "ecclesia.api.ar_validation.validate_ar_gl_on_cancel",
        ],
        "on_update": "ecclesia.api.escalation.check_invoice_overdue",
    },
    "Payment Entry": {
        "on_submit": [
            "ecclesia.api.notification.trigger_notification",
            "ecclesia.api.customer_portal_api.on_payment_submit",
            "ecclesia.api.supplier_portal_api.on_payment_submit",
            "ecclesia.api.payment_validation.validate_payment_ar_integrity",
            "ecclesia.api.payment_validation.validate_payment_ap_integrity",
        ],
    },
    "Issue": {
        "on_update": "ecclesia.api.customer_portal_api.on_issue_update",
    },
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
        "on_submit": [
            "ecclesia.api.supplier_portal_api.on_purchase_receipt_submit",
            "ecclesia.api.item_validation.validate_purchase_receipt_stock_on_submit",
        ],
        "on_cancel": "ecclesia.api.item_validation.validate_stock_cancel_integrity",
    },
    "Purchase Invoice": {
        "on_submit": [
            "ecclesia.api.supplier_portal_api.on_purchase_invoice_submit",
            "ecclesia.api.ap_validation.validate_ap_gl_on_submit",
            "ecclesia.api.compliance.liability_engine_v2.log_purchase_invoice_wht",
        ],
        "on_cancel": "ecclesia.api.ar_validation.validate_ap_gl_on_cancel",
    },
    "Stock Entry": {
        "on_submit": "ecclesia.api.item_validation.validate_stock_entry_gl_on_submit",
        "on_cancel": "ecclesia.api.item_validation.validate_stock_cancel_integrity",
    },
    "Quality Inspection": {
        "on_submit": "ecclesia.api.supplier_portal_api.on_quality_inspection_submit",
    },
    "Supplier Quotation": {
        "on_update": "ecclesia.api.supplier_portal_api.on_supplier_quotation_order",
    },
    "Communication": {
        "after_insert": [
            "ecclesia.api.customer_portal_api.on_communication_insert",
            "ecclesia.tasks.on_communication_insert",
        ],
        "on_update": [
            "ecclesia.ecclesia.page.mail_hub.mail_hub_events.on_communication_update",
            "ecclesia.tasks.on_communication_update",
        ],
    },
    "Attendance": {
        "before_insert": "ecclesia.biometric_attendance.events.validate_attendance",
        "before_save":   "ecclesia.biometric_attendance.events.validate_attendance",
        "on_submit":     "ecclesia.api.ess_portal_events.on_attendance_submit",
    },
    "Payment Gateway Log": {
        "before_save": "ecclesia.payment_gateway.events.prevent_manual_edit",
    },

    # ── Job Applicant ─────────────────────────────────────────────────────────
    "Job Applicant": {
        "after_insert": [
            "ecclesia.api.recruitment_portal_notifications.on_applicant_insert",
            "ecclesia.api.recruitment_auto_screen.on_job_applicant_submit",
        ],
        "on_update": "ecclesia.api.recruitment_portal_notifications.on_applicant_update",
        "on_submit": "ecclesia.api.recruitment_auto_screen.on_job_applicant_submit",
    },
    "Interview": {
        "on_submit": "ecclesia.api.recruitment_portal_notifications.on_interview_submit",
        "on_update": "ecclesia.api.recruitment_portal_notifications.on_interview_update",
    },
    "Leave Application": {
        "validate":  "ecclesia.handover.leave_extension.validate_handover_exists",
        "on_submit": "ecclesia.handover.leave_extension.on_leave_submitted",
        "on_cancel": "ecclesia.handover.leave_extension.on_leave_cancelled",
        "on_update_after_submit": "ecclesia.api.ess_portal_events.on_leave_status_change",
    },
    "Manager Review": {
        "on_submit": "ecclesia.ecclesia.doctype.manager_review.manager_review.on_submit_hook",
    },
    "Peer Review Request": {
        "on_update": (
            "ecclesia.ecclesia.doctype.peer_review_request"
            ".peer_review_request.on_update_hook"
        ),
    },

    # ── Employee Performance Record ───────────────────────────────────────────
    # FIX: old entry called the class method on_update as a module-level function
    # which caused AttributeError. Class methods fire automatically — removed.
    # Only module-level cross-module functions go here.
    "Employee Performance Record": {
        "on_update": [
            # Propagate EPR score changes to cycle-level analytics
            "ecclesia.api.performance_events.on_perf_record_update",
            # ESS: recalculate pulse score when performance record changes
            "ecclesia.api.ess_portal_events.on_perf_record_update",
        ],
    },

    "Employee": {
        "on_update": [
            "ecclesia.tasks.on_employee_update",
        ],
        "before_insert": [
            "ecclesia.api.employee_ctc.set_default_components",
        ],
        "validate": [
            "ecclesia.api.employee_ctc.calculate_ctc",
        ],
    },
    
    "Social Post": {
        "on_update": "ecclesia.social_media.utils.on_post_update",
        "on_trash":  "ecclesia.social_media.utils.on_post_delete",
    },
    "eRequest": {
        "on_update": "ecclesia.ecclesia.doctype.erequest.erequest.on_update",
        "on_cancel": "ecclesia.ecclesia.doctype.erequest.erequest.on_cancel",
    },
    "Employee Loan Application": {
        "on_update_after_submit": "ecclesia.api.ess_portal_events.on_loan_status_change",
    },
    "Expense Claim": {
        "on_update_after_submit": "ecclesia.api.ess_portal_events.on_expense_status_change",
    },
    "Company Policy": {
        "on_submit": [
            "ecclesia.api.compliance.policy_bridge.sync_to_compliance_policy",
            "ecclesia.api.ess_portal_events.on_policy_published",
        ],
    },

    # ── Performance Management cross-module listeners ─────────────────────────
    # Class methods on individual controllers fire automatically.
    # Only these cross-DocType score propagation functions go here.
    # All live in: ecclesia/api/performance_events.py
    "Performance Goal": {
        "on_update": "ecclesia.api.performance_events.on_goal_update",
    },
    "Self Appraisal": {
        "on_submit": "ecclesia.api.performance_events.on_self_appraisal_submit",
    },
    "Peer Review": {
        "on_submit": "ecclesia.api.performance_events.on_peer_review_submit",
    },
    "Manager Review 360": {
        "on_submit": "ecclesia.api.performance_events.on_manager_review_submit",
    },

    # ── Compliance v3 ─────────────────────────────────────────────────────────
    "Board Resolution": {
        "on_submit": (
            "ecclesia.ecclesia.doctype.board_resolution"
            ".board_resolution.on_submit"
        ),
    },
    "Corporate Compliance Register": {
        "on_submit": (
            "ecclesia.ecclesia.doctype.corporate_compliance_register"
            ".corporate_compliance_register.on_submit"
        ),
    },
    "Data Breach Register": {
        "on_submit": (
            "ecclesia.ecclesia.doctype.data_breach_register"
            ".data_breach_register.on_submit"
        ),
    },
    "Data Processing Record": {
        "on_submit": (
            "ecclesia.ecclesia.doctype.data_processing_record"
            ".data_processing_record.on_submit"
        ),
    },
    "AML KYC Record": {
        "on_submit": (
            "ecclesia.ecclesia.doctype.aml_kyc_record"
            ".aml_kyc_record.on_submit"
        ),
    },
    "Suspicious Transaction Report": {
        "on_submit": (
            "ecclesia.ecclesia.doctype.suspicious_transaction_report"
            ".suspicious_transaction_report.on_submit"
        ),
    },
    "Labour Compliance Tracker": {
        "on_submit": (
            "ecclesia.ecclesia.doctype.labour_compliance_tracker"
            ".labour_compliance_tracker.on_submit"
        ),
    },
    "Regulatory Return": {
        "on_submit": (
            "ecclesia.ecclesia.doctype.regulatory_return"
            ".regulatory_return.on_submit"
        ),
    },
    "Whistleblower Report": {
        "on_submit": (
            "ecclesia.ecclesia.doctype.whistleblower_report"
            ".whistleblower_report.on_submit"
        ),
    },
    "Conflict of Interest Declaration": {
        "on_submit": (
            "ecclesia.ecclesia.doctype.conflict_of_interest_declaration"
            ".conflict_of_interest_declaration.on_submit"
        ),
    },
    "Compliance Training Record": {
        "on_submit": (
            "ecclesia.ecclesia.doctype.compliance_training_record"
            ".compliance_training_record.on_submit"
        ),
    },
    "Compliance Training Calendar": {
        "on_submit": (
            "ecclesia.ecclesia.doctype.compliance_training_calendar"
            ".compliance_training_calendar.on_submit"
        ),
    },
    "Contract Compliance Record": {
        "on_update": (
            "ecclesia.ecclesia.doctype.contract_compliance_record"
            ".contract_compliance_record.on_update"
        ),
    },
    "Environmental Compliance Record": {
        "on_update": (
            "ecclesia.ecclesia.doctype.environmental_compliance_record"
            ".environmental_compliance_record.on_update"
        ),
    },

    # ── Admin module ──────────────────────────────────────────────────────────
    "Vehicle Trip Log": {
        "on_submit": (
            "ecclesia.ecclesia.doctype.vehicle_trip_log"
            ".vehicle_trip_log.VehicleTripLog.on_submit"
        ),
        "on_cancel": (
            "ecclesia.ecclesia.doctype.vehicle_trip_log"
            ".vehicle_trip_log.VehicleTripLog.on_cancel"
        ),
    },
    "Fuel Issue": {
        "on_submit": (
            "ecclesia.ecclesia.doctype.fuel_issue"
            ".fuel_issue.FuelIssue.on_submit"
        ),
    },
    "Utility Consumption": {
        "on_submit": (
            "ecclesia.ecclesia.doctype.utility_consumption"
            ".utility_consumption.UtilityConsumption.on_submit"
        ),
    },
    "Generator Log": {
        "on_submit": (
            "ecclesia.ecclesia.doctype.generator_log"
            ".generator_log.GeneratorLog.on_submit"
        ),
    },
    "Administrative Request": {
        "on_submit": (
            "ecclesia.ecclesia.doctype.administrative_request"
            ".administrative_request.AdministrativeRequest.on_submit"
        ),
        "on_cancel": (
            "ecclesia.ecclesia.doctype.administrative_request"
            ".administrative_request.AdministrativeRequest.on_cancel"
        ),
    },
    "Facility Maintenance Request": {
        "on_submit": (
            "ecclesia.ecclesia.doctype.facility_maintenance_request"
            ".facility_maintenance_request.FacilityMaintenanceRequest.on_submit"
        ),
        "on_cancel": (
            "ecclesia.ecclesia.doctype.facility_maintenance_request"
            ".facility_maintenance_request.FacilityMaintenanceRequest.on_cancel"
        ),
    },
    "Maintenance Work Order": {
        "on_submit": (
            "ecclesia.ecclesia.doctype.maintenance_work_order"
            ".maintenance_work_order.MaintenanceWorkOrder.on_submit"
        ),
    },
    "Service Contract": {
        "on_submit": (
            "ecclesia.ecclesia.doctype.service_contract"
            ".service_contract.ServiceContract.on_submit"
        ),
        "on_cancel": (
            "ecclesia.ecclesia.doctype.service_contract"
            ".service_contract.ServiceContract.on_cancel"
        ),
    },
    "Security Incident": {
        "on_submit": (
            "ecclesia.ecclesia.doctype.security_incident"
            ".security_incident.SecurityIncident.on_submit"
        ),
    },
    "HSE Inspection": {
        "on_submit": (
            "ecclesia.ecclesia.doctype.hse_inspection"
            ".hse_inspection.HseInspection.on_submit"
        ),
    },
    "Visitor Register": {
        "on_submit": (
            "ecclesia.ecclesia.doctype.visitor_register"
            ".visitor_register.VisitorRegister.on_submit"
        ),
    },
    # ... keep your existing "Annual General Meeting" block ...
	"Meeting": {
		"validate": "ecclesia.ecclesia.doctype.meeting.meeting.Meeting.validate",
		"on_submit": "ecclesia.ecclesia.doctype.meeting.meeting.Meeting.on_submit",
	},
	"Board Resolution": {
		"validate": "ecclesia.ecclesia.doctype.board_resolution.board_resolution.BoardResolution.validate",
		"on_submit": "ecclesia.ecclesia.doctype.board_resolution.board_resolution.BoardResolution.on_submit",
	},
}

scheduler_events = {
    "all": [
        "ecclesia.tasks.push_unread_counts",
        "ecclesia.social_media.scheduler.publish_scheduled_posts",
    ],
    "cron": {
        "*/5 * * * *": [
            "ecclesia.tasks.sync_all_accounts",
            "ecclesia.api.auto_transaction_coding.run_auto_transaction_coding",
            "ecclesia.biometric_attendance.push.flag_offline_push_devices",
        ],
        "*/15 * * * *": [
            "ecclesia.tasks.retry_failed_messages",
            "ecclesia.tasks.process_message_queue",
            "ecclesia.biometric_attendance.sync.auto_sync_all_devices",
            "ecclesia.api.payment.retry_failed_webhooks",
            "ecclesia.api.message_blast_api.process_scheduled_blasts",
        ],
        "0 8 * * *": [
            "ecclesia.scheduled_tasks.holiday_automation.send_holiday_greetings",
        ],
        "0 0 1 1 *": [
            "ecclesia.tasks.assign_leave_policies_new_year",
            "ecclesia.scheduled_tasks.holiday_automation.create_annual_holiday_list",
        ],
    },
    "hourly": [
        "ecclesia.api.telephone_api.sync_missed_calls",
        "ecclesia.tasks.check_all_escalations",
        "ecclesia.tasks.process_pending_broadcasts",
        "ecclesia.tasks.expire_pending_actions",
        "ecclesia.biometric_attendance.processor.process_pending_logs",
        "ecclesia.social_media.scheduler.sync_platform_metrics",
        "ecclesia.api.auto_transaction_coding.run_auto_transaction_coding",
        "ecclesia.ecclesia.doctype.work_session.work_session.flag_inactive_sessions",
        "ecclesia.api.ess_portal_events.check_new_payslips",
        "ecclesia.api.job_post_api.dispatch_scheduled_posts",
    ],
    "daily_long": [
        "ecclesia.ecclesia.doctype.wfh_daily_summary.wfh_daily_summary.send_summary_reminders",
        "ecclesia.api.nightly_ar_reconciliation_check",
        "ecclesia.api.nightly_ap_reconciliation_check",
        "ecclesia.api.item_validation.nightly_item_reconciliation_check",
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
        "ecclesia.ecclesia.doctype.wfh_schedule.wfh_schedule.auto_open_sessions_for_today",
        "ecclesia.api.session_hooks.close_all_open_sessions",
        "ecclesia.api.backdated_depreciation.process_all_backdated_depreciation",
        "ecclesia.api.compliance.compliance_scheduler_v2.run_daily",
        "ecclesia.scheduler.admin_scheduler.run_daily",
        "ecclesia.api.ess_portal_events.run_daily_pulse_batch",
        "ecclesia.api.ess_portal_events.send_policy_ack_reminders",
        # Recruitment
        "ecclesia.api.recruitment_auto_screen.dispatch_post_closing_emails",
        # Performance Management
        "ecclesia.api.performance_scheduler.send_deadline_reminders",
        "ecclesia.api.performance_scheduler.ensure_performance_records_exist",
        "ecclesia.api.performance_scheduler.flag_overdue_pip_checkins",
        # ... keep "ecclesia.api.agm_api.run_agm_scheduled_notifications" ...
		"ecclesia.api.meeting_api.run_meeting_scheduled_notifications",
		"ecclesia.api.documents_api.run_document_scheduled_notifications",
		"ecclesia.api.executive_api.run_executive_scheduled_notifications",
    ],
    "weekly": [
        "ecclesia.utils.ai_engine.update_risk_scores",
        "ecclesia.utils.ai_engine.refresh_audit_universe_stats",
        "ecclesia.ecclesia.doctype.audit_universe.audit_universe.sync_audit_universe",
        "ecclesia.tasks.escalate_pending_peer_reviews",
        "ecclesia.tasks.send_upcoming_loan_deduction_reminders",
        "ecclesia.api.customer_portal_api.send_weekly_account_summary",
        "ecclesia.api.supplier_portal_api.send_weekly_supplier_summary",
        "ecclesia.api.analytics.recompute_weekly_consistency",
        "ecclesia.scheduler.admin_scheduler.run_weekly",
        # Performance Management
        "ecclesia.api.performance_scheduler.send_manager_pending_digest",
        "ecclesia.api.performance_scheduler.send_hr_recruitment_summary",
    ],
    "monthly": [
        "ecclesia.utils.ai_engine.generate_monthly_audit_intelligence_report",
        "ecclesia.api.customer_portal_api.send_overdue_invoice_reminders",
        "ecclesia.api.compliance.compliance_scheduler_v2.run_monthly",
        "ecclesia.scheduler.admin_scheduler.run_monthly",
        # Performance Management
        "ecclesia.api.performance_scheduler.close_stale_goals",
    ],
    "yearly": [
        "ecclesia.api.compliance.compliance_scheduler_v2.run_yearly",
    ],
}

permission_query_conditions = {
    "WFH Request":          "ecclesia.permissions.get_employee_permission_query",
    "WFH Session":          "ecclesia.permissions.get_employee_permission_query",
    "Work Activity Log":    "ecclesia.permissions.get_employee_permission_query",
    "WFH Daily Summary":    "ecclesia.permissions.get_employee_permission_query",
    "Work Session":         "ecclesia.permissions.get_work_session_permission_query",
    "External Task":        "ecclesia.permissions.get_user_permission_query",
    "ESS Notification Log": "ecclesia.permissions.get_employee_permission_query",
    "ESS Pulse Score":      "ecclesia.permissions.get_employee_permission_query",
    "ESS Quick Action":     "ecclesia.permissions.get_employee_permission_query",
}

has_permission = {
    "eRequest":             "ecclesia.ecclesia.doctype.erequest.erequest.has_permission",
    "WFH Request":          "ecclesia.permissions.has_permission",
    "WFH Session":          "ecclesia.permissions.has_permission",
    "Work Activity Log":    "ecclesia.permissions.has_permission",
    "WFH Daily Summary":    "ecclesia.permissions.has_permission",
    "Work Session":         "ecclesia.permissions.has_work_session_permission",
    "External Task":        "ecclesia.permissions.has_user_permission",
    "ESS Notification Log": "ecclesia.permissions.has_permission",
    "ESS Pulse Score":      "ecclesia.permissions.has_permission",
    "ESS Quick Action":     "ecclesia.permissions.has_permission",
}

webhooks = {
    "/api/method/ecclesia.social_media.webhooks.facebook_webhook":
        "Social Media Webhooks",
}

standard_portal_menu_items = [
    {
        "title":             "My Requests",
        "route":             "/erequest-portal",
        "reference_doctype": "eRequest",
        "role":              "eRequest Employee",
    },
    {
        "title":             "Employee Self-Service",
        "route":             "/ess-portal",
        "reference_doctype": "Employee",
        "role":              "Employee",
    },
    {
        "title":             "My Performance",
        "route":             "/performance-hub",
        "reference_doctype": "Employee Performance Record",
        "role":              "Employee",
    },
]

custom_fields = {
    "Attendance": [
        {
            "fieldname":    "wfh_request",
            "fieldtype":    "Link",
            "options":      "WFH Request",
            "label":        "WFH Request",
            "insert_after": "leave_type",
            "read_only":    1,
            "no_copy":      1,
            "description":  "Auto-linked when a WFH Request is approved",
        }
    ]
}

fixtures = [
    {
        "dt": "Role",
        "filters": [[
            "name", "in", [
                "eRequest Employee",
                "eRequest Manager",
                "eRequest Finance",
                "Line Manager",
                "eRequest Admin",
                "HR Manager",
            ]
        ]]
    },
    {
        "dt": "Email Template",
        "filters": [["module", "=", "Ecclesia"]]
    },
    {
        "dt": "Custom Field",
        "filters": [[
            "dt", "in", [
                "Supplier", "Customer", "Communication", "Company",
                "Account", "Bank Account", "Journal Entry", "Salary Slip",
                "Salary Component", "Purchase Invoice", "Purchase Invoice Item",
                "Attendance", "Leave Policy", "Request for Quotation", "Employee", "Salary Structure Assignment",
            ]
        ]]
    },
    {
        "dt": "Property Setter",
        "filters": [["doc_type", "=", "Supplier"]]
    },
    {"dt": "Activity Configuration", "filters": [["module", "=", "Ecclesia"]]},
    {"dt": "WFH Activity Mapping",   "filters": [["module", "=", "Ecclesia"]]},
    {"dt": "Custom Field",           "filters": [["module", "=", "Ecclesia"]]},
    {"dt": "Property Setter",        "filters": [["module", "=", "Ecclesia"]]},
    {"dt": "Notification",           "filters": [["module", "=", "Ecclesia"]]},
    {"dt": "Regulatory Authority",   "filters": [["module", "=", "Ecclesia"]]},
    {"dt": "Compliance Rule",        "filters": [["module", "=", "Ecclesia"]]},
    {
        "dt": "DocType",
        "filters": [["name", "in", [
            "ESS Notification Log",
            "ESS Quick Action",
            "ESS Pulse Score",
        ]]]
    },
    {
        "dt": "DocType",
        "filters": [["name", "in", [
            "Job Requirement Profile",
            "Resume",
            "Resume Screening Result",
            "Candidate Comparison Matrix",
        ]]]
    },
    {
        "dt": "DocType",
        "filters": [["name", "in", [
            "Performance Rating Scale",
            "Performance Cycle",
            "Performance Weight Config",
            "Performance Competency",
            "Performance Goal",
            "Employee Performance Record",
            "Self Appraisal",
            "Peer Review Request",
            "Peer Review",
            "Manager Review 360",
            "Skip Level Review",
            "HR Calibration Session",
            "Performance IDP",
            "Performance PIP",
            "Continuous Feedback",
            "Performance Appeal",
        ]]]
    },
    {
        "dt": "DocType",
        "filters": [["name", "in", [
            "Job Board Platform",
            "Job Post Target",
            "Job Post",
        ]]]
    },
    # ── Employee CTC breakdown custom fields ────────────────────────────────
    {
        "dt": "Custom Field",
        "filters": [[
            "name", "in", [
                "Employee-ctc_section_break",
                "Employee-annual_gross_pay",
                "Employee-ctc_components",
                "Employee-total_components",
                "Employee-column_break_ctc",
                "Employee-pensionable_emoluments",
                "Employee-pension_ee_percent",
                "Employee-pension_ee_amount",
                "Employee-pension_er_percent",
                "Employee-pension_er_amount",
            ]
        ]]
    },
    # CTC Settings is a Single — export its one record too, so the
    # configured split ships/deploys with the site (edit it via
    # Setup > CTC Settings after install; it isn't hardcoded anywhere).
    {"dt": "CTC Settings"},
]