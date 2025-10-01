
"""
SMS Service for sending booking confirmations and notifications
Uses Twilio for SMS delivery
"""
import os
from twilio.rest import Client
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SMSService:
    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.from_number = os.getenv('TWILIO_PHONE_NUMBER')
        
        # Only initialize Twilio if credentials are provided
        self.enabled = bool(self.account_sid and self.auth_token and self.from_number)
        
        if self.enabled:
            try:
                self.client = Client(self.account_sid, self.auth_token)
                logger.info("SMS Service initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize SMS service: {e}")
                self.enabled = False
        else:
            logger.warning("SMS Service disabled - Missing Twilio credentials")
    
    def send_booking_confirmation(self, to_number, booking_details):
        """
        Send booking confirmation SMS
        
        Args:
            to_number: Customer phone number
            booking_details: Dict with facility, date, time, duration, price
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.warning("SMS service not enabled - skipping SMS")
            return False
        
        try:
            # Format booking details into message
            message = self._format_booking_confirmation(booking_details)
            
            # Send SMS
            result = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_number
            )
            
            logger.info(f"Booking confirmation SMS sent to {to_number}: {result.sid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send booking confirmation SMS: {e}")
            return False
    
    def send_booking_update(self, to_number, update_type, booking_details):
        """
        Send booking update SMS (cancellation, rescheduling, etc.)
        
        Args:
            to_number: Customer phone number
            update_type: 'cancelled', 'rescheduled', 'modified'
            booking_details: Dict with booking information
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.warning("SMS service not enabled - skipping SMS")
            return False
        
        try:
            message = self._format_booking_update(update_type, booking_details)
            
            result = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_number
            )
            
            logger.info(f"Booking update SMS sent to {to_number}: {result.sid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send booking update SMS: {e}")
            return False
    
    def send_waitlist_notification(self, to_number, facility, available_slot):
        """
        Notify customer that a waitlisted slot is now available
        
        Args:
            to_number: Customer phone number
            facility: Facility name
            available_slot: Available time slot details
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.warning("SMS service not enabled - skipping SMS")
            return False
        
        try:
            message = f"""🎉 Good news! A spot just opened up!

Facility: {facility}
Available: {available_slot}

Reply or call us to book this slot. First come, first served!"""
            
            result = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_number
            )
            
            logger.info(f"Waitlist notification SMS sent to {to_number}: {result.sid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send waitlist notification SMS: {e}")
            return False
    
    def _format_booking_confirmation(self, booking_details):
        """Format booking confirmation message"""
        facility = booking_details.get('facility', 'Facility')
        date = booking_details.get('date', '')
        time = booking_details.get('time', '')
        duration = booking_details.get('duration', '')
        price = booking_details.get('price', '')
        booking_id = booking_details.get('booking_id', '')
        
        message = f"""✅ Booking Confirmed!

Facility: {facility}
Date: {date}
Time: {time}
Duration: {duration}
Price: ${price}

Booking ID: {booking_id}

See you there! Call us if you need to make changes."""
        
        return message
    
    def _format_booking_update(self, update_type, booking_details):
        """Format booking update message"""
        facility = booking_details.get('facility', 'Facility')
        
        if update_type == 'cancelled':
            message = f"""❌ Booking Cancelled

Your booking for {facility} has been cancelled.

Booking ID: {booking_details.get('booking_id', '')}

We hope to see you again soon!"""
        
        elif update_type == 'rescheduled':
            message = f"""🔄 Booking Rescheduled

Facility: {facility}
New Date: {booking_details.get('date', '')}
New Time: {booking_details.get('time', '')}

Booking ID: {booking_details.get('booking_id', '')}

See you at the new time!"""
        
        else:
            message = f"""✏️ Booking Updated

Your booking for {facility} has been updated.

Booking ID: {booking_details.get('booking_id', '')}

Check your email for full details."""
        
        return message

# Global SMS service instance
sms_service = SMSService()
