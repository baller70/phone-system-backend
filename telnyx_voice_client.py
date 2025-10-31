"""
Telnyx Voice API Client
Handles all Telnyx Call Control API interactions
"""

import os
import json
import base64
import requests
from typing import Dict, Any, Optional, List


class TelnyxVoiceClient:
    """Client for Telnyx Voice API (Call Control)"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Telnyx client with API key"""
        self.api_key = api_key or os.getenv('TELNYX_API_KEY')
        self.base_url = 'https://api.telnyx.com/v2/calls'
        
        if not self.api_key:
            raise ValueError("TELNYX_API_KEY is required")
        
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def _make_request(self, call_control_id: str, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make a request to Telnyx Call Control API"""
        url = f"{self.base_url}/{call_control_id}/actions/{action}"
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Telnyx API Error ({action}): {e}")
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}")
            raise
    
    def encode_client_state(self, state_data: Dict[str, Any]) -> str:
        """Encode state data to base64 for client_state parameter"""
        json_str = json.dumps(state_data)
        return base64.b64encode(json_str.encode()).decode()
    
    def decode_client_state(self, client_state: str) -> Dict[str, Any]:
        """Decode base64 client_state to dictionary"""
        try:
            json_str = base64.b64decode(client_state.encode()).decode()
            return json.loads(json_str)
        except Exception as e:
            print(f"⚠️ Failed to decode client_state: {e}")
            return {}
    
    def answer_call(self, call_control_id: str, client_state: Optional[Dict] = None, command_id: Optional[str] = None):
        """Answer an incoming call"""
        payload = {}
        
        if client_state:
            payload['client_state'] = self.encode_client_state(client_state)
        if command_id:
            payload['command_id'] = command_id
        
        return self._make_request(call_control_id, 'answer', payload)
    
    def speak(self, call_control_id: str, text: str, voice: str = 'female', 
              language: str = 'en-US', client_state: Optional[Dict] = None, command_id: Optional[str] = None):
        """Speak text on the call using TTS"""
        payload = {
            'payload': text,
            'payload_type': 'text',
            'voice': voice,
            'language': language
        }
        
        if client_state:
            payload['client_state'] = self.encode_client_state(client_state)
        if command_id:
            payload['command_id'] = command_id
        
        return self._make_request(call_control_id, 'speak', payload)
    
    def gather_using_speak(self, call_control_id: str, text: str, valid_digits: str = '0123456789*#',
                          max_digits: int = 1, timeout_ms: int = 5000, 
                          voice: str = 'female', language: str = 'en-US',
                          client_state: Optional[Dict] = None, command_id: Optional[str] = None):
        """Speak text and gather DTMF input"""
        payload = {
            'payload': text,
            'payload_type': 'text',
            'voice': voice,
            'language': language,
            'valid_digits': valid_digits,
            'max': max_digits,
            'timeout_millis': timeout_ms,
            'terminating_digit': '#'
        }
        
        if client_state:
            payload['client_state'] = self.encode_client_state(client_state)
        if command_id:
            payload['command_id'] = command_id
        
        return self._make_request(call_control_id, 'gather_using_speak', payload)
    
    def gather_using_audio(self, call_control_id: str, audio_url: str, valid_digits: str = '0123456789*#',
                          max_digits: int = 1, timeout_ms: int = 5000,
                          client_state: Optional[Dict] = None, command_id: Optional[str] = None):
        """Play audio and gather DTMF input"""
        payload = {
            'audio_url': audio_url,
            'valid_digits': valid_digits,
            'max': max_digits,
            'timeout_millis': timeout_ms,
            'terminating_digit': '#'
        }
        
        if client_state:
            payload['client_state'] = self.encode_client_state(client_state)
        if command_id:
            payload['command_id'] = command_id
        
        return self._make_request(call_control_id, 'gather_using_audio', payload)
    
    def hangup(self, call_control_id: str, client_state: Optional[Dict] = None, command_id: Optional[str] = None):
        """Hang up the call"""
        payload = {}
        
        if client_state:
            payload['client_state'] = self.encode_client_state(client_state)
        if command_id:
            payload['command_id'] = command_id
        
        return self._make_request(call_control_id, 'hangup', payload)
    
    def transfer(self, call_control_id: str, to: str, from_number: str,
                client_state: Optional[Dict] = None, command_id: Optional[str] = None):
        """Transfer the call to another number"""
        payload = {
            'to': to,
            'from': from_number
        }
        
        if client_state:
            payload['client_state'] = self.encode_client_state(client_state)
        if command_id:
            payload['command_id'] = command_id
        
        return self._make_request(call_control_id, 'transfer', payload)
    
    def bridge(self, call_control_id: str, other_call_control_id: str,
              client_state: Optional[Dict] = None, command_id: Optional[str] = None):
        """Bridge two calls together"""
        payload = {
            'call_control_id': other_call_control_id
        }
        
        if client_state:
            payload['client_state'] = self.encode_client_state(client_state)
        if command_id:
            payload['command_id'] = command_id
        
        return self._make_request(call_control_id, 'bridge', payload)
    
    def start_recording(self, call_control_id: str, channels: str = 'single',
                       format: str = 'wav', client_state: Optional[Dict] = None, command_id: Optional[str] = None):
        """Start recording the call"""
        payload = {
            'channels': channels,
            'format': format
        }
        
        if client_state:
            payload['client_state'] = self.encode_client_state(client_state)
        if command_id:
            payload['command_id'] = command_id
        
        return self._make_request(call_control_id, 'record_start', payload)
    
    def stop_recording(self, call_control_id: str, client_state: Optional[Dict] = None, command_id: Optional[str] = None):
        """Stop recording the call"""
        payload = {}
        
        if client_state:
            payload['client_state'] = self.encode_client_state(client_state)
        if command_id:
            payload['command_id'] = command_id
        
        return self._make_request(call_control_id, 'record_stop', payload)
    
    def play_audio(self, call_control_id: str, audio_url: str,
                  client_state: Optional[Dict] = None, command_id: Optional[str] = None):
        """Play audio file on the call"""
        payload = {
            'audio_url': audio_url
        }
        
        if client_state:
            payload['client_state'] = self.encode_client_state(client_state)
        if command_id:
            payload['command_id'] = command_id
        
        return self._make_request(call_control_id, 'playback_start', payload)
    
    def stop_audio(self, call_control_id: str, client_state: Optional[Dict] = None, command_id: Optional[str] = None):
        """Stop audio playback"""
        payload = {}
        
        if client_state:
            payload['client_state'] = self.encode_client_state(client_state)
        if command_id:
            payload['command_id'] = command_id
        
        return self._make_request(call_control_id, 'playback_stop', payload)


# Helper function to extract event data from Telnyx webhooks
def extract_telnyx_event_data(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract useful data from Telnyx webhook event"""
    if 'data' not in webhook_data:
        return {}
    
    data = webhook_data['data']
    payload = data.get('payload', {})
    
    return {
        'event_type': data.get('event_type', ''),
        'call_control_id': payload.get('call_control_id', ''),
        'call_leg_id': payload.get('call_leg_id', ''),
        'call_session_id': payload.get('call_session_id', ''),
        'connection_id': payload.get('connection_id', ''),
        'from': payload.get('from', ''),
        'to': payload.get('to', ''),
        'direction': payload.get('direction', ''),
        'state': payload.get('state', ''),
        'client_state': payload.get('client_state', ''),
        'digit': payload.get('digit', ''),  # For DTMF events
        'digits': payload.get('digits', ''),  # For gather events
        'hangup_cause': payload.get('hangup_cause', ''),
        'occurred_at': data.get('occurred_at', ''),
        'raw_payload': payload
    }
