import frappe
import requests
from frappe.utils import flt, today

API_URL = "https://v6.exchangerate-api.com/v6/{key}/latest/{base}"


def sync_exchange_rates():
    """Daily: pull rates per company currency and upsert Currency Exchange records."""
    key = frappe.conf.get("exchangerate_api_key")
    if not key:
        frappe.log_error("exchangerate_api_key missing in site_config", "Exchange Rate Sync")
        return

    bases = set(frappe.get_all("Company", pluck="default_currency"))
    enabled = set(frappe.get_all("Currency", filters={"enabled": 1}, pluck="name"))

    for base in filter(None, bases):
        try:
            resp = requests.get(API_URL.format(key=key, base=base), timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            frappe.log_error(frappe.get_traceback(), f"Exchange Rate Sync: {base}")
            continue

        if data.get("result") != "success":
            frappe.log_error(str(data), f"Exchange Rate Sync: {base}")
            continue

        rates = data["conversion_rates"]  # units of X per 1 base

        for cur in enabled:
            if cur == base or not rates.get(cur):
                continue
            # ERPNext expects: 1 unit of from_currency = exchange_rate units of to_currency
            # Transaction currency -> company currency, so invert the API rate
            upsert_rate(from_currency=cur, to_currency=base, rate=1 / flt(rates[cur]))

    frappe.db.commit()


def upsert_rate(from_currency, to_currency, rate, date=None):
    date = date or today()
    name = frappe.db.exists(
        "Currency Exchange",
        {"date": date, "from_currency": from_currency, "to_currency": to_currency},
    )
    if name:
        frappe.db.set_value("Currency Exchange", name, "exchange_rate", rate)
    else:
        frappe.get_doc({
            "doctype": "Currency Exchange",
            "date": date,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "exchange_rate": rate,
            "for_buying": 1,
            "for_selling": 1,
        }).insert(ignore_permissions=True)


@frappe.whitelist()
def sync_now():
    frappe.only_for(["System Manager", "Accounts Manager"])
    sync_exchange_rates()
    return "ok"