# FutureOracle Deployment Guide

## Streamlit Cloud Deployment (5 minutes)

### Prerequisites
- GitHub account
- Streamlit Cloud account (free at https://streamlit.io/cloud)
- xAI API key (get from https://x.ai)
- NewsAPI key (get from https://newsapi.org)

### Step 1: Fork or Push to Your GitHub

This repo is already on GitHub at `TBSKR/future-oracle`. You can either:
- Deploy directly from this repo (if you have access)
- Fork it to your own account

### Step 2: Sign Up for Streamlit Cloud

1. Go to https://share.streamlit.io
2. Sign in with GitHub
3. Authorize Streamlit to access your repos

### Step 3: Deploy Your App

1. Click "New app" in Streamlit Cloud
2. Select your repository: `TBSKR/future-oracle`
3. Set the main file path: `src/app.py`
4. Click "Advanced settings"

### Step 4: Configure Secrets

In the "Secrets" section, paste this (with your actual keys):

```toml
XAI_API_KEY = "your-xai-api-key-here"
NEWSAPI_KEY = "your-newsapi-key-here"
DISCORD_WEBHOOK_URL = "your-discord-webhook-url-here"
```

### Step 5: Deploy

1. Click "Deploy!"
2. Wait 2-3 minutes for the app to build
3. Your app will be live at `https://[your-app-name].streamlit.app`

### Step 6: Custom Domain (Optional)

To use a custom domain:
1. Go to app settings in Streamlit Cloud
2. Navigate to "General" → "Custom subdomain"
3. Enter your desired subdomain (e.g., `futureoracle`)
4. Your app will be available at `https://futureoracle.streamlit.app`

For a fully custom domain (e.g., `app.yourdomain.com`):
1. Upgrade to Streamlit Cloud Teams plan
2. Add CNAME record in your DNS settings
3. Configure in Streamlit Cloud settings

## Environment Variables

The app reads secrets from Streamlit Cloud's secrets management:
- `XAI_API_KEY` - Required for Grok AI analysis
- `NEWSAPI_KEY` - Required for news scanning
- `DISCORD_WEBHOOK_URL` - Optional for alert notifications

## Troubleshooting

### App won't start
- Check that all required secrets are set
- Verify the main file path is `src/app.py`
- Check the logs in Streamlit Cloud dashboard

### Import errors
- Make sure `requirements.txt` is in the root directory
- All dependencies should install automatically

### Database errors
- The app uses SQLite which works on Streamlit Cloud
- Database file is created automatically in the sandbox

### API errors
- Verify your API keys are valid and active
- Check API rate limits (NewsAPI has daily limits on free tier)
- xAI Grok API requires an active account

## Production Considerations

### Rate Limits
- NewsAPI free tier: 100 requests/day
- xAI Grok: Check your plan limits
- Consider caching strategies for production use

### Database
- Streamlit Cloud uses ephemeral storage
- Database resets on app restart
- For persistent storage, consider:
  - External PostgreSQL (Supabase, Neon)
  - Cloud storage (AWS S3, Google Cloud Storage)

### Monitoring
- Use Streamlit Cloud's built-in analytics
- Set up Discord webhook for critical alerts
- Monitor API usage to avoid rate limits

## Support

For issues:
1. Check Streamlit Cloud logs
2. Review GitHub issues
3. Contact support at https://discuss.streamlit.io
