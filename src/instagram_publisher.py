import os
import time
import requests
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger('instagram_publisher')

class InstagramPublisher:
    def __init__(self):
        self.access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
        self.ig_account_id = os.getenv("INSTAGRAM_ACCOUNT_ID")
        # Content publishing for IG Business accounts uses the Facebook Graph URL
        self.base_url = "https://graph.facebook.com/v20.0"
        
    def _create_container(self, payload, attempt=1):
        url = f"{self.base_url}/{self.ig_account_id}/media"
        post_type = payload.get("post_type", "feed")
        text = payload.get("text", "")
        media_urls = payload.get("media_urls", [])

        logger.info(f"Creating container at URL: {url}")
        logger.info(f"Params being sent: {{'post_type': {post_type}, 'media_count': {len(media_urls)}}}")
        
        params = {
            "access_token": self.access_token,
        }
        
        # Only add caption for feed/reel/carousel (Stories don't support captions in the API)
        if post_type != "story":
            params["caption"] = text
        
        if post_type == "feed" and media_urls:
            params["image_url"] = media_urls[0]
            logger.info(f"Target image_url: {media_urls[0]}")
        elif post_type in ["reel", "story"] and media_urls:
            # Check if actual file is a video
            media_paths = payload.get("media_paths", [])
            first_path = media_paths[0].lower() if media_paths else ""
            is_video = any(first_path.endswith(ext) for ext in [".mp4", ".mov", ".avi", ".mkv"])
            
            if is_video:
                params["video_url"] = media_urls[0]
                logger.info(f"Target video_url: {media_urls[0]}")
            else:
                params["image_url"] = media_urls[0]
                logger.info(f"Target image_url (Story Image): {media_urls[0]}")
            
            params["media_type"] = "REELS" if post_type == "reel" else "STORIES"
            logger.info(f"Set media_type to {params['media_type']}")
        elif post_type == "carousel" and media_urls:
            # Carousel requires creating child containers first
            params["media_type"] = "CAROUSEL"
            children = []
            for m_url in media_urls:
                child_params = {
                    "image_url": m_url,
                    "is_carousel_item": "true",
                    "access_token": self.access_token
                }
                logger.debug(f"Creating carousel child for URL: {m_url}")
                child_res = requests.post(url, data=child_params)
                if child_res.status_code == 200:
                    children.append(child_res.json().get('id'))
                else:
                    logger.error(f"Failed to create carousel child: {child_res.json()}")
                    return None
            params["children"] = ",".join(children)

        response = requests.post(url, data=params)
        data = response.json()
        
        if response.status_code == 200 and 'id' in data:
            logger.info(f"Successfully created container: {data['id']}")
            return data['id']
        else:
            logger.error(f"Container creation failed: {data}")
            if attempt < 3:
                backoff = 2 ** attempt
                logger.info(f"Retrying container creation in {backoff} seconds...")
                time.sleep(backoff)
                return self._create_container(payload, attempt + 1)
            return None

    def _publish_container(self, container_id, attempt=1):
        """Step 2: Publish the media container"""
        url = f"{self.base_url}/{self.ig_account_id}/media_publish"
        params = {
            "creation_id": container_id,
            "access_token": self.access_token
        }
        
        response = requests.post(url, data=params)
        data = response.json()
        
        if response.status_code == 200 and 'id' in data:
            return data['id']
        else:
            # Sometimes video containers take time to be ready
            logger.error(f"Publish failed: {data}")
            if attempt < 3:
                backoff = (2 ** attempt) * 5 # Extra wait for videos to process
                logger.info(f"Retrying publish in {backoff} seconds...")
                time.sleep(backoff)
                return self._publish_container(container_id, attempt + 1)
            return None

    def publish_post(self, payload, dry_run=False):
        logger.info(f"Starting publish process for {payload.get('post_type')}...")
        
        if dry_run:
            logger.info("DRY RUN ENABLED. Skipping actual Instagram API call.")
            return "dry_run_post_id", "Dry Run"
            
        container_id = self._create_container(payload)
        if not container_id:
            logger.error("Failed to create container after retries. Aborting.")
            return None, "Failed at container creation"
            
        # Give Meta a moment to process the container natively
        time.sleep(5)
        
        post_id = self._publish_container(container_id)
        if not post_id:
            logger.error("Failed to publish container after retries. Aborting.")
            return None, "Failed at container publish"
            
        logger.info(f"Successfully published to Instagram! Post ID: {post_id}")
        return post_id, "Success"

if __name__ == '__main__':
    print("InstagramPublisher initialized.")
