"""
Peak Time Analyzer - Phase 6
Analyzes booking patterns and identifies peak/off-peak times
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class PeakTimeAnalyzer:
    """Analyzes and tracks peak booking times"""
    
    def __init__(self, db_connection=None):
        self.db = db_connection
    
    def record_booking(self, facility_type, booking_date, booking_time, 
                      duration_hours, revenue_dollars):
        """Record a booking for analytics"""
        if not self.db:
            return False
        
        try:
            dt = datetime.strptime(f"{booking_date} {booking_time}", "%Y-%m-%d %H:%M")
            day_of_week = dt.weekday()
            hour = dt.hour
            
            query = """
            INSERT INTO booking_analytics 
            (facility_type, day_of_week, hour, booking_count, revenue_dollars, average_duration_hours)
            VALUES (%s, %s, %s, 1, %s, %s)
            ON CONFLICT (facility_type, day_of_week, hour)
            DO UPDATE SET
                booking_count = booking_analytics.booking_count + 1,
                revenue_dollars = booking_analytics.revenue_dollars + EXCLUDED.revenue_dollars,
                average_duration_hours = (booking_analytics.average_duration_hours * booking_analytics.booking_count + EXCLUDED.average_duration_hours) / (booking_analytics.booking_count + 1),
                last_updated = NOW()
            """
            
            self.db.execute(query, (facility_type, day_of_week, hour, revenue_dollars, duration_hours))
            return True
        except Exception as e:
            logger.error(f"Error recording booking analytics: {str(e)}")
            return False
    
    def get_peak_times(self, facility_type, day_of_week=None):
        """Get peak times for a facility (most bookings)"""
        if not self.db:
            return []
        
        try:
            if day_of_week is not None:
                query = """
                SELECT hour, booking_count, revenue_dollars
                FROM booking_analytics
                WHERE facility_type = %s AND day_of_week = %s
                AND booking_count > 5
                ORDER BY booking_count DESC
                LIMIT 5
                """
                result = self.db.execute(query, (facility_type, day_of_week))
            else:
                query = """
                SELECT hour, SUM(booking_count) as total_bookings, SUM(revenue_dollars) as total_revenue
                FROM booking_analytics
                WHERE facility_type = %s
                GROUP BY hour
                HAVING SUM(booking_count) > 10
                ORDER BY total_bookings DESC
                LIMIT 5
                """
                result = self.db.execute(query, (facility_type,))
            
            rows = result.fetchall()
            peak_times = []
            
            for row in rows:
                hour = row[0]
                bookings = row[1]
                revenue = float(row[2]) if row[2] else 0
                
                peak_times.append({
                    'hour': hour,
                    'time': f"{hour:02d}:00",
                    'label': f"{hour}:00 - {(hour+1) % 24}:00",
                    'booking_count': bookings,
                    'revenue': round(revenue, 2),
                    'is_peak': True
                })
            
            return peak_times
        except Exception as e:
            logger.error(f"Error getting peak times: {str(e)}")
            return []
    
    def get_off_peak_times(self, facility_type, day_of_week=None):
        """Get off-peak times (lowest bookings)"""
        if not self.db:
            return []
        
        try:
            if day_of_week is not None:
                query = """
                SELECT hour, booking_count
                FROM booking_analytics
                WHERE facility_type = %s AND day_of_week = %s
                ORDER BY booking_count ASC
                LIMIT 5
                """
                result = self.db.execute(query, (facility_type, day_of_week))
            else:
                query = """
                SELECT hour, SUM(booking_count) as total_bookings
                FROM booking_analytics
                WHERE facility_type = %s
                GROUP BY hour
                ORDER BY total_bookings ASC
                LIMIT 5
                """
                result = self.db.execute(query, (facility_type,))
            
            rows = result.fetchall()
            off_peak_times = []
            
            for row in rows:
                hour = row[0]
                bookings = row[1]
                
                # Only include reasonable hours (6 AM - 10 PM)
                if 6 <= hour < 22:
                    off_peak_times.append({
                        'hour': hour,
                        'time': f"{hour:02d}:00",
                        'label': f"{hour}:00 - {(hour+1) % 24}:00",
                        'booking_count': bookings,
                        'is_peak': False,
                        'discount_eligible': True
                    })
            
            return off_peak_times
        except Exception as e:
            logger.error(f"Error getting off-peak times: {str(e)}")
            return []


# Global instance
peak_time_analyzer = PeakTimeAnalyzer()
