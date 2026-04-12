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

from datetime import datetime
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
            public_base = os.getenv("PUBLIC_API_URL", "http://localhost:8000")
            public_url = f"{public_base}/media/{f['name']}".replace(" ", "%20")
            media_urls.append(public_url)
            logger.info(f"Generated public media URL: {public_url}")

        # 3. Post Type + Analyze
        post_type = composer.determine_post_type(local_paths)
        
        analysis = analyzer.analyze_and_generate(local_paths, profile, post_type)
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
            post_type=post_type,
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
            "hashtags": hashtags,
            "post_id": post_id
        })

        # 8. Move files to posted
        if status == "Success":
            for f in batch:
                reader.move_file_to_posted(f['id'], folder_id)

    end_time = datetime.now()
    logger.info(f"=== Pipeline Run Completed. Time elapsed: {end_time - start_time} ===")

if __name__ == '__main__':
    main()
