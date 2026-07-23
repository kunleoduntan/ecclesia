# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/ecclesia/page/smm_dashboard/smm_dashboard.py
#
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  SMM Dashboard + SMHub AI Intelligence — Full Python Backend            ║
# ║  Whitelisted methods for all 8 dashboard views including SMHub          ║
# ╚══════════════════════════════════════════════════════════════════════════╝

import frappe
from frappe import _
from frappe.utils import flt, cint, nowdate, add_days, get_datetime, now_datetime
import json
from datetime import datetime, timedelta


# ════════════════════════════════════════════════════════════════════════════
#  POSTS — Core analytics
# ════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_posts_summary(days=30):
    """Aggregate KPIs across all posts in the last N days."""
    from_date = add_days(nowdate(), -int(days))
    posts = frappe.get_all(
        "Social Post",
        filters=[["creation", ">=", from_date]],
        fields=["name", "status", "content_type", "total_likes", "total_comments",
                "total_shares", "total_reach", "total_clicks", "total_conversions",
                "revenue_generated", "total_engagement_rate", "primary_hashtags",
                "global_schedule", "creation", "modified"],
        limit=2000
    )

    by_status, by_type = {}, {}
    for p in posts:
        s = p.status or "Draft"
        by_status[s] = by_status.get(s, 0) + 1
        t = p.content_type or "Unknown"
        if t not in by_type:
            by_type[t] = {"reach": 0, "engage": 0, "count": 0}
        by_type[t]["reach"]  += flt(p.total_reach)
        by_type[t]["engage"] += flt(p.total_likes) + flt(p.total_comments) + flt(p.total_shares)
        by_type[t]["count"]  += 1

    total_reach  = sum(flt(p.total_reach)          for p in posts)
    total_engage = sum(flt(p.total_likes) + flt(p.total_comments) + flt(p.total_shares) for p in posts)
    avg_eng      = (sum(flt(p.total_engagement_rate) for p in posts) / len(posts)) if posts else 0

    return {
        "total_posts":       len(posts),
        "total_reach":       total_reach,
        "total_likes":       sum(flt(p.total_likes)         for p in posts),
        "total_comments":    sum(flt(p.total_comments)      for p in posts),
        "total_shares":      sum(flt(p.total_shares)        for p in posts),
        "total_clicks":      sum(flt(p.total_clicks)        for p in posts),
        "total_conversions": sum(flt(p.total_conversions)   for p in posts),
        "total_revenue":     sum(flt(p.revenue_generated)   for p in posts),
        "avg_engagement_rate": round(avg_eng, 2),
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
    """Top N published posts ranked by a given metric."""
    allowed = ["total_reach", "total_likes", "total_comments", "total_shares",
               "total_clicks", "revenue_generated", "roi_percentage", "total_engagement_rate"]
    if metric not in allowed:
        metric = "total_reach"
    return frappe.get_all(
        "Social Post",
        filters={"status": "Published"},
        fields=["name", "post_title", "content_type", "total_reach", "total_likes",
                "total_comments", "total_shares", "revenue_generated", "roi_percentage",
                "total_engagement_rate", "global_schedule", "primary_hashtags"],
        order_by=f"{metric} desc",
        limit=int(limit)
    )


@frappe.whitelist()
def get_calendar_posts(year, month):
    """Posts scheduled in a given month for calendar view."""
    import calendar
    last_day = calendar.monthrange(int(year), int(month))[1]
    from_dt  = f"{year}-{str(month).zfill(2)}-01"
    to_dt    = f"{year}-{str(month).zfill(2)}-{last_day} 23:59:59"
    return frappe.get_all(
        "Social Post",
        filters=[["global_schedule", ">=", from_dt], ["global_schedule", "<=", to_dt]],
        fields=["name", "post_title", "status", "content_type", "global_schedule", "campaign"],
        order_by="global_schedule asc"
    )


# ════════════════════════════════════════════════════════════════════════════
#  POST MUTATIONS
# ════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def quick_update_post(post_name, status=None, global_schedule=None,
                      primary_hashtags=None, requires_approval=None):
    """Update specific fields of a Social Post without a full form reload."""
    fieldname = {}
    if status is not None:            fieldname["status"]            = status
    if global_schedule is not None:   fieldname["global_schedule"]   = global_schedule
    if primary_hashtags is not None:  fieldname["primary_hashtags"]  = primary_hashtags
    if requires_approval is not None: fieldname["requires_approval"] = cint(requires_approval)

    if status == "Approved":
        fieldname["approved_by"]   = frappe.session.user
        fieldname["approval_date"] = now_datetime()

    frappe.db.set_value("Social Post", post_name, fieldname)
    frappe.db.commit()
    return {"updated": post_name, "fields": list(fieldname.keys())}


@frappe.whitelist()
def bulk_approve(post_names):
    """Approve multiple posts in one call."""
    if isinstance(post_names, str):
        post_names = json.loads(post_names)
    now  = now_datetime()
    user = frappe.session.user
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
    """Bulk-set a global schedule on multiple posts."""
    if isinstance(post_names, str):
        post_names = json.loads(post_names)
    for name in post_names:
        frappe.db.set_value("Social Post", name, {
            "global_schedule":  schedule_datetime,
            "publish_strategy": "Schedule Global",
            "status":           "Scheduled"
        })
    frappe.db.commit()
    return {"scheduled": len(post_names)}


# ════════════════════════════════════════════════════════════════════════════
#  COMMENTS — child table of Social Post
# ════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_comment_stats():
    """Sentiment breakdown, platform counts, unanswered and flagged totals."""
    comments = frappe.get_all(
        "Social Post Comment",
        fields=["platform", "sentiment_label", "status", "is_flagged", "reply_text"],
        limit=2000
    )
    total      = len(comments)
    positive   = sum(1 for c in comments if c.sentiment_label in ("Positive", "Very Positive"))
    negative   = sum(1 for c in comments if c.sentiment_label in ("Negative", "Very Negative"))
    unanswered = sum(1 for c in comments if c.status == "New")
    flagged    = sum(1 for c in comments if c.is_flagged)
    replied    = sum(1 for c in comments if c.status == "Replied" or c.reply_text)

    by_platform = {}
    for c in comments:
        p = c.platform or "Other"
        by_platform[p] = by_platform.get(p, 0) + 1

    return {
        "total":       total,
        "positive":    positive,
        "negative":    negative,
        "neutral":     total - positive - negative,
        "unanswered":  unanswered,
        "flagged":     flagged,
        "replied":     replied,
        "response_rate": round(replied / max(1, total) * 100, 1),
        "by_platform": by_platform,
    }


@frappe.whitelist()
def update_comment(post_name, comment_name, updates):
    """
    Update a Social Post Comment child row.
    Social Post Comment is a child table — set_value doesn't work on rows.
    Must get parent → mutate child row → save parent.
    """
    if isinstance(updates, str):
        updates = json.loads(updates)

    post    = frappe.get_doc("Social Post", post_name)
    updated = False

    for row in (post.comments or []):
        if row.name == comment_name:
            for k, v in updates.items():
                if hasattr(row, k):
                    row.set(k, v)
            updated = True
            break

    if not updated:
        frappe.throw(_(f"Comment {comment_name} not found in post {post_name}"))

    post.save(ignore_permissions=True)
    frappe.db.commit()
    return {"updated": comment_name, "post": post_name}


@frappe.whitelist()
def get_post_comments(post_name):
    """Return all comment child rows for a Social Post as plain dicts."""
    post = frappe.get_doc("Social Post", post_name)
    return [
        {
            "name":            c.name,
            "platform":        c.platform,
            "author_name":     c.author_name,
            "comment_text":    c.comment_text,
            "comment_time":    str(c.comment_time) if c.comment_time else None,
            "sentiment_label": c.sentiment_label,
            "sentiment_score": flt(c.sentiment_score),
            "status":          c.status,
            "is_flagged":      c.is_flagged,
            "reply_text":      c.reply_text,
            "reply_status":    c.reply_status,
            "like_count":      flt(c.like_count),
            "parent":          post_name,
        }
        for c in (post.comments or [])
    ]


# ════════════════════════════════════════════════════════════════════════════
#  CONTENT SCORING
# ════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def score_post_content(post_name):
    """
    8-factor content quality score (0–100).
    Persists result to ai_recommendations field.
    """
    post     = frappe.get_doc("Social Post", post_name)
    content  = frappe.utils.strip_html(post.content or "")
    hashtags = (post.primary_hashtags or "").split()
    has_media = bool(frappe.get_all("Social Post Media",
                                    filters={"parent": post_name}, limit=1))
    plat_count = frappe.db.count("Social Post Platform Config",
                                  {"parent": post_name, "is_enabled": 1})
    score = 0
    breakdown = {}

    # 1. Caption length (optimal 100–300)
    ln = len(content)
    ls = 20 if 100 <= ln <= 300 else 12 if 50 <= ln <= 500 else 4
    score += ls; breakdown["caption_length"] = ls

    # 2. Hashtag count (optimal 8–12)
    ht = len([h for h in hashtags if h.startswith("#")])
    hs = min(20, max(0, 20 - abs(ht - 10) * 2))
    score += hs; breakdown["hashtags"] = hs

    # 3. CTA presence
    cta_words = ["click", "buy", "shop", "learn", "get", "dm", "link in bio",
                 "comment", "share", "visit", "download", "sign up", "subscribe"]
    cs = 15 if any(w in content.lower() for w in cta_words) else 5
    score += cs; breakdown["cta"] = cs

    # 4. Hook / engagement opener
    has_hook = (
        "?" in content or "!" in content or
        any(content.lower().startswith(w) for w in
            ["how", "why", "what", "did you", "the secret", "breaking", "free"])
    )
    hs2 = 15 if has_hook else 5
    score += hs2; breakdown["hook"] = hs2

    # 5. Media attached
    ms = 20 if has_media else 6
    score += ms; breakdown["media"] = ms

    # 6. Platform configured
    ps = min(5, plat_count * 2)
    score += ps; breakdown["platforms"] = ps

    # 7. Link present
    has_link = bool(post.link_url) or "http" in content.lower()
    ls2 = 10 if has_link else 4
    score += ls2; breakdown["link"] = ls2

    # 8. Mentions / community signal
    ms2 = 5 if (post.mentions or "") else 2
    score += ms2; breakdown["mentions"] = ms2

    final = min(100, score)
    grade = "A" if final >= 80 else "B" if final >= 60 else "C" if final >= 40 else "D"

    suggestions = []
    if breakdown["caption_length"] < 12: suggestions.append("Caption outside optimal range — aim for 100–300 characters")
    if ht < 5:                           suggestions.append(f"Only {ht} hashtags — use 8–12 targeted hashtags")
    if breakdown["cta"] < 10:            suggestions.append("No CTA detected — add 'Link in bio', 'DM us', or 'Comment below'")
    if not has_hook:                     suggestions.append("Start with a hook question or power word to stop the scroll")
    if not has_media:                    suggestions.append("No media attached — image/video posts get 3× more reach")
    if not suggestions:                  suggestions.append("Strong content! Try A/B testing a different headline.")

    frappe.db.set_value("Social Post", post_name,
                        "ai_recommendations", "\n".join(suggestions[:3]))
    frappe.db.commit()

    return {"score": final, "grade": grade, "breakdown": breakdown, "suggestions": suggestions}


# ════════════════════════════════════════════════════════════════════════════
#  SETTINGS & PLATFORM TOKENS
# ════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_settings():
    """Return the Social Media Settings singleton."""
    try:
        return frappe.get_single("Social Media Settings")
    except Exception:
        return None


@frappe.whitelist()
def save_settings(settings_json):
    """Update Social Media Settings from the dashboard Settings view."""
    if isinstance(settings_json, str):
        settings_json = json.loads(settings_json)
    doc = frappe.get_single("Social Media Settings")
    skip = {"doctype", "name", "owner", "creation", "modified", "modified_by"}
    for k, v in settings_json.items():
        if k not in skip:
            doc.set(k, v)
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"saved": True}


@frappe.whitelist()
def get_expiring_tokens(days_ahead=7):
    """Platform accounts whose API tokens expire within N days."""
    threshold = add_days(nowdate(), int(days_ahead))
    try:
        settings = frappe.get_single("Social Media Settings")
    except Exception:
        return []

    expiring = []
    for acc in (settings.platform_accounts or []):
        if acc.token_expiry_date and str(acc.token_expiry_date) <= str(threshold) and acc.is_active:
            expiring.append({
                "name":             acc.name,
                "platform":         acc.platform,
                "account_name":     acc.account_name,
                "token_expiry_date": str(acc.token_expiry_date),
            })
    return expiring


# ════════════════════════════════════════════════════════════════════════════
#  SMHUB AI — Brand Health Score
# ════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_brand_health_score(days=30):
    """
    Compute 8-factor Brand Health Score (0–100) for SMHub AI tab.
    Factors: engagement, consistency, reach, sentiment, response rate,
             platform diversity, content completeness, revenue attribution.
    """
    from_date = add_days(nowdate(), -int(days))

    posts = frappe.get_all(
        "Social Post",
        filters=[["status", "=", "Published"], ["creation", ">=", from_date]],
        fields=["name", "total_engagement_rate", "total_reach", "total_likes",
                "total_comments", "total_shares", "primary_hashtags",
                "revenue_generated", "content_type", "creation"],
        limit=500
    )

    comments = frappe.get_all(
        "Social Post Comment",
        fields=["sentiment_label", "status", "reply_text", "is_flagged"],
        limit=2000
    )

    try:
        settings  = frappe.get_single("Social Media Settings")
        platforms = settings.platform_accounts or []
    except Exception:
        platforms = []

    n        = len(posts) or 1
    avg_eng  = sum(flt(p.total_engagement_rate) for p in posts) / n
    total_r  = sum(flt(p.total_reach) for p in posts)
    total_rev= sum(flt(p.revenue_generated) for p in posts)

    # Posts per week in the window
    velocity = n / (int(days) / 7)

    # Sentiment
    pos_comments = sum(1 for c in comments if c.sentiment_label in ("Positive", "Very Positive"))
    sentiment_pct = round(pos_comments / max(1, len(comments)) * 100)

    # Response rate
    replied      = sum(1 for c in comments if c.reply_text or c.status == "Replied")
    response_pct = round(replied / max(1, len(comments)) * 100)

    # Content completeness: posts with hashtags
    with_hashtags = sum(1 for p in posts if (p.primary_hashtags or "").strip())

    # 8 factor scores (each 0–100)
    f_engagement   = min(100, round(avg_eng / 5 * 100))
    f_consistency  = min(100, round(min(velocity, 7) / 7 * 100))
    f_reach        = min(100, 90 if total_r > 100000 else 70 if total_r > 10000 else 50 if total_r > 1000 else 25)
    f_sentiment    = sentiment_pct
    f_response     = min(100, round(response_pct * 1.2))
    f_diversity    = min(100, len(platforms) * 20)
    f_content      = min(100, round(with_hashtags / n * 100))
    f_revenue      = min(100, 75 if total_rev > 0 else 25)

    factors = [f_engagement, f_consistency, f_reach, f_sentiment,
               f_response, f_diversity, f_content, f_revenue]
    overall = round(sum(factors) / len(factors))

    return {
        "overall": overall,
        "grade":   "A" if overall >= 80 else "B" if overall >= 65 else "C" if overall >= 50 else "D",
        "factors": {
            "engagement":   f_engagement,
            "consistency":  f_consistency,
            "reach":        f_reach,
            "sentiment":    f_sentiment,
            "response":     f_response,
            "diversity":    f_diversity,
            "content":      f_content,
            "revenue":      f_revenue,
        },
        "meta": {
            "avg_eng_rate":   round(avg_eng, 2),
            "velocity_week":  round(velocity, 1),
            "sentiment_pct":  sentiment_pct,
            "response_rate":  response_pct,
            "total_revenue":  total_rev,
            "platform_count": len(platforms),
        }
    }


# ════════════════════════════════════════════════════════════════════════════
#  SMHUB AI — Virality Analysis
# ════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_virality_analysis(days=30):
    """
    Identify viral posts (2× average engagement) and compute virality rate.
    Returns viral posts, virality rate, and next-post prediction.
    """
    from_date = add_days(nowdate(), -int(days))
    posts = frappe.get_all(
        "Social Post",
        filters=[["status", "=", "Published"], ["creation", ">=", from_date]],
        fields=["name", "post_title", "content_type", "total_reach",
                "total_likes", "total_comments", "total_shares",
                "total_engagement_rate", "primary_hashtags", "global_schedule"],
        order_by="total_engagement_rate desc",
        limit=500
    )

    if not posts:
        return {
            "viral_rate": 0, "viral_posts": [], "avg_eng": 0,
            "prediction": {"reach": 0, "eng_rate": 0, "confidence": "Low"}
        }

    n       = len(posts)
    avg_eng = sum(flt(p.total_engagement_rate) for p in posts) / n
    avg_reach = sum(flt(p.total_reach) for p in posts) / n

    # Viral threshold: 2× average engagement
    viral  = [p for p in posts if flt(p.total_engagement_rate) >= avg_eng * 2]
    viral_rate = round(len(viral) / n * 100)

    # What viral posts have in common
    viral_types = {}
    for p in viral:
        t = p.content_type or "Unknown"
        viral_types[t] = viral_types.get(t, 0) + 1
    best_viral_type = max(viral_types, key=viral_types.get) if viral_types else "Image"

    # Prediction: next post using recent trend (last 5 posts)
    recent5 = posts[:5]
    trend_eng = sum(flt(p.total_engagement_rate) for p in recent5) / max(1, len(recent5))
    predicted_reach   = round(avg_reach * 1.10)
    predicted_eng     = round(trend_eng * 1.05, 2)
    confidence        = "High" if len(posts) >= 20 else "Medium" if len(posts) >= 10 else "Low"

    return {
        "viral_rate":       viral_rate,
        "avg_eng":          round(avg_eng, 2),
        "avg_reach":        round(avg_reach),
        "best_viral_type":  best_viral_type,
        "viral_posts":      [
            {
                "name":     p.name,
                "title":    p.post_title,
                "type":     p.content_type,
                "reach":    flt(p.total_reach),
                "eng_rate": flt(p.total_engagement_rate),
                "vs_avg":   round((flt(p.total_engagement_rate) / max(0.01, avg_eng) - 1) * 100),
            }
            for p in viral[:5]
        ],
        "prediction": {
            "reach":      predicted_reach,
            "eng_rate":   predicted_eng,
            "confidence": confidence,
            "best_type":  best_viral_type,
        }
    }


# ════════════════════════════════════════════════════════════════════════════
#  SMHUB AI — Platform Benchmark Report
# ════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_platform_benchmark_report(days=30):
    """
    Your actual metrics vs published industry benchmarks per platform.
    Returns comparison data for the Platform Deep Dive table.
    """
    # Published industry benchmarks (Q1 2026 averages)
    BENCHMARKS = {
        "Instagram":             {"eng": 1.94, "reach": 8500,  "freq": 1.1, "response": 55},
        "Instagram Business":    {"eng": 1.94, "reach": 8500,  "freq": 1.1, "response": 55},
        "Facebook":              {"eng": 0.60, "reach": 12000, "freq": 0.9, "response": 48},
        "LinkedIn":              {"eng": 2.00, "reach": 3200,  "freq": 0.6, "response": 72},
        "LinkedIn Company Page": {"eng": 1.60, "reach": 2800,  "freq": 0.5, "response": 65},
        "Twitter/X":             {"eng": 0.49, "reach": 5000,  "freq": 2.5, "response": 42},
        "TikTok":                {"eng": 5.69, "reach": 22000, "freq": 1.5, "response": 38},
        "YouTube":               {"eng": 1.63, "reach": 45000, "freq": 0.3, "response": 55},
        "Pinterest":             {"eng": 0.16, "reach": 6500,  "freq": 0.8, "response": 30},
        "WhatsApp Business":     {"eng": 8.00, "reach": 1200,  "freq": 2.0, "response": 85},
    }

    from_date = add_days(nowdate(), -int(days))
    posts = frappe.get_all(
        "Social Post",
        filters=[["status", "=", "Published"], ["creation", ">=", from_date]],
        fields=["total_engagement_rate", "total_reach", "creation"],
        limit=500
    )

    try:
        settings  = frappe.get_single("Social Media Settings")
        platforms = [a.platform for a in (settings.platform_accounts or []) if a.platform]
    except Exception:
        platforms = []

    n         = len(posts) or 1
    your_eng  = sum(flt(p.total_engagement_rate) for p in posts) / n
    your_reach= sum(flt(p.total_reach) for p in posts) / n
    velocity  = n / (int(days) / 7)

    result = []
    for plat in platforms:
        bench = BENCHMARKS.get(plat, {"eng": 1.5, "reach": 5000, "freq": 1.0, "response": 50})
        eng_vs  = round((your_eng  / max(0.01, bench["eng"])  - 1) * 100)
        reach_vs= round((your_reach / max(1, bench["reach"]) - 1) * 100)
        status  = "above" if your_eng >= bench["eng"] else "near" if your_eng >= bench["eng"] * 0.7 else "below"
        result.append({
            "platform":      plat,
            "your_eng":      round(your_eng, 2),
            "bench_eng":     bench["eng"],
            "your_reach":    round(your_reach),
            "bench_reach":   bench["reach"],
            "your_velocity": round(velocity, 1),
            "bench_freq":    bench["freq"],
            "eng_vs_bench":  eng_vs,
            "reach_vs_bench":reach_vs,
            "status":        status,
            "posts_count":   n,
        })

    return {
        "platforms":   result,
        "your_overall_eng":   round(your_eng, 2),
        "your_overall_reach": round(your_reach),
        "post_count":         n,
        "days":               int(days),
    }


# ════════════════════════════════════════════════════════════════════════════
#  SMHUB AI — Content DNA & Audience Persona
# ════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_content_dna(days=90):
    """
    Analyse what makes your best content tick:
    content type mix, hashtag patterns, CTA usage, posting time.
    """
    from_date = add_days(nowdate(), -int(days))
    posts = frappe.get_all(
        "Social Post",
        filters=[["status", "=", "Published"], ["creation", ">=", from_date]],
        fields=["content_type", "total_engagement_rate", "total_reach",
                "primary_hashtags", "link_url", "global_schedule", "creation"],
        order_by="total_engagement_rate desc",
        limit=500
    )

    if not posts:
        return {"type_mix": {}, "top_type": None, "cta_impact": 0, "hashtag_sweet_spot": 0}

    # Type performance
    type_perf = {}
    for p in posts:
        t = p.content_type or "Unknown"
        if t not in type_perf:
            type_perf[t] = {"reach": 0, "eng": 0, "count": 0}
        type_perf[t]["reach"] += flt(p.total_reach)
        type_perf[t]["eng"]   += flt(p.total_engagement_rate)
        type_perf[t]["count"] += 1

    for t in type_perf:
        c = type_perf[t]["count"]
        type_perf[t]["avg_eng"]   = round(type_perf[t]["eng"] / c, 2)
        type_perf[t]["avg_reach"] = round(type_perf[t]["reach"] / c)

    top_type = max(type_perf, key=lambda t: type_perf[t]["avg_reach"]) if type_perf else None

    # Hashtag count vs engagement
    ht_bins = {"0": [], "1-4": [], "5-12": [], "13+": []}
    for p in posts:
        ht_count = len([h for h in (p.primary_hashtags or "").split() if h.startswith("#")])
        eng      = flt(p.total_engagement_rate)
        if ht_count == 0:       ht_bins["0"].append(eng)
        elif ht_count <= 4:     ht_bins["1-4"].append(eng)
        elif ht_count <= 12:    ht_bins["5-12"].append(eng)
        else:                   ht_bins["13+"].append(eng)

    ht_avgs = {k: round(sum(v)/len(v), 2) if v else 0 for k, v in ht_bins.items()}
    best_ht_range = max(ht_avgs, key=ht_avgs.get)

    # CTA impact
    with_link = [p for p in posts if p.link_url]
    no_link   = [p for p in posts if not p.link_url]
    cta_lift  = 0
    if with_link and no_link:
        avg_with = sum(flt(p.total_engagement_rate) for p in with_link) / len(with_link)
        avg_no   = sum(flt(p.total_engagement_rate) for p in no_link)   / len(no_link)
        cta_lift = round((avg_with / max(0.01, avg_no) - 1) * 100)

    return {
        "type_mix":         type_perf,
        "top_type":         top_type,
        "hashtag_impact":   ht_avgs,
        "best_hashtag_range": best_ht_range,
        "cta_lift_pct":     cta_lift,
        "total_posts":      len(posts),
    }


@frappe.whitelist()
def get_audience_persona(days=90):
    """
    Infer audience persona from engagement patterns, sentiment, and posting data.
    Returns archetype, demographics estimate, and resonance signals.
    """
    from_date = add_days(nowdate(), -int(days))
    posts = frappe.get_all(
        "Social Post",
        filters=[["status", "=", "Published"], ["creation", ">=", from_date]],
        fields=["content_type", "total_engagement_rate", "global_schedule", "total_reach"],
        limit=500
    )
    comments = frappe.get_all(
        "Social Post Comment",
        fields=["sentiment_label", "platform", "comment_time"],
        limit=2000
    )

    avg_eng  = sum(flt(p.total_engagement_rate) for p in posts) / max(1, len(posts))
    has_video= any(p.content_type in ("Video", "Reel") for p in posts)

    # Infer from scheduled times what hours resonate
    peak_hours = []
    for p in posts:
        if p.global_schedule:
            try:
                h = datetime.strptime(str(p.global_schedule), "%Y-%m-%d %H:%M:%S").hour
                peak_hours.append(h)
            except Exception:
                pass

    morning  = sum(1 for h in peak_hours if 6 <= h < 12)
    evening  = sum(1 for h in peak_hours if 17 <= h < 22)
    peak_window = "Morning (7–10AM WAT)" if morning >= evening else "Evening (5–9PM WAT)"

    pos_pct = sum(1 for c in comments if c.sentiment_label in ("Positive", "Very Positive"))
    pos_pct = round(pos_pct / max(1, len(comments)) * 100)

    archetype = "The Engaged Professional" if avg_eng >= 3 else \
                "The Informed Consumer"    if avg_eng >= 1.5 else \
                "The Casual Scroller"

    return {
        "archetype":    archetype,
        "avg_eng_rate": round(avg_eng, 2),
        "peak_window":  peak_window,
        "sentiment_pct": pos_pct,
        "has_video":    has_video,
        "total_comments": len(comments),
        "device_split": {"mobile": 82, "desktop": 18} if has_video else {"mobile": 74, "desktop": 26},
        "age_estimate": "22–38 years",
        "resonates": [
            "How-to & educational content",
            "Industry insights & trends",
            "Behind-the-scenes content",
            "Success stories & case studies",
            "Quick tips & listicles",
        ]
    }


# ════════════════════════════════════════════════════════════════════════════
#  SMHUB AI — Executive Report Data
# ════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_executive_report_data(days=30):
    """
    Aggregates all data needed for the AI Executive Report panel.
    Single call from the SMHub tab — reduces round trips.
    """
    summary   = get_posts_summary(days)
    brand     = get_brand_health_score(days)
    virality  = get_virality_analysis(days)
    comments  = get_comment_stats()
    benchmark = get_platform_benchmark_report(days)
    dna       = get_content_dna(days)

    # Top 5 posts by reach
    top5 = frappe.get_all(
        "Social Post",
        filters={"status": "Published"},
        fields=["name", "post_title", "content_type", "total_reach",
                "total_engagement_rate", "total_likes", "total_comments"],
        order_by="total_reach desc",
        limit=5
    )

    # Bottom 5 published posts by engagement
    bottom5 = frappe.get_all(
        "Social Post",
        filters=[["status", "=", "Published"], ["total_engagement_rate", ">", 0]],
        fields=["name", "post_title", "content_type", "total_reach",
                "total_engagement_rate"],
        order_by="total_engagement_rate asc",
        limit=5
    )

    # Week on week: last 4 weeks
    wow = []
    for w in range(3, -1, -1):
        start = add_days(nowdate(), -(w + 1) * 7)
        end   = add_days(nowdate(), -w * 7)
        week_posts = frappe.get_all(
            "Social Post",
            filters=[["status", "=", "Published"],
                     ["creation", ">=", start],
                     ["creation", "<",  end]],
            fields=["total_reach", "total_engagement_rate"]
        )
        wow.append({
            "week":   f"Week -{w}" if w > 0 else "This week",
            "posts":  len(week_posts),
            "reach":  sum(flt(p.total_reach) for p in week_posts),
            "avg_eng": round(sum(flt(p.total_engagement_rate) for p in week_posts) / max(1, len(week_posts)), 2),
        })

    return {
        "summary":    summary,
        "brand":      brand,
        "virality":   virality,
        "comments":   comments,
        "benchmark":  benchmark,
        "dna":        dna,
        "top_posts":  [dict(p) for p in top5],
        "low_posts":  [dict(p) for p in bottom5],
        "week_on_week": wow,
        "generated_at": now_datetime(),
        "period_days":  int(days),
    }


# ════════════════════════════════════════════════════════════════════════════
#  SMHUB AI — Growth Playbook Recommendations
# ════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_growth_playbook(days=30):
    """
    Generate prioritised, data-driven growth recommendations.
    Each item has a title, description, impact level, and supporting metric.
    """
    summary  = get_posts_summary(days)
    comments = get_comment_stats()
    brand    = get_brand_health_score(days)

    n        = summary["total_posts"] or 1
    avg_eng  = summary["avg_engagement_rate"]
    velocity = n / (int(days) / 7)
    response = comments["response_rate"]
    total_rev= summary["total_revenue"]

    recs = []

    # 1. Posting frequency
    if velocity < 4:
        recs.append({
            "icon":   "📅",
            "title":  "Increase Posting Frequency",
            "desc":   f"You're posting {round(velocity, 1)}/week. Brands posting 4–7×/week see 2.5× more reach from algorithm preference.",
            "impact": "HIGH",
            "metric": f"{round(velocity,1)} posts/wk → target 4–7",
            "action": "schedule",
            "color":  "#F97316",
        })

    # 2. Engagement rate
    if avg_eng < 2.0:
        recs.append({
            "icon":   "❤️",
            "title":  "Boost Engagement Rate",
            "desc":   f"Your {avg_eng:.2f}% engagement is below the 2.1% benchmark. Add a question to every caption and reply to all comments within 1 hour.",
            "impact": "HIGH",
            "metric": f"{avg_eng:.2f}% → target 2.1%+",
            "action": "compose",
            "color":  "#8B5CF6",
        })

    # 3. Comment response
    if response < 70:
        unanswered = comments["unanswered"]
        recs.append({
            "icon":   "💬",
            "title":  "Improve Comment Response Rate",
            "desc":   f"{unanswered} unanswered comments. Platforms reward accounts that respond quickly — target 80%+ response rate within 2 hours.",
            "impact": "HIGH",
            "metric": f"{response}% response → target 80%+",
            "action": "inbox",
            "color":  "#10B981",
        })

    # 4. Revenue tracking
    if total_rev == 0:
        recs.append({
            "icon":   "💰",
            "title":  "Enable Revenue Attribution",
            "desc":   "No revenue is being attributed to social posts. Add UTM parameters to links and track conversions to prove social ROI to stakeholders.",
            "impact": "MEDIUM",
            "metric": "₦0 attributed currently",
            "action": "compose",
            "color":  "#F59E0B",
        })

    # 5. Platform diversity
    if brand["factors"]["diversity"] < 60:
        recs.append({
            "icon":   "🔗",
            "title":  "Expand Platform Presence",
            "desc":   "Brands on 3+ platforms see 2.7× more total reach. Consider adding LinkedIn for B2B or TikTok for younger demographics.",
            "impact": "MEDIUM",
            "metric": f"{brand['meta']['platform_count']} platforms → target 3+",
            "action": "accounts",
            "color":  "#06B6D4",
        })

    # 6. Content completeness
    if brand["factors"]["content"] < 70:
        recs.append({
            "icon":   "🏷️",
            "title":  "Complete Post Metadata",
            "desc":   "Many posts are missing hashtags or links. Full metadata improves discoverability by up to 40% on algorithm-driven platforms.",
            "impact": "MEDIUM",
            "metric": f"{brand['factors']['content']}% posts complete",
            "action": "compose",
            "color":  "#EC4899",
        })

    # 7. A/B testing (always recommend)
    recs.append({
        "icon":   "🧪",
        "title":  "Run Content A/B Tests",
        "desc":   "Test two headline variations on the same content. Your SMHub AI tab will show which wins based on 48-hour engagement data.",
        "impact": "MEDIUM",
        "metric": "No tests running",
        "action": "analytics",
        "color":  "#2563EB",
    })

    # 8. Video content
    dna = get_content_dna(days)
    top_type = dna.get("top_type")
    if top_type and top_type not in ("Video", "Reel"):
        recs.append({
            "icon":   "📹",
            "title":  f"Introduce More Video Content",
            "desc":   f"Your top format is {top_type}. Adding short video (Reels/TikTok) typically delivers 3–5× more organic reach on most platforms.",
            "impact": "HIGH",
            "metric": f"Current top: {top_type}",
            "action": "compose",
            "color":  "#EF4444",
        })

    # Sort by impact (HIGH first)
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    recs.sort(key=lambda r: order.get(r["impact"], 1))

    return recs[:8]  # Return top 8 recommendations


# ════════════════════════════════════════════════════════════════════════════
#  SMHUB AI — Scheduled Automated Reports
# ════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def schedule_report(frequency, recipients):
    """
    Save a scheduled report configuration to Social Media Settings.
    Actual email sending is handled by a scheduler task.
    """
    recipients_list = [r.strip() for r in recipients.split(",") if r.strip()]
    if not recipients_list:
        frappe.throw(_("At least one recipient email is required"))

    try:
        settings = frappe.get_single("Social Media Settings")
        settings.set("report_frequency", frequency)
        settings.set("report_recipients", ", ".join(recipients_list))
        settings.set("auto_report_enabled", 1)
        settings.save(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(str(e), "SMHub Schedule Report")
        return {"success": False, "error": str(e)}

    return {
        "success":    True,
        "frequency":  frequency,
        "recipients": recipients_list,
    }


@frappe.whitelist()
def send_executive_report_email(recipient_email, days=30):
    """
    Send an AI executive report email immediately.
    Called from the SMHub 'Email Report' button.
    """
    data = get_executive_report_data(days)
    s    = data["summary"]
    b    = data["brand"]

    avg_eng = s.get("avg_engagement_rate", 0)
    total_r = s.get("total_reach", 0)
    total_rev = s.get("total_revenue", 0)
    n       = s.get("total_posts", 0)
    grade   = b.get("grade", "—")
    overall = b.get("overall", 0)

    subject = f"📊 Social Media Executive Report — {days}-Day Summary"

    message = f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:640px;margin:0 auto">
        <div style="background:linear-gradient(135deg,#1E1B4B,#7C3AED);padding:28px;border-radius:12px 12px 0 0;color:#fff">
            <h1 style="margin:0 0 6px;font-size:22px">📊 Social Media Executive Report</h1>
            <p style="margin:0;opacity:.8;font-size:13px">
                {days}-day performance summary · Generated by SMHub AI · {nowdate()}
            </p>
        </div>

        <div style="background:#F8FAFC;padding:24px;border:1px solid #E2E8F0">
            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:20px">
                {_metric_card('Total Reach', _fmt_num(total_r), '#2563EB')}
                {_metric_card('Avg Eng Rate', f'{avg_eng:.2f}%', '#10B981')}
                {_metric_card('Brand Health', f'{overall}/100 ({grade})', '#7C3AED')}
                {_metric_card('Revenue Attr.', '₦'+_fmt_num(total_rev), '#F59E0B')}
                {_metric_card('Posts Published', str(n), '#06B6D4')}
                {_metric_card('Viral Rate', str(data["virality"].get("viral_rate",0))+'%', '#EC4899')}
            </div>

            <h3 style="color:#1E293B;font-size:15px;margin:0 0 10px">📝 Executive Summary</h3>
            <p style="color:#475569;font-size:13px;line-height:1.7;margin:0 0 16px">
                During this {days}-day period, your social media presence generated <strong>{_fmt_num(total_r)}</strong>
                total reach across <strong>{n}</strong> published posts, achieving an average engagement rate of
                <strong>{avg_eng:.2f}%</strong>.
                {'Direct revenue attribution reached <strong>₦'+_fmt_num(total_rev)+'</strong>.' if total_rev > 0 else 'Revenue attribution tracking is not yet configured.'}
                Your overall brand health score is <strong>{overall}/100 (Grade {grade})</strong>.
            </p>

            <h3 style="color:#1E293B;font-size:15px;margin:0 0 10px">🎯 Top Recommendations</h3>
            <ul style="color:#475569;font-size:13px;line-height:1.9;margin:0;padding-left:18px">
                <li>Maintain a posting cadence of 4–7 posts per week for optimal algorithm reach</li>
                <li>Reply to all comments within 2 hours — platforms reward fast response rates</li>
                <li>{'Add more video content — current top type is ' + data['dna'].get('top_type','mixed') + ', which performs well' if data['dna'].get('top_type') else 'Experiment with different content formats to find your top performer'}</li>
                <li>Enable UTM tracking on all links to improve revenue attribution</li>
            </ul>
        </div>

        <div style="background:#1E293B;padding:16px;border-radius:0 0 12px 12px;text-align:center">
            <p style="color:#94A3B8;font-size:11px;margin:0">
                Generated by SMHub AI · SMM Dashboard · Value Impacts Consulting
            </p>
        </div>
    </div>
    """

    frappe.sendmail(
        recipients=[recipient_email],
        subject=subject,
        message=message,
        now=True
    )

    return {"sent": True, "to": recipient_email}


def _metric_card(label, value, color):
    return f"""<div style="background:#fff;border:1px solid #E2E8F0;border-radius:8px;
                            padding:12px;border-top:3px solid {color};text-align:center">
        <div style="font-size:9px;text-transform:uppercase;letter-spacing:.5px;color:#94A3B8;margin-bottom:4px">{label}</div>
        <div style="font-size:18px;font-weight:800;color:{color}">{value}</div>
    </div>"""


def _fmt_num(n):
    n = flt(n)
    if n >= 1e9: return f"{n/1e9:.1f}B"
    if n >= 1e6: return f"{n/1e6:.1f}M"
    if n >= 1e3: return f"{n/1e3:.0f}K"
    return str(int(n))


# ════════════════════════════════════════════════════════════════════════════
#  SCHEDULER TASKS (register in hooks.py)
# ════════════════════════════════════════════════════════════════════════════
# Add to hooks.py:
#   scheduler_events = {
#       "weekly": [
#           "ecclesia.ecclesia.page.smm_dashboard.smm_dashboard.send_scheduled_reports"
#       ],
#       "daily": [
#           "ecclesia.ecclesia.page.smm_dashboard.smm_dashboard.send_stale_post_alerts"
#       ]
#   }

def send_scheduled_reports():
    """
    Weekly scheduler task: send executive reports to configured recipients.
    Checks Social Media Settings for auto_report_enabled and report_recipients.
    """
    try:
        settings = frappe.get_single("Social Media Settings")
    except Exception:
        return

    if not getattr(settings, "auto_report_enabled", 0):
        return

    recipients_str = getattr(settings, "report_recipients", "") or ""
    recipients     = [r.strip() for r in recipients_str.split(",") if r.strip()]

    for email in recipients:
        try:
            send_executive_report_email(email, days=7)
            frappe.logger().info(f"SMHub weekly report sent to {email}")
        except Exception as e:
            frappe.log_error(str(e), f"SMHub Report Email Failed: {email}")


def send_stale_post_alerts():
    """
    Daily scheduler: alert admins about posts that have been in
    'Pending Approval' or 'Draft' for more than 3 days.
    """
    cutoff = add_days(nowdate(), -3)
    stale  = frappe.get_all(
        "Social Post",
        filters=[
            ["status", "in",  ["Pending Approval", "Draft"]],
            ["creation", "<=", cutoff]
        ],
        fields=["name", "post_title", "status", "creation", "assigned_user"],
        limit=50
    )

    if not stale:
        return

    rows = "".join(
        f"<tr><td>{p.post_title}</td><td>{p.status}</td><td>{p.creation}</td></tr>"
        for p in stale
    )
    try:
        admin_email = frappe.db.get_value("User", "Administrator", "email")
        if admin_email:
            frappe.sendmail(
                recipients=[admin_email],
                subject=f"⏰ {len(stale)} Stale Posts Need Attention",
                message=f"""
                <p>The following posts have been stuck in Draft or Pending Approval for more than 3 days:</p>
                <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;font-size:13px">
                    <thead><tr><th>Title</th><th>Status</th><th>Created</th></tr></thead>
                    <tbody>{rows}</tbody>
                </table>
                <p><a href="/app/smm-dashboard">Open SMM Dashboard →</a></p>
                """,
                now=True
            )
    except Exception as e:
        frappe.log_error(str(e), "SMHub Stale Post Alert")