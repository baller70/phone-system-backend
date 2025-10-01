"""
VIP Manager - Phase 6
Handles VIP customer recognition and benefits
"""

import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)


class VIPManager:
    """Manages VIP customer recognition and benefits"""
    
    VIP_THRESHOLD_BOOKINGS = int(os.getenv('VIP_THRESHOLD_BOOKINGS', '5'))
    VIP_THRESHOLD_SPENT = float(os.getenv('VIP_THRESHOLD_SPENT', '500'))
    PLATINUM_THRESHOLD_BOOKINGS = int(os.getenv('PLATINUM_THRESHOLD_BOOKINGS', '15'))
    PLATINUM_THRESHOLD_SPENT = float(os.getenv('PLATINUM_THRESHOLD_SPENT', '2000'))
    VIP_DISCOUNT_PERCENT = float(os.getenv('VIP_DISCOUNT_PERCENT', '5'))
    
    def __init__(self, db_connection=None):
        self.db = db_connection
    
    def calculate_customer_tier(self, customer_phone):
        """
        Calculate customer tier based on booking history
        
        Returns:
            str: 'standard', 'vip', or 'platinum'
        """
        if not self.db:
            return 'standard'
        
        try:
            # Get customer stats
            query = """
            SELECT total_bookings, total_spent_dollars, tier
            FROM customers
            WHERE phone = %s
            """
            
            result = self.db.execute(query, (customer_phone,))
            row = result.fetchone()
            
            if not row:
                return 'standard'
            
            total_bookings, total_spent, current_tier = row
            
            # Calculate new tier
            new_tier = 'standard'
            
            if total_bookings >= self.PLATINUM_THRESHOLD_BOOKINGS or total_spent >= self.PLATINUM_THRESHOLD_SPENT:
                new_tier = 'platinum'
            elif total_bookings >= self.VIP_THRESHOLD_BOOKINGS or total_spent >= self.VIP_THRESHOLD_SPENT:
                new_tier = 'vip'
            
            # Update tier if changed
            if new_tier != current_tier:
                self._update_customer_tier(customer_phone, new_tier)
                logger.info(f"Customer {customer_phone} upgraded to {new_tier}")
            
            return new_tier
            
        except Exception as e:
            logger.error(f"Error calculating customer tier: {str(e)}")
            return 'standard'
    
    def _update_customer_tier(self, customer_phone, new_tier):
        """Update customer tier in database"""
        if not self.db:
            return False
        
        try:
            # Set vip_since date if becoming VIP for first time
            vip_since_clause = ""
            if new_tier in ['vip', 'platinum']:
                vip_since_clause = ", vip_since = COALESCE(vip_since, NOW())"
            
            query = f"""
            UPDATE customers 
            SET tier = %s{vip_since_clause}
            WHERE phone = %s
            """
            
            self.db.execute(query, (new_tier, customer_phone))
            return True
        except Exception as e:
            logger.error(f"Error updating customer tier: {str(e)}")
            return False
    
    def get_vip_greeting(self, customer_name, tier):
        """Generate personalized VIP greeting"""
        if tier == 'platinum':
            return f"Welcome back, {customer_name}! As one of our platinum members, we appreciate your continued loyalty."
        elif tier == 'vip':
            return f"Welcome back, {customer_name}! As a VIP member, we're here to provide you with priority service."
        else:
            return f"Hello {customer_name}, thank you for calling!"
    
    def apply_vip_discount(self, base_price, tier):
        """Apply VIP discount to price"""
        if tier in ['vip', 'platinum']:
            discount_amount = base_price * (self.VIP_DISCOUNT_PERCENT / 100)
            final_price = base_price - discount_amount
            return round(final_price, 2), discount_amount
        return base_price, 0
    
    def is_vip(self, customer_phone):
        """Check if customer is VIP or Platinum"""
        tier = self.calculate_customer_tier(customer_phone)
        return tier in ['vip', 'platinum']
    
    def update_customer_stats(self, customer_phone, amount_spent, email=None, name=None):
        """
        Update customer booking count and total spent
        
        Args:
            customer_phone: Customer phone number
            amount_spent: Amount spent on this booking
            email: Optional customer email
            name: Optional customer name
        """
        if not self.db:
            return False
        
        try:
            # Check if customer exists
            check_query = "SELECT id FROM customers WHERE phone = ?"
            result = self.db.fetchone(check_query, (customer_phone,))
            
            if result:
                # Update existing customer
                update_query = """
                UPDATE customers 
                SET total_bookings = total_bookings + 1,
                    total_spent_dollars = total_spent_dollars + ?,
                    last_booking_at = CURRENT_TIMESTAMP
                """
                
                params = [amount_spent]
                
                if email:
                    update_query += ", email = ?"
                    params.append(email)
                if name:
                    update_query += ", name = ?"
                    params.append(name)
                
                update_query += " WHERE phone = ?"
                params.append(customer_phone)
                
                self.db.execute(update_query, tuple(params))
            else:
                # Create new customer
                insert_data = {
                    'phone': customer_phone,
                    'email': email,
                    'name': name,
                    'tier': 'standard',
                    'total_bookings': 1,
                    'total_spent_dollars': amount_spent,
                    'loyalty_points': 0,
                    'preferences': '{}',
                    'last_booking_at': datetime.now().isoformat()
                }
                
                # Remove None values
                insert_data = {k: v for k, v in insert_data.items() if v is not None}
                
                self.db.insert('customers', insert_data)
            
            # Recalculate tier after update
            self.calculate_customer_tier(customer_phone)
            
            logger.info(f"Updated stats for customer {customer_phone}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating customer stats: {str(e)}")
            return False


# Global instance
vip_manager = VIPManager()
