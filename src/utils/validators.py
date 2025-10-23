"""
Validation utilities for product data, URLs, and API responses
"""

import re
from typing import Dict, List, Optional
from urllib.parse import urlparse


def validate_url(url: str) -> bool:
    """
    Validate if a string is a proper URL

    Args:
        url: URL string to validate

    Returns:
        True if valid URL, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
    except:
        return False


def validate_product_data(product: Dict) -> bool:
    """
    Validate product data structure returned by ProductConfirmationAgent

    Expected structure:
    {
        "name": str,
        "url": str (valid URL),
        "description": str (optional)
    }

    Args:
        product: Product dictionary

    Returns:
        True if valid structure, False otherwise
    """
    if not isinstance(product, dict):
        return False

    # Required fields
    if "name" not in product or not product["name"]:
        return False

    if "url" not in product:
        return False

    # Validate URL
    if not validate_url(product["url"]):
        return False

    return True


def validate_variant_data(variant: Dict) -> bool:
    """
    Validate variant data structure

    Expected structure:
    {
        "type": str (e.g., "size", "color", "volume"),
        "value": str (e.g., "100ml", "Red", "Large"),
        "url": str (optional - direct URL to variant page)
    }

    Args:
        variant: Variant dictionary

    Returns:
        True if valid structure, False otherwise
    """
    if not isinstance(variant, dict):
        return False

    # Required fields
    if "type" not in variant or not variant["type"]:
        return False

    if "value" not in variant or not variant["value"]:
        return False

    # If URL is provided, validate it
    if "url" in variant and variant["url"]:
        if not validate_url(variant["url"]):
            return False

    return True


def validate_discovered_url(url_data: Dict) -> bool:
    """
    Validate URL data structure returned by URLDiscoveryAgent

    Expected structure (simplified - 3 fields only):
    {
        "url": str (valid URL),
        "product_type": str ("individual", "combo"),
        "variant": str
    }

    Args:
        url_data: URL data dictionary

    Returns:
        True if valid structure, False otherwise
    """
    if not isinstance(url_data, dict):
        return False

    # Required fields (reduced to 3 essential fields)
    required_fields = ["url", "product_type", "variant"]
    for field in required_fields:
        if field not in url_data or not url_data[field]:
            return False

    # Validate URL
    if not validate_url(url_data["url"]):
        return False

    # Validate product_type
    valid_types = ["individual", "combo"]
    if url_data["product_type"] not in valid_types:
        return False

    return True


def validate_enriched_url(url_data: Dict) -> bool:
    """
    Validate enriched URL data structure returned by PriceScrapingAgent

    Expected structure:
    {
        "url": str (valid URL),
        "product_type": str ("individual", "combo"),
        "variant": str,
        "name": str,
        "price": str or None,
        "currency": str or None,
        "image": str,
        "availability": str ("in_stock", "out_of_stock", "unavailable")
    }

    Args:
        url_data: Enriched URL data dictionary

    Returns:
        True if valid structure, False otherwise
    """
    if not isinstance(url_data, dict):
        return False

    # Required fields
    required_fields = ["url", "product_type", "variant", "name", "image", "availability"]
    for field in required_fields:
        if field not in url_data:
            return False

    # Validate URL
    if not validate_url(url_data["url"]):
        return False

    # Validate product_type
    valid_types = ["individual", "combo"]
    if url_data["product_type"] not in valid_types:
        return False

    # Validate availability
    valid_availability = ["in_stock", "out_of_stock", "unavailable"]
    if url_data["availability"] not in valid_availability:
        return False

    # Price and currency can be None (for unavailable/out_of_stock)
    # But if one is present, both should be present
    price = url_data.get("price")
    currency = url_data.get("currency")

    if price is not None and currency is None:
        return False
    if currency is not None and price is None:
        return False

    return True


def filter_valid_urls(urls: List[Dict]) -> List[Dict]:
    """
    Filter list of URLs, keeping only valid ones

    Args:
        urls: List of URL data dictionaries

    Returns:
        List of valid URL data dictionaries
    """
    return [url for url in urls if validate_discovered_url(url)]


def filter_valid_enriched_urls(urls: List[Dict]) -> List[Dict]:
    """
    Filter list of enriched URLs, keeping only valid ones

    Args:
        urls: List of enriched URL data dictionaries

    Returns:
        List of valid enriched URL data dictionaries
    """
    return [url for url in urls if validate_enriched_url(url)]


def extract_domain(url: str) -> Optional[str]:
    """
    Extract domain from URL

    Args:
        url: Full URL

    Returns:
        Domain string (e.g., "amazon.in") or None if invalid
    """
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except:
        return None


def is_subscription_url(url: str, url_text: str = "") -> bool:
    """
    Check if URL is a subscription link (should be excluded)

    Args:
        url: URL string
        url_text: Additional text context from the URL page

    Returns:
        True if subscription link, False otherwise
    """
    # Check URL for subscription keywords
    subscription_keywords = [
        "subscribe",
        "subscription",
        "recurring",
        "auto-ship",
        "autoship",
        "monthly-box",
    ]

    url_lower = url.lower()
    text_lower = url_text.lower()

    for keyword in subscription_keywords:
        if keyword in url_lower or keyword in text_lower:
            return True

    return False
