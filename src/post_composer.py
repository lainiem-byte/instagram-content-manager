import os
from PIL import Image
from mutagen.mp4 import MP4
import logging

logger = logging.getLogger('post_composer')

class PostComposer:
    def __init__(self):
        pass

    def determine_post_type(self, file_paths):
        """
        IF single image AND landscape/square → FEED POST
        IF 2–10 images → CAROUSEL POST
        IF vertical video (9:16 ratio) OR duration < 90 seconds → REEL
        IF image marked "story" in filename OR story subfolder → STORY
        """
        if not file_paths:
            return None

        # Check for story explicit marking
        for path in file_paths:
            if "story" in os.path.basename(path).lower() or "story" in os.path.dirname(path).lower():
                return "story"

        if len(file_paths) > 1:
            # We assume it's a carousel if there are 2-10 items
            if len(file_paths) > 10:
                logger.warning("More than 10 images provided, trimming to 10 for carousel.")
                file_paths = file_paths[:10]
            return "carousel"

        # Single file analysis
        file_path = file_paths[0]
        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.mp4':
            try:
                video = MP4(file_path)
                duration = video.info.length
                # Simple heuristic for vertical
                is_vertical = True # we don't have robust MP4 w/h purely via mutagen without extra parsing
                
                if is_vertical or duration < 90:
                    return "reel"
            except Exception as e:
                logger.error(f"Error accessing video metadata: {e}")
            return "reel"
        else:
            try:
                with Image.open(file_path) as img:
                    w, h = img.size
                    if h > w * 1.5: 
                        pass # could be story or reel, but prompt says landscape/square feed
            except Exception as e:
                logger.error(f"Error accessing image metadata: {e}")

            # Default for single image
            return "feed"

    def compose_payload(self, file_paths, analysis_result, hashtags, profile, post_type):
        """
        Assembles the final post payload.
        Includes: Selected caption, full hashtag set, link line, alt text, location tag.
        """
        link_line = f"Link in bio → {profile.get('post_link', 'lnlaiagency.com')}"
        
        # Select best caption
        if post_type == "carousel":
            caption = analysis_result.get("caption") or analysis_result.get("text", "Default carousel caption")
        elif post_type in ["story", "reel"]:
            caption = analysis_result.get("overlay_text") or analysis_result.get("caption", "Check it out!")
        else:
             # feed
             caption = analysis_result.get("caption")
             if not caption and "captions" in analysis_result:
                 caption = analysis_result["captions"][0]
             
             if not caption:
                 caption = "Follow us for more updates on AI excellence."

        final_text = f"{caption}\n\n{link_line}\n\n{hashtags}"

        alt_text = analysis_result.get("analysis", "Image from LNL AI Agency")
        
        location = "" 

        payload = {
            "post_type": post_type,
            "media_paths": file_paths,
            "text": final_text,
            "alt_text": alt_text,
            "location": location,
            "account_id": profile.get("account_id")
        }
        
        if post_type in ["story", "reel"]:
            payload["voiceover_script"] = analysis_result.get("voiceover_hook", "")

        return payload

if __name__ == '__main__':
    print("PostComposer initialized.")
