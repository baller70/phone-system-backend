"""
Vonage Smart Router
Routes incoming calls to either Thoughtly or Azure based on usage
"""

import logging
from typing import Dict, Optional
from thoughtly_usage_tracker import ThoughtlyUsageTracker

logger = logging.getLogger(__name__)

class VonageRouter:
    """Smart router that decides whether to use Thoughtly or Azure for calls"""
    
    def __init__(self, usage_tracker: Optional[ThoughtlyUsageTracker] = None):
        """
        Initialize router
        
        Args:
            usage_tracker: Optional usage tracker instance
        """
        self.usage_tracker = usage_tracker or ThoughtlyUsageTracker()
    
    def route_call(self, call_uuid: str, from_number: str, estimated_duration: int = 5) -> Dict:
        """
        Determine routing for an incoming call
        
        Args:
            call_uuid: Vonage call UUID
            from_number: Caller's phone number
            estimated_duration: Estimated call duration in minutes
            
        Returns:
            Dict with routing decision
        """
        try:
            # Check if we should use Thoughtly
            should_use_thoughtly = self.usage_tracker.should_use_thoughtly(estimated_duration)
            
            if should_use_thoughtly:
                provider = "thoughtly"
                logger.info(f"Call {call_uuid} routed to Thoughtly")
            else:
                provider = "azure"
                logger.info(f"Call {call_uuid} routed to Azure (Thoughtly limit reached)")
            
            # Get current usage stats
            usage = self.usage_tracker.get_current_usage()
            
            return {
                "call_uuid": call_uuid,
                "from_number": from_number,
                "provider": provider,
                "usage": usage,
                "timestamp": usage.get("month")
            }
            
        except Exception as e:
            logger.error(f"Error routing call: {str(e)}, defaulting to Azure")
            return {
                "call_uuid": call_uuid,
                "from_number": from_number,
                "provider": "azure",
                "error": str(e)
            }
    
    def get_routing_stats(self) -> Dict:
        """
        Get statistics about call routing
        
        Returns:
            Dict with routing statistics
        """
        try:
            usage = self.usage_tracker.get_current_usage()
            savings = self.usage_tracker.get_cost_savings()
            
            return {
                "thoughtly_usage": {
                    "total_calls": usage.get("total_calls", 0),
                    "total_minutes": usage.get("total_minutes", 0),
                    "remaining_minutes": usage.get("remaining_minutes", 0),
                    "usage_percentage": usage.get("usage_percentage", 0)
                },
                "cost_savings": savings,
                "current_provider": "thoughtly" if usage.get("has_capacity") else "azure"
            }
            
        except Exception as e:
            logger.error(f"Error getting routing stats: {str(e)}")
            return {"error": str(e)}
