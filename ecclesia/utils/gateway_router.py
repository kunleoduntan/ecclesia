"""
Routes to the correct gateway handler based on Payment Gateway Settings provider field.
"""
import frappe


def get_gateway_handler(settings):
    provider = settings.provider
    handlers = {
        "Paystack": "ecclesia.utils.gateways.paystack.PaystackHandler",
        "Flutterwave": "ecclesia.utils.gateways.flutterwave.FlutterwaveHandler",
        "Remita": "ecclesia.utils.gateways.remita.RemitaHandler",
        "Stripe": "ecclesia.utils.gateways.stripe.StripeHandler",
        "Squad": "ecclesia.utils.gateways.squad.SquadHandler",
        "M-Pesa": "ecclesia.utils.gateways.mpesa.MpesaHandler",
    }
    path = handlers.get(provider)
    if not path:
        frappe.throw(f"No handler implemented for provider: {provider}")

    module_path, class_name = path.rsplit(".", 1)
    import importlib
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    return cls(settings)