# 🚀 Deploy to Railway - Click-by-Click Guide

Your code is **100% ready** to deploy! Here's exactly what to do:

## Method 1: Deploy via Railway Dashboard (Easiest!)

### Step 1: Push Code to GitHub (1 minute)
```bash
cd /home/ubuntu/github_repos/auto_call_system
git add .
git commit -m "Ready for Railway deployment"
# Push to your GitHub repo
```

### Step 2: Deploy from GitHub (2 clicks)
1. Go to https://railway.app/new
2. Click "Deploy from GitHub repo"
3. Select your `auto_call_system` repository  
4. Railway will automatically:
   - Detect Python
   - Install dependencies
   - Deploy your app
   - Give you a URL!

### Step 3: Add Environment Variables
In Railway dashboard:
1. Click on your deployed service
2. Go to "Variables" tab
3. Add these variables:

```
VONAGE_API_KEY=f24f827b
VONAGE_API_SECRET=caN7axYnDKyPMW0MxPCZTvIDWH3fdrQgaNm18HBaNReEBSUKox
VONAGE_APPLICATION_ID=5f33f5f3-8898-4675-ad58-7823db96a34d
VONAGE_PHONE_NUMBER=+19095779171
STAFF_PHONE_NUMBER=+19177969730
CALCOM_API_TOKEN=cal_live_2d623ed4ea05f1cc11dc278d19cf2430
CALCOM_BASE_URL=https://api.cal.com/v1
FACILITY_TIMEZONE=America/New_York
BUSINESS_HOURS_START=9
BUSINESS_HOURS_END=21
FLASK_ENV=production
```

### Step 4: Generate Domain
1. Go to "Settings" tab
2. Click "Generate Domain"
3. Copy your URL: `https://your-app.up.railway.app`

**DONE!** 🎉

---

## Method 2: Deploy via CLI (if you have git configured)

```bash
cd /home/ubuntu/github_repos/auto_call_system
railway login
railway init
railway up
```

---

## Your URL Format:
After deployment, your webhook URLs will be:

**Answer URL:**
```
https://your-app.up.railway.app/webhooks/answer
```

**Event URL:**
```
https://your-app.up.railway.app/webhooks/events
```

Paste these into your Vonage Dashboard!
