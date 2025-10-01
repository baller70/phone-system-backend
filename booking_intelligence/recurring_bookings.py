
"""
Recurring Booking Manager - Phase 6
Handles creation, management, and auto-booking of recurring bookings
"""

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import os
import logging

logger = logging.getLogger(__name__)


class RecurringBookingManager:
    """Manages recurring bookings for customers"""
    
    def __init__(self, db_connection=None):
        """Initialize with optional database connection"""
        self.db = db_connection
        self.enabled = os.getenv('ENABLE_RECURRING_BOOKINGS', 'true').lower() == 'true'
    
    def create_recurring_booking(self, booking_details):
        """
        Create a new recurring booking
        
        Args:
            booking_details: dict with keys:
                - customer_phone
                - customer_email
                - customer_name
                - facility_type
                - day_of_week (0=Monday, 6=Sunday)
                - time_slot (HH:MM format)
                - duration_hours
                - frequency ('weekly', 'biweekly', 'monthly')
                - start_date
                - end_date (optional)
                - price_per_booking
        
        Returns:
            dict: Created recurring booking with id
        """
        if not self.enabled:
            logger.warning("Recurring bookings disabled")
            return None
        
        try:
            # Calculate next booking date
            start_date = datetime.strptime(booking_details['start_date'], '%Y-%m-%d').date()
            next_booking_date = self._calculate_next_booking_date(
                start_date,
                booking_details['day_of_week'],
                booking_details['frequency']
            )
            
            # Store in database (if db available)
            if self.db:
                query = """
                INSERT INTO recurring_bookings 
                (customer_phone, customer_email, customer_name, facility_type, 
                 day_of_week, time_slot, duration_hours, frequency, 
                 start_date, end_date, next_booking_date, price_per_booking, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true)
                RETURNING id, next_booking_date
                """
                
                result = self.db.execute(query, (
                    booking_details['customer_phone'],
                    booking_details.get('customer_email'),
                    booking_details.get('customer_name'),
                    booking_details['facility_type'],
                    booking_details['day_of_week'],
                    booking_details['time_slot'],
                    booking_details['duration_hours'],
                    booking_details['frequency'],
                    booking_details['start_date'],
                    booking_details.get('end_date'),
                    next_booking_date,
                    booking_details.get('price_per_booking', 0)
                ))
                
                row = result.fetchone()
                return {
                    'id': row[0],
                    'next_booking_date': row[1],
                    **booking_details
                }
            
            # In-memory fallback
            return {
                'id': 'temp_' + booking_details['customer_phone'],
                'next_booking_date': next_booking_date,
                **booking_details
            }
            
        except Exception as e:
            logger.error(f"Error creating recurring booking: {str(e)}")
            return None
    
    def _calculate_next_booking_date(self, start_date, day_of_week, frequency):
        """Calculate the next booking date based on frequency"""
        # Find the first occurrence of day_of_week after start_date
        days_ahead = day_of_week - start_date.weekday()
        if days_ahead < 0:
            days_ahead += 7
        
        next_date = start_date + timedelta(days=days_ahead)
        
        # Adjust for frequency
        if frequency == 'biweekly':
            next_date += timedelta(weeks=2)
        elif frequency == 'monthly':
            next_date += relativedelta(months=1)
        
        return next_date
    
    def get_customer_recurring_bookings(self, customer_phone):
        """Get all active recurring bookings for a customer"""
        if not self.db:
            return []
        
        try:
            query = """
            SELECT id, facility_type, day_of_week, time_slot, duration_hours, 
                   frequency, start_date, end_date, next_booking_date, 
                   price_per_booking, total_bookings_created
            FROM recurring_bookings
            WHERE customer_phone = %s AND is_active = true
            ORDER BY next_booking_date
            """
            
            result = self.db.execute(query, (customer_phone,))
            rows = result.fetchall()
            
            bookings = []
            for row in rows:
                bookings.append({
                    'id': row[0],
                    'facility_type': row[1],
                    'day_of_week': row[2],
                    'time_slot': str(row[3]),
                    'duration_hours': float(row[4]),
                    'frequency': row[5],
                    'start_date': str(row[6]),
                    'end_date': str(row[7]) if row[7] else None,
                    'next_booking_date': str(row[8]),
                    'price_per_booking': float(row[9]) if row[9] else 0,
                    'total_bookings_created': row[10]
                })
            
            return bookings
            
        except Exception as e:
            logger.error(f"Error fetching recurring bookings: {str(e)}")
            return []
    
    def pause_recurring_booking(self, booking_id):
        """Pause a recurring booking"""
        if not self.db:
            return False
        
        try:
            query = "UPDATE recurring_bookings SET is_active = false WHERE id = %s"
            self.db.execute(query, (booking_id,))
            logger.info(f"Paused recurring booking {booking_id}")
            return True
        except Exception as e:
            logger.error(f"Error pausing recurring booking: {str(e)}")
            return False
    
    def resume_recurring_booking(self, booking_id):
        """Resume a paused recurring booking"""
        if not self.db:
            return False
        
        try:
            query = "UPDATE recurring_bookings SET is_active = true WHERE id = %s"
            self.db.execute(query, (booking_id,))
            logger.info(f"Resumed recurring booking {booking_id}")
            return True
        except Exception as e:
            logger.error(f"Error resuming recurring booking: {str(e)}")
            return False
    
    def delete_recurring_booking(self, booking_id):
        """Delete a recurring booking"""
        if not self.db:
            return False
        
        try:
            query = "DELETE FROM recurring_bookings WHERE id = %s"
            self.db.execute(query, (booking_id,))
            logger.info(f"Deleted recurring booking {booking_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting recurring booking: {str(e)}")
            return False
    
    def get_due_recurring_bookings(self, lookahead_days=7):
        """Get recurring bookings that need to be created in the next N days"""
        if not self.db:
            return []
        
        try:
            future_date = datetime.now().date() + timedelta(days=lookahead_days)
            
            query = """
            SELECT id, customer_phone, customer_email, customer_name, 
                   facility_type, time_slot, duration_hours, next_booking_date,
                   price_per_booking, frequency, day_of_week
            FROM recurring_bookings
            WHERE is_active = true 
            AND next_booking_date <= %s
            AND (end_date IS NULL OR end_date >= %s)
            ORDER BY next_booking_date
            """
            
            result = self.db.execute(query, (future_date, datetime.now().date()))
            rows = result.fetchall()
            
            bookings = []
            for row in rows:
                bookings.append({
                    'id': row[0],
                    'customer_phone': row[1],
                    'customer_email': row[2],
                    'customer_name': row[3],
                    'facility_type': row[4],
                    'time_slot': str(row[5]),
                    'duration_hours': float(row[6]),
                    'next_booking_date': str(row[7]),
                    'price_per_booking': float(row[8]) if row[8] else 0,
                    'frequency': row[9],
                    'day_of_week': row[10]
                })
            
            return bookings
            
        except Exception as e:
            logger.error(f"Error fetching due recurring bookings: {str(e)}")
            return []
    
    def update_after_booking_created(self, recurring_booking_id, calcom_booking_id):
        """Update recurring booking after a booking is created"""
        if not self.db:
            return False
        
        try:
            # Get current recurring booking
            query = "SELECT frequency, day_of_week, next_booking_date FROM recurring_bookings WHERE id = %s"
            result = self.db.execute(query, (recurring_booking_id,))
            row = result.fetchone()
            
            if not row:
                return False
            
            frequency, day_of_week, current_next_date = row
            
            # Calculate new next booking date
            if frequency == 'weekly':
                new_next_date = current_next_date + timedelta(weeks=1)
            elif frequency == 'biweekly':
                new_next_date = current_next_date + timedelta(weeks=2)
            elif frequency == 'monthly':
                new_next_date = current_next_date + relativedelta(months=1)
            else:
                new_next_date = current_next_date + timedelta(weeks=1)
            
            # Update recurring booking
            update_query = """
            UPDATE recurring_bookings 
            SET next_booking_date = %s, 
                total_bookings_created = total_bookings_created + 1,
                updated_at = NOW()
            WHERE id = %s
            """
            self.db.execute(update_query, (new_next_date, recurring_booking_id))
            
            logger.info(f"Updated recurring booking {recurring_booking_id}, next date: {new_next_date}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating recurring booking: {str(e)}")
            return False


# Global instance
recurring_booking_manager = RecurringBookingManager()
