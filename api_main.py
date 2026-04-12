import os
import requests
import sys
import subprocess
import json
import logging
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse

# Load variables at the very beginning
load_dotenv()

# Import our existing logic
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))
from drive_reader import DriveReader
from post_scheduler import PostScheduler
from main import load_profile

app = FastAPI(title="Instagram Content Agent API")

# Enable CORS for Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create downloads folder if missing and mount it
os.makedirs("downloads", exist_ok=True)
app.mount("/api/media", StaticFiles(directory="downloads"), name="media")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('api')

class Profile(BaseModel):
    account_id: str
    brand_name: str
    instagram_handle: str
    active: bool
    brand_voice: Optional[str] = None
    aesthetic: Optional[str] = None
    tone_keywords: List[str] = []
    branded_hashtags: List[str] = []
    call_to_action: Optional[str] = None
    drive_folder_id: Optional[str] = None
    drive_account: Optional[str] = None
    post_link: Optional[str] = None
    sheets_log_name: Optional[str] = None
    direct_sheet_id: Optional[str] = None
    overview: Optional[str] = None
    fonts: List[str] = []

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.get("/api/profiles", response_model=List[Profile])
async def get_profiles():
    config_path = os.path.join(BASE_DIR, 'config', 'brand-profiles.json')
    if not os.path.exists(config_path):
        return []
    with open(config_path, 'r', encoding='utf-8') as f:
        profiles = json.load(f)
        return [p for p in profiles]

@app.get("/api/history")
async def get_history():
    history_path = os.path.join(BASE_DIR, 'logs', 'post_history.json')
    if not os.path.exists(history_path):
        return []
    with open(history_path, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)[::-1]
        except:
            return []

@app.get("/api/queue/{profile_id}")
async def get_queue(profile_id: str):
    profile = load_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    reader = DriveReader()
    folder_id = profile.get('drive_folder_id')
    files = reader.fetch_unprocessed_media(folder_id, limit=10)
    return files

@app.get("/api/status/{profile_id}")
async def get_status(profile_id: str):
    scheduler = PostScheduler()
    posted_today = scheduler.get_posted_types_today(profile_id)
    return {
        "posted_today": posted_today,
        "needs_main": 'main' not in posted_today,
        "needs_story": 'story' not in posted_today
    }

@app.post("/api/run/{profile_id}")
async def run_pipeline(profile_id: str, background_tasks: BackgroundTasks):
    logger.info(f"🚀 API: Manual trigger received (Profile: {profile_id})")
    
    def run_script():
        logger.info(f"⚡ [BACKEND] Starting automation for {profile_id}...")
        python_bin = sys.executable
        script_path = os.path.join(os.getcwd(), "src", "main.py")
        cmd = [python_bin, script_path, "--profile", profile_id, "--post-now"]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=os.getcwd()
            )
            
            for line in process.stdout:
                print(f"DEBUG: {line.strip()}", flush=True)
                
            process.wait()
            if process.returncode == 0:
                logger.info(f"✅ [BACKEND] Task Complete for {profile_id}")
            else:
                logger.error(f"❌ [BACKEND] Task Failed (Code: {process.returncode})")
                
        except Exception as e:
            logger.error(f"💀 [BACKEND] Subprocess Crash: {e}")
            
    background_tasks.add_task(run_script)
    return {"status": "ok", "message": "Pipeline started"}

# --- FACEBOOK OAUTH WORKFLOW ---

@app.get("/api/meta/login")
def meta_login():
    """Redirects the user to the Facebook OAuth dialog."""
    app_id = os.getenv("INSTAGRAM_APP_ID")
    base_url = os.getenv('PUBLIC_API_URL', 'https://lnldemos.tech').rstrip('/')
    redirect_uri = f"{base_url}/api/meta/instagram/callback"
    
    # Full list of scopes requested by the user for comprehensive management
    scopes = [
        "instagram_basic",
        "instagram_content_publish",
        "instagram_manage_comments",
        "instagram_manage_insights",
        "pages_show_list",
        "pages_read_engagement",
        "business_management",
        "public_profile"
    ]
    
    # User-provided setup extras for IG API Onboarding
    extras = '{"setup":{"channel":"IG_API_ONBOARDING"}}'
    
    auth_url = (
        f"https://www.facebook.com/v20.0/dialog/oauth?"
        f"client_id={app_id}&"
        f"redirect_uri={redirect_uri}&"
        f"scope={','.join(scopes)}&"
        f"response_type=code&"
        f"display=page&"
        f"extras={extras}"
    )
    return RedirectResponse(auth_url)

@app.get("/api/meta/instagram/callback")
def instagram_callback(code: Optional[str] = None, error: Optional[str] = None):
    """
    Handles the Facebook OAuth callback. 
    Exchanges the 'code' for a short-lived token, then upgrades it to a long-lived 60-day token.
    """
    app_id = os.getenv("INSTAGRAM_APP_ID")
    app_secret = os.getenv("INSTAGRAM_APP_SECRET")
    base_url = os.getenv('PUBLIC_API_URL', 'https://lnldemos.tech').rstrip('/')
    redirect_uri = f"{base_url}/api/meta/instagram/callback"
    
    token_display = "No code received"
    token_status = "error"
    error_detail = error or ""

    if code:
        try:
            # Step 1: Exchange code for short-lived access token
            exchange_url = "https://graph.facebook.com/v20.0/oauth/access_token"
            params = {
                "client_id": app_id,
                "client_secret": app_secret,
                "redirect_uri": redirect_uri,
                "code": code
            }
            res = requests.get(exchange_url, params=params)
            data = res.json()
            
            if "access_token" in data:
                short_token = data["access_token"]
                
                # Step 2: Exchange short-lived token for long-lived access token (60 days)
                ll_url = "https://graph.facebook.com/v20.0/oauth/access_token"
                ll_params = {
                    "grant_type": "fb_exchange_token",
                    "client_id": app_id,
                    "client_secret": app_secret,
                    "fb_exchange_token": short_token
                }
                ll_res = requests.get(ll_url, params=ll_params)
                ll_data = ll_res.json()
                
                if "access_token" in ll_data:
                    token_display = ll_data["access_token"]
                    token_status = "success"
                    logger.info("✅ Long-lived token successfully generated.")
                else:
                    token_display = short_token
                    token_status = "warning"
                    error_detail = ll_data.get("error", {}).get("message", "Long-lived exchange failed")
                    error_raw = json.dumps(ll_data)
                    logger.warning(f"⚠️ Long-lived exchange failed: {error_raw}")
            else:
                token_status = "error"
                # Extract specific error message from Facebook's response
                fb_error = data.get("error", {})
                error_detail = fb_error.get("message", "Token exchange failed")
                error_type = fb_error.get("type", "")
                error_code = fb_error.get("code", "")
                
                error_detail = f"{error_detail} (Type: {error_type}, Code: {error_code})"
                logger.error(f"❌ Token exchange failed: {json.dumps(data)}")
                
        except Exception as e:
            token_status = "error"
            error_detail = str(e)
            logger.error(f"💀 OAuth Callback Exception: {e}")

    # Premium UI for the Token Capture Page
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Meta Connected - LNL AI Agency</title>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
        <style>
            :root {{
                --primary: #0084ff;
                --bg: #030712;
                --card: #0f172a;
                --text: #f8fafc;
                --success: #10b981;
                --error: #ef4444;
                --warning: #f59e0b;
                --border: #1e293b;
            }}
            body {{ 
                font-family: 'Outfit', sans-serif; 
                background: var(--bg); 
                color: var(--text); 
                display: flex; 
                align-items: center; 
                justify-content: center; 
                min-height: 100vh; 
                margin: 0;
                background-image: radial-gradient(circle at top right, rgba(0, 132, 255, 0.1), transparent), 
                                  radial-gradient(circle at bottom left, rgba(147, 51, 234, 0.1), transparent);
            }}
            .card {{ 
                background: var(--card); 
                padding: 3rem; 
                border-radius: 28px; 
                border: 1px solid var(--border); 
                max-width: 550px; 
                width: 90%; 
                text-align: center;
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
                backdrop-filter: blur(12px);
            }}
            .icon-box {{
                width: 70px;
                height: 70px;
                background: linear-gradient(135deg, #0084ff, #9333ea);
                border-radius: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 1.5rem;
                font-weight: 800;
                font-size: 28px;
                box-shadow: 0 0 30px rgba(0, 132, 255, 0.3);
            }}
            h1 {{ 
                font-size: 2rem; 
                margin: 0 0 0.75rem;
                font-weight: 700;
                letter-spacing: -0.02em;
            }}
            p {{ 
                opacity: 0.7; 
                font-size: 1rem;
                line-height: 1.6;
                margin-bottom: 2.5rem;
            }}
            .token-wrapper {{
                text-align: left;
                margin-bottom: 2rem;
            }}
            .label {{
                font-size: 0.7rem;
                font-weight: 700;
                text-transform: uppercase;
                color: var(--primary);
                letter-spacing: 0.1em;
                margin-bottom: 0.75rem;
                display: block;
            }}
            .token-container {{ 
                background: #020617; 
                padding: 1.5rem; 
                border-radius: 16px; 
                border: 1px solid var(--border); 
                word-break: break-all; 
                font-family: 'JetBrains Mono', 'Fira Code', monospace; 
                font-size: 0.9rem; 
                color: { 'var(--success)' if token_status == 'success' else ('var(--warning)' if token_status == 'warning' else 'var(--error)') }; 
                min-height: 60px;
                transition: all 0.3s ease;
                box-shadow: inset 0 2px 4px 0 rgba(0, 0, 0, 0.06);
            }}
            .token-container:hover {{ border-color: var(--primary); }}
            
            .actions {{
                display: flex;
                gap: 1rem;
                justify-content: center;
            }}
            button {{ 
                background: var(--primary); 
                color: white; 
                border: none; 
                padding: 1.1rem 2.2rem; 
                border-radius: 14px; 
                cursor: pointer; 
                font-weight: 700;
                font-size: 0.95rem;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                box-shadow: 0 10px 15px -3px rgba(0, 132, 255, 0.2);
            }}
            button:hover {{ 
                transform: translateY(-2px);
                filter: brightness(1.1);
                box-shadow: 0 20px 25px -5px rgba(0, 132, 255, 0.3);
            }}
            .btn-secondary {{
                background: #1e293b;
                color: #94a3b8;
                box-shadow: none;
            }}
            .btn-secondary:hover {{
                background: #334155;
                color: #f8fafc;
                box-shadow: none;
            }}
            .error-box {{ 
                color: var(--error); 
                font-size: 0.85rem; 
                margin-top: 1.5rem;
                padding: 1.25rem;
                background: rgba(239, 68, 68, 0.08);
                border-radius: 12px;
                border: 1px solid rgba(239, 68, 68, 0.2);
                text-align: left;
            }}
            .status-badge {{
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
                font-size: 0.75rem;
                font-weight: 800;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                padding: 0.4rem 1rem;
                border-radius: 100px;
                margin-bottom: 1.5rem;
                { 'background: rgba(16, 185, 129, 0.1); color: var(--success);' if token_status == 'success' else ('background: rgba(245, 158, 11, 0.1); color: var(--warning);' if token_status == 'warning' else 'background: rgba(239, 68, 68, 0.1); color: var(--error);') }
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="icon-box">LG</div>
            <div class="status-badge">
                {{ '✓ Authorization Verified' if token_status == 'success' else ('! Verification Warning' if token_status == 'warning' else '✕ Connection Failed') }}
            </div>
            <h1>Meta Connected</h1>
            <p>Your Instagram Access Token is ready. Update your <code>INSTAGRAM_ACCESS_TOKEN</code> in the environment config.</p>
            
            <div class="token-wrapper">
                <span class="label">60-Day Long-Lived Access Token</span>
                <div id="token" class="token-container">{token_display}</div>
            </div>

            <div class="actions">
                <button id="copyBtn" onclick="copyToken()">Copy Token</button>
                <button class="btn-secondary" onclick="window.close()">Close</button>
            </div>

            {f'<div class="error-box"><strong>Debug Info:</strong> {error_detail}</div>' if error_detail else ''}
        </div>

        <script>
            function copyToken() {{
                const text = document.getElementById('token').innerText;
                if (!text || text.length < 20) return;
                
                navigator.clipboard.writeText(text).then(() => {{
                    const btn = document.getElementById('copyBtn');
                    const originalText = btn.innerText;
                    btn.innerText = 'Copied!';
                    btn.style.background = '#10b981';
                    btn.style.boxShadow = '0 10px 15px -3px rgba(16, 185, 129, 0.3)';
                    setTimeout(() => {{
                        btn.innerText = originalText;
                        btn.style.background = '#0084ff';
                        btn.style.boxShadow = '0 10px 15px -3px rgba(0, 132, 255, 0.2)';
                    }}, 2000);
                }});
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
