
"""
Event Broadcaster for Phase 8
Broadcasts real-time events to dashboard clients
"""

from datetime import datetime
from typing import Dict, Any

class EventBroadcaster:
    """Broadcast events to WebSocket clients."""
    
    def __init__(self, socket_manager):
        """Initialize event broadcaster."""
        self.socket_manager = socket_manager
        print("📢 Event Broadcaster initialized")
    
    def notify_new_booking(self, booking_data: Dict[str, Any]):
        """
        Notify about new booking.
        
        Args:
            booking_data: Booking details
        """
        event_data = {
            'type': 'new_booking',
            'booking': booking_data,
            'timestamp': datetime.now().isoformat()
        }
        
        self.socket_manager.emit_to_room('bookings', 'new_booking', event_data)
        self.socket_manager.emit_to_room('dashboard', 'notification', {
            'title': 'New Booking',
            'message': f"New booking for {booking_data.get('facility_name')}",
            'type': 'success',
            'timestamp': event_data['timestamp']
        })
        
        print(f"📢 Broadcast: new_booking ({booking_data.get('id')})")
    
    def notify_booking_updated(self, booking_data: Dict[str, Any], change_type: str = 'updated'):
        """
        Notify about booking update/cancellation.
        
        Args:
            booking_data: Booking details
            change_type: 'updated' or 'cancelled'
        """
        event_data = {
            'type': f'booking_{change_type}',
            'booking': booking_data,
            'timestamp': datetime.now().isoformat()
        }
        
        self.socket_manager.emit_to_room('bookings', f'booking_{change_type}', event_data)
        
        if change_type == 'cancelled':
            self.socket_manager.emit_to_room('dashboard', 'notification', {
                'title': 'Booking Cancelled',
                'message': f"Booking {booking_data.get('id')} cancelled",
                'type': 'warning',
                'timestamp': event_data['timestamp']
            })
        
        print(f"📢 Broadcast: booking_{change_type} ({booking_data.get('id')})")
    
    def notify_payment_received(self, payment_data: Dict[str, Any]):
        """
        Notify about successful payment.
        
        Args:
            payment_data: Payment details
        """
        event_data = {
            'type': 'payment_received',
            'payment': payment_data,
            'timestamp': datetime.now().isoformat()
        }
        
        self.socket_manager.emit_to_room('payments', 'payment_received', event_data)
        self.socket_manager.emit_to_room('revenue', 'revenue_update', event_data)
        self.socket_manager.emit_to_room('dashboard', 'notification', {
            'title': 'Payment Received',
            'message': f"${payment_data.get('amount', 0):.2f} received",
            'type': 'success',
            'timestamp': event_data['timestamp']
        })
        
        print(f"📢 Broadcast: payment_received (${payment_data.get('amount', 0):.2f})")
    
    def notify_call_started(self, call_data: Dict[str, Any]):
        """
        Notify about incoming call.
        
        Args:
            call_data: Call details
        """
        event_data = {
            'type': 'call_started',
            'call': call_data,
            'timestamp': datetime.now().isoformat()
        }
        
        self.socket_manager.emit_to_room('calls', 'call_started', event_data)
        self.socket_manager.emit_to_room('dashboard', 'notification', {
            'title': 'Incoming Call',
            'message': f"Call from {call_data.get('customer_phone')}",
            'type': 'info',
            'timestamp': event_data['timestamp']
        })
        
        print(f"📢 Broadcast: call_started ({call_data.get('call_id')})")
    
    def notify_call_ended(self, call_data: Dict[str, Any]):
        """
        Notify about completed call.
        
        Args:
            call_data: Call details including analytics
        """
        event_data = {
            'type': 'call_ended',
            'call': call_data,
            'timestamp': datetime.now().isoformat()
        }
        
        self.socket_manager.emit_to_room('calls', 'call_ended', event_data)
        
        # Only notify if booking was successful or if escalated
        if call_data.get('booking_success'):
            self.socket_manager.emit_to_room('dashboard', 'notification', {
                'title': 'Call Completed - Booking Created',
                'message': f"Successful booking from call",
                'type': 'success',
                'timestamp': event_data['timestamp']
            })
        elif call_data.get('escalated'):
            self.socket_manager.emit_to_room('dashboard', 'notification', {
                'title': 'Call Escalated',
                'message': f"Call escalated to human agent",
                'type': 'warning',
                'timestamp': event_data['timestamp']
            })
        
        print(f"📢 Broadcast: call_ended ({call_data.get('call_id')})")
    
    def notify_availability_changed(self, facility_data: Dict[str, Any]):
        """
        Notify about availability changes.
        
        Args:
            facility_data: Facility availability details
        """
        event_data = {
            'type': 'availability_changed',
            'facility': facility_data,
            'timestamp': datetime.now().isoformat()
        }
        
        self.socket_manager.emit_to_room('availability', 'availability_changed', event_data)
        
        # Alert if low availability
        if facility_data.get('available_slots', 100) < 10:
            self.socket_manager.emit_to_room('dashboard', 'alert', {
                'title': 'Low Availability',
                'message': f"{facility_data.get('facility_name')} has low availability",
                'type': 'warning',
                'priority': 'high',
                'timestamp': event_data['timestamp']
            })
        
        print(f"📢 Broadcast: availability_changed ({facility_data.get('facility_name')})")
    
    def send_alert(self, title: str, message: str, alert_type: str = 'info', priority: str = 'normal'):
        """
        Send system alert to dashboard.
        
        Args:
            title: Alert title
            message: Alert message
            alert_type: 'info', 'success', 'warning', 'error'
            priority: 'low', 'normal', 'high', 'urgent'
        """
        alert_data = {
            'title': title,
            'message': message,
            'type': alert_type,
            'priority': priority,
            'timestamp': datetime.now().isoformat()
        }
        
        self.socket_manager.emit_to_room('dashboard', 'alert', alert_data)
        print(f"🚨 Alert: {title} ({alert_type}/{priority})")
    
    def send_metric_update(self, metric_name: str, value: Any, metadata: Dict = None):
        """
        Send real-time metric update.
        
        Args:
            metric_name: Metric name (e.g., 'total_bookings', 'revenue_today')
            value: Metric value
            metadata: Additional metadata
        """
        metric_data = {
            'metric': metric_name,
            'value': value,
            'metadata': metadata or {},
            'timestamp': datetime.now().isoformat()
        }
        
        self.socket_manager.emit_to_room('metrics', 'metric_update', metric_data)
        print(f"📊 Metric update: {metric_name} = {value}")
