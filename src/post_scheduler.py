import os
import json
from datetime import datetime, timedelta
import logging

logger = logging.getLogger('post_scheduler')

class PostScheduler:
    def __init__(self, history_path="logs/post_history.json"):
        self.history_path = history_path
        
    def _read_history(self):
        if not os.path.exists(self.history_path):
            return []
        try:
            with open(self.history_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading history: {e}")
            return []

    def get_posted_types_today(self, account_id):
        history = self._read_history()
        today_str = datetime.now().strftime("%Y-%m-%d")
        posted = set()
        
        for record in history:
            if record.get('account_id') == account_id:
                record_date = record.get('timestamp', '').split('T')[0]
                if record_date == today_str and record.get('status') == 'Success':
                    ptype = record.get('post_type')
                    if ptype == 'story':
                        posted.add('story')
                    else:
                        posted.add('main')
        return posted

    def get_optimal_time(self, profile):
        """
        Fallback: industry benchmark data by vertical.
        AI/tech: Tue-Fri 10am-12pm or 6-8pm local.
        Since the job runs at 8 AM, we target 10 AM.
        """
        now = datetime.now()
        target_time = now.replace(hour=10, minute=0, second=0, microsecond=0)
        
        # If we run it late in the day, default to immediately for today if needed,
        # but optimally it runs at 8 AM.
        if now > target_time:
            target_time = now + timedelta(minutes=10) # 10 mins from now if missed window
            
        return target_time.strftime("%I:%M %p")

    def generate_queue_preview(self, payloads):
        print("\n=== Upcoming Post Queue Preview ===")
        if not payloads:
            print("No images available for scheduling. Please review the Drive folder.")
            return

        now = datetime.now()
        for i, payload in enumerate(payloads):
            post_date = now + timedelta(days=i)
            media_names = [os.path.basename(p) for p in payload.get('media_paths', [])]
            caption_preview = payload.get('text', '')[:50].replace('\n', ' ') + "..."
            
            print(f"Day {i+1} ({post_date.strftime('%Y-%m-%d')} Optimal):")
            print(f"  Media: {', '.join(media_names)}")
            print(f"  Type:  {payload.get('post_type')}")
            print(f"  Preview: {caption_preview}")
            print("-" * 35)

if __name__ == '__main__':
    print("PostScheduler initialized.")
