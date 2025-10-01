"""
Waitlist Manager - Phase 6
Handles waitlist for fully booked time slots
"""

from datetime import datetime, timedelta
import logging
import os

logger = logging.getLogger(__name__)


class WaitlistManager:
    """Manages waitlist for fully booked time slots"""
    
    def __init__(self, db_connection=None):
        self.db = db_connection
        self.enabled = os.getenv('ENABLE_WAITLIST', 'true').lower() == 'true'
        self.notification_window_hours = int(os.getenv('WAITLIST_NOTIFICATION_WINDOW_HOURS', '24'))
    
    def add_to_waitlist(self, waitlist_data):
        """
        Add customer to waitlist for a time slot
        
        Args:
            waitlist_data: dict with keys:
                - customer_phone
                - customer_email (optional)
                - customer_name (optional)
                - facility_type
                - requested_date
                - requested_time
                - duration_hours
        
        Returns:
            dict: Waitlist entry with id and priority
        """
        if not self.enabled:
            logger.warning("Waitlist disabled")
            return None
        
        if not self.db:
            logger.warning("No database connection, waitlist entry not saved")
            return None
        
        try:
            # Calculate next priority number (FIFO)
            priority_query = """
            SELECT COALESCE(MAX(priority), -1) + 1
            FROM waitlist
            WHERE facility_type = %s 
            AND requested_date = %s 
            AND requested_time = %s
            AND status = 'waiting'
            """
            
            result = self.db.execute(priority_query, (
                waitlist_data['facility_type'],
                waitlist_data['requested_date'],
                waitlist_data['requested_time']
            ))
            priority = result.fetchone()[0]
            
            # Insert waitlist entry
            insert_query = """
            INSERT INTO waitlist 
            (customer_phone, customer_email, customer_name, facility_type,
             requested_date, requested_time, duration_hours, priority, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'waiting')
            RETURNING id, priority
            """
            
            result = self.db.execute(insert_query, (
                waitlist_data['customer_phone'],
                waitlist_data.get('customer_email'),
                waitlist_data.get('customer_name'),
                waitlist_data['facility_type'],
                waitlist_data['requested_date'],
                waitlist_data['requested_time'],
                waitlist_data['duration_hours'],
                priority
            ))
            
            row = result.fetchone()
            
            logger.info(f"Added {waitlist_data['customer_phone']} to waitlist (priority {priority})")
            
            return {
                'id': row[0],
                'priority': row[1],
                'position': priority + 1,  # Human-readable position (1-indexed)
                **waitlist_data
            }
            
        except Exception as e:
            logger.error(f"Error adding to waitlist: {str(e)}")
            return None
    
    def get_waitlist_for_slot(self, facility_type, requested_date, requested_time):
        """Get all waiting customers for a specific slot"""
        if not self.db:
            return []
        
        try:
            query = """
            SELECT id, customer_phone, customer_email, customer_name, 
                   duration_hours, priority, created_at
            FROM waitlist
            WHERE facility_type = %s 
            AND requested_date = %s 
            AND requested_time = %s
            AND status = 'waiting'
            ORDER BY priority ASC
            """
            
            result = self.db.execute(query, (facility_type, requested_date, requested_time))
            rows = result.fetchall()
            
            entries = []
            for idx, row in enumerate(rows):
                entries.append({
                    'id': row[0],
                    'customer_phone': row[1],
                    'customer_email': row[2],
                    'customer_name': row[3],
                    'duration_hours': float(row[4]),
                    'priority': row[5],
                    'position': idx + 1,
                    'created_at': str(row[6])
                })
            
            return entries
            
        except Exception as e:
            logger.error(f"Error fetching waitlist: {str(e)}")
            return []
    
    def notify_next_in_waitlist(self, facility_type, requested_date, requested_time):
        """
        Mark next customer in waitlist as notified
        
        Returns:
            dict: Notified customer details or None
        """
        if not self.db:
            return None
        
        try:
            # Get next in line
            query = """
            SELECT id, customer_phone, customer_email, customer_name, duration_hours
            FROM waitlist
            WHERE facility_type = %s 
            AND requested_date = %s 
            AND requested_time = %s
            AND status = 'waiting'
            ORDER BY priority ASC
            LIMIT 1
            """
            
            result = self.db.execute(query, (facility_type, requested_date, requested_time))
            row = result.fetchone()
            
            if not row:
                return None
            
            waitlist_id, phone, email, name, duration = row
            
            # Mark as notified
            expires_at = datetime.now() + timedelta(hours=self.notification_window_hours)
            
            update_query = """
            UPDATE waitlist 
            SET status = 'notified',
                notified_at = NOW(),
                expires_at = %s,
                notification_sent = true
            WHERE id = %s
            """
            
            self.db.execute(update_query, (expires_at, waitlist_id))
            
            logger.info(f"Notified waitlist customer {phone} for {facility_type} on {requested_date} at {requested_time}")
            
            return {
                'id': waitlist_id,
                'customer_phone': phone,
                'customer_email': email,
                'customer_name': name,
                'facility_type': facility_type,
                'requested_date': requested_date,
                'requested_time': requested_time,
                'duration_hours': duration,
                'expires_at': expires_at
            }
            
        except Exception as e:
            logger.error(f"Error notifying waitlist customer: {str(e)}")
            return None
    
    def mark_as_booked(self, waitlist_id):
        """Mark waitlist entry as successfully booked"""
        if not self.db:
            return False
        
        try:
            query = "UPDATE waitlist SET status = 'booked' WHERE id = %s"
            self.db.execute(query, (waitlist_id,))
            logger.info(f"Marked waitlist entry {waitlist_id} as booked")
            return True
        except Exception as e:
            logger.error(f"Error marking waitlist as booked: {str(e)}")
            return False
    
    def remove_from_waitlist(self, waitlist_id):
        """Remove customer from waitlist (cancelled request)"""
        if not self.db:
            return False
        
        try:
            query = "DELETE FROM waitlist WHERE id = %s"
            self.db.execute(query, (waitlist_id,))
            logger.info(f"Removed waitlist entry {waitlist_id}")
            return True
        except Exception as e:
            logger.error(f"Error removing from waitlist: {str(e)}")
            return False


# Global instance
waitlist_manager = WaitlistManager()
