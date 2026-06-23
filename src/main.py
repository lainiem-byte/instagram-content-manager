import argparse
import logging
import time
import json
import os
import sys
from dotenv import load_dotenv

# Load environment variables explicitly
load_dotenv()

# Force the working directory to the project root for Task Scheduler
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(project_root)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from datetime import datetime, timedelta
from drive_reader import DriveReader
from image_analyzer import ImageAnalyzer
from hashtag_engine import HashtagEngine
from post_composer import PostComposer
from post_scheduler import PostScheduler
from instagram_publisher import InstagramPublisher
from sheets_logger import SheetsLogger

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('main')

def load_profile(profile_id):
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'brand-profiles.json')
    if not os.path.exists(config_path):
        logger.error("Brand profiles config not found.")
        return None
    with open(config_path, 'r', encoding='utf-8') as f:
        profiles = json.load(f)
        for p in profiles:
            if p.get('account_id') == profile_id and p.get('active'):
                return p
    logger.error(f"Profile {profile_id} not found or inactive.")
    return None

def save_local_history(history_path, entry):
    os.makedirs(os.path.dirname(history_path), exist_ok=True)
    history = []
    if os.path.exists(history_path):
        with open(history_path, 'r', encoding='utf-8') as f:
            try:
                history = json.load(f)
            except:
                pass
    history.append(entry)
    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2)

def main():
    parser = argparse.ArgumentParser(description="Instagram Content Automation Agent")
    parser.add_argument('--profile', required=True, help="Target brand account ID")
    parser.add_argument('--dry-run', action='store_true', help="Preview without posting")
    parser.add_argument('--post-now', action='store_true', help="Skip scheduling and post immediately")
    args = parser.parse_args()

    start_time = datetime.now()
    logger.info(f"=== Pipeline Run Started: {start_time} ===")

    profile = load_profile(args.profile)
    if not profile:
        return

    # Initialize components
    reader = DriveReader()
    analyzer = ImageAnalyzer()
    hashtag_engine = HashtagEngine()
    composer = PostComposer()
    scheduler = PostScheduler()
    publisher = InstagramPublisher()
    sheets_logger = SheetsLogger()

    folder_id = profile.get('drive_folder_id')
    sheet_name = profile.get('sheets_log_name', 'Instagram Post Log')
    direct_sheet_id = profile.get('direct_sheet_id', None)
    
    sheet_id = sheets_logger.get_or_create_sheet(folder_id, sheet_name, direct_sheet_id)

    # 1. Check Schedule Quotas
    posted_types_today = scheduler.get_posted_types_today(profile.get('account_id'))
    needs_main = 'main' not in posted_types_today or args.post_now or args.dry_run
    needs_story = 'story' not in posted_types_today or args.post_now or args.dry_run

    if not needs_main and not needs_story:
        logger.info("Already posted both Main Feed and Story today. Pipeline resting.")
        return

    # 2. Fetch Media (Get larger pool to find both)
    logger.info("Fetching unprocessed media from Drive...")
    files = reader.fetch_unprocessed_media(folder_id, limit=30)
    logger.info(f"Fetch complete. Found {len(files)} files.")
    if not files:
        logger.info("No new unprocessed files found. Please review the Drive folder.")
        return
        
    main_batch = []
    story_batch = []

    for f in files:
        is_story = "story" in f.get('name', '').lower()
        if is_story and needs_story and not story_batch:
            story_batch = [f]
        elif not is_story and needs_main and not main_batch:
            if "carousel" in f.get('name', '').lower():
                main_batch = [cf for cf in files if "carousel" in cf.get('name', '').lower()][:10]
            else:
                main_batch = [f]

    batches_to_post = []
    if main_batch: batches_to_post.append(main_batch)
    if story_batch: batches_to_post.append(story_batch)

    if not batches_to_post:
        logger.info("No files found matching today's available quotas.")
        return

    # Run posting pipeline for each batch
    for batch in batches_to_post:
        local_paths = []
        file_names = []
        media_urls = []
        
        for f in batch:
            local_path = reader.download_file(f['id'], f['name'])
            local_paths.append(local_path)
            file_names.append(f['name'])
            # Use the local VPS public URL so Instagram can actually access the file
            # Replace spaces with %20 for URL safety
            public_base = os.getenv("PUBLIC_API_URL", "http://localhost:8000").rstrip("/")
            public_url = f"{public_base}/api/media/{f['name']}".replace(" ", "%20")
            media_urls.append(public_url)
            logger.info(f"Generated public media URL: {public_url}")

        # 3. Post Type + Analyze
        post_type = composer.determine_post_type(local_paths)
        
        # Check if we have a pre-scheduled caption for this format
        scheduled_item = None
        schedule_data = None
        schedule_file = "logs/upcoming_schedule.json"
        
        if os.path.exists(schedule_file):
            try:
                with open(schedule_file, "r") as f:
                    schedule_data = json.load(f)
                for item in schedule_data.get("posts", []):
                    item_type = item.get("post_type", "")
                    is_match = (
                        item_type == post_type or 
                        (item_type in ["reel", "feed"] and post_type in ["reel", "feed"])
                    )
                    if is_match and item.get("status") == "pending":
                        scheduled_item = item
                        break
            except Exception as e:
                logger.error(f"Error reading upcoming schedule: {e}")

        if scheduled_item:
            logger.info(f"Using pre-scheduled caption from schedule for format: {post_type} (Day {scheduled_item.get('day')})")
            post_angle = scheduled_item.get("post_angle", "info")
            analysis = {
                "caption": scheduled_item.get("caption"),
                "analysis": post_angle
            }
        else:
            # Check if filename explicitly indicates the target strategic angle
            filename_combined = "".join([f.get('name', '').lower() for f in batch])
            
            if "lead_magnet" in filename_combined or "leadmag" in filename_combined:
                post_angle = "lead_magnet"
            elif "teaching" in filename_combined or "teach" in filename_combined:
                post_angle = "teaching"
            elif "story_promo" in filename_combined or "storypromo" in filename_combined:
                post_angle = "story_promo"
            elif "story_value" in filename_combined or "storyvalue" in filename_combined:
                post_angle = "story_value"
            elif "info" in filename_combined:
                post_angle = "info"
            else:
                # Calculate post angle based on post_type format and story history ratio
                if post_type == "carousel":
                    post_angle = "teaching"
                elif post_type in ["reel", "feed"]:
                    post_angle = "info"
                elif post_type == "story":
                    # Check story history for 1-in-4 or 1-in-5 promo ratio
                    history = scheduler._read_history()
                    stories_since_last_promo = 0
                    found_promo = False
                    for entry in reversed(history):
                        if entry.get("account_id") == profile.get("account_id") and entry.get("status") == "Success":
                            entry_pt = entry.get("post_type", "")
                            entry_pa = entry.get("post_angle", "")
                            
                            if "story" in entry_pt.lower():
                                if entry_pa == "story_promo" or "promo" in entry_pt.lower():
                                    found_promo = True
                                    break
                                else:
                                    stories_since_last_promo += 1
                                    if stories_since_last_promo >= 4:
                                        break
                    
                    # If no promo was found, or we've posted at least 4 non-promo stories since the last promo, make it a promo story
                    if not found_promo or stories_since_last_promo >= 4:
                        post_angle = "story_promo"
                    else:
                        post_angle = "story_value"
                else:
                    post_angle = "info"
                    
                # Lead Magnet check: Override Reel or Carousel feed posts once a week
                if post_type in ["reel", "feed", "carousel"]:
                    history = scheduler._read_history()
                    has_recent_lead_magnet = False
                    one_week_ago = datetime.now() - timedelta(days=7)
                    
                    for entry in reversed(history):
                        if entry.get("account_id") == profile.get("account_id") and entry.get("status") == "Success":
                            entry_date_str = entry.get("timestamp", "").split("T")[0]
                            try:
                                entry_date = datetime.strptime(entry_date_str, "%Y-%m-%d")
                                if entry_date >= one_week_ago and entry.get("post_angle") == "lead_magnet":
                                    has_recent_lead_magnet = True
                                    break
                            except ValueError:
                                # Fallback check if date parsing fails or missing
                                if entry.get("post_angle") == "lead_magnet":
                                    has_recent_lead_magnet = True
                                    break
                    
                    if not has_recent_lead_magnet:
                        post_angle = "lead_magnet"
                
            logger.info(f"Resolved format: {post_type}. Mapped content strategy angle: {post_angle}")

            analysis = analyzer.analyze_and_generate(local_paths, profile, post_type, post_angle)
        if not analysis:
            logger.error(f"Analysis failed for {post_type}. Skipping.")
            continue

        # 4. Hashtags
        content_cat = analysis.get("analysis", "General")
        hashtags = hashtag_engine.generate_hashtag_set(content_cat, profile)

        # 5. Compose Payload
        payload = composer.compose_payload(local_paths, analysis, hashtags, profile, post_type)
        payload['media_urls'] = media_urls

        if args.dry_run:
            scheduler.generate_queue_preview([payload])
        
        # 6. Publish        
        date_posted = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        post_id, status = publisher.publish_post(payload, dry_run=args.dry_run)

        # 7. Log
        sheets_logger.log_post(
            sheet_id=sheet_id,
            date_posted=date_posted,
            account=profile.get('brand_name'),
            filename=", ".join(file_names),
            post_type=f"{post_type} ({post_angle})",
            caption=payload.get('text', ''),
            hashtags=hashtags,
            post_id=post_id if post_id else "",
            status=status,
            notes="Dry run - not published" if args.dry_run else ""
        )
        
        save_local_history("logs/post_history.json", {
            "timestamp": datetime.now().isoformat(),
            "account_id": profile.get("account_id"),
            "status": status,
            "post_type": post_type,
            "post_angle": post_angle,
            "hashtags": hashtags,
            "post_id": post_id
        })

        # 8. Move files to posted and update pre-scheduled status
        if status == "Success":
            if scheduled_item and schedule_data:
                for item in schedule_data.get("posts", []):
                    if item.get("day") == scheduled_item.get("day") and item.get("post_type") == scheduled_item.get("post_type"):
                        item["status"] = "Success"
                        item["timestamp"] = datetime.now().isoformat()
                        item["post_id"] = post_id
                        break
                try:
                    with open(schedule_file, "w") as f:
                        json.dump(schedule_data, f, indent=2)
                    logger.info(f"Updated upcoming_schedule.json: Day {scheduled_item.get('day')} marked Success.")
                except Exception as e:
                    logger.error(f"Failed to update upcoming_schedule.json: {e}")
            for f in batch:
                reader.move_file_to_posted(f['id'], folder_id)

    end_time = datetime.now()
    logger.info(f"=== Pipeline Run Completed. Time elapsed: {end_time - start_time} ===")

if __name__ == '__main__':
    main()
