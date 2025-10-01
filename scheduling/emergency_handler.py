"""
Emergency Handler - Phase 6
Handles emergency priority bookings
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class EmergencyHandler:
    """Handles emergency priority bookings"""
    
    def __init__(self, db_connection=None, sms_service=None):
        self.db = db_connection
        self.sms = sms_service
    
    def create_emergency_booking(self, booking_data):
        """
        Create an emergency priority booking
        
        Args:
            booking_data: dict with keys:
                - conversation_uuid
                - customer_phone
                - customer_name
                - facility_type
                - booking_date
                - booking_time
                - urgency_level ('high' or 'critical')
                - reason
        
        Returns:
            dict: Emergency booking details
        """
        if not self.db:
            logger.warning("No DB connection, emergency booking not saved")
            return None
        
        try:
            query = """
            INSERT INTO emergency_bookings
            (conversation_uuid, customer_phone, customer_name, facility_type,
             booking_date, booking_time, urgency_level, reason, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pending')
            RETURNING id
            """
            
            result = self.db.execute(query, (
                booking_data['conversation_uuid'],
                booking_data['customer_phone'],
                booking_data.get('customer_name'),
                booking_data['facility_type'],
                booking_data['booking_date'],
                booking_data['booking_time'],
                booking_data.get('urgency_level', 'high'),
                booking_data.get('reason')
            ))
            
            emergency_id = result.fetchone()[0]
            
            logger.warning(f"Emergency booking created: {emergency_id}")
            
            # Notify staff
            self._notify_staff(booking_data)
            
            return {
                'id': emergency_id,
                'status': 'pending',
                **booking_data
            }
            
        except Exception as e:
            logger.error(f"Error creating emergency booking: {str(e)}")
            return None
    
    def _notify_staff(self, booking_data):
        """Send emergency notification to staff"""
        if not self.sms:
            logger.warning("SMS service not available, staff not notified")
            return False
        
        try:
            import os
            staff_phone = os.getenv('STAFF_PHONE_NUMBER')
            
            if not staff_phone:
                logger.warning("No staff phone number configured")
                return False
            
            message = f"🚨 EMERGENCY BOOKING REQUEST\n\n"
            message += f"Customer: {booking_data.get('customer_name', 'Unknown')}\n"
            message += f"Phone: {booking_data['customer_phone']}\n"
            message += f"Facility: {booking_data['facility_type']}\n"
            message += f"Date/Time: {booking_data['booking_date']} at {booking_data['booking_time']}\n"
            message += f"Urgency: {booking_data.get('urgency_level', 'high').upper()}\n"
            message += f"Reason: {booking_data.get('reason', 'Not specified')}\n\n"
            message += f"Please handle this request immediately."
            
            self.sms.send_sms(staff_phone, message)
            
            # Update notification status
            if self.db:
                update_query = """
                UPDATE emergency_bookings
                SET staff_notified = true, staff_notification_sent_at = NOW()
                WHERE conversation_uuid = %s
                """
                self.db.execute(update_query, (booking_data['conversation_uuid'],))
            
            logger.info(f"Staff notified of emergency booking")
            return True
            
        except Exception as e:
            logger.error(f"Error notifying staff: {str(e)}")
            return False
    
    def resolve_emergency(self, emergency_id, calcom_booking_id=None):
        """Mark emergency as resolved"""
        if not self.db:
            return False
        
        try:
            query = """
            UPDATE emergency_bookings
            SET status = 'resolved', 
                resolved_at = NOW(),
                calcom_booking_id = %s
            WHERE id = %s
            """
            self.db.execute(query, (calcom_booking_id, emergency_id))
            logger.info(f"Emergency booking {emergency_id} resolved")
            return True
        except Exception as e:
            logger.error(f"Error resolving emergency: {str(e)}")
            return False


# Global instance
emergency_handler = EmergencyHandler()
