"""
Recurring Booking Creator Job - Phase 6
Background job to create upcoming recurring bookings
"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RecurringBookingCreatorJob:
    """Background job to create upcoming recurring bookings"""
    
    def __init__(self, recurring_manager, calcom_helper, db_connection=None):
        self.recurring_manager = recurring_manager
        self.calcom = calcom_helper
        self.db = db_connection
    
    def run(self, lookahead_days=7):
        """
        Create bookings for all due recurring bookings
        
        Args:
            lookahead_days: How many days ahead to look for due bookings
        
        Returns:
            dict: Stats about created bookings
        """
        try:
            # Get due recurring bookings
            due_bookings = self.recurring_manager.get_due_recurring_bookings(lookahead_days)
            
            if not due_bookings:
                logger.info("No recurring bookings due")
                return {'created': 0, 'failed': 0, 'skipped': 0}
            
            stats = {'created': 0, 'failed': 0, 'skipped': 0}
            
            for recurring_booking in due_bookings:
                try:
                    # Create Cal.com booking
                    booking_result = self.calcom.create_booking(
                        facility_type=recurring_booking['facility_type'],
                        date=recurring_booking['next_booking_date'],
                        time=recurring_booking['time_slot'],
                        duration_hours=recurring_booking['duration_hours'],
                        customer_name=recurring_booking.get('customer_name', 'Recurring Customer'),
                        customer_email=recurring_booking.get('customer_email', ''),
                        customer_phone=recurring_booking['customer_phone'],
                        notes=f"Recurring booking (ID: {recurring_booking['id']})"
                    )
                    
                    if booking_result and booking_result.get('success'):
                        # Update recurring booking
                        self.recurring_manager.update_after_booking_created(
                            recurring_booking['id'],
                            booking_result.get('booking_id')
                        )
                        stats['created'] += 1
                        logger.info(f"Created recurring booking for {recurring_booking['customer_phone']}")
                    else:
                        stats['failed'] += 1
                        logger.warning(f"Failed to create recurring booking: {booking_result.get('error')}")
                
                except Exception as e:
                    stats['failed'] += 1
                    logger.error(f"Error processing recurring booking {recurring_booking['id']}: {str(e)}")
            
            logger.info(f"Recurring booking job complete: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error in recurring booking creator job: {str(e)}")
            return {'error': str(e)}


# Factory function
def create_recurring_booking_job(recurring_manager, calcom_helper, db_connection=None):
    return RecurringBookingCreatorJob(recurring_manager, calcom_helper, db_connection)
