# Instagram Content Automation Agent

A full automation pipeline for fetching images from Google Drive, generating Instagram-ready captions via Gemini Vision, and publishing to Instagram automatically, while logging everything to Google Sheets.

## Features
- Google Drive Integration for polling images
- Gemini Vision for analyzing images and generating tailored captions
- Hashtag Engine combining trending, niche, and branded tags
- Support for Single Posts, Carousels, Stories, and Reels
- Comprehensive logging to a dedicated Google Sheet
- Configurable brand profiles

## Setup Instructions

### 1. Requirements
Ensure you have Python 3.9+ installed.
```shell
pip install -r requirements.txt
```

### 2. Environment Variables
Copy `.env` and fill out your specific credentials:
- `GOOGLE_SERVICE_ACCOUNT_JSON`: The absolute or relative path to your Google Service Account JSON file.
- `GEMINI_API_KEY`: Your Google Gemini API Key.
- `META_APP_ID`: Your Meta App ID for Instagram Graph API.
- `META_APP_SECRET`: Your Meta App Secret.
- `INSTAGRAM_ACCESS_TOKEN`: The long-lived access token for Instagram Graph API.
- `INSTAGRAM_ACCOUNT_ID`: Your Instagram Business Account ID.

Note: Make sure your Google Service Account has access to the Drive folder and is equipped with the `drive.readonly` and `spreadsheets` scopes.

### 3. Adding a Brand Profile
Update `config/brand-profiles.json`. It supports an array of profiles. Adjust `brand_voice`, `branded_hashtags`, and standard values to fine-tune Gemini's content generation.

### 4. Usage
Run the pipeline to test in dry-run mode first:
```shell
python src/main.py --profile "lnlaiagency_main" --dry-run
```

To run a live publish immediately:
```shell
python src/main.py --profile "lnlaiagency_main" --post-now
```

## 🚀 Web App Dashboard (New!)

You can now manage your Instagram Agent through a modern web-based dashboard. 

### 1. Launch the App
Run the unified launch script from the project root:
```shell
python run_web.py
```

### 2. Access the Dashboard
Once running, open your browser to:
- **Dashboard:** [http://localhost:3000](http://localhost:3000)
- **API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

### Features:
- **Real-time Monitoring:** See what's currently in your Google Drive queue.
- **Quota Tracking:** Visual indicators for today's Feed and Story posts.
- **One-Click Publish:** Manual override to run the pipeline instantly.
- **Activity Logs:** View your recent post history directly in the app.
- **Profile Switching:** Seamlessly toggle between different brand identities.
