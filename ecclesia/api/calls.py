# ecclesia/ecclesia/api/calls.py
# -*- coding: utf-8 -*-
import frappe
from frappe import _
from frappe.utils import now_datetime

@frappe.whitelist()
def initiate_call(number, call_type=None, contact_name=None, reference_doctype=None, reference_docname=None):
    """Initiate a phone call - Consolidated version"""
    try:
        # Get active provider
        provider = frappe.db.get_value("Telephony Provider", {"is_active": 1})
        if not provider:
            frappe.log_error("No active telephony provider found", "Telephony Error")
            return {'success': False, 'error': 'No active telephony provider'}
        
        # Determine call type if not provided
        if not call_type:
            call_type = 'Internal' if len(number) <= 4 else 'External'
        
        # Get current user's agent record
        agent = frappe.db.get_value("Telephony Agent", {"user": frappe.session.user}, "name")
        
        # Get caller name
        caller_name = frappe.db.get_value("User", frappe.session.user, "full_name")
        
        # Create call log
        call_log = frappe.get_doc({
            'doctype': 'Telephony Call Log',
            'call_id': frappe.generate_hash(length=10),
            'caller_number': frappe.session.user,
            'caller_name': caller_name,
            'receiver_number': number,
            'receiver_name': contact_name,
            'call_type': 'Outgoing' if call_type == 'External' else 'Internal',
            'status': 'Ringing',
            'provider': provider,
            'agent': agent,
            'linked_document_type': reference_doctype,
            'linked_document': reference_docname,
            'start_time': now_datetime()
        })
        call_log.insert(ignore_permissions=True)
        frappe.db.commit()
        
        # Log the call initiation
        frappe.log_error(
            message=f"Call initiated: {call_log.name} to {number}",
            title="Telephony Call"
        )
        
        # Here you would integrate with actual telephony provider
        # For now, return success with call details
        
        return {
            'success': True,
            'call_id': call_log.name,
            'number': number,
            'contact_name': contact_name,
            'call_type': call_type,
            'message': f'Call initiated to {number}'
        }
        
    except Exception as e:
        frappe.log_error(
            message=f"Call initiation failed: {str(e)}\nNumber: {number}",
            title="Telephony Error"
        )
        return {'success': False, 'error': str(e)}

@frappe.whitelist()
def end_call(call_id):
    """End an active call"""
    try:
        # Update call log
        frappe.db.set_value('Telephony Call Log', call_id, {
            'status': 'Ended',
            'end_time': now_datetime()
        })
        frappe.db.commit()
        
        return {'success': True, 'message': 'Call ended successfully'}
        
    except Exception as e:
        frappe.log_error(
            message=f"Failed to end call {call_id}: {str(e)}",
            title="Telephony Error"
        )
        return {'success': False, 'error': str(e)}

@frappe.whitelist()
def end_call_with_notes(call_id, notes):
    """End a call and save notes"""
    try:
        # Update call log with notes
        frappe.db.set_value('Telephony Call Log', call_id, {
            'status': 'Ended',
            'end_time': now_datetime(),
            'notes': notes
        })
        frappe.db.commit()
        
        return {'success': True, 'message': 'Call ended with notes saved'}
        
    except Exception as e:
        frappe.log_error(
            message=f"Failed to end call {call_id} with notes: {str(e)}",
            title="Telephony Error"
        )
        return {'success': False, 'error': str(e)}

@frappe.whitelist()
def get_call_status(call_id):
    """Get current status of a call"""
    try:
        status = frappe.db.get_value('Telephony Call Log', call_id, 'status')
        return {
            'success': True,
            'call_id': call_id,
            'status': status
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

@frappe.whitelist()
def toggle_mute(call_id):
    """Toggle mute for an active call"""
    try:
        # This would integrate with your telephony provider
        # For now, just return success
        return {
            'success': True,
            'call_id': call_id,
            'muted': True,
            'message': 'Call muted'
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

@frappe.whitelist()
def send_dtmf(call_id, digits):
    """Send DTMF tones during a call"""
    try:
        # This would integrate with your telephony provider
        # For now, just return success
        return {
            'success': True,
            'call_id': call_id,
            'digits': digits,
            'message': f'DTMF tones sent: {digits}'
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

@frappe.whitelist()
def transfer_call(call_id, target_number):
    """Transfer an active call to another number"""
    try:
        # Update call log
        frappe.db.set_value('Telephony Call Log', call_id, {
            'status': 'Transferred',
            'notes': f'Transferred to {target_number}'
        })
        frappe.db.commit()
        
        return {
            'success': True,
            'call_id': call_id,
            'transferred_to': target_number,
            'message': f'Call transferred to {target_number}'
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}