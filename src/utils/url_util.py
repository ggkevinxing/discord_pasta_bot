import re

# Image extensions
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp', '.ico', '.tiff'}

# Video extensions and keywords
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.webm', '.avi', '.mkv', '.flv', '.wmv', '.m4v'}
VIDEO_KEYWORDS = {'youtube.com', 'youtu.be', 'twitch.tv', 'streamable', 'tenor.com', 'giphy.com'}

# Emojis
IMAGE_EMOJI = '📷'
VIDEO_EMOJI = '🎬'
LINK_EMOJI = '🔗'


def replace_urls_with_emojis(text: str) -> str:
    """
    Find URLs in a string and replace them with emojis based on content type.
    
    Images (.png, .jpg, etc.) are replaced with 📷
    Videos (.mp4, .mov, .gif, .webm, 'youtube', etc.) are replaced with 🎬
    
    Args:
        text: The input string containing URLs
        
    Returns:
        The string with URLs replaced by emojis based on their type
    """
    # Regex pattern to match URLs
    url_pattern = r'https?://[^\s]+'
    
    def replace_url(match):
        url = match.group(0)
        url_lower = url.lower()
        
        # Check for video content first (since .gif could be considered both)
        for video_ext in VIDEO_EXTENSIONS:
            if url_lower.endswith(video_ext):
                return VIDEO_EMOJI
        
        for video_keyword in VIDEO_KEYWORDS:
            if video_keyword in url_lower:
                return VIDEO_EMOJI
        
        # Check for image content
        for image_ext in IMAGE_EXTENSIONS:
            if url_lower.endswith(image_ext):
                return IMAGE_EMOJI
        
        # If no match, return link emoji
        return LINK_EMOJI
    
    return re.sub(url_pattern, replace_url, text)
