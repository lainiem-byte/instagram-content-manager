import os
import random
import json
import logging
from datetime import datetime
import requests

logger = logging.getLogger('hashtag_engine')

TRENDING_POOL = [
    "#Trending", "#Viral", "#ExplorePage", "#FYP", "#DailyInspiration",
    "#BusinessGrowth", "#EntrepreneurLife", "#TechNews", "#Innovation",
    "#MarketingStrategy", "#DigitalMarketing", "#FutureOfWork", "#SuccessMindset",
    "#HustleHard", "#CreativeProcess", "#SocialMediaTips", "#GrowthHacking",
    "#Automation", "#AI", "#TechTrends", "#DailyPost"
]

class HashtagEngine:
    def __init__(self, history_path="logs/post_history.json"):
        self.history_path = history_path
        self._ensure_history_exists()
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}" if self.api_key else None
        
    def _ensure_history_exists(self):
        os.makedirs(os.path.dirname(self.history_path), exist_ok=True)
        if not os.path.exists(self.history_path):
            with open(self.history_path, 'w', encoding='utf-8') as f:
                json.dump([], f)
                
    def _get_recently_used_tags(self):
        with open(self.history_path, 'r', encoding='utf-8') as f:
            try:
                history = json.load(f)
                recent_tags = []
                for post in history[-3:]:
                    tags = post.get('hashtags', '').split(' ')
                    recent_tags.extend([t.strip() for t in tags if t.strip()])
                return set(recent_tags)
            except json.JSONDecodeError:
                return set()

    def generate_niche_hashtags(self, content_category, profile, avoid_tags):
        fallback_niche = [
            "#NicheMarketing", "#IndustryLeader", "#SpecializedServices", "#ExpertAdvice",
            "#TargetAudience", "#NicheBusiness", "#ProfessionalServices", "#IndustryInsights",
            "#DedicatedSupport", "#TailoredSolutions"
        ]
        
        if not self.url:
            return random.sample(fallback_niche, 10)
            
        prompt = f"""
Generate exactly 10 distinct, highly relevant niche Instagram hashtags for a post in the category: '{content_category}'.
The brand is '{profile.get('brand_name')}'.
Avoid these recently used tags if possible: {', '.join(avoid_tags)}.
Return ONLY a JSON array of 10 strings, each starting with #.
"""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.8,
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"}
                }
            }
        }
        
        try:
            response = requests.post(self.url, json=payload)
            if response.status_code == 200:
                result = response.json()
                text_response = result['candidates'][0]['content']['parts'][0]['text']
                tags = json.loads(text_response)
                valid_tags = [t for t in tags if t.startswith('#')][:10]
                if len(valid_tags) < 10:
                    valid_tags.extend(fallback_niche[:10 - len(valid_tags)])
                return valid_tags
            return random.sample(fallback_niche, 10)
        except Exception as e:
            logger.error(f"Error generating niche hashtags via REST: {e}")
            return random.sample(fallback_niche, 10)

    def generate_hashtag_set(self, content_category, profile):
        recent_tags = self._get_recently_used_tags()
        
        available_trending = list(set(TRENDING_POOL) - recent_tags)
        if len(available_trending) < 5:
            available_trending = TRENDING_POOL
        tier1 = random.sample(available_trending, 5)
        
        tier2 = self.generate_niche_hashtags(content_category, profile, recent_tags)
        
        pool_branded = profile.get('branded_hashtags', [])
        limit = min(5, len(pool_branded))
        tier3 = random.sample(pool_branded, limit) if limit > 0 else []
        
        all_tags = []
        for tag in tier1 + tier2 + tier3:
            if tag not in all_tags:
                all_tags.append(tag)
                
        final_tags = all_tags[:20]
        return " ".join(final_tags)
