#!/usr/bin/env python3
"""
Migration script to help transition from Google Calendar to Cal.com API.
This script validates your Cal.com setup and provides step-by-step guidance.
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def print_banner():
    """Print a nice banner for the migration script."""
    print("=" * 60)
    print("🚀 GOOGLE CALENDAR → CAL.COM MIGRATION SCRIPT")
    print("=" * 60)
    print("This script will help you migrate from complex Google Calendar")
    print("OAuth to simple Cal.com API integration.")
    print()

def check_google_calendar_setup():
    """Check current Google Calendar configuration."""
    print("📋 Checking current Google Calendar setup...")
    
    issues = []
    
    # Check for Google Calendar environment variables
    google_calendar_id = os.getenv('GOOGLE_CALENDAR_ID')
    google_creds_path = os.getenv('GOOGLE_CREDENTIALS_PATH')
    google_token_path = os.getenv('GOOGLE_TOKEN_PATH')
    
    if not google_calendar_id:
        issues.append("❌ GOOGLE_CALENDAR_ID not set")
    else:
        print(f"✅ GOOGLE_CALENDAR_ID: {google_calendar_id}")
    
    if not google_creds_path:
        issues.append("❌ GOOGLE_CREDENTIALS_PATH not set")
    else:
        if os.path.exists(google_creds_path):
            print(f"✅ GOOGLE_CREDENTIALS_PATH: {google_creds_path} (exists)")
        else:
            issues.append(f"❌ Credentials file not found: {google_creds_path}")
    
    if not google_token_path:
        issues.append("❌ GOOGLE_TOKEN_PATH not set")
    else:
        if os.path.exists(google_token_path):
            print(f"✅ GOOGLE_TOKEN_PATH: {google_token_path} (exists)")
        else:
            issues.append(f"⚠️ Token file not found: {google_token_path} (will be created)")
    
    # Try to import and test Google Calendar
    try:
        from calendar_helper import CalendarHelper
        
        print("✅ Google Calendar helper can be imported")
        
        # Try to initialize (but don't fail if it doesn't work)
        try:
            gc = CalendarHelper()
            if gc.service:
                print("✅ Google Calendar service initialized successfully")
            else:
                issues.append("⚠️ Google Calendar service failed to initialize")
        except Exception as e:
            issues.append(f"⚠️ Google Calendar initialization error: {e}")
            
    except ImportError as e:
        issues.append(f"❌ Cannot import Google Calendar helper: {e}")
    
    print()
    
    if issues:
        print("🔍 Google Calendar Issues Found:")
        for issue in issues:
            print(f"  {issue}")
        print()
        return False
    else:
        print("✅ Google Calendar setup looks good!")
        print()
        return True

def check_calcom_setup():
    """Check Cal.com configuration."""
    print("📋 Checking Cal.com setup...")
    
    issues = []
    warnings = []
    
    # Check environment variables
    api_token = os.getenv('CALCOM_API_TOKEN')
    base_url = os.getenv('CALCOM_BASE_URL', 'https://api.cal.com/v1')
    event_type_id = os.getenv('CALCOM_EVENT_TYPE_ID')
    
    if not api_token:
        issues.append("❌ CALCOM_API_TOKEN not set")
        print("❌ CALCOM_API_TOKEN: Not set")
    else:
        # Mask the token for security
        masked_token = api_token[:12] + "..." + api_token[-4:] if len(api_token) > 16 else "***"
        print(f"✅ CALCOM_API_TOKEN: {masked_token}")
        
        if not api_token.startswith(('cal_live_', 'cal_test_')):
            warnings.append("⚠️ API token doesn't start with 'cal_live_' or 'cal_test_'")
    
    print(f"✅ CALCOM_BASE_URL: {base_url}")
    
    if not event_type_id:
        warnings.append("⚠️ CALCOM_EVENT_TYPE_ID not set (will use default)")
        print("⚠️ CALCOM_EVENT_TYPE_ID: Not set (will use default)")
    else:
        print(f"✅ CALCOM_EVENT_TYPE_ID: {event_type_id}")
    
    # Try to import and test Cal.com integration
    try:
        from calcom_calendar_helper import CalcomCalendarHelper
        print("✅ Cal.com calendar helper can be imported")
        
        if api_token:
            try:
                cc = CalcomCalendarHelper()
                # The helper tests connection in __init__
                print("✅ Cal.com calendar helper initialized")
            except Exception as e:
                issues.append(f"❌ Cal.com initialization error: {e}")
        else:
            warnings.append("⚠️ Cannot test Cal.com connection without API token")
            
    except ImportError as e:
        issues.append(f"❌ Cannot import Cal.com helper: {e}")
    
    print()
    
    if issues:
        print("🔍 Cal.com Issues Found:")
        for issue in issues:
            print(f"  {issue}")
        print()
        return False
    
    if warnings:
        print("⚠️ Cal.com Warnings:")
        for warning in warnings:
            print(f"  {warning}")
        print()
    
    print("✅ Cal.com setup looks good!")
    print()
    return True

def test_calcom_functionality():
    """Test Cal.com API functionality."""
    print("🧪 Testing Cal.com functionality...")
    
    try:
        from calcom_calendar_helper import CalcomCalendarHelper
        
        calendar = CalcomCalendarHelper()
        
        if not calendar.api_token:
            print("❌ Cannot test without API token")
            return False
        
        # Test 1: Get event types
        print("  📅 Testing: Get event types...")
        try:
            event_types = calendar.get_event_types()
            print(f"    ✅ Found {len(event_types)} event types")
        except Exception as e:
            print(f"    ❌ Error getting event types: {e}")
        
        # Test 2: Check availability for tomorrow
        print("  🔍 Testing: Check availability...")
        try:
            tomorrow = datetime.now() + timedelta(days=1)
            test_time = tomorrow.replace(hour=15, minute=0, second=0, microsecond=0)
            test_time_str = test_time.strftime('%Y-%m-%d %H:%M')
            
            availability = calendar.check_availability(test_time_str, "basketball")
            
            if availability.get('available'):
                print(f"    ✅ Availability check works - slot is available")
            else:
                reason = availability.get('reason', 'Unknown')
                print(f"    ✅ Availability check works - slot not available: {reason}")
                
        except Exception as e:
            print(f"    ❌ Error checking availability: {e}")
        
        # Test 3: Get daily schedule
        print("  📋 Testing: Get daily schedule...")
        try:
            schedule = calendar.get_daily_schedule()
            print(f"    ✅ Daily schedule retrieved - {len(schedule)} bookings today")
        except Exception as e:
            print(f"    ❌ Error getting daily schedule: {e}")
        
        print("✅ Cal.com functionality tests completed!")
        print()
        return True
        
    except Exception as e:
        print(f"❌ Error during functionality tests: {e}")
        return False

def provide_migration_steps():
    """Provide step-by-step migration instructions."""
    print("📋 MIGRATION STEPS")
    print("=" * 30)
    
    steps = [
        "1. Set up Cal.com account (if not done yet)",
        "   → Visit cal.com and create free account",
        "   → Create 'Basketball Court Rental' event type",
        "   → Set duration to 60 minutes, price to your rate",
        "",
        "2. Generate Cal.com API token",
        "   → Go to Settings → Developer → API keys",
        "   → Click '+ Add' to create new token",
        "   → Copy token immediately (you can't see it again!)",
        "",
        "3. Update your .env file",
        "   → Add CALCOM_API_TOKEN=your_token_here",
        "   → Add CALCOM_EVENT_TYPE_ID=your_event_type_id",
        "   → Keep Google Calendar settings for now (backup)",
        "",
        "4. Test the new integration",
        "   → Run this script again to verify setup",
        "   → Test booking via phone system",
        "   → Verify bookings appear in Cal.com dashboard",
        "",
        "5. Switch to Cal.com (when ready)",
        "   → Update main app to use CalcomCalendarHelper",
        "   → Monitor for a few days",
        "   → Remove Google Calendar dependencies",
        "",
        "6. Clean up (optional)",
        "   → Comment out Google Calendar env vars in .env",
        "   → Remove Google credential files",
        "   → Uninstall Google API packages"
    ]
    
    for step in steps:
        print(step)
    
    print("\n📖 For detailed instructions, see:")
    print("   → docs/CALCOM_SETUP_GUIDE.md")
    print()

def main():
    """Main migration script."""
    print_banner()
    
    # Step 1: Check current Google Calendar setup
    google_ok = check_google_calendar_setup()
    
    # Step 2: Check Cal.com setup
    calcom_ok = check_calcom_setup()
    
    # Step 3: If Cal.com is configured, test functionality
    if calcom_ok:
        test_calcom_functionality()
    
    # Step 4: Provide recommendations
    print("💡 RECOMMENDATIONS")
    print("=" * 20)
    
    if not calcom_ok:
        print("🔧 You need to set up Cal.com first:")
        print("   1. Create Cal.com account at cal.com")
        print("   2. Generate API token in account settings")
        print("   3. Add CALCOM_API_TOKEN to your .env file")
        print("   4. Run this script again to verify setup")
        print()
        print("📖 See docs/CALCOM_SETUP_GUIDE.md for detailed instructions")
    
    elif not google_ok:
        print("✅ Cal.com is ready! Google Calendar has issues anyway.")
        print("🚀 You can start using Cal.com immediately:")
        print("   → Your phone system will use CalcomCalendarHelper")
        print("   → No complex OAuth setup needed")
        print("   → More reliable than Google Calendar")
    
    else:
        print("⚖️ Both systems are working. Migration options:")
        print()
        print("🔄 SAFE MIGRATION (Recommended):")
        print("   1. Keep both systems running")
        print("   2. Test Cal.com thoroughly")
        print("   3. Switch when confident")
        print("   4. Keep Google Calendar as backup")
        print()
        print("⚡ IMMEDIATE SWITCH:")
        print("   1. Update import in app.py to use CalcomCalendarHelper")
        print("   2. Restart your phone system")
        print("   3. Monitor carefully")
        print("   4. Rollback if issues arise")
    
    print()
    print("🎉 Ready for a simpler calendar integration?")
    print("   Cal.com API is much easier than Google Calendar OAuth!")
    
    # Final status
    print("\n" + "=" * 60)
    if calcom_ok:
        print("✅ STATUS: Ready to use Cal.com!")
    else:
        print("⚠️ STATUS: Cal.com setup needed")
    
    print("📞 Need help? Check docs/CALCOM_SETUP_GUIDE.md")
    print("=" * 60)

if __name__ == "__main__":
    main()
