# -*- coding: utf-8 -*-
# Copyright (c) 2024, CareMatrix and contributors
# For license information, please see license.txt

import frappe
import hashlib
import hmac
import json
from frappe import _

@frappe.whitelist(allow_guest=True)
def facebook_webhook():
    """Handle Facebook webhook events"""
    
    # Verify webhook (for subscription)
    if frappe.request.method == "GET":
        hub_mode = frappe.form_dict.get("hub.mode")
        hub_challenge = frappe.form_dict.get("hub.challenge")
        hub_verify_token = frappe.form_dict.get("hub.verify_token")
        
        settings = frappe.get_single("Social Media Settings")
        
        # Find matching platform account
        for account in settings.platform_accounts:
            if account.platform == "Facebook" and account.webhook_verify_token == hub_verify_token:
                account.webhook_subscribed = 1
                account.webhook_last_ping = frappe.utils.now_datetime()
                settings.save(ignore_permissions=True)
                
                return hub_challenge
        
        return "Verification failed", 403
    
    # Handle POST (actual events)
    elif frappe.request.method == "POST":
        data = frappe.local.form_dict
        signature = frappe.get_request_header("X-Hub-Signature", "")
        
        # Verify signature
        settings = frappe.get_single("Social Media Settings")
        if not verify_signature(frappe.request.data, signature, settings.webhook_secret_token):
            return "Invalid signature", 401
        
        # Process the webhook data
        process_facebook_event(data)
        
        return "EVENT_RECEIVED", 200


def verify_signature(payload, signature, secret):
    """Verify webhook signature"""
    if not secret or not signature:
        return True  # Skip verification if not configured
    
    expected = hmac.new(
        key=secret.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(f"sha256={expected}", signature)


def process_facebook_event(data):
    """Process Facebook webhook events"""
    entries = data.get("entry", [])
    
    for entry in entries:
        changes = entry.get("changes", [])
        for change in changes:
            field = change.get("field")
            
            if field == "feed":
                # New post comment
                value = change.get("value", {})
                if value.get("item") == "comment":
                    create_comment_from_webhook("Facebook", value)
            
            elif field == "messages":
                # New message
                value = change.get("value", {})
                create_message_from_webhook("Facebook", value)


def create_comment_from_webhook(platform, data):
    """Create comment record from webhook data"""
    post_id = data.get("post_id") or data.get("parent_id")
    
    # Find the social post
    post_name = frappe.db.get_value(
        "Social Post Platform Config",
        {"platform_post_id": post_id},
        "parent"
    )
    
    if not post_name:
        return
    
    post = frappe.get_doc("Social Post", post_name)
    
    # Check if comment already exists
    existing = frappe.db.exists(
        "Social Post Comment",
        {
            "parent": post_name,
            "platform_comment_id": data.get("comment_id") or data.get("id")
        }
    )
    
    if existing:
        return
    
    # Create new comment
    comment = post.append("comments", {})
    comment.platform = platform
    comment.platform_comment_id = data.get("comment_id") or data.get("id")
    comment.author_name = data.get("from", {}).get("name", "Unknown")
    comment.author_id = data.get("from", {}).get("id")
    comment.comment_text = data.get("message", "")
    comment.comment_time = frappe.utils.now_datetime()
    comment.status = "New"
    
    # Perform sentiment analysis
    comment.sentiment_label = analyze_sentiment(comment.comment_text)
    
    post.save(ignore_permissions=True)
    
    # Send notification
    send_comment_notification(post, comment)


def create_message_from_webhook(platform, data):
    """Create message record from webhook data"""
    # Implementation for direct messages
    pass


def analyze_sentiment(text):
    """Simple sentiment analysis (can be replaced with AI)"""
    positive_words = ["great", "awesome", "love", "excellent", "good", "best", "amazing", "thank"]
    negative_words = ["bad", "terrible", "awful", "hate", "worst", "poor", "disappointed", "fail"]
    
    text_lower = text.lower()
    
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)
    
    if positive_count > negative_count:
        return "Positive"
    elif negative_count > positive_count:
        return "Negative"
    else:
        return "Neutral"


def send_comment_notification(post, comment):
    """Send notification for new comment"""
    settings = frappe.get_single("Social Media Settings")
    
    if not settings.notify_on_new_comment:
        return
    
    for recipient in settings.notification_recipients:
        if recipient.recipient_email:
            frappe.sendmail(
                recipients=[recipient.recipient_email],
                subject=f"💬 New Comment on {post.post_title}",
                message=f"""
                <h3>New Comment Received</h3>
                <p><b>Post:</b> {post.post_title}</p>
                <p><b>Platform:</b> {comment.platform}</p>
                <p><b>From:</b> {comment.author_name}</p>
                <p><b>Comment:</b> {comment.comment_text}</p>
                <p><b>Sentiment:</b> {comment.sentiment_label}</p>
                <p><a href="/app/social-post/{post.name}">View in CareMatrix</a></p>
                """
            )


def resubscribe_all_webhooks(settings_name):
    """Resubscribe all platform webhooks"""
    settings = frappe.get_doc("Social Media Settings", settings_name)
    
    for account in settings.platform_accounts:
        if account.platform in ["Facebook", "Instagram"]:
            # Resubscribe logic here
            pass