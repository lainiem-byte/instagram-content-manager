import os
import json
import logging
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class ImageAnalyzer:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.error("GEMINI_API_KEY is missing from environment variables.")
        else:
            genai.configure(api_key=self.api_key)
            
        self.model_name = self._discover_best_model()
        logger.info(f"Using discovered model: {self.model_name}")

    def _discover_best_model(self):
        """Find the best available model for vision/content generation."""
        try:
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            
            # Preference order
            preferences = [
                'models/gemini-1.5-flash',
                'models/gemini-1.5-flash-latest',
                'models/gemini-1.5-pro',
                'models/gemini-pro-vision',
                'models/gemini-1.0-pro-vision-latest'
            ]
            
            for pref in preferences:
                if pref in available_models:
                    return pref
            
            # Fallback to anything with 'vision' or 'flash' or 'pro'
            for m in available_models:
                if 'vision' in m or 'flash' in m or 'pro' in m:
                    return m
                    
            return available_models[0] if available_models else 'models/gemini-1.5-flash'
        except Exception as e:
            logger.error(f"Model discovery failed: {e}")
            return 'models/gemini-1.5-flash'
        
    def analyze_and_generate(self, image_paths, profile, post_type="feed", post_angle="info"):
        if not image_paths:
            return None
            
        profile_display = profile.get('brand_name') or profile.get('name') or "the brand"
        brand_voice = profile.get('brand_voice', 'professional and engaging')
        aesthetic = profile.get('aesthetic', 'modern and clean')
        overview = profile.get('overview', '')
        
        overview_section = f"- Overview: {overview}" if overview else ""
        
        # Build prompt guidelines based on post angle and format rules
        if post_angle == "teaching":
            angle_guidelines = """
            **POST TYPE: CAROUSEL (Teaching / Expertise Play)**
            - **Goal:** Prove deep technical/growth expertise, drive saves and shares.
            - **Content:** Practical step-by-step how-to, framework cheatsheet, or FAQ breakdown (focusing on Voice Agents or AI SEO).
            - **Hook:** A promise of immediate problem-solving value or a technical framework breakdown (e.g. "The exact 3-step checklist we use to audit local search visibility / design call agent flows").
            - **Structure:** Break the guides down into clear numbered points or steps with double-spacing between. Keep paragraphs very short (1-2 sentences).
            - **Call to Action (CTA):** TUCK IN A SOFT CTA AT THE END (e.g., "If you want to see how we build and deploy these automated systems for clients, link in bio to read our case study."). No hard pitches.
            """
        elif post_angle == "lead_magnet":
            angle_guidelines = """
            **POST ANGLE: LEAD MAGNET (Comment Trigger Play)**
            - **Goal:** Drive maximum comments (specifically the trigger word 'PROMPTS') to trigger your automated messaging/DM delivery system.
            - **Content:** Pitching the value of your free "Marketing Prompt Pack" (which helps businesses build voice agents, script call flow logic, or audit their local SEO search visibility).
            - **Hook:** A high-curiosity hook showing the exact outcome achieved using these prompts (e.g., "We used 3 simple prompts to design our client's voice agent script. Here they are." or "The exact prompt document we use to audit local SEO visibility in 5 minutes.").
            - **Structure:** Punchy, double-spaced single-sentence paragraphs. Outline what is inside the prompt pack in 3 short bullet points (using emojis).
            - **Call to Action (CTA):** STRICT comment trigger CTA: "Comment 'PROMPTS' below and I'll DM you the direct link to the prompt pack instantly." (Do not ask them to click a link in bio; they must comment).
            """
        elif post_angle == "story_promo":
            angle_guidelines = """
            **POST TYPE: STORY PROMO (Direct Offer / Conversion Play)**
            - **Goal:** Convert existing warm audience.
            - **Content:** Direct "work with us" ask, case study proof, client wins, or booking audits (Voice Agents or AI SEO).
            - **Hook:** Start with direct, high-value metrics or pain-point resolution.
            - **Structure & Formatting:** Hyper-punchy. Use very few words. Make it sound like a direct personal message or a quick announcement.
            - **Call to Action (CTA):** High-intent, direct action trigger (e.g. "DM us AUDIT to claim your slot" or "Tap the link to book a 15-minute voice agent audit").
            """
        elif post_angle == "story_value":
            angle_guidelines = """
            **POST TYPE: STORY VALUE (Behind-the-Scenes / Warm Play)**
            - **Goal:** Build trust and keep the current audience engaged.
            - **Content:** Quick tip, daily stat highlight, behind-the-scenes building update, or tech screenshot explanation.
            - **Hook:** Quick conversational hook.
            - **Structure & Formatting:** Casual, direct, building-in-public vibe.
            - **Call to Action (CTA):** Interactive prompt or gentle question (e.g., "Do you answer your phone 24/7 or use an answering service?").
            """
        else:  # info / reel
            angle_guidelines = """
            **POST TYPE: REEL (Informational / Reach Play)**
            - **Goal:** Reach non-followers, gain visibility, and address broad industry struggles.
            - **Content:** Expose a major operational problem or revenue leak in local business marketing, and back it up with a hard-hitting real-world statistic (e.g., *"med spas lose $130K a year to missed calls"* or *"62% of local searches go unanswered"* or *"local SEO visibility drops 35% when algorithm changes are ignored"*).
            - **Hook:** Start immediately with a striking hook and the real-world statistic.
            - **Structure:** Extremely punchy, double-spaced single-sentence paragraphs. No generic intros.
            - **Call to Action (CTA):** Purely educational/reach CTA (e.g., "Save this post to reference during your next ops meeting"). Absolutely NO direct sales pitch or "work with us" ask.
            """

        prompt = f"""You are the lead content strategy expert and master copywriter for {profile_display}. 
        Your mission is to transform these images into a high-converting, engagement-driven Instagram {post_type} post. 

        **PERSONA:** You are a sharp, forward-thinking growth engineer and tech authority. You sound human, direct, bold, and authoritative. You write like you are building in public.

        **BRAND CONTEXT:**
        - Brand: {profile_display}
        {overview_section}
        - Voice: {brand_voice} (Apply this voice but make it highly native to short-form social media: punchy, clear, no filler words).
        - Aesthetic: {aesthetic}

        {angle_guidelines}

        **CRITICAL WRITING GUARDRAILS:**
        - **Banned AI Cliches:** Do NOT use words like: "digital landscape", "tapestry", "delve", "testament", "revolutionize", "seamlessly", "harness", "elevate", "unlocking", "game-changer", "world-class". If you use these, the copy reads as AI-generated and fails.
        - **Zero Fluff:** Start immediately with the Hook. No "Hey guys," "Are you ready?", or generic welcome intros.
        - **Micro-Formatting:** Use extensive white space. Double spacing between points. Every paragraph should be 1 or 2 lines maximum.
        - **Emojis:** Use emojis selectively for formatting/bullets (e.g., ⚡, →, ✓, ✕) to guide the eye. Do not spam them.
        - **Length:** Keep the entire caption concise and punchy (between 600 and 1,200 characters).
        - **JSON Safety:** Do NOT use unescaped double quotes inside the "caption" JSON value. Use single quotes for speech, quotes, or nested terms (e.g., use 'call back later' instead of "call back later").

        Return ONLY a JSON object:
        {{
            "caption": "The scroll-stopping, high-engagement caption here",
            "analysis": "Short category name or pillar focus (e.g., Voice Agents or AI SEO)"
        }}
        """

        try:
            model = genai.GenerativeModel(self.model_name)
            
            import time
            # Prepare content
            content_parts = [prompt]
            for path in image_paths:
                if os.path.exists(path):
                    ext = os.path.splitext(path)[1].lower()
                    if ext in ['.mp4', '.mov', '.avi', '.webm', '.mkv']:
                        logger.info(f"Uploading video {path} to Gemini for analysis...")
                        video_file = genai.upload_file(path=path)
                        while video_file.state.name == "PROCESSING":
                            time.sleep(2)
                            video_file = genai.get_file(video_file.name)
                        if video_file.state.name == "FAILED":
                            logger.error(f"Gemini video processing failed for {path}")
                            continue
                        content_parts.append(video_file)
                    else:
                        img = Image.open(path)
                        content_parts.append(img)
            
            # Generate content
            response = model.generate_content(content_parts)
            
            if response and response.text:
                text = response.text
                
                # Clean up potential markdown formatting from AI
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0].strip()
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0].strip()
                
                logger.info(f"AI Success! Using {self.model_name}. Response: {text}")
                return json.loads(text, strict=False)
            else:
                logger.error("Empty response from Gemini")
                return None
                
        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            # If the current model failed, try one more time by re-discovering
            if "not found" in str(e).lower() or "404" in str(e):
                logger.info("Retrying with fresh model discovery...")
                self.model_name = self._discover_best_model()
                # Recursive call with a small limit would be safer but let's try once
                return None 
            return None
