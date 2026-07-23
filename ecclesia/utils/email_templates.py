# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/utils/email_templates.py
"""
Shared branded email template helpers for the Ecclesia Secretarial Module.

Extracted from agm_api.py so every component (AGM, Meeting, Board Resolution,
Legal Register, Correspondence, ...) shares one consistent look instead of
re-implementing header/footer/table markup per module.
"""

import frappe


def email_header(title, subtitle=""):
	return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#F0F4F8;font-family:'Segoe UI',Arial,sans-serif">
<div style="max-width:620px;margin:32px auto;background:#ffffff;border-radius:12px;
            overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.10)">

  <div style="background:linear-gradient(135deg,#1E3A5F 0%,#2563EB 100%);padding:32px 40px;text-align:center">
    <div style="display:inline-block;background:rgba(255,255,255,0.15);
                border-radius:50%;width:56px;height:56px;line-height:56px;
                font-size:28px;margin-bottom:12px">🏛️</div>
    <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:700;letter-spacing:0.5px">
        {title}
    </h1>
    {"" if not subtitle else f'<p style="margin:6px 0 0;color:#93C5FD;font-size:13px">{subtitle}</p>'}
  </div>

  <div style="padding:32px 40px">
"""


def email_footer():
	return """
  </div>

  <div style="background:#F8FAFC;border-top:1px solid #E2E8F0;padding:20px 40px;text-align:center">
    <p style="margin:0;font-size:11px;color:#94A3B8;line-height:1.7">
        This communication is issued under the Company's Articles of Association and
        applicable corporate governance policy.<br>
        If you believe you received this in error, please contact the Company Secretary.<br>
        <span style="color:#CBD5E1">Powered by Ecclesia ERP &bull; Value Impacts Consulting</span>
    </p>
  </div>

</div>
</body>
</html>
"""


def info_row(label, value, highlight=False):
	bg = "#EFF6FF" if highlight else "#F8FAFC"
	return f"""
    <tr>
        <td style="padding:10px 14px;border-bottom:1px solid #E2E8F0;
                   color:#64748B;font-size:13px;font-weight:600;width:160px;
                   background:{bg}">{label}</td>
        <td style="padding:10px 14px;border-bottom:1px solid #E2E8F0;
                   color:#1E293B;font-size:13px;background:{bg}"><b>{value}</b></td>
    </tr>"""


def status_badge(is_good, good_text, bad_text):
	if is_good:
		return (f'<span style="background:#D1FAE5;color:#059669;padding:4px 12px;'
				f'border-radius:20px;font-size:12px;font-weight:700">✅ {good_text}</span>')
	return (f'<span style="background:#FEE2E2;color:#DC2626;padding:4px 12px;'
			f'border-radius:20px;font-size:12px;font-weight:700">⚠️ {bad_text}</span>')


def cta_button(url, label, colour="#1E3A5F"):
	return f"""
    <div style="text-align:center;margin:24px 0">
        <a href="{url}"
           style="background:{colour};color:white;padding:12px 28px;border-radius:6px;
                  text-decoration:none;font-weight:700;font-size:14px">
            {label} →
        </a>
    </div>"""


def get_officer_email(employee):
	"""Resolve an Employee's best contact email (company, falling back to personal)."""
	if not employee:
		return None
	emp = frappe.db.get_value(
		"Employee", employee, ["company_email", "personal_email"], as_dict=True
	)
	if not emp:
		return None
	return emp.company_email or emp.personal_email or None


# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/utils/email_templates.py
"""
Shared branded email template helpers for the Ecclesia Secretarial Module.

Extracted from agm_api.py so every component (AGM, Meeting, Board Resolution,
Legal Register, Correspondence, ...) shares one consistent look instead of
re-implementing header/footer/table markup per module.
"""

import frappe


def email_header(title, subtitle=""):
	return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#F0F4F8;font-family:'Segoe UI',Arial,sans-serif">
<div style="max-width:620px;margin:32px auto;background:#ffffff;border-radius:12px;
            overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.10)">

  <div style="background:linear-gradient(135deg,#1E3A5F 0%,#2563EB 100%);padding:32px 40px;text-align:center">
    <div style="display:inline-block;background:rgba(255,255,255,0.15);
                border-radius:50%;width:56px;height:56px;line-height:56px;
                font-size:28px;margin-bottom:12px">🏛️</div>
    <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:700;letter-spacing:0.5px">
        {title}
    </h1>
    {"" if not subtitle else f'<p style="margin:6px 0 0;color:#93C5FD;font-size:13px">{subtitle}</p>'}
  </div>

  <div style="padding:32px 40px">
"""


def email_footer():
	return """
  </div>

  <div style="background:#F8FAFC;border-top:1px solid #E2E8F0;padding:20px 40px;text-align:center">
    <p style="margin:0;font-size:11px;color:#94A3B8;line-height:1.7">
        This communication is issued under the Company's Articles of Association and
        applicable corporate governance policy.<br>
        If you believe you received this in error, please contact the Company Secretary.<br>
        <span style="color:#CBD5E1">Powered by Ecclesia ERP &bull; Value Impacts Consulting</span>
    </p>
  </div>

</div>
</body>
</html>
"""


def info_row(label, value, highlight=False):
	bg = "#EFF6FF" if highlight else "#F8FAFC"
	return f"""
    <tr>
        <td style="padding:10px 14px;border-bottom:1px solid #E2E8F0;
                   color:#64748B;font-size:13px;font-weight:600;width:160px;
                   background:{bg}">{label}</td>
        <td style="padding:10px 14px;border-bottom:1px solid #E2E8F0;
                   color:#1E293B;font-size:13px;background:{bg}"><b>{value}</b></td>
    </tr>"""


def status_badge(is_good, good_text, bad_text):
	if is_good:
		return (f'<span style="background:#D1FAE5;color:#059669;padding:4px 12px;'
				f'border-radius:20px;font-size:12px;font-weight:700">✅ {good_text}</span>')
	return (f'<span style="background:#FEE2E2;color:#DC2626;padding:4px 12px;'
			f'border-radius:20px;font-size:12px;font-weight:700">⚠️ {bad_text}</span>')


def cta_button(url, label, colour="#1E3A5F"):
	return f"""
    <div style="text-align:center;margin:24px 0">
        <a href="{url}"
           style="background:{colour};color:white;padding:12px 28px;border-radius:6px;
                  text-decoration:none;font-weight:700;font-size:14px">
            {label} →
        </a>
    </div>"""


def get_officer_email(employee):
	"""Resolve an Employee's best contact email (company, falling back to personal)."""
	if not employee:
		return None
	emp = frappe.db.get_value(
		"Employee", employee, ["company_email", "personal_email"], as_dict=True
	)
	if not emp:
		return None
	return emp.company_email or emp.personal_email or None



# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/utils/email_templates.py
"""
Shared branded email template helpers for the Ecclesia Secretarial Module.

Extracted from agm_api.py so every component (AGM, Meeting, Board Resolution,
Legal Register, Correspondence, ...) shares one consistent look instead of
re-implementing header/footer/table markup per module.
"""

import frappe


def email_header(title, subtitle=""):
	return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#F0F4F8;font-family:'Segoe UI',Arial,sans-serif">
<div style="max-width:620px;margin:32px auto;background:#ffffff;border-radius:12px;
            overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.10)">

  <div style="background:linear-gradient(135deg,#1E3A5F 0%,#2563EB 100%);padding:32px 40px;text-align:center">
    <div style="display:inline-block;background:rgba(255,255,255,0.15);
                border-radius:50%;width:56px;height:56px;line-height:56px;
                font-size:28px;margin-bottom:12px">🏛️</div>
    <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:700;letter-spacing:0.5px">
        {title}
    </h1>
    {"" if not subtitle else f'<p style="margin:6px 0 0;color:#93C5FD;font-size:13px">{subtitle}</p>'}
  </div>

  <div style="padding:32px 40px">
"""


def email_footer():
	return """
  </div>

  <div style="background:#F8FAFC;border-top:1px solid #E2E8F0;padding:20px 40px;text-align:center">
    <p style="margin:0;font-size:11px;color:#94A3B8;line-height:1.7">
        This communication is issued under the Company's Articles of Association and
        applicable corporate governance policy.<br>
        If you believe you received this in error, please contact the Company Secretary.<br>
        <span style="color:#CBD5E1">Powered by Ecclesia ERP &bull; Value Impacts Consulting</span>
    </p>
  </div>

</div>
</body>
</html>
"""


def info_row(label, value, highlight=False):
	bg = "#EFF6FF" if highlight else "#F8FAFC"
	return f"""
    <tr>
        <td style="padding:10px 14px;border-bottom:1px solid #E2E8F0;
                   color:#64748B;font-size:13px;font-weight:600;width:160px;
                   background:{bg}">{label}</td>
        <td style="padding:10px 14px;border-bottom:1px solid #E2E8F0;
                   color:#1E293B;font-size:13px;background:{bg}"><b>{value}</b></td>
    </tr>"""


def status_badge(is_good, good_text, bad_text):
	if is_good:
		return (f'<span style="background:#D1FAE5;color:#059669;padding:4px 12px;'
				f'border-radius:20px;font-size:12px;font-weight:700">✅ {good_text}</span>')
	return (f'<span style="background:#FEE2E2;color:#DC2626;padding:4px 12px;'
			f'border-radius:20px;font-size:12px;font-weight:700">⚠️ {bad_text}</span>')


def cta_button(url, label, colour="#1E3A5F"):
	return f"""
    <div style="text-align:center;margin:24px 0">
        <a href="{url}"
           style="background:{colour};color:white;padding:12px 28px;border-radius:6px;
                  text-decoration:none;font-weight:700;font-size:14px">
            {label} →
        </a>
    </div>"""


def get_officer_email(employee):
	"""Resolve an Employee's best contact email (company, falling back to personal)."""
	if not employee:
		return None
	emp = frappe.db.get_value(
		"Employee", employee, ["company_email", "personal_email"], as_dict=True
	)
	if not emp:
		return None
	return emp.company_email or emp.personal_email or None




# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/utils/email_templates.py
"""
Shared branded email template helpers for the Ecclesia Secretarial Module.

Extracted from agm_api.py so every component (AGM, Meeting, Board Resolution,
Legal Register, Correspondence, ...) shares one consistent look instead of
re-implementing header/footer/table markup per module.
"""

import frappe


def email_header(title, subtitle=""):
	return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#F0F4F8;font-family:'Segoe UI',Arial,sans-serif">
<div style="max-width:620px;margin:32px auto;background:#ffffff;border-radius:12px;
            overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.10)">

  <div style="background:linear-gradient(135deg,#1E3A5F 0%,#2563EB 100%);padding:32px 40px;text-align:center">
    <div style="display:inline-block;background:rgba(255,255,255,0.15);
                border-radius:50%;width:56px;height:56px;line-height:56px;
                font-size:28px;margin-bottom:12px">🏛️</div>
    <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:700;letter-spacing:0.5px">
        {title}
    </h1>
    {"" if not subtitle else f'<p style="margin:6px 0 0;color:#93C5FD;font-size:13px">{subtitle}</p>'}
  </div>

  <div style="padding:32px 40px">
"""


def email_footer():
	return """
  </div>

  <div style="background:#F8FAFC;border-top:1px solid #E2E8F0;padding:20px 40px;text-align:center">
    <p style="margin:0;font-size:11px;color:#94A3B8;line-height:1.7">
        This communication is issued under the Company's Articles of Association and
        applicable corporate governance policy.<br>
        If you believe you received this in error, please contact the Company Secretary.<br>
        <span style="color:#CBD5E1">Powered by Ecclesia ERP &bull; Value Impacts Consulting</span>
    </p>
  </div>

</div>
</body>
</html>
"""


def info_row(label, value, highlight=False):
	bg = "#EFF6FF" if highlight else "#F8FAFC"
	return f"""
    <tr>
        <td style="padding:10px 14px;border-bottom:1px solid #E2E8F0;
                   color:#64748B;font-size:13px;font-weight:600;width:160px;
                   background:{bg}">{label}</td>
        <td style="padding:10px 14px;border-bottom:1px solid #E2E8F0;
                   color:#1E293B;font-size:13px;background:{bg}"><b>{value}</b></td>
    </tr>"""


def status_badge(is_good, good_text, bad_text):
	if is_good:
		return (f'<span style="background:#D1FAE5;color:#059669;padding:4px 12px;'
				f'border-radius:20px;font-size:12px;font-weight:700">✅ {good_text}</span>')
	return (f'<span style="background:#FEE2E2;color:#DC2626;padding:4px 12px;'
			f'border-radius:20px;font-size:12px;font-weight:700">⚠️ {bad_text}</span>')


def cta_button(url, label, colour="#1E3A5F"):
	return f"""
    <div style="text-align:center;margin:24px 0">
        <a href="{url}"
           style="background:{colour};color:white;padding:12px 28px;border-radius:6px;
                  text-decoration:none;font-weight:700;font-size:14px">
            {label} →
        </a>
    </div>"""


def get_officer_email(employee):
	"""Resolve an Employee's best contact email (company, falling back to personal)."""
	if not employee:
		return None
	emp = frappe.db.get_value(
		"Employee", employee, ["company_email", "personal_email"], as_dict=True
	)
	if not emp:
		return None
	return emp.company_email or emp.personal_email or None




# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/utils/email_templates.py
"""
Shared branded email template helpers for the Ecclesia Secretarial Module.

Extracted from agm_api.py so every component (AGM, Meeting, Board Resolution,
Legal Register, Correspondence, ...) shares one consistent look instead of
re-implementing header/footer/table markup per module.
"""

import frappe


def email_header(title, subtitle=""):
	return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#F0F4F8;font-family:'Segoe UI',Arial,sans-serif">
<div style="max-width:620px;margin:32px auto;background:#ffffff;border-radius:12px;
            overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.10)">

  <div style="background:linear-gradient(135deg,#1E3A5F 0%,#2563EB 100%);padding:32px 40px;text-align:center">
    <div style="display:inline-block;background:rgba(255,255,255,0.15);
                border-radius:50%;width:56px;height:56px;line-height:56px;
                font-size:28px;margin-bottom:12px">🏛️</div>
    <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:700;letter-spacing:0.5px">
        {title}
    </h1>
    {"" if not subtitle else f'<p style="margin:6px 0 0;color:#93C5FD;font-size:13px">{subtitle}</p>'}
  </div>

  <div style="padding:32px 40px">
"""


def email_footer():
	return """
  </div>

  <div style="background:#F8FAFC;border-top:1px solid #E2E8F0;padding:20px 40px;text-align:center">
    <p style="margin:0;font-size:11px;color:#94A3B8;line-height:1.7">
        This communication is issued under the Company's Articles of Association and
        applicable corporate governance policy.<br>
        If you believe you received this in error, please contact the Company Secretary.<br>
        <span style="color:#CBD5E1">Powered by Ecclesia ERP &bull; Value Impacts Consulting</span>
    </p>
  </div>

</div>
</body>
</html>
"""


def info_row(label, value, highlight=False):
	bg = "#EFF6FF" if highlight else "#F8FAFC"
	return f"""
    <tr>
        <td style="padding:10px 14px;border-bottom:1px solid #E2E8F0;
                   color:#64748B;font-size:13px;font-weight:600;width:160px;
                   background:{bg}">{label}</td>
        <td style="padding:10px 14px;border-bottom:1px solid #E2E8F0;
                   color:#1E293B;font-size:13px;background:{bg}"><b>{value}</b></td>
    </tr>"""


def status_badge(is_good, good_text, bad_text):
	if is_good:
		return (f'<span style="background:#D1FAE5;color:#059669;padding:4px 12px;'
				f'border-radius:20px;font-size:12px;font-weight:700">✅ {good_text}</span>')
	return (f'<span style="background:#FEE2E2;color:#DC2626;padding:4px 12px;'
			f'border-radius:20px;font-size:12px;font-weight:700">⚠️ {bad_text}</span>')


def cta_button(url, label, colour="#1E3A5F"):
	return f"""
    <div style="text-align:center;margin:24px 0">
        <a href="{url}"
           style="background:{colour};color:white;padding:12px 28px;border-radius:6px;
                  text-decoration:none;font-weight:700;font-size:14px">
            {label} →
        </a>
    </div>"""


def get_officer_email(employee):
	"""Resolve an Employee's best contact email (company, falling back to personal)."""
	if not employee:
		return None
	emp = frappe.db.get_value(
		"Employee", employee, ["company_email", "personal_email"], as_dict=True
	)
	if not emp:
		return None
	return emp.company_email or emp.personal_email or None
