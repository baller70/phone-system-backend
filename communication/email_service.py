"""
Email Service - Phase 6
Sends booking confirmation and other emails using SendGrid
"""

import logging
import os
from datetime import datetime
from icalendar import Calendar, Event
import pytz

logger = logging.getLogger(__name__)


class EmailService:
    """Handles all email communications"""
    
    def __init__(self, db_connection=None):
        self.db = db_connection
        self.enabled = bool(os.getenv('SENDGRID_API_KEY'))
        self.from_email = os.getenv('FROM_EMAIL', 'noreply@yoursportsfacility.com')
        self.support_email = os.getenv('SUPPORT_EMAIL', 'support@yoursportsfacility.com')
        
        if self.enabled:
            try:
                from sendgrid import SendGridAPIClient
                from sendgrid.helpers.mail import Mail
                self.sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
                self.Mail = Mail
                logger.info("Email Service: Enabled (SendGrid)")
            except Exception as e:
                logger.error(f"SendGrid initialization failed: {str(e)}")
                self.enabled = False
        else:
            logger.warning("Email Service: Disabled (no SendGrid API key)")
    
    def send_booking_confirmation(self, booking_data):
        """
        Send booking confirmation email with calendar invite
        
        Args:
            booking_data: dict with keys:
                - customer_email
                - customer_name
                - facility_type
                - booking_date
                - booking_time
                - duration_hours
                - price
                - booking_id
                - customer_phone
        
        Returns:
            bool: Success status
        """
        if not self.enabled:
            logger.info("Email service disabled, skipping confirmation email")
            return False
        
        if not booking_data.get('customer_email'):
            logger.info("No customer email provided, skipping")
            return False
        
        try:
            # Create email content
            subject = f"Booking Confirmation - {booking_data['facility_type']}"
            
            html_content = self._generate_booking_confirmation_html(booking_data)
            
            # Create calendar invite
            ical_attachment = self._create_calendar_invite(booking_data)
            
            # Send email
            message = self.Mail(
                from_email=self.from_email,
                to_emails=booking_data['customer_email'],
                subject=subject,
                html_content=html_content
            )
            
            # Attach calendar invite if created
            if ical_attachment:
                message.attachment = ical_attachment
            
            response = self.sg.send(message)
            
            # Log email
            self._log_email(
                booking_data['customer_email'],
                booking_data.get('customer_phone'),
                'booking_confirmation',
                subject,
                booking_data.get('booking_id'),
                response.status_code == 202
            )
            
            logger.info(f"Booking confirmation email sent to {booking_data['customer_email']}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending booking confirmation email: {str(e)}")
            return False
    
    def send_cancellation_email(self, booking_data):
        """Send booking cancellation confirmation"""
        if not self.enabled or not booking_data.get('customer_email'):
            return False
        
        try:
            subject = f"Booking Cancelled - {booking_data['facility_type']}"
            
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #dc2626;">Booking Cancelled</h2>
                <p>Hi {booking_data.get('customer_name', 'there')},</p>
                <p>Your booking has been successfully cancelled:</p>
                
                <div style="background-color: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <p><strong>Facility:</strong> {booking_data['facility_type']}</p>
                    <p><strong>Date:</strong> {booking_data['booking_date']}</p>
                    <p><strong>Time:</strong> {booking_data['booking_time']}</p>
                    <p><strong>Booking ID:</strong> {booking_data.get('booking_id', 'N/A')}</p>
                </div>
                
                <p>If you'd like to book again, feel free to call us or visit our website.</p>
                
                <p style="margin-top: 30px;">Best regards,<br>
                Your Sports Facility Team</p>
                
                <hr style="margin-top: 30px; border: none; border-top: 1px solid #e5e7eb;">
                <p style="font-size: 12px; color: #6b7280;">
                Questions? Contact us at {self.support_email}
                </p>
            </body>
            </html>
            """
            
            message = self.Mail(
                from_email=self.from_email,
                to_emails=booking_data['customer_email'],
                subject=subject,
                html_content=html_content
            )
            
            response = self.sg.send(message)
            
            self._log_email(
                booking_data['customer_email'],
                booking_data.get('customer_phone'),
                'cancellation',
                subject,
                booking_data.get('booking_id'),
                response.status_code == 202
            )
            
            logger.info(f"Cancellation email sent to {booking_data['customer_email']}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending cancellation email: {str(e)}")
            return False
    
    def send_modification_email(self, booking_data):
        """Send booking modification confirmation"""
        if not self.enabled or not booking_data.get('customer_email'):
            return False
        
        try:
            subject = f"Booking Modified - {booking_data['facility_type']}"
            
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #2563eb;">Booking Modified</h2>
                <p>Hi {booking_data.get('customer_name', 'there')},</p>
                <p>Your booking has been successfully modified:</p>
                
                <div style="background-color: #eff6ff; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #1e40af;">New Details</h3>
                    <p><strong>Facility:</strong> {booking_data['facility_type']}</p>
                    <p><strong>Date:</strong> {booking_data['booking_date']}</p>
                    <p><strong>Time:</strong> {booking_data['booking_time']}</p>
                    <p><strong>Duration:</strong> {booking_data['duration_hours']} hours</p>
                    {f"<p><strong>Price:</strong> ${booking_data['price']}</p>" if booking_data.get('price') else ""}
                    <p><strong>Booking ID:</strong> {booking_data.get('booking_id', 'N/A')}</p>
                </div>
                
                <p>We look forward to seeing you!</p>
                
                <p style="margin-top: 30px;">Best regards,<br>
                Your Sports Facility Team</p>
                
                <hr style="margin-top: 30px; border: none; border-top: 1px solid #e5e7eb;">
                <p style="font-size: 12px; color: #6b7280;">
                Questions? Contact us at {self.support_email}
                </p>
            </body>
            </html>
            """
            
            message = self.Mail(
                from_email=self.from_email,
                to_emails=booking_data['customer_email'],
                subject=subject,
                html_content=html_content
            )
            
            response = self.sg.send(message)
            
            self._log_email(
                booking_data['customer_email'],
                booking_data.get('customer_phone'),
                'modification',
                subject,
                booking_data.get('booking_id'),
                response.status_code == 202
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending modification email: {str(e)}")
            return False
    
    def _generate_booking_confirmation_html(self, booking_data):
        """Generate HTML content for booking confirmation"""
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #059669;">Booking Confirmed! 🎉</h2>
            <p>Hi {booking_data.get('customer_name', 'there')},</p>
            <p>Thank you for your booking! Here are your details:</p>
            
            <div style="background-color: #f0fdf4; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #059669;">
                <h3 style="margin-top: 0; color: #065f46;">Booking Details</h3>
                <p><strong>Facility:</strong> {booking_data['facility_type']}</p>
                <p><strong>Date:</strong> {booking_data['booking_date']}</p>
                <p><strong>Time:</strong> {booking_data['booking_time']}</p>
                <p><strong>Duration:</strong> {booking_data['duration_hours']} hours</p>
                {f"<p><strong>Price:</strong> ${booking_data['price']}</p>" if booking_data.get('price') else ""}
                <p><strong>Booking ID:</strong> {booking_data.get('booking_id', 'N/A')}</p>
            </div>
            
            <div style="background-color: #fef3c7; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p style="margin: 0; color: #92400e;">
                <strong>📅 Calendar Invite Attached</strong><br>
                Add this event to your calendar so you don't forget!
                </p>
            </div>
            
            <p style="margin-top: 30px;">We look forward to seeing you! If you need to modify or cancel your booking, please call us.</p>
            
            <p style="margin-top: 30px;">Best regards,<br>
            Your Sports Facility Team</p>
            
            <hr style="margin-top: 30px; border: none; border-top: 1px solid #e5e7eb;">
            <p style="font-size: 12px; color: #6b7280;">
            Questions? Contact us at {self.support_email} or call {booking_data.get('customer_phone', 'us')}
            </p>
        </body>
        </html>
        """
        return html
    
    def _create_calendar_invite(self, booking_data):
        """Create iCalendar (.ics) attachment for booking"""
        try:
            cal = Calendar()
            cal.add('prodid', '-//Sports Facility Booking//EN')
            cal.add('version', '2.0')
            
            event = Event()
            event.add('summary', f"Sports Facility - {booking_data['facility_type']}")
            
            # Parse date and time
            dt_str = f"{booking_data['booking_date']} {booking_data['booking_time']}"
            dt_start = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
            dt_end = dt_start + timedelta(hours=booking_data['duration_hours'])
            
            # Add to event
            event.add('dtstart', dt_start)
            event.add('dtend', dt_end)
            event.add('description', f"Booking ID: {booking_data.get('booking_id', 'N/A')}")
            event.add('location', 'Sports Facility')
            
            cal.add_component(event)
            
            # Create attachment
            from sendgrid.helpers.mail import Attachment, FileContent, FileName, FileType, Disposition
            
            attachment = Attachment()
            attachment.file_content = FileContent(cal.to_ical().decode('utf-8'))
            attachment.file_name = FileName('booking.ics')
            attachment.file_type = FileType('text/calendar')
            attachment.disposition = Disposition('attachment')
            
            return attachment
            
        except Exception as e:
            logger.error(f"Error creating calendar invite: {str(e)}")
            return None
    
    def _log_email(self, recipient_email, recipient_phone, email_type, 
                   subject, booking_id, success):
        """Log email send attempt"""
        if not self.db:
            return
        
        try:
            query = """
            INSERT INTO email_log
            (recipient_email, recipient_phone, email_type, subject, booking_id, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            status = 'sent' if success else 'failed'
            
            self.db.execute(query, (
                recipient_email, recipient_phone, email_type,
                subject, booking_id, status
            ))
        except Exception as e:
            logger.error(f"Error logging email: {str(e)}")


# Global instance
email_service = EmailService()
