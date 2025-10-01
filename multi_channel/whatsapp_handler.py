
"""
Phase 7: WhatsApp Business Integration
Handle booking requests via WhatsApp messages
"""

import os
import logging
import requests
from typing import Dict, Optional
from twilio.rest import Client

logger = logging.getLogger(__name__)

class WhatsAppHandler:
    """
    WhatsApp Business integration for booking management
    Uses Twilio WhatsApp API
    """
    
    def __init__(self):
        self.enabled = os.getenv('WHATSAPP_ENABLED', 'false').lower() == 'true'
        
        if self.enabled:
            self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
            self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
            self.whatsapp_number = os.getenv('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')
            
            if self.account_sid and self.auth_token:
                self.client = Client(self.account_sid, self.auth_token)
            else:
                logger.warning("WhatsApp credentials not configured")
                self.enabled = False
    
    def send_message(self, to_number: str, message: str) -> Dict:
        """
        Send WhatsApp message to customer
        
        Args:
            to_number: Customer phone number
            message: Message text
            
        Returns:
            Dictionary with send status
        """
        if not self.enabled:
            logger.info("WhatsApp not enabled, skipping message send")
            return {'status': 'disabled'}
        
        try:
            # Format number for WhatsApp
            if not to_number.startswith('whatsapp:'):
                to_number = f'whatsapp:{to_number}'
            
            # Send message via Twilio
            message_obj = self.client.messages.create(
                from_=self.whatsapp_number,
                body=message,
                to=to_number
            )
            
            logger.info(f"WhatsApp message sent to {to_number}, SID: {message_obj.sid}")
            
            return {
                'status': 'sent',
                'message_sid': message_obj.sid,
                'to': to_number
            }
            
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def send_booking_confirmation(self, to_number: str, booking_details: Dict) -> Dict:
        """
        Send booking confirmation via WhatsApp
        
        Args:
            to_number: Customer phone number
            booking_details: Dictionary with booking information
            
        Returns:
            Send status dictionary
        """
        message = f"""
✅ *Booking Confirmed!*

📅 *Date:* {booking_details.get('date', 'N/A')}
⏰ *Time:* {booking_details.get('time', 'N/A')}
🏀 *Facility:* {booking_details.get('facility', 'N/A')}
💰 *Price:* ${booking_details.get('price', 'N/A')}
🎫 *Booking ID:* {booking_details.get('booking_id', 'N/A')}

Thank you for booking with us! See you soon! 🎉
        """.strip()
        
        return self.send_message(to_number, message)
    
    def send_reminder(self, to_number: str, booking_details: Dict, hours_until: int) -> Dict:
        """
        Send booking reminder via WhatsApp
        
        Args:
            to_number: Customer phone number
            booking_details: Booking information
            hours_until: Hours until booking
            
        Returns:
            Send status dictionary
        """
        message = f"""
⏰ *Reminder: Booking in {hours_until} hour{'s' if hours_until > 1 else ''}*

📅 *Date:* {booking_details.get('date', 'N/A')}
⏰ *Time:* {booking_details.get('time', 'N/A')}
🏀 *Facility:* {booking_details.get('facility', 'N/A')}
🎫 *Booking ID:* {booking_details.get('booking_id', 'N/A')}

We look forward to seeing you! 🎯
        """.strip()
        
        return self.send_message(to_number, message)
    
    def send_cancellation(self, to_number: str, booking_id: str) -> Dict:
        """
        Send cancellation confirmation via WhatsApp
        
        Args:
            to_number: Customer phone number
            booking_id: Booking ID that was cancelled
            
        Returns:
            Send status dictionary
        """
        message = f"""
❌ *Booking Cancelled*

🎫 *Booking ID:* {booking_id}

Your booking has been cancelled. We hope to see you again soon!
        """.strip()
        
        return self.send_message(to_number, message)
    
    def handle_incoming_message(self, from_number: str, message_body: str) -> Dict:
        """
        Handle incoming WhatsApp message from customer
        
        Args:
            from_number: Customer's WhatsApp number
            message_body: Message text
            
        Returns:
            Response dictionary with action taken
        """
        # This would integrate with the NLU system to process the message
        # For now, return a placeholder response
        return {
            'status': 'received',
            'from': from_number,
            'message': message_body,
            'action': 'process_with_nlu'
        }


# Global instance
_whatsapp_handler = None

def get_whatsapp_handler() -> WhatsAppHandler:
    """Get or create global WhatsAppHandler instance"""
    global _whatsapp_handler
    if _whatsapp_handler is None:
        _whatsapp_handler = WhatsAppHandler()
    return _whatsapp_handler
