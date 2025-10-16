
"""
AI Conversation Intelligence - Phase 9
Advanced analysis of call quality, success, and insights
"""

import logging
import re
from datetime import datetime
from collections import Counter

logger = logging.getLogger(__name__)


class CallIntelligence:
    """Analyzes calls for quality, success metrics, and insights"""
    
    def __init__(self, db_connection=None):
        self.db = db_connection
        
        # Success indicators
        self.success_phrases = [
            'booking confirmed', 'reservation made', 'all set', 'booked',
            'confirmed', 'thank you', 'great', 'perfect', 'sounds good'
        ]
        
        # Problem indicators
        self.problem_phrases = [
            'problem', 'issue', 'error', 'wrong', 'mistake', 'confused',
            'don\'t understand', 'cancel', 'never mind'
        ]
        
        # Upsell opportunities
        self.upsell_phrases = [
            'how much', 'price', 'cost', 'discount', 'deal', 'package',
            'membership', 'regular', 'often', 'weekly', 'monthly'
        ]
        
        logger.info("Call Intelligence initialized")
    
    def analyze_call(self, call_data, transcription=None, sentiment=None):
        """
        Comprehensive call analysis
        
        Args:
            call_data: Dict with call information
            transcription: Call transcription text
            sentiment: Sentiment analysis results
            
        Returns:
            dict with analysis results
        """
        analysis = {
            'call_uuid': call_data.get('uuid'),
            'call_score': 0,
            'success_indicators': [],
            'problem_indicators': [],
            'upsell_opportunities': [],
            'key_phrases': [],
            'insights': [],
            'recommendations': []
        }
        
        # Analyze transcription if available
        if transcription:
            analysis.update(self._analyze_transcription(transcription))
        
        # Analyze sentiment if available
        if sentiment:
            analysis.update(self._analyze_sentiment(sentiment))
        
        # Calculate call score
        analysis['call_score'] = self._calculate_call_score(analysis, call_data)
        
        # Generate insights
        analysis['insights'] = self._generate_insights(analysis, call_data)
        
        # Save analysis to database
        self._save_analysis(analysis)
        
        return analysis
    
    def _analyze_transcription(self, transcription):
        """Analyze transcription text"""
        text_lower = transcription.lower()
        
        # Find success indicators
        success_found = [
            phrase for phrase in self.success_phrases
            if phrase in text_lower
        ]
        
        # Find problems
        problems_found = [
            phrase for phrase in self.problem_phrases
            if phrase in text_lower
        ]
        
        # Find upsell opportunities
        upsell_found = [
            phrase for phrase in self.upsell_phrases
            if phrase in text_lower
        ]
        
        # Extract key phrases (most common 3-4 word phrases)
        key_phrases = self._extract_key_phrases(transcription)
        
        return {
            'success_indicators': success_found,
            'problem_indicators': problems_found,
            'upsell_opportunities': upsell_found,
            'key_phrases': key_phrases[:5]  # Top 5
        }
    
    def _analyze_sentiment(self, sentiment):
        """Analyze sentiment data"""
        analysis = {}
        
        # Check for negative sentiment
        if sentiment.get('sentiment') == 'negative':
            analysis['recommendations'] = [
                'Follow up with customer',
                'Review call for service improvements'
            ]
        
        # Check for frustration
        if sentiment.get('is_frustrated'):
            analysis['recommendations'] = analysis.get('recommendations', []) + [
                'Priority follow-up required',
                'Consider offering discount or compensation'
            ]
        
        return analysis
    
    def _extract_key_phrases(self, text):
        """Extract most common meaningful phrases"""
        # Simple n-gram extraction
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Get 3-grams
        phrases = []
        for i in range(len(words) - 2):
            phrase = ' '.join(words[i:i+3])
            # Filter out common stopwords
            if not any(stop in phrase for stop in ['the', 'and', 'for', 'with', 'this', 'that']):
                phrases.append(phrase)
        
        # Count most common
        phrase_counts = Counter(phrases)
        return [phrase for phrase, count in phrase_counts.most_common(10)]
    
    def _calculate_call_score(self, analysis, call_data):
        """
        Calculate call quality score (0-100)
        
        Factors:
        - Call duration (optimal: 2-5 minutes)
        - Success indicators
        - Problem indicators
        - Sentiment
        - Booking completion
        """
        score = 50  # Base score
        
        # Duration score (optimal: 120-300 seconds)
        duration = call_data.get('duration', 0)
        if 120 <= duration <= 300:
            score += 20
        elif duration > 300:
            score += 10  # Too long might indicate problems
        else:
            score += 5  # Too short
        
        # Success indicators
        score += min(len(analysis.get('success_indicators', [])) * 5, 20)
        
        # Subtract for problems
        score -= min(len(analysis.get('problem_indicators', [])) * 5, 20)
        
        # Booking completion bonus
        if call_data.get('booking_created'):
            score += 15
        
        # Sentiment bonus/penalty
        sentiment_score = call_data.get('sentiment_score', 0)
        if sentiment_score > 0.5:
            score += 10
        elif sentiment_score < -0.5:
            score -= 15
        
        # Ensure score is between 0 and 100
        return max(0, min(100, score))
    
    def _generate_insights(self, analysis, call_data):
        """Generate actionable insights from analysis"""
        insights = []
        
        # Booking success
        if call_data.get('booking_created'):
            insights.append({
                'type': 'success',
                'message': 'Call resulted in successful booking',
                'priority': 'low'
            })
        else:
            insights.append({
                'type': 'warning',
                'message': 'Call did not result in booking - investigate why',
                'priority': 'medium'
            })
        
        # Upsell opportunities
        if analysis.get('upsell_opportunities'):
            insights.append({
                'type': 'opportunity',
                'message': f"Customer mentioned: {', '.join(analysis['upsell_opportunities'][:2])}",
                'priority': 'high'
            })
        
        # Problems detected
        if analysis.get('problem_indicators'):
            insights.append({
                'type': 'alert',
                'message': f"Problems detected: {', '.join(analysis['problem_indicators'][:2])}",
                'priority': 'high'
            })
        
        # Call score
        score = analysis.get('call_score', 0)
        if score < 40:
            insights.append({
                'type': 'alert',
                'message': 'Low call quality score - review needed',
                'priority': 'high'
            })
        elif score > 80:
            insights.append({
                'type': 'success',
                'message': 'Excellent call quality - great service!',
                'priority': 'low'
            })
        
        return insights
    
    def _save_analysis(self, analysis):
        """Save call analysis to database"""
        if not self.db:
            return
        
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT INTO call_intelligence
                (call_uuid, call_score, success_indicators, problem_indicators,
                 upsell_opportunities, key_phrases, insights, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                analysis['call_uuid'],
                analysis['call_score'],
                ','.join(analysis.get('success_indicators', [])),
                ','.join(analysis.get('problem_indicators', [])),
                ','.join(analysis.get('upsell_opportunities', [])),
                ','.join(analysis.get('key_phrases', [])),
                str(analysis.get('insights', [])),
                datetime.now().isoformat()
            ))
            self.db.commit()
            
            logger.info(f"Call intelligence saved for {analysis['call_uuid']}")
            
        except Exception as e:
            logger.error(f"Error saving call intelligence: {str(e)}")
    
    def get_call_analysis(self, call_uuid):
        """Get analysis for specific call"""
        if not self.db:
            return None
        
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                SELECT call_score, success_indicators, problem_indicators,
                       upsell_opportunities, key_phrases, insights, created_at
                FROM call_intelligence
                WHERE call_uuid = ?
            """, (call_uuid,))
            
            result = cursor.fetchone()
            
            if result:
                return {
                    'call_score': result[0],
                    'success_indicators': result[1].split(',') if result[1] else [],
                    'problem_indicators': result[2].split(',') if result[2] else [],
                    'upsell_opportunities': result[3].split(',') if result[3] else [],
                    'key_phrases': result[4].split(',') if result[4] else [],
                    'insights': eval(result[5]) if result[5] else [],
                    'created_at': result[6]
                }
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error getting call analysis: {str(e)}")
            return None


# Global call intelligence instance
call_intelligence = CallIntelligence()
