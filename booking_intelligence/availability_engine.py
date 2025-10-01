"""
Availability Engine - Phase 6
Smart availability suggestions with alternative time slots
"""

from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class AvailabilityEngine:
    """Smart availability suggestions for bookings"""
    
    def __init__(self, calcom_helper):
        self.calcom = calcom_helper
    
    def suggest_alternatives(self, facility_type, requested_date, requested_time, 
                           duration_hours, num_suggestions=3):
        """
        Suggest alternative time slots when requested slot is unavailable
        
        Args:
            facility_type: Type of facility
            requested_date: Requested date (YYYY-MM-DD)
            requested_time: Requested time (HH:MM)
            duration_hours: Duration in hours
            num_suggestions: Number of alternatives to suggest
        
        Returns:
            list: Alternative time slots with availability status
        """
        alternatives = []
        
        try:
            requested_dt = datetime.strptime(f"{requested_date} {requested_time}", "%Y-%m-%d %H:%M")
            
            # Strategy 1: Same day, different times (±2 hours)
            for hour_offset in [-2, -1, 1, 2]:
                alt_time = requested_dt + timedelta(hours=hour_offset)
                if alt_time.date() == requested_dt.date():
                    alternatives.append({
                        'date': alt_time.strftime('%Y-%m-%d'),
                        'time': alt_time.strftime('%H:%M'),
                        'reason': 'same_day',
                        'label': f"Same day at {alt_time.strftime('%I:%M %p')}"
                    })
            
            # Strategy 2: Next day, same time
            next_day = requested_dt + timedelta(days=1)
            alternatives.append({
                'date': next_day.strftime('%Y-%m-%d'),
                'time': requested_time,
                'reason': 'next_day',
                'label': f"Tomorrow at {requested_time}"
            })
            
            # Strategy 3: Same weekday next week
            next_week = requested_dt + timedelta(days=7)
            alternatives.append({
                'date': next_week.strftime('%Y-%m-%d'),
                'time': requested_time,
                'reason': 'next_week',
                'label': f"Next week at {requested_time}"
            })
            
            # Strategy 4: Weekend (if requested was weekday)
            if requested_dt.weekday() < 5:  # Monday-Friday
                days_until_saturday = (5 - requested_dt.weekday()) % 7
                if days_until_saturday == 0:
                    days_until_saturday = 7
                weekend = requested_dt + timedelta(days=days_until_saturday)
                alternatives.append({
                    'date': weekend.strftime('%Y-%m-%d'),
                    'time': requested_time,
                    'reason': 'weekend',
                    'label': f"This weekend at {requested_time}"
                })
            
            # Check availability for all alternatives
            available_alternatives = []
            for alt in alternatives[:num_suggestions + 5]:  # Check more than needed
                is_available = self.calcom.check_availability(
                    facility_type, alt['date'], alt['time'], duration_hours
                )
                
                alt['available'] = is_available
                if is_available:
                    available_alternatives.append(alt)
                
                if len(available_alternatives) >= num_suggestions:
                    break
            
            # If we don't have enough available alternatives, add unavailable ones
            if len(available_alternatives) < num_suggestions:
                for alt in alternatives:
                    if alt not in available_alternatives:
                        available_alternatives.append(alt)
                    if len(available_alternatives) >= num_suggestions:
                        break
            
            return available_alternatives[:num_suggestions]
            
        except Exception as e:
            logger.error(f"Error suggesting alternatives: {str(e)}")
            return []
    
    def get_popular_times(self, facility_type, date):
        """
        Get popular booking times for a facility on a given date
        (Based on historical data if available, otherwise general patterns)
        
        Returns:
            list: Popular time slots
        """
        # General popular times (can be enhanced with analytics data)
        weekday = datetime.strptime(date, '%Y-%m-%d').weekday()
        
        if weekday < 5:  # Weekday
            popular_times = [
                {'time': '18:00', 'label': '6:00 PM - Evening prime time'},
                {'time': '19:00', 'label': '7:00 PM - Most popular'},
                {'time': '17:00', 'label': '5:00 PM - After work'},
            ]
        else:  # Weekend
            popular_times = [
                {'time': '10:00', 'label': '10:00 AM - Morning rush'},
                {'time': '14:00', 'label': '2:00 PM - Afternoon favorite'},
                {'time': '16:00', 'label': '4:00 PM - Prime time'},
            ]
        
        return popular_times
    
    def suggest_off_peak_times(self, facility_type, date, discount_percent=15):
        """
        Suggest off-peak times with discount
        
        Returns:
            list: Off-peak time slots with discount info
        """
        weekday = datetime.strptime(date, '%Y-%m-%d').weekday()
        
        if weekday < 5:  # Weekday
            off_peak_times = [
                {'time': '09:00', 'label': '9:00 AM - Morning off-peak', 'discount': discount_percent},
                {'time': '14:00', 'label': '2:00 PM - Afternoon off-peak', 'discount': discount_percent},
                {'time': '21:00', 'label': '9:00 PM - Late evening', 'discount': discount_percent},
            ]
        else:  # Weekend
            off_peak_times = [
                {'time': '08:00', 'label': '8:00 AM - Early bird', 'discount': discount_percent},
                {'time': '20:00', 'label': '8:00 PM - Evening', 'discount': discount_percent},
            ]
        
        return off_peak_times
    
    def find_next_available_slot(self, facility_type, start_date, start_time, 
                                duration_hours, search_days=7):
        """
        Find the next available slot starting from a given date/time
        
        Args:
            facility_type: Type of facility
            start_date: Start search date (YYYY-MM-DD)
            start_time: Start search time (HH:MM)
            duration_hours: Duration in hours
            search_days: How many days ahead to search
        
        Returns:
            dict: Next available slot or None
        """
        try:
            start_dt = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M")
            
            # Search every hour for the next N days
            for day_offset in range(search_days):
                for hour_offset in range(24):
                    check_dt = start_dt + timedelta(days=day_offset, hours=hour_offset)
                    check_date = check_dt.strftime('%Y-%m-%d')
                    check_time = check_dt.strftime('%H:%M')
                    
                    # Skip past times
                    if check_dt < datetime.now():
                        continue
                    
                    # Skip late night hours (before 6 AM, after 10 PM)
                    if check_dt.hour < 6 or check_dt.hour >= 22:
                        continue
                    
                    is_available = self.calcom.check_availability(
                        facility_type, check_date, check_time, duration_hours
                    )
                    
                    if is_available:
                        return {
                            'date': check_date,
                            'time': check_time,
                            'datetime': check_dt.strftime('%Y-%m-%d %I:%M %p'),
                            'found': True
                        }
            
            return {'found': False, 'message': f'No availability in next {search_days} days'}
            
        except Exception as e:
            logger.error(f"Error finding next available slot: {str(e)}")
            return {'found': False, 'error': str(e)}


# Global factory function
def create_availability_engine(calcom_helper):
    """Factory function to create AvailabilityEngine with CalCom helper"""
    return AvailabilityEngine(calcom_helper)
