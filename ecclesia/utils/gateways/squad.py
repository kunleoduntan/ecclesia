"""
Squad (by GTBank) Payment Gateway Handler
Nigerian gateway with strong bank transfer and card support.
Docs: https://squadinc.gitbook.io/squad-api-documentation

Credentials in Payment Gateway Settings:
  public_key  = Squad public key  (pk_sandbox_... or pk_live_...)
  secret_key  = Squad secret key  (sk_sandbox_... or sk_live_...)
  test_mode   = True → sandbox API, False → live API
"""
import hashlib
import hmac
import json
import requests

from ecclesia.utils.gateways.base import BaseGatewayHandler


class SquadHandler(BaseGatewayHandler):

    def _base(self):
        if self.settings.test_mode:
            return "https://sandbox-api-d.squadco.com"
        return "https://api-d.squadco.com"

    # ── initiate ──────────────────────────────────────────────────────────────

    def initiate(self, amount, currency, email, reference, callback_url, **kwargs):
        """
        Initiate a transaction and get a checkout URL.
        Amount is sent in kobo (×100).
        """
        payload = {
            "email":           email,
            "amount":          int(float(amount) * 100),   # kobo
            "currency":        currency or "NGN",
            "initiate_type":   "inline",
            "transaction_ref": reference,
            "callback_url":    callback_url,
            "payment_channels": ["card", "bank_transfer", "ussd"],
        }

        if kwargs.get("customer_name"):
            payload["customer_name"] = kwargs["customer_name"]
        if kwargs.get("description"):
            payload["pass_charge"]   = False
            payload["description"]   = kwargs["description"]

        r = requests.post(
            f"{self._base()}/transaction/initiate",
            json=payload,
            headers=self.headers,
            timeout=30
        )
        r.raise_for_status()
        data = r.json()

        if data.get("success"):
            checkout = data.get("data", {}).get("checkout_url", "")
            return {"authorization_url": checkout, "reference": reference}

        raise ValueError(f"Squad initiate failed: {data.get('message')}")

    # ── verify ────────────────────────────────────────────────────────────────

    def verify(self, transaction_ref):
        r = requests.get(
            f"{self._base()}/transaction/verify/{transaction_ref}",
            headers=self.headers,
            timeout=30
        )
        r.raise_for_status()
        data = r.json().get("data", {})

        success = data.get("transaction_status") == "success"
        return {
            "status":          "success" if success else "failed",
            "transaction_ref": data.get("transaction_ref", transaction_ref),
            "amount":          (data.get("transaction_amount") or 0) / 100,
            "currency":        data.get("currency", "NGN"),
            "payment_method":  data.get("payment_type"),
            "raw":             data
        }

    # ── webhook ───────────────────────────────────────────────────────────────

    def verify_webhook(self, payload, headers, secret):
        """Squad signs webhooks with HMAC-SHA512 in the x-squad-encrypted-body header."""
        sig = headers.get("x-squad-encrypted-body", "")
        body_str = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        computed = hmac.new(
            secret.encode(), body_str.encode(), hashlib.sha512
        ).hexdigest()
        return hmac.compare_digest(sig.lower(), computed.lower())

    def parse_event(self, payload):
        event = payload.get("Event", "")
        data  = payload.get("Body", {})

        success = event == "charge_successful"
        return {
            "status":          "success" if success else "failed",
            "transaction_ref": data.get("transaction_ref", ""),
            "amount":          (data.get("amount") or 0) / 100,
            "currency":        data.get("currency", "NGN"),
            "payment_method":  data.get("payment_type"),
            "metadata":        data.get("meta_data", {})
        }

    # ── refund ────────────────────────────────────────────────────────────────

    def refund(self, transaction_ref, amount=None):
        payload = {"gateway_ref": transaction_ref}
        if amount:
            payload["refund_type"]   = 2         # partial
            payload["amount_refund"] = int(float(amount) * 100)
        else:
            payload["refund_type"]   = 1         # full

        r = requests.post(
            f"{self._base()}/transaction/refund",
            json=payload,
            headers=self.headers,
            timeout=30
        )
        r.raise_for_status()
        data = r.json()
        return {
            "status":  "success" if data.get("success") else "failed",
            "message": data.get("message", ""),
            "raw":     data
        }