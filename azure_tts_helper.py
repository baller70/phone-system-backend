
"""
Azure TTS Helper for Vonage Integration
Provides helper functions to use Azure TTS with Vonage Voice API
"""

import logging
from typing import Optional, List, Dict
import os
from azure_tts_service import azure_tts

logger = logging.getLogger(__name__)

# Configuration
BASE_URL = os.getenv('BASE_URL', 'https://phone-system-backend.onrender.com')
AZURE_AUDIO_WEBHOOK = f"{BASE_URL}/audio/azure/"

# Voice selection (can be changed globally)
DEFAULT_VOICE = 'andrew'  # or 'ava', 'ryan', 'jenny'


def create_azure_speech_ncco(
    text: str,
    voice: str = DEFAULT_VOICE,
    style: Optional[str] = None,
    allow_barge_in: bool = False
) -> List[Dict]:
    """
    Create NCCO using Azure TTS instead of Vonage's built-in voice
    
    Args:
        text: Text to speak
        voice: Azure voice to use (andrew, ava, ryan, jenny)
        style: Speaking style (e.g., 'friendly', 'cheerful')
        allow_barge_in: Whether to allow user to interrupt
        
    Returns:
        NCCO action list
    """
    try:
        # Generate speech with Azure
        audio_data = azure_tts.generate_speech(text, voice, style)
        
        if audio_data:
            # Save audio to file for streaming
            import hashlib
            import base64
            
            # Generate unique filename
            text_hash = hashlib.md5(text.encode()).hexdigest()[:16]
            filename = f"{text_hash}_{voice}.mp3"
            audio_path = os.path.join(azure_tts.cache_dir, filename)
            
            # Save audio
            with open(audio_path, 'wb') as f:
                f.write(audio_data)
            
            # Create stream URL (we'll serve this via Flask)
            stream_url = f"{AZURE_AUDIO_WEBHOOK}{filename}"
            
            logger.info(f"✅ Created Azure TTS audio: {stream_url}")
            
            return [
                {
                    "action": "stream",
                    "streamUrl": [stream_url],
                    "bargeIn": allow_barge_in
                }
            ]
        else:
            # Fallback to Vonage TTS if Azure fails
            logger.warning("Azure TTS failed, falling back to Vonage TTS")
            return _create_vonage_fallback_ncco(text, allow_barge_in)
            
    except Exception as e:
        logger.error(f"Error creating Azure speech NCCO: {str(e)}")
        return _create_vonage_fallback_ncco(text, allow_barge_in)


def create_azure_speech_input_ncco(
    text: str,
    context_state: str,
    voice: str = DEFAULT_VOICE,
    style: Optional[str] = None,
    max_duration: int = 60
) -> List[Dict]:
    """
    Create NCCO for speech with input (question/response flow)
    
    Args:
        text: Text to speak
        context_state: Context for the input handler
        voice: Azure voice to use
        style: Speaking style
        max_duration: Maximum input duration in seconds
        
    Returns:
        NCCO action list with speech and input
    """
    try:
        # Calculate speech duration for timing
        words = len(text.split())
        speech_duration = (words / 2.5) + 1
        start_timeout = max(10, int(speech_duration) + 2)
        
        # Generate Azure speech
        audio_data = azure_tts.generate_speech(text, voice, style)
        
        if audio_data:
            # Save audio
            import hashlib
            text_hash = hashlib.md5(text.encode()).hexdigest()[:16]
            filename = f"{text_hash}_{voice}.mp3"
            audio_path = os.path.join(azure_tts.cache_dir, filename)
            
            with open(audio_path, 'wb') as f:
                f.write(audio_data)
            
            stream_url = f"{AZURE_AUDIO_WEBHOOK}{filename}"
            
            return [
                {
                    "action": "stream",
                    "streamUrl": [stream_url],
                    "bargeIn": False  # Don't allow interruption
                },
                {
                    "action": "input",
                    "eventUrl": [f"{BASE_URL}/webhooks/speech"],
                    "type": ["speech"],
                    "speech": {
                        "endOnSilence": 3,
                        "language": "en-US",
                        "context": ["sports", "basketball", "booking", "rental", "party", "yes", "no"],
                        "startTimeout": start_timeout,
                        "maxDuration": max_duration
                    }
                }
            ]
        else:
            # Fallback
            logger.warning("Azure TTS failed for speech input, using Vonage")
            return _create_vonage_fallback_input_ncco(text, context_state, start_timeout, max_duration)
            
    except Exception as e:
        logger.error(f"Error creating Azure speech input NCCO: {str(e)}")
        return _create_vonage_fallback_input_ncco(text, context_state, 10, max_duration)


def _create_vonage_fallback_ncco(text: str, allow_barge_in: bool = False) -> List[Dict]:
    """Fallback to Vonage TTS if Azure fails"""
    return [
        {
            "action": "talk",
            "text": text,
            "voiceName": "Amy",
            "bargeIn": allow_barge_in
        }
    ]


def _create_vonage_fallback_input_ncco(
    text: str, 
    context_state: str,
    start_timeout: int,
    max_duration: int
) -> List[Dict]:
    """Fallback to Vonage TTS with input if Azure fails"""
    return [
        {
            "action": "talk",
            "text": text,
            "voiceName": "Amy",
            "bargeIn": False
        },
        {
            "action": "input",
            "eventUrl": [f"{BASE_URL}/webhooks/speech"],
            "type": ["speech"],
            "speech": {
                "endOnSilence": 3,
                "language": "en-US",
                "context": ["sports", "basketball", "booking", "rental", "party", "yes", "no"],
                "startTimeout": start_timeout,
                "maxDuration": max_duration
            }
        }
    ]


def get_voice_info() -> Dict:
    """Get information about available Azure voices"""
    return azure_tts.get_available_voices()


def test_azure_service() -> Dict:
    """Test Azure TTS service"""
    return azure_tts.test_service()
