
"""
Refund Processor for Phase 8
Handles refund processing and tracking
"""

import uuid
import stripe
from datetime import datetime
from typing import Dict, Optional

class RefundProcessor:
    """Handle payment refunds."""
    
    def __init__(self, database, stripe_enabled: bool = False):
        """Initialize refund processor."""
        self.db = database
        self.enabled = stripe_enabled
    
    def process_refund(
        self,
        payment_id: str,
        amount: Optional[float] = None,
        reason: str = "Customer request"
    ) -> Dict:
        """
        Process a refund for a payment.
        
        Args:
            payment_id: Payment ID to refund
            amount: Amount to refund (None = full refund)
            reason: Reason for refund
            
        Returns:
            Refund details
        """
        # Get payment details
        payment = self.db.query(
            "SELECT * FROM payments WHERE id = ?",
            [payment_id]
        )
        
        if not payment:
            raise ValueError(f"Payment {payment_id} not found")
        
        payment = payment[0]
        
        if payment['status'] != 'completed':
            raise ValueError(f"Cannot refund payment with status: {payment['status']}")
        
        refund_amount = amount or payment['amount']
        refund_id = str(uuid.uuid4())
        
        if not self.enabled:
            # Test mode - auto-approve
            self.db.execute("""
                INSERT INTO refunds (
                    id, payment_id, booking_id, amount, reason, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [
                refund_id,
                payment_id,
                payment['booking_id'],
                refund_amount,
                reason,
                'completed',
                datetime.now().isoformat()
            ])
            
            # Update payment status
            self.db.execute("""
                UPDATE payments
                SET status = 'refunded'
                WHERE id = ?
            """, [payment_id])
            
            return {
                'refund_id': refund_id,
                'amount': refund_amount,
                'status': 'completed',
                'test_mode': True
            }
        
        try:
            # Process with Stripe
            refund = stripe.Refund.create(
                payment_intent=payment['stripe_payment_id'],
                amount=int(refund_amount * 100),  # Convert to cents
                reason='requested_by_customer'
            )
            
            # Save to database
            self.db.execute("""
                INSERT INTO refunds (
                    id, payment_id, booking_id, amount, reason,
                    stripe_refund_id, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                refund_id,
                payment_id,
                payment['booking_id'],
                refund_amount,
                reason,
                refund.id,
                refund.status,
                datetime.now().isoformat()
            ])
            
            # Update payment status if fully refunded
            if refund_amount >= payment['amount']:
                self.db.execute("""
                    UPDATE payments
                    SET status = 'refunded'
                    WHERE id = ?
                """, [payment_id])
            
            return {
                'refund_id': refund_id,
                'amount': refund_amount,
                'status': refund.status,
                'stripe_refund_id': refund.id,
                'test_mode': False
            }
            
        except Exception as e:
            print(f"❌ Refund processing failed: {e}")
            
            # Mark as failed
            self.db.execute("""
                INSERT INTO refunds (
                    id, payment_id, booking_id, amount, reason, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [
                refund_id,
                payment_id,
                payment['booking_id'],
                refund_amount,
                reason,
                'failed',
                datetime.now().isoformat()
            ])
            
            raise
    
    def get_refund_history(
        self,
        booking_id: Optional[str] = None,
        customer_phone: Optional[str] = None,
        limit: int = 50
    ) -> list:
        """
        Get refund history.
        
        Args:
            booking_id: Filter by booking ID
            customer_phone: Filter by customer phone
            limit: Max records
            
        Returns:
            List of refunds
        """
        if booking_id:
            return self.db.query("""
                SELECT * FROM refunds
                WHERE booking_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, [booking_id, limit])
        elif customer_phone:
            return self.db.query("""
                SELECT r.* FROM refunds r
                JOIN payments p ON r.payment_id = p.id
                WHERE p.customer_phone = ?
                ORDER BY r.created_at DESC
                LIMIT ?
            """, [customer_phone, limit])
        else:
            return self.db.query("""
                SELECT * FROM refunds
                ORDER BY created_at DESC
                LIMIT ?
            """, [limit])
