
"""
Database helper for logging calls to the dashboard via API.
Instead of direct database connection, we call the dashboard API endpoints.
"""

import os
import requests
from datetime import datetime

# Dashboard API base URL
DASHBOARD_API_URL = os.getenv('DASHBOARD_API_URL', 'https://phone-system-dashboa-8em0c9.abacusai.app')
DASHBOARD_API_KEY = os.getenv('DASHBOARD_API_KEY', 'internal_api_key_12345')

def log_call_to_dashboard(
    caller_id: str,
    caller_name: str = None,
    duration: int = 0,
    intent: str = "unknown",
    outcome: str = "completed",
    recording_url: str = None,
    transcription: str = None,
    notes: str = None,
    cost: float = 0.0
):
    """
    Log a call to the dashboard via API.
    
    Args:
        caller_id: Phone number of the caller
        caller_name: Name of the caller (optional)
        duration: Call duration in seconds
        intent: The intent/purpose of the call (booking, pricing, info, etc.)
        outcome: Call outcome (completed, failed, transferred, etc.)
        recording_url: URL to the call recording (optional)
        transcription: Full call transcription (optional)
        notes: Additional notes about the call (optional)
        cost: Estimated call cost in dollars
    
    Returns:
        The ID of the created call log entry, or None if failed
    """
    try:
        url = f"{DASHBOARD_API_URL}/api/call-logs"
        payload = {
            "callerId": caller_id,
            "callerName": caller_name or "Unknown",
            "duration": duration,
            "intent": intent,
            "outcome": outcome,
            "recordingUrl": recording_url,
            "transcription": transcription,
            "notes": notes,
            "cost": cost
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": DASHBOARD_API_KEY
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code in [200, 201]:
            result = response.json()
            print(f"✓ Call logged to dashboard: {caller_id} - {intent} - {outcome}")
            return result.get('id')
        else:
            print(f"Failed to log call: HTTP {response.status_code} - {response.text}")
            return None
                
    except Exception as e:
        print(f"Failed to log call to dashboard: {e}")
        return None

def get_recent_calls(limit: int = 10):
    """Fetch recent calls from the dashboard via API."""
    try:
        url = f"{DASHBOARD_API_URL}/api/call-logs?limit={limit}"
        headers = {"X-API-Key": DASHBOARD_API_KEY}
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('calls', [])
        else:
            print(f"Failed to fetch calls: HTTP {response.status_code}")
            return []
    except Exception as e:
        print(f"Failed to fetch recent calls: {e}")
        return []

def test_dashboard_connection():
    """Test the dashboard API connection."""
    try:
        print(f"Testing dashboard API connection...")
        print(f"Dashboard URL: {DASHBOARD_API_URL}")
        
        url = f"{DASHBOARD_API_URL}/api/call-logs?limit=1"
        headers = {"X-API-Key": DASHBOARD_API_KEY}
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            call_count = len(data.get('calls', []))
            print(f"✓ Dashboard API connection successful! Can access call logs.")
            return True
        elif response.status_code == 401:
            print(f"✗ Dashboard API connection failed: Unauthorized (check API key)")
            return False
        else:
            print(f"✗ Dashboard API connection failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Dashboard API connection failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False
