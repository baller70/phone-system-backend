
"""
Booking Intelligence Module - Phase 6
Handles recurring bookings, group bookings, waitlist, and smart availability
"""

from .recurring_bookings import RecurringBookingManager
from .group_bookings import GroupBookingManager
from .waitlist import WaitlistManager
from .availability_engine import AvailabilityEngine

__all__ = [
    'RecurringBookingManager',
    'GroupBookingManager',
    'WaitlistManager',
    'AvailabilityEngine'
]
