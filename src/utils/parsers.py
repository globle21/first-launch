"""
EMERGENCY FALLBACK PARSERS - Use only if Gemini fails

⚠️ WARNING: These regex-based parsers are NOT the primary parsing method.
⚠️ Gemini 2.5 Flash should handle 99%+ of parsing tasks.
⚠️ These parsers only exist as a last-resort fallback if Gemini fails.

Primary Parser: Gemini 2.5 Flash (in orchestrator_agent.py)
Fallback Parser: These regex utilities (rarely used)
"""

import re
from typing import Dict, Optional, List


# ============================================================================
# EMERGENCY FALLBACK PATTERNS
# ============================================================================
# These regex patterns are generic and may not work well for all cases.
# Gemini should handle the parsing. These are only for emergencies.

VARIANT_PATTERNS = {
    "volume": r'\b(\d+)\s*(ml|l|litre|liter)\b',
    "weight": r'\b(\d+)\s*(g|kg|gram|kilogram)\b',
    "count": r'\b(\d+)\s*(pack|pcs|pieces|units?)\b',
    "size": r'\b(small|medium|large|xl|xxl|s|m|l)\b',
}


def parse_user_query_fallback(user_query: str) -> Dict[str, Optional[str]]:
    """
    EMERGENCY FALLBACK: Parse user query with regex patterns

    ⚠️ This function should RARELY be called!
    ⚠️ Gemini 2.5 Flash is the primary parser (in orchestrator_agent.py)
    ⚠️ This is only used if Gemini fails or errors occur

    This parser uses generic heuristics and may not work well for all cases:
    - Assumes brand is first 1-2 words (may be wrong)
    - Uses word length to guess brand name (unreliable)
    - Cannot understand context (unlike Gemini)

    Examples:
        "True Frog Curl Shampoo" → {brand: "True Frog", product: "Curl Shampoo", variant: None}
        "True Frog Curl Shampoo 100ml" → {brand: "True Frog", product: "Curl Shampoo", variant: "100ml"}
        "Nykaa Matte Lipstick Red" → {brand: "Nykaa", product: "Matte Lipstick", variant: "Red"}

    Args:
        user_query: Raw user input from landing page

    Returns:
        Dictionary with extracted brand, product_name, variant, has_variant
    """
    user_query = user_query.strip()

    # Extract variant first (so we can remove it from the query)
    variant = extract_variant_fallback(user_query)
    has_variant = variant is not None

    # Remove variant from query to isolate brand + product
    if variant:
        # Remove the variant pattern from query
        query_without_variant = user_query.replace(variant, "").strip()
    else:
        query_without_variant = user_query

    # Simple heuristic: First 1-3 words are likely the brand
    # Remaining words are the product name
    words = query_without_variant.split()

    # Extract brand (first 1-2 words typically)
    # If query has 2 words: assume first word is brand
    # If query has 3+ words: assume first 1-2 words are brand
    if len(words) <= 2:
        brand = words[0] if words else None
        product_name = " ".join(words[1:]) if len(words) > 1 else None
    else:
        # Check if first two words could be a brand (common pattern: "True Frog", "Mamaearth", etc.)
        if len(words[0]) <= 6 and len(words[1]) <= 6:
            # Likely a two-word brand like "True Frog"
            brand = f"{words[0]} {words[1]}"
            product_name = " ".join(words[2:])
        else:
            # Single-word brand
            brand = words[0]
            product_name = " ".join(words[1:])

    return {
        "brand": brand,
        "product_name": product_name,
        "variant": variant,
        "has_variant": has_variant,
        "original_query": user_query,
    }


def extract_variant_fallback(text: str) -> Optional[str]:
    """
    EMERGENCY FALLBACK: Extract variant information using regex patterns

    ⚠️ This function should RARELY be called!
    ⚠️ Gemini handles variant extraction in most cases
    ⚠️ Generic regex patterns may miss context-specific variants

    Args:
        text: Input text containing potential variant info

    Returns:
        Extracted variant string (e.g., "100ml", "250g", "red") or None
    """
    text_lower = text.lower()

    # Check for volume (ml, l)
    volume_match = re.search(VARIANT_PATTERNS["volume"], text_lower)
    if volume_match:
        return f"{volume_match.group(1)}{volume_match.group(2)}"

    # Check for weight (g, kg)
    weight_match = re.search(VARIANT_PATTERNS["weight"], text_lower)
    if weight_match:
        return f"{volume_match.group(1)}{weight_match.group(2)}"

    # Check for count (pack, pcs)
    count_match = re.search(VARIANT_PATTERNS["count"], text_lower)
    if count_match:
        return f"{count_match.group(1)} {count_match.group(2)}"

    # Check for size (S, M, L, XL)
    size_match = re.search(VARIANT_PATTERNS["size"], text_lower, re.IGNORECASE)
    if size_match:
        return size_match.group(1).upper()

    # Check for color at the end (simple heuristic)
    # Common colors
    colors = ["red", "blue", "green", "black", "white", "pink", "purple", "orange", "yellow", "brown", "grey", "gray"]
    words = text_lower.split()
    if words and words[-1] in colors:
        return words[-1].capitalize()

    return None


def extract_search_terms(product_data: Dict) -> List[str]:
    """
    Generate search terms from parsed product data for web search

    Args:
        product_data: Dictionary with brand, product_name, variant

    Returns:
        List of search query strings
    """
    brand = product_data.get("brand", "")
    product_name = product_data.get("product_name", "")
    variant = product_data.get("variant", "")

    search_terms = []

    # Base search: brand + product
    if brand and product_name:
        search_terms.append(f"{brand} {product_name}")

    # If variant specified, add variant-specific search
    if variant:
        if brand and product_name:
            search_terms.append(f"{brand} {product_name} {variant}")

    # Add "official website" search
    if brand:
        search_terms.append(f"{brand} official website India")

    return search_terms


def clean_product_name(product_name: str) -> str:
    """
    Clean and normalize product name for comparison

    Args:
        product_name: Raw product name

    Returns:
        Cleaned product name
    """
    # Remove extra whitespace
    cleaned = " ".join(product_name.split())

    # Remove special characters but keep hyphens and spaces
    cleaned = re.sub(r'[^\w\s\-]', '', cleaned)

    return cleaned.strip()
