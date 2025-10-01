"""
Preference Learner - Phase 6
Learns and tracks customer preferences
"""

import logging
from collections import Counter

logger = logging.getLogger(__name__)


class PreferenceLearner:
    """Learns customer preferences from booking history"""
    
    def __init__(self, db_connection=None):
        self.db = db_connection
    
    def learn_preferences(self, customer_phone):
        """
        Analyze booking history and learn preferences
        
        Returns:
            dict: Learned preferences
        """
        if not self.db:
            return {}
        
        try:
            # Get booking history from conversation memory
            # (We'll integrate with conversation_memory module)
            query = """
            SELECT preferences
            FROM customers
            WHERE phone = %s
            """
            
            result = self.db.execute(query, (customer_phone,))
            row = result.fetchone()
            
            if row and row[0]:
                return row[0]  # JSONB field
            
            return {}
            
        except Exception as e:
            logger.error(f"Error learning preferences: {str(e)}")
            return {}
    
    def analyze_booking_patterns(self, booking_history):
        """
        Analyze patterns from booking history
        
        Args:
            booking_history: List of booking dicts
        
        Returns:
            dict: Patterns like favorite facility, preferred time, etc.
        """
        if not booking_history:
            return {}
        
        try:
            facilities = [b.get('facility_type') for b in booking_history if b.get('facility_type')]
            times = [b.get('time') for b in booking_history if b.get('time')]
            durations = [b.get('duration_hours') for b in booking_history if b.get('duration_hours')]
            
            patterns = {}
            
            # Favorite facility (most booked)
            if facilities:
                facility_counts = Counter(facilities)
                patterns['favorite_facility'] = facility_counts.most_common(1)[0][0]
            
            # Preferred time slot (morning/afternoon/evening)
            if times:
                time_periods = []
                for time_str in times:
                    try:
                        hour = int(time_str.split(':')[0])
                        if 6 <= hour < 12:
                            time_periods.append('morning')
                        elif 12 <= hour < 18:
                            time_periods.append('afternoon')
                        else:
                            time_periods.append('evening')
                    except:
                        pass
                
                if time_periods:
                    period_counts = Counter(time_periods)
                    patterns['preferred_time_slot'] = period_counts.most_common(1)[0][0]
            
            # Average duration
            if durations:
                patterns['average_duration_hours'] = round(sum(durations) / len(durations), 1)
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error analyzing booking patterns: {str(e)}")
            return {}
    
    def update_customer_preferences(self, customer_phone, preferences):
        """Update customer preferences in database"""
        if not self.db:
            return False
        
        try:
            query = """
            UPDATE customers
            SET preferences = %s::jsonb,
                favorite_facility = %s,
                preferred_time_slot = %s,
                average_duration_hours = %s
            WHERE phone = %s
            """
            
            self.db.execute(query, (
                preferences,
                preferences.get('favorite_facility'),
                preferences.get('preferred_time_slot'),
                preferences.get('average_duration_hours'),
                customer_phone
            ))
            
            logger.info(f"Updated preferences for {customer_phone}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating preferences: {str(e)}")
            return False


# Global instance
preference_learner = PreferenceLearner()
