
#!/usr/bin/env python3
"""
Comprehensive test suite for the phone system.
Tests all components and identifies issues.
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Import components
from nlu import SportsRentalNLU
from calcom_calendar_helper import CalcomCalendarHelper
from pricing import PricingEngine

print("="*80)
print("COMPREHENSIVE PHONE SYSTEM TEST")
print("="*80)

# Test 1: NLU Testing
print("\n🧠 TEST 1: NLU (Natural Language Understanding)")
print("-"*80)
nlu = SportsRentalNLU()

test_phrases = [
    "I want to book a basketball court for October the 2nd at 3 PM",
    "I want to book a basketball court tomorrow at 3 PM",
    "What are your prices for basketball",
    "Is the court available tomorrow afternoon",
    "Book me a court for 2 hours on Friday",
    "I need a court on Oct 2nd at 3pm",
    "Can I rent a basketball court",
    "What time slots are open tomorrow"
]

nlu_passed = True
for phrase in test_phrases:
    result = nlu.process_speech_input(phrase)
    intent = result.get('intent', 'unknown')
    confidence = result.get('confidence', 0)
    entities = result.get('entities', {})
    
    print(f"\nInput: '{phrase}'")
    print(f"  Intent: {intent} (confidence: {confidence:.2f})")
    print(f"  Entities: {entities}")
    
    if intent == 'unknown' and confidence < 0.5:
        print(f"  ⚠️  WARNING: Low confidence or unknown intent")
        nlu_passed = False
    else:
        print(f"  ✅ OK")

print(f"\nNLU Test Result: {'✅ PASSED' if nlu_passed else '❌ FAILED'}")

# Test 2: Pricing Engine
print("\n💰 TEST 2: PRICING ENGINE")
print("-"*80)
pricing = PricingEngine()

pricing_tests = [
    ('basketball', 1),
    ('basketball', 2),
    ('birthday_party', 3),
    ('volleyball', 1),
]

pricing_passed = True
for service_type, duration in pricing_tests:
    try:
        # Use current time for testing
        test_time = datetime.now() + timedelta(days=1)
        rate = pricing.calculate_hourly_rate(test_time, service_type)
        total = rate * duration
        print(f"\n{service_type.title()} ({duration}h):")
        print(f"  Rate: ${rate}/hour")
        print(f"  Total: ${total}")
        print(f"  ✅ OK")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        pricing_passed = False

print(f"\nPricing Test Result: {'✅ PASSED' if pricing_passed else '❌ FAILED'}")

# Test 3: Cal.com Integration
print("\n📅 TEST 3: CAL.COM INTEGRATION")
print("-"*80)

calcom = CalcomCalendarHelper()

# Check if API token is configured
if not calcom.api_token:
    print("❌ CRITICAL: CALCOM_API_TOKEN not configured!")
    print("   Set this environment variable in Render")
    calcom_passed = False
else:
    print(f"✅ API Token configured")
    calcom_passed = True

# Check if event type ID is configured
if not calcom.event_type_id:
    print("❌ CRITICAL: CALCOM_EVENT_TYPE_ID not configured!")
    print("   Set this environment variable in Render")
    calcom_passed = False
else:
    print(f"✅ Event Type ID: {calcom.event_type_id}")

# Test availability check
if calcom_passed:
    try:
        tomorrow = datetime.now() + timedelta(days=1)
        test_datetime = tomorrow.replace(hour=15, minute=0, second=0, microsecond=0)
        test_datetime_str = test_datetime.strftime('%Y-%m-%d %H:%M')
        
        print(f"\nTesting availability check for: {test_datetime_str}")
        availability = calcom.check_availability(test_datetime_str, duration_hours=1)
        print(f"  Available: {availability['available']}")
        if 'slots' in availability:
            print(f"  Slots found: {len(availability['slots'])}")
        print(f"  ✅ Availability check working")
    except Exception as e:
        print(f"  ❌ Availability check failed: {e}")
        calcom_passed = False

print(f"\nCal.com Test Result: {'✅ PASSED' if calcom_passed else '❌ FAILED'}")

# Test 4: End-to-End Booking Scenario
print("\n🎯 TEST 4: END-TO-END BOOKING SCENARIO")
print("-"*80)

user_input = "I want to book a basketball court for October the 2nd at 3 PM"
print(f"User says: '{user_input}'")

# Step 1: NLU processes input
nlu_result = nlu.process_speech_input(user_input)
print(f"\n1️⃣  NLU Processing:")
print(f"    Intent: {nlu_result['intent']}")
print(f"    Entities: {nlu_result['entities']}")

# Step 2: Extract booking details
intent = nlu_result['intent']
entities = nlu_result['entities']
date_time = entities.get('date_time')
service_type = entities.get('service_type', 'basketball')

print(f"\n2️⃣  Extracted Details:")
print(f"    Service: {service_type}")
print(f"    Date/Time: {date_time}")

e2e_passed = True

if not date_time:
    print(f"    ❌ ERROR: Failed to extract date/time!")
    e2e_passed = False
else:
    # Step 3: Check pricing
    try:
        # Parse date_time for pricing calculation
        booking_datetime = datetime.strptime(date_time, '%Y-%m-%d %H:%M')
        rate = pricing.calculate_hourly_rate(booking_datetime, service_type)
        print(f"\n3️⃣  Pricing:")
        print(f"    Rate: ${rate}/hour")
    except Exception as e:
        print(f"    ❌ ERROR: {e}")
        e2e_passed = False
    
    # Step 4: Check availability (if Cal.com is configured)
    if calcom.api_token:
        try:
            availability = calcom.check_availability(date_time, duration_hours=1)
            print(f"\n4️⃣  Availability:")
            print(f"    Available: {availability['available']}")
        except Exception as e:
            print(f"    ⚠️  Warning: {e}")
            print(f"    (Continuing - might be API issue)")

print(f"\nEnd-to-End Test Result: {'✅ PASSED' if e2e_passed else '❌ FAILED'}")

# Final Summary
print("\n" + "="*80)
print("FINAL SUMMARY")
print("="*80)
all_passed = nlu_passed and pricing_passed and calcom_passed and e2e_passed
print(f"NLU: {'✅ PASSED' if nlu_passed else '❌ FAILED'}")
print(f"Pricing: {'✅ PASSED' if pricing_passed else '❌ FAILED'}")
print(f"Cal.com: {'✅ PASSED' if calcom_passed else '❌ FAILED'}")
print(f"End-to-End: {'✅ PASSED' if e2e_passed else '❌ FAILED'}")
print(f"\nOVERALL: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")

if not all_passed:
    print("\n⚠️  Issues found - will be fixed now...")
    sys.exit(1)
else:
    print("\n✅ System is ready!")
    sys.exit(0)
