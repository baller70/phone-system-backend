
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
import requests

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

def format_price_for_speech(text):
    """
    Format prices in text to be spoken naturally by TTS.
    Converts "$65/hour" to "65 dollars per hour"
    Converts "$395" to "395 dollars"
    """
    import re
    
    # Order matters! Most specific patterns first
    
    # Pattern 1: "$65/hour" or "$65 per hour" → "65 dollars per hour"
    text = re.sub(r'\$(\d+)\s*/?per\s*hour', r'\1 dollars per hour', text, flags=re.IGNORECASE)
    text = re.sub(r'\$(\d+)\s*/\s*hour', r'\1 dollars per hour', text, flags=re.IGNORECASE)
    
    # Pattern 2: "$65-80" or "$65 to $80" → "65 to 80 dollars"
    text = re.sub(r'\$(\d+)\s*-\s*\$?(\d+)', r'\1 to \2 dollars', text)
    text = re.sub(r'\$(\d+)\s+to\s+\$(\d+)', r'\1 to \2 dollars', text)
    
    # Pattern 3: "$65-80/hour" → "65 to 80 dollars per hour"
    text = re.sub(r'\$(\d+)\s*-\s*\$?(\d+)\s*/?per\s*hour', r'\1 to \2 dollars per hour', text, flags=re.IGNORECASE)
    text = re.sub(r'\$(\d+)\s*-\s*\$?(\d+)\s*/\s*hour', r'\1 to \2 dollars per hour', text, flags=re.IGNORECASE)
    
    # Pattern 4: Standalone prices like "$395" or "$65" → "395 dollars" or "65 dollars"
    text = re.sub(r'\$(\d+)', r'\1 dollars', text)
    
    # Cleanup: Fix any double "dollars dollars"
    text = re.sub(r'(\d+)\s+dollars\s+dollars', r'\1 dollars', text)
    
    print(f"[PRICE FORMAT] Converted: {text}")
    return text

def construct_audio_url(audio_path):
    """
    Generate a pre-signed S3 URL for audio files.
    The S3 bucket is private, so we need signed URLs for Vonage to access them.
    We use a 7-day expiration to ensure the URL works for IVR playback.
    """
    if not audio_path:
        return None
    
    # If already a full URL, return as is
    if audio_path.startswith('http://') or audio_path.startswith('https://'):
        return audio_path
    
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        bucket_name = os.getenv('AWS_BUCKET_NAME', 'abacusai-apps-c20303f21c19131e5ce80575-us-west-2')
        region = 'us-west-2'  # Default region
        
        # Remove leading slash if present
        audio_path = audio_path.lstrip('/')
        
        # Create S3 client
        s3_client = boto3.client('s3', region_name=region)
        
        # Generate pre-signed URL with 7-day expiration (604800 seconds)
        # This is long enough for IVR audio files that are frequently accessed
        audio_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': audio_path
            },
            ExpiresIn=604800  # 7 days
        )
        
        print(f"[AUDIO] Generated signed URL for: {audio_path} (expires in 7 days)")
        return audio_url
        
    except ClientError as e:
        print(f"[AUDIO ERROR] Failed to generate signed URL: {e}")
        # Fallback to direct S3 URL (will fail if bucket is private, but good for debugging)
        audio_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{audio_path}"
        print(f"[AUDIO] Falling back to direct URL: {audio_url}")
        return audio_url
    except Exception as e:
        print(f"[AUDIO ERROR] Unexpected error: {e}")
        return None

# Debug storage for last DTMF input
last_dtmf_debug = {
    'timestamp': None,
    'raw_data': None,
    'dtmf_value': None,
    'matched': None
}

def add_to_conversation_history(session, role, message):
    """Add a message to the conversation history for later email summary."""
    if 'conversation_history' not in session:
        session['conversation_history'] = []
    
    session['conversation_history'].append({
        'timestamp': datetime.now().isoformat(),
        'role': role,  # 'ai' or 'customer'
        'message': message
    })
    
    print(f"[CONVERSATION] Added {role} message: {message[:50]}...")

def create_call_summary_html(session, call_details):
    """Create a beautifully formatted HTML email for the call summary."""
    
    conversation_history = session.get('conversation_history', [])
    customer_name = session.get('customer_name', 'Unknown')
    customer_email = session.get('customer_email', 'Not provided')
    department = session.get('department', 'Unknown')
    from_number = call_details.get('from_number', 'Unknown')
    duration = call_details.get('duration', 0)
    outcome = session.get('outcome', 'completed')
    booking_made = session.get('booking_id') is not None
    
    # Format duration
    minutes = duration // 60
    seconds = duration % 60
    duration_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
    
    # Format timestamp
    start_time = session.get('start_time', datetime.now())
    if isinstance(start_time, str):
        start_time = datetime.fromisoformat(start_time)
    timestamp_str = start_time.strftime("%B %d, %Y at %I:%M %p")
    
    # Build conversation HTML
    conversation_html = ""
    for msg in conversation_history:
        role = msg['role']
        message = msg['message']
        timestamp = msg.get('timestamp', '')
        
        if role == 'ai':
            conversation_html += f"""
            <div style="margin-bottom: 20px; padding: 15px; background-color: #f0f7ff; border-left: 4px solid #2563eb; border-radius: 8px;">
                <div style="font-weight: bold; color: #2563eb; margin-bottom: 5px;">🤖 AI Assistant</div>
                <div style="color: #1e293b; line-height: 1.6;">{message}</div>
            </div>
            """
        else:  # customer
            conversation_html += f"""
            <div style="margin-bottom: 20px; padding: 15px; background-color: #f0fdf4; border-left: 4px solid #16a34a; border-radius: 8px;">
                <div style="font-weight: bold; color: #16a34a; margin-bottom: 5px;">👤 Customer</div>
                <div style="color: #1e293b; line-height: 1.6;">{message}</div>
            </div>
            """
    
    if not conversation_html:
        conversation_html = "<p style='color: #64748b; font-style: italic;'>No conversation recorded</p>"
    
    # Booking info section
    booking_html = ""
    if booking_made:
        booking_id = session.get('booking_id', 'N/A')
        booking_details = session.get('context', {}).get('proposed_booking', {})
        service_type = booking_details.get('service_type', 'N/A')
        date_time = booking_details.get('date_time', 'N/A')
        total_cost = booking_details.get('total_cost', 'N/A')
        
        booking_html = f"""
        <div style="margin: 30px 0; padding: 20px; background: linear-gradient(135deg, #16a34a 0%, #22c55e 100%); border-radius: 12px; color: white;">
            <h3 style="margin: 0 0 15px 0; font-size: 18px;">✅ Booking Confirmed</h3>
            <div style="background: rgba(255,255,255,0.2); padding: 15px; border-radius: 8px;">
                <p style="margin: 5px 0;"><strong>Booking ID:</strong> {booking_id}</p>
                <p style="margin: 5px 0;"><strong>Service:</strong> {service_type.replace('_', ' ').title()}</p>
                <p style="margin: 5px 0;"><strong>Date/Time:</strong> {date_time}</p>
                <p style="margin: 5px 0;"><strong>Total Cost:</strong> ${total_cost}</p>
            </div>
        </div>
        """
    
    # Outcome badge
    outcome_colors = {
        'completed': ('#16a34a', '#f0fdf4', '✅'),
        'booking_success': ('#16a34a', '#f0fdf4', '🎉'),
        'booking_failed': ('#dc2626', '#fef2f2', '❌'),
        'transferred': ('#f59e0b', '#fffbeb', '📞'),
        'failed': ('#dc2626', '#fef2f2', '❌')
    }
    
    outcome_color, outcome_bg, outcome_icon = outcome_colors.get(outcome, ('#64748b', '#f1f5f9', 'ℹ️'))
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Call Summary</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f8fafc;">
        <div style="max-width: 600px; margin: 40px auto; background: white; border-radius: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); overflow: hidden;">
            
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%); padding: 30px; text-align: center; color: white;">
                <h1 style="margin: 0; font-size: 28px; font-weight: bold;">📞 New Call Received</h1>
                <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">{timestamp_str}</p>
            </div>
            
            <!-- Call Details -->
            <div style="padding: 30px;">
                
                <!-- Status Badge -->
                <div style="text-align: center; margin-bottom: 30px;">
                    <span style="display: inline-block; padding: 10px 20px; background-color: {outcome_bg}; color: {outcome_color}; border-radius: 20px; font-weight: bold; font-size: 14px;">
                        {outcome_icon} {outcome.replace('_', ' ').title()}
                    </span>
                </div>
                
                <!-- Key Information -->
                <div style="background: #f8fafc; padding: 20px; border-radius: 12px; margin-bottom: 30px;">
                    <h2 style="margin: 0 0 15px 0; font-size: 18px; color: #1e293b;">📋 Call Information</h2>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px 0; color: #64748b; font-weight: 500;">Caller Phone:</td>
                            <td style="padding: 8px 0; color: #1e293b; font-weight: 600; text-align: right;">{from_number}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #64748b; font-weight: 500;">Customer Name:</td>
                            <td style="padding: 8px 0; color: #1e293b; font-weight: 600; text-align: right;">{customer_name}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #64748b; font-weight: 500;">Email:</td>
                            <td style="padding: 8px 0; color: #1e293b; font-weight: 600; text-align: right;">{customer_email}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #64748b; font-weight: 500;">Department:</td>
                            <td style="padding: 8px 0; color: #1e293b; font-weight: 600; text-align: right;">{department.title()}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #64748b; font-weight: 500;">Call Duration:</td>
                            <td style="padding: 8px 0; color: #1e293b; font-weight: 600; text-align: right;">{duration_str}</td>
                        </tr>
                    </table>
                </div>
                
                {booking_html}
                
                <!-- Conversation Transcript -->
                <div style="margin-top: 30px;">
                    <h2 style="margin: 0 0 20px 0; font-size: 18px; color: #1e293b;">💬 Full Conversation</h2>
                    {conversation_html}
                </div>
                
            </div>
            
            <!-- Footer -->
            <div style="background: #f8fafc; padding: 20px 30px; text-align: center; color: #64748b; font-size: 14px; border-top: 1px solid #e2e8f0;">
                <p style="margin: 0;">This is an automated call summary from your Phone System Dashboard</p>
                <p style="margin: 10px 0 0 0;">
                    <a href="https://phone-system-dashboa-8em0c9.abacusai.app" style="color: #3b82f6; text-decoration: none; font-weight: 600;">
                        View Full Dashboard →
                    </a>
                </p>
            </div>
            
        </div>
    </body>
    </html>
    """
    
    return html

def send_call_summary_email(session, call_details):
    """Send a call summary email using Resend API."""
    try:
        resend_api_key = os.getenv('RESEND_API_KEY')
        owner_email = os.getenv('OWNER_EMAIL', 'notifications@phone-system-dashboa-8em0c9.abacusai.app')
        email_from = os.getenv('EMAIL_FROM', 'onboarding@resend.dev')
        
        if not resend_api_key:
            print("❌ RESEND_API_KEY not configured, skipping email")
            return False
        
        # Create HTML email content
        html_content = create_call_summary_html(session, call_details)
        
        # Prepare email
        from_number = call_details.get('from_number', 'Unknown')
        customer_name = session.get('customer_name', 'Unknown')
        department = session.get('department', 'Unknown')
        
        subject = f"📞 New Call from {customer_name} ({from_number}) - {department.title()}"
        
        # Send via Resend API
        response = requests.post(
            'https://api.resend.com/emails',
            headers={
                'Authorization': f'Bearer {resend_api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'from': email_from,
                'to': [owner_email],
                'subject': subject,
                'html': html_content
            }
        )
        
        if response.status_code == 200:
            print(f"✅ Call summary email sent successfully to {owner_email}")
            return True
        else:
            print(f"❌ Failed to send email: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending call summary email: {e}")
        import traceback
        traceback.print_exc()
        return False

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
    """Test endpoint to verify dashboard API connection."""
    try:
        if database.test_dashboard_connection():
            return jsonify({
                'status': 'success',
                'message': 'Dashboard API connection working! Call logging is ready.',
                'dashboard_url': database.DASHBOARD_API_URL,
                'note': 'A test call log was created to verify the connection',
                'next_step': 'Make a call to your Vonage number to see it logged in the dashboard'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Dashboard API connection failed',
                'dashboard_url': database.DASHBOARD_API_URL,
                'note': 'Check Render logs for detailed error'
            }), 500
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'type': type(e).__name__
        }), 500

@app.route('/webhooks', methods=['GET', 'POST'])
def webhooks_fallback():
    """
    Fallback endpoint for incorrect Vonage configuration.
    Redirects to the proper answer_call() handler.
    """
    print("⚠️  WARNING: /webhooks endpoint hit - Vonage Answer URL should be /webhooks/answer")
    return answer_call()

@app.route('/webhooks/answer', methods=['GET', 'POST'])
def answer_call():
    """
    Handle incoming calls with Vonage Voice API.
    Returns NCCO (Nexmo Call Control Object) to control call flow.
    
    OPTIMIZED FOR INSTANT RESPONSE - NO DELAYS!
    """
    try:
        # INSTANT EXTRACTION - minimal processing
        if request.method == 'POST':
            call_data = request.get_json() or {}
        else:
            call_data = request.args.to_dict()
        
        conversation_uuid = call_data.get('conversation_uuid', '')
        from_number = call_data.get('from', '')
        call_uuid = call_data.get('uuid', '')
        
        print(f"📞 INCOMING CALL from {from_number}")
        
        # Initialize session (AFTER sending NCCO to avoid any delay)
        call_sessions[conversation_uuid] = {
            'from_number': from_number,
            'call_uuid': call_uuid,
            'state': 'greeting',
            'context': {},
            'start_time': datetime.now(),
            'conversation_transcript': []
        }
        
        # INSTANT NCCO RESPONSE - send greeting immediately
        ncco = create_greeting_ncco_with_recording(conversation_uuid)
        
        print(f"✅ Returning NCCO for call {call_uuid}")
        return jsonify(ncco)
        
    except Exception as e:
        print(f"❌ ERROR in answer_call: {e}")
        # Even on error, return NCCO immediately
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
            
            # Store outcome in session for email
            session['outcome'] = outcome
            
            # Get transcription/notes from session
            notes = None
            if 'conversation_history' in session:
                notes = "\n".join([
                    f"{'User' if msg.get('role') == 'user' else 'AI'}: {msg.get('content', '')}"
                    for msg in session['conversation_history'][-5:]  # Last 5 messages
                ])
            
            # Estimate call cost (Vonage charges approximately $0.007 per minute)
            cost = (duration / 60) * 0.007 if duration > 0 else 0.0
            
            # Get recording URL and transcription from session (if available)
            recording_url = session.get('recording_url') or event_data.get('recording_url')
            transcription = session.get('transcription')
            
            # Log to dashboard database
            try:
                call_log_id = database.log_call_to_dashboard(
                    caller_id=from_number or 'unknown',
                    caller_name=session.get('caller_name', 'Unknown'),
                    duration=int(duration) if duration else 0,
                    intent=intent,
                    outcome=outcome,
                    recording_url=recording_url,
                    transcription=transcription,
                    notes=notes,
                    cost=round(cost, 4)
                )
                print(f"✓ Call logged to dashboard (ID: {call_log_id}): {from_number} - {intent} - {outcome}")
                
                # Store call log ID in session for later updates (recording/transcription)
                if call_log_id and conversation_uuid in call_sessions:
                    call_sessions[conversation_uuid]['call_log_id'] = call_log_id
            except Exception as log_error:
                print(f"Warning: Failed to log call to dashboard: {log_error}")
            
            # Send call summary email (only for completed calls that lasted > 5 seconds)
            if event_status == 'completed' and duration > 5 and session:
                try:
                    call_details = {
                        'from_number': from_number,
                        'duration': duration,
                        'outcome': outcome
                    }
                    send_call_summary_email(session, call_details)
                except Exception as email_error:
                    print(f"Warning: Failed to send call summary email: {email_error}")
            
            # Clean up session after logging
            if conversation_uuid in call_sessions:
                del call_sessions[conversation_uuid]
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        print(f"Error handling event: {e}")
        return jsonify({'status': 'error'})

@app.route('/webhooks/recording', methods=['POST'])
def handle_recording():
    """Handle recording completion webhook from Vonage."""
    try:
        recording_data = request.get_json() or {}
        
        print(f"\n🎙️ Recording webhook received:")
        print(f"Data: {json.dumps(recording_data, indent=2)}")
        
        recording_url = recording_data.get('recording_url')
        conversation_uuid = recording_data.get('conversation_uuid')
        call_uuid = recording_data.get('call_uuid')
        
        if recording_url and conversation_uuid:
            # Try to update via session first (if call is still active)
            if conversation_uuid in call_sessions:
                call_sessions[conversation_uuid]['recording_url'] = recording_url
                
                # If we have a call_log_id, update the database immediately
                call_log_id = call_sessions[conversation_uuid].get('call_log_id')
                if call_log_id:
                    database.update_call_recording(call_log_id, recording_url)
                
                print(f"✓ Recording URL stored for conversation {conversation_uuid}")
            else:
                # Session has been cleaned up, recording arrived after call ended
                # This is normal behavior - recordings can take a few seconds to process
                print(f"⚠️ Session not found (call already ended), recording will be in next update")
                # Note: The recording may already be in the call log if the event came before cleanup
                
        return jsonify({'status': 'ok'})
    except Exception as e:
        print(f"Error handling recording webhook: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/webhooks/transcription', methods=['POST'])
def handle_transcription():
    """Handle transcription completion webhook from Vonage."""
    try:
        transcription_data = request.get_json() or {}
        
        print(f"\n📝 Transcription webhook received:")
        print(f"Data: {json.dumps(transcription_data, indent=2)}")
        
        transcript = transcription_data.get('text') or transcription_data.get('transcript')
        conversation_uuid = transcription_data.get('conversation_uuid')
        call_uuid = transcription_data.get('call_uuid')
        
        if transcript and conversation_uuid:
            # Try to update via session first (if call is still active)
            if conversation_uuid in call_sessions:
                call_sessions[conversation_uuid]['transcription'] = transcript
                
                # If we have a call_log_id, update the database immediately
                call_log_id = call_sessions[conversation_uuid].get('call_log_id')
                if call_log_id:
                    database.update_call_transcription(call_log_id, transcript)
                
                print(f"✓ Transcription stored for conversation {conversation_uuid}")
            else:
                # Session has been cleaned up, transcription arrived after call ended
                # This is normal - transcriptions can take time to process
                print(f"⚠️ Session not found (call already ended), transcription processing delayed")
                # Note: The transcription may already be in the call log if it came before cleanup
                
        return jsonify({'status': 'ok'})
    except Exception as e:
        print(f"Error handling transcription webhook: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

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
                    'transfer_number': option.get('transferNumber'),
                    'use_audio': option.get('useAudio', False),
                    'audio_url': option.get('audioUrl', None)
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
                    'action_type': 'ai_conversation',
                    'use_audio': False,
                    'audio_url': None
                },
                '2': {
                    'name': 'Parties',
                    'greeting': 'Perfect! Let me help you plan a birthday party. How many guests are you expecting?',
                    'intent': 'party_booking',
                    'action_type': 'ai_conversation',
                    'use_audio': False,
                    'audio_url': None
                },
                '9': {
                    'name': 'AI Assistant',
                    'greeting': "Hi! I'm your AI assistant. How can I help you today?",
                    'intent': 'general_inquiry',
                    'action_type': 'ai_conversation',
                    'use_audio': False,
                    'audio_url': None
                },
                '0': {
                    'name': 'Operator',
                    'greeting': None,  # Will transfer
                    'intent': 'transfer',
                    'action_type': 'transfer',
                    'use_audio': False,
                    'audio_url': None
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
            session['department'] = option['name']  # Store department name for email
            
            # Track customer selection in conversation history
            add_to_conversation_history(session, 'customer', f"Selected option {dtmf}: {option['name']}")
            
            # Handle operator transfer
            if dtmf == '0':
                print("Transferring to operator...")
                add_to_conversation_history(session, 'ai', "Transferring you to a live operator...")
                return jsonify(create_transfer_ncco())
            
            # Set context
            session['context']['service_type'] = option['intent']
            session['state'] = 'collect_name'  # Start with name collection
            
            # Build NCCO for department greeting + name collection
            ncco = []
            
            # START RECORDING NOW (after initial greeting already played)
            # This ensures the initial greeting plays instantly, but the conversation is still recorded
            ncco.append({
                "action": "record",
                "eventUrl": [f"{BASE_URL}/webhooks/recording"],
                "eventMethod": "POST",
                "format": "mp3",
                "split": "conversation",
                "channels": 2,
                "endOnSilence": 3,
                "endOnKey": "#",
                "timeOut": 7200,
                "beepStart": False,
                "transcription": {
                    "language": "en-US",
                    "eventUrl": [f"{BASE_URL}/webhooks/transcription"],
                    "eventMethod": "POST"
                }
            })
            
            # Add department greeting (audio or TTS)
            department_greeting_text = option['greeting']
            if option.get('use_audio') and option.get('audio_url'):
                # Use audio file
                audio_url = construct_audio_url(option['audio_url'])
                print(f"Playing department audio: {audio_url}")
                ncco.append({
                    "action": "stream",
                    "streamUrl": [audio_url],
                    "bargeIn": True
                })
                # Track with original greeting text
                add_to_conversation_history(session, 'ai', department_greeting_text)
            else:
                # Use text-to-speech
                print(f"Speaking department greeting: {department_greeting_text}")
                ncco.append({
                    "action": "talk",
                    "text": department_greeting_text,
                    "voiceName": "Amy",
                    "bargeIn": True
                })
                add_to_conversation_history(session, 'ai', department_greeting_text)
            
            # Ask for customer name
            name_request = "Before we begin, may I have your name please?"
            print(f"Asking for name: {name_request}")
            add_to_conversation_history(session, 'ai', name_request)
            
            ncco.extend([
                {
                    "action": "talk",
                    "text": name_request,
                    "voiceName": "Amy",
                    "bargeIn": True
                },
                {
                    "action": "input",
                    "eventUrl": [f"{BASE_URL}/webhooks/speech"],
                    "type": ["speech"],
                    "speech": {
                        "endOnSilence": 2,
                        "language": "en-US",
                        "context": ["name", "firstname", "lastname"],
                        "startTimeout": 8,
                        "maxDuration": 10  # Short duration for name
                    }
                }
            ])
            
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
        
        # Track customer's speech input in conversation history
        add_to_conversation_history(session, 'customer', speech_text)
        
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
    
    # Handle name collection (FIRST PRIORITY)
    if current_state == 'collect_name':
        # Extract name from speech
        speech_text = session.get('last_speech', '')
        # Store the name (simple extraction - user said their name)
        session['customer_name'] = speech_text.strip()
        session['state'] = 'collect_email'
        
        response_text = f"Thank you! And what's your email address?"
        print(f"Collected name: {session['customer_name']}, asking for email")
        
        # Track AI response
        add_to_conversation_history(session, 'ai', response_text)
        
        return [
            {
                "action": "talk",
                "text": response_text,
                "voiceName": "Amy",
                "bargeIn": True
            },
            {
                "action": "input",
                "eventUrl": [f"{BASE_URL}/webhooks/speech"],
                "type": ["speech"],
                "speech": {
                    "endOnSilence": 2,
                    "language": "en-US",
                    "context": ["email", "address", "@"],
                    "startTimeout": 8,
                    "maxDuration": 15  # Longer for email
                }
            }
        ]
    
    # Handle email collection (SECOND PRIORITY)
    if current_state == 'collect_email':
        # Extract email from speech
        speech_text = session.get('last_speech', '')
        # Store the email (will need parsing)
        session['customer_email'] = speech_text.strip()
        session['state'] = 'ready'  # Now ready for main conversation
        
        customer_name = session.get('customer_name', 'there')
        response_text = f"Perfect! Thanks {customer_name}. How may I help you today?"
        print(f"Collected email: {session['customer_email']}, ready for conversation")
        
        # Track AI response
        add_to_conversation_history(session, 'ai', response_text)
        
        return [
            {
                "action": "talk",
                "text": response_text,
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
                    "maxDuration": 60
                }
            }
        ]
    
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
            add_to_conversation_history(session, 'ai', response_text)
            return create_speech_input_ncco(response_text, 'booking_restart')
        else:
            # Didn't understand, ask again
            if 'proposed_booking' in session['context']:
                booking = session['context']['proposed_booking']
                response_text = f"Just to confirm, would you like me to book {booking['service_type'].replace('_', ' ')} for {booking['date_time']} at ${booking['total_cost']}? Please say yes or no."
                response_text = format_price_for_speech(response_text)
                add_to_conversation_history(session, 'ai', response_text)
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
    
    # Format prices naturally for TTS (convert "$65/hour" to "65 dollars per hour")
    description = format_price_for_speech(pricing_info['description'])
    
    response_text = f"For {service_type} rentals, our pricing is as follows: {description}. Would you like to check availability or make a booking?"
    
    # Track AI response
    add_to_conversation_history(session, 'ai', response_text)
    
    return create_speech_input_ncco(response_text, 'pricing_followup')

def handle_availability_inquiry(entities, session):
    """Handle availability checks."""
    date_time = entities.get('date_time')
    service_type = entities.get('service_type', 'basketball')
    
    if not date_time:
        response_text = "I'd be happy to check availability for you. What date and time are you looking for?"
        add_to_conversation_history(session, 'ai', response_text)
        return create_speech_input_ncco(response_text, 'availability_date_needed')
    
    # Check calendar availability
    availability = calendar_helper.check_availability(date_time, service_type)
    
    if availability['available']:
        response_text = f"Great news! We have availability on {date_time} for {service_type}. The rate would be ${availability['rate']} per hour. Would you like to make a booking?"
        response_text = format_price_for_speech(response_text)
        session['context']['proposed_booking'] = {
            'date_time': date_time,
            'service_type': service_type,
            'rate': availability['rate']
        }
        add_to_conversation_history(session, 'ai', response_text)
        return create_speech_input_ncco(response_text, 'booking_confirmation')
    else:
        alternative_times = availability.get('alternatives', [])
        if alternative_times:
            alt_text = ", ".join(alternative_times[:3])
            response_text = f"I'm sorry, that time slot isn't available. However, I have these alternatives: {alt_text}. Would any of these work for you?"
        else:
            response_text = "I'm sorry, that time slot isn't available. Would you like me to check a different date or time?"
        
        add_to_conversation_history(session, 'ai', response_text)
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
            session['booking_id'] = booking_result['booking_id']  # Store booking ID for email
            response_text = f"Perfect! I've reserved {booking_details['service_type'].replace('_', ' ')} for {booking_details['date_time']} at ${booking_details['rate']} per hour. Your booking confirmation is {booking_result['booking_id']}. You'll receive a confirmation text shortly. Is there anything else I can help you with?"
            response_text = format_price_for_speech(response_text)
            add_to_conversation_history(session, 'ai', response_text)
            return create_speech_input_ncco(response_text, 'booking_complete')
        else:
            # Track failed booking
            session['outcome'] = 'booking_failed'
            session['intent'] = 'booking'
            response_text = "I'm sorry, there was an issue creating your booking. Let me transfer you to our staff for assistance."
            add_to_conversation_history(session, 'ai', response_text)
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
            response_text = format_price_for_speech(response_text)
            session['state'] = 'booking_confirmation'
            add_to_conversation_history(session, 'ai', response_text)
            return create_speech_input_ncco(response_text, 'booking_confirmation')
        else:
            reason = availability.get('reason', 'not available')
            response_text = f"I'm sorry, that time slot is {reason}. "
            
            alternatives = availability.get('alternatives', [])
            if alternatives:
                response_text += f"I have availability on {alternatives[0]}. Would that work for you?"
            else:
                response_text = "Let me transfer you to our staff to find an available time."
                add_to_conversation_history(session, 'ai', response_text)
                return escalation_handler.create_escalation_ncco('no_availability', entities)
            
            add_to_conversation_history(session, 'ai', response_text)
            return create_speech_input_ncco(response_text, 'booking_alternative')
    
    # Missing information - ask for what we need
    if not service_type:
        response_text = "I'd be happy to help you make a booking. What type of activity are you planning - basketball, multi-sport, or a birthday party?"
        session['state'] = 'need_service_type'
        add_to_conversation_history(session, 'ai', response_text)
        return create_speech_input_ncco(response_text, 'need_service_type')
    elif not date_time:
        response_text = f"Perfect! For {service_type.replace('_', ' ')}, what date and time work best for you?"
        # Store service type in context
        session['context']['service_type'] = service_type
        session['state'] = 'need_date_time'
        add_to_conversation_history(session, 'ai', response_text)
        return create_speech_input_ncco(response_text, 'need_date_time')
    else:
        # Shouldn't reach here, but just in case
        response_text = "I'd be happy to help you make a booking. What type of activity and what date/time would you like?"
        session['state'] = 'booking_details_needed'
        add_to_conversation_history(session, 'ai', response_text)
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
    
    # Track AI response
    add_to_conversation_history(session, 'ai', response_text)
    
    return create_speech_input_ncco(response_text, 'general_followup')

def create_greeting_ncco():
    """Create initial greeting NCCO with IVR menu."""
    return create_ivr_menu_ncco()

def create_greeting_ncco_with_recording(conversation_uuid):
    """
    Create initial greeting NCCO - greeting plays IMMEDIATELY.
    Recording is NOT included here to avoid Vonage setup delays.
    Recording will be started via the /webhooks/dtmf endpoint after DTMF is received.
    """
    # Get IVR settings from cache (instant)
    dashboard_settings = ivr_config.fetch_ivr_settings()
    
    # Extract greeting settings (with fallbacks)
    if dashboard_settings:
        greeting_text = dashboard_settings.get('greetingText', 'Welcome to Premier Sports.')
        voice_name = dashboard_settings.get('voiceName', 'Amy')
    else:
        greeting_text = 'Welcome to Premier Sports. Press 1 for basketball, press 2 for parties, press 9 for AI assistant, or press 0 for operator.'
        voice_name = 'Amy'
    
    # Build NCCO array - NO RECORDING HERE (to avoid delay)
    # Recording will be started after DTMF input
    ncco = [
        # Action 1: Play greeting IMMEDIATELY (no recording setup delay)
        {
            "action": "talk",
            "text": greeting_text,
            "voiceName": voice_name,
            "bargeIn": True
        },
        # Action 2: Collect DTMF input
        {
            "action": "input",
            "eventUrl": [f"{BASE_URL}/webhooks/dtmf"],
            "type": ["dtmf"],
            "dtmf": {
                "timeOut": 5,
                "maxDigits": 1,
                "submitOnHash": False
            }
        }
    ]
    
    return ncco

def create_ivr_menu_ncco(replay=False, invalid=False):
    """Create IVR menu NCCO with DTMF input options - pulls from dashboard."""
    
    # Fetch IVR settings from dashboard
    dashboard_settings = ivr_config.fetch_ivr_settings()
    
    if dashboard_settings:
        # Use dashboard settings
        # The greetingText from dashboard ALREADY contains the full greeting + all menu options
        full_greeting = dashboard_settings.get('greetingText', 'Welcome to Premier Sports.')
        invalid_msg = dashboard_settings.get('invalidOptionMessage', "Sorry, invalid option.")
        replay_msg = dashboard_settings.get('replayMessage', "I didn't catch that.")
        menu_options = dashboard_settings.get('menuOptions', [])
        use_audio = dashboard_settings.get('useAudioGreeting', False)
        audio_url = dashboard_settings.get('greetingAudioUrl', None)
        
        print(f"✓ Using IVR settings from dashboard with {len(menu_options)} menu options")
        print(f"  Use audio: {use_audio}, Audio URL: {audio_url}")
    else:
        # Fallback to static settings
        print(f"⚠ Using fallback IVR settings")
        full_greeting = "Welcome to Premier Sports. Press 1 for basketball, press 2 for parties, press 9 for the AI assistant, or press 0 for an operator."
        invalid_msg = "Sorry, invalid option."
        replay_msg = "I didn't catch that."
        use_audio = False
        audio_url = None
    
    # For replay/invalid, always use TTS (no audio for error messages)
    if invalid or replay:
        if invalid:
            full_text = invalid_msg + " " + full_greeting
        else:
            full_text = replay_msg + " " + full_greeting
        
        print(f"\n===== IVR MENU NCCO (REPLAY/INVALID) =====")
        print(f"Text: {full_text}")
        print(f"==================================\n")
        
        return [
            {
                "action": "talk",
                "text": full_text,
                "voiceName": "Amy",
                "bargeIn": True
            },
            {
                "action": "input",
                "eventUrl": [f"{BASE_URL}/webhooks/dtmf"],
                "type": ["dtmf"],
                "dtmf": {
                    "timeOut": 5,
                    "maxDigits": 1,
                    "submitOnHash": False
                }
            }
        ]
    
    # Use the full greeting from dashboard (already includes all options)
    # No need to append anything!
    full_text = full_greeting
    
    # CRITICAL: Check if we should use audio or TTS
    # ALWAYS fall back to TTS for now since audio files don't exist yet
    use_tts_fallback = True  # Force TTS until audio files are uploaded to S3
    
    if use_audio and audio_url and not use_tts_fallback:
        # Build full S3 URL for audio
        s3_bucket_url = os.getenv('S3_BUCKET_URL', 'https://abacus-prod-uploaded-files.s3.us-west-2.amazonaws.com')
        full_audio_url = f"{s3_bucket_url}/{audio_url}"
        
        print(f"\n===== IVR MENU NCCO (AUDIO) =====")
        print(f"Audio URL: {full_audio_url}")
        print(f"==================================\n")
        
        ncco = [{
            "action": "stream",
            "streamUrl": [full_audio_url],
            "bargeIn": True
        }]
    else:
        # Use TTS (either by choice or as fallback)
        if use_audio and audio_url:
            print(f"⚠ Audio configured but using TTS fallback (audio files not yet uploaded)")
        
        print(f"\n===== IVR MENU NCCO (TTS) =====")
        print(f"Text: {full_text}")
        print(f"==================================\n")
        
        ncco = [{
            "action": "talk",
            "text": full_text,
            "voiceName": "Amy",
            "bargeIn": True
        }]
    
    # Add DTMF input
    ncco.append({
        "action": "input",
        "eventUrl": [f"{BASE_URL}/webhooks/dtmf"],
        "type": ["dtmf"],
        "dtmf": {
            "timeOut": 5,
            "maxDigits": 1,
            "submitOnHash": False
        }
    })
    
    return ncco

def create_department_greeting_ncco(menu_option):
    """Create department-specific greeting after menu selection."""
    greeting_text = menu_option.get('greeting', menu_option.get('departmentGreeting', ''))
    use_audio = menu_option.get('useAudio', False)
    audio_url = menu_option.get('audioUrl', None)
    
    # CRITICAL: Force TTS fallback until audio files are uploaded to S3
    use_tts_fallback = True
    
    # Check if we should use audio or TTS
    if use_audio and audio_url and not use_tts_fallback:
        # Build full S3 URL for audio
        s3_bucket_url = os.getenv('S3_BUCKET_URL', 'https://abacus-prod-uploaded-files.s3.us-west-2.amazonaws.com')
        full_audio_url = f"{s3_bucket_url}/{audio_url}"
        
        print(f"\n===== DEPARTMENT GREETING (AUDIO) =====")
        print(f"Department: {menu_option.get('optionName')}")
        print(f"Audio URL: {full_audio_url}")
        print(f"==================================\n")
        
        ncco = [{
            "action": "stream",
            "streamUrl": [full_audio_url],
            "bargeIn": True
        }]
    else:
        # Use TTS (either by choice or as fallback)
        if use_audio and audio_url:
            print(f"⚠ Audio configured for {menu_option.get('optionName')} but using TTS fallback")
        
        print(f"\n===== DEPARTMENT GREETING (TTS) =====")
        print(f"Department: {menu_option.get('optionName')}")
        print(f"Text: {greeting_text}")
        print(f"==================================\n")
        
        ncco = [{
            "action": "talk",
            "text": greeting_text,
            "voiceName": "Amy",
            "bargeIn": True
        }]
    
    # Add speech input
    ncco.append({
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
    })
    
    return ncco

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

@app.route('/debug/clear-cache', methods=['POST'])
def clear_ivr_cache():
    """Clear the IVR settings cache to force a fresh fetch."""
    try:
        ivr_config._ivr_cache = {'settings': None, 'timestamp': 0}
        print("[CACHE] IVR cache manually cleared")
        return jsonify({'status': 'success', 'message': 'IVR cache cleared'})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

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
