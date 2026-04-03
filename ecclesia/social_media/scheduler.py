# -*- coding: utf-8 -*-
# Copyright (c) 2024, CareMatrix and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now_datetime, get_datetime
from frappe import _

def publish_scheduled_posts():
    """Scheduled job to publish posts that are due"""
    
    # Get all scheduled posts
    scheduled_posts = frappe.get_all(
        "Social Post Platform Config",
        filters={
            "post_status": "Scheduled",
            "scheduled_time": ["<=", now_datetime()],
            "is_enabled": 1
        },
        fields=["parent", "name", "platform", "scheduled_time"]
    )
    
    posts_to_publish = {}
    for config in scheduled_posts:
        if config.parent not in posts_to_publish:
            posts_to_publish[config.parent] = []
        posts_to_publish[config.parent].append(config.name)
    
    # Publish each post
    for post_name, config_names in posts_to_publish.items():
        try:
            post = frappe.get_doc("Social Post", post_name)
            
            # Only publish the specific configs that are due
            for config in post.platform_configs:
                if config.name in config_names:
                    # Mark as publishing
                    config.post_status = "Publishing"
                    post.save(ignore_permissions=True)
            
            # Queue the publish job
            frappe.enqueue(
                "carematrix.social_media.api.publish_post",
                queue="short",
                post_name=post_name
            )
            
        except Exception as e:
            frappe.log_error(f"Failed to publish scheduled post {post_name}: {str(e)}", "Social Media Scheduler")


def sync_platform_metrics():
    """Scheduled job to sync metrics for published posts"""
    
    # Get all published posts from last 30 days
    posts = frappe.get_all(
        "Social Post",
        filters={
            "status": ["in", ["Published", "Partially Published"]],
            "published_time": [">=", frappe.utils.add_days(now_datetime(), -30)]
        },
        fields=["name"]
    )
    
    for post in posts:
        frappe.enqueue(
            "carematrix.social_media.scheduler.sync_single_post_metrics",
            queue="long",
            post_name=post.name
        )


def sync_single_post_metrics(post_name):
    """Sync metrics for a single post"""
    post = frappe.get_doc("Social Post", post_name)
    settings = frappe.get_single("Social Media Settings")
    
    for config in post.platform_configs:
        if config.post_status != "Published" or not config.platform_post_id:
            continue
        
        # Get platform account
        platform_account = None
        for acc in settings.platform_accounts:
            if acc.name == config.platform_account:
                platform_account = acc
                break
        
        if not platform_account:
            continue
        
        # Get API and fetch metrics
        from .api import SocialMediaAPI
        api = SocialMediaAPI.get_api(platform_account)
        metrics = api.get_metrics(config.platform_post_id)
        
        if metrics:
            post.update_performance_metrics(config.platform, metrics)
    
    post.save(ignore_permissions=True)


def sync_comments():
    """Scheduled job to sync comments for published posts"""
    
    posts = frappe.get_all(
        "Social Post",
        filters={"status": ["in", ["Published", "Partially Published"]]},
        fields=["name"]
    )
    
    for post in posts:
        frappe.enqueue(
            "carematrix.social_media.scheduler.sync_single_post_comments",
            queue="long",
            post_name=post.name
        )


def sync_single_post_comments(post_name):
    """Sync comments for a single post"""
    post = frappe.get_doc("Social Post", post_name)
    settings = frappe.get_single("Social Media Settings")
    
    for config in post.platform_configs:
        if config.post_status != "Published" or not config.platform_post_id:
            continue
        
        platform_account = settings.get_platform_account(account_id=config.platform_account)
        if not platform_account:
            continue
        
        # Get API and fetch comments
        from .api import SocialMediaAPI
        api = SocialMediaAPI.get_api(platform_account)
        comments = api.get_comments(config.platform_post_id)
        
        # Process comments (implementation would vary by platform)
        process_comments(post, config, comments)
    
    post.save(ignore_permissions=True)


def process_comments(post, config, comments):
    """Process and store comments"""
    # Implementation would parse platform-specific comment data
    pass


def check_token_expiry():
    """Daily job to check for expiring tokens"""
    settings = frappe.get_single("Social Media Settings")
    
    for account in settings.platform_accounts:
        if account.token_expiry_date:
            days_to_expiry = (get_datetime(account.token_expiry_date) - now_datetime()).days
            
            if days_to_expiry < 7 and days_to_expiry >= 0:
                # Notify account manager
                if account.primary_manager:
                    frappe.sendmail(
                        recipients=[account.primary_manager],
                        subject=f"⚠️ Token Expiry Warning - {account.account_name}",
                        message=f"Your {account.platform} account token expires in {days_to_expiry} days. Please refresh."
                    )