
"""
Phase 8: Real-Time Communication Module
Handles WebSocket connections and live updates
"""

from .websocket_server import socket_manager, init_socketio
from .event_broadcaster import EventBroadcaster

__all__ = [
    'socket_manager',
    'init_socketio',
    'EventBroadcaster'
]
