import os
import json
import logging
import argparse
from datetime import datetime, timedelta
import sys
import google.generativeai as genai
from dotenv import load_dotenv

# Add current folder to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from main import load_profile

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('generate_schedule')

load_dotenv()

class ScheduleGenerator:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            # Fallback search in the other project if needed
            seo_env = "/Users/lainie/Documents/lnl-agency-content-briefs/lnl-seo-agent/.env"
            if os.path.exists(seo_env):
                with open(seo_env, "r") as f:
                    for line in f:
                        if line.startswith("GEMINI_API_KEY="):
                            self.api_key = line.strip().split("=")[1]
                            break
        if self.api_key:
            genai.configure(api_key=self.api_key)
        else:
            logger.error("GEMINI_API_KEY is missing from environment variables.")
        self.model_name = self._discover_best_model()
        logger.info(f"Using discovered model for schedule generation: {self.model_name}")

    def _discover_best_model(self):
        """Find the best available model for content generation."""
        try:
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            
            # Preference order
            preferences = [
                'models/gemini-2.5-flash',
                'models/gemini-2.5-pro',
                'models/gemini-2.0-flash',
                'models/gemini-1.5-flash',
                'models/gemini-1.5-flash-latest',
                'models/gemini-1.5-pro'
            ]
            
            for pref in preferences:
                if pref in available_models:
                    return pref
            
            # Fallback to anything with 'flash' or 'pro'
            for m in available_models:
                if 'flash' in m or 'pro' in m:
                    return m
                    
            return available_models[0] if available_models else 'models/gemini-1.5-flash'
        except Exception as e:
            logger.error(f"Model discovery failed: {e}")
            return 'models/gemini-1.5-flash'

    def generate_batch(self, profile):
        profile_display = profile.get('brand_name') or "LNL AI Agency"
        brand_voice = profile.get('brand_voice', '')
        overview = profile.get('overview', '')
        
        prompt = f"""You are the lead content strategy director and master copywriter for {profile_display}. 
        Your mission is to generate a comprehensive **two-week content calendar and captions** in advance.
        
        **BRAND CONTEXT:**
        - Brand: {profile_display}
        - Overview: {overview}
        - Voice: {brand_voice} (Direct, bold, results-oriented, human building-in-public, zero fluff).

        **THE CONTENT PROTOCOL RULES:**
        You must generate exactly 4 Feed Posts and 14 Stories.

        1. **Feed Posts (4 total - alternating Reel/Carousel):**
           - **Post 1 (Day 2 - Reel - Info Angle):** Expose a major problem regarding **Voice Agents / Automated Phone Receptionists**. Include a hard-hitting statistic (e.g. "med spas lose $130K/year to missed calls"). Hook first. Educational/Reach CTA only (no pitch).
           - **Post 2 (Day 5 - Carousel - Teaching Angle):** Actionable step-by-step how-to on **AI SEO / Search Visibility** (GEO, local rankings). Must include a **soft CTA** at the end (e.g. read our case study via link in bio).
           - **Post 3 (Day 9 - Reel - Info Angle):** Expose a major problem regarding **AI SEO / Search Visibility** (GEO, local rankings) with a hard-hitting statistic. Hook first. Educational/Reach CTA only.
           - **Post 4 (Day 12 - Carousel - Lead Magnet Angle):** Pitch the value of your free **Marketing Prompt Pack** (containing prompts for voice agents & SEO). CTA must be a strict comment trigger: *"Comment 'PROMPTS' below and I'll DM you the link to the prompt pack instantly."*

        2. **Stories (14 total - Day 1 to 14):**
           - Stories should be short, casual, and punchy.
           - **Day 3, 7, and 11 (Story Promo Angle - 1-in-5 ratio):** Direct conversion ask (e.g. "DM us AUDIT for a call audit" or "Link in bio to hear a live voice agent demo").
           - **All other Days (Story Value Angle):** Quick tips, behind-the-scenes building updates, daily tech stats, or interactive questions.

        **CRITICAL WRITING GUARDRAILS:**
        - **Banned AI Cliches:** Do NOT use words like: "digital landscape", "tapestry", "delve", "testament", "revolutionize", "seamlessly", "harness", "elevate", "unlocking", "game-changer", "world-class".
        - **No Fluff:** Start captions immediately. No introductions.
        - **Micro-Formatting:** Use double-spacing, bullet points, and single-sentence paragraphs. Emojis should be used selectively.
        - **Visual Design Prompts:** For each post, generate a clear, detailed instruction for the designer on what graphic or video to create (e.g. *"Single-slide clean black background graphic showing the stat: $130,000 lost. In Outfit font."*).
        
        Return ONLY a JSON object matching this structure:
        {{
            "posts": [
                {{
                    "day": 1,
                    "post_type": "story",
                    "post_angle": "story_value",
                    "caption": "Caption text...",
                    "visual_prompt": "Design instruction..."
                }},
                ...
            ]
        }}
        """

        try:
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            
            if response and response.text:
                text = response.text
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0].strip()
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0].strip()
                
                return json.loads(text, strict=False)
            else:
                return None
        except Exception as e:
            logger.error(f"Failed to batch generate content: {e}")
            return None

    def save_schedule(self, data):
        # Create output directories if missing
        os.makedirs("logs", exist_ok=True)
        os.makedirs("reports", exist_ok=True)
        
        # 1. Save local JSON schedule
        schedule_path = "logs/upcoming_schedule.json"
        
        # Set all generated posts status to 'pending'
        for post in data.get("posts", []):
            post["status"] = "pending"
            
        with open(schedule_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved schedule to: {schedule_path}")
        
        # 2. Write beautiful Markdown report
        md_path = "reports/content_schedule_2_weeks.md"
        
        start_date = datetime.now()
        
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# LNL AI Agency - Two-Week Content Planner\n\n")
            f.write(f"Generated on: {start_date.strftime('%Y-%m-%d')}\n\n")
            f.write(f"This plan covers a 14-day schedule alternating Reach (Reels), Value (Carousels), and Lead Magnets, with daily Stories.\n\n")
            f.write(f"--- \n\n")
            
            for post in data.get("posts", []):
                day_num = post.get("day", 1)
                post_date = start_date + timedelta(days=day_num - 1)
                date_str = post_date.strftime("%A, %b %d")
                
                f.write(f"## 📅 Day {day_num} ({date_str}) - {post.get('post_type').upper()} ({post.get('post_angle').upper()})\n\n")
                f.write(f"> **🎨 VISUAL DESIGN PROMPT (Create this asset):**\n")
                f.write(f"> {post.get('visual_prompt')}\n\n")
                f.write(f"**Instagram Caption:**\n")
                f.write(f"```text\n")
                f.write(f"{post.get('caption')}\n")
                f.write(f"```\n\n")
                f.write(f"---\n\n")
                
        logger.info(f"Generated beautiful markdown report at: {md_path}")

def main():
    parser = argparse.ArgumentParser(description="Batch schedule generator")
    parser.add_argument('--profile', required=True, help="Profile ID to generate for")
    args = parser.parse_args()
    
    profile = load_profile(args.profile)
    if not profile:
        logger.error("Brand profile not found.")
        return
        
    logger.info(f"Starting 2-week batch schedule generation for profile: {args.profile}")
    generator = ScheduleGenerator()
    data = generator.generate_batch(profile)
    
    if data:
        generator.save_schedule(data)
        print("\n" + "="*50)
        print("BATCH SCHEDULE GENERATED SUCCESSFULLY!")
        print("Schedule JSON: logs/upcoming_schedule.json")
        print("Visual Guide:  reports/content_schedule_2_weeks.md")
        print("="*50 + "\n")
    else:
        logger.error("Batch generation failed.")

if __name__ == "__main__":
    main()
