
"""
Call Recording Service - Phase 9
Handles Vonage call recording and storage
"""

import os
import logging
import requests
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class RecordingService:
    """Manages call recordings via Vonage"""
    
    def __init__(self, db_connection=None):
        self.db = db_connection
        self.vonage_api_key = os.getenv('VONAGE_API_KEY')
        self.vonage_api_secret = os.getenv('VONAGE_API_SECRET')
        self.vonage_app_id = os.getenv('VONAGE_APPLICATION_ID')
        self.recordings_dir = os.getenv('RECORDINGS_DIR', './recordings/audio')
        
        # Create recordings directory if it doesn't exist
        os.makedirs(self.recordings_dir, exist_ok=True)
        
        self.enabled = bool(self.vonage_api_key and self.vonage_api_secret)
        
        if self.enabled:
            logger.info("Recording Service initialized")
        else:
            logger.warning("Recording Service disabled (missing Vonage credentials)")
    
    def start_recording(self, conversation_uuid):
        """
        Start recording a call
        
        Args:
            conversation_uuid: Vonage conversation UUID
            
        Returns:
            dict with recording info or None
        """
        if not self.enabled:
            logger.warning("Recording service disabled")
            return None
        
        try:
            url = f"https://api.nexmo.com/v1/calls/{conversation_uuid}/stream"
            
            headers = {
                'Authorization': f'Bearer {self._generate_jwt()}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'action': 'start',
                'format': 'mp3',
                'channels': 2,
                'beep_start': False
            }
            
            response = requests.put(url, headers=headers, json=data)
            
            if response.status_code == 200:
                logger.info(f"Recording started for conversation {conversation_uuid}")
                return response.json()
            else:
                logger.error(f"Failed to start recording: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error starting recording: {str(e)}")
            return None
    
    def stop_recording(self, conversation_uuid):
        """Stop recording a call"""
        if not self.enabled:
            return None
        
        try:
            url = f"https://api.nexmo.com/v1/calls/{conversation_uuid}/stream"
            
            headers = {
                'Authorization': f'Bearer {self._generate_jwt()}',
                'Content-Type': 'application/json'
            }
            
            data = {'action': 'stop'}
            
            response = requests.put(url, headers=headers, json=data)
            
            if response.status_code == 200:
                logger.info(f"Recording stopped for conversation {conversation_uuid}")
                return response.json()
            else:
                logger.error(f"Failed to stop recording: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error stopping recording: {str(e)}")
            return None
    
    def download_recording(self, recording_url, call_uuid):
        """
        Download recording from Vonage and save locally
        
        Args:
            recording_url: URL to download recording from
            call_uuid: Call UUID for filename
            
        Returns:
            str: Local file path or None
        """
        if not self.enabled:
            return None
        
        try:
            # Get recording from Vonage
            headers = {
                'Authorization': f'Bearer {self._generate_jwt()}'
            }
            
            response = requests.get(recording_url, headers=headers, stream=True)
            
            if response.status_code == 200:
                # Save to file
                filename = f"{call_uuid}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
                filepath = os.path.join(self.recordings_dir, filename)
                
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                logger.info(f"Recording downloaded: {filepath}")
                
                # Save to database
                self._save_recording_metadata(call_uuid, filepath, recording_url)
                
                return filepath
            else:
                logger.error(f"Failed to download recording: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error downloading recording: {str(e)}")
            return None
    
    def get_recording_path(self, call_uuid):
        """Get local path to recording file"""
        if not self.db:
            return None
        
        try:
            cursor = self.db.cursor()
            cursor.execute(
                "SELECT file_path FROM call_recordings WHERE call_uuid = ?",
                (call_uuid,)
            )
            result = cursor.fetchone()
            return result[0] if result else None
            
        except Exception as e:
            logger.error(f"Error getting recording path: {str(e)}")
            return None
    
    def _save_recording_metadata(self, call_uuid, file_path, recording_url):
        """Save recording metadata to database"""
        if not self.db:
            return
        
        try:
            # Get file size
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO call_recordings 
                (call_uuid, file_path, recording_url, file_size, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                call_uuid,
                file_path,
                recording_url,
                file_size,
                datetime.now().isoformat()
            ))
            self.db.commit()
            
            logger.info(f"Recording metadata saved for {call_uuid}")
            
        except Exception as e:
            logger.error(f"Error saving recording metadata: {str(e)}")
    
    def _generate_jwt(self):
        """Generate JWT token for Vonage API authentication"""
        import jwt
        import time
        
        payload = {
            'application_id': self.vonage_app_id,
            'iat': int(time.time()),
            'exp': int(time.time()) + 3600,
            'jti': str(time.time())
        }
        
        # Read private key
        private_key_path = os.getenv('VONAGE_PRIVATE_KEY_PATH', './private.key')
        
        try:
            with open(private_key_path, 'r') as f:
                private_key = f.read()
            
            token = jwt.encode(payload, private_key, algorithm='RS256')
            return token
            
        except Exception as e:
            logger.error(f"Error generating JWT: {str(e)}")
            # Fallback to basic auth
            return None


# Global recording service instance
recording_service = RecordingService()
