
"""
Transcription Service
Converts speech to text for all calls
Uses Vonage's built-in ASR capability
"""
import logging
from datetime import datetime
import json
import os

logger = logging.getLogger(__name__)

class TranscriptionService:
    def __init__(self):
        self.storage_path = os.getenv('TRANSCRIPTION_STORAGE_PATH', './transcriptions')
        os.makedirs(self.storage_path, exist_ok=True)
        logger.info("Transcription Service initialized")
    
    def save_transcription(self, conversation_uuid, speaker, text, timestamp=None):
        """
        Save transcription segment
        
        Args:
            conversation_uuid: Call identifier
            speaker: 'user' or 'ai'
            text: Transcribed text
            timestamp: Optional timestamp
        """
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        transcription_file = os.path.join(
            self.storage_path,
            f"{conversation_uuid}.jsonl"
        )
        
        entry = {
            'timestamp': timestamp,
            'speaker': speaker,
            'text': text
        }
        
        try:
            with open(transcription_file, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            logger.error(f"Failed to save transcription: {e}")
    
    def get_transcription(self, conversation_uuid):
        """
        Get full transcription for a call
        
        Args:
            conversation_uuid: Call identifier
            
        Returns:
            List of transcription entries
        """
        transcription_file = os.path.join(
            self.storage_path,
            f"{conversation_uuid}.jsonl"
        )
        
        transcriptions = []
        try:
            with open(transcription_file, 'r') as f:
                for line in f:
                    transcriptions.append(json.loads(line))
            return transcriptions
        except FileNotFoundError:
            return []
        except Exception as e:
            logger.error(f"Failed to read transcription: {e}")
            return []
    
    def get_full_conversation_text(self, conversation_uuid):
        """
        Get formatted full conversation text
        
        Args:
            conversation_uuid: Call identifier
            
        Returns:
            Formatted conversation string
        """
        transcriptions = self.get_transcription(conversation_uuid)
        
        conversation = []
        for entry in transcriptions:
            speaker_label = "Customer" if entry['speaker'] == 'user' else "AI"
            conversation.append(f"{speaker_label}: {entry['text']}")
        
        return '\n'.join(conversation)

# Global transcription service instance
transcription_service = TranscriptionService()
