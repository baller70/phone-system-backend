"""
Rebooking Service - Phase 6
Handles proactive rebooking campaigns and outbound calls
"""

import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RebookingService:
    """Manages rebooking campaigns and outbound calls"""
    
    def __init__(self, db_connection=None):
        self.db = db_connection
        self.enabled = os.getenv('ENABLE_REBOOKING_CALLS', 'true').lower() == 'true'
        self.delay_days = int(os.getenv('REBOOKING_CALL_DELAY_DAYS', '7'))
    
    def create_rebooking_campaign(self, booking_data):
        """
        Create a rebooking campaign after a booking is completed
        
        Args:
            booking_data: dict with keys:
                - customer_phone
                - customer_email
                - customer_name
                - booking_id
                - booking_date
                - facility_type
        
        Returns:
            dict: Campaign details
        """
        if not self.enabled or not self.db:
            return None
        
        try:
            # Schedule outbound call N days after booking
            booking_date = datetime.strptime(booking_data['booking_date'], '%Y-%m-%d').date()
            call_date = booking_date + timedelta(days=self.delay_days)
            
            query = """
            INSERT INTO rebooking_campaigns
            (customer_phone, customer_email, customer_name, last_booking_id,
             last_booking_date, last_facility_type, outbound_call_scheduled_at, call_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending')
            RETURNING id
            """
            
            scheduled_time = datetime.combine(call_date, datetime.min.time().replace(hour=10))
            
            result = self.db.execute(query, (
                booking_data['customer_phone'],
                booking_data.get('customer_email'),
                booking_data.get('customer_name'),
                booking_data['booking_id'],
                booking_data['booking_date'],
                booking_data['facility_type'],
                scheduled_time
            ))
            
            campaign_id = result.fetchone()[0]
            
            logger.info(f"Rebooking campaign {campaign_id} created for {booking_data['customer_phone']}")
            
            return {
                'id': campaign_id,
                'scheduled_for': str(scheduled_time),
                'status': 'pending'
            }
            
        except Exception as e:
            logger.error(f"Error creating rebooking campaign: {str(e)}")
            return None
    
    def get_due_campaigns(self):
        """Get campaigns that are due for outbound calls"""
        if not self.db:
            return []
        
        try:
            query = """
            SELECT id, customer_phone, customer_name, last_facility_type,
                   last_booking_date, outbound_call_scheduled_at
            FROM rebooking_campaigns
            WHERE call_status = 'pending'
            AND outbound_call_scheduled_at <= NOW()
            ORDER BY outbound_call_scheduled_at
            LIMIT 50
            """
            
            result = self.db.execute(query)
            rows = result.fetchall()
            
            campaigns = []
            for row in rows:
                campaigns.append({
                    'id': row[0],
                    'customer_phone': row[1],
                    'customer_name': row[2],
                    'last_facility_type': row[3],
                    'last_booking_date': str(row[4]),
                    'scheduled_at': str(row[5])
                })
            
            return campaigns
            
        except Exception as e:
            logger.error(f"Error fetching due campaigns: {str(e)}")
            return []
    
    def mark_campaign_called(self, campaign_id, success=False, rebooked=False, new_booking_id=None):
        """Mark campaign as called"""
        if not self.db:
            return False
        
        try:
            status = 'completed' if success else 'failed'
            if rebooked:
                status = 'booked'
            
            query = """
            UPDATE rebooking_campaigns
            SET call_status = %s,
                outbound_call_made_at = NOW(),
                rebooked = %s,
                new_booking_id = %s
            WHERE id = %s
            """
            
            self.db.execute(query, (status, rebooked, new_booking_id, campaign_id))
            logger.info(f"Rebooking campaign {campaign_id} marked as {status}")
            return True
            
        except Exception as e:
            logger.error(f"Error marking campaign as called: {str(e)}")
            return False


# Global instance
rebooking_service = RebookingService()
