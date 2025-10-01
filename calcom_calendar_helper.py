"""
Cal.com Calendar integration for sports facility booking system.
Simple API key authentication - no OAuth complexity!
Handles availability checks and booking creation.
"""

import os
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json

class CalcomCalendarHelper:
    """
    Handles Cal.com Calendar operations for facility booking.
    Much simpler than Google Calendar - just needs an API token!
    """
    
    def __init__(self):
        self.api_token = os.getenv('CALCOM_API_TOKEN')
        self.base_url = os.getenv('CALCOM_BASE_URL', 'https://api.cal.com/v1')
        self.event_type_id = os.getenv('CALCOM_EVENT_TYPE_ID')  # Basketball court event type
        self.facility_timezone = 'America/New_York'
        
        if not self.api_token:
            print("Warning: Cal.com API token not found. Set CALCOM_API_TOKEN environment variable.")
            return
            
        # Test API connection
        self._test_connection()
    
    def _test_connection(self):
        """Test the API connection and token validity."""
        try:
            response = self._make_request('GET', '/me')
            if response.status_code == 200:
                user_info = response.json()
                print(f"✅ Cal.com API connected successfully for user: {user_info.get('email', 'Unknown')}")
            else:
                print(f"⚠️ Cal.com API connection issue: {response.status_code}")
        except Exception as e:
            print(f"❌ Cal.com API connection failed: {e}")
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> requests.Response:
        """Make authenticated request to Cal.com API."""
        url = f"{self.base_url}{endpoint}"
        headers = {
            'Content-Type': 'application/json'
        }
        
        # Cal.com uses API key as query parameter, not Bearer token
        if data is None:
            data = {}
        data['apiKey'] = self.api_token
        
        if method == 'GET':
            return requests.get(url, headers=headers, params=data)
        elif method == 'POST':
            return requests.post(url, headers=headers, params={'apiKey': self.api_token}, json=data)
        elif method == 'PUT':
            return requests.put(url, headers=headers, params={'apiKey': self.api_token}, json=data)
        elif method == 'DELETE':
            return requests.delete(url, headers=headers, params={'apiKey': self.api_token})
        
        raise ValueError(f"Unsupported HTTP method: {method}")
    
    def check_availability(self, date_time_str: str, service_type: str = 'basketball', 
                          duration_hours: int = 1) -> Dict[str, Any]:
        """
        Check availability for a specific date/time using Cal.com's availability API.
        
        Args:
            date_time_str: Date/time string in format 'YYYY-MM-DD HH:MM'
            service_type: Type of service (basketball, birthday_party, multi_sport)
            duration_hours: Duration in hours
            
        Returns:
            Dictionary with availability info and pricing
        """
        if not self.api_token:
            return {
                'available': False,
                'error': 'Cal.com API token not configured',
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
            
            # Format for Cal.com API (ISO format)
            start_time = requested_datetime.isoformat()
            end_time = end_datetime.isoformat()
            
            # For now, assume availability based on business hours
            # In production, this would check Cal.com's actual availability
            print(f"🔍 Checking availability for {date_time_str} ({service_type})")
            
            # Simple check: if time is in business hours, it's available
            # You can enhance this later to check actual Cal.com bookings
            slot_available = True
            
            # Optional: Try to check actual Cal.com availability (may fail if event type not configured)
            try:
                availability_params = {
                    'dateFrom': start_time,
                    'dateTo': end_time,
                    'eventTypeId': self.event_type_id or 1,
                    'timezone': self.facility_timezone
                }
                
                response = self._make_request('GET', '/availability', availability_params)
                
                if response.status_code == 200:
                    availability_data = response.json()
                    available_slots = availability_data.get('slots', [])
                    print(f"   Cal.com returned {len(available_slots)} available slots")
                    
                    # If Cal.com returns data, use it
                    if len(available_slots) == 0:
                        slot_available = False
                else:
                    print(f"   Cal.com availability check returned {response.status_code}, assuming available")
                    # If API call fails, assume available (fail-open for better UX)
                    slot_available = True
            except Exception as api_error:
                print(f"   Cal.com API error: {api_error}, assuming available")
                # If API fails, assume available
                slot_available = True
            
            if not slot_available:
                return {
                    'available': False,
                    'reason': 'Time slot already booked',
                    'alternatives': self._get_alternative_times(requested_datetime, duration_hours, 3, service_type)
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
        Create a booking using Cal.com API.
        
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
        if not self.api_token:
            return {
                'success': False,
                'error': 'Cal.com API token not configured'
            }
        
        try:
            # Parse the date/time
            start_datetime = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M')
            end_datetime = start_datetime + timedelta(hours=duration_hours)
            
            # Format for Cal.com API
            start_time = start_datetime.isoformat()
            end_time = end_datetime.isoformat()
            
            # Create booking details
            total_cost = hourly_rate * duration_hours
            
            booking_title = f"{service_type.replace('_', ' ').title()} Rental"
            if customer_name:
                booking_title += f" - {customer_name}"
            
            booking_notes = f"""
Booking Details:
- Service: {service_type.replace('_', ' ').title()}
- Duration: {duration_hours} hour(s)
- Rate: ${hourly_rate}/hour
- Total Cost: ${total_cost}
- Customer Phone: {customer_phone}
- Booked via: Automated Phone System
- Booking Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """.strip()
            
            # Create booking payload (Cal.com API v1 format)
            booking_data = {
                'start': start_time,  # Required field, correct name
                'eventTypeId': self.event_type_id or 1,
                'timeZone': self.facility_timezone,  # Correct camelCase
                'language': 'en',  # Required field
                'responses': {
                    'name': customer_name or 'Phone Customer',
                    'email': f'phone-booking-{datetime.now().strftime("%Y%m%d%H%M%S")}@facility.local',
                    'phone': customer_phone,
                    'notes': booking_notes
                },
                'metadata': {
                    'service_type': service_type,
                    'hourly_rate': str(hourly_rate),  # Convert to string
                    'duration_hours': str(duration_hours),  # Convert to string
                    'total_cost': str(total_cost),  # Convert to string
                    'booking_source': 'phone_system',
                    'booking_title': booking_title
                }
            }
            
            # Create the booking
            response = self._make_request('POST', '/bookings', booking_data)
            
            if response.status_code == 201:
                booking_result = response.json()
                
                # Generate a short booking ID
                booking_id = str(booking_result.get('id', ''))[:8].upper()
                
                return {
                    'success': True,
                    'booking_id': booking_id,
                    'calcom_booking_id': booking_result.get('id'),
                    'booking_url': booking_result.get('url', ''),
                    'total_cost': total_cost,
                    'start_time': start_time,
                    'end_time': end_time
                }
            else:
                error_msg = f"Cal.com booking failed: {response.status_code}"
                if response.text:
                    error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                    error_msg += f" - {error_data}"
                
                print(f"Booking creation error: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }
                
        except Exception as e:
            print(f"Error creating booking: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_alternative_times(self, requested_datetime: datetime, 
                              duration_hours: int, num_alternatives: int = 3, 
                              service_type: str = 'basketball') -> List[str]:
        """Get alternative available time slots."""
        alternatives = []
        
        try:
            # For now, just return static alternatives to avoid recursive API calls
            # In production, this would check real availability
            for day_offset in range(1, 4):  # Next 3 days
                alt_date = requested_datetime + timedelta(days=day_offset)
                day_name = alt_date.strftime('%A')
                date_str = alt_date.strftime('%B %d')
                
                # Suggest similar time slot on different days
                time_str = requested_datetime.strftime('%I:%M %p')
                alternatives.append(f"{day_name}, {date_str} at {time_str}")
                
                if len(alternatives) >= num_alternatives:
                    break
            
            # Original recursive code - commented out to prevent issues
            # # Check next few days for alternatives
            # for day_offset in range(7):  # Check next week
            #     check_date = requested_datetime + timedelta(days=day_offset)
            #     
            #     # Check multiple time slots throughout the day
            #     for hour in [9, 11, 13, 15, 17, 19]:  # 9 AM to 7 PM
            #         if len(alternatives) >= num_alternatives:
            #             break
            #         
            #         alt_datetime = check_date.replace(hour=hour, minute=0, second=0, microsecond=0)
            #         
            #         # Skip if it's the same as requested time
            #         if alt_datetime == requested_datetime:
            #             continue
            #         
            #         # Check if this slot is available
            #         alt_availability = self.check_availability(
            #             alt_datetime.strftime('%Y-%m-%d %H:%M'),
            #             service_type=service_type,
            #             duration_hours=duration_hours
            #         )
            #             
            #         if alt_availability.get('available', False):
            #             day_name = alt_datetime.strftime('%A')
            #             time_str = alt_datetime.strftime('%I:%M %p')
            #             date_str = alt_datetime.strftime('%B %d')
            #             
            #             alternatives.append(f"{day_name}, {date_str} at {time_str}")
            #     
            #     if len(alternatives) >= num_alternatives:
            #         break
                    
        except Exception as e:
            print(f"Error getting alternatives: {e}")
        
        return alternatives
    
    def get_daily_schedule(self, date: datetime = None) -> List[Dict[str, Any]]:
        """Get the schedule for a specific day."""
        if not self.api_token:
            return []
        
        if date is None:
            date = datetime.now()
        
        try:
            # Format date for Cal.com API
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Get bookings for the day
            params = {
                'dateFrom': start_of_day.isoformat(),
                'dateTo': end_of_day.isoformat(),
                'status': 'upcoming'
            }
            
            response = self._make_request('GET', '/bookings', params)
            
            if response.status_code != 200:
                print(f"Error getting daily schedule: {response.status_code}")
                return []
            
            bookings = response.json().get('bookings', [])
            
            schedule = []
            for booking in bookings:
                start_time = booking.get('startTime', '')
                end_time = booking.get('endTime', '')
                
                schedule.append({
                    'title': booking.get('title', 'Sports Facility Booking'),
                    'start': start_time,
                    'end': end_time,
                    'description': booking.get('description', ''),
                    'id': booking.get('id'),
                    'attendees': booking.get('attendees', [])
                })
            
            return schedule
            
        except Exception as e:
            print(f"Error getting daily schedule: {e}")
            return []
    
    def get_event_types(self) -> List[Dict[str, Any]]:
        """Get available event types for the facility."""
        if not self.api_token:
            return []
        
        try:
            response = self._make_request('GET', '/event-types')
            
            if response.status_code == 200:
                return response.json().get('event_types', [])
            else:
                print(f"Error getting event types: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"Error getting event types: {e}")
            return []

# Example usage and testing
if __name__ == "__main__":
    calendar_helper = CalcomCalendarHelper()
    
    # Test availability check
    test_datetime = "2025-10-01 15:00"
    availability = calendar_helper.check_availability(test_datetime, "basketball")
    print(f"Availability for {test_datetime}: {availability}")
    
    # Test getting event types
    event_types = calendar_helper.get_event_types()
    print(f"Available event types: {event_types}")
    
    # Test booking creation (commented out to avoid actual bookings)
    # booking_result = calendar_helper.create_booking(
    #     test_datetime, "basketball", "+15551234567", 65.0
    # )
    # print(f"Booking result: {booking_result}")
