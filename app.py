
"""
Main Flask application for automated phone answering system.
Handles Vonage Voice API webhooks and orchestrates call flow.
"""

import os
import json
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from vonage import Vonage, Auth
from nlu import SportsRentalNLU
from calcom_calendar_helper import CalcomCalendarHelper
from pricing import PricingEngine
from escalation import EscalationHandler

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Get base URL for webhooks (use environment variable or default to request)
BASE_URL = os.getenv('BASE_URL', 'https://phone-system-backend.onrender.com')

# Initialize components
nlu = SportsRentalNLU()
calendar_helper = CalcomCalendarHelper()
pricing_engine = PricingEngine()
escalation_handler = EscalationHandler()

# Initialize Vonage client
try:
    vonage_client = Vonage(
        Auth(
            api_key=os.getenv('VONAGE_API_KEY'),
            api_secret=os.getenv('VONAGE_API_SECRET')
        )
    )
    print("✓ Vonage client initialized successfully")
except Exception as e:
    print(f"Warning: Vonage client initialization failed: {e}")
    vonage_client = None

# Business hours configuration
BUSINESS_HOURS = {
    'start': 9,  # 9 AM
    'end': 21,   # 9 PM
    'timezone': 'America/New_York'
}

# Session storage (in production, use Redis or database)
call_sessions = {}

@app.route('/webhooks/answer', methods=['GET', 'POST'])
def answer_call():
    """
    Handle incoming calls with Vonage Voice API.
    Returns NCCO (Nexmo Call Control Object) to control call flow.
    """
    try:
        # Handle both GET and POST requests from Vonage
        if request.method == 'POST':
            call_data = request.get_json() or {}
        else:
            call_data = request.args.to_dict()
        
        conversation_uuid = call_data.get('conversation_uuid', '')
        from_number = call_data.get('from', '')
        
        # Initialize session
        call_sessions[conversation_uuid] = {
            'from_number': from_number,
            'state': 'greeting',
            'context': {},
            'start_time': datetime.now()
        }
        
        # Check business hours
        current_hour = datetime.now().hour
        if current_hour < BUSINESS_HOURS['start'] or current_hour >= BUSINESS_HOURS['end']:
            return jsonify(create_after_hours_ncco())
        
        # Create greeting NCCO
        ncco = create_greeting_ncco()
        return jsonify(ncco)
        
    except Exception as e:
        print(f"Error in answer_call: {e}")
        return jsonify(create_error_ncco())

@app.route('/webhooks/events', methods=['GET', 'POST'])
def handle_events():
    """Handle Vonage Voice API events."""
    try:
        # Handle both GET and POST requests from Vonage
        if request.method == 'POST':
            event_data = request.get_json() or {}
        else:
            event_data = request.args.to_dict()
        
        print(f"Received event: {event_data}")
        return jsonify({'status': 'ok'})
    except Exception as e:
        print(f"Error handling event: {e}")
        return jsonify({'status': 'error'})

@app.route('/webhooks/fallback', methods=['GET', 'POST'])
def handle_fallback():
    """Handle fallback when main webhook fails."""
    try:
        # Handle both GET and POST requests from Vonage
        if request.method == 'POST':
            fallback_data = request.get_json() or {}
        else:
            fallback_data = request.args.to_dict()
        
        print(f"Fallback triggered: {fallback_data}")
        
        # Return a simple NCCO to handle the call gracefully
        return jsonify([
            {
                "action": "talk",
                "text": "I'm sorry, we're experiencing technical difficulties. Please call back in a few moments or visit our website to book online. Thank you!",
                "voiceName": "Amy"
            }
        ])
    except Exception as e:
        print(f"Error in fallback: {e}")
        return jsonify(create_error_ncco())

@app.route('/webhooks/speech', methods=['POST'])
def handle_speech():
    """Process speech input from caller."""
    try:
        speech_data = request.get_json()
        conversation_uuid = speech_data.get('conversation_uuid', '')
        speech_text = speech_data.get('speech', {}).get('results', [{}])[0].get('text', '')
        
        if not speech_text or conversation_uuid not in call_sessions:
            return jsonify(create_error_ncco())
        
        session = call_sessions[conversation_uuid]
        
        # Process speech with NLU
        nlu_result = nlu.process_speech_input(speech_text, session['context'])
        
        # Update session context
        session['context'].update(nlu_result.get('entities', {}))
        
        # Generate response based on intent
        ncco = handle_intent(nlu_result, session)
        
        return jsonify(ncco)
        
    except Exception as e:
        print(f"Error processing speech: {e}")
        return jsonify(create_error_ncco())

def handle_intent(nlu_result, session):
    """Route to appropriate handler based on detected intent."""
    intent = nlu_result.get('intent', 'unknown')
    entities = nlu_result.get('entities', {})
    
    if intent == 'pricing':
        return handle_pricing_inquiry(entities, session)
    elif intent == 'availability':
        return handle_availability_inquiry(entities, session)
    elif intent == 'booking':
        return handle_booking_request(entities, session)
    elif intent == 'general_info':
        return handle_general_info(entities, session)
    elif intent == 'payment_issue' or intent == 'complex_booking':
        return escalation_handler.create_escalation_ncco(intent, entities)
    else:
        return create_clarification_ncco()

def handle_pricing_inquiry(entities, session):
    """Handle pricing-related questions."""
    service_type = entities.get('service_type', 'basketball')
    time_period = entities.get('time_period', 'hourly')
    
    pricing_info = pricing_engine.get_pricing_info(service_type, time_period)
    
    response_text = f"For {service_type} rentals, our pricing is as follows: {pricing_info['description']}. Would you like to check availability or make a booking?"
    
    return create_speech_input_ncco(response_text, 'pricing_followup')

def handle_availability_inquiry(entities, session):
    """Handle availability checks."""
    date_time = entities.get('date_time')
    service_type = entities.get('service_type', 'basketball')
    
    if not date_time:
        response_text = "I'd be happy to check availability for you. What date and time are you looking for?"
        return create_speech_input_ncco(response_text, 'availability_date_needed')
    
    # Check calendar availability
    availability = calendar_helper.check_availability(date_time, service_type)
    
    if availability['available']:
        response_text = f"Great news! We have availability on {date_time} for {service_type}. The rate would be ${availability['rate']} per hour. Would you like to make a booking?"
        session['context']['proposed_booking'] = {
            'date_time': date_time,
            'service_type': service_type,
            'rate': availability['rate']
        }
        return create_speech_input_ncco(response_text, 'booking_confirmation')
    else:
        alternative_times = availability.get('alternatives', [])
        if alternative_times:
            alt_text = ", ".join(alternative_times[:3])
            response_text = f"I'm sorry, that time slot isn't available. However, I have these alternatives: {alt_text}. Would any of these work for you?"
        else:
            response_text = "I'm sorry, that time slot isn't available. Would you like me to check a different date or time?"
        
        return create_speech_input_ncco(response_text, 'availability_alternatives')

def handle_booking_request(entities, session):
    """Handle booking requests."""
    if 'proposed_booking' in session['context']:
        # Confirm the previously discussed booking
        booking_details = session['context']['proposed_booking']
        
        # Create the booking
        booking_result = calendar_helper.create_booking(
            booking_details['date_time'],
            booking_details['service_type'],
            session['from_number'],
            booking_details['rate']
        )
        
        if booking_result['success']:
            response_text = f"Perfect! I've reserved {booking_details['service_type']} for {booking_details['date_time']} at ${booking_details['rate']} per hour. Your booking confirmation is {booking_result['booking_id']}. You'll receive a confirmation text shortly. Is there anything else I can help you with?"
            return create_speech_input_ncco(response_text, 'booking_complete')
        else:
            response_text = "I'm sorry, there was an issue creating your booking. Let me transfer you to our staff for assistance."
            return escalation_handler.create_escalation_ncco('booking_error', entities)
    else:
        # Need more information for booking
        response_text = "I'd be happy to help you make a booking. What type of activity are you planning - basketball, multi-sport, or a birthday party? And what date and time work best for you?"
        return create_speech_input_ncco(response_text, 'booking_details_needed')

def handle_general_info(entities, session):
    """Handle general information requests."""
    info_type = entities.get('info_type', 'general')
    
    if info_type == 'hours':
        response_text = "We're open daily from 9 AM to 9 PM. Our facility offers basketball courts, multi-sport activities, and birthday party packages."
    elif info_type == 'services':
        response_text = "We offer basketball court rentals, multi-sport activities like dodgeball and volleyball, and complete birthday party packages with dedicated hosts."
    else:
        response_text = "Welcome to our sports facility! We offer basketball court rentals, multi-sport activities, and birthday parties from 9 AM to 9 PM daily. How can I help you today?"
    
    response_text += " Would you like to hear about pricing or check availability?"
    return create_speech_input_ncco(response_text, 'general_followup')

def create_greeting_ncco():
    """Create initial greeting NCCO."""
    return [
        {
            "action": "talk",
            "text": "Hello! Thank you for calling our sports facility. I'm here to help you with court rentals, birthday parties, and availability. How can I assist you today?",
            "voiceName": "Amy",
            "bargeIn": True
        },
        {
            "action": "input",
            "eventUrl": [f"{BASE_URL}/webhooks/speech"],
            "timeOut": 10,
            "maxDigits": 0,
            "speech": {
                "endOnSilence": 2,
                "language": "en-US",
                "context": ["sports", "basketball", "booking", "rental", "party"]
            }
        }
    ]

def create_speech_input_ncco(text, context_state):
    """Create NCCO for speech input with custom text."""
    return [
        {
            "action": "talk",
            "text": text,
            "voiceName": "Amy",
            "bargeIn": True
        },
        {
            "action": "input",
            "eventUrl": [f"{BASE_URL}/webhooks/speech"],
            "timeOut": 10,
            "maxDigits": 0,
            "speech": {
                "endOnSilence": 2,
                "language": "en-US",
                "context": ["sports", "basketball", "booking", "rental", "party", "yes", "no"]
            }
        }
    ]

def create_after_hours_ncco():
    """Create NCCO for after-hours calls."""
    return [
        {
            "action": "talk",
            "text": "Thank you for calling our sports facility. We're currently closed. Our hours are 9 AM to 9 PM daily. Please call back during business hours, or visit our website to book online. Have a great day!",
            "voiceName": "Amy"
        }
    ]

def create_error_ncco():
    """Create NCCO for error handling."""
    return [
        {
            "action": "talk",
            "text": "I'm sorry, I'm having trouble processing your request. Let me transfer you to our staff for assistance.",
            "voiceName": "Amy"
        },
        {
            "action": "connect",
            "endpoint": [
                {
                    "type": "phone",
                    "number": os.getenv('STAFF_PHONE_NUMBER', '15551234567')
                }
            ]
        }
    ]

def create_clarification_ncco():
    """Create NCCO when we need clarification."""
    return [
        {
            "action": "talk",
            "text": "I'm not sure I understood that. Are you looking for pricing information, checking availability, or wanting to make a booking? You can also ask about our services or hours.",
            "voiceName": "Amy",
            "bargeIn": True
        },
        {
            "action": "input",
            "eventUrl": [f"{BASE_URL}/webhooks/speech"],
            "timeOut": 10,
            "maxDigits": 0,
            "speech": {
                "endOnSilence": 2,
                "language": "en-US",
                "context": ["pricing", "availability", "booking", "services", "hours"]
            }
        }
    ]

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'vonage_client': vonage_client is not None
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
