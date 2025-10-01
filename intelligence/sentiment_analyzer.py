
"""
Sentiment Analysis Service
Detects customer emotions: frustration, urgency, satisfaction, confusion
"""
import logging
from textblob import TextBlob

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    def __init__(self):
        # Keywords for detecting specific emotions
        self.frustration_keywords = [
            'frustrated', 'annoyed', 'upset', 'angry', 'ridiculous', 
            'terrible', 'awful', 'worst', 'hate', 'stupid', 'useless'
        ]
        
        self.urgency_keywords = [
            'urgent', 'asap', 'emergency', 'immediately', 'right now',
            'quickly', 'hurry', 'fast', 'need now', 'today', 'tonight'
        ]
        
        self.confusion_keywords = [
            'confused', 'don\'t understand', 'what do you mean', 'unclear',
            'not sure', 'i don\'t know', 'can you explain', 'help me understand'
        ]
        
        logger.info("Sentiment Analyzer initialized")
    
    def analyze_sentiment(self, text):
        """
        Analyze sentiment of customer message
        
        Args:
            text: Customer's message text
            
        Returns:
            Dict with sentiment analysis results
        """
        text_lower = text.lower()
        
        # Use TextBlob for polarity and subjectivity
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity  # -1 to 1
        subjectivity = blob.sentiment.subjectivity  # 0 to 1
        
        # Detect specific emotions
        is_frustrated = any(keyword in text_lower for keyword in self.frustration_keywords)
        is_urgent = any(keyword in text_lower for keyword in self.urgency_keywords)
        is_confused = any(keyword in text_lower for keyword in self.confusion_keywords)
        
        # Determine overall sentiment
        if polarity > 0.3:
            sentiment = 'positive'
        elif polarity < -0.3:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        
        # Determine emotion
        if is_frustrated:
            emotion = 'frustrated'
        elif is_urgent:
            emotion = 'urgent'
        elif is_confused:
            emotion = 'confused'
        elif sentiment == 'positive':
            emotion = 'satisfied'
        else:
            emotion = 'neutral'
        
        result = {
            'sentiment': sentiment,
            'emotion': emotion,
            'polarity': round(polarity, 2),
            'subjectivity': round(subjectivity, 2),
            'is_frustrated': is_frustrated,
            'is_urgent': is_urgent,
            'is_confused': is_confused,
            'confidence': abs(polarity)  # Confidence in sentiment
        }
        
        logger.info(f"Sentiment analysis: {result['sentiment']}, emotion: {result['emotion']}")
        
        return result
    
    def should_escalate(self, sentiment_result):
        """
        Determine if call should be escalated based on sentiment
        
        Args:
            sentiment_result: Result from analyze_sentiment()
            
        Returns:
            Boolean indicating if escalation is recommended
        """
        # Escalate if customer is frustrated or very negative
        if sentiment_result['is_frustrated']:
            return True
        
        if sentiment_result['sentiment'] == 'negative' and sentiment_result['polarity'] < -0.5:
            return True
        
        return False
    
    def get_adaptive_response_style(self, sentiment_result):
        """
        Get recommended response style based on sentiment
        
        Args:
            sentiment_result: Result from analyze_sentiment()
            
        Returns:
            Dict with response recommendations
        """
        if sentiment_result['is_frustrated']:
            return {
                'tone': 'empathetic',
                'speed': 'slower',
                'recommendation': 'Apologize and offer to escalate to manager'
            }
        
        elif sentiment_result['is_urgent']:
            return {
                'tone': 'efficient',
                'speed': 'faster',
                'recommendation': 'Prioritize quick resolution'
            }
        
        elif sentiment_result['is_confused']:
            return {
                'tone': 'patient',
                'speed': 'slower',
                'recommendation': 'Provide clear, simple explanations'
            }
        
        else:
            return {
                'tone': 'friendly',
                'speed': 'normal',
                'recommendation': 'Continue normal conversation'
            }

# Global sentiment analyzer instance
sentiment_analyzer = SentimentAnalyzer()
