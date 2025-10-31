"""
Main Flask application for automated phone answering system.
Migrated from Vonage to Telnyx Voice API.
Handles Telnyx Call Control webhooks and orchestrates call flow.
"""

import os
import json
import uuid
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from telnyx_voice_client import TelnyxVoiceClient, extract_telnyx_event_data
from nlu import SportsRentalNLU
from calcom_calendar_helper import CalcomCalendarHelper
from pricing import PricingEngine
from escalation import EscalationHandler
from knowledge_base import KnowledgeBase
import ivr_config
import database
import requests

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Get base URL for webhooks
BASE_URL = os.getenv('BASE_URL', 'https://phone-system-backend.onrender.com')

# Initialize components
nlu = SportsRentalNLU()
calendar_helper = CalcomCalendarHelper()
pricing_engine = PricingEngine()
escalation_handler = EscalationHandler()
knowledge_base = KnowledgeBase()

# Initialize Telnyx client
try:
    telnyx_client = TelnyxVoiceClient()
    print("✓ Telnyx client initialized successfully")
except Exception as e:
    print(f"❌ Telnyx client initialization failed: {e}")
    telnyx_client = None

# Business hours configuration
BUSINESS_HOURS = {
    'start': 9,  # 9 AM
    'end': 21,   # 9 PM
    'timezone': 'America/New_York'
}

# Session storage - maps call_control_id to session data
call_sessions = {}

# Debug storage for troubleshooting
last_event_debug = {}


# ==================== HELPER FUNCTIONS ====================

def get_or_create_session(call_control_id: str, event_data: dict) -> dict:
    """Get existing session or create new one"""
    if call_control_id not in call_sessions:
        call_sessions[call_control_id] = {
            'call_control_id': call_control_id,
            'call_session_id': event_data.get('call_session_id', ''),
            'from_number': event_data.get('from', ''),
            'to_number': event_data.get('to', ''),
            'state': 'new',
            'context': {},
            'start_time': datetime.now(),
            'conversation_transcript': [],
            'menu_selection': None,
            'intent': None
        }
    return call_sessions[call_control_id]


def is_business_hours() -> bool:
    """Check if current time is within business hours"""
    from pytz import timezone
    tz = timezone(BUSINESS_HOURS['timezone'])
    now = datetime.now(tz)
    
    # Check if weekend
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    
    # Check time
    if now.hour < BUSINESS_HOURS['start'] or now.hour >= BUSINESS_HOURS['end']:
        return False
    
    return True


def log_call_to_database(session: dict, hangup_cause: str = 'normal'):
    """Log call details to database"""
    try:
        call_log = {
            'call_id': session.get('call_control_id', ''),
            'from_number': session.get('from_number', ''),
            'to_number': session.get('to_number', ''),
            'start_time': session.get('start_time'),
            'end_time': datetime.now(),
            'duration': (datetime.now() - session.get('start_time', datetime.now())).total_seconds(),
            'menu_selection': session.get('menu_selection'),
            'intent': session.get('intent'),
            'status': 'completed' if hangup_cause == 'normal' else 'failed',
            'transcript': json.dumps(session.get('conversation_transcript', [])),
            'metadata': json.dumps(session.get('context', {}))
        }
        database.log_call(call_log)
        print(f"✓ Call logged to database: {call_log['call_id']}")
    except Exception as e:
        print(f"⚠️ Failed to log call to database: {e}")


# ==================== IVR MENU FUNCTIONS ====================

def play_ivr_menu(call_control_id: str, session: dict, replay: bool = False, invalid: bool = False):
    """Play IVR menu and gather DTMF input"""
    
    # Fetch IVR settings from dashboard
    dashboard_settings = ivr_config.fetch_ivr_settings()
    
    if dashboard_settings:
        full_greeting = dashboard_settings.get('greetingText', 'Welcome to Premier Sports.')
        invalid_msg = dashboard_settings.get('invalidOptionMessage', "Sorry, invalid option.")
        replay_msg = dashboard_settings.get('replayMessage', "I didn't catch that.")
        menu_options = dashboard_settings.get('menuOptions', [])
        use_audio = dashboard_settings.get('useAudioGreeting', False)
        audio_url = dashboard_settings.get('greetingAudioUrl', None)
        
        print(f"✓ Using IVR settings from dashboard with {len(menu_options)} menu options")
    else:
        print(f"⚠ Using fallback IVR settings")
        full_greeting = "Welcome to Premier Sports. Press 1 for basketball, press 2 for parties, press 9 for the AI assistant, or press 0 for an operator."
        invalid_msg = "Sorry, invalid option."
        replay_msg = "I didn't catch that."
        use_audio = False
        audio_url = None
    
    # Build message text
    if invalid:
        text = f"{invalid_msg} {full_greeting}"
    elif replay:
        text = f"{replay_msg} {full_greeting}"
    else:
        text = full_greeting
    
    # Update session state
    session['state'] = 'menu'
    client_state = {
        'state': 'menu',
        'attempt': session.get('context', {}).get('menu_attempts', 0) + 1
    }
    
    # Use audio or TTS
    if use_audio and audio_url:
        # Play audio and gather DTMF
        s3_bucket_url = os.getenv('S3_BUCKET_URL', 'https://abacus-prod-uploaded-files.s3.us-west-2.amazonaws.com')
        full_audio_url = f"{s3_bucket_url}/{audio_url}"
        print(f"🎵 Playing audio menu: {full_audio_url}")
        
        telnyx_client.gather_using_audio(
            call_control_id=call_control_id,
            audio_url=full_audio_url,
            valid_digits='0123456789',
            max_digits=1,
            timeout_ms=5000,
            client_state=client_state
        )
    else:
        # Use TTS and gather DTMF
        print(f"🗣️ Speaking menu: {text[:50]}...")
        
        telnyx_client.gather_using_speak(
            call_control_id=call_control_id,
            text=text,
            valid_digits='0123456789',
            max_digits=1,
            timeout_ms=5000,
            voice='female',
            language='en-US',
            client_state=client_state
        )


def handle_menu_selection(call_control_id: str, session: dict, digit: str):
    """Handle menu selection based on DTMF digit"""
    
    # Fetch menu options from dashboard
    dashboard_settings = ivr_config.fetch_ivr_settings()
    
    MENU = {}
    if dashboard_settings and 'menuOptions' in dashboard_settings:
        for option in dashboard_settings['menuOptions']:
            MENU[option['keyPress']] = {
                'name': option['optionName'],
                'greeting': option['departmentGreeting'],
                'intent': option['intentType'],
                'action_type': option.get('actionType', 'ai_conversation'),
                'transfer_number': option.get('transferNumber'),
                'use_audio': option.get('useAudio', False),
                'audio_url': option.get('audioUrl', None)
            }
        print(f"✓ Using menu options from dashboard: {list(MENU.keys())}")
    else:
        # Fallback menu
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
            '0': {
                'name': 'Operator',
                'greeting': None,
                'intent': 'transfer',
                'action_type': 'transfer',
                'transfer_number': os.getenv('STAFF_PHONE_NUMBER', '+19177969730')
            }
        }
    
    # Check if digit is valid
    if digit not in MENU:
        print(f"❌ Invalid menu selection: {digit}")
        session['context']['menu_attempts'] = session.get('context', {}).get('menu_attempts', 0) + 1
        
        if session['context']['menu_attempts'] >= 3:
            # Too many attempts, transfer to operator
            transfer_to_operator(call_control_id, session)
        else:
            # Replay menu with invalid message
            play_ivr_menu(call_control_id, session, invalid=True)
        return
    
    # Valid selection
    menu_option = MENU[digit]
    session['menu_selection'] = digit
    session['intent'] = menu_option['intent']
    
    print(f"✓ Menu selection: {digit} - {menu_option['name']}")
    
    # Handle based on action type
    action_type = menu_option.get('action_type', 'ai_conversation')
    
    if action_type == 'transfer':
        # Transfer to number
        transfer_number = menu_option.get('transfer_number')
        if transfer_number:
            transfer_call(call_control_id, session, transfer_number)
        else:
            transfer_to_operator(call_control_id, session)
    
    elif action_type == 'ai_conversation':
        # Start AI conversation
        greeting = menu_option.get('greeting', 'How can I help you?')
        start_ai_conversation(call_control_id, session, greeting)
    
    else:
        # Unknown action type, default to AI
        start_ai_conversation(call_control_id, session, "How can I help you?")


def start_ai_conversation(call_control_id: str, session: dict, greeting: str):
    """Start AI-powered conversation"""
    session['state'] = 'conversation'
    
    client_state = {
        'state': 'conversation',
        'intent': session.get('intent', 'general')
    }
    
    print(f"🤖 Starting AI conversation: {greeting[:50]}...")
    
    # Speak greeting and wait for response
    # NOTE: For full AI integration, you'd need to implement speech recognition
    # For now, we'll use DTMF-based interaction
    
    telnyx_client.gather_using_speak(
        call_control_id=call_control_id,
        text=greeting,
        valid_digits='0123456789*#',
        max_digits=10,
        timeout_ms=8000,
        voice='female',
        language='en-US',
        client_state=client_state
    )


def transfer_call(call_control_id: str, session: dict, to_number: str):
    """Transfer call to another number"""
    session['state'] = 'transferring'
    
    from_number = os.getenv('TELNYX_PHONE_NUMBER', '+12014096125')
    
    print(f"📞 Transferring call to {to_number}")
    
    try:
        # Speak transfer message
        telnyx_client.speak(
            call_control_id=call_control_id,
            text="Please hold while I transfer you.",
            voice='female',
            language='en-US'
        )
        
        # Wait a moment then transfer
        # NOTE: In production, you'd use async/delayed execution
        import time
        time.sleep(2)
        
        telnyx_client.transfer(
            call_control_id=call_control_id,
            to=to_number,
            from_number=from_number
        )
    except Exception as e:
        print(f"❌ Transfer failed: {e}")
        telnyx_client.speak(
            call_control_id=call_control_id,
            text="Sorry, we're unable to transfer your call at this time. Please call back later.",
            voice='female',
            language='en-US'
        )


def transfer_to_operator(call_control_id: str, session: dict):
    """Transfer to operator/staff"""
    staff_number = os.getenv('STAFF_PHONE_NUMBER', '+19177969730')
    transfer_call(call_control_id, session, staff_number)


# ==================== WEBHOOK HANDLERS ====================

@app.route('/webhooks/telnyx', methods=['POST'])
def handle_telnyx_webhook():
    """
    Main webhook handler for all Telnyx Call Control events.
    Handles: call.initiated, call.answered, call.gather.ended, call.hangup, etc.
    """
    try:
        # Get webhook data
        webhook_data = request.get_json()
        
        # Extract event data
        event_data = extract_telnyx_event_data(webhook_data)
        event_type = event_data['event_type']
        call_control_id = event_data['call_control_id']
        
        # Store in debug
        last_event_debug['timestamp'] = datetime.now().isoformat()
        last_event_debug['event_type'] = event_type
        last_event_debug['call_control_id'] = call_control_id
        last_event_debug['raw_data'] = webhook_data
        
        print(f"\n{'='*60}")
        print(f"📞 TELNYX EVENT: {event_type}")
        print(f"Call Control ID: {call_control_id}")
        print(f"{'='*60}")
        
        # Route based on event type
        if event_type == 'call.initiated':
            handle_call_initiated(call_control_id, event_data)
        
        elif event_type == 'call.answered':
            handle_call_answered(call_control_id, event_data)
        
        elif event_type == 'call.gather.ended':
            handle_gather_ended(call_control_id, event_data)
        
        elif event_type == 'call.hangup':
            handle_call_hangup(call_control_id, event_data)
        
        elif event_type == 'call.speak.started':
            print(f"🗣️ Speech started")
        
        elif event_type == 'call.speak.ended':
            print(f"✓ Speech ended")
        
        elif event_type == 'call.dtmf.received':
            print(f"🔢 DTMF received: {event_data.get('digit', '')}")
        
        else:
            print(f"ℹ️ Unhandled event type: {event_type}")
        
        # Return 200 OK to acknowledge webhook
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        print(f"❌ ERROR in webhook handler: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def handle_call_initiated(call_control_id: str, event_data: dict):
    """Handle call.initiated event - call is ringing"""
    print(f"📞 Call initiated from {event_data.get('from', '')}")
    
    # Create session
    session = get_or_create_session(call_control_id, event_data)
    session['state'] = 'initiated'
    
    # Answer the call
    try:
        telnyx_client.answer_call(call_control_id)
        print(f"✓ Call answered")
    except Exception as e:
        print(f"❌ Failed to answer call: {e}")


def handle_call_answered(call_control_id: str, event_data: dict):
    """Handle call.answered event - call is connected"""
    print(f"✅ Call answered")
    
    # Get session
    session = get_or_create_session(call_control_id, event_data)
    session['state'] = 'answered'
    
    # Check business hours
    if not is_business_hours():
        print(f"⏰ Outside business hours")
        telnyx_client.speak(
            call_control_id=call_control_id,
            text="Thank you for calling. We are currently closed. Our business hours are Monday through Friday, 9 AM to 9 PM Eastern Time. Please call back during business hours.",
            voice='female',
            language='en-US'
        )
        return
    
    # Play IVR menu
    play_ivr_menu(call_control_id, session)


def handle_gather_ended(call_control_id: str, event_data: dict):
    """Handle call.gather.ended event - DTMF input received"""
    
    digits = event_data.get('digits', '')
    client_state_encoded = event_data.get('client_state', '')
    
    print(f"🔢 Gather ended - Digits: '{digits}'")
    
    # Decode client state
    if client_state_encoded:
        try:
            client_state = telnyx_client.decode_client_state(client_state_encoded)
            print(f"📋 Client state: {client_state}")
        except:
            client_state = {}
    else:
        client_state = {}
    
    # Get session
    session = get_or_create_session(call_control_id, event_data)
    
    # Handle based on current state
    current_state = client_state.get('state', session.get('state', 'menu'))
    
    if current_state == 'menu':
        # Handle menu selection
        if digits:
            handle_menu_selection(call_control_id, session, digits)
        else:
            # Timeout - replay menu
            play_ivr_menu(call_control_id, session, replay=True)
    
    elif current_state == 'conversation':
        # Handle conversation input
        # This would integrate with your AI/NLU system
        print(f"💬 Conversation input: {digits}")
        
        # For now, just acknowledge
        telnyx_client.speak(
            call_control_id=call_control_id,
            text="Thank you for your input. Let me connect you with someone who can help.",
            voice='female',
            language='en-US'
        )
        
        # Transfer to operator
        transfer_to_operator(call_control_id, session)
    
    else:
        print(f"⚠️ Unknown state: {current_state}")


def handle_call_hangup(call_control_id: str, event_data: dict):
    """Handle call.hangup event - call ended"""
    
    hangup_cause = event_data.get('hangup_cause', 'unknown')
    print(f"📴 Call hung up - Cause: {hangup_cause}")
    
    # Get session
    if call_control_id in call_sessions:
        session = call_sessions[call_control_id]
        
        # Log to database
        log_call_to_database(session, hangup_cause)
        
        # Clean up session
        del call_sessions[call_control_id]
        print(f"✓ Session cleaned up")


# ==================== HEALTH & DEBUG ENDPOINTS ====================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'phone-system-backend',
        'version': '2.0.0-telnyx',
        'timestamp': datetime.now().isoformat(),
        'telnyx_configured': telnyx_client is not None,
        'active_calls': len(call_sessions)
    })


@app.route('/debug/last-event', methods=['GET'])
def debug_last_event():
    """Debug endpoint to view last event"""
    return jsonify(last_event_debug)


@app.route('/debug/sessions', methods=['GET'])
def debug_sessions():
    """Debug endpoint to view active sessions"""
    return jsonify({
        'active_sessions': len(call_sessions),
        'sessions': {k: {
            'from': v.get('from_number'),
            'state': v.get('state'),
            'start_time': v.get('start_time').isoformat() if v.get('start_time') else None
        } for k, v in call_sessions.items()}
    })


# ==================== STARTUP ====================

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 PHONE SYSTEM BACKEND - TELNYX VERSION")
    print("="*60)
    print(f"Telnyx configured: {telnyx_client is not None}")
    print(f"Phone number: {os.getenv('TELNYX_PHONE_NUMBER', 'NOT SET')}")
    print(f"Base URL: {BASE_URL}")
    print(f"Webhook URL: {BASE_URL}/webhooks/telnyx")
    print("="*60 + "\n")
    
    # Run app
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
