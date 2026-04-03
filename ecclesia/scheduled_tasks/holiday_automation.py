# Copyright (c) 2024, Ecclesia and contributors
# For license information, please see license.txt

"""
Holiday Automation — Two scheduled tasks:

1. create_annual_holiday_list()
   → Runs on Jan 1 every year (cron: 0 0 1 1 *)
   → Creates Holiday List named by year (e.g. "2026")
   → Populates it with Nigerian public holidays via Nager.Date public API
   → Notifies HR Manager and HR User roles

2. send_holiday_greetings()
   → Runs daily (cron: 0 8 * * *)
   → Checks if today is a holiday in the current year's Holiday List
   → Sends personalized emails to Employees, Customers, Suppliers,
     Leads, Opportunities, and Contacts
   → Deduplicates by email address across all recipient types
"""

import frappe
from frappe import _
from frappe.utils import today, nowdate, getdate
import requests
import json
from datetime import date


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COUNTRY_CODE   = "NG"          # ISO 3166-1 alpha-2  (Nigeria)
COUNTRY_NAME   = "Nigeria"
NAGER_API_BASE = "https://date.nager.at/api/v3/PublicHolidays"


# ---------------------------------------------------------------------------
# 1. Create Annual Holiday List  (Jan 1 every year)
# ---------------------------------------------------------------------------

def create_annual_holiday_list():
	"""
	Scheduled entry point — triggered on January 1 each year.
	Creates a Holiday List for the current year and notifies HR roles.
	"""
	current_year = getdate(today()).year
	list_name    = str(current_year)

	# ── Guard: skip if already exists ──────────────────────────────────────
	if frappe.db.exists("Holiday List", list_name):
		frappe.logger().info(
			f"[Holiday Automation] Holiday List '{list_name}' already exists — skipping creation."
		)
		return

	# ── Fetch holidays from public API ─────────────────────────────────────
	holidays = _fetch_public_holidays(current_year, COUNTRY_CODE)

	if not holidays:
		frappe.log_error(
			title="[Holiday Automation] Failed to fetch holidays",
			message=f"Could not retrieve holidays for {COUNTRY_NAME} ({current_year}) from Nager.Date API.",
		)
		return

	# ── Create Holiday List document ───────────────────────────────────────
	holiday_list = frappe.new_doc("Holiday List")
	holiday_list.holiday_list_name = list_name
	holiday_list.from_date         = f"{current_year}-01-01"
	holiday_list.to_date           = f"{current_year}-12-31"
	holiday_list.country           = COUNTRY_NAME

	for h in holidays:
		holiday_list.append("holidays", {
			"holiday_date":        h["date"],
			"description":         h["name"],
			"weekly_off":          0,
		})

	holiday_list.insert(ignore_permissions=True)
	frappe.db.commit()

	frappe.logger().info(
		f"[Holiday Automation] Created Holiday List '{list_name}' "
		f"with {len(holidays)} holidays for {COUNTRY_NAME}."
	)

	# ── Notify HR roles ────────────────────────────────────────────────────
	_notify_hr_roles(list_name, holidays, current_year)


def _fetch_public_holidays(year: int, country_code: str) -> list:
	"""
	Calls the Nager.Date public API and returns a list of
	{ date, name, localName } dicts.
	"""
	url = f"{NAGER_API_BASE}/{year}/{country_code}"

	try:
		response = requests.get(url, timeout=10)
		response.raise_for_status()
		data = response.json()

		return [
			{
				"date":      item["date"],          # "YYYY-MM-DD"
				"name":      item["localName"],     # local language name
				"global_name": item["name"],        # English name
			}
			for item in data
		]

	except Exception as e:
		frappe.log_error(
			title="[Holiday Automation] API Error",
			message=str(e),
		)
		return []


def _notify_hr_roles(list_name: str, holidays: list, year: int):
	"""
	Sends an in-app + email notification to all users with
	HR Manager or HR User roles.
	"""
	hr_roles = ["HR Manager", "HR User"]

	hr_users = frappe.db.sql("""
		SELECT DISTINCT
			u.name,
			u.full_name,
			u.email
		FROM `tabUser`       u
		JOIN `tabHas Role`   r ON r.parent = u.name
		WHERE r.role        IN %(roles)s
		  AND u.enabled      = 1
		  AND u.name        != 'Administrator'
	""", {"roles": hr_roles}, as_dict=True)

	if not hr_users:
		return

	holiday_rows = "".join(
		f"<tr>"
		f"<td style='padding:6px 12px;border-bottom:1px solid #f0f0f0'>{h['date']}</td>"
		f"<td style='padding:6px 12px;border-bottom:1px solid #f0f0f0'>{h['name']}</td>"
		f"</tr>"
		for h in holidays
	)

	subject = f"✅ Holiday List {list_name} Created — {COUNTRY_NAME}"

	message = f"""
	<div style="font-family:Arial,sans-serif;max-width:640px;margin:0 auto;">
	  <div style="background:#1a4a8a;padding:28px 32px;border-radius:8px 8px 0 0;">
	    <h2 style="color:#fff;margin:0;font-size:22px;">🗓️ {year} Holiday List Ready</h2>
	    <p style="color:#b8d4f5;margin:6px 0 0;">Ecclesia · Human Resources</p>
	  </div>

	  <div style="background:#fff;padding:28px 32px;border:1px solid #e4e9f0;border-top:none;border-radius:0 0 8px 8px;">
	    <p style="color:#333;font-size:15px;">
	      The <strong>{year}</strong> Holiday List has been automatically created and populated
	      with <strong>{len(holidays)} public holidays</strong> for <strong>{COUNTRY_NAME}</strong>.
	    </p>

	    <table style="width:100%;border-collapse:collapse;margin:20px 0;font-size:14px;">
	      <thead>
	        <tr style="background:#f4f7fb;">
	          <th style="padding:10px 12px;text-align:left;color:#1a4a8a;font-weight:600;">Date</th>
	          <th style="padding:10px 12px;text-align:left;color:#1a4a8a;font-weight:600;">Holiday</th>
	        </tr>
	      </thead>
	      <tbody>
	        {holiday_rows}
	      </tbody>
	    </table>

	    <p style="color:#666;font-size:13px;margin-top:20px;">
	      Please review the list and assign it to the relevant employee groups.
	      <br>You can view it in <strong>Human Resources → Holiday List → {list_name}</strong>.
	    </p>
	  </div>
	</div>
	"""

	for user in hr_users:
		# In-app notification
		frappe.get_doc({
			"doctype":   "Notification Log",
			"subject":   subject,
			"for_user":  user["name"],
			"type":      "Alert",
			"document_type": "Holiday List",
			"document_name": list_name,
			"from_user": "Administrator",
		}).insert(ignore_permissions=True)

		# Email notification
		frappe.sendmail(
			recipients=[user["email"]],
			subject=subject,
			message=message,
			now=True,
		)

	frappe.db.commit()
	frappe.logger().info(
		f"[Holiday Automation] Notified {len(hr_users)} HR users about Holiday List '{list_name}'."
	)


# ---------------------------------------------------------------------------
# 2. Send Holiday Greetings  (Daily at 08:00)
# ---------------------------------------------------------------------------

def send_holiday_greetings():
	"""
	Scheduled entry point — runs daily.
	If today is a holiday in the current year's Holiday List,
	sends personalized greetings to all relevant parties.
	"""
	current_year = getdate(today()).year
	list_name    = str(current_year)
	today_date   = today()  # "YYYY-MM-DD"

	if not frappe.db.exists("Holiday List", list_name):
		return

	# ── Check if today is a holiday ────────────────────────────────────────
	holiday = frappe.db.get_value(
		"Holiday",
		{"parent": list_name, "holiday_date": today_date},
		["holiday_date", "description"],
		as_dict=True,
	)

	if not holiday:
		return

	holiday_name = holiday["description"]

	frappe.logger().info(
		f"[Holiday Automation] Today ({today_date}) is '{holiday_name}'. Sending greetings…"
	)

	sent_emails = set()  # deduplication bucket

	# ── Collect and send per recipient type ────────────────────────────────
	_send_to_employees(holiday_name, today_date, sent_emails)
	_send_to_customers(holiday_name, today_date, sent_emails)
	_send_to_suppliers(holiday_name, today_date, sent_emails)
	_send_to_leads(holiday_name, today_date, sent_emails)
	_send_to_opportunities(holiday_name, today_date, sent_emails)
	_send_to_contacts(holiday_name, today_date, sent_emails)

	frappe.logger().info(
		f"[Holiday Automation] Greetings sent to {len(sent_emails)} unique recipients."
	)


# ---------------------------------------------------------------------------
# Recipient helpers
# ---------------------------------------------------------------------------

def _safe_send(email: str, subject: str, message: str, sent_emails: set):
	"""Sends an email only if the address has not been used in this run."""
	email = (email or "").strip().lower()
	if not email or email in sent_emails:
		return
	try:
		frappe.sendmail(recipients=[email], subject=subject, message=message, now=True)
		sent_emails.add(email)
	except Exception as e:
		frappe.log_error(
			title=f"[Holiday Automation] Failed to send to {email}",
			message=str(e),
		)


def _send_to_employees(holiday_name: str, holiday_date: str, sent_emails: set):
	employees = frappe.db.get_all(
		"Employee",
		filters={"status": "Active"},
		fields=["name", "employee_name", "company_email", "personal_email"],
	)

	for emp in employees:
		email = emp.company_email or emp.personal_email
		if not email:
			continue

		subject = f"🎉 Happy {holiday_name}!"
		message = _template_employee(emp.employee_name, holiday_name, holiday_date)
		_safe_send(email, subject, message, sent_emails)


def _send_to_customers(holiday_name: str, holiday_date: str, sent_emails: set):
	customers = frappe.db.get_all(
		"Contact",
		filters={"status": "Open"},
		fields=["name", "first_name", "last_name", "email_id"],
	)

	# Also pull directly from Customer where email_id is set
	customer_docs = frappe.db.sql("""
		SELECT name, customer_name, email_id
		FROM `tabCustomer`
		WHERE disabled = 0
		  AND email_id IS NOT NULL
		  AND email_id != ''
	""", as_dict=True)

	for c in customer_docs:
		subject = f"Season's Greetings from Ecclesia — {holiday_name}"
		message = _template_customer(c.customer_name, holiday_name, holiday_date)
		_safe_send(c.email_id, subject, message, sent_emails)


def _send_to_suppliers(holiday_name: str, holiday_date: str, sent_emails: set):
	suppliers = frappe.db.sql("""
		SELECT name, supplier_name, email_id
		FROM `tabSupplier`
		WHERE disabled = 0
		  AND email_id IS NOT NULL
		  AND email_id != ''
	""", as_dict=True)

	for s in suppliers:
		subject = f"Warm Wishes — {holiday_name} | Ecclesia"
		message = _template_supplier(s.supplier_name, holiday_name, holiday_date)
		_safe_send(s.email_id, subject, message, sent_emails)


def _send_to_leads(holiday_name: str, holiday_date: str, sent_emails: set):
	leads = frappe.db.get_all(
		"Lead",
		filters={"status": ["not in", ["Converted", "Do Not Contact"]]},
		fields=["name", "lead_name", "email_id"],
	)

	for lead in leads:
		if not lead.email_id:
			continue
		subject = f"Happy {holiday_name} from Ecclesia 🌟"
		message = _template_lead(lead.lead_name, holiday_name, holiday_date)
		_safe_send(lead.email_id, subject, message, sent_emails)


def _send_to_opportunities(holiday_name: str, holiday_date: str, sent_emails: set):
	opps = frappe.db.sql("""
		SELECT o.name, o.contact_email, o.customer_name
		FROM `tabOpportunity` o
		WHERE o.status NOT IN ('Closed', 'Lost')
		  AND o.contact_email IS NOT NULL
		  AND o.contact_email != ''
	""", as_dict=True)

	for opp in opps:
		subject = f"Happy {holiday_name} — Wishing You Success 🚀"
		message = _template_opportunity(opp.customer_name, holiday_name, holiday_date)
		_safe_send(opp.contact_email, subject, message, sent_emails)


def _send_to_contacts(holiday_name: str, holiday_date: str, sent_emails: set):
	contacts = frappe.db.sql("""
		SELECT name, first_name, last_name, email_id
		FROM `tabContact`
		WHERE email_id IS NOT NULL
		  AND email_id != ''
	""", as_dict=True)

	for c in contacts:
		full_name = f"{c.first_name or ''} {c.last_name or ''}".strip() or "Friend"
		subject   = f"Happy {holiday_name}! 🎊"
		message   = _template_contact(full_name, holiday_name, holiday_date)
		_safe_send(c.email_id, subject, message, sent_emails)


# ---------------------------------------------------------------------------
# Email Templates
# ---------------------------------------------------------------------------

def _base_wrapper(content: str, footer_note: str = "") -> str:
	"""Wraps content in a consistent branded shell."""
	return f"""
<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#f9fafb;padding:24px;">
  <div style="background:#1a4a8a;padding:20px 32px;border-radius:10px 10px 0 0;text-align:center;">
    <span style="color:#fff;font-size:26px;font-weight:700;letter-spacing:1px;">ECCLESIA</span>
  </div>
  <div style="background:#fff;padding:32px;border:1px solid #e4e9f0;border-top:none;border-radius:0 0 10px 10px;">
    {content}
    <hr style="border:none;border-top:1px solid #f0f0f0;margin:28px 0 16px;">
    <p style="color:#aaa;font-size:11px;text-align:center;margin:0;">
      {footer_note or "Ecclesia · Sent automatically · Please do not reply to this email."}
    </p>
  </div>
</div>
"""


def _template_employee(name: str, holiday: str, date_str: str) -> str:
	content = f"""
    <p style="font-size:28px;text-align:center;margin:0 0 8px;">🎉</p>
    <h2 style="text-align:center;color:#1a4a8a;margin:0 0 20px;">Happy {holiday}!</h2>
    <p style="color:#333;font-size:15px;line-height:1.7;">Dear <strong>{name}</strong>,</p>
    <p style="color:#444;font-size:15px;line-height:1.7;">
      On behalf of everyone at <strong>Ecclesia</strong>, we wish you and your loved ones
      a joyful and restful <strong>{holiday}</strong>.
    </p>
    <p style="color:#444;font-size:15px;line-height:1.7;">
      Your dedication and hard work make this organisation great.
      Today, take a well-deserved break — you have earned it! 🌟
    </p>
    <p style="color:#444;font-size:15px;line-height:1.7;">
      Warm regards,<br>
      <strong>The Ecclesia Leadership Team</strong>
    </p>
	"""
	return _base_wrapper(content, "This message was sent to all Ecclesia employees.")


def _template_customer(name: str, holiday: str, date_str: str) -> str:
	content = f"""
    <p style="font-size:28px;text-align:center;margin:0 0 8px;">🏅</p>
    <h2 style="text-align:center;color:#1a4a8a;margin:0 0 20px;">Season's Greetings</h2>
    <p style="color:#333;font-size:15px;line-height:1.7;">Dear <strong>{name}</strong>,</p>
    <p style="color:#444;font-size:15px;line-height:1.7;">
      As we celebrate <strong>{holiday}</strong>, we want to take a moment to express
      our sincere gratitude for your continued trust and partnership with <strong>Ecclesia</strong>.
    </p>
    <p style="color:#444;font-size:15px;line-height:1.7;">
      You are the reason we strive for excellence every day.
      We look forward to serving you even better in the days ahead.
    </p>
    <p style="color:#444;font-size:15px;line-height:1.7;">
      With appreciation,<br>
      <strong>The Ecclesia Team</strong>
    </p>
	"""
	return _base_wrapper(content, "You are receiving this as a valued Ecclesia customer.")


def _template_supplier(name: str, holiday: str, date_str: str) -> str:
	content = f"""
    <p style="font-size:28px;text-align:center;margin:0 0 8px;">🤝</p>
    <h2 style="text-align:center;color:#1a4a8a;margin:0 0 20px;">Warm Wishes on {holiday}</h2>
    <p style="color:#333;font-size:15px;line-height:1.7;">Dear <strong>{name}</strong>,</p>
    <p style="color:#444;font-size:15px;line-height:1.7;">
      On this occasion of <strong>{holiday}</strong>, we extend our warmest greetings
      to you and your entire team.
    </p>
    <p style="color:#444;font-size:15px;line-height:1.7;">
      Our partnership has been invaluable to our operations, and we deeply appreciate
      the reliability and quality you bring to our work together.
      Here's to continued success and collaboration!
    </p>
    <p style="color:#444;font-size:15px;line-height:1.7;">
      Kind regards,<br>
      <strong>Procurement · Ecclesia</strong>
    </p>
	"""
	return _base_wrapper(content, "You are receiving this as a valued Ecclesia supplier.")


def _template_lead(name: str, holiday: str, date_str: str) -> str:
	content = f"""
    <p style="font-size:28px;text-align:center;margin:0 0 8px;">🌟</p>
    <h2 style="text-align:center;color:#1a4a8a;margin:0 0 20px;">Happy {holiday}!</h2>
    <p style="color:#333;font-size:15px;line-height:1.7;">Hi <strong>{name}</strong>,</p>
    <p style="color:#444;font-size:15px;line-height:1.7;">
      The whole team at <strong>Ecclesia</strong> wishes you a wonderful <strong>{holiday}</strong>!
    </p>
    <p style="color:#444;font-size:15px;line-height:1.7;">
      We hope this day brings you joy, rest, and a fresh sense of inspiration.
      When you are ready to explore how Ecclesia can support your goals, we would love to connect.
    </p>
    <p style="color:#444;font-size:15px;line-height:1.7;">
      Cheers,<br>
      <strong>The Ecclesia Sales Team</strong>
    </p>
	"""
	return _base_wrapper(content, "You are on our outreach list. To unsubscribe, reply with 'Unsubscribe'.")


def _template_opportunity(name: str, holiday: str, date_str: str) -> str:
	content = f"""
    <p style="font-size:28px;text-align:center;margin:0 0 8px;">🚀</p>
    <h2 style="text-align:center;color:#1a4a8a;margin:0 0 20px;">Wishing You a Successful {holiday}</h2>
    <p style="color:#333;font-size:15px;line-height:1.7;">Dear <strong>{name}</strong>,</p>
    <p style="color:#444;font-size:15px;line-height:1.7;">
      As we mark <strong>{holiday}</strong> today, we at <strong>Ecclesia</strong> want to
      take a brief pause from business to simply wish you and your team a truly wonderful day.
    </p>
    <p style="color:#444;font-size:15px;line-height:1.7;">
      We are excited about what we can build together and look forward to
      making great things happen. Enjoy the celebration!
    </p>
    <p style="color:#444;font-size:15px;line-height:1.7;">
      Warmly,<br>
      <strong>Ecclesia Business Development</strong>
    </p>
	"""
	return _base_wrapper(content, "You are receiving this as part of an active opportunity with Ecclesia.")


def _template_contact(name: str, holiday: str, date_str: str) -> str:
	content = f"""
    <p style="font-size:28px;text-align:center;margin:0 0 8px;">🎊</p>
    <h2 style="text-align:center;color:#1a4a8a;margin:0 0 20px;">Happy {holiday}, {name.split()[0]}!</h2>
    <p style="color:#333;font-size:15px;line-height:1.7;">Dear <strong>{name}</strong>,</p>
    <p style="color:#444;font-size:15px;line-height:1.7;">
      Wishing you a joyful and memorable <strong>{holiday}</strong> from all of us at
      <strong>Ecclesia</strong>!
    </p>
    <p style="color:#444;font-size:15px;line-height:1.7;">
      It's a privilege to have you in our circle. May this day be filled with
      warmth, laughter, and everything good.
    </p>
    <p style="color:#444;font-size:15px;line-height:1.7;">
      With warm wishes,<br>
      <strong>The Ecclesia Team</strong>
    </p>
	"""
	return _base_wrapper(content, "You are receiving this because you are a contact in our system.")