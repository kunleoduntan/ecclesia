# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt



import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, get_datetime, add_days
from frappe import _

class SocialMediaSettings(Document):
    def validate(self):
        self.validate_api_settings()
        self.validate_webhook_url()
        self.check_token_expiry()
        self.update_platform_status()
    
    def validate_api_settings(self):
        """Validate API configuration"""
        if self.api_timeout_seconds < 1 or self.api_timeout_seconds > 120:
            frappe.throw(_("API Timeout must be between 1 and 120 seconds"))
        
        if self.max_retry_attempts < 0 or self.max_retry_attempts > 10:
            frappe.throw(_("Max Retry Attempts must be between 0 and 10"))
    
    def validate_webhook_url(self):
        """Validate webhook configuration"""
        if self.enable_webhooks and not self.webhook_base_url:
            frappe.msgprint(
                _("Webhook Base URL is required for webhooks to function"),
                alert=True, indicator="orange"
            )
        
        if self.enable_webhooks and not self.webhook_secret_token:
            frappe.msgprint(
                _("Webhook Secret Token is recommended for security"),
                alert=True, indicator="orange"
            )
    
    def check_token_expiry(self):
        """Check for expiring tokens across all platform accounts"""
        if not self.platform_accounts:
            return
        
        expiring_soon = []
        expired = []
        
        for account in self.platform_accounts:
            if account.token_expiry_date:
                days_to_expiry = (get_datetime(account.token_expiry_date) - now_datetime()).days
                
                if days_to_expiry < 0:
                    expired.append(account.account_name)
                    account.account_status = "Token Expired"
                elif days_to_expiry < 7:
                    expiring_soon.append(account.account_name)
                    frappe.msgprint(
                        _(f"⚠️ Token for {account.account_name} ({account.platform}) expires in {days_to_expiry} days"),
                        alert=True, indicator="orange"
                    )
        
        if expired:
            frappe.msgprint(
                _(f"❌ Tokens expired for: {', '.join(expired)}"),
                alert=True, indicator="red"
            )
    
    def update_platform_status(self):
        """Update platform account status based on API connectivity"""
        for account in self.platform_accounts:
            if account.account_status != "Connected":
                # Attempt to reconnect if token not expired
                if account.account_status == "Disconnected" and account.access_token:
                    account.account_status = "Pending Verification"
    
    def on_update(self):
        """Trigger webhook subscription updates"""
        if self.enable_webhooks and self.has_value_changed("webhook_base_url"):
            self.resubscribe_all_webhooks()
    
    def resubscribe_all_webhooks(self):
        """Resubscribe all platform webhooks when URL changes"""
        frappe.enqueue(
            "carematrix.social_media.webhooks.resubscribe_all_webhooks",
            queue="long",
            timeout=300,
            settings_name=self.name
        )
    
    def get_platform_account(self, platform_name=None, account_id=None):
        """Get platform account by name or ID"""
        for account in self.platform_accounts:
            if platform_name and account.platform == platform_name:
                return account
            if account_id and account.name == account_id:
                return account
        return None


@frappe.whitelist()
def get_global_analytics():
    """Get aggregated analytics across all platforms"""
    settings = frappe.get_single("Social Media Settings")
    
    # Get all posted posts
    posts = frappe.get_all(
        "Social Post",
        filters={
            "status": ["in", ["Published", "Partially Published"]],
            "docstatus": 1
        },
        fields=["name", "post_title", "total_likes", "total_comments", 
                "total_shares", "total_reach", "total_engagement_rate",
                "total_views", "total_clicks", "revenue_generated"]
    )
    
    # Aggregate totals
    total_posts = len(posts)
    total_likes = sum(p.total_likes or 0 for p in posts)
    total_comments = sum(p.total_comments or 0 for p in posts)
    total_shares = sum(p.total_shares or 0 for p in posts)
    total_reach = sum(p.total_reach or 0 for p in posts)
    total_views = sum(p.total_views or 0 for p in posts)
    total_clicks = sum(p.total_clicks or 0 for p in posts)
    total_revenue = sum(p.revenue_generated or 0 for p in posts)
    
    # Platform breakdown
    platform_stats = {}
    
    for post in posts:
        post_doc = frappe.get_doc("Social Post", post.name)
        for perf in post_doc.platform_performance:
            if perf.platform not in platform_stats:
                platform_stats[perf.platform] = {
                    "likes": 0, "comments": 0, "shares": 0, "reach": 0,
                    "views": 0, "clicks": 0, "posts": 0
                }
            
            stats = platform_stats[perf.platform]
            stats["likes"] += perf.likes or 0
            stats["comments"] += perf.comments or 0
            stats["shares"] += perf.shares or 0
            stats["reach"] += perf.reach or 0
            stats["views"] += perf.views or 0
            stats["clicks"] += perf.clicks or 0
            stats["posts"] += 1
    
    # Calculate engagement rate
    avg_engagement = round(
        ((total_likes + total_comments + total_shares) / total_reach * 100) if total_reach else 0,
        2
    )
    
    return {
        "total_posts": total_posts,
        "total_likes": total_likes,
        "total_comments": total_comments,
        "total_shares": total_shares,
        "total_reach": total_reach,
        "total_views": total_views,
        "total_clicks": total_clicks,
        "total_revenue": total_revenue,
        "avg_engagement_rate": avg_engagement,
        "platform_breakdown": platform_stats,
        "top_posts": get_top_performing_posts(5)
    }


def get_top_performing_posts(limit=5):
    """Get top performing posts by engagement"""
    return frappe.db.sql("""
        SELECT 
            name, post_title, 
            (total_likes + total_comments + total_shares) as total_engagement,
            total_reach, total_engagement_rate
        FROM `tabSocial Post`
        WHERE docstatus = 1 AND status IN ('Published', 'Partially Published')
        ORDER BY total_engagement DESC
        LIMIT %s
    """, limit, as_dict=True)