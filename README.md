# Automated Phone Answering System for Sports Facility Rental

## Overview
This system provides an automated phone answering solution for a sports facility rental company using Vonage Voice API. It handles incoming calls with speech recognition, natural language understanding, and Google Calendar integration for real-time booking management.

## System Architecture

### Core Components

1. **Flask Webhook Server (app.py)**
   - Handles incoming Vonage Voice API webhooks
   - Routes `/webhooks/answer` for call handling
   - Routes `/webhooks/events` for call status updates
   - Integrates all system components

2. **Natural Language Understanding (nlu.py)**
   - Processes speech-to-text input from callers
   - Identifies caller intent (pricing, availability, booking, etc.)
   - Extracts relevant parameters (date, time, party size)
   - Rule-based system with keyword matching

3. **Calendar Integration (calendar_helper.py)**
   - Google Calendar API integration using service account
   - Real-time availability checking
   - Automated booking creation and management
   - Business hours validation (9am-9pm)

4. **Pricing Engine (pricing.py)**
   - Loads pricing data from CSV files
   - Calculates rates based on time, season, and usage type
   - Supports hourly rentals and birthday party packages
   - Peak/off-peak pricing logic

5. **Escalation Module (escalation.py)**
   - Handles complex scenarios requiring human intervention
   - Payment processing issues
   - Complex booking requests
   - Generates NCCO for agent connection

## Features

- **Speech Recognition**: Vonage ASR with female voice responses
- **Multi-Sport Support**: Basketball court for various sports and parties
- **Dynamic Pricing**: Peak/off-peak rates, seasonal adjustments
- **Real-Time Booking**: Google Calendar integration
- **Human Escalation**: Seamless transfer to agents when needed
- **Business Hours**: Operates 9am-9pm with appropriate messaging

## Business Context

- **Facility**: Basketball court used for multiple sports and birthday parties
- **Operating Hours**: 9am-9pm daily
- **Call Volume**: ~5 calls per day
- **Services**: Hourly rentals, birthday party packages, memberships

## Technical Stack

- **Backend**: Python Flask
- **Voice API**: Vonage Voice API with NCCO
- **Speech Recognition**: Vonage ASR
- **Calendar**: Google Calendar API
- **Data Processing**: Pandas for pricing data
- **Authentication**: Service account for Google APIs

## Setup Instructions

### Prerequisites
- Python 3.11+
- Vonage account with Voice API access
- Google Cloud project with Calendar API enabled
- Virtual phone number from Vonage

### Installation
1. Clone the repository
2. Create virtual environment: `python -m venv venv`
3. Activate environment: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`

### Configuration
1. Copy `.env.example` to `.env`
2. Add Vonage API credentials
3. Add Google service account key file
4. Configure webhook URLs in Vonage dashboard
5. Set up ngrok for local development

### Deployment
1. Configure webhook URLs in Vonage application
2. Deploy to production server
3. Update environment variables
4. Test call flow end-to-end

## Call Flow

1. **Incoming Call**: Vonage sends webhook to `/webhooks/answer`
2. **Greeting**: Female voice welcomes caller
3. **Speech Input**: ASR captures caller's request
4. **Intent Recognition**: NLU processes speech and identifies intent
5. **Response Generation**: System provides appropriate response:
   - Pricing information
   - Availability checking
   - Booking confirmation
   - Human escalation
6. **Follow-up**: Additional questions or booking completion

## Supported Intents

- **Pricing Inquiry**: Hourly rates, party packages, membership options
- **Availability Check**: Real-time calendar availability
- **Booking Request**: Create new reservations
- **General Information**: Hours, location, services
- **Payment Issues**: Escalate to human agent
- **Complex Bookings**: Multi-day events, special requirements

## Development

### Testing
- Unit tests for each module
- Mock Vonage webhooks for testing
- Calendar API testing with test events

### Monitoring
- Call logs and analytics
- Error tracking and alerting
- Performance monitoring

## Security

- Environment variables for sensitive data
- Service account key protection
- Webhook signature verification
- Input validation and sanitization

## Future Enhancements

- AI-powered NLU with OpenAI/Claude
- SMS confirmations and reminders
- Multi-language support
- Advanced analytics dashboard
- CRM integration
