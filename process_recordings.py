
#!/usr/bin/env python3
"""
Background job to process recordings and transcriptions
Runs periodically to catch any recordings that arrived after calls ended
"""

import os
import sys
import time
import logging
import requests
import json
from datetime import datetime, timedelta
import database

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import transcription service
sys.path.append(os.path.dirname(__file__))
from transcriptions.transcription_service import TranscriptionService

# Initialize transcription service
transcription_service = TranscriptionService()

# Vonage API credentials
VONAGE_API_KEY = os.getenv('VONAGE_API_KEY')
VONAGE_API_SECRET = os.getenv('VONAGE_API_SECRET')
VONAGE_APPLICATION_ID = os.getenv('VONAGE_APPLICATION_ID')

# Dashboard API
DASHBOARD_API_URL = os.getenv('DASHBOARD_API_URL', 'https://phone-system-dashboa-8em0c9.abacusai.app')
DASHBOARD_API_KEY = os.getenv('DASHBOARD_API_KEY', 'internal_api_key_12345')


def get_recent_calls_without_recordings():
    """Get calls from last 24 hours that don't have recordings yet"""
    try:
        headers = {
            'X-API-Key': DASHBOARD_API_KEY
        }
        
        # Get calls from last 24 hours
        response = requests.get(
            f"{DASHBOARD_API_URL}/api/call-logs?limit=100",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            calls = data.get('calls', [])
            
            # Filter calls without recordings
            calls_without_recordings = [
                call for call in calls 
                if not call.get('recordingUrl') or not call.get('transcription')
            ]
            
            logger.info(f"Found {len(calls_without_recordings)} calls without recordings/transcriptions")
            return calls_without_recordings
        else:
            logger.error(f"Failed to fetch calls: {response.status_code}")
            return []
            
    except Exception as e:
        logger.error(f"Error fetching calls: {e}")
        return []


def update_call_with_recording(call_id, recording_url):
    """Update call log with recording URL"""
    try:
        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': DASHBOARD_API_KEY
        }
        
        payload = {'recordingUrl': recording_url}
        
        response = requests.patch(
            f"{DASHBOARD_API_URL}/api/call-logs/{call_id}",
            json=payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info(f"✓ Updated call {call_id} with recording URL")
            return True
        else:
            logger.error(f"Failed to update call: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error updating call: {e}")
        return False


def transcribe_and_update_call(call_id, recording_url):
    """Download recording, transcribe it, and update call log"""
    try:
        # Download recording
        logger.info(f"Downloading recording for call {call_id}")
        
        # Use Vonage auth to download
        import jwt
        
        payload = {
            'application_id': VONAGE_APPLICATION_ID,
            'iat': int(time.time()),
            'exp': int(time.time()) + 3600,
            'jti': str(time.time())
        }
        
        private_key_path = os.getenv('VONAGE_PRIVATE_KEY_PATH', './private.key')
        
        if not os.path.exists(private_key_path):
            logger.error(f"Private key not found")
            return False
        
        with open(private_key_path, 'r') as f:
            private_key = f.read()
        
        token = jwt.encode(payload, private_key, algorithm='RS256')
        
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(recording_url, headers=headers, timeout=30, stream=True)
        
        if response.status_code != 200:
            logger.error(f"Failed to download recording: {response.status_code}")
            return False
        
        # Save temporarily
        temp_file = f"/tmp/recording_{call_id}.mp3"
        with open(temp_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"Recording downloaded: {temp_file}")
        
        # Transcribe
        if transcription_service.enabled:
            logger.info(f"Transcribing recording for call {call_id}")
            result = transcription_service.transcribe_recording(temp_file, call_id)
            
            if result and result.get('success'):
                transcription = result.get('transcription')
                
                # Update call log with transcription
                headers = {
                    'Content-Type': 'application/json',
                    'X-API-Key': DASHBOARD_API_KEY
                }
                
                payload = {'transcription': transcription}
                
                response = requests.patch(
                    f"{DASHBOARD_API_URL}/api/call-logs/{call_id}",
                    json=payload,
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    logger.info(f"✓ Updated call {call_id} with transcription")
                else:
                    logger.error(f"Failed to update transcription: {response.status_code}")
                
                # Clean up temp file
                os.remove(temp_file)
                return True
            else:
                logger.warning(f"Transcription failed for call {call_id}")
        else:
            logger.warning("Transcription service not enabled")
        
        # Clean up temp file
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        return False
        
    except Exception as e:
        logger.error(f"Error transcribing recording: {e}")
        return False


def process_recordings_job():
    """Main job to process recordings"""
    logger.info("Starting recording processing job")
    
    # Get calls without recordings
    calls = get_recent_calls_without_recordings()
    
    if not calls:
        logger.info("No calls to process")
        return
    
    processed = 0
    for call in calls:
        call_id = call.get('id')
        recording_url = call.get('recordingUrl')
        transcription = call.get('transcription')
        
        logger.info(f"Processing call {call_id}")
        
        # If we have recording URL but no transcription, transcribe it
        if recording_url and not transcription:
            logger.info(f"Call {call_id} has recording but no transcription")
            if transcribe_and_update_call(call_id, recording_url):
                processed += 1
        
        # Add small delay to avoid rate limiting
        time.sleep(0.5)
    
    logger.info(f"✓ Processed {processed} recordings")


if __name__ == '__main__':
    # Run once
    process_recordings_job()
