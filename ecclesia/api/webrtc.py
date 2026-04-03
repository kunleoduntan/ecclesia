# ecclesia/ecclesia/api/webrtc.py
import frappe
import json

@frappe.whitelist()
def get_webrtc_config():
    """Get WebRTC configuration for client"""
    settings = frappe.get_single('Telephony Settings')
    
    # Get STUN servers
    stun_servers = []
    if settings.stun_servers:
        stun_servers = [s.strip() for s in settings.stun_servers.split('\n') if s.strip()]
    
    # Get TURN servers
    turn_servers = []
    if settings.turn_enabled and settings.turn_servers:
        for server in settings.turn_servers:
            turn_servers.append({
                'urls': server.server_url,
                'username': server.username,
                'credential': server.get_password('credential')
            })
    
    return {
        'stun_servers': stun_servers,
        'turn_servers': turn_servers,
        'webrtc_server': settings.webrtc_server,
        'webrtc_port': settings.webrtc_port
    }