"""
ecclesia/api/job_post_api.py
==============================
Platform posting logic for the Job Publishing integration.
Supports: LinkedIn, Twitter/X, Facebook, Instagram, Indeed, Glassdoor,
          Jobberman, WhatsApp Business, Telegram, Company Website.

Place at: ecclesia/ecclesia/api/job_post_api.py
"""
import frappe
from frappe import _
from frappe.utils import flt, cint, nowdate, now_datetime, add_days
import json
import requests


# ── DISPATCHER ──────────────────────────────────────────────────────────────

def post_to_platform(job_post_name, target_row_name):
    """
    Route a single target row to the correct platform integration.
    Returns { success, post_id, post_url, error }.
    """
    job_post = frappe.get_doc("Job Post", job_post_name)
    target   = next((r for r in job_post.targets if r.name == target_row_name), None)
    if not target:
        return {"success": False, "error": "Target row not found"}

    platform = frappe.get_doc("Job Board Platform", target.platform)
    message  = _build_message(job_post, platform, target)

    payload = {
        "job_post":    job_post,
        "platform":    platform,
        "target":      target,
        "message":     message,
        "image_url":   target.image_attachment or job_post.featured_image or "",
        "apply_url":   job_post.apply_url or "",
        "hashtags":    _merge_hashtags(target.hashtags, platform.default_hashtags),
    }

    name_lower = (platform.platform_name or "").lower()
    ptype      = (platform.platform_type or "").lower()

    try:
        if "linkedin" in name_lower and ptype == "job board":
            return _post_linkedin_job(payload)
        elif "linkedin" in name_lower:
            return _post_linkedin_social(payload)
        elif "twitter" in name_lower or "/x" in name_lower or name_lower == "x":
            return _post_twitter(payload)
        elif "facebook" in name_lower:
            return _post_facebook(payload)
        elif "instagram" in name_lower:
            return _post_instagram(payload)
        elif "indeed" in name_lower:
            return _post_indeed_feed(payload)
        elif "glassdoor" in name_lower:
            return _post_glassdoor_feed(payload)
        elif "jobberman" in name_lower:
            return _post_jobberman(payload)
        elif "whatsapp" in name_lower:
            return _post_whatsapp(payload)
        elif "telegram" in name_lower:
            return _post_telegram(payload)
        elif ptype == "company website":
            return _post_company_website(payload)
        else:
            return _post_indeed_feed(payload)   # fallback: XML feed
    except Exception:
        err = frappe.get_traceback()
        frappe.log_error(err, "Job Post Error: " + (platform.platform_name or ""))
        return {"success": False, "error": err[:500]}


# ── MESSAGE BUILDER ──────────────────────────────────────────────────────────

def _build_message(job_post, platform, target):
    if target.custom_message and target.custom_message.strip():
        return target.custom_message.strip()
    if platform.message_template:
        try:
            ctx = {
                "job_title":    job_post.job_title or "",
                "company":      job_post.company   or "",
                "location":     job_post.location_display or "",
                "work_mode":    job_post.work_mode or "",
                "requirements": job_post.key_requirements or "",
                "description":  frappe.utils.strip_html(job_post.base_description or ""),
                "salary":       job_post.salary_display or "Competitive",
                "apply_url":    job_post.apply_url or "",
                "priority":     job_post.priority or "Normal",
            }
            return frappe.render_template(platform.message_template, ctx)
        except Exception:
            pass
    # Generic fallback
    limit = cint(platform.character_limit) or 3000
    desc  = frappe.utils.strip_html(job_post.base_description or "")[:400]
    msg   = (f"We're Hiring: {job_post.job_title}\n"
             f"Company: {job_post.company}\n"
             f"Location: {job_post.location_display or ''} {job_post.work_mode or ''}\n\n"
             f"{desc}\n\nApply: {job_post.apply_url or ''}")
    return msg[:limit] if limit else msg


def _merge_hashtags(*args):
    tags = set()
    for a in args:
        for t in (a or "").split():
            t = t.strip()
            if t:
                tags.add(t if t.startswith("#") else "#" + t)
    return " ".join(sorted(tags))


# ── SOCIAL MEDIA ─────────────────────────────────────────────────────────────

def _post_linkedin_social(p):
    platform = p["platform"]
    token    = platform.get_password("access_token")
    org_urn  = f"urn:li:organization:{platform.organization_id}"
    body = {
        "author": org_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": p["message"]},
                "shareMediaCategory": "ARTICLE" if p["apply_url"] else "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    if p["apply_url"]:
        body["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [{
            "status": "READY",
            "description": {"text": "Apply now"},
            "originalUrl": p["apply_url"],
            "title": {"text": p["job_post"].job_title or ""},
        }]
    resp = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json",
                 "X-Restli-Protocol-Version": "2.0.0"},
        json=body, timeout=30
    )
    if resp.ok:
        post_id = resp.json().get("id","").split(":")[-1]
        return {"success": True, "post_id": post_id,
                "post_url": f"https://www.linkedin.com/feed/update/urn:li:share:{post_id}"}
    return {"success": False, "error": f"LinkedIn {resp.status_code}: {resp.text[:300]}"}


def _post_linkedin_job(p):
    platform = p["platform"]
    token    = platform.get_password("access_token")
    job_post = p["job_post"]
    body = {
        "companyApplyUrl":        p["apply_url"],
        "description":            frappe.utils.strip_html(job_post.base_description or "")[:25000],
        "employmentStatus":       "FULL_TIME",
        "externalJobPostingId":   job_post.name,
        "listedAt":               int(now_datetime().timestamp() * 1000),
        "jobPostingOperationType":"CREATE",
        "title":                  job_post.job_title or "",
        "location":               {"countryCode": "NG", "description": job_post.location_display or ""},
        "workplaceTypes": [
            "REMOTE" if "remote" in (job_post.work_mode or "").lower()
            else "HYBRID" if "hybrid" in (job_post.work_mode or "").lower()
            else "ON_SITE"
        ],
    }
    resp = requests.post(
        "https://api.linkedin.com/v2/simpleJobPostings",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json",
                 "X-Restli-Protocol-Version": "2.0.0"},
        json=body, timeout=30
    )
    if resp.ok:
        jid = resp.json().get("id","")
        return {"success": True, "post_id": str(jid),
                "post_url": f"https://www.linkedin.com/jobs/view/{jid}"}
    return {"success": False, "error": f"LinkedIn Jobs {resp.status_code}: {resp.text[:300]}"}


def _post_twitter(p):
    platform = p["platform"]
    token    = platform.get_password("access_token")
    text     = p["message"]
    if p["hashtags"]:
        candidate = text + "\n" + p["hashtags"]
        text = candidate if len(candidate) <= 280 else text[:276] + "...\n" + p["hashtags"][:3]
    text = text[:280]
    resp = requests.post(
        "https://api.twitter.com/2/tweets",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"text": text}, timeout=30
    )
    if resp.ok:
        tweet_id = resp.json().get("data",{}).get("id","")
        return {"success": True, "post_id": tweet_id,
                "post_url": f"https://twitter.com/i/web/status/{tweet_id}"}
    return {"success": False, "error": f"X/Twitter {resp.status_code}: {resp.text[:300]}"}


def _post_facebook(p):
    platform = p["platform"]
    token    = platform.get_password("access_token")
    page_id  = platform.page_id
    data     = {"message": p["message"], "access_token": token}
    if p["apply_url"]:
        data["link"] = p["apply_url"]
    resp = requests.post(
        f"https://graph.facebook.com/v19.0/{page_id}/feed",
        data=data, timeout=30
    )
    if resp.ok:
        post_id = resp.json().get("id","")
        return {"success": True, "post_id": post_id,
                "post_url": f"https://www.facebook.com/{post_id.replace('_','/')}"}
    return {"success": False, "error": f"Facebook {resp.status_code}: {resp.text[:300]}"}


def _post_instagram(p):
    platform   = p["platform"]
    token      = platform.get_password("access_token")
    ig_user_id = platform.page_id
    if not p["image_url"]:
        return {"success": False, "error": "Instagram requires an image. Add a featured image."}
    caption = p["message"][:2200]
    if p["hashtags"]:
        caption += "\n" + p["hashtags"]
    container = requests.post(
        f"https://graph.facebook.com/v19.0/{ig_user_id}/media",
        data={"image_url": p["image_url"], "caption": caption, "access_token": token},
        timeout=30
    )
    if not container.ok:
        return {"success": False, "error": f"IG container {container.status_code}: {container.text[:200]}"}
    container_id = container.json().get("id")
    publish = requests.post(
        f"https://graph.facebook.com/v19.0/{ig_user_id}/media_publish",
        data={"creation_id": container_id, "access_token": token}, timeout=30
    )
    if publish.ok:
        media_id = publish.json().get("id","")
        return {"success": True, "post_id": media_id,
                "post_url": f"https://www.instagram.com/p/{media_id}"}
    return {"success": False, "error": f"IG publish {publish.status_code}: {publish.text[:200]}"}


# ── JOB BOARDS ───────────────────────────────────────────────────────────────

def _build_indeed_xml(job_post, apply_url):
    from xml.etree.ElementTree import Element, SubElement, tostring
    root = Element("source")
    SubElement(root, "publisherUrl").text   = frappe.utils.get_url()
    SubElement(root, "lastBuildDate").text  = now_datetime().strftime("%a, %d %b %Y %H:%M:%S +0000")
    j = SubElement(root, "job")
    SubElement(j, "title").text         = job_post.job_title or ""
    SubElement(j, "date").text          = nowdate()
    SubElement(j, "referencenumber").text= job_post.name
    SubElement(j, "url").text           = apply_url
    SubElement(j, "company").text       = job_post.company or ""
    SubElement(j, "city").text          = job_post.location_display or "Lagos"
    SubElement(j, "country").text       = "Nigeria"
    SubElement(j, "description").text   = frappe.utils.strip_html(
        job_post.base_description or "")[:10000]
    SubElement(j, "salary").text        = job_post.salary_display or ""
    if job_post.expiry_date:
        SubElement(j, "expirationdate").text = str(job_post.expiry_date)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(root, encoding="unicode")


def _save_feed_file(content, filename):
    file_doc = frappe.get_doc({"doctype":"File","file_name":filename,
                                "content": content,"is_private":0})
    file_doc.save(ignore_permissions=True)
    return frappe.utils.get_url(file_doc.file_url), file_doc.name


def _post_indeed_feed(p):
    job_post = p["job_post"]
    xml      = _build_indeed_xml(job_post, p["apply_url"])
    url, fid = _save_feed_file(xml, f"indeed_feed_{job_post.name}.xml")
    # Optionally ping Indeed's re-crawl API
    token = p["platform"].get_password("access_token")
    if token:
        try:
            requests.post("https://apis.indeed.com/publisher-jobs/v2/jobs",
                headers={"Authorization": f"Bearer {token}","Content-Type":"application/xml"},
                data=xml, timeout=20)
        except Exception:
            pass
    return {"success": True, "post_id": fid, "post_url": url}


def _post_glassdoor_feed(p):
    from xml.etree.ElementTree import Element, SubElement, tostring
    job_post = p["job_post"]
    root = Element("JobListings")
    j = SubElement(root, "Job")
    SubElement(j, "JobTitle").text    = job_post.job_title or ""
    SubElement(j, "JobFunction").text = "General"
    SubElement(j, "JobDesc").text     = frappe.utils.strip_html(job_post.base_description or "")[:5000]
    SubElement(j, "JobType").text     = "fulltime"
    SubElement(j, "Location").text    = job_post.location_display or "Lagos, Nigeria"
    SubElement(j, "PostDate").text    = nowdate()
    SubElement(j, "ApplyURL").text    = p["apply_url"]
    SubElement(j, "Employer").text    = job_post.company or ""
    if job_post.expiry_date:
        SubElement(j, "ExpirationDate").text = str(job_post.expiry_date)
    xml      = '<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(root, encoding="unicode")
    url, fid = _save_feed_file(xml, f"glassdoor_feed_{job_post.name}.xml")
    return {"success": True, "post_id": fid, "post_url": url}


def _post_jobberman(p):
    platform = p["platform"]
    job_post = p["job_post"]
    token    = platform.get_password("access_token")
    if token:
        extra    = json.loads(platform.extra_config or "{}")
        endpoint = extra.get("api_endpoint", "https://api.jobberman.com/v2/jobs")
        body = {
            "title":        job_post.job_title,
            "description":  frappe.utils.strip_html(job_post.base_description or ""),
            "location":     job_post.location_display or "Lagos",
            "company_name": job_post.company,
            "apply_url":    p["apply_url"],
            "salary":       job_post.salary_display or "",
            "closing_date": str(job_post.expiry_date or add_days(nowdate(), 30)),
        }
        resp = requests.post(endpoint,
            headers={"Authorization": f"Bearer {token}","Content-Type":"application/json"},
            json=body, timeout=30)
        if resp.ok:
            jid = resp.json().get("id","")
            return {"success": True, "post_id": str(jid),
                    "post_url": f"https://www.jobberman.com/jobs/{jid}"}
        return {"success": False, "error": f"Jobberman {resp.status_code}: {resp.text[:300]}"}
    # Email fallback
    email_body = (f"Job Title: {job_post.job_title}\nCompany: {job_post.company}\n"
                  f"Location: {job_post.location_display}\nSalary: {job_post.salary_display or 'Competitive'}\n\n"
                  f"Description:\n{frappe.utils.strip_html(job_post.base_description or '')}\n\n"
                  f"Apply at: {p['apply_url']}\nClosing: {job_post.expiry_date or add_days(nowdate(),30)}")
    frappe.sendmail(recipients=["jobs@jobberman.com"],
        subject=f"Job Posting: {job_post.job_title} at {job_post.company}",
        message=email_body)
    return {"success": True, "post_id": "email-fallback",
            "post_url": "https://www.jobberman.com",
            "error": "Submitted via email — add API token for direct posting"}


# ── MESSAGING ────────────────────────────────────────────────────────────────

def _post_whatsapp(p):
    platform  = p["platform"]
    token     = platform.get_password("access_token")
    phone_id  = platform.page_id
    extra     = json.loads(platform.extra_config or "{}")
    recipient = extra.get("broadcast_list_id") or extra.get("channel_id","")
    if not recipient:
        return {"success": False, "error": "WhatsApp: set broadcast_list_id in Extra Config JSON"}
    body = {"messaging_product":"whatsapp","to": recipient,
            "type":"text","text":{"body": p["message"][:4096]}}
    resp = requests.post(
        f"https://graph.facebook.com/v19.0/{phone_id}/messages",
        headers={"Authorization": f"Bearer {token}","Content-Type":"application/json"},
        json=body, timeout=30)
    if resp.ok:
        msg_id = resp.json().get("messages",[{}])[0].get("id","")
        return {"success": True, "post_id": msg_id, "post_url": ""}
    return {"success": False, "error": f"WhatsApp {resp.status_code}: {resp.text[:300]}"}


def _post_telegram(p):
    platform  = p["platform"]
    bot_token = platform.get_password("access_token")
    channel   = platform.page_id
    text      = p["message"]
    if p["hashtags"]:
        text += "\n\n" + p["hashtags"]
    resp = requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        json={"chat_id": channel,"text": text[:4096],
              "parse_mode":"HTML","disable_web_page_preview": False},
        timeout=30)
    if resp.ok:
        msg_id = str(resp.json().get("result",{}).get("message_id",""))
        return {"success": True, "post_id": msg_id,
                "post_url": f"https://t.me/{channel.lstrip('@')}/{msg_id}"}
    return {"success": False, "error": f"Telegram {resp.status_code}: {resp.text[:300]}"}


# ── COMPANY WEBSITE ───────────────────────────────────────────────────────────

def _post_company_website(p):
    job_post    = p["job_post"]
    apply_url   = p["apply_url"] or (
        frappe.utils.get_url() + f"/apply?job={job_post.job_opening}")
    frappe.db.set_value("Job Opening", job_post.job_opening, {
        "custom_published_date": nowdate(),
        "custom_is_published":   1,
    })
    frappe.db.commit()
    return {"success": True, "post_id": job_post.job_opening, "post_url": apply_url}


# ── AI CONTENT OPTIMIZER ──────────────────────────────────────────────────────

@frappe.whitelist()
def ai_optimize_targets(job_post_name):
    """
    Use Claude to rewrite content for every platform's style and character limit.
    Called from the Job Post form's AI Optimize button.
    """
    doc      = frappe.get_doc("Job Post", job_post_name)
    base     = frappe.utils.strip_html(doc.base_description or "")
    results  = {}

    for target in doc.targets:
        if not cint(target.include):
            continue
        platform = frappe.get_doc("Job Board Platform", target.platform)
        limit    = cint(platform.character_limit) or 3000

        optimized = _call_ai_for_platform(
            job_title    = doc.job_title or "",
            company      = doc.company or "",
            location     = doc.location_display or "",
            work_mode    = doc.work_mode or "",
            requirements = doc.key_requirements or "",
            description  = base,
            salary       = doc.salary_display or "Competitive",
            apply_url    = doc.apply_url or "",
            tone         = doc.tone or "Professional",
            audience     = doc.target_audience or "Mid-level",
            platform_name= platform.platform_name or "",
            platform_type= platform.platform_type or "",
            char_limit   = limit,
            hashtags     = _merge_hashtags(target.hashtags, platform.default_hashtags),
        )
        if optimized:
            frappe.db.set_value("Job Post Target", target.name, "custom_message", optimized)
            results[target.platform] = "optimized"
        else:
            results[target.platform] = "skipped"

    frappe.db.set_value("Job Post", job_post_name,
        {"ai_status": "Complete", "ai_last_run": now_datetime()})
    frappe.db.commit()
    return results


def _call_ai_for_platform(job_title, company, location, work_mode,
                           requirements, description, salary, apply_url,
                           tone, audience, platform_name, platform_type,
                           char_limit, hashtags):
    style_guides = {
        "linkedin":   "Professional thought-leadership tone. Use line breaks. Mention culture. Clear CTA.",
        "twitter":    "Punchy. Under 240 chars body. Heavy hashtags. Energy.",
        "facebook":   "Conversational community feel. Tell the role story. Invite engagement.",
        "instagram":  "Very short caption. Emoji-friendly. 5+ hashtags.",
        "indeed":     "SEO-optimized. Bullet points for requirements. No fluff.",
        "glassdoor":  "Honest, culture-focused. Mention benefits. Candidates research here.",
        "jobberman":  "Nigerian market. Mention location clearly. Use NGN for salary.",
        "whatsapp":   "Short, direct. Mobile-friendly. Apply link prominent.",
        "telegram":   "Brief. Plain text. Hyperlink the apply URL.",
    }
    name_lower = platform_name.lower()
    style      = next((v for k,v in style_guides.items() if k in name_lower),
                      f"Appropriate for {platform_type}.")
    limit_note = f"STRICT limit: {char_limit} characters max." if char_limit else ""

    prompt = (
        f"Write a job posting for {platform_name}.\n\n"
        f"Title: {job_title} | Company: {company} | Location: {location} ({work_mode})\n"
        f"Salary: {salary}\nRequirements: {requirements}\n"
        f"Description: {description[:800]}\nApply URL: {apply_url}\n"
        f"Hashtags: {hashtags}\n\n"
        f"Style: {style}\nTone: {tone}\nAudience: {audience}\n{limit_note}\n\n"
        f"Return ONLY the post text ready to publish. No preamble. Include apply URL naturally."
    )
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type":"application/json"},
            json={"model":"claude-sonnet-4-6","max_tokens":600,
                  "messages":[{"role":"user","content":prompt}]},
            timeout=25
        )
        if resp.ok:
            text = resp.json().get("content",[{}])[0].get("text","").strip()
            if char_limit and len(text) > char_limit:
                text = text[:char_limit-3] + "..."
            return text
    except Exception:
        frappe.log_error(frappe.get_traceback(), "AI Optimize Error")
    return None


# ── SCHEDULER & BULK ACTIONS ──────────────────────────────────────────────────

def dispatch_scheduled_posts():
    """Hourly scheduler — posts anything due now."""
    from frappe.utils import get_datetime
    now    = now_datetime()
    pending = frappe.get_all("Job Post",
        filters={"posting_status":"Scheduled","docstatus":1},
        fields=["name","scheduled_date","scheduled_time"])
    for jp in pending:
        if not jp.scheduled_date:
            continue
        sched = get_datetime(f"{jp.scheduled_date} {jp.scheduled_time or '09:00:00'}")
        if sched <= now:
            frappe.enqueue("ecclesia.api.job_post_api._execute_job_post",
                           job_post_name=jp.name, queue="short", timeout=180)


def _execute_job_post(job_post_name):
    doc = frappe.get_doc("Job Post", job_post_name)
    doc.db_set("posting_status","Posting")
    success_count = 0
    log_lines     = []
    for target in doc.targets:
        if not cint(target.include) or target.post_status == "Posted":
            continue
        frappe.db.set_value("Job Post Target", target.name, "post_status","Posting")
        result = post_to_platform(job_post_name, target.name)
        if result.get("success"):
            frappe.db.set_value("Job Post Target", target.name, {
                "post_status":"Posted","post_id":result.get("post_id",""),
                "post_url":result.get("post_url",""),"posted_on":now_datetime(),"error_message":""})
            success_count += 1
            log_lines.append(f"ok  {target.platform_name}: {result.get('post_url','')}")
            frappe.db.sql("UPDATE `tabJob Board Platform` SET total_posts=IFNULL(total_posts,0)+1,"
                          "last_post_date=%s WHERE name=%s", (now_datetime(), target.platform))
        else:
            frappe.db.set_value("Job Post Target", target.name, {
                "post_status":"Failed","error_message":(result.get("error",""))[:500]})
            log_lines.append(f"err {target.platform_name}: {result.get('error','')[:100]}")
    total   = sum(1 for t in doc.targets if cint(t.include))
    status  = ("Posted" if success_count==total else
               "Partially Posted" if success_count>0 else "Failed")
    ts      = now_datetime().strftime("%Y-%m-%d %H:%M")
    new_log = f"\n[{ts}]\n" + "\n".join(log_lines)
    frappe.db.set_value("Job Post", job_post_name, {
        "posting_status":    status,
        "successfully_posted": success_count,
        "total_platforms":   total,
        "last_posted_on":    now_datetime(),
        "post_log":          (doc.post_log or "") + new_log,
    })
    frappe.db.commit()


@frappe.whitelist()
def post_now(job_post_name):
    """Called from the 'Post Now' button on the Job Post form."""
    frappe.only_for("HR Manager")
    frappe.enqueue("ecclesia.api.job_post_api._execute_job_post",
                   job_post_name=job_post_name, queue="short", timeout=180)
    return {"queued": True, "message": "Posting queued. Refresh in a minute to see results."}


@frappe.whitelist()
def test_platform_connection(platform_name):
    """Test API credentials. Called from Job Board Platform form."""
    frappe.only_for("HR Manager")
    platform  = frappe.get_doc("Job Board Platform", platform_name)
    name_lower = (platform.platform_name or "").lower()
    token     = platform.get_password("access_token")
    ok, error = False, ""
    try:
        if "linkedin" in name_lower:
            r  = requests.get("https://api.linkedin.com/v2/me",
                headers={"Authorization": f"Bearer {token}"}, timeout=15)
            ok = r.ok; error = r.text[:200] if not ok else ""
        elif "twitter" in name_lower or "/x" in name_lower:
            r  = requests.get("https://api.twitter.com/2/users/me",
                headers={"Authorization": f"Bearer {token}"}, timeout=15)
            ok = r.ok; error = r.text[:200] if not ok else ""
        elif "facebook" in name_lower or "instagram" in name_lower:
            r  = requests.get(f"https://graph.facebook.com/v19.0/me?access_token={token}", timeout=15)
            ok = r.ok; error = r.text[:200] if not ok else ""
        elif "telegram" in name_lower:
            r  = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=15)
            ok = r.ok; error = r.text[:200] if not ok else ""
        else:
            ok = bool(token); error = "" if ok else "No access token configured"
    except Exception as e:
        error = str(e)
    frappe.db.set_value("Job Board Platform", platform_name, {
        "connection_status": "Connected" if ok else "Failed",
        "last_tested": now_datetime(),
    })
    frappe.db.commit()
    return {"success": ok, "error": error}


@frappe.whitelist()
def sync_engagement(job_post_name):
    """Fetch latest views/likes/shares from supported platforms."""
    frappe.only_for("HR Manager")
    doc = frappe.get_doc("Job Post", job_post_name)
    for target in doc.targets:
        if target.post_status != "Posted" or not target.post_id:
            continue
        platform  = frappe.get_doc("Job Board Platform", target.platform)
        name_lower = (platform.platform_name or "").lower()
        stats     = {}
        try:
            if "linkedin" in name_lower:
                r = requests.get(
                    f"https://api.linkedin.com/v2/organizationalEntityShareStatistics"
                    f"?q=organizationalEntity&organizationalEntity=urn:li:organization:{platform.organization_id}"
                    f"&shares[0]=urn:li:share:{target.post_id}",
                    headers={"Authorization": f"Bearer {platform.get_password('access_token')}"},
                    timeout=15)
                if r.ok:
                    s = (r.json().get("elements",[{}]) or [{}])[0].get("totalShareStatistics",{})
                    stats = {"views": s.get("impressionCount",0),
                             "likes": s.get("likeCount",0),
                             "shares":s.get("shareCount",0)}
            elif "twitter" in name_lower or "/x" in name_lower:
                r = requests.get(
                    f"https://api.twitter.com/2/tweets/{target.post_id}?tweet.fields=public_metrics",
                    headers={"Authorization": f"Bearer {platform.get_password('access_token')}"},
                    timeout=15)
                if r.ok:
                    m = r.json().get("data",{}).get("public_metrics",{})
                    stats = {"views": m.get("impression_count",0),
                             "likes": m.get("like_count",0),
                             "shares":m.get("retweet_count",0)}
            elif "facebook" in name_lower:
                r = requests.get(
                    f"https://graph.facebook.com/v19.0/{target.post_id}/insights"
                    f"?metric=post_impressions,post_shares"
                    f"&access_token={platform.get_password('access_token')}",
                    timeout=15)
                if r.ok:
                    d = {x["name"]: x.get("values",[{}])[-1].get("value",0)
                         for x in r.json().get("data",[])}
                    stats = {"views": d.get("post_impressions",0),
                             "shares":d.get("post_shares",0)}
        except Exception:
            continue
        if stats:
            frappe.db.set_value("Job Post Target", target.name, {
                "views":  stats.get("views", target.views or 0),
                "likes":  stats.get("likes", target.likes or 0),
                "shares": stats.get("shares",target.shares or 0),
            })
    doc.reload()
    frappe.db.set_value("Job Post", job_post_name, {
        "total_views": sum(t.views or 0 for t in doc.targets),
        "total_likes": sum(t.likes or 0 for t in doc.targets),
    })
    frappe.db.commit()
    return {"synced": True}
