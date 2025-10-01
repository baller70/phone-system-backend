
"""
Call Recording Service
Records and stores all calls for quality assurance and compliance
"""
import os
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class CallRecordingService:
    def __init__(self):
        self.recording_enabled = os.getenv('ENABLE_CALL_RECORDING', 'true').lower() == 'true'
        self.storage_path = os.getenv('RECORDING_STORAGE_PATH', './recordings')
        
        # Create storage directory if it doesn't exist
        if self.recording_enabled:
            os.makedirs(self.storage_path, exist_ok=True)
            logger.info("Call Recording Service initialized")
    
    def start_recording(self, conversation_uuid, caller_number):
        """
        Start recording a call
        
        Args:
            conversation_uuid: Vonage conversation UUID
            caller_number: Caller's phone number
            
        Returns:
            Recording session info
        """
        if not self.recording_enabled:
            return None
        
        recording_info = {
            'conversation_uuid': conversation_uuid,
            'caller_number': caller_number,
            'start_time': datetime.now().isoformat(),
            'status': 'recording'
        }
        
        logger.info(f"Started recording for call {conversation_uuid}")
        return recording_info
    
    def stop_recording(self, conversation_uuid, recording_url=None):
        """
        Stop recording and save metadata
        
        Args:
            conversation_uuid: Vonage conversation UUID
            recording_url: URL of the recording from Vonage
        """
        if not self.recording_enabled:
            return
        
        metadata = {
            'conversation_uuid': conversation_uuid,
            'stop_time': datetime.now().isoformat(),
            'recording_url': recording_url,
            'status': 'completed'
        }
        
        # Save metadata to file
        metadata_file = os.path.join(
            self.storage_path,
            f"{conversation_uuid}_metadata.json"
        )
        
        try:
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            logger.info(f"Saved recording metadata for {conversation_uuid}")
        except Exception as e:
            logger.error(f"Failed to save recording metadata: {e}")
    
    def get_recording_url(self, conversation_uuid):
        """
        Get the recording URL for a call
        
        Args:
            conversation_uuid: Vonage conversation UUID
            
        Returns:
            Recording URL or None
        """
        metadata_file = os.path.join(
            self.storage_path,
            f"{conversation_uuid}_metadata.json"
        )
        
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
                return metadata.get('recording_url')
        except:
            return None
    
    def enable_recording_for_call(self):
        """
        Return NCCO action to enable recording
        """
        if not self.recording_enabled:
            return []
        
        return [{
            "action": "record",
            "eventUrl": [f"{os.getenv('BASE_URL', '')}/webhooks/recording"],
            "eventMethod": "POST"
        }]

# Global recording service instance
call_recording_service = CallRecordingService()
