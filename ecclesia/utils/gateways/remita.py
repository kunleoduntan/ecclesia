"""
Remita Payment Gateway Handler
Used heavily by Nigerian government agencies, universities, and corporates.
Docs: https://remitademo.net/remita/developers

Flow:
  1. Generate RRR (Remita Retrieval Reference) via initiate()
  2. Redirect customer to Remita payment page
  3. Customer pays → Remita calls your webhook (or you poll verify())
  4. On success → reconcile in ERPNext
"""
import hashlib
import hmac
import json
import requests

from ecclesia.utils.gateways.base import BaseGatewayHandler


class RemitaHandler(BaseGatewayHandler):
    """
    Credentials needed in Payment Gateway Settings:
      public_key   = Merchant ID (merchantId)
      secret_key   = Service Type ID (serviceTypeId)  ← Remita calls this the API key
      webhook_secret = API Key for hash generation

    test_mode = True  → uses remitademo.net
    test_mode = False → uses login.remita.net
    """

    def _base(self):
        if self.settings.test_mode:
            return "https://remitademo.net/remita/exapp/api/v1/send/payment"
        return "https://login.remita.net/remita/exapp/api/v1/send/payment"

    def _merchant_id(self):
        return self.settings.public_key or ""

    def _service_type_id(self):
        return self.settings.get_password("secret_key") or ""

    def _api_key(self):
        return self.settings.get_password("webhook_secret") or ""

    def _auth_hash(self, rrr=""):
        """SHA512(merchantId + serviceTypeId + orderId + totalAmount + apiKey)"""
        raw = f"{self._merchant_id()}{self._service_type_id()}{rrr}{self._api_key()}"
        return hashlib.sha512(raw.encode()).hexdigest()

    # ── initiate ──────────────────────────────────────────────────────────────

    def initiate(self, amount, currency, email, reference, callback_url, **kwargs):
        """
        Step 1: Get an RRR from Remita.
        Returns authorization_url (Remita hosted payment page).
        """
        merchant_id    = self._merchant_id()
        service_type   = self._service_type_id()
        api_key        = self._api_key()

        # Hash = SHA512(merchantId + serviceTypeId + orderId + totalAmount + apiKey)
        raw_hash = f"{merchant_id}{service_type}{reference}{amount}{api_key}"
        auth_hash = hashlib.sha512(raw_hash.encode()).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"remitaConsumerKey={merchant_id},remitaConsumerToken={auth_hash}"
        }

        payload = {
            "serviceTypeId": service_type,
            "amount":         str(amount),
            "orderId":        reference,
            "payerName":      kwargs.get("customer_name", "Customer"),
            "payerEmail":     email,
            "payerPhone":     kwargs.get("phone", ""),
            "description":    kwargs.get("description", f"Payment {reference}"),
            "responseurl":    callback_url,
        }

        r = requests.post(
            f"{self._base()}/init",
            json=payload, headers=headers, timeout=30
        )
        r.raise_for_status()
        data = r.json()

        rrr = data.get("RRR") or data.get("rrr", "")
        if not rrr:
            raise ValueError(f"Remita did not return RRR: {data}")

        # Build redirect URL for customer
        base_pay = (
            "https://remitademo.net/remita/ecomm/init.reg"
            if self.settings.test_mode
            else "https://login.remita.net/remita/ecomm/init.reg"
        )
        pay_url = (
            f"{base_pay}?merchantId={merchant_id}"
            f"&hash={self._auth_hash(rrr)}"
            f"&rrr={rrr}"
            f"&responseurl={callback_url}"
        )

        return {"authorization_url": pay_url, "reference": rrr}

    # ── verify ────────────────────────────────────────────────────────────────

    def verify(self, transaction_ref):
        """Verify payment status by RRR."""
        merchant_id = self._merchant_id()
        auth_hash   = self._auth_hash(transaction_ref)

        headers = {
            "Content-Type": "application/json",
            "Authorization": (
                f"remitaConsumerKey={merchant_id},"
                f"remitaConsumerToken={auth_hash}"
            )
        }

        r = requests.get(
            f"{self._base()}/{transaction_ref}/status",
            headers=headers, timeout=30
        )
        r.raise_for_status()
        data = r.json()

        # Remita status codes: 01 = successful, 021 = used, others = pending/failed
        paid_codes = {"01", "021", "00"}
        status = str(data.get("status", ""))

        return {
            "status":          "success" if status in paid_codes else "pending",
            "transaction_ref": transaction_ref,
            "amount":          data.get("amount"),
            "currency":        "NGN",
            "raw":             data
        }

    # ── webhook ───────────────────────────────────────────────────────────────

    def verify_webhook(self, payload, headers, secret):
        """
        Remita does not send a standard HMAC header.
        Validate by re-querying the RRR status instead.
        Always return True here; api/payment.py will call verify() to confirm.
        """
        return True

    def parse_event(self, payload):
        rrr    = payload.get("RRR") or payload.get("rrr", "")
        status = str(payload.get("status", ""))
        paid   = status in {"01", "021", "00"}
        return {
            "status":          "success" if paid else "failed",
            "transaction_ref": rrr,
            "amount":          payload.get("amount"),
            "currency":        "NGN",
            "metadata":        payload
        }

    # ── refund ────────────────────────────────────────────────────────────────

    def refund(self, transaction_ref, amount=None):
        """Remita refunds are processed manually via the merchant dashboard."""
        return {
            "status":  "manual",
            "message": (
                "Remita refunds must be processed via the Remita merchant dashboard. "
                f"RRR: {transaction_ref}"
            )
        }