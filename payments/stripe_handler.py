
"""
Stripe Payment Handler for Phase 8
Processes payments, deposits, and full charges
"""

import os
import uuid
import stripe
from datetime import datetime
from typing import Dict, Optional

class StripePaymentHandler:
    """Handle Stripe payment processing."""
    
    def __init__(self, database):
        """Initialize Stripe handler."""
        self.db = database
        self.enabled = os.getenv('STRIPE_ENABLED', 'false').lower() == 'true'
        
        if self.enabled:
            stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
            self.publishable_key = os.getenv('STRIPE_PUBLISHABLE_KEY')
        
        print(f"💳 Stripe Payment Handler: {'Enabled' if self.enabled else 'Disabled (Test Mode)'}")
    
    def create_payment_intent(
        self,
        amount: float,
        customer_phone: str,
        booking_id: str,
        payment_type: str = 'full',
        metadata: Dict = None
    ) -> Dict:
        """
        Create a Stripe payment intent.
        
        Args:
            amount: Amount to charge in USD
            customer_phone: Customer phone number
            booking_id: Associated booking ID
            payment_type: 'deposit', 'full', or 'balance'
            metadata: Additional metadata
            
        Returns:
            Payment intent details
        """
        payment_id = str(uuid.uuid4())
        
        if not self.enabled:
            # Test mode - simulate payment
            payment_data = {
                'payment_id': payment_id,
                'client_secret': f'test_secret_{payment_id}',
                'status': 'requires_payment_method',
                'amount': amount,
                'currency': 'usd',
                'test_mode': True
            }
            
            # Save to database
            self.db.execute("""
                INSERT INTO payments (
                    id, booking_id, customer_phone, amount, currency,
                    payment_type, status, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                payment_id,
                booking_id,
                customer_phone,
                amount,
                'USD',
                payment_type,
                'pending',
                str(metadata or {}),
                datetime.now().isoformat()
            ])
            
            return payment_data
        
        try:
            # Create Stripe payment intent
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Convert to cents
                currency='usd',
                metadata={
                    'booking_id': booking_id,
                    'customer_phone': customer_phone,
                    'payment_type': payment_type,
                    **(metadata or {})
                }
            )
            
            # Save to database
            self.db.execute("""
                INSERT INTO payments (
                    id, booking_id, customer_phone, amount, currency,
                    payment_type, stripe_payment_id, status, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                payment_id,
                booking_id,
                customer_phone,
                amount,
                'USD',
                payment_type,
                intent.id,
                intent.status,
                str(metadata or {}),
                datetime.now().isoformat()
            ])
            
            return {
                'payment_id': payment_id,
                'client_secret': intent.client_secret,
                'status': intent.status,
                'amount': amount,
                'currency': 'usd',
                'stripe_intent_id': intent.id,
                'test_mode': False
            }
            
        except Exception as e:
            print(f"❌ Stripe payment intent creation failed: {e}")
            raise
    
    def confirm_payment(
        self,
        payment_id: str,
        payment_method_id: Optional[str] = None
    ) -> Dict:
        """
        Confirm a payment intent.
        
        Args:
            payment_id: Our internal payment ID
            payment_method_id: Stripe payment method ID (optional for test mode)
            
        Returns:
            Payment confirmation details
        """
        # Get payment from database
        payment = self.db.query(
            "SELECT * FROM payments WHERE id = ?",
            [payment_id]
        )
        
        if not payment:
            raise ValueError(f"Payment {payment_id} not found")
        
        if not self.enabled:
            # Test mode - auto-confirm
            self.db.execute("""
                UPDATE payments
                SET status = 'completed', completed_at = ?
                WHERE id = ?
            """, [datetime.now().isoformat(), payment_id])
            
            return {
                'payment_id': payment_id,
                'status': 'completed',
                'test_mode': True
            }
        
        try:
            stripe_intent_id = payment[0]['stripe_payment_id']
            
            # Confirm with Stripe
            intent = stripe.PaymentIntent.confirm(
                stripe_intent_id,
                payment_method=payment_method_id
            )
            
            # Update database
            self.db.execute("""
                UPDATE payments
                SET status = ?, completed_at = ?
                WHERE id = ?
            """, [intent.status, datetime.now().isoformat(), payment_id])
            
            return {
                'payment_id': payment_id,
                'status': intent.status,
                'stripe_intent_id': intent.id,
                'test_mode': False
            }
            
        except Exception as e:
            print(f"❌ Payment confirmation failed: {e}")
            
            # Mark as failed
            self.db.execute("""
                UPDATE payments
                SET status = 'failed'
                WHERE id = ?
            """, [payment_id])
            
            raise
    
    def create_deposit_payment(
        self,
        total_amount: float,
        customer_phone: str,
        booking_id: str,
        deposit_percent: float = 30.0
    ) -> Dict:
        """
        Create a deposit payment (partial payment).
        
        Args:
            total_amount: Total booking amount
            customer_phone: Customer phone
            booking_id: Booking ID
            deposit_percent: Deposit percentage (default 30%)
            
        Returns:
            Payment intent for deposit
        """
        deposit_amount = total_amount * (deposit_percent / 100)
        
        return self.create_payment_intent(
            amount=deposit_amount,
            customer_phone=customer_phone,
            booking_id=booking_id,
            payment_type='deposit',
            metadata={
                'total_amount': total_amount,
                'deposit_percent': deposit_percent,
                'remaining_balance': total_amount - deposit_amount
            }
        )
    
    def get_payment_history(
        self,
        customer_phone: str,
        limit: int = 50
    ) -> list:
        """
        Get payment history for a customer.
        
        Args:
            customer_phone: Customer phone number
            limit: Max number of records
            
        Returns:
            List of payments
        """
        return self.db.query("""
            SELECT * FROM payments
            WHERE customer_phone = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, [customer_phone, limit])
    
    def get_payment_analytics(
        self,
        days: int = 30
    ) -> Dict:
        """
        Get payment analytics for the last N days.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Analytics data
        """
        # Total revenue
        total_revenue = self.db.query("""
            SELECT COALESCE(SUM(amount), 0) as total
            FROM payments
            WHERE status = 'completed'
            AND created_at >= datetime('now', '-{} days')
        """.format(days))
        
        # Payment success rate
        success_rate = self.db.query("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful
            FROM payments
            WHERE created_at >= datetime('now', '-{} days')
        """.format(days))
        
        # Average payment amount
        avg_payment = self.db.query("""
            SELECT AVG(amount) as avg_amount
            FROM payments
            WHERE status = 'completed'
            AND created_at >= datetime('now', '-{} days')
        """.format(days))
        
        total = success_rate[0]['total'] if success_rate else 0
        successful = success_rate[0]['successful'] if success_rate else 0
        
        return {
            'total_revenue': total_revenue[0]['total'] if total_revenue else 0,
            'total_payments': total,
            'successful_payments': successful,
            'failed_payments': total - successful,
            'success_rate': (successful / total * 100) if total > 0 else 0,
            'avg_payment_amount': avg_payment[0]['avg_amount'] if avg_payment and avg_payment[0]['avg_amount'] else 0
        }

# Singleton instance
_stripe_service = None

def get_stripe_service(database):
    """Get or create Stripe service instance."""
    global _stripe_service
    if _stripe_service is None:
        _stripe_service = StripePaymentHandler(database)
    return _stripe_service
