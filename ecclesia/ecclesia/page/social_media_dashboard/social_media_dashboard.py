# Copyright (c) 2026, Value Impacts Consulting
# ecclesia/ecclesia/page/smm_dashboard/smm_dashboard.py
#
# Whitelisted server-side API methods for the Social Media Studio page.
# Called from JS via: frappe.call('ecclesia.ecclesia.page.smm_dashboard.smm_dashboard.<method>')

import frappe
from frappe import _
from frappe.utils import nowdate, add_days, flt, cint, now_datetime
import json
import calendar


# ═══════════════════════════════════════════════════════════════════════════
#  THEME REGISTRY — Pure Code, No Database Storage
# ═══════════════════════════════════════════════════════════════════════════

SMM_THEMES = {
    "nova": {
        "name": "Nova", "icon": "🌟", "isDark": False,
        "colors": {
            "bg": "#FAF5FF", "bg2": "#F5F3FF", "bg3": "#EDE9FE", "card": "#FFFFFF",
            "brd": "#E9D5FF", "brd2": "#D8B4FE",
            "tx1": "#2E1065", "tx2": "#5B21B6", "tx3": "#A78BFA",
            "pri": "#7C3AED", "pri_d": "#6D28D9", "pri2": "#A78BFA",
            "pri_x": "rgba(124,58,237,.09)",
            "acc": "#A78BFA", "acc_x": "rgba(167,139,250,.12)",
            "grn": "#10B981", "grn_x": "rgba(16,185,129,.09)",
            "red": "#EF4444", "red_x": "rgba(239,68,68,.09)",
            "amb": "#F59E0B", "amb_x": "rgba(245,158,11,.09)",
            "sky": "#06B6D4", "sky_x": "rgba(6,182,212,.09)",
            "pink": "#EC4899", "pink_x": "rgba(236,72,153,.09)",
            "banner": "linear-gradient(135deg,#1E1B4B 0%,#4C1D95 40%,#7C3AED 70%,#EC4899 100%)"
        }
    },
    "ocean": {
        "name": "Ocean", "icon": "🌊", "isDark": False,
        "colors": {
            "bg": "#F0F9FF", "bg2": "#E0F2FE", "bg3": "#BAE6FD", "card": "#FFFFFF",
            "brd": "#BAE6FD", "brd2": "#7DD3FC",
            "tx1": "#0C4A6E", "tx2": "#075985", "tx3": "#7DD3FC",
            "pri": "#0EA5E9", "pri_d": "#0284C7", "pri2": "#38BDF8",
            "pri_x": "rgba(14,165,233,.09)",
            "acc": "#38BDF8", "acc_x": "rgba(56,189,248,.12)",
            "grn": "#10B981", "grn_x": "rgba(16,185,129,.09)",
            "red": "#F43F5E", "red_x": "rgba(244,63,94,.09)",
            "amb": "#F59E0B", "amb_x": "rgba(245,158,11,.09)",
            "sky": "#06B6D4", "sky_x": "rgba(6,182,212,.09)",
            "pink": "#EC4899", "pink_x": "rgba(236,72,153,.09)",
            "banner": "linear-gradient(135deg,#0C4A6E 0%,#0369A1 40%,#0EA5E9 70%,#06B6D4 100%)"
        }
    },
    "ember": {
        "name": "Ember", "icon": "🔥", "isDark": False,
        "colors": {
            "bg": "#FFF7ED", "bg2": "#FFEDD5", "bg3": "#FED7AA", "card": "#FFFFFF",
            "brd": "#FED7AA", "brd2": "#FDBA74",
            "tx1": "#431407", "tx2": "#9A3412", "tx3": "#FDBA74",
            "pri": "#F97316", "pri_d": "#EA580C", "pri2": "#FB923C",
            "pri_x": "rgba(249,115,22,.09)",
            "acc": "#FB923C", "acc_x": "rgba(251,146,60,.12)",
            "grn": "#22C55E", "grn_x": "rgba(34,197,94,.09)",
            "red": "#EF4444", "red_x": "rgba(239,68,68,.09)",
            "amb": "#EAB308", "amb_x": "rgba(234,179,8,.09)",
            "sky": "#0EA5E9", "sky_x": "rgba(14,165,233,.09)",
            "pink": "#EC4899", "pink_x": "rgba(236,72,153,.09)",
            "banner": "linear-gradient(135deg,#431407 0%,#C2410C 40%,#F97316 70%,#EAB308 100%)"
        }
    },
    "midnight": {
        "name": "Midnight", "icon": "🌙", "isDark": True,
        "colors": {
            "bg": "#0F172A", "bg2": "#1E293B", "bg3": "#334155", "card": "#1E293B",
            "brd": "rgba(255,255,255,.08)", "brd2": "rgba(255,255,255,.14)",
            "tx1": "#F1F5F9", "tx2": "#94A3B8", "tx3": "#475569",
            "pri": "#818CF8", "pri_d": "#6366F1", "pri2": "#A5B4FC",
            "pri_x": "rgba(129,140,248,.12)",
            "acc": "#A5B4FC", "acc_x": "rgba(165,180,252,.12)",
            "grn": "#34D399", "grn_x": "rgba(52,211,153,.12)",
            "red": "#F87171", "red_x": "rgba(248,113,113,.12)",
            "amb": "#FCD34D", "amb_x": "rgba(252,211,77,.12)",
            "sky": "#38BDF8", "sky_x": "rgba(56,189,248,.12)",
            "pink": "#F9A8D4", "pink_x": "rgba(249,168,212,.12)",
            "banner": "linear-gradient(135deg,#020617 0%,#0F172A 50%,#1E3A5F 70%,#312E81 100%)"
        }
    },
    "verdant": {
        "name": "Verdant", "icon": "🌿", "isDark": False,
        "colors": {
            "bg": "#ECFDF5", "bg2": "#D1FAE5", "bg3": "#A7F3D0", "card": "#FFFFFF",
            "brd": "#A7F3D0", "brd2": "#6EE7B7",
            "tx1": "#022C22", "tx2": "#065F46", "tx3": "#6EE7B7",
            "pri": "#059669", "pri_d": "#047857", "pri2": "#34D399",
            "pri_x": "rgba(5,150,105,.09)",
            "acc": "#34D399", "acc_x": "rgba(52,211,153,.12)",
            "grn": "#10B981", "grn_x": "rgba(16,185,129,.09)",
            "red": "#EF4444", "red_x": "rgba(239,68,68,.09)",
            "amb": "#F59E0B", "amb_x": "rgba(245,158,11,.09)",
            "sky": "#0EA5E9", "sky_x": "rgba(14,165,233,.09)",
            "pink": "#EC4899", "pink_x": "rgba(236,72,153,.09)",
            "banner": "linear-gradient(135deg,#022C22 0%,#047857 40%,#059669 70%,#10B981 100%)"
        }
    },
    "sunset": {
        "name": "Sunset", "icon": "🌅", "isDark": False,
        "colors": {
            "bg": "#FFF1F2", "bg2": "#FFE4E6", "bg3": "#FECDD3", "card": "#FFFFFF",
            "brd": "#FECDD3", "brd2": "#FDA4AF",
            "tx1": "#4C0519", "tx2": "#881337", "tx3": "#FDA4AF",
            "pri": "#DC2626", "pri_d": "#B91C1C", "pri2": "#F87171",
            "pri_x": "rgba(220,38,38,.09)",
            "acc": "#F87171", "acc_x": "rgba(248,113,113,.12)",
            "grn": "#10B981", "grn_x": "rgba(16,185,129,.09)",
            "red": "#EF4444", "red_x": "rgba(239,68,68,.09)",
            "amb": "#F59E0B", "amb_x": "rgba(245,158,11,.09)",
            "sky": "#06B6D4", "sky_x": "rgba(6,182,212,.09)",
            "pink": "#EC4899", "pink_x": "rgba(236,72,153,.09)",
            "banner": "linear-gradient(135deg,#4C0519 0%,#881337 40%,#DC2626 70%,#F59E0B 100%)"
        }
    },
    "arctic": {
        "name": "Arctic", "icon": "❄️", "isDark": False,
        "colors": {
            "bg": "#F8FAFC", "bg2": "#F1F5F9", "bg3": "#E2E8F0", "card": "#FFFFFF",
            "brd": "#E2E8F0", "brd2": "#CBD5E1",
            "tx1": "#0F172A", "tx2": "#334155", "tx3": "#94A3B8",
            "pri": "#0284C7", "pri_d": "#0369A1", "pri2": "#7DD3FC",
            "pri_x": "rgba(2,132,199,.09)",
            "acc": "#7DD3FC", "acc_x": "rgba(125,211,252,.12)",
            "grn": "#10B981", "grn_x": "rgba(16,185,129,.09)",
            "red": "#EF4444", "red_x": "rgba(239,68,68,.09)",
            "amb": "#F59E0B", "amb_x": "rgba(245,158,11,.09)",
            "sky": "#06B6D4", "sky_x": "rgba(6,182,212,.09)",
            "pink": "#EC4899", "pink_x": "rgba(236,72,153,.09)",
            "banner": "linear-gradient(135deg,#0F172A 0%,#1E3A5F 40%,#0284C7 70%,#06B6D4 100%)"
        }
    },
    "forest": {
        "name": "Forest", "icon": "🌲", "isDark": True,
        "colors": {
            "bg": "#052E16", "bg2": "#14532D", "bg3": "#166534", "card": "#14532D",
            "brd": "rgba(187,247,208,.1)", "brd2": "rgba(134,239,172,.18)",
            "tx1": "#F0FDF4", "tx2": "#86EFAC", "tx3": "#4ADE80",
            "pri": "#22C55E", "pri_d": "#16A34A", "pri2": "#4ADE80",
            "pri_x": "rgba(34,197,94,.12)",
            "acc": "#4ADE80", "acc_x": "rgba(74,222,128,.12)",
            "grn": "#22C55E", "grn_x": "rgba(34,197,94,.12)",
            "red": "#F87171", "red_x": "rgba(248,113,113,.12)",
            "amb": "#FBBF24", "amb_x": "rgba(251,191,36,.12)",
            "sky": "#38BDF8", "sky_x": "rgba(56,189,248,.12)",
            "pink": "#F472B6", "pink_x": "rgba(244,114,182,.12)",
            "banner": "linear-gradient(135deg,#052E16 0%,#14532D 40%,#166534 70%,#22C55E 100%)"
        }
    },
    "candy": {
        "name": "Candy", "icon": "🍬", "isDark": False,
        "colors": {
            "bg": "#FDF2F8", "bg2": "#FCE7F3", "bg3": "#FBCFE8", "card": "#FFFFFF",
            "brd": "#FBCFE8", "brd2": "#F9A8D4",
            "tx1": "#500724", "tx2": "#831843", "tx3": "#F9A8D4",
            "pri": "#DB2777", "pri_d": "#BE185D", "pri2": "#F472B6",
            "pri_x": "rgba(219,39,119,.09)",
            "acc": "#F472B6", "acc_x": "rgba(244,114,182,.12)",
            "grn": "#10B981", "grn_x": "rgba(16,185,129,.09)",
            "red": "#EF4444", "red_x": "rgba(239,68,68,.09)",
            "amb": "#F59E0B", "amb_x": "rgba(245,158,11,.09)",
            "sky": "#06B6D4", "sky_x": "rgba(6,182,212,.09)",
            "pink": "#EC4899", "pink_x": "rgba(236,72,153,.09)",
            "banner": "linear-gradient(135deg,#500724 0%,#831843 40%,#DB2777 70%,#EC4899 100%)"
        }
    }
}


@frappe.whitelist(allow_guest=True)
def get_themes():
    """Return all available themes — pure code, no DB dependency."""
    themes = {}
    for key, theme in SMM_THEMES.items():
        themes[key] = {
            "name": theme["name"],
            "icon": theme["icon"],
            "isDark": theme["isDark"],
            "preview_colors": {
                "primary": theme["colors"]["pri"],
                "accent": theme["colors"]["acc"],
                "background": theme["colors"]["bg"]
            }
        }
    return themes


@frappe.whitelist(allow_guest=True)
def get_theme(key="midnight"):
    """Return a specific theme by key — no DB query."""
    theme = SMM_THEMES.get(key, SMM_THEMES["midnight"])
    return {
        "key": key,
        "name": theme["name"],
        "icon": theme["icon"],
        "isDark": theme["isDark"],
        "colors": theme["colors"]
    }


# ─── OVERVIEW / SUMMARY ──────────────────────────────────────────────────────

@frappe.whitelist()
def get_dashboard_summary():
    """Aggregate KPIs for the overview panel."""
    posts = frappe.get_all(
        "Social Post",
        fields=[
            "name", "status", "content_type", "total_reach", "total_likes",
            "total_comments", "total_shares", "total_clicks", "total_conversions",
            "total_engagement_rate", "revenue_generated", "roi_percentage",
            "creation", "global_schedule", "campaign"
        ],
        limit=1000,
        order_by="modified desc"
    )

    total_reach      = sum(flt(p.total_reach) for p in posts)
    total_likes      = sum(flt(p.total_likes) for p in posts)
    total_comments   = sum(flt(p.total_comments) for p in posts)
    total_shares     = sum(flt(p.total_shares) for p in posts)
    total_clicks     = sum(flt(p.total_clicks) for p in posts)
    total_conversions= sum(flt(p.total_conversions) for p in posts)
    total_revenue    = sum(flt(p.revenue_generated) for p in posts)
    published_count  = len([p for p in posts if p.status == "Published"])
    scheduled_count  = len([p for p in posts if p.status == "Scheduled"])
    draft_count      = len([p for p in posts if p.status in ("Draft", "Pending Approval")])
    failed_count     = len([p for p in posts if p.status == "Failed"])

    eng_posts   = [p for p in posts if flt(p.total_engagement_rate) > 0]
    avg_eng_rate= (sum(flt(p.total_engagement_rate) for p in eng_posts) / len(eng_posts)) if eng_posts else 0

    # Count active platforms from Social Media Settings child table
    active_platforms = 0
    try:
        settings = frappe.get_single("Social Media Settings")
        active_platforms = len([a for a in (settings.platform_accounts or []) if a.is_active])
    except Exception:
        pass

    return {
        "total_reach":       total_reach,
        "total_engagements": total_likes + total_comments + total_shares,
        "total_likes":       total_likes,
        "total_comments":    total_comments,
        "total_shares":      total_shares,
        "total_clicks":      total_clicks,
        "total_conversions": total_conversions,
        "total_revenue":     total_revenue,
        "avg_engagement_rate": round(avg_eng_rate, 2),
        "published_count":   published_count,
        "scheduled_count":   scheduled_count,
        "draft_count":       draft_count,
        "failed_count":      failed_count,
        "active_platforms":  active_platforms,
        "total_posts":       len(posts),
    }


# ─── PERFORMANCE OVER TIME ────────────────────────────────────────────────────

@frappe.whitelist()
def get_performance_trend(days=30):
    """Daily reach + engagement for the last N days."""
    days   = cint(days)
    result = []
    for i in range(days - 1, -1, -1):
        date = add_days(nowdate(), -i)
        day_posts = frappe.get_all(
            "Social Post",
            filters=[["global_schedule", "like", f"{date}%"]],
            fields=["total_reach", "total_likes", "total_comments", "total_shares", "total_clicks"]
        )
        result.append({
            "date":        date,
            "posts":       len(day_posts),
            "reach":       sum(flt(p.total_reach) for p in day_posts),
            "engagements": sum(flt(p.total_likes) + flt(p.total_comments) + flt(p.total_shares) for p in day_posts),
            "clicks":      sum(flt(p.total_clicks) for p in day_posts),
        })
    return result


# ─── PLATFORM BREAKDOWN ───────────────────────────────────────────────────────

@frappe.whitelist()
def get_platform_performance():
    """Per-platform aggregated performance from Social Platform Performance child table."""
    rows = frappe.get_all(
        "Social Platform Performance",
        fields=["platform", "account_name", "likes", "comments", "shares", "reach", "views", "clicks", "engagement_rate", "sentiment_score"],
        limit=500
    )

    summary = {}
    for r in rows:
        plat = r.platform or "Other"
        if plat not in summary:
            summary[plat] = {"platform": plat, "likes": 0, "comments": 0, "shares": 0,
                             "reach": 0, "views": 0, "clicks": 0, "posts": 0}
        summary[plat]["likes"]    += flt(r.likes)
        summary[plat]["comments"] += flt(r.comments)
        summary[plat]["shares"]   += flt(r.shares)
        summary[plat]["reach"]    += flt(r.reach)
        summary[plat]["views"]    += flt(r.views)
        summary[plat]["clicks"]   += flt(r.clicks)
        summary[plat]["posts"]    += 1

    return sorted(summary.values(), key=lambda x: x["reach"], reverse=True)


# ─── CONTENT TYPE ANALYSIS ────────────────────────────────────────────────────

@frappe.whitelist()
def get_content_type_performance():
    """Reach, engagement, and ROI grouped by content type."""
    posts = frappe.get_all(
        "Social Post",
        filters={"status": "Published"},
        fields=["content_type", "total_reach", "total_likes", "total_comments",
                "total_shares", "revenue_generated", "roi_percentage"]
    )
    summary = {}
    for p in posts:
        ct = p.content_type or "Other"
        if ct not in summary:
            summary[ct] = {"content_type": ct, "reach": 0, "engagements": 0,
                           "revenue": 0, "count": 0, "roi": 0}
        summary[ct]["reach"]       += flt(p.total_reach)
        summary[ct]["engagements"] += flt(p.total_likes) + flt(p.total_comments) + flt(p.total_shares)
        summary[ct]["revenue"]     += flt(p.revenue_generated)
        summary[ct]["roi"]         += flt(p.roi_percentage)
        summary[ct]["count"]       += 1

    for ct in summary:
        if summary[ct]["count"] > 0:
            summary[ct]["avg_roi"] = round(summary[ct]["roi"] / summary[ct]["count"], 2)

    return sorted(summary.values(), key=lambda x: x["reach"], reverse=True)


# ─── COMMENT ANALYTICS ────────────────────────────────────────────────────────

@frappe.whitelist()
def get_comment_summary():
    """Unanswered count, sentiment breakdown, platform distribution."""
    comments = frappe.get_all(
        "Social Post Comment",
        fields=["platform", "reply_status", "sentiment_score", "comment_time", "sentiment_label", "status", "is_flagged", "author_name", "comment_text"],
        limit=2000,
        order_by="comment_time desc"
    )
    total      = len(comments)
    unanswered = len([c for c in comments if not c.reply_status or c.reply_status == "Unanswered"])
    positive   = len([c for c in comments if flt(c.sentiment_score) >  0.3])
    negative   = len([c for c in comments if flt(c.sentiment_score) < -0.3])
    neutral    = total - positive - negative

    by_platform = {}
    for c in comments:
        p = c.platform or "Other"
        by_platform[p] = by_platform.get(p, 0) + 1

    return {
        "total":       total,
        "unanswered":  unanswered,
        "positive":    positive,
        "neutral":     neutral,
        "negative":    negative,
        "by_platform": by_platform,
    }


# ─── SCHEDULED POSTS FOR CALENDAR ─────────────────────────────────────────────

@frappe.whitelist()
def get_calendar_posts(year, month):
    """All posts scheduled in a given year+month."""
    year  = cint(year)
    month = cint(month)
    from_date = f"{year}-{str(month).zfill(2)}-01"
    last_day = calendar.monthrange(year, month)[1]
    to_date  = f"{year}-{str(month).zfill(2)}-{last_day}"

    posts = frappe.get_all(
        "Social Post",
        filters=[
            ["global_schedule", ">=", from_date],
            ["global_schedule", "<=", to_date + " 23:59:59"],
        ],
        fields=["name", "post_title", "status", "content_type", "global_schedule", "campaign"],
        order_by="global_schedule asc"
    )
    return posts


# ─── TOP PERFORMERS ───────────────────────────────────────────────────────────

@frappe.whitelist()
def get_top_posts(limit=10, metric="total_reach"):
    """Top N published posts by a given metric."""
    allowed_metrics = ["total_reach", "total_likes", "total_comments",
                       "total_shares", "total_clicks", "revenue_generated", "roi_percentage"]
    if metric not in allowed_metrics:
        metric = "total_reach"

    return frappe.get_all(
        "Social Post",
        filters={"status": "Published"},
        fields=["name", "post_title", "content_type", "total_reach", "total_likes",
                "total_comments", "total_shares", "revenue_generated", "roi_percentage",
                "total_engagement_rate", "global_schedule"],
        order_by=f"{metric} desc",
        limit=cint(limit)
    )


# ─── TOKEN EXPIRY ALERTS ──────────────────────────────────────────────────────

@frappe.whitelist()
def get_expiring_tokens(days_ahead=7):
    """
    Platform accounts with token expiry within N days.
    Since Social Media Platform Account is a child table of Social Media Settings,
    we query through the parent doc.
    """
    threshold = add_days(nowdate(), cint(days_ahead))
    
    try:
        settings = frappe.get_single("Social Media Settings")
    except Exception:
        return []
    
    expiring = []
    for acc in (settings.platform_accounts or []):
        if (acc.token_expiry_date and 
            str(acc.token_expiry_date) <= str(threshold) and 
            acc.is_active):
            days_remaining = frappe.utils.date_diff(str(acc.token_expiry_date), str(nowdate()))
            expiring.append({
                "name": acc.name,
                "platform": acc.platform,
                "account_name": acc.account_name,
                "token_expiry_date": str(acc.token_expiry_date),
                "days_remaining": days_remaining,
                "is_expired": days_remaining <= 0,
            })
    
    expiring.sort(key=lambda x: x["days_remaining"])
    return expiring


# ─── AI CONTENT SCORE ─────────────────────────────────────────────────────────

@frappe.whitelist()
def score_post_content(post_name):
    """
    Simple heuristic content quality score (0-100) for a Social Post.
    Scores: hook presence, CTA, hashtags, caption length, media attached.
    """
    try:
        post = frappe.get_doc("Social Post", post_name)
    except frappe.DoesNotExistError:
        return {"error": "Post not found", "score": 0, "grade": "N/A", "breakdown": {}, "suggestion": []}

    content = frappe.utils.strip_html(post.content or "")
    hashtags = (post.primary_hashtags or "").split()
    has_media = bool(frappe.get_all("Social Post Media", filters={"parent": post_name}, limit=1))
    
    score = 0
    breakdown = {}

    # Hook strength (0-20)
    hook_words = ["how", "why", "what", "did you know", "breaking", "secret", "free", "new"]
    has_hook = any(content.lower().startswith(w) or content.lower()[:40].find(w) >= 0 for w in hook_words) or "?" in content
    hook_score = 20 if has_hook else 8
    score += hook_score
    breakdown["hook"] = hook_score

    # CTA presence (0-15)
    cta_words = ["click", "buy", "shop", "learn", "discover", "get", "dm", "link in bio", "comment", "share", "subscribe", "download", "sign up", "register", "visit"]
    has_cta = any(w in content.lower() for w in cta_words)
    cta_score = 15 if has_cta else 5
    score += cta_score
    breakdown["cta"] = cta_score

    # Hashtags (0-20) — sweet spot 8-12
    htag_count = len([h for h in hashtags if h.startswith("#")])
    htag_score = min(20, max(0, 20 - abs(htag_count - 10) * 2))
    score += htag_score
    breakdown["hashtags"] = htag_score

    # Caption length (0-25)
    content_len = len(content)
    if 100 <= content_len <= 300:
        len_score = 25
    elif 50 <= content_len <= 500:
        len_score = 15
    else:
        len_score = 5
    score += len_score
    breakdown["length"] = len_score

    # Media attached (0-25)
    media_score = 25 if has_media else 8
    score += media_score
    breakdown["media"] = media_score

    final_score = min(100, score)
    grade = "A+" if final_score >= 85 else "A" if final_score >= 75 else "B+" if final_score >= 65 else "B" if final_score >= 55 else "C" if final_score >= 40 else "D"

    suggestions = []
    if hook_score < 15: suggestions.append("Start with a compelling question or power word to boost hook strength.")
    if cta_score < 10: suggestions.append("Add a clear call-to-action (e.g. 'Click the link in bio' or 'DM us now').")
    if htag_score < 15: suggestions.append("Use 8–12 targeted hashtags for optimal reach.")
    if media_score < 20: suggestions.append("Attach an image or video — posts with media get 3× more engagement.")
    if len_score < 15: suggestions.append("Caption length is outside optimal range (100–300 characters).")
    if not suggestions: suggestions.append("Content looks strong! Consider A/B testing with a different hook.")

    # Persist score back to post
    try:
        frappe.db.set_value("Social Post", post_name, "ai_recommendations", "\n".join(suggestions[:5]))
        frappe.db.commit()
    except Exception:
        pass

    return {
        "score": final_score,
        "grade": grade,
        "breakdown": breakdown,
        "suggestions": suggestions,
        "suggestion": suggestions[:5]
    }


# ─── BULK OPERATIONS ──────────────────────────────────────────────────────────

@frappe.whitelist()
def bulk_schedule(post_names, schedule_datetime):
    """Bulk-set schedule datetime on multiple posts."""
    if isinstance(post_names, str):
        post_names = json.loads(post_names)

    updated = 0
    for name in post_names:
        frappe.db.set_value("Social Post", name, {
            "global_schedule": schedule_datetime,
            "publish_strategy": "Schedule Global",
            "status": "Scheduled"
        })
        updated += 1

    frappe.db.commit()
    return {"updated": updated}


@frappe.whitelist()
def bulk_approve(post_names):
    """Approve multiple posts at once."""
    if isinstance(post_names, str):
        post_names = json.loads(post_names)

    now = now_datetime()
    user = frappe.session.user
    updated = 0
    for name in post_names:
        if frappe.db.get_value("Social Post", name, "status") == "Pending Approval":
            frappe.db.set_value("Social Post", name, {
                "status": "Approved",
                "approved_by": user,
                "approval_date": now
            })
            updated += 1

    frappe.db.commit()
    return {"approved": updated}


@frappe.whitelist()
def bulk_delete(post_names):
    """Soft delete multiple posts (set status to Deleted)."""
    if isinstance(post_names, str):
        post_names = json.loads(post_names)

    deleted = 0
    for name in post_names:
        frappe.db.set_value("Social Post", name, "status", "Deleted")
        deleted += 1

    frappe.db.commit()
    return {"deleted": deleted}


# ─── SETTINGS HELPERS ──────────────────────────────────────────────────────────

@frappe.whitelist()
def get_settings():
    """Return full Social Media Settings document."""
    try:
        return frappe.get_single("Social Media Settings").as_dict()
    except frappe.DoesNotExistError:
        doc = frappe.get_doc({"doctype": "Social Media Settings"})
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return doc.as_dict()


@frappe.whitelist()
def save_settings(settings_json):
    """Save Social Media Settings from dashboard."""
    if isinstance(settings_json, str):
        settings_json = json.loads(settings_json)

    doc = frappe.get_single("Social Media Settings")
    for k, v in settings_json.items():
        if k not in ("doctype", "name", "owner", "creation", "modified", "idx"):
            try:
                doc.set(k, v)
            except Exception:
                pass

    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"saved": True}


# ─── DASHBOARD DATA ───────────────────────────────────────────────────────────

@frappe.whitelist()
def get_dashboard_data():
    """Get all dashboard data in one call."""
    return {
        "summary": get_dashboard_summary(),
        "trend": get_performance_trend(30),
        "top_posts": get_top_posts(5),
        "comment_stats": get_comment_summary(),
        "expiring_tokens": get_expiring_tokens(),
        "themes": get_themes(),
        "platform_performance": get_platform_performance(),
        "content_type_performance": get_content_type_performance(),
    }


# ─── UTILITY ───────────────────────────────────────────────────────────────────

@frappe.whitelist()
def ping():
    """Health check endpoint."""
    return {
        "status": "ok",
        "timestamp": str(now_datetime()),
        "user": frappe.session.user,
        "available_themes": len(SMM_THEMES),
        "themes": list(SMM_THEMES.keys()),
    }