"""
Thoughtly Webhook Handler
Processes webhook events from Thoughtly
"""

import logging
from typing import Dict, Any
from datetime import datetime
from thoughtly_usage_tracker import ThoughtlyUsageTracker
import json

logger = logging.getLogger(__name__)

class ThoughtlyWebhookHandler:
    """Handles webhooks from Thoughtly"""
    
    def __init__(self, usage_tracker: ThoughtlyUsageTracker):
        """
        Initialize webhook handler
        
        Args:
            usage_tracker: Usage tracker instance
        """
        self.usage_tracker = usage_tracker
    
    def process_webhook(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a webhook event from Thoughtly
        
        Args:
            event_data: Webhook payload from Thoughtly
            
        Returns:
            Dict with processing result
        """
        try:
            event_type = event_data.get("event")
            
            if not event_type:
                return {"error": "No event type specified"}
            
            logger.info(f"Processing Thoughtly webhook: {event_type}")
            
            # Route to specific handler
            if event_type == "call.started":
                return self._handle_call_started(event_data)
            elif event_type == "call.completed":
                return self._handle_call_completed(event_data)
            elif event_type == "call.failed":
                return self._handle_call_failed(event_data)
            elif event_type == "booking.created":
                return self._handle_booking_created(event_data)
            elif event_type == "transcript.ready":
                return self._handle_transcript_ready(event_data)
            else:
                logger.warning(f"Unknown event type: {event_type}")
                return {"success": True, "message": f"Event {event_type} received but not handled"}
                
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            return {"error": str(e)}
    
    def _handle_call_started(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle call started event"""
        try:
            call_id = data.get("call_id")
            from_number = data.get("from")
            timestamp = data.get("timestamp", datetime.now().isoformat())
            
            logger.info(f"Thoughtly call started: {call_id} from {from_number}")
            
            # You can log this to database here
            # For now, just return success
            
            return {
                "success": True,
                "event": "call.started",
                "call_id": call_id,
                "processed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error handling call started: {str(e)}")
            return {"error": str(e)}
    
    def _handle_call_completed(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle call completed event"""
        try:
            call_id = data.get("call_id")
            duration = data.get("duration_seconds", 0)
            credits_used = data.get("credits_used")
            
            logger.info(f"Thoughtly call completed: {call_id}, duration: {duration}s")
            
            # Record usage
            result = self.usage_tracker.record_call(call_id, duration, credits_used)
            
            # Get updated usage
            usage = self.usage_tracker.get_current_usage()
            
            return {
                "success": True,
                "event": "call.completed",
                "call_id": call_id,
                "duration_seconds": duration,
                "credits_used": credits_used,
                "current_usage": usage,
                "processed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error handling call completed: {str(e)}")
            return {"error": str(e)}
    
    def _handle_call_failed(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle call failed event"""
        try:
            call_id = data.get("call_id")
            error = data.get("error")
            
            logger.error(f"Thoughtly call failed: {call_id}, error: {error}")
            
            # You can log this to database here
            
            return {
                "success": True,
                "event": "call.failed",
                "call_id": call_id,
                "error": error,
                "processed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error handling call failed: {str(e)}")
            return {"error": str(e)}
    
    def _handle_booking_created(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle booking created event"""
        try:
            call_id = data.get("call_id")
            booking_data = data.get("booking", {})
            
            customer_name = booking_data.get("name")
            customer_phone = booking_data.get("phone")
            facility = booking_data.get("facility")
            booking_datetime = booking_data.get("datetime")
            
            logger.info(f"Booking created via Thoughtly: {facility} for {customer_name} at {booking_datetime}")
            
            # Here you would:
            # 1. Create Cal.com booking if not already done
            # 2. Send SMS confirmation
            # 3. Log to database
            
            return {
                "success": True,
                "event": "booking.created",
                "call_id": call_id,
                "booking": booking_data,
                "processed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error handling booking created: {str(e)}")
            return {"error": str(e)}
    
    def _handle_transcript_ready(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle transcript ready event"""
        try:
            call_id = data.get("call_id")
            transcript = data.get("transcript")
            
            logger.info(f"Transcript ready for call: {call_id}")
            
            # You can save transcript to database here
            
            return {
                "success": True,
                "event": "transcript.ready",
                "call_id": call_id,
                "transcript_length": len(transcript) if transcript else 0,
                "processed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error handling transcript ready: {str(e)}")
            return {"error": str(e)}
    
    def validate_webhook_signature(self, payload: str, signature: str, secret: str) -> bool:
        """
        Validate webhook signature (if Thoughtly provides signatures)
        
        Args:
            payload: Raw webhook payload
            signature: Signature from Thoughtly
            secret: Webhook secret
            
        Returns:
            bool: True if signature is valid
        """
        # This would be implemented if Thoughtly provides webhook signatures
        # For now, just return True
        return True
