
"""
Subscription Manager for Phase 8
Handles recurring billing and subscriptions
"""

import uuid
import stripe
from datetime import datetime, timedelta
from typing import Dict, Optional

class SubscriptionManager:
    """Manage customer subscriptions."""
    
    def __init__(self, database, stripe_enabled: bool = False):
        """Initialize subscription manager."""
        self.db = database
        self.enabled = stripe_enabled
    
    def create_subscription(
        self,
        customer_phone: str,
        plan_name: str,
        amount: float,
        interval: str = 'monthly'
    ) -> Dict:
        """
        Create a new subscription.
        
        Args:
            customer_phone: Customer phone number
            plan_name: Plan name (e.g., 'VIP Unlimited')
            amount: Monthly/yearly amount
            interval: 'monthly' or 'yearly'
            
        Returns:
            Subscription details
        """
        subscription_id = str(uuid.uuid4())
        
        if not self.enabled:
            # Test mode
            current_period_start = datetime.now().date()
            current_period_end = (current_period_start + timedelta(days=30 if interval == 'monthly' else 365))
            
            self.db.execute("""
                INSERT INTO subscriptions (
                    id, customer_phone, plan_name, status, amount,
                    interval, current_period_start, current_period_end, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                subscription_id,
                customer_phone,
                plan_name,
                'active',
                amount,
                interval,
                current_period_start.isoformat(),
                current_period_end.isoformat(),
                datetime.now().isoformat()
            ])
            
            return {
                'subscription_id': subscription_id,
                'status': 'active',
                'plan_name': plan_name,
                'amount': amount,
                'interval': interval,
                'test_mode': True
            }
        
        try:
            # Create with Stripe
            subscription = stripe.Subscription.create(
                customer=customer_phone,  # Should be Stripe customer ID
                items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': plan_name,
                        },
                        'unit_amount': int(amount * 100),
                        'recurring': {
                            'interval': 'month' if interval == 'monthly' else 'year',
                        },
                    },
                }],
            )
            
            self.db.execute("""
                INSERT INTO subscriptions (
                    id, customer_phone, plan_name, stripe_subscription_id,
                    status, amount, interval, current_period_start,
                    current_period_end, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                subscription_id,
                customer_phone,
                plan_name,
                subscription.id,
                subscription.status,
                amount,
                interval,
                datetime.fromtimestamp(subscription.current_period_start).date().isoformat(),
                datetime.fromtimestamp(subscription.current_period_end).date().isoformat(),
                datetime.now().isoformat()
            ])
            
            return {
                'subscription_id': subscription_id,
                'status': subscription.status,
                'plan_name': plan_name,
                'amount': amount,
                'interval': interval,
                'stripe_subscription_id': subscription.id,
                'test_mode': False
            }
            
        except Exception as e:
            print(f"❌ Subscription creation failed: {e}")
            raise
    
    def cancel_subscription(
        self,
        subscription_id: str,
        cancel_immediately: bool = False
    ) -> Dict:
        """
        Cancel a subscription.
        
        Args:
            subscription_id: Subscription ID
            cancel_immediately: Cancel now or at period end
            
        Returns:
            Cancellation details
        """
        subscription = self.db.query(
            "SELECT * FROM subscriptions WHERE id = ?",
            [subscription_id]
        )
        
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")
        
        subscription = subscription[0]
        
        if not self.enabled:
            # Test mode
            self.db.execute("""
                UPDATE subscriptions
                SET status = ?, cancel_at_period_end = ?, updated_at = ?
                WHERE id = ?
            """, [
                'cancelled' if cancel_immediately else 'active',
                not cancel_immediately,
                datetime.now().isoformat(),
                subscription_id
            ])
            
            return {
                'subscription_id': subscription_id,
                'status': 'cancelled' if cancel_immediately else 'active',
                'cancel_at_period_end': not cancel_immediately,
                'test_mode': True
            }
        
        try:
            if cancel_immediately:
                cancelled = stripe.Subscription.delete(subscription['stripe_subscription_id'])
            else:
                cancelled = stripe.Subscription.modify(
                    subscription['stripe_subscription_id'],
                    cancel_at_period_end=True
                )
            
            self.db.execute("""
                UPDATE subscriptions
                SET status = ?, cancel_at_period_end = ?, updated_at = ?
                WHERE id = ?
            """, [
                cancelled.status,
                cancelled.cancel_at_period_end,
                datetime.now().isoformat(),
                subscription_id
            ])
            
            return {
                'subscription_id': subscription_id,
                'status': cancelled.status,
                'cancel_at_period_end': cancelled.cancel_at_period_end,
                'test_mode': False
            }
            
        except Exception as e:
            print(f"❌ Subscription cancellation failed: {e}")
            raise
    
    def list_subscriptions(
        self,
        customer_phone: Optional[str] = None,
        status: Optional[str] = None
    ) -> list:
        """
        List subscriptions.
        
        Args:
            customer_phone: Filter by customer
            status: Filter by status
            
        Returns:
            List of subscriptions
        """
        if customer_phone and status:
            return self.db.query("""
                SELECT * FROM subscriptions
                WHERE customer_phone = ? AND status = ?
                ORDER BY created_at DESC
            """, [customer_phone, status])
        elif customer_phone:
            return self.db.query("""
                SELECT * FROM subscriptions
                WHERE customer_phone = ?
                ORDER BY created_at DESC
            """, [customer_phone])
        elif status:
            return self.db.query("""
                SELECT * FROM subscriptions
                WHERE status = ?
                ORDER BY created_at DESC
            """, [status])
        else:
            return self.db.query("""
                SELECT * FROM subscriptions
                ORDER BY created_at DESC
                LIMIT 100
            """)
