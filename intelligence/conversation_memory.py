
"""
Conversation Memory Service
Remembers context across multiple calls from the same customer
Uses Redis for fast in-memory storage
"""
import os
import logging
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available - conversation memory will use in-memory fallback")

class ConversationMemory:
    def __init__(self):
        self.redis_available = REDIS_AVAILABLE and os.getenv('REDIS_URL')
        
        if self.redis_available:
            try:
                redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_client.ping()
                logger.info("Conversation Memory initialized with Redis")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self.redis_available = False
        
        # Fallback to in-memory storage
        if not self.redis_available:
            self.memory_store = {}
            logger.info("Conversation Memory initialized with in-memory storage")
    
    def save_conversation_context(self, phone_number, context_data, ttl_hours=720):
        """
        Save conversation context for a customer
        
        Args:
            phone_number: Customer's phone number (identifier)
            context_data: Dict with conversation data
            ttl_hours: Time-to-live in hours (default: 30 days)
        """
        key = f"conversation:{phone_number}"
        
        # Add timestamp
        context_data['last_updated'] = datetime.now().isoformat()
        
        if self.redis_available:
            try:
                self.redis_client.setex(
                    key,
                    timedelta(hours=ttl_hours),
                    json.dumps(context_data)
                )
                logger.info(f"Saved conversation context for {phone_number}")
            except Exception as e:
                logger.error(f"Failed to save to Redis: {e}")
        else:
            self.memory_store[key] = {
                'data': context_data,
                'expires': datetime.now() + timedelta(hours=ttl_hours)
            }
    
    def get_conversation_context(self, phone_number):
        """
        Retrieve conversation context for a customer
        
        Args:
            phone_number: Customer's phone number
            
        Returns:
            Dict with conversation context or None
        """
        key = f"conversation:{phone_number}"
        
        if self.redis_available:
            try:
                data = self.redis_client.get(key)
                if data:
                    return json.loads(data)
            except Exception as e:
                logger.error(f"Failed to retrieve from Redis: {e}")
        else:
            if key in self.memory_store:
                stored = self.memory_store[key]
                # Check if expired
                if datetime.now() < stored['expires']:
                    return stored['data']
                else:
                    del self.memory_store[key]
        
        return None
    
    def update_booking_history(self, phone_number, booking_info):
        """
        Add booking to customer's history
        
        Args:
            phone_number: Customer's phone number
            booking_info: Dict with booking details
        """
        context = self.get_conversation_context(phone_number) or {}
        
        if 'booking_history' not in context:
            context['booking_history'] = []
        
        booking_info['timestamp'] = datetime.now().isoformat()
        context['booking_history'].append(booking_info)
        
        # Keep only last 10 bookings
        context['booking_history'] = context['booking_history'][-10:]
        
        self.save_conversation_context(phone_number, context)
        logger.info(f"Updated booking history for {phone_number}")
    
    def get_customer_preferences(self, phone_number):
        """
        Get customer's preferences based on history
        
        Args:
            phone_number: Customer's phone number
            
        Returns:
            Dict with preferences
        """
        context = self.get_conversation_context(phone_number)
        
        if not context or 'booking_history' not in context:
            return None
        
        history = context['booking_history']
        
        # Analyze preferences
        facilities = [b.get('facility') for b in history if b.get('facility')]
        times = [b.get('time') for b in history if b.get('time')]
        
        preferences = {
            'favorite_facility': max(set(facilities), key=facilities.count) if facilities else None,
            'preferred_time': max(set(times), key=times.count) if times else None,
            'total_bookings': len(history),
            'last_booking': history[-1] if history else None
        }
        
        return preferences
    
    def is_returning_customer(self, phone_number):
        """
        Check if customer has called before
        
        Args:
            phone_number: Customer's phone number
            
        Returns:
            Boolean
        """
        context = self.get_conversation_context(phone_number)
        return context is not None

# Global conversation memory instance
conversation_memory = ConversationMemory()
