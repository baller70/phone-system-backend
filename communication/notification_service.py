
"""
Smart Notification Service - Phase 9
Sends automated reminders, confirmations via Email (Resend) and SMS (Vonage)
"""

import os
import logging
import json
from datetime import datetime, timedelta
import requests

logger = logging.getLogger(__name__)


class NotificationService:
    """Handles all customer notifications"""
    
    def __init__(self, db_connection=None):
        self.db = db_connection
        
        # Load Resend API key from auth secrets
        self.resend_api_key = None
        self._load_resend_credentials()
        
        self.vonage_api_key = os.getenv('VONAGE_API_KEY')
        self.vonage_api_secret = os.getenv('VONAGE_API_SECRET')
        self.from_email = os.getenv('FROM_EMAIL', 'bookings@sportsfacility.com')
        self.from_phone = os.getenv('FROM_PHONE', '+1234567890')
        
        self.email_enabled = bool(self.resend_api_key)
        self.sms_enabled = bool(self.vonage_api_key and self.vonage_api_secret)
        
        if self.email_enabled:
            logger.info("Email notifications enabled (Resend)")
        else:
            logger.warning("Email notifications disabled (missing Resend API key)")
        
        if self.sms_enabled:
            logger.info("SMS notifications enabled (Vonage)")
        else:
            logger.warning("SMS notifications disabled (missing Vonage credentials)")
    
    def _load_resend_credentials(self):
        """Load Resend API key from auth secrets"""
        try:
            secrets_path = '/home/ubuntu/.config/abacusai_auth_secrets.json'
            
            if os.path.exists(secrets_path):
                with open(secrets_path, 'r') as f:
                    secrets = json.load(f)
                
                resend_secrets = secrets.get('resend', {}).get('secrets', {})
                self.resend_api_key = resend_secrets.get('api_key', {}).get('value')
                
                if self.resend_api_key:
                    logger.info("Resend API key loaded successfully")
                else:
                    logger.warning("Resend API key not found in secrets file")
            else:
                logger.warning(f"Secrets file not found: {secrets_path}")
                
        except Exception as e:
            logger.error(f"Error loading Resend credentials: {str(e)}")
    
    def send_booking_confirmation(self, booking_data):
        """
        Send booking confirmation via email and/or SMS
        
        Args:
            booking_data: dict with booking details
        """
        success = {'email': False, 'sms': False}
        
        # Send email
        if self.email_enabled and booking_data.get('customer_email'):
            success['email'] = self._send_confirmation_email(booking_data)
        
        # Send SMS
        if self.sms_enabled and booking_data.get('customer_phone'):
            success['sms'] = self._send_confirmation_sms(booking_data)
        
        return success
    
    def send_reminder(self, booking_data, hours_before=24):
        """
        Send booking reminder
        
        Args:
            booking_data: dict with booking details
            hours_before: hours before booking to send reminder
        """
        success = {'email': False, 'sms': False}
        
        # Send email reminder
        if self.email_enabled and booking_data.get('customer_email'):
            success['email'] = self._send_reminder_email(booking_data, hours_before)
        
        # Send SMS reminder
        if self.sms_enabled and booking_data.get('customer_phone'):
            success['sms'] = self._send_reminder_sms(booking_data, hours_before)
        
        # Log reminder
        self._log_notification(
            booking_data.get('booking_id'),
            'reminder',
            success['email'] or success['sms']
        )
        
        return success
    
    def _send_confirmation_email(self, booking_data):
        """Send confirmation email via Resend"""
        try:
            url = 'https://api.resend.com/emails'
            
            headers = {
                'Authorization': f'Bearer {self.resend_api_key}',
                'Content-Type': 'application/json'
            }
            
            html_content = self._generate_confirmation_email_html(booking_data)
            
            data = {
                'from': self.from_email,
                'to': booking_data['customer_email'],
                'subject': f"✅ Booking Confirmed - {booking_data['facility_type']}",
                'html': html_content
            }
            
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                logger.info(f"Confirmation email sent to {booking_data['customer_email']}")
                self._log_notification(
                    booking_data.get('booking_id'),
                    'confirmation_email',
                    True
                )
                return True
            else:
                logger.error(f"Failed to send email: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending confirmation email: {str(e)}")
            return False
    
    def _send_confirmation_sms(self, booking_data):
        """Send confirmation SMS via Vonage"""
        try:
            url = 'https://rest.nexmo.com/sms/json'
            
            message = f"✅ Booking Confirmed!\n"
            message += f"Facility: {booking_data['facility_type']}\n"
            message += f"Date: {booking_data['booking_date']} at {booking_data['booking_time']}\n"
            message += f"Duration: {booking_data['duration_hours']}hrs\n"
            message += f"Booking ID: {booking_data.get('booking_id', 'N/A')}"
            
            data = {
                'api_key': self.vonage_api_key,
                'api_secret': self.vonage_api_secret,
                'from': self.from_phone,
                'to': booking_data['customer_phone'],
                'text': message
            }
            
            response = requests.post(url, data=data)
            result = response.json()
            
            if result['messages'][0]['status'] == '0':
                logger.info(f"Confirmation SMS sent to {booking_data['customer_phone']}")
                self._log_notification(
                    booking_data.get('booking_id'),
                    'confirmation_sms',
                    True
                )
                return True
            else:
                logger.error(f"Failed to send SMS: {result['messages'][0].get('error-text')}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending confirmation SMS: {str(e)}")
            return False
    
    def _send_reminder_email(self, booking_data, hours_before):
        """Send reminder email"""
        try:
            url = 'https://api.resend.com/emails'
            
            headers = {
                'Authorization': f'Bearer {self.resend_api_key}',
                'Content-Type': 'application/json'
            }
            
            html_content = self._generate_reminder_email_html(booking_data, hours_before)
            
            data = {
                'from': self.from_email,
                'to': booking_data['customer_email'],
                'subject': f"⏰ Reminder: Your booking is in {hours_before} hours!",
                'html': html_content
            }
            
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                logger.info(f"Reminder email sent to {booking_data['customer_email']}")
                return True
            else:
                logger.error(f"Failed to send reminder email: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending reminder email: {str(e)}")
            return False
    
    def _send_reminder_sms(self, booking_data, hours_before):
        """Send reminder SMS"""
        try:
            url = 'https://rest.nexmo.com/sms/json'
            
            message = f"⏰ Reminder: Your booking is in {hours_before} hours!\n"
            message += f"Facility: {booking_data['facility_type']}\n"
            message += f"Date: {booking_data['booking_date']} at {booking_data['booking_time']}\n"
            message += f"See you soon!"
            
            data = {
                'api_key': self.vonage_api_key,
                'api_secret': self.vonage_api_secret,
                'from': self.from_phone,
                'to': booking_data['customer_phone'],
                'text': message
            }
            
            response = requests.post(url, data=data)
            result = response.json()
            
            if result['messages'][0]['status'] == '0':
                logger.info(f"Reminder SMS sent to {booking_data['customer_phone']}")
                return True
            else:
                logger.error(f"Failed to send reminder SMS: {result['messages'][0].get('error-text')}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending reminder SMS: {str(e)}")
            return False
    
    def _generate_confirmation_email_html(self, booking_data):
        """Generate HTML for confirmation email"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f5f5f5;">
            <div style="background-color: #ffffff; border-radius: 12px; padding: 32px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <h1 style="color: #10b981; margin-top: 0; font-size: 28px;">✅ Booking Confirmed!</h1>
                
                <p style="color: #374151; font-size: 16px;">Hi {booking_data.get('customer_name', 'there')},</p>
                
                <p style="color: #374151; font-size: 16px;">Great news! Your booking has been confirmed. Here are the details:</p>
                
                <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 24px; border-radius: 8px; margin: 24px 0;">
                    <h2 style="margin: 0 0 16px 0; font-size: 20px;">Booking Details</h2>
                    <table style="width: 100%; color: white;">
                        <tr>
                            <td style="padding: 8px 0;"><strong>Facility:</strong></td>
                            <td style="padding: 8px 0; text-align: right;">{booking_data['facility_type']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;"><strong>Date:</strong></td>
                            <td style="padding: 8px 0; text-align: right;">{booking_data['booking_date']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;"><strong>Time:</strong></td>
                            <td style="padding: 8px 0; text-align: right;">{booking_data['booking_time']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;"><strong>Duration:</strong></td>
                            <td style="padding: 8px 0; text-align: right;">{booking_data['duration_hours']} hours</td>
                        </tr>
                        {f'''<tr>
                            <td style="padding: 8px 0;"><strong>Price:</strong></td>
                            <td style="padding: 8px 0; text-align: right;">${booking_data['price']}</td>
                        </tr>''' if booking_data.get('price') else ''}
                        <tr>
                            <td style="padding: 8px 0;"><strong>Booking ID:</strong></td>
                            <td style="padding: 8px 0; text-align: right; font-family: monospace;">{booking_data.get('booking_id', 'N/A')}</td>
                        </tr>
                    </table>
                </div>
                
                <div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 16px; border-radius: 4px; margin: 24px 0;">
                    <p style="margin: 0; color: #92400e; font-size: 14px;">
                        <strong>📅 Add to Calendar</strong><br>
                        Don't forget to add this to your calendar so you don't miss it!
                    </p>
                </div>
                
                <p style="color: #374151; font-size: 16px; margin-top: 24px;">
                    We look forward to seeing you! If you need to cancel or reschedule, please call us or use your customer portal.
                </p>
                
                <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 32px 0;">
                
                <p style="color: #6b7280; font-size: 14px; margin: 0;">
                    Questions? Contact us at support@sportsfacility.com<br>
                    <small>Booking ID: {booking_data.get('booking_id', 'N/A')}</small>
                </p>
            </div>
        </body>
        </html>
        """
    
    def _generate_reminder_email_html(self, booking_data, hours_before):
        """Generate HTML for reminder email"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f5f5f5;">
            <div style="background-color: #ffffff; border-radius: 12px; padding: 32px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                <h1 style="color: #f59e0b; margin-top: 0; font-size: 28px;">⏰ Booking Reminder</h1>
                
                <p style="color: #374151; font-size: 16px;">Hi {booking_data.get('customer_name', 'there')},</p>
                
                <p style="color: #374151; font-size: 16px;">
                    This is a friendly reminder that your booking is coming up in <strong>{hours_before} hours</strong>!
                </p>
                
                <div style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: white; padding: 24px; border-radius: 8px; margin: 24px 0;">
                    <h2 style="margin: 0 0 16px 0; font-size: 20px;">Your Booking</h2>
                    <table style="width: 100%; color: white;">
                        <tr>
                            <td style="padding: 8px 0;"><strong>Facility:</strong></td>
                            <td style="padding: 8px 0; text-align: right;">{booking_data['facility_type']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;"><strong>Date:</strong></td>
                            <td style="padding: 8px 0; text-align: right;">{booking_data['booking_date']}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;"><strong>Time:</strong></td>
                            <td style="padding: 8px 0; text-align: right;">{booking_data['booking_time']}</td>
                        </tr>
                    </table>
                </div>
                
                <p style="color: #374151; font-size: 16px;">
                    See you soon! If you need to cancel or make changes, please contact us as soon as possible.
                </p>
                
                <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 32px 0;">
                
                <p style="color: #6b7280; font-size: 14px; margin: 0;">
                    Questions? Contact us at support@sportsfacility.com<br>
                    <small>Booking ID: {booking_data.get('booking_id', 'N/A')}</small>
                </p>
            </div>
        </body>
        </html>
        """
    
    def _log_notification(self, booking_id, notification_type, success):
        """Log notification send attempt"""
        if not self.db:
            return
        
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO notifications_log
                (booking_id, notification_type, status, sent_at)
                VALUES (?, ?, ?, ?)
            """, (
                booking_id,
                notification_type,
                'sent' if success else 'failed',
                datetime.now().isoformat()
            ))
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error logging notification: {str(e)}")
    
    def schedule_reminder(self, booking_data, hours_before=24):
        """
        Schedule a reminder to be sent before booking
        
        Args:
            booking_data: dict with booking details
            hours_before: hours before booking to send reminder
        """
        if not self.db:
            return False
        
        try:
            # Calculate when to send reminder
            booking_datetime = datetime.strptime(
                f"{booking_data['booking_date']} {booking_data['booking_time']}",
                "%Y-%m-%d %H:%M"
            )
            reminder_time = booking_datetime - timedelta(hours=hours_before)
            
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO scheduled_notifications
                (booking_id, notification_type, scheduled_time, booking_data, status)
                VALUES (?, ?, ?, ?, ?)
            """, (
                booking_data.get('booking_id'),
                'reminder',
                reminder_time.isoformat(),
                json.dumps(booking_data),
                'pending'
            ))
            self.db.commit()
            
            logger.info(f"Reminder scheduled for {reminder_time}")
            return True
            
        except Exception as e:
            logger.error(f"Error scheduling reminder: {str(e)}")
            return False
    
    def process_scheduled_notifications(self):
        """Process all pending scheduled notifications"""
        if not self.db:
            return
        
        try:
            cursor = self.db.cursor()
            
            # Get all pending notifications that are due
            cursor.execute("""
                SELECT id, booking_id, notification_type, booking_data
                FROM scheduled_notifications
                WHERE status = 'pending'
                AND scheduled_time <= ?
            """, (datetime.now().isoformat(),))
            
            pending = cursor.fetchall()
            
            for notification in pending:
                notif_id, booking_id, notif_type, booking_data_json = notification
                booking_data = json.loads(booking_data_json)
                
                # Send notification
                if notif_type == 'reminder':
                    success = self.send_reminder(booking_data)
                else:
                    success = False
                
                # Update status
                cursor.execute("""
                    UPDATE scheduled_notifications
                    SET status = ?, sent_at = ?
                    WHERE id = ?
                """, (
                    'sent' if success else 'failed',
                    datetime.now().isoformat(),
                    notif_id
                ))
            
            self.db.commit()
            logger.info(f"Processed {len(pending)} scheduled notifications")
            
        except Exception as e:
            logger.error(f"Error processing scheduled notifications: {str(e)}")


# Global notification service instance
notification_service = NotificationService()
