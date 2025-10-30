
"""
Azure Text-to-Speech Service
Generates high-quality speech using Azure Neural HD voices
"""

import os
import json
import requests
import logging
from typing import Optional, Dict
from datetime import datetime, timedelta
import hashlib
import base64

logger = logging.getLogger(__name__)


class AzureTTSService:
    """Service for generating speech using Azure Neural HD voices"""
    
    # Voice configurations
    VOICES = {
        'andrew': {
            'name': 'en-US-AndrewMultilingualNeural',
            'gender': 'Male',
            'description': 'HD quality, warm and professional',
            'style': 'conversational'
        },
        'ava': {
            'name': 'en-US-AvaMultilingualNeural', 
            'gender': 'Female',
            'description': 'HD quality, friendly and engaging',
            'style': 'conversational'
        },
        'ryan': {
            'name': 'en-US-RyanMultilingualNeural',
            'gender': 'Male',
            'description': 'Neural quality, warm tone',
            'style': 'conversational'
        },
        'jenny': {
            'name': 'en-US-JennyNeural',
            'gender': 'Female',
            'description': 'Neural quality, clear and professional',
            'style': 'customerservice'
        }
    }
    
    def __init__(self):
        """Initialize Azure TTS service with credentials"""
        self.speech_key = None
        self.speech_region = None
        self.access_token = None
        self.token_expires_at = None
        
        # Load credentials
        self._load_azure_credentials()
        
        # Set up audio output format
        self.output_format = "audio-24khz-96kbitrate-mono-mp3"  # High quality
        
        # Cache directory for generated audio
        self.cache_dir = os.path.join(os.path.dirname(__file__), 'audio_cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        
        logger.info("Azure TTS Service initialized")
    
    def _load_azure_credentials(self):
        """Load Azure credentials from auth secrets"""
        try:
            secrets_path = '/home/ubuntu/.config/abacusai_auth_secrets.json'
            
            if os.path.exists(secrets_path):
                with open(secrets_path, 'r') as f:
                    secrets = json.load(f)
                
                azure_secrets = secrets.get('azure cognitive services', {}).get('secrets', {})
                self.speech_key = azure_secrets.get('speech_key', {}).get('value')
                self.speech_region = azure_secrets.get('speech_region', {}).get('value')
                
                if self.speech_key and self.speech_region:
                    logger.info("✅ Azure TTS credentials loaded successfully")
                else:
                    logger.warning("⚠️  Azure credentials incomplete")
            else:
                logger.warning(f"Secrets file not found: {secrets_path}")
                
        except Exception as e:
            logger.error(f"Error loading Azure credentials: {str(e)}")
    
    def _get_access_token(self) -> Optional[str]:
        """Get or refresh Azure access token"""
        # Check if we have a valid token
        if self.access_token and self.token_expires_at:
            if datetime.now() < self.token_expires_at:
                return self.access_token
        
        # Get new token
        try:
            token_url = f"https://{self.speech_region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
            headers = {"Ocp-Apim-Subscription-Key": self.speech_key}
            
            response = requests.post(token_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                self.access_token = response.text
                # Token expires in 10 minutes, refresh at 9 minutes
                self.token_expires_at = datetime.now() + timedelta(minutes=9)
                logger.info("✅ Access token obtained")
                return self.access_token
            else:
                logger.error(f"Failed to get access token: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting access token: {str(e)}")
            return None
    
    def generate_speech(
        self, 
        text: str, 
        voice: str = 'andrew',
        style: Optional[str] = None,
        rate: str = '0%',
        pitch: str = '0%'
    ) -> Optional[bytes]:
        """
        Generate speech using Azure Neural HD voices
        
        Args:
            text: Text to convert to speech
            voice: Voice to use (andrew, ava, ryan, jenny)
            style: Speaking style (e.g., 'friendly', 'cheerful')
            rate: Speech rate adjustment (-50% to +50%)
            pitch: Pitch adjustment (-50% to +50%)
            
        Returns:
            Audio data as bytes, or None if failed
        """
        if not self.speech_key or not self.speech_region:
            logger.error("Azure credentials not configured")
            return None
        
        # Get voice configuration
        voice_config = self.VOICES.get(voice, self.VOICES['andrew'])
        voice_name = voice_config['name']
        
        # Build SSML
        ssml = self._build_ssml(text, voice_name, voice_config, style, rate, pitch)
        
        # Generate cache key
        cache_key = self._get_cache_key(text, voice, style, rate, pitch)
        cache_path = os.path.join(self.cache_dir, f"{cache_key}.mp3")
        
        # Check cache first
        if os.path.exists(cache_path):
            logger.info(f"✅ Using cached audio for: {text[:50]}...")
            with open(cache_path, 'rb') as f:
                return f.read()
        
        # Generate new audio
        try:
            # Get access token
            token = self._get_access_token()
            if not token:
                logger.error("Failed to get access token")
                return None
            
            # TTS endpoint
            tts_url = f"https://{self.speech_region}.tts.speech.microsoft.com/cognitiveservices/v1"
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": self.output_format,
                "User-Agent": "SportsRentalPhoneSystem"
            }
            
            # Make request
            response = requests.post(
                tts_url, 
                headers=headers, 
                data=ssml.encode('utf-8'),
                timeout=30
            )
            
            if response.status_code == 200:
                audio_data = response.content
                logger.info(f"✅ Generated audio: {len(audio_data)} bytes for: {text[:50]}...")
                
                # Cache the audio
                with open(cache_path, 'wb') as f:
                    f.write(audio_data)
                
                return audio_data
            else:
                logger.error(f"TTS request failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating speech: {str(e)}")
            return None
    
    def generate_speech_stream_url(
        self,
        text: str,
        voice: str = 'andrew',
        style: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate speech and return a stream URL for Vonage
        
        Args:
            text: Text to convert to speech
            voice: Voice to use
            style: Speaking style
            
        Returns:
            Base64 encoded data URL for streaming
        """
        audio_data = self.generate_speech(text, voice, style)
        
        if audio_data:
            # Convert to base64 data URL
            base64_audio = base64.b64encode(audio_data).decode('utf-8')
            data_url = f"data:audio/mp3;base64,{base64_audio}"
            return data_url
        
        return None
    
    def _build_ssml(
        self, 
        text: str, 
        voice_name: str,
        voice_config: Dict,
        style: Optional[str],
        rate: str,
        pitch: str
    ) -> str:
        """Build SSML for speech synthesis"""
        
        # Start SSML
        ssml = f"""<speak version='1.0' xml:lang='en-US' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='https://www.w3.org/2001/mstts'>
    <voice name='{voice_name}'>"""
        
        # Add style if specified
        if style:
            ssml += f"""
        <mstts:express-as style='{style}'>"""
        
        # Add prosody adjustments
        if rate != '0%' or pitch != '0%':
            ssml += f"""
            <prosody rate='{rate}' pitch='{pitch}'>
                {text}
            </prosody>"""
        else:
            ssml += f"""
            {text}"""
        
        # Close style tag if used
        if style:
            ssml += """
        </mstts:express-as>"""
        
        # Close SSML
        ssml += """
    </voice>
</speak>"""
        
        return ssml
    
    def _get_cache_key(self, text: str, voice: str, style: Optional[str], rate: str, pitch: str) -> str:
        """Generate cache key for audio file"""
        key_string = f"{text}_{voice}_{style}_{rate}_{pitch}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get_available_voices(self) -> Dict:
        """Get list of available voices"""
        return self.VOICES
    
    def test_service(self) -> Dict:
        """Test Azure TTS service connectivity"""
        test_text = "Hello, this is a test of the Azure text to speech service."
        
        result = {
            'credentials_loaded': bool(self.speech_key and self.speech_region),
            'region': self.speech_region,
            'voices': list(self.VOICES.keys())
        }
        
        # Try to generate test audio
        audio = self.generate_speech(test_text, voice='andrew')
        
        if audio:
            result['service_status'] = 'active'
            result['test_audio_size'] = len(audio)
        else:
            result['service_status'] = 'failed'
        
        return result


# Global instance
azure_tts = AzureTTSService()
