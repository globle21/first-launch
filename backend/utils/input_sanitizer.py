"""
Input sanitization utilities to prevent injection attacks and validate user inputs
"""
import re
import html
from typing import Optional, Tuple
from urllib.parse import urlparse, urlunparse


def sanitize_text_input(text: str, max_length: int = 5000, allow_html: bool = False) -> str:
    """
    Sanitize text input to prevent injection attacks
    
    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length
        allow_html: If False, HTML entities are escaped
    
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Strip whitespace
    text = text.strip()
    
    # Limit length
    if len(text) > max_length:
        text = text[:max_length]
    
    # Escape HTML if not allowed
    if not allow_html:
        text = html.escape(text)
    
    # Remove null bytes and control characters (except newlines, tabs, carriage returns)
    text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
    
    return text


def sanitize_url(url: str) -> Optional[str]:
    """
    Sanitize and validate URL input
    
    Args:
        url: URL string to sanitize
    
    Returns:
        Sanitized URL or None if invalid
    """
    if not url:
        return None
    
    url = url.strip()
    
    # Add protocol if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    try:
        parsed = urlparse(url)
        
        # Only allow http/https schemes
        if parsed.scheme not in ['http', 'https']:
            return None
        
        # Validate hostname (basic check)
        if not parsed.netloc:
            return None
        
        # Reconstruct URL (sanitizes query params)
        sanitized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            ''  # Remove fragment
        ))
        
        # Limit total URL length
        if len(sanitized) > 2048:  # RFC 7230 recommends max 8000, but 2048 is safer
            return None
        
        return sanitized
    
    except Exception:
        return None


def sanitize_keyword(keyword: str, max_length: int = 500) -> str:
    """
    Sanitize keyword/search query input
    
    Args:
        keyword: Keyword string to sanitize
        max_length: Maximum allowed length
    
    Returns:
        Sanitized keyword
    """
    if not keyword:
        return ""
    
    # Strip whitespace
    keyword = keyword.strip()
    
    # Limit length
    if len(keyword) > max_length:
        keyword = keyword[:max_length]
    
    # Remove potentially dangerous characters while keeping normal search characters
    # Allow: letters, numbers, spaces, dashes, underscores, dots, parentheses, commas
    keyword = re.sub(r'[^\w\s\-_.(),/&+]', '', keyword)
    
    # Remove excessive whitespace
    keyword = re.sub(r'\s+', ' ', keyword)
    
    return keyword.strip()


def validate_search_input(input_type: str, user_input: str) -> Tuple[bool, Optional[str]]:
    """
    Validate search input based on type
    
    Args:
        input_type: "keyword" or "url"
        user_input: The input to validate
    
    Returns:
        Tuple of (is_valid: bool, error_message: Optional[str])
    """
    if not user_input or not user_input.strip():
        return False, "Input cannot be empty"
    
    if input_type == "keyword":
        sanitized = sanitize_keyword(user_input)
        if not sanitized:
            return False, "Invalid keyword format"
        if len(sanitized) < 2:
            return False, "Keyword must be at least 2 characters"
        if len(sanitized) > 500:
            return False, "Keyword exceeds maximum length of 500 characters"
    
    elif input_type == "url":
        sanitized = sanitize_url(user_input)
        if not sanitized:
            return False, "Invalid URL format"
    
    else:
        return False, f"Unknown input_type: {input_type}. Must be 'keyword' or 'url'"
    
    return True, None

