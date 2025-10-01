"""
Waitlist Notifier Job - Phase 6
Background job to notify waitlisted customers when slots become available
"""

import logging

logger = logging.getLogger(__name__)


class WaitlistNotifierJob:
    """Background job to check for available slots and notify waitlist"""
    
    def __init__(self, waitlist_manager, calcom_helper, sms_service, db_connection=None):
        self.waitlist = waitlist_manager
        self.calcom = calcom_helper
        self.sms = sms_service
        self.db = db_connection
    
    def run(self):
        """
        Check for available slots and notify waiting customers
        
        Returns:
            dict: Stats about notifications sent
        """
        try:
            # First, expire old notifications
            expired_count = self.waitlist.expire_old_notifications()
            
            # Get all active waitlist entries
            # (In production, would query unique facility/date/time combinations)
            if not self.db:
                return {'notifications': 0, 'expired': expired_count}
            
            query = """
            SELECT DISTINCT facility_type, requested_date, requested_time
            FROM waitlist
            WHERE status = 'waiting'
            AND requested_date >= CURRENT_DATE
            ORDER BY requested_date, requested_time
            """
            
            result = self.db.execute(query)
            rows = result.fetchall()
            
            notifications_sent = 0
            
            for row in rows:
                facility_type, requested_date, requested_time = row
                
                # Check if slot is now available
                is_available = self.calcom.check_availability(
                    facility_type,
                    str(requested_date),
                    str(requested_time),
                    2  # Assume 2 hour duration
                )
                
                if is_available:
                    # Notify next person in waitlist
                    notified_customer = self.waitlist.notify_next_in_waitlist(
                        facility_type,
                        str(requested_date),
                        str(requested_time)
                    )
                    
                    if notified_customer:
                        # Send SMS notification
                        self._send_waitlist_notification(notified_customer)
                        notifications_sent += 1
            
            logger.info(f"Waitlist notifier job complete: {notifications_sent} notifications, {expired_count} expired")
            
            return {
                'notifications': notifications_sent,
                'expired': expired_count
            }
            
        except Exception as e:
            logger.error(f"Error in waitlist notifier job: {str(e)}")
            return {'error': str(e)}
    
    def _send_waitlist_notification(self, customer_data):
        """Send SMS notification to waitlisted customer"""
        if not self.sms:
            logger.warning("SMS service not available")
            return False
        
        try:
            message = f"🎉 Good news! Your requested time slot is now available:\n\n"
            message += f"Facility: {customer_data['facility_type']}\n"
            message += f"Date: {customer_data['requested_date']}\n"
            message += f"Time: {customer_data['requested_time']}\n\n"
            message += f"Call us now to book this slot! You have 24 hours to claim it."
            
            self.sms.send_sms(customer_data['customer_phone'], message)
            logger.info(f"Waitlist notification sent to {customer_data['customer_phone']}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending waitlist notification: {str(e)}")
            return False


# Factory function
def create_waitlist_notifier_job(waitlist_manager, calcom_helper, sms_service, db_connection=None):
    return WaitlistNotifierJob(waitlist_manager, calcom_helper, sms_service, db_connection)
