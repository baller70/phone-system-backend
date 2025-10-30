"""
Thoughtly Usage Tracker
Tracks Thoughtly usage to ensure we stay within the 300 free minutes per month
"""

import json
import logging
from datetime import datetime
from typing import Dict, Optional
import os

logger = logging.getLogger(__name__)

class ThoughtlyUsageTracker:
    """Tracks Thoughtly usage to manage the 300 minute monthly limit"""
    
    def __init__(self, usage_file: str = "/tmp/thoughtly_usage.json"):
        """
        Initialize usage tracker
        
        Args:
            usage_file: Path to usage tracking file
        """
        self.usage_file = usage_file
        self.monthly_limit_minutes = 300  # 3000 credits = 300 minutes
        self.monthly_limit_credits = 3000
        
    def _load_usage_data(self) -> Dict:
        """Load usage data from file"""
        try:
            if os.path.exists(self.usage_file):
                with open(self.usage_file, 'r') as f:
                    return json.load(f)
            return self._create_new_month_data()
        except Exception as e:
            logger.error(f"Error loading usage data: {str(e)}")
            return self._create_new_month_data()
    
    def _save_usage_data(self, data: Dict):
        """Save usage data to file"""
        try:
            with open(self.usage_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving usage data: {str(e)}")
    
    def _create_new_month_data(self) -> Dict:
        """Create new month usage data"""
        now = datetime.now()
        return {
            "month": now.strftime("%Y-%m"),
            "total_minutes": 0,
            "total_credits": 0,
            "total_calls": 0,
            "calls": [],
            "last_reset": now.isoformat()
        }
    
    def _check_month_rollover(self, data: Dict) -> Dict:
        """Check if we need to roll over to a new month"""
        current_month = datetime.now().strftime("%Y-%m")
        if data.get("month") != current_month:
            logger.info(f"Rolling over usage from {data.get('month')} to {current_month}")
            return self._create_new_month_data()
        return data
    
    def record_call(self, call_id: str, duration_seconds: int, credits_used: int = None) -> Dict:
        """
        Record a call's usage
        
        Args:
            call_id: Thoughtly call ID
            duration_seconds: Call duration in seconds
            credits_used: Credits consumed (if known)
            
        Returns:
            Dict with updated usage stats
        """
        try:
            data = self._load_usage_data()
            data = self._check_month_rollover(data)
            
            minutes = duration_seconds / 60
            # If credits not provided, estimate: 10 credits per minute
            if credits_used is None:
                credits_used = int(minutes * 10)
            
            call_record = {
                "call_id": call_id,
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": duration_seconds,
                "duration_minutes": round(minutes, 2),
                "credits_used": credits_used
            }
            
            data["calls"].append(call_record)
            data["total_minutes"] += minutes
            data["total_credits"] += credits_used
            data["total_calls"] += 1
            
            self._save_usage_data(data)
            
            logger.info(f"Recorded Thoughtly call: {call_id}, {round(minutes, 2)} min, {credits_used} credits")
            logger.info(f"Monthly usage: {round(data['total_minutes'], 2)}/{self.monthly_limit_minutes} minutes")
            
            return {
                "success": True,
                "usage": data
            }
            
        except Exception as e:
            logger.error(f"Error recording call usage: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_current_usage(self) -> Dict:
        """
        Get current month usage statistics
        
        Returns:
            Dict with usage stats
        """
        try:
            data = self._load_usage_data()
            data = self._check_month_rollover(data)
            
            remaining_minutes = self.monthly_limit_minutes - data["total_minutes"]
            remaining_credits = self.monthly_limit_credits - data["total_credits"]
            usage_percentage = (data["total_minutes"] / self.monthly_limit_minutes) * 100
            
            return {
                "month": data["month"],
                "total_minutes": round(data["total_minutes"], 2),
                "total_credits": data["total_credits"],
                "total_calls": data["total_calls"],
                "limit_minutes": self.monthly_limit_minutes,
                "limit_credits": self.monthly_limit_credits,
                "remaining_minutes": round(remaining_minutes, 2),
                "remaining_credits": remaining_credits,
                "usage_percentage": round(usage_percentage, 2),
                "has_capacity": remaining_minutes > 0
            }
            
        except Exception as e:
            logger.error(f"Error getting usage: {str(e)}")
            return {"error": str(e)}
    
    def should_use_thoughtly(self, estimated_duration_minutes: int = 5) -> bool:
        """
        Determine if we should use Thoughtly for the next call
        
        Args:
            estimated_duration_minutes: Estimated call duration
            
        Returns:
            bool: True if we should use Thoughtly, False if we should fall back to Azure
        """
        try:
            usage = self.get_current_usage()
            
            if "error" in usage:
                logger.warning("Error checking usage, defaulting to Azure")
                return False
            
            remaining = usage.get("remaining_minutes", 0)
            
            # Add 10% buffer - don't use if we're within 10% of limit
            buffer = self.monthly_limit_minutes * 0.1
            effective_remaining = remaining - buffer
            
            should_use = effective_remaining >= estimated_duration_minutes
            
            if not should_use:
                logger.info(f"Thoughtly limit reached (remaining: {remaining:.2f} min), routing to Azure")
            else:
                logger.info(f"Using Thoughtly (remaining: {remaining:.2f} min)")
            
            return should_use
            
        except Exception as e:
            logger.error(f"Error checking if should use Thoughtly: {str(e)}")
            return False
    
    def get_cost_savings(self) -> Dict:
        """
        Calculate cost savings from using Thoughtly
        
        Returns:
            Dict with savings calculation
        """
        try:
            usage = self.get_current_usage()
            
            # Cost per minute: Vonage + Azure ~$0.025/min
            cost_per_minute_azure = 0.025
            
            minutes_used = usage.get("total_minutes", 0)
            savings = minutes_used * cost_per_minute_azure
            
            return {
                "minutes_saved": round(minutes_used, 2),
                "money_saved": round(savings, 2),
                "month": usage.get("month")
            }
            
        except Exception as e:
            logger.error(f"Error calculating savings: {str(e)}")
            return {"error": str(e)}
