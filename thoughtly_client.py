
"""
Thoughtly API Client
Handles all interactions with Thoughtly's voice AI API
"""

import requests
import logging
from typing import Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class ThoughtlyClient:
    """Client for interacting with Thoughtly API"""
    
    def __init__(self, api_key: str):
        """
        Initialize Thoughtly client
        
        Args:
            api_key: Thoughtly API key
        """
        self.api_key = api_key
        self.base_url = "https://api.thoughtly.co/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def initiate_call(self, phone_number: str, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Initiate an outbound call through Thoughtly
        
        Args:
            phone_number: Phone number to call
            agent_id: Optional specific agent ID to use
            
        Returns:
            Dict containing call information
        """
        try:
            payload = {
                "phone_number": phone_number,
                "agent_id": agent_id
            }
            
            response = requests.post(
                f"{self.base_url}/calls",
                json=payload,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 201:
                logger.info(f"Thoughtly call initiated to {phone_number}")
                return response.json()
            else:
                logger.error(f"Failed to initiate Thoughtly call: {response.text}")
                return {"error": response.text, "status_code": response.status_code}
                
        except Exception as e:
            logger.error(f"Exception initiating Thoughtly call: {str(e)}")
            return {"error": str(e)}
    
    def get_call_status(self, call_id: str) -> Dict[str, Any]:
        """
        Get the status of a call
        
        Args:
            call_id: Thoughtly call ID
            
        Returns:
            Dict containing call status
        """
        try:
            response = requests.get(
                f"{self.base_url}/calls/{call_id}",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get call status: {response.text}")
                return {"error": response.text, "status_code": response.status_code}
                
        except Exception as e:
            logger.error(f"Exception getting call status: {str(e)}")
            return {"error": str(e)}
    
    def get_call_transcript(self, call_id: str) -> Dict[str, Any]:
        """
        Get the transcript of a completed call
        
        Args:
            call_id: Thoughtly call ID
            
        Returns:
            Dict containing transcript data
        """
        try:
            response = requests.get(
                f"{self.base_url}/calls/{call_id}/transcript",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get transcript: {response.text}")
                return {"error": response.text, "status_code": response.status_code}
                
        except Exception as e:
            logger.error(f"Exception getting transcript: {str(e)}")
            return {"error": str(e)}
    
    def create_contact(self, phone_number: str, name: Optional[str] = None, 
                      email: Optional[str] = None, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Create a contact in Thoughtly
        
        Args:
            phone_number: Contact phone number
            name: Contact name
            email: Contact email
            metadata: Additional metadata
            
        Returns:
            Dict containing contact information
        """
        try:
            payload = {
                "phone_number": phone_number
            }
            
            if name:
                payload["name"] = name
            if email:
                payload["email"] = email
            if metadata:
                payload["metadata"] = metadata
            
            response = requests.post(
                f"{self.base_url}/contacts",
                json=payload,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Contact created in Thoughtly: {phone_number}")
                return response.json()
            else:
                logger.error(f"Failed to create contact: {response.text}")
                return {"error": response.text, "status_code": response.status_code}
                
        except Exception as e:
            logger.error(f"Exception creating contact: {str(e)}")
            return {"error": str(e)}
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get current usage statistics
        
        Returns:
            Dict containing usage data (credits, minutes, etc.)
        """
        try:
            response = requests.get(
                f"{self.base_url}/usage",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get usage stats: {response.text}")
                return {"error": response.text, "status_code": response.status_code}
                
        except Exception as e:
            logger.error(f"Exception getting usage stats: {str(e)}")
            return {"error": str(e)}
    
    def transfer_call(self, call_id: str, target_number: str) -> Dict[str, Any]:
        """
        Transfer an active call to another number
        
        Args:
            call_id: Thoughtly call ID
            target_number: Number to transfer to
            
        Returns:
            Dict containing transfer result
        """
        try:
            payload = {
                "target_number": target_number
            }
            
            response = requests.post(
                f"{self.base_url}/calls/{call_id}/transfer",
                json=payload,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Call {call_id} transferred to {target_number}")
                return response.json()
            else:
                logger.error(f"Failed to transfer call: {response.text}")
                return {"error": response.text, "status_code": response.status_code}
                
        except Exception as e:
            logger.error(f"Exception transferring call: {str(e)}")
            return {"error": str(e)}
