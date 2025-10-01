"""
Loyalty System - Phase 6
Manages loyalty points earning and redemption
"""

import logging
import os

logger = logging.getLogger(__name__)


class LoyaltySystem:
    """Manages loyalty points for customers"""
    
    POINTS_PER_DOLLAR = float(os.getenv('LOYALTY_POINTS_PER_DOLLAR', '1'))
    POINTS_REDEMPTION_RATE = float(os.getenv('POINTS_REDEMPTION_RATE', '0.10'))  # 100 points = $10
    
    def __init__(self, db_connection=None):
        self.db = db_connection
        self.enabled = os.getenv('ENABLE_LOYALTY_PROGRAM', 'true').lower() == 'true'
    
    def earn_points(self, customer_phone, amount_spent, booking_id=None):
        """
        Award loyalty points for a booking
        
        Args:
            customer_phone: Customer phone number
            amount_spent: Amount spent in dollars
            booking_id: Optional booking reference
        
        Returns:
            dict: Points earned and new balance
        """
        if not self.enabled or not self.db:
            return {'success': False, 'message': 'Loyalty program not available'}
        
        try:
            points_earned = int(amount_spent * self.POINTS_PER_DOLLAR)
            
            # Get or create customer
            self._ensure_customer_exists(customer_phone)
            
            # Update customer points
            update_query = """
            UPDATE customers 
            SET loyalty_points = loyalty_points + %s
            WHERE phone = %s
            RETURNING loyalty_points
            """
            
            result = self.db.execute(update_query, (points_earned, customer_phone))
            new_balance = result.fetchone()[0]
            
            # Log transaction
            self._log_transaction(customer_phone, 'earned', points_earned, 
                                f"Earned from booking (${amount_spent})", 
                                booking_id, new_balance)
            
            logger.info(f"Customer {customer_phone} earned {points_earned} points")
            
            return {
                'success': True,
                'points_earned': points_earned,
                'new_balance': new_balance,
                'message': f"You earned {points_earned} loyalty points!"
            }
            
        except Exception as e:
            logger.error(f"Error earning points: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def redeem_points(self, customer_phone, points_to_redeem, booking_id=None):
        """
        Redeem loyalty points for discount
        
        Args:
            customer_phone: Customer phone number
            points_to_redeem: Points to redeem
            booking_id: Optional booking reference
        
        Returns:
            dict: Discount amount and new balance
        """
        if not self.enabled or not self.db:
            return {'success': False, 'message': 'Loyalty program not available'}
        
        try:
            # Get current balance
            balance_query = "SELECT loyalty_points FROM customers WHERE phone = %s"
            result = self.db.execute(balance_query, (customer_phone,))
            row = result.fetchone()
            
            if not row:
                return {'success': False, 'message': 'Customer not found'}
            
            current_balance = row[0]
            
            if points_to_redeem > current_balance:
                return {
                    'success': False,
                    'message': f'Insufficient points. You have {current_balance} points.',
                    'current_balance': current_balance
                }
            
            # Calculate discount
            discount_amount = points_to_redeem * self.POINTS_REDEMPTION_RATE
            
            # Update customer points
            update_query = """
            UPDATE customers 
            SET loyalty_points = loyalty_points - %s
            WHERE phone = %s
            RETURNING loyalty_points
            """
            
            result = self.db.execute(update_query, (points_to_redeem, customer_phone))
            new_balance = result.fetchone()[0]
            
            # Log transaction
            self._log_transaction(customer_phone, 'redeemed', -points_to_redeem,
                                f"Redeemed for ${discount_amount} discount",
                                booking_id, new_balance)
            
            logger.info(f"Customer {customer_phone} redeemed {points_to_redeem} points for ${discount_amount}")
            
            return {
                'success': True,
                'points_redeemed': points_to_redeem,
                'discount_amount': round(discount_amount, 2),
                'new_balance': new_balance,
                'message': f"Applied ${discount_amount} discount using {points_to_redeem} points"
            }
            
        except Exception as e:
            logger.error(f"Error redeeming points: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_points_balance(self, customer_phone):
        """Get customer's current points balance"""
        if not self.db:
            return 0
        
        try:
            query = "SELECT loyalty_points FROM customers WHERE phone = %s"
            result = self.db.execute(query, (customer_phone,))
            row = result.fetchone()
            return row[0] if row else 0
        except Exception as e:
            logger.error(f"Error getting points balance: {str(e)}")
            return 0
    
    def _ensure_customer_exists(self, customer_phone):
        """Ensure customer record exists"""
        try:
            check_query = "SELECT id FROM customers WHERE phone = %s"
            result = self.db.execute(check_query, (customer_phone,))
            
            if not result.fetchone():
                insert_query = """
                INSERT INTO customers (phone, tier, loyalty_points)
                VALUES (%s, 'standard', 0)
                ON CONFLICT (phone) DO NOTHING
                """
                self.db.execute(insert_query, (customer_phone,))
        except Exception as e:
            logger.error(f"Error ensuring customer exists: {str(e)}")
    
    def _log_transaction(self, customer_phone, transaction_type, points, 
                        description, booking_id, balance_after):
        """Log loyalty transaction"""
        try:
            # Get customer_id
            id_query = "SELECT id FROM customers WHERE phone = %s"
            result = self.db.execute(id_query, (customer_phone,))
            row = result.fetchone()
            customer_id = row[0] if row else None
            
            query = """
            INSERT INTO loyalty_transactions
            (customer_id, customer_phone, transaction_type, points, description, 
             booking_id, balance_after)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            self.db.execute(query, (customer_id, customer_phone, transaction_type,
                                   points, description, booking_id, balance_after))
        except Exception as e:
            logger.error(f"Error logging loyalty transaction: {str(e)}")


# Global instance
loyalty_system = LoyaltySystem()
