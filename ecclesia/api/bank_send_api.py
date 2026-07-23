# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/api/bank_send_api.py
"""
Bank Payment Send API
═════════════════════
Direct submission of payment files to banks via:
  1. SFTP upload      — Zenith, GTB, Access, UBA SFTP servers
  2. REST API         — Paystack, Flutterwave, Squad bulk transfer APIs
  3. Status check     — Poll submission status from aggregators

Whitelisted methods:
  send_payroll_payment(payroll_entry, send_channel, gateway_name)
  send_batch_payment(payment_batch, send_channel, gateway_name)
  check_payment_status(gateway_name, batch_reference)
  get_send_channels(gateway_name)
"""

import frappe
from frappe import _
from frappe.utils import flt, nowdate, getdate
import json
import base64


# ══════════════════════════════════════════════════════════════════════════════
#  SEND CHANNELS REGISTRY
# ══════════════════════════════════════════════════════════════════════════════

SEND_CHANNELS = {
    "sftp_upload": {
        "label":       "SFTP Upload (Corporate Banking)",
        "description": "Upload payment file directly to bank SFTP server",
        "requires":    ["sftp_host", "sftp_username", "sftp_password", "sftp_path"],
        "banks":       ["Zenith Bank", "GTBank", "Access Bank", "UBA", "First Bank"],
    },
    "paystack_bulk": {
        "label":       "Paystack Bulk Transfer API",
        "description": "Send via Paystack Transfers API (REST)",
        "requires":    ["secret_key"],
        "api_url":     "https://api.paystack.co/transfer",
        "banks":       ["All Nigerian Banks"],
    },
    "flutterwave_bulk": {
        "label":       "Flutterwave Bulk Transfer API",
        "description": "Send via Flutterwave Bulk Transfer (REST)",
        "requires":    ["secret_key"],
        "api_url":     "https://api.flutterwave.com/v3/bulk-transfers",
        "banks":       ["All Nigerian Banks"],
    },
    "squad_bulk": {
        "label":       "Squad (GTBank) Bulk Transfer API",
        "description": "Send via Squad bulk disbursement API (REST)",
        "requires":    ["secret_key"],
        "api_url":     "https://api-d.squadco.com/payout/bulk",
        "banks":       ["All Nigerian Banks"],
    },
    "manual_download": {
        "label":       "Manual Download",
        "description": "Download file and upload to bank portal manually",
        "requires":    [],
        "banks":       ["All Banks"],
    },
}


@frappe.whitelist()
def get_send_channels(gateway_name=None):
    """Return available send channels, optionally filtered by gateway provider."""
    if gateway_name:
        gw = frappe.get_doc("Payment Gateway Settings", gateway_name)
        provider = (gw.provider or "").lower()
        # Filter to relevant channels for this provider
        relevant = []
        if "paystack" in provider:
            relevant = ["paystack_bulk", "manual_download"]
        elif "flutterwave" in provider:
            relevant = ["flutterwave_bulk", "manual_download"]
        elif "squad" in provider or "gtb" in provider:
            relevant = ["squad_bulk", "sftp_upload", "manual_download"]
        elif "bank" in provider or gw.bank_export_format:
            relevant = ["sftp_upload", "manual_download"]
        else:
            relevant = list(SEND_CHANNELS.keys())
        return [{"key": k, **SEND_CHANNELS[k]} for k in relevant]
    return [{"key": k, **v} for k, v in SEND_CHANNELS.items()]


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN SEND ENTRY POINTS
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def send_payroll_payment(payroll_entry, send_channel, gateway_name):
    """
    Generate and send payroll payment file from a submitted Payroll Entry.

    send_channel: sftp_upload | paystack_bulk | flutterwave_bulk | squad_bulk
    gateway_name: Payment Gateway Settings record name
    """
    # 1. Generate the file
    from ecclesia.api.bank_payment_export import generate_payroll_payment_file
    gw     = frappe.get_doc("Payment Gateway Settings", gateway_name)
    fmt    = gw.bank_export_format or "zenith_iso20022"
    result = generate_payroll_payment_file(payroll_entry, fmt)

    if not result.get("success"):
        return result

    # 2. Send via the chosen channel
    return _dispatch_send(
        result       = result,
        send_channel = send_channel,
        gateway      = gw,
        source_doc   = payroll_entry,
        source_type  = "Payroll Entry",
    )


@frappe.whitelist()
def send_batch_payment(payment_batch, send_channel, gateway_name):
    """
    Generate and send a bank payment file from a submitted Batch Bank Transaction.
    """
    from ecclesia.api.bank_payment_export import generate_batch_payment_file
    gw     = frappe.get_doc("Payment Gateway Settings", gateway_name)
    fmt    = gw.bank_export_format or "zenith_iso20022"
    result = generate_batch_payment_file(payment_batch, fmt)

    if not result.get("success"):
        return result

    return _dispatch_send(
        result       = result,
        send_channel = send_channel,
        gateway      = gw,
        source_doc   = payment_batch,
        source_type  = "Batch Bank Transaction",
    )


def _dispatch_send(result, send_channel, gateway, source_doc, source_type):
    """Route to the correct send implementation."""
    fn_map = {
        "sftp_upload":       _send_sftp,
        "paystack_bulk":     _send_paystack,
        "flutterwave_bulk":  _send_flutterwave,
        "squad_bulk":        _send_squad,
        "manual_download":   _send_manual,
    }
    fn = fn_map.get(send_channel)
    if not fn:
        return {"success": False, "error": f"Unknown send channel: {send_channel}"}

    send_result = fn(result, gateway)

    # Log the submission regardless of outcome
    _log_submission(
        source_type  = source_type,
        source_name  = source_doc,
        send_channel = send_channel,
        gateway_name = gateway.name,
        file_name    = result.get("file_name",""),
        row_count    = result.get("row_count", 0),
        total_amount = result.get("total_amount", 0),
        send_result  = send_result,
    )
    return send_result


# ══════════════════════════════════════════════════════════════════════════════
#  CHANNEL IMPLEMENTATIONS
# ══════════════════════════════════════════════════════════════════════════════

# ── 1. SFTP Upload ────────────────────────────────────────────────────────────

def _send_sftp(result, gateway):
    """
    Upload the payment file to the bank's SFTP server.

    Gateway fields used:
      sftp_host     — e.g. sftp.zenithbank.com
      sftp_port     — default 22
      sftp_username — corporate SFTP login
      sftp_password — dedicated SFTP Password field
      sftp_path     — remote folder, e.g. /uploads/payroll/
    """
    try:
        import paramiko, io

        host     = getattr(gateway, "sftp_host", "") or ""
        port     = int(getattr(gateway, "sftp_port", 22) or 22)
        username = getattr(gateway, "sftp_username", "") or ""
        password = gateway.get_password("sftp_password") or ""
        path     = getattr(gateway, "sftp_path", "/uploads/") or "/uploads/"

        if not host:
            return {
                "success": False,
                "error": "SFTP host not configured. Set sftp_host in Payment Gateway Settings.",
                "channel": "sftp_upload",
            }
        if not username or not password:
            return {
                "success": False,
                "error": "SFTP credentials not configured. Set SFTP Username and SFTP Password in the Payment Gateway Settings record.",
                "channel": "sftp_upload",
            }

        # Decode the file
        file_bytes = base64.b64decode(result["file_data"])
        file_name  = result["file_name"]
        remote_path = path.rstrip("/") + "/" + file_name

        # Connect and upload
        transport = paramiko.Transport((host, port))
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.putfo(io.BytesIO(file_bytes), remote_path)
        sftp.close()
        transport.close()

        return {
            "success":     True,
            "channel":     "sftp_upload",
            "message":     f"File uploaded to {host}{remote_path}",
            "file_name":   file_name,
            "remote_path": remote_path,
            "row_count":   result.get("row_count", 0),
            "total_amount": result.get("total_amount", 0),
        }

    except ImportError:
        return {
            "success": False,
            "channel": "sftp_upload",
            "error": "paramiko library not installed. Run: pip install paramiko --break-system-packages",
        }
    except Exception as e:
        frappe.log_error(f"SFTP upload failed: {e}", "Bank Send API")
        return {"success": False, "channel": "sftp_upload", "error": str(e)}


# ── 2. Paystack Bulk Transfer ─────────────────────────────────────────────────

def _send_paystack(result, gateway):
    """
    Send bulk transfer via Paystack Transfers API.
    Paystack supports bulk transfers via POST /transfer/bulk.

    Docs: https://paystack.com/docs/transfers/bulk-transfers
    """
    try:
        import requests

        secret_key = gateway.get_password("secret_key") or ""
        if not secret_key:
            return {"success": False, "channel": "paystack_bulk",
                    "error": "Paystack secret key not configured in Payment Gateway Settings."}

        base_url = (gateway.base_url or "https://api.paystack.co").rstrip("/")

        # Parse the payment file to extract rows
        # For Paystack we need: amount (kobo), recipient_code or account details
        # First create transfer recipients, then bulk transfer
        file_bytes = base64.b64decode(result["file_data"])
        rows = _parse_csv_rows(file_bytes, result.get("format",""))

        if not rows:
            return {"success": False, "channel": "paystack_bulk",
                    "error": "Could not parse payment rows from file."}

        # Step 1: Create transfer recipients
        recipients = []
        for row in rows:
            acc_no   = row.get("cred_acc_no", "")
            bank_code= _bic_to_nibss_code(row.get("cred_acc_bic",""))
            name     = row.get("cred_name", "")

            if not acc_no or not bank_code:
                continue

            res = requests.post(
                f"{base_url}/transferrecipient",
                headers={"Authorization": f"Bearer {secret_key}",
                         "Content-Type": "application/json"},
                json={
                    "type":           "nuban",
                    "name":           name,
                    "account_number": acc_no,
                    "bank_code":      bank_code,
                    "currency":       row.get("currency", "NGN"),
                },
                timeout=30
            )
            rdata = res.json()
            if rdata.get("status"):
                recipients.append({
                    "amount":           int(flt(row.get("amount",0)) * 100),  # kobo
                    "reference":        row.get("reference","")[:60],
                    "reason":           row.get("details","PAYROLL")[:30],
                    "recipient":        rdata["data"]["recipient_code"],
                })

        if not recipients:
            return {"success": False, "channel": "paystack_bulk",
                    "error": "No valid recipients created. Check account numbers and bank codes."}

        # Step 2: Bulk transfer
        res = requests.post(
            f"{base_url}/transfer/bulk",
            headers={"Authorization": f"Bearer {secret_key}",
                     "Content-Type": "application/json"},
            json={"currency": "NGN", "source": "balance", "transfers": recipients},
            timeout=60
        )
        data = res.json()

        if data.get("status"):
            return {
                "success":      True,
                "channel":      "paystack_bulk",
                "message":      f"Paystack bulk transfer initiated — {len(recipients)} recipients",
                "batch_code":   data.get("data", {}).get("batch_code",""),
                "reference":    data.get("data", {}).get("transfer_code",""),
                "row_count":    len(recipients),
                "total_amount": result.get("total_amount", 0),
            }
        else:
            return {
                "success": False,
                "channel": "paystack_bulk",
                "error":   data.get("message", "Paystack transfer failed"),
                "details": data,
            }

    except Exception as e:
        frappe.log_error(f"Paystack bulk transfer failed: {e}", "Bank Send API")
        return {"success": False, "channel": "paystack_bulk", "error": str(e)}


# ── 3. Flutterwave Bulk Transfer ──────────────────────────────────────────────

def _send_flutterwave(result, gateway):
    """
    Send bulk transfer via Flutterwave Bulk Transfers API.
    Docs: https://developer.flutterwave.com/docs/making-payments/payouts
    """
    try:
        import requests

        secret_key = gateway.get_password("secret_key") or ""
        if not secret_key:
            return {"success": False, "channel": "flutterwave_bulk",
                    "error": "Flutterwave secret key not configured."}

        base_url = (gateway.base_url or "https://api.flutterwave.com/v3").rstrip("/")
        file_bytes = base64.b64decode(result["file_data"])
        rows = _parse_csv_rows(file_bytes, result.get("format",""))

        if not rows:
            return {"success": False, "channel": "flutterwave_bulk",
                    "error": "Could not parse payment rows."}

        bulk_data = []
        for i, row in enumerate(rows):
            bank_code = _bic_to_nibss_code(row.get("cred_acc_bic",""))
            bulk_data.append({
                "Bank":           bank_code,
                "Account Number": row.get("cred_acc_no",""),
                "Amount":         flt(row.get("amount",0)),
                "Currency":       row.get("currency","NGN"),
                "Narration":      row.get("details","PAYROLL")[:100],
                "reference":      f"{row.get('reference','')}_{i}",
                "beneficiary_name": row.get("cred_name",""),
            })

        res = requests.post(
            f"{base_url}/bulk-transfers",
            headers={"Authorization": f"Bearer {secret_key}",
                     "Content-Type": "application/json"},
            json={
                "title":          result.get("file_name","Bulk Payment"),
                "bulk_data":      bulk_data,
            },
            timeout=60
        )
        data = res.json()

        if data.get("status") == "success":
            return {
                "success":    True,
                "channel":    "flutterwave_bulk",
                "message":    f"Flutterwave bulk transfer queued — {len(bulk_data)} beneficiaries",
                "reference":  data.get("data",{}).get("id",""),
                "row_count":  len(bulk_data),
                "total_amount": result.get("total_amount",0),
            }
        else:
            return {
                "success": False,
                "channel": "flutterwave_bulk",
                "error":   data.get("message","Flutterwave transfer failed"),
            }

    except Exception as e:
        frappe.log_error(f"Flutterwave bulk transfer failed: {e}", "Bank Send API")
        return {"success": False, "channel": "flutterwave_bulk", "error": str(e)}


# ── 4. Squad (GTBank) Bulk Transfer ──────────────────────────────────────────

def _send_squad(result, gateway):
    """
    Send via Squad's bulk payout API.
    Docs: https://squadinc.gitbook.io/squad-api-documentation/transfer-api
    """
    try:
        import requests

        secret_key = gateway.get_password("secret_key") or ""
        if not secret_key:
            return {"success": False, "channel": "squad_bulk",
                    "error": "Squad secret key not configured."}

        is_test   = getattr(gateway, "test_mode", 1)
        base_url  = ("https://sandbox-api-d.squadco.com"
                     if is_test else "https://api-d.squadco.com")

        file_bytes = base64.b64decode(result["file_data"])
        rows = _parse_csv_rows(file_bytes, result.get("format",""))

        if not rows:
            return {"success": False, "channel": "squad_bulk",
                    "error": "Could not parse payment rows."}

        transfers = []
        for row in rows:
            bank_code = _bic_to_nibss_code(row.get("cred_acc_bic",""))
            transfers.append({
                "account_number":   row.get("cred_acc_no",""),
                "bank_code":        bank_code,
                "amount":           int(flt(row.get("amount",0)) * 100),  # kobo
                "currency_id":      "NGN",
                "remark":           row.get("details","PAYROLL")[:100],
                "transaction_reference": f"{row.get('reference','')}",
                "beneficiary_name": row.get("cred_name",""),
            })

        res = requests.post(
            f"{base_url}/payout/bulk",
            headers={"Authorization": f"Bearer {secret_key}",
                     "Content-Type": "application/json"},
            json={"bulk_list": transfers},
            timeout=60
        )
        data = res.json()

        if data.get("success"):
            return {
                "success":    True,
                "channel":    "squad_bulk",
                "message":    f"Squad bulk transfer queued — {len(transfers)} beneficiaries",
                "reference":  data.get("data",{}).get("batch_reference",""),
                "row_count":  len(transfers),
                "total_amount": result.get("total_amount",0),
            }
        else:
            return {
                "success": False,
                "channel": "squad_bulk",
                "error":   data.get("message","Squad transfer failed"),
            }

    except Exception as e:
        frappe.log_error(f"Squad bulk transfer failed: {e}", "Bank Send API")
        return {"success": False, "channel": "squad_bulk", "error": str(e)}


# ── 5. Manual Download (passthrough) ─────────────────────────────────────────

def _send_manual(result, gateway):
    """Return the file for the user to download and upload manually."""
    return {
        "success":      True,
        "channel":      "manual_download",
        "message":      "File ready for download. Upload to your bank portal manually.",
        "file_data":    result.get("file_data",""),
        "file_name":    result.get("file_name",""),
        "row_count":    result.get("row_count",0),
        "total_amount": result.get("total_amount",0),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  STATUS CHECK
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def check_payment_status(gateway_name, batch_reference):
    """
    Check submission status from the payment provider.
    Supported: paystack_bulk, flutterwave_bulk, squad_bulk
    """
    try:
        import requests
        gw         = frappe.get_doc("Payment Gateway Settings", gateway_name)
        provider   = (gw.provider or "").lower()
        secret_key = gw.get_password("secret_key") or ""

        if "paystack" in provider:
            res  = requests.get(
                f"https://api.paystack.co/transfer/{batch_reference}",
                headers={"Authorization": f"Bearer {secret_key}"},
                timeout=15
            )
            data = res.json()
            return {
                "success":   True,
                "provider":  "Paystack",
                "reference": batch_reference,
                "status":    data.get("data",{}).get("status","unknown"),
                "details":   data.get("data",{}),
            }

        elif "flutterwave" in provider:
            res  = requests.get(
                f"https://api.flutterwave.com/v3/bulk-transfers/{batch_reference}",
                headers={"Authorization": f"Bearer {secret_key}"},
                timeout=15
            )
            data = res.json()
            return {
                "success":   True,
                "provider":  "Flutterwave",
                "reference": batch_reference,
                "status":    data.get("status","unknown"),
                "details":   data.get("data",{}),
            }

        elif "squad" in provider:
            is_test = getattr(gw, "test_mode", 1)
            base    = "https://sandbox-api-d.squadco.com" if is_test else "https://api-d.squadco.com"
            res     = requests.get(
                f"{base}/payout/bulk/{batch_reference}",
                headers={"Authorization": f"Bearer {secret_key}"},
                timeout=15
            )
            data = res.json()
            return {
                "success":   True,
                "provider":  "Squad",
                "reference": batch_reference,
                "status":    data.get("data",{}).get("status","unknown"),
                "details":   data.get("data",{}),
            }

        else:
            return {
                "success": False,
                "error":   f"Status check not supported for provider: {gw.provider}. Check your bank portal directly.",
            }

    except Exception as e:
        frappe.log_error(f"Payment status check failed: {e}", "Bank Send API")
        return {"success": False, "error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
#  GATEWAY SETTINGS — SFTP FIELDS
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_sftp_fields():
    """Return the list of SFTP fields that should be added to Payment Gateway Settings."""
    return [
        {"fieldname": "sftp_host",     "fieldtype": "Data",     "label": "SFTP Host"},
        {"fieldname": "sftp_port",     "fieldtype": "Int",      "label": "SFTP Port", "default": "22"},
        {"fieldname": "sftp_username", "fieldtype": "Data",     "label": "SFTP Username"},
        {"fieldname": "sftp_path",     "fieldtype": "Data",     "label": "SFTP Remote Path",
         "description": "e.g. /uploads/payroll/"},
    ]


# ══════════════════════════════════════════════════════════════════════════════
#  UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def _parse_csv_rows(file_bytes, fmt=""):
    """
    Parse the generated payment file back into a list of dicts for API submission.
    Works for Zenith ISO 20022 CSV and all other CSV formats.
    """
    import csv, io

    try:
        text = file_bytes.decode("utf-8")
        # Detect delimiter
        delimiter = ";" if fmt == "zenith_iso20022" else ","

        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        rows = []
        for r in reader:
            # Normalise key names to our standard payment dict keys
            row = {
                "cred_name":    r.get("CRED_NAME") or r.get("Beneficiary Name") or r.get("AccountName") or r.get("Employee Name") or r.get("BENEFICIARY_NAME",""),
                "cred_acc_no":  r.get("CREDACC_NUMBER") or r.get("Beneficiary Account Number") or r.get("AccountNumber") or r.get("Account Number") or r.get("BENEFICIARY_ACCOUNT",""),
                "cred_acc_bic": r.get("CREDACC_BIC") or r.get("BankCode") or r.get("Bank Code",""),
                "amount":       r.get("OPE_PAYMENT_AMOUNT") or r.get("Amount") or r.get("Net Pay","0"),
                "currency":     r.get("OPE_PAYMENT_CURRENCY") or r.get("CurrencyCode","NGN"),
                "details":      r.get("OPE_DETAILS") or r.get("Narration") or r.get("Payment Description","PAYROLL"),
                "reference":    r.get("OPE_END_TO_END_ID") or r.get("Reference",""),
            }
            if row["cred_acc_no"]:
                rows.append(row)
        return rows
    except Exception as e:
        frappe.log_error(f"CSV parse failed: {e}", "Bank Send API")
        return []


# Nigerian bank NIP codes (for Paystack/Flutterwave/Squad)
_NIBSS_CODES = {
    "ZEIBNGLA": "000015",  # Zenith Bank
    "GTBINGLA": "000013",  # GTBank
    "ABNGNGLA": "000014",  # Access Bank
    "UNAFNGLA": "000004",  # UBA
    "FBNINGLA": "000016",  # First Bank
    "FCMBNGLA": "000003",  # FCMB
    "NAMENGLA": "000232",  # Sterling
    "SBICNGLA": "000012",  # Stanbic IBTC
    "UBNINGLA": "000018",  # Union Bank
    "WEMANGLA": "000017",  # Wema Bank
    "ECOCNGLA": "000010",  # Ecobank
    "FIDTNGLA": "000007",  # Fidelity
    "JAIZNGLA": "000006",  # JAIZ
}

def _bic_to_nibss_code(bic):
    """Convert BIC/SWIFT to NIBSS bank code for API submissions."""
    return _NIBSS_CODES.get(bic, "000015")


def _log_submission(source_type, source_name, send_channel, gateway_name,
                    file_name, row_count, total_amount, send_result):
    """Log bank submission to Payment Gateway Log."""
    try:
        if not frappe.db.table_exists("tabPayment Gateway Log"):
            return
        frappe.get_doc({
            "doctype":         "Payment Gateway Log",
            "gateway":         gateway_name,
            "reference_doctype": source_type,
            "reference_name":  source_name,
            "channel":         send_channel,
            "file_name":       file_name,
            "row_count":       row_count,
            "total_amount":    total_amount,
            "status":          "Success" if send_result.get("success") else "Failed",
            "response":        json.dumps(send_result)[:2000],
            "batch_reference": send_result.get("reference","") or send_result.get("batch_code",""),
            "message":         send_result.get("message","") or send_result.get("error",""),
        }).insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(f"Failed to log payment submission: {e}", "Bank Send API")