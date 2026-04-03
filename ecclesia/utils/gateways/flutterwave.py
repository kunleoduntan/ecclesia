import hashlib
import requests
from ecclesia.utils.gateways.base import BaseGatewayHandler


FW_BASE = "https://api.flutterwave.com/v3"


class FlutterwaveHandler(BaseGatewayHandler):

    def initiate(self, amount, currency, email, reference, callback_url):
        payload = {
            "tx_ref": reference,
            "amount": str(amount),
            "currency": currency or "NGN",
            "redirect_url": callback_url,
            "customer": {"email": email},
            "customizations": {"title": "Payment"}
        }
        r = requests.post(f"{FW_BASE}/payments",
                          json=payload, headers=self.headers, timeout=30)
        r.raise_for_status()
        data = r.json().get("data", {})
        return {"authorization_url": data.get("link"), "reference": reference}

    def verify(self, transaction_ref):
        r = requests.get(f"{FW_BASE}/transactions/verify_by_reference",
                         params={"tx_ref": transaction_ref},
                         headers=self.headers, timeout=30)
        r.raise_for_status()
        return r.json().get("data", {})

    def verify_webhook(self, payload, headers, secret):
        sig = headers.get("Verif-Hash", "")
        return sig == secret

    def parse_event(self, payload):
        data = payload.get("data", {})
        return {
            "status": "success" if data.get("status") == "successful" else "failed",
            "transaction_ref": data.get("tx_ref"),
            "amount": data.get("amount"),
            "currency": data.get("currency"),
            "metadata": data.get("meta", {})
        }

    def refund(self, transaction_ref, amount=None):
        payload = {"id": transaction_ref}
        if amount:
            payload["amount"] = amount
        r = requests.post(f"{FW_BASE}/transactions/{transaction_ref}/refund",
                          json=payload, headers=self.headers, timeout=30)
        r.raise_for_status()
        return r.json()