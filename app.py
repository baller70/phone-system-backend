
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

@app.route('/', methods=['GET'])
def index():
    """Root endpoint for health checks."""
    return jsonify({
        'status': 'running',
        'service': 'Sports Facility Phone System',
        'version': '1.0'
    }), 200

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
        
        # Initialize session with complete structure
        call_sessions[conversation_uuid] = {
            'from_number': from_number,
            'state': 'greeting',
            'context': {},
            'start_time': datetime.now(),
            'booking_info': {
                # Facility details
                'facility_type': None,
                'date': None,
                'start_time': None,
                'duration_hours': 1,
                
                # Customer details
                'customer_name': None,
                'customer_email': None,
                'customer_phone': from_number,  # Get from caller ID
                
                # Booking status
                'availability_checked': False,
                'pricing_calculated': False,
                'price': None,
                'total_cost': None,
                'details_confirmed': False,
            },
            'conversation_state': 'greeting',  # greeting, collecting_info, confirming, processing, completed
            'clarification_attempts': 0
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

@app.route('/webhooks/speech', methods=['GET', 'POST'])
def handle_speech():
    """Process speech input from caller."""
    try:
        # Handle both GET and POST requests
        if request.method == 'POST':
            speech_data = request.get_json() or {}
        else:
            speech_data = request.args.to_dict()
        
        print(f"Speech webhook called with data: {speech_data}")
        
        conversation_uuid = speech_data.get('conversation_uuid', '')
        
        # Handle both speech results formats
        speech_text = ''
        if 'speech' in speech_data:
            speech_obj = speech_data.get('speech', {})
            if isinstance(speech_obj, dict):
                results = speech_obj.get('results', [])
                if results and len(results) > 0:
                    speech_text = results[0].get('text', '')
        
        # Also check for timeout scenario
        timed_out = speech_data.get('timed_out', False)
        
        print(f"Conversation UUID: {conversation_uuid}")
        print(f"Speech text: '{speech_text}'")
        print(f"Timed out: {timed_out}")
        
        # If timeout or no speech, provide helpful message
        if timed_out or not speech_text:
            return jsonify(create_speech_input_ncco(
                "I didn't catch that. Could you please repeat? Are you interested in pricing, availability, or making a booking?",
                'retry'
            ))
        
        # Initialize session if it doesn't exist
        if conversation_uuid not in call_sessions:
            call_sessions[conversation_uuid] = {
                'from_number': speech_data.get('from', ''),
                'state': 'greeting',
                'context': {},
                'start_time': datetime.now()
            }
        
        session = call_sessions[conversation_uuid]
        
        # Process speech with NLU
        nlu_result = nlu.process_speech_input(speech_text, session['context'])
        
        print(f"NLU result: {nlu_result}")
        
        # Update session context
        session['context'].update(nlu_result.get('entities', {}))
        
        # Generate response based on intent
        ncco = handle_intent(nlu_result, session)
        
        return jsonify(ncco)
        
    except Exception as e:
        print(f"Error processing speech: {e}")
        import traceback
        traceback.print_exc()
        return jsonify(create_error_ncco())

def get_missing_required_fields(booking_info):
    """Return list of fields that still need to be collected."""
    required_fields = {
        'facility_type': 'the type of facility you need',
        'date': 'what date you want to book',
        'start_time': 'what time you want to start',
        'duration_hours': 'how long you need the facility',
        'customer_name': 'your name',
        'customer_email': 'your email address',
    }
    
    missing = []
    for field, description in required_fields.items():
        if not booking_info.get(field) or (field == 'duration_hours' and not booking_info.get(field)):
            missing.append({'field': field, 'description': description})
    
    # Duration defaults to 1, so only flag if explicitly needed
    missing = [m for m in missing if m['field'] != 'duration_hours' or booking_info.get('duration_hours') is None]
    
    return missing

def generate_collection_prompt(missing_fields):
    """Generate natural prompt to collect missing information."""
    if not missing_fields:
        return None
    
    # Group by type
    facility_fields = [f for f in missing_fields if f['field'] in ['facility_type', 'date', 'start_time', 'duration_hours']]
    customer_fields = [f for f in missing_fields if f['field'] in ['customer_name', 'customer_email', 'customer_phone']]
    
    if facility_fields and customer_fields:
        # Collect facility info first
        if len(facility_fields) == 1:
            return f"I'll need to know {facility_fields[0]['description']}."
        elif len(facility_fields) == 2:
            return f"I'll need to know {facility_fields[0]['description']} and {facility_fields[1]['description']}."
        else:
            return f"I'll need to know {facility_fields[0]['description']}, {facility_fields[1]['description']}, and {facility_fields[2]['description']}."
    
    elif facility_fields:
        if len(facility_fields) == 1:
            return f"I'll need to know {facility_fields[0]['description']}."
        elif len(facility_fields) == 2:
            return f"I'll need to know {facility_fields[0]['description']} and {facility_fields[1]['description']}."
        else:
            return f"I'll need to know {facility_fields[0]['description']}, {facility_fields[1]['description']}, and {facility_fields[2]['description']}."
    
    elif customer_fields:
        if len(customer_fields) == 1:
            return f"I'll need {customer_fields[0]['description']} to complete the booking."
        else:
            return f"I'll need {customer_fields[0]['description']} and {customer_fields[1]['description']} to complete the booking."
    
    return None

def update_booking_info_from_entities(booking_info, entities):
    """Update booking info with extracted entities."""
    # Map entity keys to booking_info keys
    if entities.get('service_type'):
        booking_info['facility_type'] = entities['service_type']
    
    if entities.get('date_time'):
        # Parse date_time into date and start_time
        try:
            dt = datetime.strptime(entities['date_time'], '%Y-%m-%d %H:%M')
            booking_info['date'] = dt.strftime('%Y-%m-%d')
            booking_info['start_time'] = dt.strftime('%H:%M')
        except:
            pass
    
    if entities.get('duration'):
        booking_info['duration_hours'] = entities['duration']
    
    if entities.get('email'):
        booking_info['customer_email'] = entities['email']
    
    if entities.get('name'):
        booking_info['customer_name'] = entities['name']
    
    if entities.get('phone'):
        booking_info['customer_phone'] = entities['phone']
    
    return booking_info

def generate_confirmation_text(booking_info):
    """Generate confirmation text with all booking details."""
    # Format date nicely
    try:
        date_obj = datetime.strptime(booking_info['date'], '%Y-%m-%d')
        formatted_date = date_obj.strftime('%A, %B %d, %Y')
    except:
        formatted_date = booking_info['date']
    
    # Format time nicely (convert 24h to 12h)
    try:
        time_obj = datetime.strptime(booking_info['start_time'], '%H:%M')
        formatted_time = time_obj.strftime('%I:%M %p').lstrip('0')
    except:
        formatted_time = booking_info['start_time']
    
    facility_name = booking_info['facility_type'].replace('_', ' ').title()
    
    confirmation = f"""Let me confirm your booking details.

{facility_name} for {booking_info['duration_hours']} hour{'s' if booking_info['duration_hours'] > 1 else ''} on {formatted_date} at {formatted_time}.

The total cost is ${booking_info['total_cost']}.

Name: {booking_info['customer_name']}
Email: {booking_info['customer_email']}
Phone: {booking_info['customer_phone']}

Is everything correct?"""
    
    return confirmation

def handle_intent(nlu_result, session):
    """Route to appropriate handler based on detected intent."""
    intent = nlu_result.get('intent', 'unknown')
    entities = nlu_result.get('entities', {})
    current_state = session.get('state', '')
    
    print(f"Intent: {intent}, State: {current_state}, Entities: {entities}")
    
    # Handle context-aware responses
    # If we're waiting for specific info and user provides it, continue the booking flow
    if current_state == 'need_service_type' and entities.get('service_type'):
        # User provided service type, continue with booking
        return handle_booking_request(entities, session)
    elif current_state == 'need_date_time' and entities.get('date_time'):
        # User provided date/time, continue with booking
        return handle_booking_request(entities, session)
    elif current_state == 'booking_confirmation':
        # User is confirming/declining a booking
        confirmation = entities.get('confirmation')
        if confirmation is True:
            # User said yes, create the booking
            return handle_booking_request(entities, session)
        elif confirmation is False:
            # User said no
            response_text = "No problem! Would you like to try a different date or time?"
            session['context'].pop('proposed_booking', None)
            return create_speech_input_ncco(response_text, 'booking_restart')
        else:
            # Didn't understand, ask again
            if 'proposed_booking' in session['context']:
                booking = session['context']['proposed_booking']
                response_text = f"Just to confirm, would you like me to book {booking['service_type'].replace('_', ' ')} for {booking['date_time']} at ${booking['total_cost']}? Please say yes or no."
                return create_speech_input_ncco(response_text, 'booking_confirmation')
    
    # Handle primary intents
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
        # Unknown intent - check if we have useful entities anyway
        if entities.get('service_type') or entities.get('date_time'):
            # User mentioned booking details even if intent unclear
            return handle_booking_request(entities, session)
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
    """Handle booking requests with complete information collection."""
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"🎯 BOOKING REQUEST HANDLER")
    print(f"Entities: {entities}")
    print(f"Conversation State: {session.get('conversation_state')}")
    print(f"Booking Info: {session.get('booking_info', {})}")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    # Get or initialize booking_info
    booking_info = session.get('booking_info', {})
    
    # Update booking info with any new entities
    booking_info = update_booking_info_from_entities(booking_info, entities)
    session['booking_info'] = booking_info
    
    # Handle confirmation state
    if session.get('conversation_state') == 'confirming':
        confirmation = entities.get('confirmation')
        if confirmation is True:
            # User confirmed - process booking
            return process_confirmed_booking(booking_info, session)
        elif confirmation is False:
            # User declined
            response_text = "No problem! What would you like to change?"
            session['conversation_state'] = 'collecting_info'
            booking_info['details_confirmed'] = False
            return create_speech_input_ncco(response_text, 'change_details')
        else:
            # Unclear response, ask again
            confirmation_text = generate_confirmation_text(booking_info)
            return create_speech_input_ncco(confirmation_text, 'confirming', allow_barge_in=False)
    
    # Check if we have all facility information
    facility_fields_complete = all([
        booking_info.get('facility_type'),
        booking_info.get('date'),
        booking_info.get('start_time'),
        booking_info.get('duration_hours')
    ])
    
    # If facility info is complete but availability not checked, check it now
    if facility_fields_complete and not booking_info.get('availability_checked'):
        print(f"✅ Facility info complete! Checking availability...")
        
        # Reconstruct date_time
        date_time_str = f"{booking_info['date']} {booking_info['start_time']}"
        
        availability = calendar_helper.check_availability(
            date_time_str, 
            booking_info['facility_type'], 
            booking_info['duration_hours']
        )
        
        print(f"📊 Availability result: {availability}")
        
        if availability['available']:
            # Mark as checked and store pricing
            booking_info['availability_checked'] = True
            booking_info['pricing_calculated'] = True
            booking_info['price'] = availability['rate']
            booking_info['total_cost'] = availability['total_cost']
            session['booking_info'] = booking_info
            
            # Now check if we have customer info
            customer_fields_complete = all([
                booking_info.get('customer_name'),
                booking_info.get('customer_email')
            ])
            
            if customer_fields_complete:
                # Everything ready - show confirmation
                confirmation_text = generate_confirmation_text(booking_info)
                session['conversation_state'] = 'confirming'
                return create_speech_input_ncco(confirmation_text, 'confirming', allow_barge_in=False)
            else:
                # Need customer info
                missing_fields = get_missing_required_fields(booking_info)
                customer_missing = [f for f in missing_fields if f['field'] in ['customer_name', 'customer_email']]
                
                if customer_missing:
                    prompt = generate_collection_prompt(customer_missing)
                    session['conversation_state'] = 'collecting_info'
                    return create_speech_input_ncco(prompt, 'collecting_customer_info')
        else:
            # Slot not available - offer alternatives
            reason = availability.get('reason', 'not available')
            response_text = f"I'm sorry, that time slot is {reason}. "
            
            alternatives = availability.get('alternatives', [])
            if alternatives:
                response_text += f"I have availability on {alternatives[0]}. Would that work for you?"
                # Reset availability check
                booking_info['availability_checked'] = False
                session['booking_info'] = booking_info
                session['conversation_state'] = 'collecting_info'
                return create_speech_input_ncco(response_text, 'alternative_offered')
            else:
                response_text += "Would you like to try a different date or time?"
                booking_info['availability_checked'] = False
                session['booking_info'] = booking_info
                session['conversation_state'] = 'collecting_info'
                return create_speech_input_ncco(response_text, 'no_alternatives')
    
    # Missing facility information - collect it
    missing_fields = get_missing_required_fields(booking_info)
    
    if missing_fields:
        prompt = generate_collection_prompt(missing_fields)
        session['conversation_state'] = 'collecting_info'
        return create_speech_input_ncco(prompt, 'collecting_info')
    
    # Shouldn't reach here, but just in case
    response_text = "I'd be happy to help you make a booking. What type of facility would you like to book?"
    session['conversation_state'] = 'collecting_info'
    return create_speech_input_ncco(response_text, 'booking_start')

def process_confirmed_booking(booking_info, session):
    """Process a confirmed booking and send confirmation."""
    print(f"📝 PROCESSING CONFIRMED BOOKING")
    print(f"Booking Info: {booking_info}")
    
    try:
        # Reconstruct date_time for Cal.com
        date_time_str = f"{booking_info['date']} {booking_info['start_time']}"
        
        # Create booking with customer info
        booking_result = calendar_helper.create_booking(
            date_time_str,
            booking_info['facility_type'],
            booking_info['customer_phone'],
            booking_info['price'],
            booking_info['duration_hours'],
            customer_name=booking_info.get('customer_name', ''),
            customer_email=booking_info.get('customer_email', '')
        )
        
        if booking_result['success']:
            booking_id = booking_result.get('booking_id', 'N/A')
            
            # Format response
            facility_name = booking_info['facility_type'].replace('_', ' ').title()
            try:
                date_obj = datetime.strptime(booking_info['date'], '%Y-%m-%d')
                formatted_date = date_obj.strftime('%A, %B %d')
            except:
                formatted_date = booking_info['date']
            
            try:
                time_obj = datetime.strptime(booking_info['start_time'], '%H:%M')
                formatted_time = time_obj.strftime('%I:%M %p').lstrip('0')
            except:
                formatted_time = booking_info['start_time']
            
            response_text = f"""Perfect! I've confirmed your booking for {facility_name} on {formatted_date} at {formatted_time} for {booking_info['duration_hours']} hour{'s' if booking_info['duration_hours'] > 1 else ''}.

Your booking reference number is {booking_id}.

I'll send a confirmation email to {booking_info['customer_email']} with all the details.

Is there anything else I can help you with?"""
            
            # Mark session as complete
            session['conversation_state'] = 'completed'
            session['state'] = 'booking_complete'
            
            return create_speech_input_ncco(response_text, 'booking_complete', allow_barge_in=False)
        
        else:
            # Booking failed - check if it's a double booking
            error_details = booking_result.get('details', '').lower()
            is_double_booking = any(keyword in error_details for keyword in 
                ['already booked', 'not available', 'conflict', 'occupied', 'unavailable'])
            
            if is_double_booking:
                response_text = f"I apologize, but that time slot just became unavailable. Let me check for alternative times. "
                
                # Get alternatives
                try:
                    requested_datetime = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M')
                    alternatives = calendar_helper._get_alternative_times(
                        requested_datetime, 
                        booking_info['duration_hours'],
                        3,
                        booking_info['facility_type']
                    )
                    
                    if alternatives:
                        response_text += f"I have availability on {alternatives[0]}. Would that work for you?"
                        # Reset for new booking
                        booking_info['availability_checked'] = False
                        booking_info['details_confirmed'] = False
                        session['booking_info'] = booking_info
                        session['conversation_state'] = 'collecting_info'
                        return create_speech_input_ncco(response_text, 'booking_alternative')
                except Exception as e:
                    print(f"Error getting alternatives: {e}")
                
                response_text += "Would you like to try a different date or time?"
                booking_info['availability_checked'] = False
                booking_info['details_confirmed'] = False
                session['booking_info'] = booking_info
                session['conversation_state'] = 'collecting_info'
                return create_speech_input_ncco(response_text, 'booking_retry')
            else:
                # Some other error
                response_text = "I'm sorry, there was a technical issue processing your booking. Let me transfer you to our staff who can help."
                return escalation_handler.create_escalation_ncco('booking_error', {})
    
    except Exception as e:
        print(f"ERROR in process_confirmed_booking: {e}")
        import traceback
        traceback.print_exc()
        response_text = "I'm sorry, there was a technical issue. Let me connect you with our staff for assistance."
        return escalation_handler.create_escalation_ncco('booking_error', {})

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
    """Create initial greeting NCCO with sequential talk then input."""
    return [
        {
            "action": "talk",
            "text": "Hello! Thank you for calling our sports facility. I'm here to help you with court rentals, birthday parties, and availability. How can I assist you today?",
            "voiceName": "Amy",
            "bargeIn": False  # Prevent interruption to ensure full greeting plays
        },
        {
            "action": "input",
            "eventUrl": [f"{BASE_URL}/webhooks/speech"],
            "type": ["speech"],
            "speech": {
                "endOnSilence": 3,
                "language": "en-US",
                "context": ["sports", "basketball", "booking", "rental", "party"],
                "startTimeout": 10,
                "maxDuration": 15
            }
        }
    ]

def create_speech_input_ncco(text, context_state, allow_barge_in=True):
    """Create NCCO for speech input with custom text."""
    # For confirmation messages, disable barge-in to ensure full message is heard
    barge_in = allow_barge_in and context_state not in ['booking_confirmation', 'booking_complete']
    
    # Calculate approximate speech duration (assuming ~150 words per minute)
    word_count = len(text.split())
    speech_duration_seconds = (word_count / 150) * 60
    
    # Set timeout based on message length
    start_timeout = max(10, int(speech_duration_seconds) + 3)
    
    return [
        {
            "action": "talk",
            "text": text,
            "voiceName": "Amy",
            "bargeIn": barge_in
        },
        {
            "action": "input",
            "eventUrl": [f"{BASE_URL}/webhooks/speech"],
            "type": ["speech"],
            "speech": {
                "endOnSilence": 3,
                "language": "en-US",
                "context": ["sports", "basketball", "booking", "rental", "party", "yes", "no"],
                "startTimeout": start_timeout,
                "maxDuration": 15
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
            "type": ["speech"],
            "speech": {
                "endOnSilence": 3,
                "language": "en-US",
                "context": ["pricing", "availability", "booking", "services", "hours"],
                "startTimeout": 5,
                "maxDuration": 10
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
