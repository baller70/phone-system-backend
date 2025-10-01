
"""
Natural Language Understanding module for processing speech input.
Identifies caller intent and extracts relevant entities.
Phase 3: Enhanced with better date/time parsing, fuzzy matching, and modification/cancellation support
"""

import re
from datetime import datetime, timedelta, time
from typing import Dict, Any, List, Optional
import calendar
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta
from difflib import get_close_matches

class SportsRentalNLU:
    """
    Rule-based NLU for sports facility rental inquiries.
    Processes speech input to identify intents and extract entities.
    """
    
    def __init__(self):
        self.intent_patterns = {
            'pricing': [
                r'\b(prices?|costs?|rates?|fees?|charges?|how much|pricing|expensive|cheap)\b',
                r'\b(hourly|per hour|birthday party|package|membership)\b',
                r'\b(what does it cost|how much does|price for|what are .* prices)\b'
            ],
            'availability': [
                r'\b(available|availability|free|open|check|vacant)\b',
                r'\b(tomorrow|today|this week|next week|weekend|weekday)\b',
                r'\b(morning|afternoon|evening|night|time slot)\b',
                r'\b(when can|what times|is.*available)\b'
            ],
            'booking': [
                r'\b(book|reserve|schedule|make a booking|rent|hire|need)\b',
                r'\b(want to book|need to reserve|like to rent|book me|I need|need a)\b',
                r'\b(booking|reservation|appointment)\b',
                r'\b(yes.*book|confirm.*booking|go ahead)\b'
            ],
            'modify_booking': [
                r'\b(change|modify|reschedule|move|update|alter)\b',
                r'\b(different time|another time|new time|switch)\b',
                r'\b(change.*booking|modify.*reservation|reschedule.*appointment)\b'
            ],
            'cancel_booking': [
                r'\b(cancel|cancellation|cancelling)\b',
                r'\b(don\'t need|won\'t make it|not coming|can\'t make)\b',
                r'\b(cancel.*booking|cancel.*reservation|cancel.*appointment)\b'
            ],
            'lookup_booking': [
                r'\b(my booking|my reservation|booking reference|confirmation number)\b',
                r'\b(check.*booking|find.*booking|look.*up)\b',
                r'\b(what.*time|when.*booking)\b'
            ],
            'escalate_to_human': [
                r'\b(speak to|talk to|connect me|transfer me)\b',
                r'\b(human|person|representative|agent|manager|someone)\b',
                r'\b(real person|actual person|not.*robot)\b'
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
        
        # Email pattern
        self.email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        
        # Name patterns
        self.name_patterns = [
            r"(?:my name is|i'm|this is|i am|name's)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
            r"(?:my name is|i'm|this is|i am|name's)\s+([A-Z][a-z]+)",  # Just first name
        ]
        
        # Phone patterns
        self.phone_patterns = [
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # 123-456-7890 or 1234567890
            r'\(\d{3}\)\s*\d{3}[-.]?\d{4}',     # (123) 456-7890
        ]

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
        
        # Extract service type (now with fuzzy matching)
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
        
        # Extract customer information
        email = self._extract_email(speech_text)
        if email:
            entities['email'] = email
        
        name = self._extract_name(speech_text)
        if name:
            entities['name'] = name
        
        phone = self._extract_phone(speech_text)
        if phone:
            entities['phone'] = phone
        
        # Extract booking reference (Phase 3)
        booking_ref = self.extract_booking_reference(speech_text)
        if booking_ref:
            entities['booking_reference'] = booking_ref
        
        return entities
    
    def _extract_service_type(self, speech_text: str) -> Optional[str]:
        """
        Extract service type from speech with fuzzy matching.
        Phase 3: Enhanced to handle typos and variations.
        """
        # First try pattern matching
        for service_type, patterns in self.service_type_patterns.items():
            for pattern in patterns:
                if re.search(pattern, speech_text, re.IGNORECASE):
                    return service_type
        
        # Then try fuzzy matching (Phase 3 enhancement)
        fuzzy_match = self.match_facility_fuzzy(speech_text)
        if fuzzy_match:
            return fuzzy_match
        
        return None
    
    def _extract_time_info(self, speech_text: str) -> Dict[str, Any]:
        """Extract time-related information."""
        time_info = {}
        
        # Check for relative time references
        for time_ref, pattern in self.time_patterns.items():
            if re.search(pattern, speech_text, re.IGNORECASE):
                time_info['time_reference'] = time_ref
                break
        
        # Extract specific dates (e.g., "October 2nd", "Oct 2", "October the 2nd", "10/2")
        # Pattern handles optional "the" and ordinal suffixes (1st, 2nd, 3rd, etc.)
        date_patterns = [
            r'(january|jan)\s+(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?',
            r'(february|feb)\s+(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?',
            r'(march|mar)\s+(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?',
            r'(april|apr)\s+(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?',
            r'(may)\s+(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?',
            r'(june|jun)\s+(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?',
            r'(july|jul)\s+(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?',
            r'(august|aug)\s+(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?',
            r'(september|sept|sep)\s+(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?',
            r'(october|oct)\s+(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?',
            r'(november|nov)\s+(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?',
            r'(december|dec)\s+(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?'
        ]
        
        month_map = {
            'january': 1, 'jan': 1,
            'february': 2, 'feb': 2,
            'march': 3, 'mar': 3,
            'april': 4, 'apr': 4,
            'may': 5,
            'june': 6, 'jun': 6,
            'july': 7, 'jul': 7,
            'august': 8, 'aug': 8,
            'september': 9, 'sept': 9, 'sep': 9,
            'october': 10, 'oct': 10,
            'november': 11, 'nov': 11,
            'december': 12, 'dec': 12
        }
        
        specific_date = None
        for pattern in date_patterns:
            date_match = re.search(pattern, speech_text, re.IGNORECASE)
            if date_match:
                month_name = date_match.group(1).lower()
                day = int(date_match.group(2))
                month = month_map.get(month_name)
                
                if month and 1 <= day <= 31:
                    # Determine the year (current year or next year)
                    now = datetime.now()
                    year = now.year
                    
                    # If the date is in the past this year, assume next year
                    try:
                        specific_date = datetime(year, month, day)
                        if specific_date < now:
                            specific_date = datetime(year + 1, month, day)
                    except ValueError:
                        # Invalid date
                        pass
                    
                    if specific_date:
                        time_info['specific_date'] = specific_date
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
        elif not time_info.get('specific_time'):
            # Phase 3: Try conversational time parsing
            conv_time = self.parse_conversational_time(speech_text)
            if conv_time:
                time_info['specific_time'] = conv_time
        
        # Convert relative references to actual datetime
        if 'specific_date' in time_info:
            # Use the specific date if provided
            target_date = time_info['specific_date']
            if 'specific_time' in time_info:
                hour, minute = map(int, time_info['specific_time'].split(':'))
                target_date = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            else:
                # Default to 3 PM if no time specified
                target_date = target_date.replace(hour=15, minute=0, second=0, microsecond=0)
            time_info['date_time'] = target_date.strftime('%Y-%m-%d %H:%M')
        elif 'time_reference' in time_info:
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
    
    def _extract_email(self, speech_text: str) -> Optional[str]:
        """Extract email address from speech text."""
        match = re.search(self.email_pattern, speech_text, re.IGNORECASE)
        if match:
            return match.group(0).lower()
        return None
    
    def _extract_name(self, speech_text: str) -> Optional[str]:
        """Extract customer name from speech text."""
        for pattern in self.name_patterns:
            match = re.search(pattern, speech_text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Capitalize properly (handle "john smith" -> "John Smith")
                return ' '.join(word.capitalize() for word in name.split())
        return None
    
    def _extract_phone(self, speech_text: str) -> Optional[str]:
        """Extract phone number from speech text."""
        for pattern in self.phone_patterns:
            match = re.search(pattern, speech_text)
            if match:
                # Normalize to just digits
                phone = re.sub(r'[^\d]', '', match.group(0))
                # Return in standard format
                if len(phone) == 10:
                    return f"({phone[:3]}) {phone[3:6]}-{phone[6:]}"
                return phone
        return None
    
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
    
    def parse_relative_date(self, text: str) -> Optional[str]:
        """
        Parse relative dates like 'next Tuesday', 'in 2 weeks', etc.
        Phase 3 enhancement for better date understanding.
        """
        text_lower = text.lower()
        today = datetime.now().date()
        
        # Today/Tomorrow/Yesterday
        if 'today' in text_lower:
            return today.strftime('%Y-%m-%d')
        elif 'tomorrow' in text_lower:
            return (today + timedelta(days=1)).strftime('%Y-%m-%d')
        elif 'yesterday' in text_lower:
            return (today - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Day of week patterns
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        
        for i, day in enumerate(days):
            if day in text_lower:
                # Calculate next occurrence of this day
                current_weekday = today.weekday()
                target_weekday = i
                
                if 'next' in text_lower:
                    # Next week's occurrence
                    days_ahead = (target_weekday - current_weekday + 7) % 7
                    if days_ahead == 0:
                        days_ahead = 7
                    result_date = today + timedelta(days=days_ahead + 7)
                else:
                    # This week's occurrence (or next week if it's passed)
                    days_ahead = (target_weekday - current_weekday) % 7
                    if days_ahead == 0 and datetime.now().hour > 18:  # After 6pm
                        days_ahead = 7
                    result_date = today + timedelta(days=days_ahead)
                
                return result_date.strftime('%Y-%m-%d')
        
        # "in X days/weeks/months"
        if 'in' in text_lower:
            # Extract number
            numbers = re.findall(r'\d+', text)
            if numbers:
                num = int(numbers[0])
                
                if 'day' in text_lower:
                    return (today + timedelta(days=num)).strftime('%Y-%m-%d')
                elif 'week' in text_lower:
                    return (today + timedelta(weeks=num)).strftime('%Y-%m-%d')
                elif 'month' in text_lower:
                    result_date = today + relativedelta(months=num)
                    return result_date.strftime('%Y-%m-%d')
        
        # Try dateutil parser as fallback
        try:
            parsed = date_parser.parse(text, fuzzy=True)
            return parsed.date().strftime('%Y-%m-%d')
        except:
            pass
        
        return None
    
    def parse_conversational_time(self, text: str) -> Optional[str]:
        """
        Parse conversational time expressions like 'morning', 'afternoon'.
        Phase 3 enhancement for better time understanding.
        """
        text_lower = text.lower()
        
        # Time of day keywords
        time_mappings = {
            'early morning': '07:00',
            'morning': '09:00',
            'mid morning': '10:00',
            'late morning': '11:00',
            'noon': '12:00',
            'midday': '12:00',
            'early afternoon': '13:00',
            'afternoon': '14:00',
            'mid afternoon': '15:00',
            'late afternoon': '16:00',
            'early evening': '17:00',
            'evening': '18:00',
            'late evening': '20:00',
            'night': '19:00',
        }
        
        for phrase, time_value in time_mappings.items():
            if phrase in text_lower:
                return time_value
        
        return None
    
    def extract_booking_reference(self, text: str) -> Optional[str]:
        """
        Extract booking reference number from text.
        Phase 3 enhancement for modification/cancellation support.
        """
        # Look for patterns like: #12345, booking 12345, reference 12345
        patterns = [
            r'#([A-Z0-9]{4,})',
            r'booking\s+(?:number\s+)?([A-Z0-9]{4,})',
            r'reference\s+(?:number\s+)?([A-Z0-9]{4,})',
            r'confirmation\s+(?:number\s+)?([A-Z0-9]{4,})',
            r'\b([A-Z0-9]{6,8})\b',  # Any 6-8 character alphanumeric
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        return None
    
    def get_facility_variants(self) -> Dict[str, List[str]]:
        """Return dictionary of facility types and their variants for fuzzy matching."""
        return {
            'basketball': ['basketball', 'basketball court', 'b-ball', 'hoops', 'court', 'bball'],
            'tennis': ['tennis', 'tennis court'],
            'soccer': ['soccer', 'soccer field', 'football', 'football field', 'pitch'],
            'volleyball': ['volleyball', 'volleyball court', 'v-ball', 'vball'],
            'badminton': ['badminton', 'badminton court'],
            'pool': ['pool', 'swimming pool', 'swim'],
            'gym': ['gym', 'fitness', 'weight room'],
            'birthday_party': ['birthday', 'party', 'birthday party', 'celebration'],
            'multi_sport': ['multi sport', 'multisport', 'mixed sports', 'activities'],
        }
    
    def match_facility_fuzzy(self, text: str) -> Optional[str]:
        """
        Match facility type with fuzzy matching to handle typos.
        Phase 3 enhancement for more robust facility extraction.
        """
        text_lower = text.lower()
        variants = self.get_facility_variants()
        
        # First, try exact matching
        for facility, variant_list in variants.items():
            for variant in variant_list:
                if variant in text_lower:
                    return facility
        
        # Then try fuzzy matching
        all_variants = []
        for facility, variant_list in variants.items():
            all_variants.extend([(v, facility) for v in variant_list])
        
        # Extract potential facility words from text
        words = text_lower.split()
        for word in words:
            if len(word) > 3:  # Only check words longer than 3 chars
                matches = get_close_matches(word, [v[0] for v in all_variants], n=1, cutoff=0.75)
                if matches:
                    # Find which facility this belongs to
                    for variant, facility in all_variants:
                        if variant == matches[0]:
                            return facility
        
        return None

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
