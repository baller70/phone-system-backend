
"""
Phase 7: Dynamic Pricing Engine
AI-powered pricing optimization based on demand, time, and customer behavior
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from decimal import Decimal

logger = logging.getLogger(__name__)

class DynamicPricingEngine:
    """
    Intelligent pricing engine that adjusts prices based on:
    - Demand forecasts
    - Current availability
    - Time of day/week
    - Customer tier (VIP, Standard)
    - Historical booking patterns
    """
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.enabled = os.getenv('DYNAMIC_PRICING_ENABLED', 'true').lower() == 'true'
        
        # Pricing rules from environment
        self.surge_threshold = float(os.getenv('SURGE_PRICING_THRESHOLD', '0.8'))  # 80% capacity
        self.surge_multiplier = float(os.getenv('SURGE_PRICING_MULTIPLIER', '1.2'))  # +20%
        self.off_peak_discount = float(os.getenv('OFF_PEAK_DISCOUNT', '0.15'))  # -15%
        
        # Time-based pricing rules
        self.peak_hours = [17, 18, 19, 20]  # 5 PM - 9 PM
        self.weekend_multiplier = 1.1  # +10% on weekends
    
    def calculate_dynamic_price(
        self, 
        facility_id: int, 
        base_price: float, 
        date: str, 
        hour: int,
        customer_phone: Optional[str] = None
    ) -> Dict:
        """
        Calculate dynamic price for a booking
        
        Args:
            facility_id: Facility ID
            base_price: Base price from pricing data
            date: Booking date (YYYY-MM-DD)
            hour: Booking hour (0-23)
            customer_phone: Optional customer phone for VIP pricing
            
        Returns:
            Dictionary with final price and breakdown
        """
        if not self.enabled:
            return {
                'final_price': base_price,
                'base_price': base_price,
                'adjustments': [],
                'discount_percent': 0,
                'surge_applied': False
            }
        
        try:
            final_price = base_price
            adjustments = []
            
            # 1. Check current availability (capacity-based pricing)
            availability_factor = self._get_availability_factor(facility_id, date, hour)
            
            if availability_factor >= self.surge_threshold:
                # High demand - apply surge pricing
                surge_amount = base_price * (self.surge_multiplier - 1)
                final_price += surge_amount
                adjustments.append({
                    'type': 'surge',
                    'reason': f'High demand ({int(availability_factor * 100)}% booked)',
                    'amount': surge_amount,
                    'percentage': (self.surge_multiplier - 1) * 100
                })
            elif availability_factor < 0.3:
                # Low demand - apply discount
                discount_amount = base_price * self.off_peak_discount
                final_price -= discount_amount
                adjustments.append({
                    'type': 'discount',
                    'reason': f'Low demand ({int(availability_factor * 100)}% booked)',
                    'amount': -discount_amount,
                    'percentage': -self.off_peak_discount * 100
                })
            
            # 2. Time-based pricing (peak hours)
            if hour in self.peak_hours:
                peak_amount = base_price * 0.1  # +10% for peak hours
                final_price += peak_amount
                adjustments.append({
                    'type': 'peak_hour',
                    'reason': f'Peak hour pricing ({hour}:00)',
                    'amount': peak_amount,
                    'percentage': 10
                })
            
            # 3. Weekend pricing
            booking_date = datetime.strptime(date, '%Y-%m-%d')
            if booking_date.weekday() >= 5:  # Saturday or Sunday
                weekend_amount = base_price * (self.weekend_multiplier - 1)
                final_price += weekend_amount
                adjustments.append({
                    'type': 'weekend',
                    'reason': 'Weekend premium',
                    'amount': weekend_amount,
                    'percentage': (self.weekend_multiplier - 1) * 100
                })
            
            # 4. Customer tier discount (VIP)
            if customer_phone:
                vip_discount = self._get_vip_discount(customer_phone)
                if vip_discount > 0:
                    discount_amount = base_price * vip_discount
                    final_price -= discount_amount
                    adjustments.append({
                        'type': 'vip_discount',
                        'reason': 'VIP customer discount',
                        'amount': -discount_amount,
                        'percentage': -vip_discount * 100
                    })
            
            # 5. Last-minute booking premium (<4 hours)
            hours_until_booking = self._get_hours_until_booking(date, hour)
            if hours_until_booking < 4:
                last_minute_amount = base_price * 0.15  # +15% for last-minute
                final_price += last_minute_amount
                adjustments.append({
                    'type': 'last_minute',
                    'reason': 'Last-minute booking premium',
                    'amount': last_minute_amount,
                    'percentage': 15
                })
            
            # 6. Early bird discount (>7 days in advance)
            elif hours_until_booking > 168:  # 7 days
                early_bird_amount = base_price * 0.1  # -10% for early booking
                final_price -= early_bird_amount
                adjustments.append({
                    'type': 'early_bird',
                    'reason': 'Early bird discount (7+ days advance)',
                    'amount': -early_bird_amount,
                    'percentage': -10
                })
            
            # Ensure price doesn't go below a minimum
            min_price = base_price * 0.5  # Never less than 50% of base
            final_price = max(min_price, final_price)
            
            # Round to 2 decimal places
            final_price = round(final_price, 2)
            
            # Calculate total discount/surge percentage
            total_adjustment = ((final_price - base_price) / base_price) * 100
            
            # Store pricing record
            self._store_pricing_record(facility_id, date, hour, base_price, final_price, adjustments)
            
            return {
                'final_price': final_price,
                'base_price': base_price,
                'adjustments': adjustments,
                'total_adjustment_percent': round(total_adjustment, 2),
                'surge_applied': any(a['type'] == 'surge' for a in adjustments),
                'demand_level': self._classify_demand(availability_factor)
            }
            
        except Exception as e:
            logger.error(f"Error calculating dynamic price: {e}")
            return {
                'final_price': base_price,
                'base_price': base_price,
                'adjustments': [],
                'error': str(e)
            }
    
    def _get_availability_factor(self, facility_id: int, date: str, hour: int) -> float:
        """
        Calculate availability factor (0 = empty, 1 = full)
        
        Args:
            facility_id: Facility ID
            date: Date string
            hour: Hour of day
            
        Returns:
            Availability factor (0.0 to 1.0)
        """
        try:
            # Count bookings for the same time slot
            cursor = self.db.cursor()
            query = """
                SELECT COUNT(*) as booked_slots
                FROM bookings
                WHERE facility_id = %s 
                AND DATE(start_time) = %s
                AND EXTRACT(HOUR FROM start_time) = %s
                AND status IN ('confirmed', 'pending')
            """
            cursor.execute(query, (facility_id, date, hour))
            result = cursor.fetchone()
            cursor.close()
            
            booked_slots = result[0] if result else 0
            
            # Assume max capacity of 10 bookings per hour slot
            max_capacity = 10
            
            return min(booked_slots / max_capacity, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating availability factor: {e}")
            return 0.5  # Default to medium
    
    def _get_vip_discount(self, customer_phone: str) -> float:
        """
        Get VIP discount percentage for customer
        
        Args:
            customer_phone: Customer phone number
            
        Returns:
            Discount percentage (0.0 to 1.0)
        """
        try:
            cursor = self.db.cursor(dictionary=True)
            query = """
                SELECT tier, vip_discount_percent
                FROM customers
                WHERE phone = %s
            """
            cursor.execute(query, (customer_phone,))
            customer = cursor.fetchone()
            cursor.close()
            
            if customer and customer['tier'] in ['VIP', 'Platinum']:
                return customer['vip_discount_percent'] / 100.0
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error getting VIP discount: {e}")
            return 0.0
    
    def _get_hours_until_booking(self, date: str, hour: int) -> int:
        """
        Calculate hours until the booking time
        
        Args:
            date: Booking date
            hour: Booking hour
            
        Returns:
            Hours until booking
        """
        try:
            booking_datetime = datetime.strptime(f"{date} {hour:02d}:00:00", "%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            delta = booking_datetime - now
            return int(delta.total_seconds() / 3600)
        except Exception as e:
            logger.error(f"Error calculating hours until booking: {e}")
            return 24  # Default to 1 day
    
    def _classify_demand(self, availability_factor: float) -> str:
        """
        Classify demand level based on availability
        
        Args:
            availability_factor: Availability factor (0-1)
            
        Returns:
            Demand level string
        """
        if availability_factor >= 0.8:
            return 'surge'
        elif availability_factor >= 0.6:
            return 'high'
        elif availability_factor >= 0.3:
            return 'medium'
        else:
            return 'low'
    
    def _store_pricing_record(self, facility_id: int, date: str, hour: int, 
                              base_price: float, dynamic_price: float, adjustments: list):
        """
        Store pricing record in database for analytics
        
        Args:
            facility_id: Facility ID
            date: Date
            hour: Hour
            base_price: Base price
            dynamic_price: Final dynamic price
            adjustments: List of adjustments applied
        """
        try:
            cursor = self.db.cursor()
            query = """
                INSERT INTO dynamic_prices 
                (id, facility_id, date, hour, base_price, dynamic_price, demand_level, discount_percent, created_at)
                VALUES (UUID(), %s, %s, %s, %s, %s, %s, %s, NOW())
            """
            
            discount_percent = ((dynamic_price - base_price) / base_price) * 100
            demand_level = self._classify_demand(self._get_availability_factor(facility_id, date, hour))
            
            cursor.execute(query, (
                facility_id,
                date,
                hour,
                base_price,
                dynamic_price,
                demand_level,
                round(discount_percent, 2)
            ))
            
            self.db.commit()
            cursor.close()
            
        except Exception as e:
            logger.error(f"Error storing pricing record: {e}")
            self.db.rollback()
    
    def get_pricing_analytics(self, days: int = 30) -> Dict:
        """
        Get pricing analytics for the last N days
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with pricing analytics
        """
        try:
            cursor = self.db.cursor(dictionary=True)
            query = """
                SELECT 
                    AVG(dynamic_price) as avg_price,
                    AVG(base_price) as avg_base_price,
                    AVG(discount_percent) as avg_discount,
                    COUNT(*) as total_bookings,
                    SUM(CASE WHEN demand_level = 'surge' THEN 1 ELSE 0 END) as surge_bookings,
                    SUM(CASE WHEN demand_level = 'low' THEN 1 ELSE 0 END) as low_demand_bookings
                FROM dynamic_prices
                WHERE created_at >= NOW() - INTERVAL %s DAY
            """
            cursor.execute(query, (days,))
            analytics = cursor.fetchone()
            cursor.close()
            
            return analytics or {}
            
        except Exception as e:
            logger.error(f"Error getting pricing analytics: {e}")
            return {}


def get_dynamic_pricing_engine(db_connection):
    """Get DynamicPricingEngine instance"""
    return DynamicPricingEngine(db_connection)
