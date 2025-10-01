
"""
Test suite for the automated phone answering system.
Tests core functionality including NLU, pricing, calendar integration, and call flows.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, call_sessions
from nlu import SportsRentalNLU
from pricing import PricingEngine
from calendar_helper import CalendarHelper
from escalation import EscalationHandler

class TestNLU:
    """Test Natural Language Understanding functionality."""
    
    def setup_method(self):
        self.nlu = SportsRentalNLU()
    
    def test_pricing_intent_detection(self):
        """Test pricing intent detection."""
        test_cases = [
            "How much does it cost to rent a basketball court?",
            "What are your prices for birthday parties?",
            "Can you tell me the hourly rates?",
            "What's the pricing for membership?"
        ]
        
        for text in test_cases:
            result = self.nlu.process_speech_input(text)
            assert result['intent'] == 'pricing'
            assert result['confidence'] > 0.0
    
    def test_availability_intent_detection(self):
        """Test availability intent detection."""
        test_cases = [
            "Are you available tomorrow afternoon?",
            "What times are free this weekend?",
            "Do you have any openings next week?",
            "Check availability for Friday evening"
        ]
        
        for text in test_cases:
            result = self.nlu.process_speech_input(text)
            assert result['intent'] == 'availability'
    
    def test_booking_intent_detection(self):
        """Test booking intent detection."""
        test_cases = [
            "I want to book a basketball court",
            "Can I reserve a time slot?",
            "I'd like to make a booking",
            "Yes, book it for me"
        ]
        
        for text in test_cases:
            result = self.nlu.process_speech_input(text)
            assert result['intent'] == 'booking'
    
    def test_service_type_extraction(self):
        """Test service type entity extraction."""
        test_cases = [
            ("I need a basketball court", "basketball"),
            ("We want to book a birthday party", "birthday_party"),
            ("Looking for multi-sport activities", "multi_sport")
        ]
        
        for text, expected_service in test_cases:
            result = self.nlu.process_speech_input(text)
            assert result['entities'].get('service_type') == expected_service
    
    def test_time_extraction(self):
        """Test time-related entity extraction."""
        test_cases = [
            "tomorrow afternoon",
            "next Friday at 3 PM",
            "this weekend morning",
            "today at 6:30 PM"
        ]
        
        for text in test_cases:
            result = self.nlu.process_speech_input(text)
            entities = result['entities']
            # Should extract some time-related information
            assert any(key in entities for key in ['time_reference', 'specific_time', 'date_time'])
    
    def test_party_size_extraction(self):
        """Test party size extraction."""
        test_cases = [
            ("We have 15 kids", 15),
            ("Birthday party for 20 children", 20),
            ("Group of 8 people", 8)
        ]
        
        for text, expected_size in test_cases:
            result = self.nlu.process_speech_input(text)
            assert result['entities'].get('party_size') == expected_size

class TestPricingEngine:
    """Test pricing calculations and information."""
    
    def setup_method(self):
        self.pricing_engine = PricingEngine()
    
    def test_basketball_pricing_info(self):
        """Test basketball pricing information retrieval."""
        result = self.pricing_engine.get_pricing_info('basketball', 'hourly')
        
        assert result['service_type'] == 'basketball'
        assert 'rates' in result
        assert 'description' in result
        assert '$' in result['description']  # Should contain pricing info
    
    def test_birthday_party_pricing_info(self):
        """Test birthday party pricing information."""
        result = self.pricing_engine.get_pricing_info('birthday_party')
        
        assert result['service_type'] == 'birthday_party'
        assert 'packages' in result
        assert 'starter' in result['packages']
        assert 'champion' in result['packages']
        assert 'all_star' in result['packages']
    
    def test_hourly_rate_calculation(self):
        """Test hourly rate calculation for different times."""
        # Test peak time (weekend)
        weekend_datetime = datetime(2025, 10, 11, 15, 0)  # Saturday 3 PM
        peak_rate = self.pricing_engine.calculate_hourly_rate(weekend_datetime, 'basketball')
        
        # Test off-peak time (weekday morning)
        weekday_datetime = datetime(2025, 10, 13, 10, 0)  # Monday 10 AM
        off_peak_rate = self.pricing_engine.calculate_hourly_rate(weekday_datetime, 'basketball')
        
        # Peak rate should be higher than off-peak
        assert peak_rate >= off_peak_rate
        assert peak_rate > 0
        assert off_peak_rate > 0
    
    def test_off_season_pricing(self):
        """Test off-season pricing (May-August)."""
        # Summer date
        summer_datetime = datetime(2025, 7, 15, 15, 0)  # July 15, 3 PM
        summer_rate = self.pricing_engine.calculate_hourly_rate(summer_datetime, 'basketball')
        
        # Should be flat rate of $55 during off-season
        assert summer_rate == 55.0
    
    def test_party_cost_calculation(self):
        """Test birthday party cost calculation."""
        # Test starter package with additional children
        result = self.pricing_engine.calculate_party_cost('starter', 15, ['pizza_package'])
        
        assert result['package_type'] == 'starter'
        assert result['num_children'] == 15
        assert result['additional_children'] == 3  # 15 - 12 included
        assert result['total_cost'] > result['base_cost']
        assert 'breakdown' in result
    
    def test_membership_savings_calculation(self):
        """Test membership savings calculation."""
        result = self.pricing_engine.get_membership_savings(12, 'basketball')
        
        assert result['monthly_hours'] == 12
        assert 'membership_analysis' in result
        assert 'basic' in result['membership_analysis']
        assert 'premium' in result['membership_analysis']
        assert 'best_option' in result

class TestCalendarHelper:
    """Test Google Calendar integration."""
    
    def setup_method(self):
        self.calendar_helper = CalendarHelper()
    
    @patch('calendar_helper.CalendarHelper._initialize_service')
    def test_availability_check_business_hours(self, mock_init):
        """Test availability check respects business hours."""
        # Mock the service to avoid actual Google API calls
        mock_service = Mock()
        self.calendar_helper.service = mock_service
        
        # Test time outside business hours (before 9 AM)
        early_time = "2025-10-15 08:00"
        result = self.calendar_helper.check_availability(early_time)
        
        assert not result['available']
        assert 'business hours' in result['reason'].lower()
    
    @patch('calendar_helper.CalendarHelper._initialize_service')
    def test_availability_check_with_conflicts(self, mock_init):
        """Test availability check with existing events."""
        # Mock the service
        mock_service = Mock()
        mock_events = Mock()
        mock_events.list.return_value.execute.return_value = {
            'items': [{'summary': 'Existing booking'}]  # Simulate conflict
        }
        mock_service.events.return_value = mock_events
        self.calendar_helper.service = mock_service
        
        test_time = "2025-10-15 15:00"
        result = self.calendar_helper.check_availability(test_time)
        
        assert not result['available']
        assert 'already booked' in result['reason'].lower()
    
    @patch('calendar_helper.CalendarHelper._initialize_service')
    def test_booking_creation(self, mock_init):
        """Test booking creation."""
        # Mock the service
        mock_service = Mock()
        mock_events = Mock()
        mock_events.insert.return_value.execute.return_value = {
            'id': 'test_event_id_123',
            'htmlLink': 'https://calendar.google.com/event/test'
        }
        mock_service.events.return_value = mock_events
        self.calendar_helper.service = mock_service
        
        result = self.calendar_helper.create_booking(
            "2025-10-15 15:00", "basketball", "+15551234567", 65.0
        )
        
        assert result['success']
        assert 'booking_id' in result
        assert 'event_id' in result
        assert result['total_cost'] == 65.0

class TestEscalationHandler:
    """Test escalation logic and handling."""
    
    def setup_method(self):
        self.escalation_handler = EscalationHandler()
    
    def test_payment_issue_escalation(self):
        """Test that payment issues are always escalated."""
        should_escalate = self.escalation_handler.should_escalate(
            'payment_issue', {}, {}
        )
        assert should_escalate
    
    def test_large_group_escalation(self):
        """Test escalation for large groups."""
        entities = {'party_size': 35}
        should_escalate = self.escalation_handler.should_escalate(
            'booking', entities, {}
        )
        assert should_escalate
    
    def test_complex_booking_escalation(self):
        """Test escalation for complex bookings."""
        should_escalate = self.escalation_handler.should_escalate(
            'complex_booking', {}, {}
        )
        assert should_escalate
    
    def test_escalation_ncco_creation(self):
        """Test NCCO creation for escalation."""
        ncco = self.escalation_handler.create_escalation_ncco('payment_issue')
        
        assert isinstance(ncco, list)
        assert len(ncco) >= 2  # Should have talk and connect actions
        assert ncco[0]['action'] == 'talk'
        assert 'payment issue' in ncco[0]['text'].lower()
        
        # Should have connect action
        connect_action = next((action for action in ncco if action['action'] == 'connect'), None)
        assert connect_action is not None
        assert 'endpoint' in connect_action

class TestAppEndpoints:
    """Test Flask application endpoints."""
    
    def setup_method(self):
        self.app = app.test_client()
        self.app.testing = True
    
    def test_health_check(self):
        """Test health check endpoint."""
        response = self.app.get('/health')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
    
    def test_answer_webhook_business_hours(self):
        """Test answer webhook during business hours."""
        # Mock current time to be within business hours
        with patch('app.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 10, 15, 15, 0)  # 3 PM
            mock_datetime.now().hour = 15
            
            response = self.app.post('/webhooks/answer', 
                                   json={'conversation_uuid': 'test-123', 'from': '+15551234567'})
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert isinstance(data, list)  # Should return NCCO array
            assert data[0]['action'] == 'talk'
    
    def test_answer_webhook_after_hours(self):
        """Test answer webhook after business hours."""
        with patch('app.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 10, 15, 22, 0)  # 10 PM
            mock_datetime.now().hour = 22
            
            response = self.app.post('/webhooks/answer',
                                   json={'conversation_uuid': 'test-123', 'from': '+15551234567'})
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'closed' in data[0]['text'].lower()
    
    @patch('app.nlu')
    def test_speech_webhook(self, mock_nlu):
        """Test speech processing webhook."""
        # Setup mock NLU response
        mock_nlu.process_speech_input.return_value = {
            'intent': 'pricing',
            'entities': {'service_type': 'basketball'},
            'confidence': 0.8
        }
        
        # Setup session
        conversation_uuid = 'test-speech-123'
        call_sessions[conversation_uuid] = {
            'from_number': '+15551234567',
            'state': 'greeting',
            'context': {},
            'start_time': datetime.now()
        }
        
        speech_data = {
            'conversation_uuid': conversation_uuid,
            'speech': {
                'results': [{'text': 'How much does basketball cost?'}]
            }
        }
        
        response = self.app.post('/webhooks/speech', json=speech_data)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert data[0]['action'] == 'talk'

class TestIntegrationFlows:
    """Test complete conversation flows."""
    
    def setup_method(self):
        self.app = app.test_client()
        self.app.testing = True
        self.nlu = SportsRentalNLU()
        self.pricing_engine = PricingEngine()
    
    def test_pricing_inquiry_flow(self):
        """Test complete pricing inquiry flow."""
        # Step 1: Process pricing question
        speech_input = "How much does it cost to rent a basketball court?"
        nlu_result = self.nlu.process_speech_input(speech_input)
        
        assert nlu_result['intent'] == 'pricing'
        assert nlu_result['entities'].get('service_type') == 'basketball'
        
        # Step 2: Get pricing information
        pricing_info = self.pricing_engine.get_pricing_info('basketball', 'hourly')
        
        assert pricing_info['service_type'] == 'basketball'
        assert 'description' in pricing_info
        assert '$' in pricing_info['description']
    
    @patch('calendar_helper.CalendarHelper.check_availability')
    def test_availability_and_booking_flow(self, mock_availability):
        """Test availability check followed by booking."""
        # Mock availability response
        mock_availability.return_value = {
            'available': True,
            'rate': 65.0,
            'service_type': 'basketball',
            'duration': 1,
            'total_cost': 65.0
        }
        
        # Step 1: Check availability
        speech_input = "Are you available tomorrow at 3 PM for basketball?"
        nlu_result = self.nlu.process_speech_input(speech_input)
        
        assert nlu_result['intent'] == 'availability'
        assert nlu_result['entities'].get('service_type') == 'basketball'
        
        # Step 2: Confirm booking
        booking_speech = "Yes, book it for me"
        booking_result = self.nlu.process_speech_input(booking_speech)
        
        assert booking_result['intent'] == 'booking'
    
    def test_escalation_flow(self):
        """Test escalation flow for complex requests."""
        escalation_handler = EscalationHandler()
        
        # Complex booking scenario
        entities = {
            'party_size': 40,
            'special_requirements': 'catering and decorations'
        }
        
        should_escalate = escalation_handler.should_escalate('complex_booking', entities)
        assert should_escalate
        
        ncco = escalation_handler.create_escalation_ncco('complex_booking', entities)
        assert ncco[0]['action'] == 'talk'
        assert 'staff' in ncco[0]['text'].lower()

# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
