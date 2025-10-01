
"""
Group Booking Manager - Phase 6
Handles group bookings with dynamic pricing and capacity validation
"""

import logging
import os

logger = logging.getLogger(__name__)


class GroupBookingManager:
    """Manages group bookings with dynamic pricing"""
    
    # Facility capacities (max group size)
    FACILITY_CAPACITIES = {
        'basketball': 30,
        'volleyball': 30,
        'soccer': 50,
        'tennis': 8,
        'badminton': 8,
        'swimming': 40,
        'gym': 50
    }
    
    # Group pricing multipliers
    # Base price × multiplier based on group size
    GROUP_MULTIPLIERS = {
        (1, 1): 1.0,      # Individual (no change)
        (2, 5): 1.8,      # Small group (2-5 people): 1.8x base
        (6, 10): 2.5,     # Medium group (6-10): 2.5x base
        (11, 20): 3.5,    # Large group (11-20): 3.5x base
        (21, 50): 5.0,    # Very large group (21-50): 5x base
    }
    
    def __init__(self, db_connection=None):
        self.db = db_connection
        self.enabled = os.getenv('ENABLE_GROUP_BOOKINGS', 'true').lower() == 'true'
    
    def validate_group_size(self, facility_type, group_size):
        """
        Validate if group size is acceptable for the facility
        
        Returns:
            tuple: (is_valid: bool, max_capacity: int, message: str)
        """
        if not self.enabled:
            return (False, 0, "Group bookings are currently disabled")
        
        # Normalize facility type
        facility_key = facility_type.lower().replace(' ', '_')
        
        max_capacity = self.FACILITY_CAPACITIES.get(facility_key, 20)
        
        if group_size < 1:
            return (False, max_capacity, "Group size must be at least 1 person")
        
        if group_size > max_capacity:
            return (False, max_capacity, 
                   f"Group size exceeds maximum capacity of {max_capacity} people for {facility_type}")
        
        return (True, max_capacity, "Group size is valid")
    
    def calculate_group_price(self, base_price, group_size):
        """
        Calculate total price for group booking
        
        Args:
            base_price: Base price for the facility
            group_size: Number of people
        
        Returns:
            tuple: (total_price: float, multiplier: float, per_person_price: float)
        """
        # Find applicable multiplier
        multiplier = 1.0
        for (min_size, max_size), mult in self.GROUP_MULTIPLIERS.items():
            if min_size <= group_size <= max_size:
                multiplier = mult
                break
        
        # If group size exceeds all ranges, use highest multiplier
        if group_size > 50:
            multiplier = 5.0
        
        total_price = base_price * multiplier
        per_person_price = total_price / group_size
        
        return (round(total_price, 2), multiplier, round(per_person_price, 2))
    
    def save_group_booking_details(self, booking_data):
        """
        Save group booking details to database
        
        Args:
            booking_data: dict with keys:
                - calcom_booking_id
                - conversation_uuid
                - customer_phone
                - coordinator_name
                - coordinator_email
                - facility_type
                - booking_date
                - booking_time
                - group_size
                - base_price
                - group_multiplier
                - total_price
                - special_requirements (optional)
        
        Returns:
            bool: Success status
        """
        if not self.db:
            logger.warning("No database connection, group booking details not saved")
            return False
        
        try:
            query = """
            INSERT INTO group_bookings 
            (calcom_booking_id, conversation_uuid, customer_phone, coordinator_name, 
             coordinator_email, facility_type, booking_date, booking_time, group_size,
             base_price, group_multiplier, total_price, special_requirements)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            self.db.execute(query, (
                booking_data['calcom_booking_id'],
                booking_data.get('conversation_uuid'),
                booking_data['customer_phone'],
                booking_data.get('coordinator_name'),
                booking_data.get('coordinator_email'),
                booking_data['facility_type'],
                booking_data['booking_date'],
                booking_data['booking_time'],
                booking_data['group_size'],
                booking_data['base_price'],
                booking_data['group_multiplier'],
                booking_data['total_price'],
                booking_data.get('special_requirements')
            ))
            
            logger.info(f"Saved group booking details for {booking_data['calcom_booking_id']}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving group booking: {str(e)}")
            return False
    
    def get_group_booking(self, calcom_booking_id):
        """Get group booking details by Cal.com booking ID"""
        if not self.db:
            return None
        
        try:
            query = """
            SELECT id, customer_phone, coordinator_name, coordinator_email, facility_type,
                   booking_date, booking_time, group_size, base_price, group_multiplier,
                   total_price, special_requirements, created_at
            FROM group_bookings
            WHERE calcom_booking_id = %s
            """
            
            result = self.db.execute(query, (calcom_booking_id,))
            row = result.fetchone()
            
            if not row:
                return None
            
            return {
                'id': row[0],
                'customer_phone': row[1],
                'coordinator_name': row[2],
                'coordinator_email': row[3],
                'facility_type': row[4],
                'booking_date': str(row[5]),
                'booking_time': str(row[6]),
                'group_size': row[7],
                'base_price': float(row[8]),
                'group_multiplier': float(row[9]),
                'total_price': float(row[10]),
                'special_requirements': row[11],
                'created_at': str(row[12])
            }
            
        except Exception as e:
            logger.error(f"Error fetching group booking: {str(e)}")
            return None
    
    def get_recent_group_bookings(self, limit=20):
        """Get recent group bookings"""
        if not self.db:
            return []
        
        try:
            query = """
            SELECT calcom_booking_id, customer_phone, coordinator_name, facility_type,
                   booking_date, booking_time, group_size, total_price, created_at
            FROM group_bookings
            ORDER BY created_at DESC
            LIMIT %s
            """
            
            result = self.db.execute(query, (limit,))
            rows = result.fetchall()
            
            bookings = []
            for row in rows:
                bookings.append({
                    'calcom_booking_id': row[0],
                    'customer_phone': row[1],
                    'coordinator_name': row[2],
                    'facility_type': row[3],
                    'booking_date': str(row[4]),
                    'booking_time': str(row[5]),
                    'group_size': row[6],
                    'total_price': float(row[7]),
                    'created_at': str(row[8])
                })
            
            return bookings
            
        except Exception as e:
            logger.error(f"Error fetching recent group bookings: {str(e)}")
            return []


# Global instance
group_booking_manager = GroupBookingManager()
