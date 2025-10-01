
"""
Communication Module - Phase 6
Handles email services and rebooking campaigns
"""

from .email_service import EmailService
from .rebooking_service import RebookingService

__all__ = [
    'EmailService',
    'RebookingService'
]
