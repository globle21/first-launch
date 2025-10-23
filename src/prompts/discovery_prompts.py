"""
Prompts for URLDiscoveryAgent (Claude 4.5 Haiku with web search)
Task: Find MAXIMUM URLs for specific product variant across all retailers
"""


def get_url_discovery_prompt(
    brand: str,
    product_name: str,
    variant: str,
    brand_product_url: str = None
) -> str:
    """
    Generate prompt for discovering maximum product URLs across web

    Args:
        brand: Brand name
        product_name: Full product name
        variant: Specific variant (e.g., "100ml", "Red", "Pack of 2")
        brand_product_url: Official brand URL (optional, for reference)

    Returns:
        Formatted prompt string for Claude 4.5 Haiku
    """

    brand_context = ""
    if brand_product_url:
        brand_context = f"\nOfficial: {brand_product_url}"

    prompt = f"""FIND MAXIMUM URLs - EXACT VARIANT MATCH

TARGET:
Brand: {brand}
Product: {product_name}
Variant: {variant}{brand_context}

OBJECTIVE:

Search Strategy:
1. Perform comprehensive web searches
2. Check ALL major Indian e-commerce platforms
3. Include official brand store
4. Find as many URLs as possible (aim for 20-50+ URLs if available)

MATCHING RULES:

✓ INCLUDE:
- Exact variant "{variant}" only
- Individual products
- Combos/bundles containing this exact variant
- Same product across multiple retailers

✗ EXCLUDE:
- Different variants/sizes
- Subscriptions
- Non-purchase pages (blogs, reviews)
- Category pages

COMBO EXAMPLES:
✓ "Shampoo 100ml + Conditioner 100ml" (if searching 100ml shampoo)
✗ "Shampoo 250ml + Conditioner 100ml" (if searching 100ml shampoo)

OUTPUT (JSON only, no explanations):

{{
  "urls": [
    {{"url": "https://truefrog.in/products/...", "product_type": "individual", "variant": "{variant}"}},
    {{"url": "https://amazon.in/dp/...", "product_type": "combo", "variant": "{variant}"}}
  ]
}}

Fields:
- url: Purchase page URL
- product_type: "individual" or "combo"
- variant: "{variant}"

Requirements:
- Exact variant "{variant}" only
- Direct purchase pages
- Deduplicated URLs
- 20-50+ URLs total

Return JSON only."""

    return prompt
