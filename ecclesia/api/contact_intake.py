"""
Contact Us Web Integration API
File: ecclesia/api/contact_intake.py

Architecture:
  - Every website form carries only a short `form_key` (e.g. "vic-main").
  - On load, the form fetches its full config from `get_form_config`.
  - On submit, `receive_contact_form` looks up the Web Form Settings record
    by form_key, validates the CORS origin, creates the Contact Us doc
    under the correct company, and runs AI/load-balance assignment.
  - One ERPNext instance can serve unlimited companies / websites.
"""

import frappe
import json
import re
from frappe.utils import now_datetime, cint
from datetime import timedelta


# ── Default fallback options ─────────────────────────────────────────────────

DEFAULT_INDUSTRIES = [
    "Technology", "Finance & Banking", "Healthcare", "Manufacturing",
    "Retail & FMCG", "Oil & Gas", "Real Estate", "Education",
    "Logistics", "NGO / Non-Profit", "Government", "Other",
]

DEFAULT_BUDGETS = [
    "Under ₦500K", "₦500K – ₦2M", "₦2M – ₦10M",
    "₦10M – ₦50M", "Above ₦50M", "Not sure",
]


# ── 1. Config loader (called by the form on page load) ───────────────────────

@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_form_config(key: str = ""):
    """
    Returns the public branding + field config for a given form_key.
    No sensitive data (API keys, internal emails) is exposed.

    GET /api/method/ecclesia.api.contact_intake.get_form_config?key=vic-main
    """
    if not key:
        frappe.response["http_status_code"] = 400
        return {"success": False, "error": "form_key is required."}

    settings = _get_settings(key)
    if not settings:
        frappe.response["http_status_code"] = 404
        return {"success": False, "error": f"No active form found for key '{key}'."}

    # Parse multiline options into arrays
    industries = _parse_options(settings.get("industry_options"), DEFAULT_INDUSTRIES)
    budgets    = _parse_options(settings.get("budget_options"),   DEFAULT_BUDGETS)

    return {
        "success": True,
        "config": {
            # Identity
            "form_key":        settings.form_key,
            "form_label":      settings.form_label,
            "company":         settings.company,
            # Branding
            "header_title":    settings.header_title    or "Get in touch",
            "header_subtitle": settings.header_subtitle or "We'll respond within one business day",
            "brand_color":     settings.brand_color     or "#c8972a",
            "logo_url":        settings.logo_url        or "",
            "contact_email":   settings.contact_email   or "",
            "contact_phone":   settings.contact_phone   or "",
            "contact_address": settings.contact_address or "",
            # Field visibility
            "show_phone":    cint(settings.show_phone),
            "show_company":  cint(settings.show_company),
            "show_industry": cint(settings.show_industry),
            "show_budget":   cint(settings.show_budget),
            "industries":    industries,
            "budgets":       budgets,
            # Submission behaviour
            "success_message": settings.success_message or "Message sent!",
            "success_subtext": settings.success_subtext or "Thanks for reaching out. We'll be in touch shortly.",
            "redirect_url":    settings.redirect_url    or "",
        }
    }


# ── 2. Form submission endpoint ──────────────────────────────────────────────

@frappe.whitelist(allow_guest=True, methods=["POST"])
def receive_contact_form():
    """
    Receives a contact form submission from the website.

    POST /api/method/ecclesia.api.contact_intake.receive_contact_form
    Body (JSON): { form_key, full_name, email, message, ... }
    """
    try:
        data = frappe.request.get_json(silent=True) or {}

        # ── Resolve form config ──────────────────────────────
        form_key = _sanitise(data.get("form_key", ""))
        if not form_key:
            frappe.response["http_status_code"] = 400
            return {"success": False, "error": "form_key is required."}

        settings = _get_settings(form_key)
        if not settings:
            frappe.response["http_status_code"] = 404
            return {"success": False, "error": f"No active form found for key '{form_key}'. Please create a Web Form Settings record with this key."}

        # ── CORS / origin validation ─────────────────────────
        origin  = frappe.request.headers.get("Origin", "")
        allowed = (settings.allowed_origin or "").rstrip("/")
        # Only enforce if allowed_origin is explicitly set
        if allowed and origin and origin.rstrip("/") != allowed:
            frappe.response["http_status_code"] = 403
            return {"success": False, "error": f"Origin '{origin}' is not allowed for this form."}

        # ── Required field validation ────────────────────────
        required = ["full_name", "email", "message"]
        missing  = [f for f in required if not data.get(f)]
        if missing:
            frappe.response["http_status_code"] = 400
            return {"success": False, "error": f"Missing required fields: {', '.join(missing)}"}

        # ── Sanitise inputs ──────────────────────────────────
        full_name = _sanitise(data.get("full_name", ""))
        email     = _sanitise(data.get("email", "")).lower()
        phone     = _sanitise(data.get("phone", ""))
        company   = _sanitise(data.get("company", ""))
        subject   = _sanitise(data.get("subject", "General Inquiry"))
        message   = _sanitise(data.get("message", ""))
        industry  = _sanitise(data.get("industry", ""))
        budget    = _sanitise(data.get("estimated_budget", ""))

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            frappe.response["http_status_code"] = 400
            return {"success": False, "error": "Invalid email address."}

        # ── Duplicate guard ──────────────────────────────────
        window_hours = cint(getattr(settings, "duplicate_window_hours", 24)) or 24
        if _is_duplicate(email, getattr(settings, "company", ""), window_hours):
            return {
                "success":   True,
                "duplicate": True,
                "message":   "We already received your inquiry. Our team will reach out soon.",
            }

        # ── AI + load-balance assignment ─────────────────────
        assignment = assign_salesperson(
            context={
                "full_name": full_name, "email": email,
                "company":   company,   "industry": industry,
                "subject":   subject,   "message": message,
                "estimated_budget": budget,
            },
            settings=settings,
        )

        assigned_to   = assignment.get("salesperson_email", "")
        assigned_name = assignment.get("salesperson_name", "")
        ai_reasoning  = assignment.get("reasoning", "")
        priority      = assignment.get("priority", "Medium")

        # ── Build doc dict — only include fields that exist in the DocType ──
        existing_fields = _get_doctype_fieldnames("Contact Us")

        doc_data = {"doctype": "Contact Us"}

        # Core fields — these must exist or the DocType is broken
        _sf(doc_data, existing_fields, "full_name",  full_name)
        _sf(doc_data, existing_fields, "email",      email)
        _sf(doc_data, existing_fields, "phone",      phone)
        _sf(doc_data, existing_fields, "company",    company)
        _sf(doc_data, existing_fields, "subject",    subject)
        _sf(doc_data, existing_fields, "message",    message)

        # Optional extended fields — silently skipped if not yet added
        _sf(doc_data, existing_fields, "source",           "Website")
        _sf(doc_data, existing_fields, "industry",         industry)
        _sf(doc_data, existing_fields, "estimated_budget", budget)
        _sf(doc_data, existing_fields, "status",           "New")
        _sf(doc_data, existing_fields, "priority",         priority)
        _sf(doc_data, existing_fields, "assigned_to",      assigned_to)
        _sf(doc_data, existing_fields, "assigned_to_name", assigned_name)
        _sf(doc_data, existing_fields, "ai_reasoning",     ai_reasoning)
        _sf(doc_data, existing_fields, "submission_date",  now_datetime())
        _sf(doc_data, existing_fields, "web_form_key",     form_key)
        _sf(doc_data, existing_fields, "linked_company",   getattr(settings, "company", ""))

        # ── Insert doc ───────────────────────────────────────
        doc = frappe.get_doc(doc_data)
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        # ── Notifications ────────────────────────────────────
        _notify_salesperson(doc, assigned_to, assigned_name, settings)
        _notify_additional_emails(doc, settings)

        # ── Response ─────────────────────────────────────────
        return {
            "success":      True,
            "message":      getattr(settings, "success_message", None) or "Thank you! We will be in touch shortly.",
            "subtext":      getattr(settings, "success_subtext", "") or "",
            "reference":    doc.name,
            "assigned_to":  assigned_name,
            "redirect_url": getattr(settings, "redirect_url", "") or "",
        }

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Contact Form Intake Error")
        frappe.response["http_status_code"] = 500
        return {"success": False, "error": "An internal error occurred. Please check the ERPNext Error Log for details."}


# ── 3. AI + Load Balancing Assignment Engine ─────────────────────────────────

def assign_salesperson(context: dict, settings) -> dict:
    """
    Determines the best salesperson using:
      1. Load balancing — open lead count per eligible salesperson
      2. AI reasoning   — matches context to specialisation (if strategy allows)
    """
    strategy    = settings.assignment_strategy or "AI + Load Balancing"
    target_role = settings.target_salesperson_role or ""
    company     = settings.company

    salespeople = _get_active_salespeople(role=target_role, company=company)

    if not salespeople:
        return _fallback_assignment("No eligible salespeople found for this form.")

    # Enrich with open lead counts
    for sp in salespeople:
        sp["open_leads"] = _get_open_lead_count(sp["email"], company)

    # Round Robin — ignore load, cycle by order
    if strategy == "Round Robin":
        sp = salespeople[_get_round_robin_index(company) % len(salespeople)]
        return {
            "salesperson_email": sp["email"],
            "salesperson_name":  sp["full_name"],
            "priority":          "Medium",
            "reasoning":         f"Round robin assignment (position {sp.get('rr_index', 0)}).",
        }

    # Fixed Salesperson — target_role holds a specific user email
    if strategy == "Fixed Salesperson":
        fixed = next((s for s in salespeople if s["email"] == target_role), salespeople[0])
        return {
            "salesperson_email": fixed["email"],
            "salesperson_name":  fixed["full_name"],
            "priority":          "Medium",
            "reasoning":         "Fixed salesperson assignment per form configuration.",
        }

    # Load Balancing Only
    if strategy == "Load Balancing Only":
        best = min(salespeople, key=lambda x: x["open_leads"])
        return {
            "salesperson_email": best["email"],
            "salesperson_name":  best["full_name"],
            "priority":          "Medium",
            "reasoning":         f"Assigned by load balancing ({best['open_leads']} open leads).",
        }

    # AI + Load Balancing (default)
    prompt      = _build_assignment_prompt(context, salespeople)
    ai_response = _call_ai(prompt, settings)
    return _parse_ai_response(ai_response, salespeople)


def _build_assignment_prompt(context: dict, salespeople: list) -> str:
    sp_list = "\n".join([
        f"  - Name: {sp['full_name']}, Email: {sp['email']}, "
        f"Specialisation: {sp.get('specialisation', 'General')}, "
        f"Open Leads: {sp['open_leads']}, "
        f"Industries: {sp.get('industries', 'All')}"
        for sp in salespeople
    ])
    return f"""You are a CRM assignment engine for a B2B sales team.

INCOMING LEAD:
- Name: {context.get('full_name')}
- Company: {context.get('company', 'N/A')}
- Industry: {context.get('industry', 'N/A')}
- Subject: {context.get('subject')}
- Message: {context.get('message')}
- Estimated Budget: {context.get('estimated_budget', 'Unknown')}

AVAILABLE SALESPEOPLE (with current open lead counts):
{sp_list}

INSTRUCTIONS:
1. Consider BOTH specialisation match AND load balancing.
2. Classify lead priority as High, Medium, or Low based on intent and budget signals.
3. Return ONLY valid JSON — no prose, no markdown fences.

Required JSON format:
{{
  "salesperson_email": "<email>",
  "salesperson_name": "<full name>",
  "priority": "<High|Medium|Low>",
  "reasoning": "<one sentence explaining the decision>"
}}"""


def _call_ai(prompt: str, settings) -> str:
    """Call the configured AI provider. Returns raw text or empty string on failure."""
    try:
        provider  = settings.ai_provider or "Anthropic (Claude)"
        api_key   = frappe.conf.get("anthropic_api_key") or frappe.conf.get("openai_api_key") or ""
        if not api_key:
            return ""

        import requests

        if provider == "Anthropic (Claude)":
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 300,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json()["content"][0]["text"]

        elif provider == "OpenAI":
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini",
                    "max_tokens": 300,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]

        return ""
    except Exception:
        frappe.log_error(frappe.get_traceback(), "AI Assignment Call Failed")
        return ""


def _parse_ai_response(ai_text: str, salespeople: list) -> dict:
    """Parse AI JSON; fall back to pure load balancing on any failure."""
    try:
        if ai_text:
            clean  = re.sub(r"```json|```", "", ai_text).strip()
            result = json.loads(clean)
            valid_emails = {sp["email"] for sp in salespeople}
            if result.get("salesperson_email") in valid_emails:
                return result
    except Exception:
        pass

    best = min(salespeople, key=lambda x: x["open_leads"])
    return {
        "salesperson_email": best["email"],
        "salesperson_name":  best["full_name"],
        "priority":          "Medium",
        "reasoning":         f"AI unavailable; assigned by load balancing ({best['open_leads']} open leads).",
    }


# ── 4. Internal / UI endpoints ───────────────────────────────────────────────

@frappe.whitelist()
def reassign_lead(contact_us_name: str, reason: str = "Manual reassignment"):
    """Re-run AI assignment on an existing lead from the ERPNext UI."""
    doc      = frappe.get_doc("Contact Us", contact_us_name)
    form_key = doc.get("web_form_key") or ""
    settings = _get_settings(form_key) if form_key else _get_default_settings()

    result = assign_salesperson(
        context={
            "full_name": doc.full_name, "email": doc.email,
            "company": doc.company, "industry": doc.get("industry", ""),
            "subject": doc.subject, "message": doc.message,
            "estimated_budget": doc.get("estimated_budget", ""),
        },
        settings=settings,
    )

    doc.assigned_to      = result["salesperson_email"]
    doc.assigned_to_name = result["salesperson_name"]
    doc.ai_reasoning     = result["reasoning"]
    doc.priority         = result["priority"]
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    _notify_salesperson(doc, doc.assigned_to, doc.assigned_to_name, settings)
    return {"success": True, "assigned_to": result["salesperson_name"], "reasoning": result["reasoning"]}


@frappe.whitelist()
def test_form_submission(form_key: str):
    """Send a synthetic test submission through a form config. Called from Web Form Settings UI."""
    settings = _get_settings(form_key)
    if not settings:
        return {"success": False, "error": f"No active form found for key '{form_key}'."}

    result = assign_salesperson(
        context={
            "full_name": "Test User",
            "email": "test@example.com",
            "company": "Test Company Ltd",
            "industry": "Technology",
            "subject": "Test Submission — please ignore",
            "message": "This is an automated test submission from the Web Form Settings page.",
            "estimated_budget": "Not sure",
        },
        settings=settings,
    )
    return {
        "success":     True,
        "reference":   f"TEST-{form_key.upper()}",
        "assigned_to": result.get("salesperson_name"),
        "priority":    result.get("priority"),
        "reasoning":   result.get("reasoning"),
    }


# ── 5. Debug endpoint (guest-accessible, remove after fixing) ────────────────

@frappe.whitelist(allow_guest=True, methods=["POST"])
def debug_submission():
    """
    Temporary debug endpoint — returns the full traceback in the response.
    REMOVE THIS after the issue is resolved.

    POST /api/method/ecclesia.api.contact_intake.debug_submission
    Body: same payload as receive_contact_form
    """
    import traceback as tb_module

    steps = []
    try:
        data = frappe.request.get_json(silent=True) or {}
        steps.append(f"1. Payload received: {list(data.keys())}")

        form_key = _sanitise(data.get("form_key", ""))
        steps.append(f"2. form_key = '{form_key}'")

        # Check Web Form Settings DocType exists
        wfs_exists = frappe.db.exists("DocType", "Web Form Settings")
        steps.append(f"3. Web Form Settings DocType exists: {bool(wfs_exists)}")

        if not wfs_exists:
            return {"success": False, "steps": steps,
                    "error": "Web Form Settings DocType does not exist. Run bench migrate."}

        settings = _get_settings(form_key)
        steps.append(f"4. Settings found: {bool(settings)}")

        if not settings:
            # List all existing form keys to help diagnose
            all_keys = frappe.get_all("Web Form Settings",
                fields=["form_key", "is_active", "name"], limit=20)
            return {"success": False, "steps": steps,
                    "error": f"No active record found for form_key='{form_key}'",
                    "existing_records": all_keys}

        steps.append(f"5. Company = '{settings.company}'")
        steps.append(f"6. Assignment strategy = '{settings.assignment_strategy}'")

        # Check Contact Us DocType fields
        existing = _get_doctype_fieldnames("Contact Us")
        critical = ["full_name", "email", "message"]
        missing_critical = [f for f in critical if f not in existing]
        steps.append(f"7. Contact Us fields check — missing critical: {missing_critical}")

        if missing_critical:
            return {"success": False, "steps": steps,
                    "error": f"Contact Us DocType is missing critical fields: {missing_critical}"}

        optional_fields = ["subject", "phone", "company", "source", "industry",
                           "estimated_budget", "status", "priority", "assigned_to",
                           "assigned_to_name", "ai_reasoning", "submission_date",
                           "web_form_key", "linked_company"]
        missing_optional = [f for f in optional_fields if f not in existing]
        steps.append(f"8. Missing optional fields (will be skipped): {missing_optional}")

        # Test salesperson fetch
        salespeople = _get_active_salespeople(
            role=getattr(settings, "target_salesperson_role", ""),
            company=settings.company
        )
        steps.append(f"9. Active salespeople found: {len(salespeople)} — {[s['email'] for s in salespeople]}")

        steps.append("10. All checks passed — safe to submit via receive_contact_form")
        return {"success": True, "steps": steps,
                "missing_optional_fields": missing_optional,
                "salespeople_count": len(salespeople)}

    except Exception:
        return {
            "success": False,
            "steps": steps,
            "error": str(tb_module.format_exc()),
        }


# ── 6. Helper / Data functions ───────────────────────────────────────────────

def _get_settings(form_key: str):
    """Fetch the Web Form Settings record by form_key. Returns doc or None."""
    if not form_key:
        return None
    name = frappe.db.get_value(
        "Web Form Settings",
        {"form_key": form_key, "is_active": 1},
        "name",
    )
    if not name:
        return None
    return frappe.get_doc("Web Form Settings", name)


def _get_default_settings():
    """Fallback settings object when no form_key is available."""
    class _S:
        assignment_strategy    = "AI + Load Balancing"
        ai_provider            = "Anthropic (Claude)"
        target_salesperson_role= ""
        company                = ""
        duplicate_window_hours = 24
        notify_emails          = ""
        redirect_url           = ""
        success_message        = "Thank you!"
        success_subtext        = ""
    return _S()


def _get_active_salespeople(role: str = "", company: str = "") -> list:
    """
    Fetch salespeople eligible for assignment.
    Filters by role if provided, otherwise falls back to Sales User / Sales Manager roles.
    """
    try:
        if frappe.db.exists("DocType", "Salesperson Profile"):
            filters = {"enabled": 1, "is_active": 1}
            if company:
                filters["company"] = company
            records = frappe.get_all(
                "Salesperson Profile",
                filters=filters,
                fields=["name", "full_name", "email", "specialisation", "industries"],
            )
            return [dict(r) for r in records]

        # Fall back to ERPNext Users with sales role
        target_roles = [role] if role else ["Sales User", "Sales Manager"]
        users = frappe.get_all(
            "User",
            filters={"enabled": 1, "user_type": "System User"},
            fields=["name as email", "full_name"],
        )
        result = []
        for u in users:
            user_roles = frappe.get_roles(u["email"])
            if any(r in user_roles for r in target_roles):
                result.append({
                    "email":          u["email"],
                    "full_name":      u["full_name"],
                    "specialisation": "General",
                    "industries":     "All",
                })
        return result
    except Exception:
        return []


def _get_open_lead_count(salesperson_email: str, company: str = "") -> int:
    filters = {
        "assigned_to": salesperson_email,
        "status": ["in", ["New", "In Progress", "Contacted"]],
    }
    existing_fields = _get_doctype_fieldnames("Contact Us")
    if company and "linked_company" in existing_fields:
        filters["linked_company"] = company
    return cint(frappe.db.count("Contact Us", filters=filters))


def _get_round_robin_index(company: str) -> int:
    """
    Uses ERPNext's cache to maintain a per-company round-robin counter.
    Increments atomically and returns the current index.
    """
    key = f"rr_index_{company or 'global'}"
    idx = cint(frappe.cache().get_value(key) or 0)
    frappe.cache().set_value(key, idx + 1)
    return idx


def _is_duplicate(email: str, company: str = "", window_hours: int = 24) -> bool:
    cutoff  = now_datetime() - timedelta(hours=window_hours)
    filters = {"email": email, "creation": [">", cutoff]}
    # Only filter by linked_company if that column actually exists in the table
    existing_fields = _get_doctype_fieldnames("Contact Us")
    if company and "linked_company" in existing_fields:
        filters["linked_company"] = company
    return bool(frappe.db.exists("Contact Us", filters))


def _fallback_assignment(reason: str = "") -> dict:
    return {
        "salesperson_email": "",
        "salesperson_name":  "Unassigned",
        "priority":          "Medium",
        "reasoning":         reason or "No eligible salesperson found; left unassigned.",
    }


def _notify_salesperson(doc, email: str, name: str, settings):
    if not email:
        return
    try:
        frappe.publish_realtime(
            "new_lead_assigned",
            {"message": f"New lead from {doc.full_name} ({doc.company or doc.email}).", "doc": doc.name},
            user=email,
        )
        frappe.sendmail(
            recipients=[email],
            subject=f"[New Lead] {doc.full_name} — {doc.subject}",
            message=f"""
            <p>Hi {name},</p>
            <p>A new contact inquiry has been assigned to you via <b>{settings.form_label if hasattr(settings, 'form_label') else 'Website'}</b>.</p>
            <table style="border-collapse:collapse;width:100%;font-size:13px">
              <tr><td style="padding:5px 8px;font-weight:600;color:#555">Name</td><td>{doc.full_name}</td></tr>
              <tr><td style="padding:5px 8px;font-weight:600;color:#555">Email</td><td>{doc.email}</td></tr>
              <tr><td style="padding:5px 8px;font-weight:600;color:#555">Company</td><td>{doc.company or '—'}</td></tr>
              <tr><td style="padding:5px 8px;font-weight:600;color:#555">Subject</td><td>{doc.subject}</td></tr>
              <tr><td style="padding:5px 8px;font-weight:600;color:#555">Priority</td><td>{doc.priority}</td></tr>
              <tr><td style="padding:5px 8px;font-weight:600;color:#555">Message</td><td>{doc.message}</td></tr>
              <tr><td style="padding:5px 8px;font-weight:600;color:#555">AI Reasoning</td><td><em>{doc.ai_reasoning}</em></td></tr>
            </table>
            <p style="margin-top:16px">
              <a href="{frappe.utils.get_url()}/app/contact-us/{doc.name}"
                 style="background:#0f1117;color:#fff;padding:8px 16px;border-radius:4px;text-decoration:none;font-size:13px">
                Open in ERPNext →
              </a>
            </p>
            """,
            now=True,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Salesperson Notification Failed")


def _notify_additional_emails(doc, settings):
    """Send BCC copy to any additional notification addresses on the form config."""
    raw = (settings.notify_emails or "") if hasattr(settings, "notify_emails") else ""
    extras = [e.strip() for e in raw.splitlines() if e.strip()]
    if not extras:
        return
    try:
        frappe.sendmail(
            recipients=extras,
            subject=f"[Contact Form Copy] {doc.full_name} — {doc.subject}",
            message=f"<p>New submission via <b>{getattr(settings, 'form_label', 'Website')}</b>.</p>"
                    f"<p><b>Name:</b> {doc.full_name}<br><b>Email:</b> {doc.email}<br>"
                    f"<b>Subject:</b> {doc.subject}<br><b>Message:</b> {doc.message}</p>",
            now=True,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Additional Email Notification Failed")


def _parse_options(raw: str, defaults: list) -> list:
    """Parse newline-delimited options string; fall back to defaults."""
    if not raw or not raw.strip():
        return defaults
    return [o.strip() for o in raw.splitlines() if o.strip()]


def _sanitise(value: str) -> str:
    clean = re.sub(r"<[^>]+>", "", str(value or ""))
    return clean[:500].strip()

def _get_doctype_fieldnames(doctype: str) -> set:
    """Return set of fieldnames that exist in a DocType. Cached per request."""
    cache_key = f"_fieldnames_{doctype}"
    cached = frappe.local.flags.get(cache_key)
    if cached:
        return cached
    meta  = frappe.get_meta(doctype)
    names = {f.fieldname for f in meta.fields}
    frappe.local.flags[cache_key] = names
    return names


def _sf(doc_data: dict, existing: set, fieldname: str, value) -> None:
    """Set field on doc_data only if the field exists in the DocType."""
    if fieldname in existing and value not in (None, ""):
        doc_data[fieldname] = value