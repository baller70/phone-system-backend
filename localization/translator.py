
"""
Phase 7: Multi-Language Translation Service
Supports 10+ languages with automatic detection and translation
"""

import os
from typing import Optional, Dict, List
from googletrans import Translator, LANGUAGES
from langdetect import detect, DetectorFactory
import logging

# Make language detection deterministic
DetectorFactory.seed = 0

logger = logging.getLogger(__name__)

class TranslationService:
    """
    Multi-language translation service using Google Translate
    """
    
    # Supported languages for the sports facility booking system
    SUPPORTED_LANGUAGES = {
        'en': 'English',
        'es': 'Spanish',
        'fr': 'French',
        'zh-cn': 'Chinese (Simplified)',
        'hi': 'Hindi',
        'pt': 'Portuguese',
        'de': 'German',
        'ja': 'Japanese',
        'ko': 'Korean',
        'ar': 'Arabic'
    }
    
    def __init__(self):
        self.translator = Translator()
        self.default_language = os.getenv('DEFAULT_LANGUAGE', 'en')
        self.cache = {}  # Simple in-memory cache
    
    def detect_language(self, text: str) -> str:
        """
        Detect the language of the input text
        
        Args:
            text: Input text to detect
            
        Returns:
            Language code (e.g., 'en', 'es', 'fr')
        """
        try:
            if not text or len(text.strip()) < 3:
                return self.default_language
            
            detected = detect(text)
            
            # Map simplified Chinese
            if detected == 'zh':
                detected = 'zh-cn'
            
            # Return only if it's a supported language
            if detected in self.SUPPORTED_LANGUAGES:
                logger.info(f"Detected language: {detected} for text: {text[:50]}")
                return detected
            else:
                logger.warning(f"Unsupported language detected: {detected}, defaulting to {self.default_language}")
                return self.default_language
                
        except Exception as e:
            logger.error(f"Error detecting language: {e}")
            return self.default_language
    
    def translate(self, text: str, target_language: str, source_language: Optional[str] = None) -> str:
        """
        Translate text from source language to target language
        
        Args:
            text: Text to translate
            target_language: Target language code
            source_language: Source language code (auto-detected if None)
            
        Returns:
            Translated text
        """
        try:
            # Check if translation is needed
            if not text or not text.strip():
                return text
            
            if target_language not in self.SUPPORTED_LANGUAGES:
                logger.warning(f"Unsupported target language: {target_language}")
                return text
            
            # Check cache
            cache_key = f"{text}:{source_language}:{target_language}"
            if cache_key in self.cache:
                return self.cache[cache_key]
            
            # Detect source language if not provided
            if not source_language:
                source_language = self.detect_language(text)
            
            # No translation needed if same language
            if source_language == target_language:
                return text
            
            # Perform translation
            result = self.translator.translate(
                text,
                src=source_language,
                dest=target_language
            )
            
            translated_text = result.text
            
            # Cache the result
            self.cache[cache_key] = translated_text
            
            logger.info(f"Translated from {source_language} to {target_language}: {text[:50]} -> {translated_text[:50]}")
            
            return translated_text
            
        except Exception as e:
            logger.error(f"Error translating text: {e}")
            return text  # Return original text on error
    
    def translate_conversation(self, messages: List[Dict], target_language: str) -> List[Dict]:
        """
        Translate an entire conversation history
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            target_language: Target language code
            
        Returns:
            List of translated messages
        """
        translated_messages = []
        
        for message in messages:
            translated_message = message.copy()
            if 'content' in message:
                translated_message['content'] = self.translate(
                    message['content'],
                    target_language
                )
            translated_messages.append(translated_message)
        
        return translated_messages
    
    def get_greeting(self, language: str) -> str:
        """
        Get a localized greeting message
        
        Args:
            language: Language code
            
        Returns:
            Greeting in the specified language
        """
        greetings = {
            'en': "Hello! Welcome to our sports facility booking service. How can I help you today?",
            'es': "¡Hola! Bienvenido a nuestro servicio de reservas de instalaciones deportivas. ¿Cómo puedo ayudarte hoy?",
            'fr': "Bonjour! Bienvenue à notre service de réservation d'installations sportives. Comment puis-je vous aider aujourd'hui?",
            'zh-cn': "你好！欢迎来到我们的体育设施预订服务。我今天能为您做什么？",
            'hi': "नमस्ते! हमारी खेल सुविधा बुकिंग सेवा में आपका स्वागत है। आज मैं आपकी कैसे मदद कर सकता हूँ?",
            'pt': "Olá! Bem-vindo ao nosso serviço de reserva de instalações desportivas. Como posso ajudá-lo hoje?",
            'de': "Hallo! Willkommen bei unserem Sportanlagen-Buchungsservice. Wie kann ich Ihnen heute helfen?",
            'ja': "こんにちは！スポーツ施設予約サービスへようこそ。今日はどのようにお手伝いできますか？",
            'ko': "안녕하세요! 스포츠 시설 예약 서비스에 오신 것을 환영합니다. 오늘 어떻게 도와드릴까요?",
            'ar': "مرحبا! مرحبا بكم في خدمة حجز المرافق الرياضية لدينا. كيف يمكنني مساعدتك اليوم؟"
        }
        
        return greetings.get(language, greetings['en'])
    
    def format_datetime(self, dt: str, language: str) -> str:
        """
        Format datetime according to language locale
        
        Args:
            dt: Datetime string
            language: Language code
            
        Returns:
            Formatted datetime string
        """
        # This is a simplified version. In production, use babel or similar for proper locale formatting
        from datetime import datetime
        
        try:
            dt_obj = datetime.fromisoformat(dt) if isinstance(dt, str) else dt
            
            # Language-specific date formats
            if language in ['en']:
                return dt_obj.strftime('%A, %B %d, %Y at %I:%M %p')
            elif language in ['es', 'fr', 'pt']:
                return dt_obj.strftime('%A %d de %B de %Y a las %H:%M')
            elif language in ['de']:
                return dt_obj.strftime('%A, %d. %B %Y um %H:%M Uhr')
            elif language in ['ja']:
                return dt_obj.strftime('%Y年%m月%d日 %A %H:%M')
            elif language in ['zh-cn']:
                return dt_obj.strftime('%Y年%m月%d日 星期%w %H:%M')
            elif language in ['ko']:
                return dt_obj.strftime('%Y년 %m월 %d일 %A %H:%M')
            elif language in ['ar']:
                return dt_obj.strftime('%Y/%m/%d %A %H:%M')
            else:
                return dt_obj.strftime('%Y-%m-%d %H:%M')
                
        except Exception as e:
            logger.error(f"Error formatting datetime: {e}")
            return dt
    
    def format_currency(self, amount: float, language: str) -> str:
        """
        Format currency according to language locale
        
        Args:
            amount: Amount to format
            language: Language code
            
        Returns:
            Formatted currency string
        """
        currency_formats = {
            'en': f"${amount:.2f}",
            'es': f"{amount:.2f} €",
            'fr': f"{amount:.2f} €",
            'zh-cn': f"¥{amount:.2f}",
            'hi': f"₹{amount:.2f}",
            'pt': f"R$ {amount:.2f}",
            'de': f"{amount:.2f} €",
            'ja': f"¥{amount:.0f}",
            'ko': f"₩{amount:.0f}",
            'ar': f"{amount:.2f} ر.س"
        }
        
        return currency_formats.get(language, f"${amount:.2f}")
    
    def is_supported_language(self, language: str) -> bool:
        """
        Check if a language is supported
        
        Args:
            language: Language code
            
        Returns:
            True if supported, False otherwise
        """
        return language in self.SUPPORTED_LANGUAGES
    
    def get_supported_languages(self) -> Dict[str, str]:
        """
        Get all supported languages
        
        Returns:
            Dictionary of language codes and names
        """
        return self.SUPPORTED_LANGUAGES.copy()


# Global instance
_translator_service = None

def get_translator_service() -> TranslationService:
    """Get or create the global TranslationService instance"""
    global _translator_service
    if _translator_service is None:
        _translator_service = TranslationService()
    return _translator_service
