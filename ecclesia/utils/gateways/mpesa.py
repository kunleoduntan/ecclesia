"""
M-Pesa (Safaricom) Payment Gateway Handler
STK Push (Lipa na M-Pesa Online) for Kenya, Tanzania, Uganda.
Docs: https://developer.safaricom.co.ke/APIs/MpesaExpressSimulate

Credentials in Payment Gateway Settings:
  public_key    = Consumer Key       (from Safaricom developer portal)
  secret_key    = Consumer Secret    (from Safaricom developer portal)
  webhook_secret = Business Short Code (Paybill or Till number)
  test_mode     = True → sandbox, False → production

Additional config stored in base_url field:
  base_url      = Passkey            (from Safaricom for your shortcode)
  Note: Store the passkey in base_url field as a workaround since
        Safaricom needs 3 credentials. Alternatively add a custom field.
"""
import base64
import hashlib
import json
import time
from datetime import datetime

import requests

from ecclesia.utils.gateways.base import BaseGatewayHandler


class MpesaHandler(BaseGatewayHandler):

    def _base(self):
        if self.settings.test_mode:
            return "https://sandbox.safaricom.co.ke"
        return "https://api.safaricom.co.ke"

    def _shortcode(self):
        return self.settings.get_password("webhook_secret") or ""

    def _passkey(self):
        # Stored in base_url field (passkey is not a URL but reusing the field)
        return self.settings.base_url or ""

    def _access_token(self):
        """Get OAuth token from Safaricom. Valid for 1 hour."""
        key    = self.settings.public_key or ""
        secret = self.settings.get_password("secret_key") or ""

        credentials = base64.b64encode(f"{key}:{secret}".encode()).decode()
        r = requests.get(
            f"{self._base()}/oauth/v1/generate?grant_type=client_credentials",
            headers={"Authorization": f"Basic {credentials}"},
            timeout=15
        )
        r.raise_for_status()
        return r.json().get("access_token", "")

    def _headers(self):
        return {
            "Authorization": f"Bearer {self._access_token()}",
            "Content-Type":  "application/json"
        }

    def _password_and_timestamp(self):
        """
        M-Pesa password = Base64(shortcode + passkey + timestamp)
        Timestamp format: YYYYMMDDHHmmss
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        raw       = f"{self._shortcode()}{self._passkey()}{timestamp}"
        password  = base64.b64encode(raw.encode()).decode()
        return password, timestamp

    # ── initiate (STK Push) ───────────────────────────────────────────────────

    def initiate(self, amount, currency, email, reference, callback_url, **kwargs):
        """
        Send an STK Push to the customer's M-Pesa phone.
        Requires phone number in kwargs['phone'] — format: 254XXXXXXXXX
        """
        phone = kwargs.get("phone", "")
        if not phone:
            raise ValueError(
                "M-Pesa STK Push requires a phone number. "
                "Pass phone='254XXXXXXXXX' in the payment metadata."
            )

        # Normalise phone: strip +, leading 0 → 254
        phone = str(phone).strip().lstrip("+")
        if phone.startswith("0"):
            phone = "254" + phone[1:]

        password, timestamp = self._password_and_timestamp()
        shortcode           = self._shortcode()

        payload = {
            "BusinessShortCode": shortcode,
            "Password":          password,
            "Timestamp":         timestamp,
            "TransactionType":   "CustomerPayBillOnline",
            "Amount":            int(float(amount)),     # M-Pesa uses whole KES
            "PartyA":            phone,
            "PartyB":            shortcode,
            "PhoneNumber":       phone,
            "CallBackURL":       callback_url,
            "AccountReference":  reference[:12],          # max 12 chars
            "TransactionDesc":   kwargs.get("description", "Payment")[:13],
        }

        r = requests.post(
            f"{self._base()}/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers=self._headers(),
            timeout=30
        )
        r.raise_for_status()
        data = r.json()

        # ResponseCode "0" = accepted (not yet paid — customer must approve on phone)
        if data.get("ResponseCode") != "0":
            raise ValueError(f"M-Pesa STK Push failed: {data.get('ResponseDescription')}")

        checkout_request_id = data.get("CheckoutRequestID", "")
        return {
            # No redirect URL — M-Pesa sends prompt to phone
            "authorization_url": None,
            "reference":         checkout_request_id,
            "message":           data.get("CustomerMessage", "Check your phone to complete payment"),
        }

    # ── verify ────────────────────────────────────────────────────────────────

    def verify(self, transaction_ref):
        """
        Query status of an STK Push by CheckoutRequestID.
        Call this after receiving the callback or for manual checks.
        """
        password, timestamp = self._password_and_timestamp()

        payload = {
            "BusinessShortCode": self._shortcode(),
            "Password":          password,
            "Timestamp":         timestamp,
            "CheckoutRequestID": transaction_ref,
        }

        r = requests.post(
            f"{self._base()}/mpesa/stkpushquery/v1/query",
            json=payload,
            headers=self._headers(),
            timeout=30
        )
        r.raise_for_status()
        data = r.json()

        # ResultCode "0" = success
        success = str(data.get("ResultCode", "")) == "0"
        return {
            "status":          "success" if success else "pending",
            "transaction_ref": transaction_ref,
            "mpesa_receipt":   data.get("MpesaReceiptNumber", ""),
            "amount":          data.get("Amount"),
            "currency":        "KES",
            "raw":             data
        }

    # ── webhook ───────────────────────────────────────────────────────────────

    def verify_webhook(self, payload, headers, secret):
        """
        Safaricom does not sign callbacks with HMAC.
        Basic IP whitelisting is done at the network level.
        Return True and rely on ResultCode in parse_event().
        """
        return True

    def parse_event(self, payload):
        """
        M-Pesa STK callback body:
        {
          "Body": {
            "stkCallback": {
              "ResultCode": 0,
              "ResultDesc": "...",
              "CallbackMetadata": { "Item": [...] }
            }
          }
        }
        """
        stk      = payload.get("Body", {}).get("stkCallback", {})
        code     = str(stk.get("ResultCode", "1"))
        success  = code == "0"

        # Extract metadata items if success
        amount, receipt, phone = None, "", ""
        if success:
            items = stk.get("CallbackMetadata", {}).get("Item", [])
            meta  = {i["Name"]: i.get("Value") for i in items}
            amount  = meta.get("Amount")
            receipt = str(meta.get("MpesaReceiptNumber", ""))
            phone   = str(meta.get("PhoneNumber", ""))

        return {
            "status":          "success" if success else "failed",
            "transaction_ref": receipt or stk.get("CheckoutRequestID", ""),
            "amount":          amount,
            "currency":        "KES",
            "phone":           phone,
            "metadata":        stk
        }

    # ── refund (reversal) ─────────────────────────────────────────────────────

    def refund(self, transaction_ref, amount=None):
        """
        M-Pesa Transaction Reversal API.
        transaction_ref must be the MpesaReceiptNumber (e.g. QH721I3ASB).
        """
        payload = {
            "Initiator":              "apitest",      # replace with your initiator name
            "SecurityCredential":     "",             # encrypted credential — set in deployment
            "CommandID":              "TransactionReversal",
            "TransactionID":          transaction_ref,
            "Amount":                 str(int(float(amount or 0))),
            "ReceiverParty":          self._shortcode(),
            "RecieverIdentifierType": "11",
            "ResultURL":              self.settings.callback_url or "",
            "QueueTimeOutURL":        self.settings.callback_url or "",
            "Remarks":                "Refund",
            "Occasion":               "",
        }

        r = requests.post(
            f"{self._base()}/mpesa/reversal/v1/request",
            json=payload,
            headers=self._headers(),
            timeout=30
        )
        r.raise_for_status()
        data = r.json()

        return {
            "status":  "submitted",
            "message": data.get("ResponseDescription", "Reversal submitted"),
            "raw":     data
        }