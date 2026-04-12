import os
import json
import logging
from src.image_analyzer import ImageAnalyzer
from src.post_composer import PostComposer
from src.hashtag_engine import HashtagEngine
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def load_profile(profile_id):
    config_path = os.path.join('config', 'brand-profiles.json')
    if not os.path.exists(config_path):
        return None
    with open(config_path, 'r', encoding='utf-8') as f:
        profiles = json.load(f)
        for p in profiles:
            if p.get('account_id') == profile_id:
                return p
    return None

def test_new_copywriting():
    # 1. Setup profile and local file
    profile_id = "lnlaiagency_main"
    profile = load_profile(profile_id)
    if not profile:
        print(f"Error: Profile {profile_id} not found.")
        return

    # Pick a local image found earlier
    test_image_path = os.path.abspath(r"downloads\Dominate_the_Q2_Surge_version_1.png")
    if not os.path.exists(test_image_path):
        print(f"Error: Test image not found at {test_image_path}")
        return

    print(f"\n--- Testing New High-Authority Copywriting Engine ---")
    print(f"Target Image: {os.path.basename(test_image_path)}")
    print(f"Persona: Educator / Authority\n")

    # 2. Initialize components
    analyzer = ImageAnalyzer()
    hashtag_engine = HashtagEngine()
    composer = PostComposer()

    # 3. Analyze and Generate
    print("AI is analyzing image and drafting authority-building copy...")
    analysis = analyzer.analyze_and_generate([test_image_path], profile, post_type="feed")
    
    if not analysis:
        print("Error: Analysis failed. Please check your GEMINI_API_KEY.")
        return

    # 4. Generate Hashtags
    content_cat = analysis.get("analysis", "AI Automation")
    hashtags = hashtag_engine.generate_hashtag_set(content_cat, profile)

    # 5. Compose Final Payload
    payload = composer.compose_payload([test_image_path], analysis, hashtags, profile, post_type="feed")

    # 6. Display Result
    print("\n" + "="*50)
    print("Generated Authority-Building Content:")
    print("="*50)
    print(payload.get('text'))
    print("="*50 + "\n")
    print(f"Internal Topic Analysis: {analysis.get('analysis')}")

if __name__ == '__main__':
    test_new_copywriting()
