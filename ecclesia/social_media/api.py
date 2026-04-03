# -*- coding: utf-8 -*-
# Copyright (c) 2024, CareMatrix and contributors
# For license information, please see license.txt

import frappe
import requests
import json
from frappe import _
from frappe.utils import now_datetime, get_datetime

# Platform API adapters
class PlatformAPI:
    """Base class for platform APIs"""
    
    def __init__(self, platform_account):
        self.account = platform_account
        self.settings = frappe.get_single("Social Media Settings")
    
    def post_content(self, post, config):
        """Post content to platform - override in subclass"""
        raise NotImplementedError
    
    def get_metrics(self, post_id):
        """Get metrics for a post - override in subclass"""
        raise NotImplementedError
    
    def get_comments(self, post_id):
        """Get comments for a post - override in subclass"""
        raise NotImplementedError
    
    def reply_to_comment(self, comment_id, message):
        """Reply to a comment - override in subclass"""
        raise NotImplementedError


class FacebookAPI(PlatformAPI):
    """Facebook Graph API implementation"""
    
    BASE_URL = "https://graph.facebook.com/v18.0"
    
    def post_content(self, post, config):
        """Post to Facebook"""
        try:
            url = f"{self.BASE_URL}/{self.account.account_id}/feed"
            
            payload = {
                "access_token": self.account.access_token,
                "message": config.custom_caption or post.content,
            }
            
            if post.link_url:
                payload["link"] = post.link_url
            
            # Handle media
            if post.media_attachments:
                # For simplicity, just attach first image
                media = post.media_attachments[0]
                if media.media_file:
                    # Upload media first
                    media_url = self.upload_media(media.media_file)
                    if media_url:
                        payload["attached_media"] = [{"media_fbid": media_url}]
            
            response = requests.post(url, data=payload, timeout=self.settings.api_timeout_seconds)
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "post_id": result.get("id"),
                    "post_url": f"https://facebook.com/{result.get('id')}"
                }
            else:
                return {
                    "success": False,
                    "error": response.text
                }
                
        except Exception as e:
            frappe.log_error(f"Facebook post failed: {str(e)}", "Social Media API")
            return {"success": False, "error": str(e)}
    
    def upload_media(self, media_file):
        """Upload media to Facebook"""
        # Implementation for media upload
        pass
    
    def get_metrics(self, post_id):
        """Get post metrics"""
        url = f"{self.BASE_URL}/{post_id}"
        params = {
            "access_token": self.account.access_token,
            "fields": "likes.summary(true),comments.summary(true),shares,reach,views"
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            return {
                "likes": data.get("likes", {}).get("summary", {}).get("total_count", 0),
                "comments": data.get("comments", {}).get("summary", {}).get("total_count", 0),
                "shares": data.get("shares", {}).get("count", 0),
                "reach": data.get("reach", 0),
                "views": data.get("views", 0)
            }
        return {}


class InstagramAPI(PlatformAPI):
    """Instagram Graph API implementation"""
    
    BASE_URL = "https://graph.facebook.com/v18.0"
    
    def post_content(self, post, config):
        """Post to Instagram (requires media)"""
        if not post.media_attachments:
            return {"success": False, "error": "Instagram requires media"}
        
        try:
            # First create media container
            creation_url = f"{self.BASE_URL}/{self.account.account_id}/media"
            
            media = post.media_attachments[0]
            payload = {
                "access_token": self.account.access_token,
                "image_url": media.media_url or self.get_public_url(media.media_file),
                "caption": config.custom_caption or post.content,
                "media_type": "IMAGE"
            }
            
            if config.post_type == "Reel":
                payload["media_type"] = "REELS"
            
            response = requests.post(creation_url, data=payload)
            
            if response.status_code == 200:
                container_id = response.json().get("id")
                
                # Publish the container
                publish_url = f"{self.BASE_URL}/{self.account.account_id}/media_publish"
                publish_response = requests.post(publish_url, data={
                    "access_token": self.account.access_token,
                    "creation_id": container_id
                })
                
                if publish_response.status_code == 200:
                    result = publish_response.json()
                    return {
                        "success": True,
                        "post_id": result.get("id"),
                        "post_url": f"https://instagram.com/p/{result.get('id')}"
                    }
            
            return {"success": False, "error": response.text}
            
        except Exception as e:
            frappe.log_error(f"Instagram post failed: {str(e)}", "Social Media API")
            return {"success": False, "error": str(e)}


class LinkedInAPI(PlatformAPI):
    """LinkedIn API implementation"""
    
    BASE_URL = "https://api.linkedin.com/v2"
    
    def post_content(self, post, config):
        """Post to LinkedIn"""
        try:
            headers = {
                "Authorization": f"Bearer {self.account.access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0"
            }
            
            # Create ugc post
            url = f"{self.BASE_URL}/ugcPosts"
            
            payload = {
                "author": f"urn:li:person:{self.account.account_id}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": config.custom_caption or post.content
                        },
                        "shareMediaCategory": "ARTICLE" if post.link_url else "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
            
            if post.link_url:
                payload["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [{
                    "status": "READY",
                    "originalUrl": post.link_url
                }]
            
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 201:
                result = response.json()
                return {
                    "success": True,
                    "post_id": result.get("id"),
                    "post_url": f"https://linkedin.com/feed/update/{result.get('id')}"
                }
            
            return {"success": False, "error": response.text}
            
        except Exception as e:
            frappe.log_error(f"LinkedIn post failed: {str(e)}", "Social Media API")
            return {"success": False, "error": str(e)}


class TwitterAPI(PlatformAPI):
    """Twitter/X API implementation"""
    
    BASE_URL = "https://api.twitter.com/2"
    
    def post_content(self, post, config):
        """Post to Twitter/X"""
        try:
            headers = {
                "Authorization": f"Bearer {self.account.access_token}",
                "Content-Type": "application/json"
            }
            
            url = f"{self.BASE_URL}/tweets"
            
            # Truncate caption for Twitter
            caption = config.custom_caption or post.content
            if len(caption) > 280:
                caption = caption[:277] + "..."
            
            payload = {"text": caption}
            
            if post.media_attachments:
                # Upload media first (simplified)
                media_id = self.upload_media(post.media_attachments[0])
                if media_id:
                    payload["media"] = {"media_ids": [media_id]}
            
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 201:
                result = response.json()
                return {
                    "success": True,
                    "post_id": result.get("data", {}).get("id"),
                    "post_url": f"https://twitter.com/i/web/status/{result.get('data', {}).get('id')}"
                }
            
            return {"success": False, "error": response.text}
            
        except Exception as e:
            frappe.log_error(f"Twitter post failed: {str(e)}", "Social Media API")
            return {"success": False, "error": str(e)}


# API Factory
class SocialMediaAPI:
    """Factory for creating platform-specific API instances"""
    
    @staticmethod
    def get_api(platform_account):
        """Get appropriate API instance for platform"""
        platform = platform_account.platform.lower()
        
        if "facebook" in platform:
            return FacebookAPI(platform_account)
        elif "instagram" in platform:
            return InstagramAPI(platform_account)
        elif "linkedin" in platform:
            return LinkedInAPI(platform_account)
        elif "twitter" in platform or "x" in platform:
            return TwitterAPI(platform_account)
        else:
            return PlatformAPI(platform_account)  # Fallback


@frappe.whitelist()
def publish_post(post_name):
    """Publish a post to all enabled platforms"""
    post = frappe.get_doc("Social Post", post_name)
    settings = frappe.get_single("Social Media Settings")
    
    results = []
    
    for config in post.platform_configs:
        if not config.is_enabled:
            continue
        
        # Get platform account
        platform_account = None
        for acc in settings.platform_accounts:
            if acc.name == config.platform_account:
                platform_account = acc
                break
        
        if not platform_account:
            config.post_status = "Failed"
            config.error_message = "Platform account not found"
            results.append({
                "platform": config.platform,
                "success": False,
                "error": "Account not found"
            })
            continue
        
        # Get API instance
        api = SocialMediaAPI.get_api(platform_account)
        
        # Post content
        result = api.post_content(post, config)
        
        if result.get("success"):
            config.post_status = "Published"
            config.platform_post_id = result.get("post_id")
            config.post_url = result.get("post_url")
            config.published_time = now_datetime()
            
            results.append({
                "platform": config.platform,
                "success": True,
                "post_id": result.get("post_id"),
                "url": result.get("post_url")
            })
        else:
            config.post_status = "Failed"
            config.error_message = result.get("error")
            config.retry_count = (config.retry_count or 0) + 1
            config.last_attempt = now_datetime()
            
            results.append({
                "platform": config.platform,
                "success": False,
                "error": result.get("error")
            })
        
        post.save(ignore_permissions=True)
    
    # Update overall status
    all_published = all(r.get("success") for r in results if r.get("platform") in 
                        [c.platform for c in post.platform_configs if c.is_enabled])
    
    if all_published:
        post.db_set("status", "Published")
        post.db_set("published_time", now_datetime())
    elif any(r.get("success") for r in results):
        post.db_set("status", "Partially Published")
    else:
        post.db_set("status", "Failed")
    
    # Send notifications
    send_publish_notifications(post, results)
    
    return results


def send_publish_notifications(post, results):
    """Send notifications about publish results"""
    settings = frappe.get_single("Social Media Settings")
    
    if not settings.notify_on_post_failure:
        return
    
    failures = [r for r in results if not r.get("success")]
    if failures:
        message = f"❌ Post {post.name} failed on: {', '.join(f['platform'] for f in failures)}"
        
        for recipient in settings.notification_recipients:
            if recipient.recipient_email:
                frappe.sendmail(
                    recipients=[recipient.recipient_email],
                    subject=f"⚠️ Social Media Post Failure - {post.name}",
                    message=message
                )


@frappe.whitelist()
def optimize_and_schedule(post_name):
    """AI optimization for posting times"""
    post = frappe.get_doc("Social Post", post_name)
    settings = frappe.get_single("Social Media Settings")
    
    for config in post.platform_configs:
        if not config.is_enabled:
            continue
        
        # Get best time from platform account
        platform_account = settings.get_platform_account(account_id=config.platform_account)
        
        if platform_account and platform_account.best_posting_times:
            best_times = json.loads(platform_account.best_posting_times)
            # Simple implementation - schedule for next best time
            # In production, this would be more sophisticated
            config.scheduled_time = get_next_optimal_time(best_times)
            config.post_status = "Scheduled"
    
    post.db_set("status", "Scheduled")
    frappe.msgprint(_("✅ Posts optimized and scheduled"))


def get_next_optimal_time(best_times):
    """Get next optimal posting time based on AI data"""
    # Implementation would use historical data
    from frappe.utils import now_datetime, add_days
    return add_days(now_datetime(), 1)