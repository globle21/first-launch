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

    prompt = f"""Find purchase URLs for the exact product variant specified below.

PRODUCT SPECIFICATION:
Brand: {brand}
Product: {product_name}
Variant: {variant}{brand_context}

SEARCH REQUIREMENTS:
- Search Indian e-commerce platforms (Amazon.in, Flipkart, Nykaa, Myntra, brand website, etc.)
- Find direct purchase pages only
- Target: 15-30 URLs (return fewer if that's all available)

MATCHING CRITERIA:

VARIANT TYPE HANDLING:

For SIZE/VOLUME/WEIGHT variants (100ml, 250ml, 500g, Large, Small, XL):
  → EXACT MATCH REQUIRED
  → "{variant}" must match exactly
  → "100ml" should NOT match "100ml x 2 pack" unless variant specifies "pack"
  → "Large" should NOT match "X-Large" unless variant specifies "XL"

For COLOR variants (black, red, white, blue, pink, etc.):
  → FLEXIBLE MATCH ALLOWED (products CONTAINING the color)
  → "black" MATCHES: "Black", "All Black", "Black/White", "Black and Red"
  → "black" MATCHES: "Nike Blazer Black/White/Orange" (black is present)
  → Focus on products where requested color is PRIMARY or VISIBLE
  → Accept multi-color products if they contain the requested color

MUST MATCH:
- Product: {product_name}
- Brand: {brand}
- Variant: "{variant}" (exact for sizes, contains for colors)

INCLUDE:
✓ Individual product listings with matching variant
✓ Combo/bundle packs containing this variant
  Example: If variant is "180ml", include "180ml + Conditioner Bundle"
✓ Out-of-stock products (we can still extract pricing data)
✓ Multi-color products containing the requested color

EXCLUDE:
✗ Different SIZE variants (e.g., 200ml when searching 100ml)
✗ Completely wrong colors (e.g., "red" when searching "black")
✗ Different products (even from same brand)
✗ Different pack sizes (e.g., "Pack of 2" unless variant specifies it)
✗ Subscription/auto-delivery options
✗ Review pages, blogs, comparison sites
✗ Pre-order/upcoming launch pages (unless price visible)

EDGE CASES & RESTRICTIONS:

1. VARIANT AMBIGUITY:
   - If variant has multiple interpretations, match conservative
   - "100ml" should NOT match "100ml x 2 pack" unless variant explicitly says "pack"
   - "Blue" color should NOT match "Blue Ocean" variant if different

2. URL QUALITY:
   - Skip shortened URLs (bit.ly, goo.gl) - get full URLs only
   - Skip URLs with excessive tracking parameters - use clean URLs
   - Skip mobile-specific URLs (m.amazon.in) - use desktop versions
   - Skip AMP pages - use canonical URLs

3. REGIONAL RESTRICTIONS:
   - Only Indian e-commerce sites (.in domains or India-specific pages)
   - Exclude international sites (.com, .uk) unless they ship to India

4. DUPLICATE DETECTION:
   - Same product on same site with different URLs → include only one
   - Example: amazon.in/dp/B0X and amazon.in/gp/product/B0X → keep shorter
   - URL parameters like ?ref=, &source= → treat as duplicates

5. COMBO VALIDATION:
   - If product_type is "combo", ALL items in combo must be identifiable
   - Combo must clearly show the target variant is included
   - "Mystery box" or "Surprise pack" → EXCLUDE (cannot verify variant)

6. BRAND VERIFICATION:
   - Verify brand name matches exactly (case-insensitive)
   - "Dove" ≠ "Dove Men" ≠ "Baby Dove" (treat as different brands)
   - Authorized resellers only - skip grey market indicators

7. PRICE PRESENCE:
   - Include only if price is visible on page
   - "Contact for price" or "Price on request" → EXCLUDE

8. LISTING FRESHNESS:
   - If page shows "discontinued" or "no longer available" → EXCLUDE
   - Prefer active listings over archived/cached pages

VALIDATION CHECKLIST (verify each URL before including):
1. Does the page show variant "{variant}"? (exact for sizes, contains for colors)
2. Is it a purchase page with buy/cart button or product details?
3. Is the URL not already in your list (check for duplicates)?
4. Is the URL a clean, direct link (not shortened/tracking)?
5. Is the price visible OR is pricing structure detectable?
6. Is the product page accessible (not 404 error)?

OUTPUT FORMAT:
{{
  "urls": [
    {{"url": "https://amazon.in/dp/...", "product_type": "individual", "variant": "{variant}"}},
    {{"url": "https://nykaa.com/...", "product_type": "combo", "variant": "{variant}"}}
  ]
}}

Return empty array if no matches: {{"urls": []}}

CRITICAL RULES:
- For SIZE variants: Only include if variant "{variant}" matches EXACTLY
- For COLOR variants: Include if product CONTAINS the color "{variant}"
- Include out-of-stock products (pricing data still valuable)
- Quality over quantity - but prioritize maximum URL coverage
- When uncertain about size variant, EXCLUDE it
- When uncertain about color variant, INCLUDE if color is mentioned
- Each URL must be independently verifiable

Return valid JSON only, no explanations."""

    return prompt
