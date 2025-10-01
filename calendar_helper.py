
"""
Google Calendar integration for sports facility booking system.
Handles availability checks and booking creation.
"""

import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json

class CalendarHelper:
    """
    Handles Google Calendar operations for facility booking.
    """
    
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    
    def __init__(self):
        self.service = None
        self.calendar_id = os.getenv('GOOGLE_CALENDAR_ID', 'primary')
        self.facility_timezone = 'America/New_York'  # Adjust as needed
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Google Calendar service."""
        try:
            creds = None
            token_path = os.getenv('GOOGLE_TOKEN_PATH', 'token.json')
            credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
            
            # Load existing token
            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, self.SCOPES)
            
            # If no valid credentials, get new ones
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if os.path.exists(credentials_path):
                        flow = InstalledAppFlow.from_client_secrets_file(
                            credentials_path, self.SCOPES)
                        creds = flow.run_local_server(port=0)
                    else:
                        print("Warning: Google Calendar credentials not found")
                        return
                
                # Save credentials for next run
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
            
            self.service = build('calendar', 'v3', credentials=creds)
            print("Google Calendar service initialized successfully")
            
        except Exception as e:
            print(f"Error initializing Google Calendar service: {e}")
            self.service = None
    
    def check_availability(self, date_time_str: str, service_type: str = 'basketball', 
                          duration_hours: int = 1) -> Dict[str, Any]:
        """
        Check availability for a specific date/time.
        
        Args:
            date_time_str: Date/time string in format 'YYYY-MM-DD HH:MM'
            service_type: Type of service (basketball, birthday_party, multi_sport)
            duration_hours: Duration in hours
            
        Returns:
            Dictionary with availability info and pricing
        """
        if not self.service:
            return {
                'available': False,
                'error': 'Calendar service not available',
                'alternatives': []
            }
        
        try:
            # Parse the date/time
            requested_datetime = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M')
            end_datetime = requested_datetime + timedelta(hours=duration_hours)
            
            # Check business hours (9 AM - 9 PM)
            if requested_datetime.hour < 9 or end_datetime.hour > 21:
                return {
                    'available': False,
                    'reason': 'Outside business hours (9 AM - 9 PM)',
                    'alternatives': self._get_alternative_times(requested_datetime, duration_hours)
                }
            
            # Format times for Google Calendar API
            start_time = requested_datetime.isoformat() + '-05:00'  # EST timezone
            end_time = end_datetime.isoformat() + '-05:00'
            
            # Check for conflicts
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=start_time,
                timeMax=end_time,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            if events:
                # Time slot is occupied
                return {
                    'available': False,
                    'reason': 'Time slot already booked',
                    'alternatives': self._get_alternative_times(requested_datetime, duration_hours),
                    'conflicting_events': len(events)
                }
            
            # Calculate pricing
            from pricing import PricingEngine
            pricing_engine = PricingEngine()
            rate = pricing_engine.calculate_hourly_rate(requested_datetime, service_type)
            
            return {
                'available': True,
                'rate': rate,
                'service_type': service_type,
                'duration': duration_hours,
                'total_cost': rate * duration_hours,
                'date_time': date_time_str
            }
            
        except Exception as e:
            print(f"Error checking availability: {e}")
            return {
                'available': False,
                'error': str(e),
                'alternatives': []
            }
    
    def create_booking(self, date_time_str: str, service_type: str, 
                      customer_phone: str, hourly_rate: float, 
                      duration_hours: int = 1, customer_name: str = None) -> Dict[str, Any]:
        """
        Create a booking in Google Calendar.
        
        Args:
            date_time_str: Date/time string in format 'YYYY-MM-DD HH:MM'
            service_type: Type of service
            customer_phone: Customer phone number
            hourly_rate: Rate per hour
            duration_hours: Duration in hours
            customer_name: Optional customer name
            
        Returns:
            Dictionary with booking result
        """
        if not self.service:
            return {
                'success': False,
                'error': 'Calendar service not available'
            }
        
        try:
            # Parse the date/time
            start_datetime = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M')
            end_datetime = start_datetime + timedelta(hours=duration_hours)
            
            # Format times for Google Calendar API
            start_time = start_datetime.isoformat() + '-05:00'
            end_time = end_datetime.isoformat() + '-05:00'
            
            # Create event details
            total_cost = hourly_rate * duration_hours
            
            event_title = f"{service_type.replace('_', ' ').title()} Rental"
            if customer_name:
                event_title += f" - {customer_name}"
            
            event_description = f"""
Booking Details:
- Service: {service_type.replace('_', ' ').title()}
- Duration: {duration_hours} hour(s)
- Rate: ${hourly_rate}/hour
- Total Cost: ${total_cost}
- Customer Phone: {customer_phone}
- Booked via: Automated Phone System
- Booking Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """.strip()
            
            event = {
                'summary': event_title,
                'description': event_description,
                'start': {
                    'dateTime': start_time,
                    'timeZone': self.facility_timezone,
                },
                'end': {
                    'dateTime': end_time,
                    'timeZone': self.facility_timezone,
                },
                'attendees': [],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 24 hours before
                        {'method': 'popup', 'minutes': 60},       # 1 hour before
                    ],
                },
                'colorId': self._get_color_id(service_type)
            }
            
            # Create the event
            created_event = self.service.events().insert(
                calendarId=self.calendar_id, 
                body=event
            ).execute()
            
            booking_id = created_event['id'][:8].upper()  # Short booking ID
            
            return {
                'success': True,
                'booking_id': booking_id,
                'event_id': created_event['id'],
                'event_link': created_event.get('htmlLink', ''),
                'total_cost': total_cost,
                'start_time': start_time,
                'end_time': end_time
            }
            
        except HttpError as e:
            print(f"Google Calendar API error: {e}")
            return {
                'success': False,
                'error': f'Calendar API error: {e}'
            }
        except Exception as e:
            print(f"Error creating booking: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_alternative_times(self, requested_datetime: datetime, 
                              duration_hours: int, num_alternatives: int = 3) -> List[str]:
        """Get alternative available time slots."""
        alternatives = []
        
        try:
            # Check next few days for alternatives
            for day_offset in range(7):  # Check next week
                check_date = requested_datetime + timedelta(days=day_offset)
                
                # Check multiple time slots throughout the day
                for hour in [9, 11, 13, 15, 17, 19]:  # 9 AM to 7 PM
                    if len(alternatives) >= num_alternatives:
                        break
                    
                    alt_datetime = check_date.replace(hour=hour, minute=0, second=0, microsecond=0)
                    
                    # Skip if it's the same as requested time
                    if alt_datetime == requested_datetime:
                        continue
                    
                    # Check if this slot is available
                    alt_availability = self.check_availability(
                        alt_datetime.strftime('%Y-%m-%d %H:%M'),
                        duration_hours=duration_hours
                    )
                    
                    if alt_availability.get('available', False):
                        day_name = alt_datetime.strftime('%A')
                        time_str = alt_datetime.strftime('%I:%M %p')
                        date_str = alt_datetime.strftime('%B %d')
                        
                        alternatives.append(f"{day_name}, {date_str} at {time_str}")
                
                if len(alternatives) >= num_alternatives:
                    break
                    
        except Exception as e:
            print(f"Error getting alternatives: {e}")
        
        return alternatives
    
    def _get_color_id(self, service_type: str) -> str:
        """Get calendar color ID based on service type."""
        color_map = {
            'basketball': '7',      # Blue
            'birthday_party': '4',  # Red
            'multi_sport': '2',     # Green
        }
        return color_map.get(service_type, '1')  # Default to lavender
    
    def get_daily_schedule(self, date: datetime = None) -> List[Dict[str, Any]]:
        """Get the schedule for a specific day."""
        if not self.service:
            return []
        
        if date is None:
            date = datetime.now()
        
        try:
            # Set time range for the day
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            start_time = start_of_day.isoformat() + '-05:00'
            end_time = end_of_day.isoformat() + '-05:00'
            
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=start_time,
                timeMax=end_time,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            schedule = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                
                schedule.append({
                    'title': event.get('summary', 'No Title'),
                    'start': start,
                    'end': end,
                    'description': event.get('description', ''),
                    'id': event['id']
                })
            
            return schedule
            
        except Exception as e:
            print(f"Error getting daily schedule: {e}")
            return []

# Example usage and testing
if __name__ == "__main__":
    calendar_helper = CalendarHelper()
    
    # Test availability check
    test_datetime = "2025-10-01 15:00"
    availability = calendar_helper.check_availability(test_datetime, "basketball")
    print(f"Availability for {test_datetime}: {availability}")
    
    # Test booking creation (commented out to avoid actual bookings)
    # booking_result = calendar_helper.create_booking(
    #     test_datetime, "basketball", "+15551234567", 65.0
    # )
    # print(f"Booking result: {booking_result}")
