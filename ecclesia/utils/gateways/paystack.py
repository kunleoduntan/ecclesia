import hashlib
import hmac
import json
import requests
from ecclesia.utils.gateways.base import BaseGatewayHandler


PAYSTACK_BASE = "https://api.paystack.co"


class PaystackHandler(BaseGatewayHandler):

    def initiate(self, amount, currency, email, reference, callback_url):
        payload = {
            "email": email,
            "amount": int(float(amount) * 100),   # kobo
            "currency": currency or "NGN",
            "reference": reference,
            "callback_url": callback_url
        }
        r = requests.post(f"{PAYSTACK_BASE}/transaction/initialize",
                          json=payload, headers=self.headers, timeout=30)
        r.raise_for_status()
        data = r.json().get("data", {})
        return {"authorization_url": data.get("authorization_url"),
                "reference": data.get("reference")}

    def verify(self, transaction_ref):
        r = requests.get(f"{PAYSTACK_BASE}/transaction/verify/{transaction_ref}",
                         headers=self.headers, timeout=30)
        r.raise_for_status()
        return r.json().get("data", {})

    def verify_webhook(self, payload, headers, secret):
        sig = headers.get("X-Paystack-Signature", "")
        computed = hmac.new(secret.encode(), json.dumps(payload).encode(),
                            hashlib.sha512).hexdigest()
        return hmac.compare_digest(sig, computed)

    def parse_event(self, payload):
        data = payload.get("data", {})
        return {
            "status": "success" if payload.get("event") == "charge.success" else "failed",
            "transaction_ref": data.get("reference"),
            "amount": data.get("amount", 0) / 100,
            "currency": data.get("currency"),
            "metadata": data.get("metadata", {})
        }

    def refund(self, transaction_ref, amount=None):
        payload = {"transaction": transaction_ref}
        if amount:
            payload["amount"] = int(float(amount) * 100)
        r = requests.post(f"{PAYSTACK_BASE}/refund",
                          json=payload, headers=self.headers, timeout=30)
        r.raise_for_status()
        return r.json()