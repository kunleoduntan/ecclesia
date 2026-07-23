# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/ecclesia/page/smm_dashboard/smm_dashboard.py
#
# Whitelisted server-side methods for the Social Media Studio page.

import frappe
from frappe import _
from frappe.utils import flt, nowdate, add_days, get_datetime
import json


# ── POSTS ANALYTICS ──────────────────────────────────────────────────────────

@frappe.whitelist()
def get_posts_summary(days=30):
    """Aggregate KPIs across all posts in the last N days."""
    from_date = add_days(nowdate(), -int(days))
    posts = frappe.get_all(
        "Social Post",
        filters=[["creation", ">=", from_date]],
        fields=["name","status","content_type","total_likes","total_comments",
                "total_shares","total_reach","total_clicks","total_conversions",
                "revenue_generated","total_engagement_rate","creation"],
        limit=2000
    )
    by_status = {}
    for p in posts:
        s = p.status or "Draft"
        by_status[s] = by_status.get(s, 0) + 1

    by_type = {}
    for p in posts:
        t = p.content_type or "Unknown"
        if t not in by_type:
            by_type[t] = {"reach":0, "engage":0, "count":0}
        by_type[t]["reach"]  += flt(p.total_reach)
        by_type[t]["engage"] += flt(p.total_likes) + flt(p.total_comments) + flt(p.total_shares)
        by_type[t]["count"]  += 1

    return {
        "total_posts":       len(posts),
        "total_reach":       sum(flt(p.total_reach) for p in posts),
        "total_likes":       sum(flt(p.total_likes) for p in posts),
        "total_comments":    sum(flt(p.total_comments) for p in posts),
        "total_shares":      sum(flt(p.total_shares) for p in posts),
        "total_clicks":      sum(flt(p.total_clicks) for p in posts),
        "total_conversions": sum(flt(p.total_conversions) for p in posts),
        "total_revenue":     sum(flt(p.revenue_generated) for p in posts),
        "by_status":         by_status,
        "by_content_type":   by_type,
    }


@frappe.whitelist()
def get_daily_trend(days=30):
    """Per-day reach + engagement for trend chart."""
    result = []
    for i in range(int(days) - 1, -1, -1):
        date = add_days(nowdate(), -i)
        posts = frappe.get_all(
            "Social Post",
            filters=[["creation", "like", f"{date}%"]],
            fields=["total_reach", "total_likes", "total_comments", "total_shares", "total_clicks"]
        )
        result.append({
            "date":        date,
            "posts":       len(posts),
            "reach":       sum(flt(p.total_reach) for p in posts),
            "engagements": sum(flt(p.total_likes) + flt(p.total_comments) + flt(p.total_shares) for p in posts),
            "clicks":      sum(flt(p.total_clicks) for p in posts),
        })
    return result


@frappe.whitelist()
def get_top_posts(limit=10, metric="total_reach"):
    """Top N posts by a metric."""
    allowed = ["total_reach","total_likes","total_comments","total_shares","total_clicks","revenue_generated","roi_percentage"]
    if metric not in allowed:
        metric = "total_reach"
    return frappe.get_all(
        "Social Post",
        filters={"status": "Published"},
        fields=["name","post_title","content_type","total_reach","total_likes",
                "total_comments","total_shares","revenue_generated","roi_percentage",
                "total_engagement_rate","global_schedule"],
        order_by=f"{metric} desc",
        limit=int(limit)
    )


# ── COMMENT ANALYTICS ─────────────────────────────────────────────────────────

@frappe.whitelist()
def get_comment_stats():
    """Sentiment + platform breakdown + unanswered count."""
    comments = frappe.get_all(
        "Social Post Comment",
        fields=["platform","sentiment_label","status","is_flagged"],
        limit=2000
    )
    total      = len(comments)
    positive   = len([c for c in comments if c.sentiment_label in ("Positive","Very Positive")])
    negative   = len([c for c in comments if c.sentiment_label in ("Negative","Very Negative")])
    unanswered = len([c for c in comments if c.status == "New"])
    flagged    = len([c for c in comments if c.is_flagged])

    by_platform = {}
    for c in comments:
        p = c.platform or "Other"
        by_platform[p] = by_platform.get(p, 0) + 1

    return {
        "total":      total,
        "positive":   positive,
        "negative":   negative,
        "neutral":    total - positive - negative,
        "unanswered": unanswered,
        "flagged":    flagged,
        "by_platform":by_platform,
    }


# ── POST QUICK-UPDATE ─────────────────────────────────────────────────────────

@frappe.whitelist()
def quick_update_post(post_name, status=None, global_schedule=None, primary_hashtags=None, requires_approval=None):
    """Update specific fields of a post without full reload."""
    fieldname = {}
    if status is not None:           fieldname["status"]             = status
    if global_schedule is not None:  fieldname["global_schedule"]    = global_schedule
    if primary_hashtags is not None: fieldname["primary_hashtags"]   = primary_hashtags
    if requires_approval is not None: fieldname["requires_approval"] = frappe.utils.cint(requires_approval)

    if status == "Approved":
        fieldname["approved_by"]   = frappe.session.user
        fieldname["approval_date"] = frappe.utils.now_datetime()

    frappe.db.set_value("Social Post", post_name, fieldname)
    frappe.db.commit()
    return {"updated": post_name, "fields": fieldname}


@frappe.whitelist()
def bulk_approve(post_names):
    """Approve multiple posts at once."""
    if isinstance(post_names, str):
        post_names = json.loads(post_names)
    now   = frappe.utils.now_datetime()
    user  = frappe.session.user
    updated = 0
    for name in post_names:
        if frappe.db.get_value("Social Post", name, "status") == "Pending Approval":
            frappe.db.set_value("Social Post", name, {
                "status": "Approved", "approved_by": user, "approval_date": now
            })
            updated += 1
    frappe.db.commit()
    return {"approved": updated}


@frappe.whitelist()
def bulk_schedule(post_names, schedule_datetime):
    """Set schedule on multiple posts."""
    if isinstance(post_names, str):
        post_names = json.loads(post_names)
    for name in post_names:
        frappe.db.set_value("Social Post", name, {
            "global_schedule": schedule_datetime,
            "publish_strategy": "Schedule Global",
            "status": "Scheduled"
        })
    frappe.db.commit()
    return {"scheduled": len(post_names)}


# ── CONTENT SCORING ───────────────────────────────────────────────────────────

@frappe.whitelist()
def score_post_content(post_name):
    """Server-side content quality heuristic. Returns 0-100 score + breakdown."""
    post    = frappe.get_doc("Social Post", post_name)
    content = frappe.utils.strip_html(post.content or "")
    hashtags = (post.primary_hashtags or "").split()
    has_media = bool(frappe.get_all("Social Post Media", filters={"parent": post_name}, limit=1))

    score = 0
    breakdown = {}

    # Caption length
    length = len(content)
    if 100 <= length <= 300:   ls = 20
    elif 50 <= length <= 500:  ls = 12
    else:                      ls = 4
    score += ls; breakdown["caption_length"] = ls

    # Hashtags (sweet spot 8-12)
    ht_count = len([h for h in hashtags if h.startswith("#")])
    hs = min(20, max(0, 20 - abs(ht_count - 10) * 2))
    score += hs; breakdown["hashtags"] = hs

    # CTA presence
    cta_words = ["click","buy","shop","learn","discover","get","dm","link in bio","comment","share","visit","download","sign up"]
    has_cta   = any(w in content.lower() for w in cta_words)
    cs = 15 if has_cta else 5
    score += cs; breakdown["cta"] = cs

    # Question / hook
    has_hook = "?" in content or "!" in content or any(content.lower().startswith(w) for w in ["how","why","what","did you","the secret","breaking"])
    hs2 = 15 if has_hook else 5
    score += hs2; breakdown["hook"] = hs2

    # Media
    ms = 25 if has_media else 8
    score += ms; breakdown["media"] = ms

    # Platform config
    plat_count = frappe.db.count("Social Post Platform Config", {"parent": post_name, "is_enabled": 1})
    ps = min(5, plat_count * 2)
    score += ps; breakdown["platforms"] = ps

    final = min(100, score)
    grade = "A" if final >= 80 else "B" if final >= 60 else "C" if final >= 40 else "D"

    suggestions = []
    if breakdown["caption_length"] < 12:  suggestions.append("Caption length is outside optimal range (100–300 chars)")
    if breakdown["hashtags"] < 12:         suggestions.append(f"Add more hashtags (currently {ht_count}) — optimal is 8–12")
    if not has_cta:                        suggestions.append("Add a clear call-to-action to drive clicks")
    if not has_hook:                       suggestions.append("Start with a question or power word to improve hook strength")
    if not has_media:                      suggestions.append("Attach an image or video — posts with media get 3× more reach")
    if not suggestions:                    suggestions.append("Content looks strong! Consider A/B testing with a different hook.")

    # Persist score back
    frappe.db.set_value("Social Post", post_name, "ai_recommendations", "\n".join(suggestions[:3]))
    frappe.db.commit()

    return {"score": final, "grade": grade, "breakdown": breakdown, "suggestions": suggestions}


# ── PLATFORM TOKEN CHECK ──────────────────────────────────────────────────────

@frappe.whitelist()
def get_expiring_tokens(days_ahead=7):
    """Return platform accounts with tokens expiring within N days."""
    threshold = add_days(nowdate(), int(days_ahead))
    settings  = frappe.get_single("Social Media Settings")
    expiring  = []
    for acc in (settings.platform_accounts or []):
        if acc.token_expiry_date and acc.token_expiry_date <= threshold and acc.is_active:
            expiring.append({
                "name":             acc.name,
                "platform":         acc.platform,
                "account_name":     acc.account_name,
                "token_expiry_date":acc.token_expiry_date,
            })
    return expiring


# ── SETTINGS HELPERS ──────────────────────────────────────────────────────────

@frappe.whitelist()
def get_settings():
    """Return full Social Media Settings document."""
    return frappe.get_single("Social Media Settings")


@frappe.whitelist()
def save_settings(settings_json):
    """Save Social Media Settings from dashboard."""
    if isinstance(settings_json, str):
        settings_json = json.loads(settings_json)
    doc = frappe.get_single("Social Media Settings")
    for k, v in settings_json.items():
        if k not in ("doctype", "name", "owner", "creation", "modified"):
            doc.set(k, v)
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"saved": True}


# ── CALENDAR POSTS ────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_calendar_posts(year, month):
    """Posts scheduled in a given month."""
    import calendar
    last_day = calendar.monthrange(int(year), int(month))[1]
    from_dt  = f"{year}-{str(month).zfill(2)}-01"
    to_dt    = f"{year}-{str(month).zfill(2)}-{last_day} 23:59:59"
    return frappe.get_all(
        "Social Post",
        filters=[["global_schedule",">=",from_dt],["global_schedule","<=",to_dt]],
        fields=["name","post_title","status","content_type","global_schedule","campaign"],
        order_by="global_schedule asc"
    )


# ── COMMENT UPDATES (child table of Social Post) ──────────────────────────────

@frappe.whitelist()
def update_comment(post_name, comment_name, updates):
    """
    Update a Social Post Comment child row.
    Social Post Comment is a child table — cannot use set_value directly.
    Must get the parent Social Post, mutate the child row, then save.
    """
    if isinstance(updates, str):
        import json
        updates = json.loads(updates)

    post = frappe.get_doc("Social Post", post_name)

    # Find the matching child row by name
    updated = False
    for row in post.comments:
        if row.name == comment_name:
            for k, v in updates.items():
                if hasattr(row, k):
                    row.set(k, v)
            updated = True
            break

    if not updated:
        frappe.throw(f"Comment {comment_name} not found in post {post_name}")

    post.save(ignore_permissions=True)
    frappe.db.commit()
    return {"updated": comment_name, "post": post_name}


@frappe.whitelist()
def get_post_comments(post_name):
    """Fetch all comments for a specific Social Post."""
    post = frappe.get_doc("Social Post", post_name)
    return [
        {
            "name":            c.name,
            "platform":        c.platform,
            "author_name":     c.author_name,
            "comment_text":    c.comment_text,
            "comment_time":    str(c.comment_time) if c.comment_time else None,
            "sentiment_label": c.sentiment_label,
            "sentiment_score": c.sentiment_score,
            "status":          c.status,
            "is_flagged":      c.is_flagged,
            "reply_text":      c.reply_text,
            "reply_status":    c.reply_status,
            "like_count":      c.like_count,
            "parent":          post_name,
        }
        for c in (post.comments or [])
    ]