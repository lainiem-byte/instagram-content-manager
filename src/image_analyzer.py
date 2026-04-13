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
        
    def analyze_and_generate(self, image_paths, profile, post_type="feed"):
        if not image_paths:
            return None
            
        profile_display = profile.get('brand_name') or profile.get('name') or "the brand"
        brand_voice = profile.get('brand_voice', 'professional and engaging')
        aesthetic = profile.get('aesthetic', 'modern and clean')
        tone_keywords = ", ".join(profile.get('tone_keywords', []))
        overview = profile.get('overview', '')
        
        overview_section = f"- Overview: {overview}" if overview else ""
        
        prompt = f"""You are the lead content strategy expert and master copywriter for {profile_display}. 
        Your mission is to transform these images into a high-converting, authority-building Instagram {post_type} post. 

        **PERSONA:** You are a seasoned educator and consultant. You don't just "post"—you teach, lead, and build trust through deep expertise.

        **BRAND CONTEXT:**
        - Brand: {profile_display}
        {overview_section}
        - Voice: {brand_voice}
        - Aesthetic: {aesthetic}

        **THE ASSIGNMENT (SURGICAL EXPERT):**
        1. **HOOK:** Start with a bold, scroll-stopping engineering insight.
        2. **AUTHORITY:** Write 2-3 precise paragraphs. No marketing fluff. Every sentence must command respect.
        3. **CONSTRAINTS:** Keep the total caption between 1,000 and 1,500 characters.
        4. **CTA:** Link in bio.
        5. **STRUCTURE:** Use line breaks for mobile readability.

        Return ONLY a JSON object:
        {{
            "caption": "The surgical expert caption here",
            "analysis": "Short category name"
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
                return json.loads(text)
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
