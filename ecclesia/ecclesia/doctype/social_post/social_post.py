# Copyright (c) 2026, Kunle Oduntan and contributors
# For license information, please see license.txt



import frappe
import json
from frappe.model.document import Document
from frappe.utils import now_datetime, get_datetime, add_to_date, flt
from frappe import _

class SocialPost(Document):
    def autoname(self):
        """Generate name: SOC-POST-YYYY-MM-#####"""
        from frappe.model.naming import make_autoname
        self.name = make_autoname("SOC-POST-.YYYY.-.MM.-.#####")
    
    def validate(self):
        self.validate_content()
        self.validate_platform_configs()
        self.calculate_character_counts()
        self.check_media_compatibility()
        self.set_optimization_scores()
        self.calculate_totals_from_configs()
    
    def validate_content(self):
        """Validate basic content requirements"""
        if not self.content and not self.media_attachments:
            frappe.throw(_("Either content or media attachments is required"))
        
        if self.content_type == "Link" and not self.link_url:
            frappe.throw(_("Link URL is required for Link post type"))
    
    def validate_platform_configs(self):
        """Ensure at least one platform is enabled"""
        if not self.platform_configs:
            frappe.throw(_("At least one platform configuration is required"))
        
        enabled_platforms = [p for p in self.platform_configs if p.is_enabled]
        if not enabled_platforms:
            frappe.throw(_("At least one platform must be enabled"))
        
        # Check for duplicate platforms
        platforms = []
        for config in enabled_platforms:
            if config.platform in platforms:
                frappe.throw(_(f"Duplicate platform {config.platform} is not allowed"))
            platforms.append(config.platform)
    
    def calculate_character_counts(self):
        """Calculate character counts for each platform config"""
        for config in self.platform_configs:
            if not config.is_enabled:
                continue
            
            caption = config.custom_caption or self.content
            if caption:
                # Strip HTML tags for character count
                text = frappe.utils.strip_html(caption)
                config.character_count = len(text)
                
                # Get platform limits from settings
                settings = frappe.get_single("Social Media Settings")
                account = settings.get_platform_account(account_id=config.platform_account)
                
                if account and account.character_limit:
                    if config.character_count > account.character_limit:
                        frappe.msgprint(
                            _(f"Caption for {config.platform} exceeds character limit ({config.character_count}/{account.character_limit})"),
                            alert=True, indicator="orange"
                        )
    
    def check_media_compatibility(self):
        """Check if media is compatible with selected platforms"""
        if not self.media_attachments:
            return
        
        settings = frappe.get_single("Social Media Settings")
        
        for config in self.platform_configs:
            if not config.is_enabled:
                continue
            
            account = settings.get_platform_account(account_id=config.platform_account)
            if not account:
                continue
            
            # Check media compatibility for this platform
            for media in self.media_attachments:
                if account.max_image_size_mb and media.file_size_mb > account.max_image_size_mb:
                    frappe.msgprint(
                        _(f"Media file for {config.platform} exceeds size limit ({media.file_size_mb}MB > {account.max_image_size_mb}MB)"),
                        alert=True, indicator="orange"
                    )
    
    def set_optimization_scores(self):
        """Calculate optimization scores for each platform"""
        for config in self.platform_configs:
            if not config.is_enabled:
                continue
            
            score = 100
            reasons = []
            
            # Check character count
            account = frappe.get_single("Social Media Settings").get_platform_account(
                account_id=config.platform_account
            )
            
            if account and account.character_limit:
                char_ratio = (config.character_count or 0) / account.character_limit
                if char_ratio > 0.9:
                    score -= 10
                    reasons.append("Caption too long")
                elif char_ratio < 0.1:
                    score -= 5
                    reasons.append("Caption too short")
            
            # Check hashtags
            hashtags = config.custom_hashtags or self.primary_hashtags
            if hashtags:
                hashtag_count = len(hashtags.split())
                if account and account.hashtag_limit and hashtag_count > account.hashtag_limit:
                    score -= 15
                    reasons.append("Too many hashtags")
            
            # Check media
            if not self.media_attachments and config.post_type not in ["Text Only", "Link"]:
                score -= 20
                reasons.append("Missing media for this post type")
            
            config.optimization_score = max(0, score)
            config.ai_suggestions = ", ".join(reasons) if reasons else "Optimized"
    
    def calculate_totals_from_configs(self):
        """Calculate total metrics from platform configs"""
        # This will be updated by scheduler after publishing
        pass
    
    def on_submit(self):
        """Handle submission - trigger publishing or scheduling"""
        self.db_set("status", "Approved" if not self.requires_approval else "Pending Approval")
        
        if self.publish_strategy == "Publish Now":
            self.publish_now()
        elif self.publish_strategy in ["Schedule Global", "Schedule Per Platform"]:
            self.schedule_posts()
        elif self.publish_strategy == "Optimize AI":
            self.optimize_and_schedule()
    
    def publish_now(self):
        """Publish immediately to all enabled platforms"""
        frappe.enqueue(
            "carematrix.social_media.api.publish_post",
            queue="short",
            post_name=self.name
        )
        
        self.db_set("status", "Publishing")
        frappe.msgprint(_("🚀 Publishing job queued for all platforms"), alert=True)
    
    def schedule_posts(self):
        """Schedule posts based on configuration"""
        scheduled_count = 0
        
        for config in self.platform_configs:
            if not config.is_enabled:
                continue
            
            if self.publish_strategy == "Schedule Global" and self.global_schedule:
                config.scheduled_time = self.global_schedule
                config.post_status = "Scheduled"
                scheduled_count += 1
            elif config.scheduled_time:
                config.post_status = "Scheduled"
                scheduled_count += 1
        
        self.db_set("status", "Scheduled")
        frappe.msgprint(
            _(f"📅 {scheduled_count} posts scheduled"),
            alert=True, indicator="blue"
        )
    
    def optimize_and_schedule(self):
        """Use AI to determine best posting times"""
        frappe.enqueue(
            "carematrix.social_media.api.optimize_and_schedule",
            queue="long",
            post_name=self.name
        )
        
        self.db_set("status", "Optimizing")
        frappe.msgprint(
            _("🤖 AI optimization in progress..."),
            alert=True, indicator="purple"
        )
    
    def on_cancel(self):
        """Handle cancellation"""
        self.db_set("status", "Cancelled")
        
        # Delete scheduled jobs
        frappe.db.delete("Scheduled Job Log", {
            "reference_doctype": "Social Post",
            "reference_name": self.name,
            "status": "Scheduled"
        })
    
    def after_insert(self):
        """Create platform performance records after insert"""
        for config in self.platform_configs:
            if not config.is_enabled:
                continue
            
            # Create performance record
            perf = self.append("platform_performance", {})
            perf.platform = config.platform
            perf.account_name = config.account_name
            perf.likes = 0
            perf.comments = 0
            perf.shares = 0
            perf.reach = 0
            perf.views = 0
            perf.clicks = 0
            perf.engagement_rate = 0
    
    def update_performance_metrics(self, platform, metrics):
        """Update performance metrics for a platform"""
        for perf in self.platform_performance:
            if perf.platform == platform:
                perf.likes = metrics.get("likes", perf.likes)
                perf.comments = metrics.get("comments", perf.comments)
                perf.shares = metrics.get("shares", perf.shares)
                perf.reach = metrics.get("reach", perf.reach)
                perf.views = metrics.get("views", perf.views)
                perf.clicks = metrics.get("clicks", perf.clicks)
                
                # Calculate engagement rate
                total_engagement = (perf.likes + perf.comments + perf.shares)
                if perf.reach:
                    perf.engagement_rate = round((total_engagement / perf.reach) * 100, 2)
                
                # Store platform-specific metrics
                perf.platform_specific_metrics = json.dumps(metrics)
                break
        
        self.calculate_totals()
    
    def calculate_totals(self):
        """Calculate total metrics across all platforms"""
        self.total_likes = sum(p.likes or 0 for p in self.platform_performance)
        self.total_comments = sum(p.comments or 0 for p in self.platform_performance)
        self.total_shares = sum(p.shares or 0 for p in self.platform_performance)
        self.total_reach = sum(p.reach or 0 for p in self.platform_performance)
        self.total_views = sum(p.views or 0 for p in self.platform_performance)
        self.total_clicks = sum(p.clicks or 0 for p in self.platform_performance)
        
        total_engagement = self.total_likes + self.total_comments + self.total_shares
        if self.total_reach:
            self.total_engagement_rate = round((total_engagement / self.total_reach) * 100, 2)
        
        self.db_set({
            "total_likes": self.total_likes,
            "total_comments": self.total_comments,
            "total_shares": self.total_shares,
            "total_reach": self.total_reach,
            "total_views": self.total_views,
            "total_clicks": self.total_clicks,
            "total_engagement_rate": self.total_engagement_rate
        }, update_modified=False)
    
    def get_platform_config(self, platform):
        """Get platform config by platform name"""
        for config in self.platform_configs:
            if config.platform == platform:
                return config
        return None


@frappe.whitelist()
def get_post_analytics(post_name):
    """Get comprehensive analytics for a post"""
    post = frappe.get_doc("Social Post", post_name)
    
    # Get comments with sentiment
    comments = frappe.db.get_all(
        "Social Post Comment",
        filters={"parent": post_name},
        fields=["platform", "sentiment_label", "count(*) as count"],
        group_by="platform, sentiment_label"
    )
    
    # Get performance timeline (last 7 days)
    timeline = frappe.db.sql("""
        SELECT 
            DATE(creation) as date,
            SUM(likes) as likes,
            SUM(comments) as comments,
            SUM(shares) as shares
        FROM `tabSocial Platform Performance`
        WHERE parent = %s
        AND creation >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        GROUP BY DATE(creation)
        ORDER BY date
    """, post_name, as_dict=True)
    
    return {
        "post": {
            "name": post.name,
            "title": post.post_title,
            "status": post.status,
            "published_time": post.published_time,
            "total_engagement": post.total_likes + post.total_comments + post.total_shares,
            "total_reach": post.total_reach,
            "engagement_rate": post.total_engagement_rate,
            "revenue": post.revenue_generated
        },
        "platform_performance": post.platform_performance,
        "comment_sentiment": comments,
        "engagement_timeline": timeline
    }