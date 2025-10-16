
"""
Transcription Service - Phase 9
Converts call recordings to text using Azure Speech-to-Text
"""

import os
import logging
import json
from datetime import datetime
import azure.cognitiveservices.speech as speechsdk

logger = logging.getLogger(__name__)


class TranscriptionService:
    """Handles speech-to-text transcription using Azure"""
    
    def __init__(self, db_connection=None):
        self.db = db_connection
        
        # Load Azure credentials from auth secrets
        self.speech_key = None
        self.speech_region = None
        
        self._load_azure_credentials()
        
        self.enabled = bool(self.speech_key and self.speech_region)
        
        if self.enabled:
            # Initialize Azure Speech Config
            self.speech_config = speechsdk.SpeechConfig(
                subscription=self.speech_key,
                region=self.speech_region
            )
            self.speech_config.speech_recognition_language = "en-US"
            logger.info("Transcription Service initialized with Azure Speech")
        else:
            logger.warning("Transcription Service disabled (missing Azure credentials)")
    
    def _load_azure_credentials(self):
        """Load Azure credentials from auth secrets file"""
        try:
            secrets_path = '/home/ubuntu/.config/abacusai_auth_secrets.json'
            
            if os.path.exists(secrets_path):
                with open(secrets_path, 'r') as f:
                    secrets = json.load(f)
                
                azure_secrets = secrets.get('azure cognitive services', {}).get('secrets', {})
                self.speech_key = azure_secrets.get('speech_key', {}).get('value')
                self.speech_region = azure_secrets.get('speech_region', {}).get('value')
                
                if self.speech_key and self.speech_region:
                    logger.info("Azure credentials loaded successfully")
                else:
                    logger.warning("Azure credentials not found in secrets file")
            else:
                logger.warning(f"Secrets file not found: {secrets_path}")
                
        except Exception as e:
            logger.error(f"Error loading Azure credentials: {str(e)}")
    
    def transcribe_recording(self, audio_file_path, call_uuid):
        """
        Transcribe audio file to text
        
        Args:
            audio_file_path: Path to audio file
            call_uuid: Call UUID for metadata
            
        Returns:
            dict with transcription results
        """
        if not self.enabled:
            logger.warning("Transcription service disabled")
            return None
        
        if not os.path.exists(audio_file_path):
            logger.error(f"Audio file not found: {audio_file_path}")
            return None
        
        try:
            logger.info(f"Starting transcription for {audio_file_path}")
            
            # Create audio config
            audio_config = speechsdk.AudioConfig(filename=audio_file_path)
            
            # Create speech recognizer
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )
            
            # Store transcribed text
            transcribed_text = []
            
            def handle_final_result(evt):
                """Callback for final recognition results"""
                if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                    transcribed_text.append(evt.result.text)
            
            # Connect callback
            speech_recognizer.recognized.connect(handle_final_result)
            
            # Start continuous recognition
            speech_recognizer.start_continuous_recognition()
            
            # Wait for transcription to complete
            import time
            timeout = 300  # 5 minutes max
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                time.sleep(1)
                # Check if we have transcription
                if transcribed_text:
                    # Wait a bit more to ensure we got everything
                    time.sleep(5)
                    break
            
            # Stop recognition
            speech_recognizer.stop_continuous_recognition()
            
            # Combine transcribed text
            full_transcription = ' '.join(transcribed_text)
            
            if full_transcription:
                logger.info(f"Transcription completed: {len(full_transcription)} characters")
                
                # Save to database
                self._save_transcription(call_uuid, full_transcription, audio_file_path)
                
                return {
                    'success': True,
                    'transcription': full_transcription,
                    'word_count': len(full_transcription.split()),
                    'char_count': len(full_transcription)
                }
            else:
                logger.warning("No transcription generated")
                return {
                    'success': False,
                    'error': 'No speech detected in audio'
                }
                
        except Exception as e:
            logger.error(f"Error transcribing audio: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_transcription(self, call_uuid):
        """Get transcription for a call"""
        if not self.db:
            return None
        
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                SELECT transcription_text, word_count, created_at
                FROM call_transcriptions
                WHERE call_uuid = ?
            """, (call_uuid,))
            
            result = cursor.fetchone()
            
            if result:
                return {
                    'transcription': result[0],
                    'word_count': result[1],
                    'created_at': result[2]
                }
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error getting transcription: {str(e)}")
            return None
    
    def _save_transcription(self, call_uuid, transcription_text, audio_file_path):
        """Save transcription to database"""
        if not self.db:
            return
        
        try:
            word_count = len(transcription_text.split())
            char_count = len(transcription_text)
            
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO call_transcriptions
                (call_uuid, transcription_text, word_count, char_count, 
                 audio_file_path, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                call_uuid,
                transcription_text,
                word_count,
                char_count,
                audio_file_path,
                datetime.now().isoformat()
            ))
            self.db.commit()
            
            logger.info(f"Transcription saved for {call_uuid}")
            
        except Exception as e:
            logger.error(f"Error saving transcription: {str(e)}")
    
    def search_transcriptions(self, search_query):
        """Search transcriptions for specific phrases"""
        if not self.db:
            return []
        
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                SELECT call_uuid, transcription_text, created_at
                FROM call_transcriptions
                WHERE transcription_text LIKE ?
                ORDER BY created_at DESC
                LIMIT 50
            """, (f'%{search_query}%',))
            
            results = cursor.fetchall()
            
            return [
                {
                    'call_uuid': row[0],
                    'transcription': row[1],
                    'created_at': row[2]
                }
                for row in results
            ]
            
        except Exception as e:
            logger.error(f"Error searching transcriptions: {str(e)}")
            return []


# Global transcription service instance
transcription_service = TranscriptionService()
