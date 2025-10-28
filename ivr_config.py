
"""
IVR Configuration Module
Fetches IVR settings from the dashboard API dynamically
"""

import os
import requests
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# Dashboard URL from environment
DASHBOARD_URL = os.environ.get('DASHBOARD_URL', 'https://phone-system-dashboa-8em0c9.abacusai.app')

# Cache for IVR settings (optional, to reduce API calls)
_ivr_cache = {
    'settings': None,
    'timestamp': 0
}

CACHE_TTL = 300  # Cache for 5 minutes

def fetch_ivr_settings() -> Optional[Dict]:
    """
    Fetch IVR settings from the dashboard API.
    Returns the settings dict or None if fetch fails.
    """
    try:
        # Check cache first
        import time
        current_time = time.time()
        if _ivr_cache['settings'] and (current_time - _ivr_cache['timestamp']) < CACHE_TTL:
            print(f"[IVR CONFIG] Using cached IVR settings (age: {int(current_time - _ivr_cache['timestamp'])}s)")
            logger.info("Using cached IVR settings")
            return _ivr_cache['settings']
        
        # Fetch from API (using public endpoint)
        url = f"{DASHBOARD_URL}/api/public/ivr-settings"
        print(f"[IVR CONFIG] Fetching IVR settings from {url}")
        logger.info(f"Fetching IVR settings from {url}")
        
        # Add API key header if available (optional for security)
        headers = {}
        api_key = os.environ.get('BACKEND_API_KEY')
        if api_key:
            headers['x-api-key'] = api_key
        
        # REDUCED TIMEOUT: 2 seconds instead of 5 to avoid blocking
        response = requests.get(url, headers=headers, timeout=2)
        
        if response.status_code == 200:
            settings = response.json()
            
            print(f"[IVR CONFIG] ✓ Successfully fetched {len(settings.get('menuOptions', []))} menu options from dashboard")
            
            # Update cache
            _ivr_cache['settings'] = settings
            _ivr_cache['timestamp'] = current_time
            
            logger.info("Successfully fetched IVR settings from dashboard")
            return settings
        else:
            print(f"[IVR CONFIG] ✗ Failed to fetch IVR settings: HTTP {response.status_code}")
            logger.error(f"Failed to fetch IVR settings: {response.status_code}")
            return None
            
    except requests.exceptions.Timeout as e:
        print(f"[IVR CONFIG] ✗ Dashboard API timeout after 2s: {str(e)}")
        logger.error(f"Dashboard API timeout: {str(e)}")
        return None
    except Exception as e:
        print(f"[IVR CONFIG] ✗ Error fetching IVR settings: {str(e)}")
        logger.error(f"Error fetching IVR settings: {str(e)}")
        return None


def get_default_ivr_settings() -> Dict:
    """
    Return default IVR settings as fallback.
    """
    return {
        'greetingText': 'Thank you for calling Premier Sports Facility! Please listen carefully to the following options.',
        'voiceName': 'Amy',
        'timeoutSeconds': 10,
        'invalidOptionMessage': "I'm sorry, that's not a valid option.",
        'replayMessage': "I didn't catch that.",
        'useAudioGreeting': False,
        'greetingAudioUrl': None,
        'menuOptions': [
            {
                'keyPress': '1',
                'optionName': 'Basketball Court Rentals',
                'optionText': 'Press 1 for basketball court rentals.',
                'departmentGreeting': 'Great choice! I can help you book a basketball court. What date and time would you like to reserve?',
                'aiContext': 'Customer is interested in basketball court rentals. Help them with pricing, availability, and booking.',
                'intentType': 'basketball_rental',
                'orderIndex': 1,
                'isActive': True,
            },
            {
                'keyPress': '2',
                'optionName': 'Birthday Party Packages',
                'optionText': 'Press 2 for birthday party packages.',
                'departmentGreeting': 'Perfect! Let me help you plan an amazing birthday party. How many guests are you expecting?',
                'aiContext': 'Customer wants to book a birthday party package. Help them with package options, pricing, dates, and special requests.',
                'intentType': 'party_booking',
                'orderIndex': 2,
                'isActive': True,
            },
            {
                'keyPress': '3',
                'optionName': 'Multi-Sport Activities',
                'optionText': 'Press 3 for multi-sport activities like volleyball or dodgeball.',
                'departmentGreeting': 'Awesome! I can help you with volleyball, dodgeball, and other sports activities. What sport are you interested in?',
                'aiContext': 'Customer is interested in multi-sport activities. Help with availability and booking.',
                'intentType': 'multi_sport',
                'orderIndex': 3,
                'isActive': True,
            },
            {
                'keyPress': '4',
                'optionName': 'Corporate Events & Leagues',
                'optionText': 'Press 4 for corporate events and leagues.',
                'departmentGreeting': 'Excellent! I can assist you with corporate events, team building, and league information. What type of event are you planning?',
                'aiContext': 'Customer wants information about corporate events, team building, or league registration.',
                'intentType': 'corporate_events',
                'orderIndex': 4,
                'isActive': True,
            },
            {
                'keyPress': '9',
                'optionName': 'AI Assistant',
                'optionText': 'Press 9 to speak with our AI assistant.',
                'departmentGreeting': "Hi! I'm your AI assistant. How can I help you today?",
                'aiContext': 'Customer chose to speak directly with AI assistant. Handle any inquiry.',
                'intentType': 'general_inquiry',
                'orderIndex': 5,
                'isActive': True,
            },
            {
                'keyPress': '0',
                'optionName': 'Live Operator',
                'optionText': 'Or press 0 to speak with a representative.',
                'departmentGreeting': 'Please hold while I transfer you to a representative.',
                'aiContext': 'Customer wants to speak with a live operator.',
                'intentType': 'transfer',
                'orderIndex': 6,
                'isActive': True,
                'actionType': 'transfer',
            },
        ]
    }


def get_ivr_settings() -> Dict:
    """
    Get IVR settings from dashboard or return defaults.
    """
    settings = fetch_ivr_settings()
    
    if settings:
        return settings
    else:
        logger.warning("Using default IVR settings")
        return get_default_ivr_settings()


def get_menu_option_by_key(key: str) -> Optional[Dict]:
    """
    Get a specific menu option by key press.
    """
    settings = get_ivr_settings()
    
    # Ensure key is a string for comparison
    key = str(key).strip()
    
    print(f"[IVR CONFIG] Looking for menu option with key: '{key}'")
    logger.info(f"Looking for menu option with key: '{key}'")
    
    for option in settings.get('menuOptions', []):
        option_key = str(option.get('keyPress', '')).strip()
        is_active = option.get('isActive', True)
        
        print(f"[IVR CONFIG] Comparing key '{key}' with option key '{option_key}', active: {is_active}, match: {option_key == key}")
        logger.info(f"Comparing key '{key}' with option key '{option_key}', active: {is_active}, match: {option_key == key}")
        
        if option_key == key and is_active:
            print(f"[IVR CONFIG] ✓ Found matching option: {option.get('optionName')}")
            logger.info(f"Found matching option: {option.get('optionName')}")
            return option
    
    print(f"[IVR CONFIG] ✗ No matching menu option found for key: '{key}'")
    logger.warning(f"No matching menu option found for key: '{key}'")
    return None


def build_menu_text(settings: Dict) -> str:
    """
    Build the menu text from active menu options.
    """
    menu_options = settings.get('menuOptions', [])
    active_options = [opt for opt in menu_options if opt.get('isActive', True)]
    active_options.sort(key=lambda x: x.get('orderIndex', 0))
    
    menu_text = "Please listen carefully to the following options. "
    
    for option in active_options:
        menu_text += option.get('optionText', '') + " "
    
    return menu_text


def clear_ivr_cache():
    """
    Clear the IVR settings cache.
    Useful for testing or forcing a refresh.
    """
    global _ivr_cache
    _ivr_cache = {
        'settings': None,
        'timestamp': 0
    }
    logger.info("IVR cache cleared")
