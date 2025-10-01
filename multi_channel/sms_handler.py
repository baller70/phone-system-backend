
"""
Phase 7: SMS Booking & Notifications
Handle booking via SMS with simple commands
"""

import os
import logging
import re
from typing import Dict, Optional
from twilio.rest import Client

logger = logging.getLogger(__name__)

class SMSHandler:
    """
    SMS-based booking and notification system
    Supports simple commands like "BOOK BASKETBALL SAT 3PM"
    """
    
    def __init__(self):
        self.enabled = os.getenv('SMS_ENABLED', 'true').lower() == 'true'
        
        if self.enabled:
            self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
            self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
            self.sms_number = os.getenv('TWILIO_PHONE_NUMBER')
            
            if self.account_sid and self.auth_token and self.sms_number:
                self.client = Client(self.account_sid, self.auth_token)
            else:
                logger.warning("SMS credentials not configured")
                self.enabled = False
    
    def send_sms(self, to_number: str, message: str) -> Dict:
        """
        Send SMS to customer
        
        Args:
            to_number: Customer phone number
            message: Message text (max 160 chars recommended)
            
        Returns:
            Dictionary with send status
        """
        if not self.enabled:
            logger.info("SMS not enabled, skipping message send")
            return {'status': 'disabled'}
        
        try:
            message_obj = self.client.messages.create(
                from_=self.sms_number,
                body=message,
                to=to_number
            )
            
            logger.info(f"SMS sent to {to_number}, SID: {message_obj.sid}")
            
            return {
                'status': 'sent',
                'message_sid': message_obj.sid,
                'to': to_number
            }
            
        except Exception as e:
            logger.error(f"Error sending SMS: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def send_booking_confirmation(self, to_number: str, booking_details: Dict) -> Dict:
        """
        Send booking confirmation SMS
        
        Args:
            to_number: Customer phone number
            booking_details: Booking information
            
        Returns:
            Send status
        """
        message = (
            f"✓ Booking confirmed! "
            f"{booking_details.get('facility', '')} on "
            f"{booking_details.get('date', '')} at "
            f"{booking_details.get('time', '')}. "
            f"ID: {booking_details.get('booking_id', '')}. "
            f"Price: ${booking_details.get('price', '')}"
        )
        
        return self.send_sms(to_number, message)
    
    def send_reminder(self, to_number: str, booking_details: Dict, hours_until: int) -> Dict:
        """
        Send booking reminder SMS
        
        Args:
            to_number: Customer phone number
            booking_details: Booking information
            hours_until: Hours until booking
            
        Returns:
            Send status
        """
        message = (
            f"Reminder: Your {booking_details.get('facility', '')} booking "
            f"is in {hours_until}h at {booking_details.get('time', '')}. "
            f"ID: {booking_details.get('booking_id', '')}. See you soon!"
        )
        
        return self.send_sms(to_number, message)
    
    def send_cancellation(self, to_number: str, booking_id: str) -> Dict:
        """
        Send cancellation confirmation SMS
        
        Args:
            to_number: Customer phone number
            booking_id: Cancelled booking ID
            
        Returns:
            Send status
        """
        message = f"Booking {booking_id} has been cancelled. Hope to see you again soon!"
        
        return self.send_sms(to_number, message)
    
    def parse_booking_command(self, sms_body: str) -> Optional[Dict]:
        """
        Parse SMS booking command
        
        Supported formats:
        - "BOOK BASKETBALL SAT 3PM"
        - "BOOK TENNIS TOMORROW 5PM"
        - "CANCEL 12345"
        - "BALANCE"
        
        Args:
            sms_body: SMS message text
            
        Returns:
            Parsed command dictionary or None
        """
        sms_body = sms_body.upper().strip()
        
        # BOOK command
        if sms_body.startswith('BOOK'):
            match = re.search(r'BOOK\s+(\w+)\s+(\w+)\s+(\d+(?:AM|PM)?)', sms_body)
            if match:
                return {
                    'command': 'book',
                    'facility': match.group(1).lower(),
                    'date': match.group(2).lower(),
                    'time': match.group(3).lower()
                }
        
        # CANCEL command
        elif sms_body.startswith('CANCEL'):
            match = re.search(r'CANCEL\s+(\w+)', sms_body)
            if match:
                return {
                    'command': 'cancel',
                    'booking_id': match.group(1)
                }
        
        # BALANCE command
        elif sms_body.startswith('BALANCE'):
            return {'command': 'balance'}
        
        # SCHEDULE command
        elif sms_body.startswith('SCHEDULE'):
            return {'command': 'schedule'}
        
        # HELP command
        elif sms_body.startswith('HELP'):
            return {'command': 'help'}
        
        return None
    
    def get_help_message(self) -> str:
        """
        Get SMS help message with available commands
        
        Returns:
            Help message text
        """
        return (
            "SMS Commands:\n"
            "BOOK [sport] [day] [time] - Book a facility\n"
            "CANCEL [booking_id] - Cancel booking\n"
            "BALANCE - Check loyalty points\n"
            "SCHEDULE - View your bookings\n"
            "HELP - Show this message"
        )
    
    def handle_incoming_sms(self, from_number: str, sms_body: str) -> Dict:
        """
        Handle incoming SMS from customer
        
        Args:
            from_number: Customer phone number
            sms_body: SMS message text
            
        Returns:
            Response dictionary with action and reply
        """
        parsed = self.parse_booking_command(sms_body)
        
        if not parsed:
            # Unrecognized command
            return {
                'status': 'error',
                'reply': self.get_help_message()
            }
        
        if parsed['command'] == 'help':
            return {
                'status': 'success',
                'reply': self.get_help_message()
            }
        
        # Return parsed command for further processing
        return {
            'status': 'success',
            'command': parsed,
            'from': from_number
        }


# Global instance
_sms_handler = None

def get_sms_handler() -> SMSHandler:
    """Get or create global SMSHandler instance"""
    global _sms_handler
    if _sms_handler is None:
        _sms_handler = SMSHandler()
    return _sms_handler
