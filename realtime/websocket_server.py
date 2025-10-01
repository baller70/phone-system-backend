
"""
WebSocket Server for Phase 8
Real-time communication with dashboard clients
"""

import os
from flask_socketio import SocketIO, emit, join_room, leave_room
from typing import Dict, Any

class WebSocketManager:
    """Manage WebSocket connections and rooms."""
    
    def __init__(self):
        """Initialize WebSocket manager."""
        self.socketio = None
        self.connected_clients = {}
        self.room_members = {}
        print("📡 WebSocket Manager initialized")
    
    def init(self, app):
        """Initialize SocketIO with Flask app."""
        # Use eventlet for production WebSocket support
        async_mode = 'eventlet' if os.getenv('FLASK_ENV') == 'production' else 'threading'
        
        self.socketio = SocketIO(
            app,
            cors_allowed_origins="*",
            async_mode=async_mode,
            logger=False,
            engineio_logger=False
        )
        
        # Register event handlers
        self._register_handlers()
        
        print(f"✅ SocketIO initialized (async_mode={async_mode})")
        return self.socketio
    
    def _register_handlers(self):
        """Register WebSocket event handlers."""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection."""
            client_id = str(id(self.socketio))
            self.connected_clients[client_id] = {
                'connected_at': self._get_timestamp(),
                'rooms': []
            }
            emit('connected', {
                'message': 'Connected to real-time server',
                'timestamp': self._get_timestamp()
            })
            print(f"✅ Client connected: {client_id} (Total: {len(self.connected_clients)})")
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection."""
            client_id = str(id(self.socketio))
            if client_id in self.connected_clients:
                del self.connected_clients[client_id]
            print(f"❌ Client disconnected: {client_id} (Total: {len(self.connected_clients)})")
        
        @self.socketio.on('subscribe')
        def handle_subscribe(data):
            """Handle room subscription."""
            room = data.get('room')
            if room:
                join_room(room)
                
                if room not in self.room_members:
                    self.room_members[room] = []
                
                client_id = str(id(self.socketio))
                self.room_members[room].append(client_id)
                
                emit('subscribed', {
                    'room': room,
                    'message': f'Subscribed to {room}',
                    'timestamp': self._get_timestamp()
                })
                print(f"✅ Client subscribed to room: {room}")
        
        @self.socketio.on('unsubscribe')
        def handle_unsubscribe(data):
            """Handle room unsubscription."""
            room = data.get('room')
            if room:
                leave_room(room)
                
                if room in self.room_members:
                    client_id = str(id(self.socketio))
                    if client_id in self.room_members[room]:
                        self.room_members[room].remove(client_id)
                
                emit('unsubscribed', {
                    'room': room,
                    'message': f'Unsubscribed from {room}',
                    'timestamp': self._get_timestamp()
                })
                print(f"❌ Client unsubscribed from room: {room}")
        
        @self.socketio.on('ping')
        def handle_ping():
            """Handle ping/pong for connection health check."""
            emit('pong', {'timestamp': self._get_timestamp()})
    
    def _get_timestamp(self):
        """Get current timestamp as ISO string."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def emit_to_room(self, room: str, event: str, data: Dict[str, Any]):
        """
        Emit event to all clients in a room.
        
        Args:
            room: Room name
            event: Event name
            data: Event data
        """
        if self.socketio:
            self.socketio.emit(event, data, room=room)
    
    def broadcast(self, event: str, data: Dict[str, Any]):
        """
        Broadcast event to all connected clients.
        
        Args:
            event: Event name
            data: Event data
        """
        if self.socketio:
            self.socketio.emit(event, data, broadcast=True)
    
    def emit_to_client(self, client_id: str, event: str, data: Dict[str, Any]):
        """
        Emit event to specific client.
        
        Args:
            client_id: Client identifier
            event: Event name
            data: Event data
        """
        if self.socketio:
            self.socketio.emit(event, data, room=client_id)
    
    def get_stats(self) -> Dict:
        """Get WebSocket statistics."""
        return {
            'connected_clients': len(self.connected_clients),
            'active_rooms': len(self.room_members),
            'room_details': {
                room: len(members)
                for room, members in self.room_members.items()
            }
        }

# Singleton instance
socket_manager = WebSocketManager()

def init_socketio(app):
    """Initialize SocketIO with Flask app."""
    return socket_manager.init(app)
