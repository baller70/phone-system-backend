
"""
Natural Language Understanding module for processing speech input.
Identifies caller intent and extracts relevant entities.
"""

import re
from datetime import datetime, timedelta, time
from typing import Dict, Any, List, Optional
import calendar

class SportsRentalNLU:
    """
    Rule-based NLU for sports facility rental inquiries.
    Processes speech input to identify intents and extract entities.
    """
    
    def __init__(self):
        self.intent_patterns = {
            'pricing': [
                r'\b(price|cost|rate|fee|charge|how much|pricing|expensive|cheap)\b',
                r'\b(hourly|per hour|birthday party|package|membership)\b',
                r'\b(what does it cost|how much does|price for)\b'
            ],
            'availability': [
                r'\b(available|availability|free|open|check|vacant)\b',
                r'\b(tomorrow|today|this week|next week|weekend|weekday)\b',
                r'\b(morning|afternoon|evening|night|time slot)\b',
                r'\b(when can|what times|is.*available)\b'
            ],
            'booking': [
                r'\b(book|reserve|schedule|make a booking|rent|hire)\b',
                r'\b(want to book|need to reserve|like to rent|book me)\b',
                r'\b(booking|reservation|appointment)\b',
                r'\b(yes.*book|confirm.*booking|go ahead)\b'
            ],
            'general_info': [
                r'\b(hours|location|address|information|about|services)\b',
                r'\b(what do you offer|what services|facilities|amenities)\b',
                r'\b(hello|hi|help|info|tell me about)\b',
                r'\b(how does.*work|what is|explain)\b'
            ],
            'payment_issue': [
                r'\b(payment|pay|credit card|billing|charge|declined)\b',
                r'\b(problem|issue|error|trouble|failed)\b',
                r'\b(card.*declined|payment.*failed|billing.*problem)\b'
            ],
            'complex_booking': [
                r'\b(multiple days|recurring|weekly|daily|tournament|league)\b',
                r'\b(large group|corporate|team building|company event)\b',
                r'\b(special requirements|equipment|catering|setup)\b',
                r'\b(more than.*people|over.*kids|big group)\b'
            ]
        }
        
        self.service_type_patterns = {
            'basketball': [
                r'\b(basketball|hoops|court|full court|half court)\b',
                r'\b(shoot.*hoops|play.*basketball|basketball.*game)\b'
            ],
            'birthday_party': [
                r'\b(birthday|party|celebration|kids.*party)\b',
                r'\b(birthday.*party|party.*package|kids.*birthday)\b',
                r'\b(turning.*years|birthday.*celebration)\b'
            ],
            'multi_sport': [
                r'\b(multi.*sport|dodgeball|volleyball|soccer|activities)\b',
                r'\b(different.*sports|various.*activities|mixed.*sports)\b',
                r'\b(dodge.*ball|volley.*ball|multiple.*activities)\b'
            ]
        }
        
        self.time_patterns = {
            'today': r'\b(today|this.*day|right now|immediately)\b',
            'tomorrow': r'\b(tomorrow|next.*day)\b',
            'this_week': r'\b(this.*week|later.*week|end.*week)\b',
            'next_week': r'\b(next.*week|following.*week)\b',
            'weekend': r'\b(weekend|saturday|sunday|sat|sun)\b',
            'weekday': r'\b(weekday|monday|tuesday|wednesday|thursday|friday|mon|tue|wed|thu|fri)\b',
            'morning': r'\b(morning|am|early|9.*am|10.*am|11.*am)\b',
            'afternoon': r'\b(afternoon|pm|noon|12.*pm|1.*pm|2.*pm|3.*pm|4.*pm|5.*pm)\b',
            'evening': r'\b(evening|night|6.*pm|7.*pm|8.*pm|9.*pm|late)\b'
        }
        
        self.confirmation_patterns = {
            'yes': r'\b(yes|yeah|yep|sure|okay|ok|correct|right|that.*works|sounds.*good|go.*ahead|book.*it)\b',
            'no': r'\b(no|nope|not.*right|wrong|different|change|not.*that)\b'
        }
        
        # Number patterns for party size, duration, etc.
        self.number_patterns = {
            'party_size': r'\b(\d+).*(?:kids|children|people|guests|players)\b',
            'duration': r'\b(\d+).*(?:hours?|hrs?)\b',
            'specific_time': r'\b(\d{1,2})(?::(\d{2}))?\s*([ap]m?)\b'
        }

    def process_speech_input(self, speech_text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process speech input and return intent and entities.
        
        Args:
            speech_text: The transcribed speech text
            context: Current conversation context
            
        Returns:
            Dictionary with intent, entities, and confidence
        """
        if not speech_text:
            return {'intent': 'unknown', 'entities': {}, 'confidence': 0.0}
        
        speech_lower = speech_text.lower()
        context = context or {}
        
        # Detect intent
        intent, intent_confidence = self._detect_intent(speech_lower)
        
        # Extract entities
        entities = self._extract_entities(speech_lower, context)
        
        # Handle context-dependent intents
        if context.get('state') == 'booking_confirmation':
            if self._matches_pattern(speech_lower, self.confirmation_patterns['yes']):
                intent = 'booking_confirm'
            elif self._matches_pattern(speech_lower, self.confirmation_patterns['no']):
                intent = 'booking_decline'
        
        return {
            'intent': intent,
            'entities': entities,
            'confidence': intent_confidence,
            'original_text': speech_text
        }
    
    def _detect_intent(self, speech_text: str) -> tuple[str, float]:
        """Detect the primary intent from speech text."""
        intent_scores = {}
        
        for intent, patterns in self.intent_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, speech_text, re.IGNORECASE))
                score += matches
            
            if score > 0:
                intent_scores[intent] = score
        
        if not intent_scores:
            return 'unknown', 0.0
        
        # Get the intent with highest score
        best_intent = max(intent_scores, key=intent_scores.get)
        max_score = intent_scores[best_intent]
        
        # Calculate confidence (simple heuristic)
        confidence = min(max_score / 3.0, 1.0)  # Normalize to 0-1
        
        return best_intent, confidence
    
    def _extract_entities(self, speech_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract entities from speech text."""
        entities = {}
        
        # Extract service type
        service_type = self._extract_service_type(speech_text)
        if service_type:
            entities['service_type'] = service_type
        
        # Extract time information
        time_info = self._extract_time_info(speech_text)
        if time_info:
            entities.update(time_info)
        
        # Extract numbers (party size, duration, etc.)
        numbers = self._extract_numbers(speech_text)
        if numbers:
            entities.update(numbers)
        
        # Extract confirmation
        confirmation = self._extract_confirmation(speech_text)
        if confirmation:
            entities['confirmation'] = confirmation
        
        return entities
    
    def _extract_service_type(self, speech_text: str) -> Optional[str]:
        """Extract service type from speech."""
        for service_type, patterns in self.service_type_patterns.items():
            for pattern in patterns:
                if re.search(pattern, speech_text, re.IGNORECASE):
                    return service_type
        return None
    
    def _extract_time_info(self, speech_text: str) -> Dict[str, Any]:
        """Extract time-related information."""
        time_info = {}
        
        # Check for relative time references
        for time_ref, pattern in self.time_patterns.items():
            if re.search(pattern, speech_text, re.IGNORECASE):
                time_info['time_reference'] = time_ref
                break
        
        # Extract specific times (e.g., "3 PM", "10:30 AM")
        time_match = re.search(self.number_patterns['specific_time'], speech_text, re.IGNORECASE)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.group(2) else 0
            period = time_match.group(3).lower() if time_match.group(3) else ''
            
            # Convert to 24-hour format
            if 'p' in period and hour != 12:
                hour += 12
            elif 'a' in period and hour == 12:
                hour = 0
            
            time_info['specific_time'] = f"{hour:02d}:{minute:02d}"
        
        # Convert relative references to actual datetime
        if 'time_reference' in time_info:
            time_info['date_time'] = self._resolve_time_reference(
                time_info['time_reference'], 
                time_info.get('specific_time')
            )
        
        return time_info
    
    def _extract_numbers(self, speech_text: str) -> Dict[str, Any]:
        """Extract numeric information."""
        numbers = {}
        
        # Party size
        party_match = re.search(self.number_patterns['party_size'], speech_text, re.IGNORECASE)
        if party_match:
            numbers['party_size'] = int(party_match.group(1))
        
        # Duration
        duration_match = re.search(self.number_patterns['duration'], speech_text, re.IGNORECASE)
        if duration_match:
            numbers['duration'] = int(duration_match.group(1))
        
        return numbers
    
    def _extract_confirmation(self, speech_text: str) -> Optional[bool]:
        """Extract confirmation (yes/no) from speech."""
        if self._matches_pattern(speech_text, self.confirmation_patterns['yes']):
            return True
        elif self._matches_pattern(speech_text, self.confirmation_patterns['no']):
            return False
        return None
    
    def _matches_pattern(self, text: str, pattern: str) -> bool:
        """Check if text matches a regex pattern."""
        return bool(re.search(pattern, text, re.IGNORECASE))
    
    def _resolve_time_reference(self, time_ref: str, specific_time: str = None) -> str:
        """Convert relative time reference to actual datetime string."""
        now = datetime.now()
        target_date = now
        
        if time_ref == 'today':
            target_date = now
        elif time_ref == 'tomorrow':
            target_date = now + timedelta(days=1)
        elif time_ref == 'this_week':
            # Find next weekday
            days_ahead = 1 if now.weekday() < 4 else 7 - now.weekday()
            target_date = now + timedelta(days=days_ahead)
        elif time_ref == 'next_week':
            days_ahead = 7 - now.weekday()
            target_date = now + timedelta(days=days_ahead)
        elif time_ref == 'weekend':
            # Find next Saturday
            days_ahead = (5 - now.weekday()) % 7
            if days_ahead == 0 and now.weekday() == 5:  # Already Saturday
                days_ahead = 0
            elif days_ahead == 0:  # Sunday, go to next Saturday
                days_ahead = 6
            target_date = now + timedelta(days=days_ahead)
        
        # Set specific time if provided
        if specific_time:
            hour, minute = map(int, specific_time.split(':'))
            target_date = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        else:
            # Default to reasonable times based on time reference
            if time_ref in ['morning']:
                target_date = target_date.replace(hour=10, minute=0, second=0, microsecond=0)
            elif time_ref in ['afternoon']:
                target_date = target_date.replace(hour=14, minute=0, second=0, microsecond=0)
            elif time_ref in ['evening']:
                target_date = target_date.replace(hour=18, minute=0, second=0, microsecond=0)
            else:
                target_date = target_date.replace(hour=15, minute=0, second=0, microsecond=0)
        
        return target_date.strftime('%Y-%m-%d %H:%M')

# Example usage and testing
if __name__ == "__main__":
    nlu = SportsRentalNLU()
    
    # Test cases
    test_inputs = [
        "I want to book a basketball court for tomorrow afternoon",
        "How much does it cost for a birthday party?",
        "Are you available this weekend?",
        "What are your hours?",
        "I need to rent a court for 20 kids",
        "Yes, book it for me",
        "No, that doesn't work"
    ]
    
    for test_input in test_inputs:
        result = nlu.process_speech_input(test_input)
        print(f"Input: {test_input}")
        print(f"Result: {result}")
        print("-" * 50)
