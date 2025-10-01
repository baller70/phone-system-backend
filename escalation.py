
"""
Escalation handler for complex bookings and payment issues.
Routes calls to human staff when automated system cannot handle the request.
"""

import os
from datetime import datetime
from typing import Dict, Any, List, Optional

class EscalationHandler:
    """
    Handles escalation scenarios that require human intervention.
    """
    
    def __init__(self):
        self.staff_phone = os.getenv('STAFF_PHONE_NUMBER', '+15551234567')
        self.escalation_reasons = {
            'payment_issue': 'Payment processing problem',
            'complex_booking': 'Complex booking requirements',
            'booking_error': 'System error during booking',
            'large_group': 'Large group or corporate event',
            'special_requirements': 'Special equipment or setup needs',
            'complaint': 'Customer complaint or issue',
            'technical_error': 'Technical system error',
            'outside_hours': 'Request outside business hours'
        }
    
    def should_escalate(self, intent: str, entities: Dict[str, Any], 
                       context: Dict[str, Any] = None) -> bool:
        """
        Determine if a request should be escalated to human staff.
        
        Args:
            intent: The detected intent from NLU
            entities: Extracted entities
            context: Current conversation context
            
        Returns:
            Boolean indicating if escalation is needed
        """
        # Always escalate payment issues
        if intent == 'payment_issue':
            return True
        
        # Escalate complex bookings
        if intent == 'complex_booking':
            return True
        
        # Escalate large groups (>30 people for parties, >20 for regular bookings)
        party_size = entities.get('party_size', 0)
        if party_size > 30:
            return True
        
        # Escalate if multiple days or recurring bookings
        if any(keyword in str(entities).lower() for keyword in 
               ['multiple days', 'recurring', 'weekly', 'tournament', 'league']):
            return True
        
        # Escalate if special requirements mentioned
        if any(keyword in str(entities).lower() for keyword in 
               ['catering', 'special setup', 'equipment rental', 'decorations']):
            return True
        
        # Escalate if booking system errors
        if context and context.get('booking_errors', 0) > 2:
            return True
        
        return False
    
    def create_escalation_ncco(self, reason: str, entities: Dict[str, Any] = None,
                              custom_message: str = None) -> List[Dict[str, Any]]:
        """
        Create NCCO for escalating to human staff.
        
        Args:
            reason: Reason for escalation
            entities: Extracted entities for context
            custom_message: Custom message to play before transfer
            
        Returns:
            NCCO list for call transfer
        """
        # Log escalation for analytics
        self._log_escalation(reason, entities)
        
        # Create appropriate message based on reason
        if custom_message:
            message = custom_message
        else:
            message = self._get_escalation_message(reason, entities)
        
        # Create NCCO with message and transfer
        ncco = [
            {
                "action": "talk",
                "text": message,
                "voiceName": "Amy"
            }
        ]
        
        # Add hold music if available
        hold_music_url = os.getenv('HOLD_MUSIC_URL')
        if hold_music_url:
            ncco.append({
                "action": "stream",
                "streamUrl": [hold_music_url],
                "loop": 0
            })
        
        # Connect to staff
        ncco.append({
            "action": "connect",
            "endpoint": [
                {
                    "type": "phone",
                    "number": self.staff_phone
                }
            ],
            "from": os.getenv('VONAGE_PHONE_NUMBER', '15551234567'),
            "timeOut": 30,
            "machineDetection": "continue"
        })
        
        return ncco
    
    def _get_escalation_message(self, reason: str, entities: Dict[str, Any] = None) -> str:
        """Generate appropriate escalation message based on reason."""
        base_message = "I understand you need assistance with "
        
        if reason == 'payment_issue':
            message = base_message + "a payment issue. Let me connect you with our staff who can help resolve this right away."
        
        elif reason == 'complex_booking':
            details = []
            if entities:
                if entities.get('party_size', 0) > 20:
                    details.append(f"a large group of {entities['party_size']} people")
                if 'recurring' in str(entities).lower():
                    details.append("recurring bookings")
                if 'tournament' in str(entities).lower():
                    details.append("tournament arrangements")
            
            if details:
                detail_text = " and ".join(details)
                message = base_message + f"{detail_text}. Our staff can provide personalized assistance for your specific needs."
            else:
                message = base_message + "a complex booking. Our staff will be able to help you with all the details."
        
        elif reason == 'booking_error':
            message = "I apologize, but I'm experiencing a technical issue with the booking system. Let me connect you with our staff who can complete your reservation manually."
        
        elif reason == 'large_group':
            party_size = entities.get('party_size', 'large group') if entities else 'large group'
            message = base_message + f"arrangements for your {party_size}. Our staff can provide specialized service for large groups and corporate events."
        
        elif reason == 'special_requirements':
            message = base_message + "special requirements for your event. Our staff can coordinate custom setups, equipment, and services."
        
        elif reason == 'complaint':
            message = "I want to make sure we address your concerns properly. Let me connect you with our staff who can assist you personally."
        
        elif reason == 'technical_error':
            message = "I'm experiencing a technical issue. Let me connect you with our staff who can help you right away."
        
        else:
            message = base_message + "your request. Our staff will be happy to assist you personally."
        
        message += " Please hold while I connect you."
        
        return message
    
    def _log_escalation(self, reason: str, entities: Dict[str, Any] = None):
        """Log escalation for analytics and improvement."""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'reason': reason,
                'entities': entities or {},
                'description': self.escalation_reasons.get(reason, 'Unknown reason')
            }
            
            # In production, this would go to a proper logging system
            print(f"ESCALATION LOG: {log_entry}")
            
            # Could also write to file or send to analytics service
            log_file = os.getenv('ESCALATION_LOG_FILE', '/tmp/escalations.log')
            with open(log_file, 'a') as f:
                f.write(f"{log_entry}\n")
                
        except Exception as e:
            print(f"Error logging escalation: {e}")
    
    def create_callback_ncco(self, customer_phone: str, reason: str) -> List[Dict[str, Any]]:
        """
        Create NCCO for offering callback instead of immediate transfer.
        
        Args:
            customer_phone: Customer's phone number
            reason: Reason for callback
            
        Returns:
            NCCO for callback offer
        """
        message = f"""I understand you need assistance with {self.escalation_reasons.get(reason, 'your request')}. 
        Our staff are currently busy, but I can have someone call you back within the next hour. 
        Would you like me to schedule a callback to this number, or would you prefer to hold for the next available representative?
        Say 'callback' for a callback, or 'hold' to wait on the line."""
        
        return [
            {
                "action": "talk",
                "text": message,
                "voiceName": "Amy",
                "bargeIn": True
            },
            {
                "action": "input",
                "eventUrl": [f"{os.getenv('BASE_URL', 'http://localhost:5000')}/webhooks/callback_choice"],
                "timeOut": 10,
                "maxDigits": 0,
                "speech": {
                    "endOnSilence": 2,
                    "language": "en-US",
                    "context": ["callback", "hold", "wait"]
                }
            }
        ]
    
    def handle_callback_choice(self, choice: str, customer_phone: str, reason: str) -> List[Dict[str, Any]]:
        """Handle customer's choice for callback vs hold."""
        if 'callback' in choice.lower():
            # Schedule callback (in production, this would integrate with staff scheduling system)
            self._schedule_callback(customer_phone, reason)
            
            return [
                {
                    "action": "talk",
                    "text": "Perfect! I've scheduled a callback for you within the next hour. Our staff will call you back at this number to assist with your request. Thank you for calling, and have a great day!",
                    "voiceName": "Amy"
                }
            ]
        else:
            # Proceed with hold and transfer
            return [
                {
                    "action": "talk",
                    "text": "I'll connect you with our staff now. Please hold while I transfer your call.",
                    "voiceName": "Amy"
                },
                {
                    "action": "connect",
                    "endpoint": [
                        {
                            "type": "phone",
                            "number": self.staff_phone
                        }
                    ],
                    "timeOut": 60
                }
            ]
    
    def _schedule_callback(self, customer_phone: str, reason: str):
        """Schedule a callback (placeholder for integration with staff system)."""
        callback_info = {
            'phone': customer_phone,
            'reason': reason,
            'scheduled_time': datetime.now().isoformat(),
            'priority': self._get_callback_priority(reason)
        }
        
        # In production, this would integrate with staff scheduling/CRM system
        print(f"CALLBACK SCHEDULED: {callback_info}")
        
        # Could send to staff notification system, CRM, etc.
        callback_file = os.getenv('CALLBACK_LOG_FILE', '/tmp/callbacks.log')
        with open(callback_file, 'a') as f:
            f.write(f"{callback_info}\n")
    
    def _get_callback_priority(self, reason: str) -> str:
        """Determine callback priority based on reason."""
        high_priority_reasons = ['payment_issue', 'complaint', 'booking_error']
        
        if reason in high_priority_reasons:
            return 'high'
        elif reason in ['complex_booking', 'large_group']:
            return 'medium'
        else:
            return 'normal'
    
    def create_after_hours_escalation_ncco(self) -> List[Dict[str, Any]]:
        """Create NCCO for after-hours escalation attempts."""
        return [
            {
                "action": "talk",
                "text": """I understand you need to speak with our staff, but we're currently closed. 
                Our business hours are 9 AM to 9 PM daily. For urgent matters, you can visit our website 
                or send us an email, and we'll respond first thing in the morning. 
                Otherwise, please call back during business hours. Thank you!""",
                "voiceName": "Amy"
            }
        ]
    
    def get_escalation_stats(self) -> Dict[str, Any]:
        """Get escalation statistics for analytics."""
        # In production, this would query actual logs/database
        return {
            'total_escalations': 0,
            'escalation_reasons': {},
            'average_resolution_time': 0,
            'callback_success_rate': 0
        }

# Example usage and testing
if __name__ == "__main__":
    escalation_handler = EscalationHandler()
    
    # Test escalation decision
    test_entities = {'party_size': 35, 'special_requirements': 'catering'}
    should_escalate = escalation_handler.should_escalate('complex_booking', test_entities)
    print(f"Should escalate: {should_escalate}")
    
    # Test escalation NCCO
    if should_escalate:
        ncco = escalation_handler.create_escalation_ncco('complex_booking', test_entities)
        print(f"Escalation NCCO: {ncco}")
