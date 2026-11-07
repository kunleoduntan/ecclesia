"""
ecclesia.erequest/utils/amount_words.py
─────────────────────────────────────────────────────────────────────────────
Convert a numeric amount to English words (Nigerian currency aware).
"""
from frappe.utils import money_in_words


def amount_to_words(amount: float, currency: str = "NGN") -> str:
    """
    Wrap Frappe's built-in money_in_words for the eRequest context.
    Returns e.g. 'One Hundred and Fifty Thousand Naira Only'
    """
    try:
        words = money_in_words(amount, currency)
        return words
    except Exception:
        return _manual_words(amount, currency)


def _manual_words(amount: float, currency: str) -> str:
    """Fallback pure-Python implementation."""
    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven",
            "Eight", "Nine", "Ten", "Eleven", "Twelve", "Thirteen",
            "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty",
            "Sixty", "Seventy", "Eighty", "Ninety"]

    def _below_thousand(n):
        if n == 0:
            return ""
        elif n < 20:
            return ones[n]
        elif n < 100:
            return tens[n // 10] + (" " + ones[n % 10] if n % 10 else "")
        else:
            rem = _below_thousand(n % 100)
            return ones[n // 100] + " Hundred" + (" and " + rem if rem else "")

    def _convert(n):
        if n == 0:
            return "Zero"
        parts = []
        billions  = n // 1_000_000_000; n %= 1_000_000_000
        millions  = n // 1_000_000;     n %= 1_000_000
        thousands = n // 1_000;         n %= 1_000
        remainder = n
        if billions:  parts.append(_below_thousand(billions)  + " Billion")
        if millions:  parts.append(_below_thousand(millions)  + " Million")
        if thousands: parts.append(_below_thousand(thousands) + " Thousand")
        if remainder: parts.append(_below_thousand(remainder))
        return " ".join(parts)

    whole = int(amount)
    kobo  = round((amount - whole) * 100)
    curr_map = {"NGN": ("Naira", "Kobo"), "USD": ("Dollar", "Cent"), "GBP": ("Pound", "Penny")}
    major, minor = curr_map.get(currency, (currency, "Cents"))

    result = _convert(whole) + " " + major
    if kobo:
        result += " and " + _convert(kobo) + " " + minor
    return result + " Only"



"""
ecclesia.erequest/utils/cleanup.py
Purge expired OTP cache entries (belt-and-suspenders — Redis TTL handles most).
"""
import frappe


def purge_expired_otps():
    """
    Frappe Redis cache TTLs handle expiry automatically.
    This is a no-op safety net kept for visibility in scheduler logs.
    """
    frappe.logger().debug("eRequest: OTP cleanup tick (Redis TTL handles expiry).")


"""
ecclesia.erequest/utils/reminders.py
Daily reminder emails for pending approvals.
"""
import frappe
from frappe.utils import add_days, today, get_url


def send_pending_approval_reminders():
    """Runs daily. Sends reminder to approvers for requests pending > 2 days."""
    cutoff = add_days(today(), -2)
    pending_states = [
        ("Pending Manager Approval", "eRequest Manager"),
        ("Pending Finance Approval",  "eRequest Finance"),
        ("Pending Final Approval",    "eRequest Admin"),
    ]
    for state, role in pending_states:
        old_requests = frappe.get_all(
            "eRequest",
            filters={"workflow_state": state, "modified": ["<", cutoff]},
            fields=["name", "title", "requested_by", "priority", "request_date"],
        )
        if not old_requests:
            continue
        approvers = [r.parent for r in frappe.get_all(
            "Has Role", filters={"role": role, "parenttype": "User"}, fields=["parent"],
        )]
        if not approvers:
            continue
        rows_html = "".join(
            f"<tr><td>{r.name}</td><td>{r.title}</td><td>{r.priority}</td>"
            f"<td>{r.request_date}</td>"
            f"<td><a href='{get_url()}/app/erequest/{r.name}'>Open</a></td></tr>"
            for r in old_requests
        )
        frappe.sendmail(
            recipients=approvers,
            subject=f"[eRequest] Reminder: {len(old_requests)} Request(s) Awaiting Approval",
            message=f"""<p>The following requests have been waiting for your approval for more than 2 days:</p>
            <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%">
              <thead style="background:#f3f4f6"><tr><th>Ref</th><th>Title</th><th>Priority</th><th>Date</th><th>Link</th></tr></thead>
              <tbody>{rows_html}</tbody>
            </table>
            <p>Please review and take action at your earliest convenience.</p>""",
        )
