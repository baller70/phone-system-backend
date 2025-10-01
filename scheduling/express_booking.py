"""
Express Booking - Phase 6
Fast booking flow for returning customers
"""

import logging

logger = logging.getLogger(__name__)


class ExpressBooking:
    """Handles express booking for VIP/returning customers"""
    
    def __init__(self, conversation_memory=None):
        self.conversation_memory = conversation_memory
    
    def get_usual_booking(self, customer_phone):
        """
        Get customer's "usual" booking based on history
        
        Returns:
            dict: Suggested booking or None
        """
        if not self.conversation_memory:
            return None
        
        try:
            # Get booking history
            history = self.conversation_memory.get_booking_history(customer_phone)
            
            if not history or len(history) < 2:
                return None
            
            # Analyze last 3 bookings for patterns
            recent = history[:3]
            
            # Check if there's a consistent pattern
            facilities = [b.get('facility_type') for b in recent]
            durations = [b.get('duration_hours') for b in recent]
            
            # Find most common facility
            facility_counts = {}
            for f in facilities:
                facility_counts[f] = facility_counts.get(f, 0) + 1
            
            most_common_facility = max(facility_counts, key=facility_counts.get)
            
            # Average duration
            avg_duration = sum(d for d in durations if d) / len(durations) if durations else 2
            
            return {
                'facility_type': most_common_facility,
                'duration_hours': round(avg_duration, 1),
                'confidence': 'high' if len(recent) >= 3 else 'medium',
                'last_booking_date': recent[0].get('date')
            }
            
        except Exception as e:
            logger.error(f"Error getting usual booking: {str(e)}")
            return None
    
    def suggest_express_booking(self, customer_phone, preferences=None):
        """Generate express booking suggestion"""
        usual = self.get_usual_booking(customer_phone)
        
        if not usual:
            return None
        
        # Apply preferences if available
        if preferences:
            preferred_time = preferences.get('preferred_time_slot', 'evening')
            
            # Map time slot to hour
            time_map = {
                'morning': '09:00',
                'afternoon': '14:00',
                'evening': '18:00'
            }
            suggested_time = time_map.get(preferred_time, '18:00')
        else:
            suggested_time = '18:00'  # Default to evening
        
        return {
            'facility_type': usual['facility_type'],
            'duration_hours': usual['duration_hours'],
            'suggested_time': suggested_time,
            'message': f"Would you like to book your usual - {usual['facility_type']} for {usual['duration_hours']} hours?"
        }


# Global factory
def create_express_booking(conversation_memory):
    return ExpressBooking(conversation_memory)
