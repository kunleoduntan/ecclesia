"""Base class all gateway handlers must inherit from."""


class BaseGatewayHandler:
    def __init__(self, settings):
        self.settings = settings
        self.headers = settings.get_headers()

    def initiate(self, amount, currency, email, reference, callback_url):
        raise NotImplementedError

    def verify(self, transaction_ref):
        raise NotImplementedError

    def verify_webhook(self, payload, headers, secret):
        raise NotImplementedError

    def parse_event(self, payload):
        raise NotImplementedError

    def refund(self, transaction_ref, amount=None):
        raise NotImplementedError