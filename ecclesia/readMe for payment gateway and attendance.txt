ecclesia/                                         ← Frappe app root (bench get-app target)
│
├── setup.py                                      ← App metadata & pip dependencies
├── requirements.txt                              ← Python packages (pyzk, requests, etc.)
│
└── ecclesia/                                     ← Python package (same name as app)
    ├── __init__.py
    ├── hooks.py                                  ← Scheduled tasks, doc_events, fixtures
    ├── modules.txt                               ← Declares "Ecclesia" module to Frappe
    │
    ├── api/                                      ← Whitelisted API endpoints (your existing folder)
    │   ├── __init__.py
    │   ├── payment.py                            ← initiate(), webhook(), verify()
    │   └── attendance.py                         ← sync_device(), ping_device(), process_logs(), receive_push(), get_device_users()
    │
    ├── utils/                                    ← Shared logic (your existing folder)
    │   ├── __init__.py
    │   ├── helpers.py                            ← kobo_to_naira(), safe_json(), log_error()
    │   ├── gateway_router.py                     ← get_gateway_handler() factory
    │   ├── device_connector.py                   ← get_connector() + all 8 brand connectors
    │   └── gateways/                             ← One file per payment provider
    │       ├── __init__.py
    │       ├── base.py                           ← BaseGatewayHandler (abstract interface)
    │       ├── paystack.py                       ← ✅ Full (initiate, verify, webhook, refund)
    │       ├── flutterwave.py                    ← ✅ Full
    │       ├── remita.py                         ← 🔲 Stub (ready to implement)
    │       ├── squad.py                          ← 🔲 Stub
    │       ├── stripe.py                         ← 🔲 Stub
    │       └── mpesa.py                          ← 🔲 Stub
    │
    ├── payment_gateway/                          ← Payment Gateway module
    │   ├── __init__.py
    │   ├── events.py                             ← on_sales_invoice_submit → auto payment link
    │   └── doctype/
    │       ├── __init__.py
    │       │
    │       ├── payment_gateway_settings/         ← Per-gateway config (credentials, keys, mode)
    │       │   ├── __init__.py
    │       │   ├── payment_gateway_settings.json ← DocType schema
    │       │   ├── payment_gateway_settings.py   ← validate(), get_headers(), _build_callback_url()
    │       │   └── payment_gateway_settings.js   ← Form JS (show/hide fields per provider)
    │       │
    │       ├── payment_gateway_log/              ← Every transaction attempt recorded here
    │       │   ├── __init__.py
    │       │   ├── payment_gateway_log.json
    │       │   └── payment_gateway_log.py        ← create_log(), update_status()
    │       │
    │       ├── payment_gateway_provider/         ← Provider endpoint registry (base URLs)
    │       │   ├── __init__.py
    │       │   └── payment_gateway_provider.json
    │       │
    │       ├── payment_transaction_log/          ← Raw webhook payloads stored here
    │       │   ├── __init__.py
    │       │   ├── payment_transaction_log.json
    │       │   └── payment_transaction_log.py
    │       │
    │       └── gateway_webhook_log/              ← Webhook events audit trail
    │           ├── __init__.py
    │           ├── gateway_webhook_log.json
    │           └── gateway_webhook_log.py
    │
    └── biometric_attendance/                     ← Biometric Attendance module
        ├── __init__.py
        ├── sync.py                               ← auto_sync_all_devices(), pull_device_logs(), mark_absent_employees()
        ├── processor.py                          ← process_pending_logs(), _create_attendance()
        ├── events.py                             ← validate_attendance() (prevent duplicates)
        └── doctype/
            ├── __init__.py
            │
            ├── biometric_device/                 ← Device config (brand, IP, credentials, sync mode)
            │   ├── __init__.py
            │   ├── biometric_device.json         ← DocType schema (all 8 brands + protocol fields)
            │   ├── biometric_device.py           ← validate(), ping(), pull_logs(), get_users()
            │   └── biometric_device.js           ← Auto-set protocol/port, Ping/Sync/Users buttons
            │
            ├── biometric_attendance_log/         ← Raw punch records from devices
            │   ├── __init__.py
            │   ├── biometric_attendance_log.json
            │   └── biometric_attendance_log.py   ← before_insert(), process_to_attendance()
            │
            ├── biometric_sync_log/               ← Per-sync audit (device, fetched, created, errors)
            │   ├── __init__.py
            │   ├── biometric_sync_log.json
            │   └── biometric_sync_log.py
            │
            └── device_employee_mapping/          ← Map biometric_user_id → ERPNext Employee
                ├── __init__.py
                ├── device_employee_mapping.json
                └── device_employee_mapping.py


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DATA FLOW SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PAYMENT FLOW:
  Sales Invoice (submitted)
    → api/payment.py::initiate()
    → utils/gateway_router.py → gateways/paystack.py (or flutterwave etc.)
    → Payment Gateway Log (status: Initiated)
    → Customer pays on gateway page
    → Webhook → api/payment.py::webhook()
    → Payment Gateway Log (status: Success)
    → Payment Entry created → Sales Invoice marked Paid

BIOMETRIC FLOW:
  hooks.py scheduler (every 30 min)
    → api/attendance.py::sync_device()  OR  push endpoint::receive_push()
    → utils/device_connector.py → ZKTecoConnector / HikvisionConnector / etc.
    → Biometric Attendance Log (raw punches)
    → biometric_attendance/processor.py::process_pending_logs()
    → ERPNext Attendance record (IN/OUT times, status)
    → Salary Slip via standard ERPNext Payroll

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEVICE CONNECTOR BRAND MAP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Brand       Protocol        Port    Connector Class       Auth Method
ZKTeco      SDK/UDP         4370    ZKTecoConnector       communication_key (numeric)
eSSL        SDK/UDP         4370    ZKTecoConnector       communication_key (numeric)
Hikvision   ISAPI/REST      80/443  HikvisionConnector    username + password (Basic)
Dahua       HTTP CGI        80/443  DahuaConnector        username + password (Digest)
Suprema     BioStar2 REST   443     SupremaConnector      username + password → session token
Anviz       CloudClox REST  cloud   AnvizConnector        api_key (Bearer) + cloudclox_device_id
Virdi       REST API        80/443  VirdiConnector        username + password OR api_key (Bearer)
Realand     SDK/UDP         4370    RealandConnector      communication_key (force_udp=True)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INSTALLATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  bench get-app ecclesia /path/to/ecclesia   (or git URL)
  bench --site yoursite.com install-app ecclesia
  bench --site yoursite.com migrate
  bench restart

Python dependencies (requirements.txt):
  pyzk          ← ZKTeco + eSSL + Realand
  requests      ← Hikvision, Dahua, Suprema, Anviz, Virdi, all gateways