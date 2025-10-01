# Cal.com Calendar Integration Setup Guide

## 🎉 Why Cal.com is Better Than Google Calendar

**Say goodbye to OAuth complexity!** This integration replaces Google Calendar with Cal.com's much simpler API:

| Feature | Google Calendar | Cal.com API |
|---------|----------------|-------------|
| Authentication | Complex OAuth 2.0 flow | Simple API token |
| Setup Time | 30+ minutes | 5 minutes |
| Credentials Files | Multiple (credentials.json, token.json) | Single API token |
| Token Refresh | Required every hour | Not needed |
| Documentation | Complex | Crystal clear |
| Error Handling | Frequent auth issues | Reliable |

## 🚀 Quick Setup (5 Minutes!)

### Step 1: Create Cal.com Account

1. Visit [cal.com](https://cal.com) and sign up for a **free account**
2. Complete your profile setup
3. Create an event type for your basketball court:
   - Name: "Basketball Court Rental"
   - Duration: 60 minutes
   - Price: Set your hourly rate
   - Availability: Set to your business hours (9 AM - 9 PM)

### Step 2: Generate API Token

1. **Log into your Cal.com account**
2. **Click your profile dropdown** (top right corner)
3. **Select "My Settings"**
4. **Scroll down to find "Developer" section**
5. **Click "API keys"**
6. **Click "+ Add" to create new API key**
7. **Name it**: `Sports Facility Phone System`
8. **Set expiry**: 1 year from now
9. **Click "Create token"**
10. **COPY THE TOKEN IMMEDIATELY** (you can't see it again!)

> 💡 **Pro Tip**: Store the API token securely - you'll need it for configuration!

### Step 3: Configure Your System

1. **Copy your existing `.env` file or create from example:**
   ```bash
   cp .env.example .env
   ```

2. **Edit the `.env` file and add your Cal.com credentials:**
   ```bash
   # Cal.com Calendar Configuration
   CALCOM_API_TOKEN=cal_live_xxxxxxxxxxxxxxxxxxxxxxxx
   CALCOM_BASE_URL=https://api.cal.com/v1
   CALCOM_EVENT_TYPE_ID=123456
   ```

3. **Find your Event Type ID:**
   - Go to your Cal.com dashboard
   - Click on your "Basketball Court Rental" event type
   - Look at the URL: `https://app.cal.com/event-types/123456`
   - The number at the end is your Event Type ID

### Step 4: Test the Integration

1. **Install required dependencies** (if not already installed):
   ```bash
   pip install requests
   ```

2. **Test the connection:**
   ```bash
   cd /path/to/your/phone/system
   python calcom_calendar_helper.py
   ```

   You should see:
   ```
   ✅ Cal.com API connected successfully for user: your@email.com
   ```

3. **Start your phone system:**
   ```bash
   python app.py
   ```

## 🎯 Event Type Setup Best Practices

### Creating Basketball Court Event Type

1. **Go to Event Types** in your Cal.com dashboard
2. **Click "New Event Type"**
3. **Configure as follows:**

| Setting | Value |
|---------|--------|
| **Event Name** | Basketball Court Rental |
| **URL Slug** | basketball-court |
| **Duration** | 60 minutes |
| **Event Type** | One-on-One |
| **Locations** | Your facility address |
| **Price** | Your hourly rate (e.g., $65) |
| **Availability** | 9:00 AM - 9:00 PM daily |
| **Buffer Time** | 15 minutes before/after |
| **Max Events Per Day** | 10 |

4. **Advanced Settings:**
   - ✅ Enable "Require confirmation"
   - ✅ Enable "Collect phone number"
   - ✅ Enable "Send SMS notifications"
   - ✅ Enable "Require payment upfront" (optional)

### Additional Event Types (Optional)

Create separate event types for different services:

- **Birthday Parties** (2-3 hour duration)
- **Multi-Sport Activities** (90 minutes)
- **Team Practice** (2 hours)

## 🔧 Configuration Reference

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `CALCOM_API_TOKEN` | Your Cal.com API token | `cal_live_abc123...` |
| `CALCOM_BASE_URL` | Cal.com API base URL | `https://api.cal.com/v1` |
| `CALCOM_EVENT_TYPE_ID` | Basketball court event type ID | `123456` |

### Finding Your Event Type ID

**Method 1: From URL**
1. Go to Cal.com dashboard
2. Click on your event type
3. Copy ID from URL: `https://app.cal.com/event-types/[ID]`

**Method 2: API Call**
```bash
curl -X GET \
  "https://api.cal.com/v1/event-types" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

## 🔍 Testing & Troubleshooting

### Test API Connection

```python
from calcom_calendar_helper import CalcomCalendarHelper

# Initialize helper
calendar = CalcomCalendarHelper()

# Test availability check
result = calendar.check_availability("2025-10-01 15:00", "basketball")
print("Availability:", result)

# Test booking creation (with test data)
booking = calendar.create_booking(
    "2025-10-01 15:00", 
    "basketball", 
    "+15551234567", 
    65.0,
    customer_name="Test Customer"
)
print("Booking:", booking)
```

### Common Issues & Solutions

#### ❌ "Cal.com API token not found"

**Problem**: Environment variable not set correctly

**Solution**: 
1. Check your `.env` file exists in the project root
2. Verify `CALCOM_API_TOKEN` is set correctly
3. Restart your application after changing `.env`

#### ❌ "API connection issue: 401"

**Problem**: Invalid or expired API token

**Solution**:
1. Generate a new API token in Cal.com settings
2. Update your `.env` file
3. Make sure token starts with `cal_live_` or `cal_test_`

#### ❌ "Event type not found"

**Problem**: Wrong Event Type ID

**Solution**:
1. Go to your Cal.com dashboard
2. Click on your basketball court event type
3. Copy the correct ID from the URL
4. Update `CALCOM_EVENT_TYPE_ID` in `.env`

#### ❌ "No available slots"

**Problem**: Event type availability not configured

**Solution**:
1. Go to your event type settings
2. Set availability hours (9 AM - 9 PM)
3. Enable the event type
4. Check for date-specific overrides

## 📊 Monitoring & Logs

### Check System Health

Your phone system now includes improved logging:

```python
# The CalcomCalendarHelper logs all API interactions
# Check your console output for:
✅ Cal.com API connected successfully for user: your@email.com
⚠️ Cal.com API connection issue: 429 (rate limit)
❌ Cal.com API connection failed: Invalid token
```

### API Rate Limits

Cal.com has reasonable rate limits:
- **Free Plan**: 100 requests/hour
- **Pro Plan**: 1,000 requests/hour
- **Enterprise**: Custom limits

For a typical phone system, free plan is usually sufficient!

## 🚀 Advanced Features

### Multiple Event Types

You can easily support different services by creating multiple event types:

```python
# In your .env file:
CALCOM_BASKETBALL_EVENT_TYPE_ID=123456
CALCOM_BIRTHDAY_EVENT_TYPE_ID=789012
CALCOM_MULTISPORT_EVENT_TYPE_ID=345678

# In your code:
event_type_map = {
    'basketball': os.getenv('CALCOM_BASKETBALL_EVENT_TYPE_ID'),
    'birthday_party': os.getenv('CALCOM_BIRTHDAY_EVENT_TYPE_ID'),
    'multi_sport': os.getenv('CALCOM_MULTISPORT_EVENT_TYPE_ID')
}
```

### Webhook Integration

Cal.com supports webhooks for real-time updates:

1. Go to your Cal.com account settings
2. Navigate to "Webhooks"
3. Add webhook URL: `https://your-domain.com/calcom-webhook`
4. Select events: booking created, cancelled, rescheduled

### Payment Integration

Cal.com integrates with Stripe automatically:

1. Connect your Stripe account in Cal.com settings
2. Set prices on your event types
3. Enable "Require payment upfront"
4. Payments are processed automatically!

## 🔄 Migration from Google Calendar

### What Changes

- ✅ **Authentication**: Much simpler (just API token)
- ✅ **Setup**: 5 minutes vs 30+ minutes
- ✅ **Reliability**: Better uptime and fewer auth errors
- ✅ **Features**: Built-in booking system features

### What Stays the Same

- ✅ **Your phone system code**: No changes needed!
- ✅ **Customer experience**: Same booking flow
- ✅ **All functionality**: Availability, bookings, alternatives

### Migration Steps

1. **Keep Google Calendar running** (for safety)
2. **Set up Cal.com** following this guide
3. **Test thoroughly** with the test scripts
4. **Switch environment variables** to Cal.com
5. **Monitor for a few days**
6. **Deactivate Google Calendar** once confident

## 💡 Best Practices

### Security

- 🔒 **Never commit** API tokens to git
- 🔒 **Use environment variables** for all secrets
- 🔒 **Regenerate tokens** annually
- 🔒 **Monitor API usage** for unusual activity

### Performance

- ⚡ **Cache availability** for frequently requested times
- ⚡ **Use batch requests** when possible
- ⚡ **Implement retry logic** for API failures
- ⚡ **Monitor response times** and optimize

### User Experience

- 📱 **Send SMS confirmations** for bookings
- 📱 **Include booking URLs** in confirmations
- 📱 **Allow easy rescheduling** via Cal.com links
- 📱 **Collect customer feedback** on booking experience

## 📞 Support

### Cal.com Support

- **Documentation**: [cal.com/docs](https://cal.com/docs)
- **Community**: [Discord](https://discord.com/invite/gfcVXqN4G9) 
- **Email**: support@cal.com

### Phone System Support

- **Check logs** first for error details
- **Test API connection** using provided scripts
- **Verify environment variables** are set correctly
- **Review this guide** for common solutions

---

**🎉 Congratulations!** You've successfully replaced complex Google Calendar OAuth with simple Cal.com API integration. Your phone system is now easier to maintain and more reliable!

---

*Last updated: December 2024*  
*Cal.com API Version: v1*
