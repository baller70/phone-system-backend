
# 🚀 Deploy to Railway in 3 Clicks

## What You'll Get:
- ✅ Permanent public HTTPS URL (like `https://your-app.up.railway.app`)
- ✅ Automatic SSL certificate
- ✅ Free tier (no credit card needed)
- ✅ Auto-restarts if it crashes

## The 3 Steps:

### Step 1: Login to Railway (1 click)
1. Go to https://railway.app
2. Click "Login with GitHub" (or Google)
3. That's it - you're logged in!

### Step 2: Deploy (1 click)
1. Click "New Project"
2. Select "Deploy from GitHub repo"
3. Choose the `auto_call_system` repository
4. Railway automatically detects everything - just click "Deploy"!

### Step 3: Get Your URL (1 click)
1. After deployment finishes (takes 2-3 minutes)
2. Click "Settings" → "Generate Domain"
3. Copy your new URL: `https://your-app-XXXX.up.railway.app`

## What to Do With Your New URL:

Go back to your **Vonage Dashboard** and fill in:

**Answer URL:**
```
https://your-app-XXXX.up.railway.app/webhooks/answer
```

**Event URL:**
```
https://your-app-XXXX.up.railway.app/webhooks/events
```

**That's it!** Your phone system is now live! 📞

---

## Important: Environment Variables

After deploying, you need to add your environment variables in Railway:

1. In Railway dashboard, click on your project
2. Go to "Variables" tab
3. Click "Raw Editor" and paste this:

```
VONAGE_API_KEY=f24f827b
VONAGE_API_SECRET=caN7axYnDKyPMW0MxPCZTvIDWH3fdrQgaNm18HBaNReEBSUKox
VONAGE_APPLICATION_ID=5f33f5f3-8898-4675-ad58-7823db96a34d
VONAGE_PHONE_NUMBER=+12014096125
STAFF_PHONE_NUMBER=+19177969730
CALCOM_API_TOKEN=cal_live_2d623ed4ea05f1cc11dc278d19cf2430
CALCOM_BASE_URL=https://api.cal.com/v1
CALCOM_EVENT_TYPE_ID=your_event_type_id_here
FLASK_ENV=production
FACILITY_TIMEZONE=America/New_York
BUSINESS_HOURS_START=9
BUSINESS_HOURS_END=21
```

4. Click "Save"
5. Railway will automatically restart with your credentials

---

## Troubleshooting:

**Q: What about the private key?**
A: You'll need to add it as a variable. After downloading from Vonage:
1. Open the private.key file in a text editor
2. Copy all the contents
3. In Railway Variables, add:
   - Key: `VONAGE_PRIVATE_KEY`
   - Value: (paste the entire key content)

**Q: How do I check if it's working?**
A: Visit `https://your-app-XXXX.up.railway.app/health` - you should see:
```json
{"status":"healthy","timestamp":"..."}
```

**Q: How much does Railway cost?**
A: Free tier includes:
- $5 of usage per month (usually enough for development)
- 500 hours of execution time
- Perfect for testing and small projects

---

## Need Help?

If anything goes wrong, check the Railway logs:
1. Click on your project
2. Go to "Deployments" tab
3. Click on the latest deployment
4. View logs to see any errors
