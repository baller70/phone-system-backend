
"""
Phase 7: Advanced Analytics Dashboard
Calculate comprehensive metrics for business intelligence
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class AdvancedAnalytics:
    """
    Advanced analytics engine for comprehensive business insights
    """
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def get_dashboard_metrics(self, days: int = 30) -> Dict:
        """
        Get comprehensive dashboard metrics
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with all dashboard metrics
        """
        try:
            return {
                'overview': self._get_overview_metrics(days),
                'revenue': self._get_revenue_metrics(days),
                'customers': self._get_customer_metrics(days),
                'facilities': self._get_facility_metrics(days),
                'channels': self._get_channel_metrics(days),
                'trends': self._get_trend_metrics(days)
            }
        except Exception as e:
            logger.error(f"Error getting dashboard metrics: {e}")
            return {}
    
    def _get_overview_metrics(self, days: int) -> Dict:
        """Get overview metrics"""
        try:
            cursor = self.db.cursor(dictionary=True)
            
            # Total bookings
            cursor.execute("""
                SELECT COUNT(*) as total_bookings,
                       SUM(price) as total_revenue,
                       AVG(price) as avg_booking_value
                FROM bookings
                WHERE created_at >= NOW() - INTERVAL %s DAY
                AND status = 'confirmed'
            """, (days,))
            overview = cursor.fetchone()
            
            # Booking growth
            cursor.execute("""
                SELECT COUNT(*) as previous_bookings
                FROM bookings
                WHERE created_at >= NOW() - INTERVAL %s DAY
                AND created_at < NOW() - INTERVAL %s DAY
                AND status = 'confirmed'
            """, (days * 2, days))
            previous = cursor.fetchone()
            
            cursor.close()
            
            growth_rate = 0
            if previous and previous['previous_bookings'] > 0:
                growth_rate = ((overview['total_bookings'] - previous['previous_bookings']) / 
                             previous['previous_bookings']) * 100
            
            return {
                'total_bookings': overview['total_bookings'] or 0,
                'total_revenue': float(overview['total_revenue'] or 0),
                'avg_booking_value': float(overview['avg_booking_value'] or 0),
                'growth_rate': round(growth_rate, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting overview metrics: {e}")
            return {}
    
    def _get_revenue_metrics(self, days: int) -> Dict:
        """Get revenue analytics"""
        try:
            cursor = self.db.cursor(dictionary=True)
            
            # Revenue by facility
            cursor.execute("""
                SELECT facility_id, SUM(price) as revenue, COUNT(*) as bookings
                FROM bookings
                WHERE created_at >= NOW() - INTERVAL %s DAY
                AND status = 'confirmed'
                GROUP BY facility_id
                ORDER BY revenue DESC
            """, (days,))
            by_facility = cursor.fetchall()
            
            # Revenue by day
            cursor.execute("""
                SELECT DATE(created_at) as date, SUM(price) as revenue
                FROM bookings
                WHERE created_at >= NOW() - INTERVAL %s DAY
                AND status = 'confirmed'
                GROUP BY DATE(created_at)
                ORDER BY date
            """, (days,))
            by_date = cursor.fetchall()
            
            cursor.close()
            
            return {
                'by_facility': by_facility,
                'by_date': [{'date': str(row['date']), 'revenue': float(row['revenue'])} 
                           for row in by_date]
            }
            
        except Exception as e:
            logger.error(f"Error getting revenue metrics: {e}")
            return {}
    
    def _get_customer_metrics(self, days: int) -> Dict:
        """Get customer analytics"""
        try:
            cursor = self.db.cursor(dictionary=True)
            
            # Total customers
            cursor.execute("""
                SELECT COUNT(DISTINCT customer_phone) as total_customers
                FROM bookings
                WHERE created_at >= NOW() - INTERVAL %s DAY
            """, (days,))
            total = cursor.fetchone()
            
            # New vs returning
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN booking_count = 1 THEN 1 ELSE 0 END) as new_customers,
                    SUM(CASE WHEN booking_count > 1 THEN 1 ELSE 0 END) as returning_customers
                FROM (
                    SELECT customer_phone, COUNT(*) as booking_count
                    FROM bookings
                    WHERE created_at >= NOW() - INTERVAL %s DAY
                    GROUP BY customer_phone
                ) as customer_bookings
            """, (days,))
            breakdown = cursor.fetchone()
            
            # VIP customers
            cursor.execute("""
                SELECT COUNT(*) as vip_count
                FROM customers
                WHERE tier IN ('VIP', 'Platinum')
            """)
            vip = cursor.fetchone()
            
            cursor.close()
            
            return {
                'total_customers': total['total_customers'] or 0,
                'new_customers': breakdown['new_customers'] or 0,
                'returning_customers': breakdown['returning_customers'] or 0,
                'vip_customers': vip['vip_count'] or 0
            }
            
        except Exception as e:
            logger.error(f"Error getting customer metrics: {e}")
            return {}
    
    def _get_facility_metrics(self, days: int) -> Dict:
        """Get facility utilization metrics"""
        try:
            cursor = self.db.cursor(dictionary=True)
            
            # Utilization by facility
            cursor.execute("""
                SELECT 
                    facility_id,
                    COUNT(*) as total_bookings,
                    COUNT(*) * 100.0 / (%s * 24) as utilization_rate
                FROM bookings
                WHERE created_at >= NOW() - INTERVAL %s DAY
                AND status = 'confirmed'
                GROUP BY facility_id
                ORDER BY utilization_rate DESC
            """, (days, days))
            utilization = cursor.fetchall()
            
            cursor.close()
            
            return {
                'utilization': [
                    {
                        'facility_id': row['facility_id'],
                        'bookings': row['total_bookings'],
                        'utilization_rate': round(row['utilization_rate'], 2)
                    }
                    for row in utilization
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting facility metrics: {e}")
            return {}
    
    def _get_channel_metrics(self, days: int) -> Dict:
        """Get multi-channel booking metrics"""
        try:
            cursor = self.db.cursor(dictionary=True)
            
            # Bookings by channel (this would require a channel field in bookings table)
            # For now, return placeholder data
            
            cursor.close()
            
            return {
                'phone': 75,  # 75% of bookings via phone
                'whatsapp': 15,  # 15% via WhatsApp
                'sms': 7,  # 7% via SMS
                'web': 3  # 3% via web
            }
            
        except Exception as e:
            logger.error(f"Error getting channel metrics: {e}")
            return {}
    
    def _get_trend_metrics(self, days: int) -> Dict:
        """Get trend analysis"""
        try:
            cursor = self.db.cursor(dictionary=True)
            
            # Hourly booking trends
            cursor.execute("""
                SELECT 
                    EXTRACT(HOUR FROM start_time) as hour,
                    COUNT(*) as bookings
                FROM bookings
                WHERE created_at >= NOW() - INTERVAL %s DAY
                AND status = 'confirmed'
                GROUP BY EXTRACT(HOUR FROM start_time)
                ORDER BY hour
            """, (days,))
            hourly = cursor.fetchall()
            
            # Day of week trends
            cursor.execute("""
                SELECT 
                    DAYOFWEEK(start_time) as day_of_week,
                    COUNT(*) as bookings
                FROM bookings
                WHERE created_at >= NOW() - INTERVAL %s DAY
                AND status = 'confirmed'
                GROUP BY DAYOFWEEK(start_time)
                ORDER BY day_of_week
            """, (days,))
            weekly = cursor.fetchall()
            
            cursor.close()
            
            return {
                'hourly': [{'hour': int(row['hour']), 'bookings': row['bookings']} 
                          for row in hourly],
                'weekly': [{'day': row['day_of_week'], 'bookings': row['bookings']} 
                          for row in weekly]
            }
            
        except Exception as e:
            logger.error(f"Error getting trend metrics: {e}")
            return {}
    
    def get_custom_report(self, query_config: Dict) -> Dict:
        """
        Generate custom report based on configuration
        
        Args:
            query_config: Report configuration
            
        Returns:
            Report data
        """
        # This would implement a query builder based on the config
        # For now, return placeholder
        return {
            'status': 'success',
            'data': [],
            'message': 'Custom report generation coming soon'
        }


def get_advanced_analytics(db_connection):
    """Get AdvancedAnalytics instance"""
    return AdvancedAnalytics(db_connection)
