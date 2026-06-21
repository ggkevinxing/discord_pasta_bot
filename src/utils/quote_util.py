from src.utils.url_util import replace_urls_with_emojis

def generate_quote_content(original_content: str, max_quote_len: int):
    # Replace URLs with emojis
    formatted_content = replace_urls_with_emojis(original_content)
    
    # If content is within limit, return as is
    if len(formatted_content) <= max_quote_len:
        return formatted_content
    
    # Truncate to max_quote_len, trying to preserve word boundaries
    truncated = formatted_content[:max_quote_len]
    
    # If the last character is not a space, try to truncate at the last word boundary
    if truncated and truncated[-1] != ' ':
        last_space_idx = truncated.rfind(' ')
        if last_space_idx > 0:  # Make sure we found a space and it's not at the very beginning
            truncated = truncated[:last_space_idx]
    
    return truncated.rstrip() + '...'