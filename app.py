
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
from knowledge_base import KnowledgeBase
import ivr_config
import database

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
knowledge_base = KnowledgeBase()

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

# IVR Menu Configuration
IVR_MENU = {
    '1': {
        'name': 'Basketball Court Rentals',
        'description': 'Book basketball courts, check pricing and availability',
        'department': 'basketball',
        'greeting': "You've reached basketball court rentals. I can help you book a court, check pricing, or verify availability. What would you like to do?"
    },
    '2': {
        'name': 'Birthday Party Packages',
        'description': 'Party bookings, packages, and planning',
        'department': 'parties',
        'greeting': "Welcome to birthday party bookings! I can help you plan the perfect party. We offer complete packages with dedicated hosts, food options, and activities. What would you like to know?"
    },
    '3': {
        'name': 'Multi-Sport Activities',
        'description': 'Volleyball, dodgeball, and other sports',
        'department': 'multisport',
        'greeting': "You've reached multi-sport activities. We offer volleyball, dodgeball, and more. How can I assist you today?"
    },
    '4': {
        'name': 'Corporate Events & Leagues',
        'description': 'Team building, corporate events, and league information',
        'department': 'corporate',
        'greeting': "Welcome to corporate events and leagues. I can help you plan team building activities, corporate tournaments, or get you information about our leagues. What are you interested in?"
    },
    '9': {
        'name': 'Speak to AI Assistant',
        'description': 'Talk to our AI assistant for any questions',
        'department': 'ai',
        'greeting': "Great! I'm your AI assistant. I can help you with bookings, pricing, availability, or general questions. How can I help you today?"
    },
    '0': {
        'name': 'Operator',
        'description': 'Connect to a live representative',
        'department': 'operator',
        'greeting': None  # Will transfer directly
    }
}

# Session storage (in production, use Redis or database)
call_sessions = {}

# Debug storage for last DTMF input
last_dtmf_debug = {
    'timestamp': None,
    'raw_data': None,
    'dtmf_value': None,
    'matched': None
}

@app.route('/', methods=['GET'])
def index():
    """Root endpoint for health checks."""
    return jsonify({
        'status': 'running',
        'service': 'Sports Facility Phone System',
        'version': '1.0'
    }), 200

@app.route('/test/dtmf', methods=['GET', 'POST'])
def test_dtmf():
    """Test endpoint to verify DTMF handling is working."""
    print(f"\n===== TEST DTMF ENDPOINT HIT =====")
    if request.method == 'POST':
        data = request.get_json() or request.form.to_dict()
    else:
        data = request.args.to_dict()
    
    print(f"Test data received: {data}")
    
    # Return a simple response
    return jsonify([
        {
            "action": "talk",
            "text": f"Test DTMF endpoint received. You pressed {data.get('dtmf', 'unknown')}.",
            "voiceName": "Amy"
        }
    ])

@app.route('/debug/last-dtmf', methods=['GET'])
def debug_last_dtmf():
    """View the last DTMF input received for debugging."""
    return jsonify({
        'last_dtmf_input': last_dtmf_debug,
        'instructions': 'Make a test call, press a button, then refresh this page to see what was received.'
    })

@app.route('/test/database', methods=['GET'])
def test_database():
    """Test endpoint to verify database connection."""
    import traceback
    
    try:
        # Use the same DATABASE_URL that database.py uses
        db_url = database.DATABASE_URL
        env_var_set = bool(os.getenv('DATABASE_URL'))
        
        if not db_url:
            return jsonify({
                'status': 'error',
                'message': 'DATABASE_URL is None',
                'env_var_set': env_var_set
            }), 500
        
        # Show partial connection string for debugging (hide password)
        db_info = db_url.split('@')[1] if '@' in db_url else 'invalid format'
        
        # Try to actually connect and get detailed error
        try:
            import psycopg2
            conn = psycopg2.connect(db_url)
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM \"CallLog\"")
                count = cur.fetchone()[0]
            conn.close()
            
            return jsonify({
                'status': 'success',
                'message': 'Database connection working!',
                'database_host': db_info,
                'call_count': count,
                'env_var_set': env_var_set,
                'using_default': not env_var_set
            })
        except Exception as db_error:
            return jsonify({
                'status': 'error',
                'message': str(db_error),
                'error_type': type(db_error).__name__,
                'database_host': db_info,
                'traceback': traceback.format_exc(),
                'env_var_set': env_var_set,
                'using_default': not env_var_set
            }), 500
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'type': type(e).__name__,
            'traceback': traceback.format_exc()
        }), 500

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
    """Handle Vonage Voice API events and log calls to dashboard."""
    try:
        # Handle both GET and POST requests from Vonage
        if request.method == 'POST':
            event_data = request.get_json() or {}
        else:
            event_data = request.args.to_dict()
        
        print(f"Received event: {event_data}")
        
        # Extract event details
        event_status = event_data.get('status', '')
        conversation_uuid = event_data.get('conversation_uuid', '')
        from_number = event_data.get('from', '')
        duration = event_data.get('duration', 0)
        
        # Track call start time
        if event_status == 'started':
            if conversation_uuid not in call_sessions:
                call_sessions[conversation_uuid] = {
                    'from_number': from_number,
                    'start_time': datetime.now(),
                    'intent': 'unknown',
                    'outcome': 'in_progress',
                    'context': {}
                }
            else:
                call_sessions[conversation_uuid]['start_time'] = datetime.now()
        
        # Log call completion to dashboard
        elif event_status in ['completed', 'answered', 'unanswered', 'failed', 'rejected', 'timeout']:
            # Get session data
            session = call_sessions.get(conversation_uuid, {})
            
            # Calculate duration if available
            if duration == 0 and 'start_time' in session:
                duration = int((datetime.now() - session['start_time']).total_seconds())
            
            # Determine intent and outcome from session
            intent = session.get('intent', session.get('intent_type', session.get('department', 'unknown')))
            outcome = event_status
            
            # If call was answered and lasted more than a few seconds, mark as completed
            if event_status == 'completed' and duration > 5:
                outcome = 'completed'
            elif event_status in ['unanswered', 'failed', 'rejected', 'timeout']:
                outcome = 'failed'
            
            # Get transcription/notes from session
            notes = None
            if 'conversation_history' in session:
                notes = "\n".join([
                    f"{'User' if msg.get('role') == 'user' else 'AI'}: {msg.get('content', '')}"
                    for msg in session['conversation_history'][-5:]  # Last 5 messages
                ])
            
            # Estimate call cost (Vonage charges approximately $0.007 per minute)
            cost = (duration / 60) * 0.007 if duration > 0 else 0.0
            
            # Log to dashboard database
            try:
                database.log_call_to_dashboard(
                    caller_id=from_number or 'unknown',
                    caller_name=session.get('caller_name', 'Unknown'),
                    duration=int(duration) if duration else 0,
                    intent=intent,
                    outcome=outcome,
                    recording_url=event_data.get('recording_url'),
                    transcription=None,  # Not available yet
                    notes=notes,
                    cost=round(cost, 4)
                )
                print(f"✓ Call logged to dashboard: {from_number} - {intent} - {outcome}")
            except Exception as log_error:
                print(f"Warning: Failed to log call to dashboard: {log_error}")
            
            # Clean up session after logging
            if conversation_uuid in call_sessions:
                del call_sessions[conversation_uuid]
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        print(f"Error handling event: {e}")
        return jsonify({'status': 'error'})

@app.route('/webhooks/dtmf', methods=['GET', 'POST'])
def handle_dtmf():
    """Handle DTMF (keypad) input from IVR menu - SIMPLIFIED FOR TESTING."""
    
    try:
        # LOG EVERYTHING - this will help us see if Vonage is even calling this webhook
        print(f"\n" + "="*60)
        print(f"DTMF WEBHOOK HIT!")
        print(f"="*60)
        print(f"Method: {request.method}")
        print(f"URL: {request.url}")
        print(f"Path: {request.path}")
        
        # Get request body
        if request.method == 'POST':
            print(f"Content-Type: {request.content_type}")
            raw_data = request.get_data(as_text=True)
            print(f"Raw body: {raw_data}")
            
            if request.is_json:
                dtmf_data = request.get_json() or {}
                print(f"Parsed JSON: {dtmf_data}")
            else:
                dtmf_data = request.form.to_dict() or {}
                print(f"Parsed Form: {dtmf_data}")
        else:
            dtmf_data = request.args.to_dict()
            print(f"Query params: {dtmf_data}")
        
        print(f"Headers: {dict(request.headers)}")
        
        conversation_uuid = dtmf_data.get('conversation_uuid', '')
        
        # CRITICAL FIX: Vonage sends DTMF as nested object {"digits": "1", "timed_out": false}
        # We need to extract the "digits" field, not treat the whole object as a string
        dtmf_object = dtmf_data.get('dtmf', {})
        
        if isinstance(dtmf_object, dict):
            # New format: {"digits": "1", "timed_out": false}
            dtmf = dtmf_object.get('digits', '')
            timed_out = dtmf_object.get('timed_out', False)
            print(f"Parsed DTMF object - digits: '{dtmf}', timed_out: {timed_out}")
        else:
            # Old format: just a string "1"
            dtmf = str(dtmf_object).strip()
            timed_out = dtmf_data.get('timed_out', False)
            print(f"Parsed DTMF string - value: '{dtmf}', timed_out: {timed_out}")
        
        print(f"Parsed - UUID: {conversation_uuid}, DTMF digits: '{dtmf}' (type: {type(dtmf)}), Timed out: {timed_out}")
        
        # Initialize session if it doesn't exist
        if conversation_uuid not in call_sessions:
            call_sessions[conversation_uuid] = {
                'from_number': dtmf_data.get('from', ''),
                'state': 'menu',
                'context': {},
                'start_time': datetime.now()
            }
        
        session = call_sessions[conversation_uuid]
        
        # Handle timeout - replay menu
        if timed_out or not dtmf:
            print("DTMF timed out or empty, replaying menu")
            return jsonify(create_ivr_menu_ncco(replay=True))
        
        # Ensure DTMF is a clean string
        dtmf = str(dtmf).strip()
        print(f"Normalized DTMF: '{dtmf}'")
        
        # Store in debug storage for easy viewing
        last_dtmf_debug['timestamp'] = datetime.now().isoformat()
        last_dtmf_debug['raw_data'] = dtmf_data
        last_dtmf_debug['dtmf_value'] = dtmf
        last_dtmf_debug['dtmf_type'] = str(type(dtmf))
        
        # Fetch menu options from dashboard (with fallback to static menu)
        dashboard_settings = ivr_config.fetch_ivr_settings()
        
        if dashboard_settings and 'menuOptions' in dashboard_settings:
            # Use dashboard settings
            MENU = {}
            for option in dashboard_settings['menuOptions']:
                MENU[option['keyPress']] = {
                    'name': option['optionName'],
                    'greeting': option['departmentGreeting'],
                    'intent': option['intentType'],
                    'action_type': option.get('actionType', 'ai_conversation'),
                    'transfer_number': option.get('transferNumber')
                }
            print(f"✓ Using menu options from dashboard: {list(MENU.keys())}")
        else:
            # Fallback to static menu if dashboard fetch fails
            print("⚠ Dashboard fetch failed, using fallback static menu")
            MENU = {
                '1': {
                    'name': 'Basketball',
                    'greeting': 'Great! I can help you book a basketball court. What date and time would you like?',
                    'intent': 'basketball_rental',
                    'action_type': 'ai_conversation'
                },
                '2': {
                    'name': 'Parties',
                    'greeting': 'Perfect! Let me help you plan a birthday party. How many guests are you expecting?',
                    'intent': 'party_booking',
                    'action_type': 'ai_conversation'
                },
                '9': {
                    'name': 'AI Assistant',
                    'greeting': "Hi! I'm your AI assistant. How can I help you today?",
                    'intent': 'general_inquiry',
                    'action_type': 'ai_conversation'
                },
                '0': {
                    'name': 'Operator',
                    'greeting': None,  # Will transfer
                    'intent': 'transfer',
                    'action_type': 'transfer'
                }
            }
        
        print(f"Checking DTMF '{dtmf}' against menu: {list(MENU.keys())}")
        
        if dtmf in MENU:
            option = MENU[dtmf]
            print(f"✓ MATCHED! Option: {option['name']}")
            
            # Update debug storage
            last_dtmf_debug['matched'] = True
            last_dtmf_debug['matched_option'] = option['name']
            
            # Store in session
            session['selected_option'] = option['name']
            session['intent_type'] = option['intent']
            session['intent'] = option['intent']  # For logging consistency
            
            # Handle operator transfer
            if dtmf == '0':
                print("Transferring to operator...")
                return jsonify(create_transfer_ncco())
            
            # Set context
            session['context']['service_type'] = option['intent']
            
            # Return department greeting and speech input
            department_greeting = option['greeting']
            print(f"Returning greeting: {department_greeting}")
            
            ncco = [
                {
                    "action": "talk",
                    "text": department_greeting,
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
                        "context": ["sports", "basketball", "booking", "rental", "party", "price", "availability"],
                        "startTimeout": 10,
                        "maxDuration": 60  # Increased to allow longer customer responses during booking
                    }
                }
            ]
            
            print(f"NCCO to return: {json.dumps(ncco, indent=2)}")
            print(f"===============================\n")
            return jsonify(ncco)
        else:
            # Invalid input - replay menu
            print(f"✗ NO MATCH for DTMF '{dtmf}'. Valid options: {list(MENU.keys())}")
            
            # Update debug storage
            last_dtmf_debug['matched'] = False
            last_dtmf_debug['matched_option'] = None
            last_dtmf_debug['valid_options'] = list(MENU.keys())
            
            print(f"===============================\n")
            return jsonify(create_ivr_menu_ncco(invalid=True))
        
    except Exception as e:
        print(f"ERROR processing DTMF: {e}")
        import traceback
        traceback.print_exc()
        print(f"===============================\n")
        return jsonify(create_error_ncco())

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
        
        # Store the speech text for knowledge base queries
        session['last_speech'] = speech_text
        
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
    """Handle booking requests."""
    # Get service type from entities or context
    service_type = entities.get('service_type') or session['context'].get('service_type')
    date_time = entities.get('date_time') or session['context'].get('date_time')
    
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"🎯 BOOKING REQUEST HANDLER")
    print(f"Service: {service_type}, DateTime: {date_time}")
    print(f"Session State: {session.get('state')}")
    print(f"Session Context: {session['context']}")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    # If we have a proposed booking in context, confirm and create it
    if 'proposed_booking' in session['context']:
        booking_details = session['context']['proposed_booking']
        
        # Create the booking
        booking_result = calendar_helper.create_booking(
            booking_details['date_time'],
            booking_details['service_type'],
            session['from_number'],
            booking_details['rate'],
            booking_details.get('duration', 1)
        )
        
        if booking_result['success']:
            # Track successful booking
            session['outcome'] = 'booking_success'
            session['intent'] = 'booking'
            response_text = f"Perfect! I've reserved {booking_details['service_type'].replace('_', ' ')} for {booking_details['date_time']} at ${booking_details['rate']} per hour. Your booking confirmation is {booking_result['booking_id']}. You'll receive a confirmation text shortly. Is there anything else I can help you with?"
            return create_speech_input_ncco(response_text, 'booking_complete')
        else:
            # Track failed booking
            session['outcome'] = 'booking_failed'
            session['intent'] = 'booking'
            response_text = "I'm sorry, there was an issue creating your booking. Let me transfer you to our staff for assistance."
            return escalation_handler.create_escalation_ncco('booking_error', entities)
    
    # Check if we have both service type and date/time
    if service_type and date_time:
        # We have all the info we need! Check availability
        duration = entities.get('duration', 1)
        
        print(f"✅ Have both service_type and date_time! Checking availability...")
        print(f"   Service: {service_type}, DateTime: {date_time}, Duration: {duration}h")
        
        availability = calendar_helper.check_availability(date_time, service_type, duration)
        
        print(f"📊 Availability result: {availability}")
        
        if availability['available']:
            # Store the proposed booking
            session['context']['proposed_booking'] = {
                'service_type': service_type,
                'date_time': date_time,
                'rate': availability['rate'],
                'duration': duration,
                'total_cost': availability['total_cost']
            }
            
            response_text = f"Great! I can book a {service_type.replace('_', ' ')} court for {date_time} at ${availability['rate']} per hour for {duration} hour(s). That's a total of ${availability['total_cost']}. Shall I go ahead and reserve that for you?"
            session['state'] = 'booking_confirmation'
            return create_speech_input_ncco(response_text, 'booking_confirmation')
        else:
            reason = availability.get('reason', 'not available')
            response_text = f"I'm sorry, that time slot is {reason}. "
            
            alternatives = availability.get('alternatives', [])
            if alternatives:
                response_text += f"I have availability on {alternatives[0]}. Would that work for you?"
            else:
                response_text = "Let me transfer you to our staff to find an available time."
                return escalation_handler.create_escalation_ncco('no_availability', entities)
            
            return create_speech_input_ncco(response_text, 'booking_alternative')
    
    # Missing information - ask for what we need
    if not service_type:
        response_text = "I'd be happy to help you make a booking. What type of activity are you planning - basketball, multi-sport, or a birthday party?"
        session['state'] = 'need_service_type'
        return create_speech_input_ncco(response_text, 'need_service_type')
    elif not date_time:
        response_text = f"Perfect! For {service_type.replace('_', ' ')}, what date and time work best for you?"
        # Store service type in context
        session['context']['service_type'] = service_type
        session['state'] = 'need_date_time'
        return create_speech_input_ncco(response_text, 'need_date_time')
    else:
        # Shouldn't reach here, but just in case
        response_text = "I'd be happy to help you make a booking. What type of activity and what date/time would you like?"
        session['state'] = 'booking_details_needed'
        return create_speech_input_ncco(response_text, 'booking_details_needed')

def handle_general_info(entities, session):
    """Handle general information requests using knowledge base."""
    
    # Get the last thing the user said from session
    user_question = session.get('last_speech', '')
    
    # If we don't have the question, use entities to construct one
    if not user_question:
        info_type = entities.get('info_type', 'general')
        if info_type == 'hours':
            user_question = "What are your hours?"
        elif info_type == 'services':
            user_question = "What services do you offer?"
        else:
            user_question = "Tell me about your facility"
    
    # Query knowledge base
    kb_response = knowledge_base.query_knowledge(user_question, session.get('context', {}))
    
    response_text = kb_response['answer']
    
    # Add source attribution if available
    if kb_response.get('source'):
        print(f"[KB] Response from {kb_response['source']}")
    
    # Add follow-up prompt
    response_text += " Is there anything else you'd like to know?"
    
    return create_speech_input_ncco(response_text, 'general_followup')

def create_greeting_ncco():
    """Create initial greeting NCCO with IVR menu."""
    return create_ivr_menu_ncco()

def create_ivr_menu_ncco(replay=False, invalid=False):
    """Create IVR menu NCCO with DTMF input options - pulls from dashboard."""
    
    # Fetch IVR settings from dashboard
    dashboard_settings = ivr_config.fetch_ivr_settings()
    
    if dashboard_settings:
        # Use dashboard settings
        base_greeting = dashboard_settings.get('greetingText', 'Welcome to Premier Sports.')
        invalid_msg = dashboard_settings.get('invalidOptionMessage', "Sorry, invalid option.")
        replay_msg = dashboard_settings.get('replayMessage', "I didn't catch that.")
        menu_options = dashboard_settings.get('menuOptions', [])
        
        # Build menu text from options
        menu_parts = []
        for option in menu_options:
            menu_parts.append(option.get('optionText', ''))
        menu_text = ' '.join(menu_parts)
        
        print(f"✓ Using IVR settings from dashboard")
    else:
        # Fallback to static settings
        print(f"⚠ Using fallback IVR settings")
        base_greeting = "Welcome to Premier Sports."
        invalid_msg = "Sorry, invalid option."
        replay_msg = "I didn't catch that."
        menu_text = "Press 1 for basketball, press 2 for parties, press 9 for the AI assistant, or press 0 for an operator."
    
    if invalid:
        greeting_text = invalid_msg + " "
    elif replay:
        greeting_text = replay_msg + " "
    else:
        greeting_text = base_greeting + " "
    
    full_text = greeting_text + menu_text
    
    print(f"\n===== IVR MENU NCCO CREATED =====")
    print(f"Full text: {full_text}")
    print(f"DTMF webhook URL: {BASE_URL}/webhooks/dtmf")
    print(f"==================================\n")
    
    # Return NCCO with talk and input actions
    return [
        {
            "action": "talk",
            "text": full_text,
            "voiceName": "Amy",
            "bargeIn": False  # User must wait for greeting to complete
        },
        {
            "action": "input",
            "eventUrl": [f"{BASE_URL}/webhooks/dtmf"],
            "type": ["dtmf"],
            "dtmf": {
                "timeOut": 10,
                "maxDigits": 1,
                "submitOnHash": False
            }
        }
    ]

def create_department_greeting_ncco(menu_option):
    """Create department-specific greeting after menu selection."""
    greeting_text = menu_option['greeting']
    
    return [
        {
            "action": "talk",
            "text": greeting_text,
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
                "context": ["sports", "basketball", "booking", "rental", "party", "price", "availability"],
                "startTimeout": 10,
                "maxDuration": 60  # Increased to allow longer customer responses during booking
            }
        }
    ]

def create_transfer_ncco():
    """Create NCCO to transfer to a live operator."""
    staff_phone = os.getenv('STAFF_PHONE_NUMBER', '15551234567')
    
    return [
        {
            "action": "talk",
            "text": "Please hold while I connect you to one of our representatives.",
            "voiceName": "Amy",
            "bargeIn": False
        },
        {
            "action": "connect",
            "timeout": 30,
            "from": os.getenv('VONAGE_NUMBER', 'unknown'),
            "endpoint": [
                {
                    "type": "phone",
                    "number": staff_phone
                }
            ],
            "eventUrl": [f"{BASE_URL}/webhooks/events"]
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
            "type": ["speech"],
            "speech": {
                "endOnSilence": 3,
                "language": "en-US",
                "context": ["sports", "basketball", "booking", "rental", "party", "yes", "no"],
                "startTimeout": 10,  # Increased to allow full message to complete
                "maxDuration": 60  # Increased to allow longer customer conversations during booking
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
                "startTimeout": 10,
                "maxDuration": 60  # Increased to allow longer customer responses
            }
        }
    ]

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'vonage_client': vonage_client is not None,
        'version': '1.1-ivr-integrated'
    })

@app.route('/debug/ivr-settings', methods=['GET'])
def debug_ivr_settings():
    """Debug endpoint to see what IVR settings the backend is using."""
    try:
        # Fetch current IVR settings
        settings = ivr_config.get_ivr_settings()
        
        # Build the greeting text that would be announced
        greeting_text = settings.get('greetingText', 'No greeting')
        
        # Build menu text
        menu_options = settings.get('menuOptions', [])
        menu_text_parts = []
        for option in menu_options:
            if option.get('isActive', True):
                menu_text_parts.append(option.get('optionText', ''))
        
        full_menu_text = ' '.join(menu_text_parts)
        
        return jsonify({
            'status': 'success',
            'dashboard_url': ivr_config.DASHBOARD_URL,
            'api_endpoint': f"{ivr_config.DASHBOARD_URL}/api/public/ivr-settings",
            'greeting_text': greeting_text,
            'full_announcement': greeting_text + ' ' + full_menu_text,
            'menu_options': [
                {
                    'key': opt.get('keyPress'),
                    'name': opt.get('optionName'),
                    'announcement': opt.get('optionText'),
                    'department_greeting': opt.get('departmentGreeting'),
                    'active': opt.get('isActive', True)
                }
                for opt in menu_options
            ],
            'total_options': len(menu_options),
            'active_options': len([o for o in menu_options if o.get('isActive', True)]),
            'cache_status': 'cached' if ivr_config._ivr_cache['settings'] else 'not_cached'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
