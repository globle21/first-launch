"""
Prompts for ProductConfirmationAgent (GPT-4o with web search)
Task: Find brand page, confirm product, extract variants (NO PRICES)
"""


def get_product_confirmation_prompt(brand: str, product_name: str, variant_hint: str = None) -> str:
    """
    Generate prompt for finding brand page and confirming product

    Args:
        brand: Brand name (e.g., "True Frog")
        product_name: Product name (e.g., "Curl Shampoo")
        variant_hint: Optional variant hint if user mentioned it (e.g., "100ml")

    Returns:
        Formatted prompt string for GPT-4o
    """

    variant_instruction = ""
    if variant_hint:
        variant_instruction = f"\n- User mentioned variant: {variant_hint} (keep this in mind during confirmation)"

    prompt = f"""
TASK: FIND BRAND PAGE AND CONFIRM PRODUCT

You are helping a user find a specific product from a brand. Your task is to:
1. Find the brand's official website
2. Locate the specific product the user is looking for
3. Return structured information about the product

=== USER QUERY ===
Brand: {brand}
Product: {product_name}{variant_instruction}

=== INSTRUCTIONS ===

STEP 1: FIND OFFICIAL BRAND WEBSITE
- Search for "{brand} official website" or "{brand} India official site"
- Prioritize:
  • Official .in domains for Indian brands
  • Brand's own website (not retailer pages)
  • Verified brand pages
- Avoid: Amazon, Flipkart, Nykaa product listings (we need the BRAND's page)

STEP 2: LOCATE THE PRODUCT
- Navigate to the product catalog/shop section
- Search for "{product_name}" on the brand's website
- Find the exact product matching the user's query
- If multiple similar products exist, list ALL candidates

STEP 3: EXTRACT PRODUCT INFORMATION (NO PRICES!)
For each matching product, extract:
- Product full name (as shown on brand page)
- Product URL (direct link to product page)
- Brief description (1-2 sentences)
- Category/type if available

DO NOT extract prices - we only need product identification info.

=== EXPECTED OUTPUT FORMAT ===

Return valid JSON in this EXACT format:

{{
  "brand_page_found": true,
  "brand_page_url": "https://truefrog.in",
  "products_found": [
    {{
      "name": "True Frog Curl Retaining Shampoo",
      "url": "https://truefrog.in/products/curl-retaining-shampoo",
      "description": "Gentle cleansing shampoo with flax seed extract for curly hair"
    }},
    {{
      "name": "True Frog Curl Defining Shampoo",
      "url": "https://truefrog.in/products/curl-defining-shampoo",
      "description": "Defines and enhances natural curls with botanical extracts"
    }}
  ],
  "match_confidence": "high",
  "notes": "Found 2 curl shampoo products on brand page"
}}

=== ERROR HANDLING ===

If brand page not found:
{{
  "brand_page_found": false,
  "brand_page_url": null,
  "products_found": [],
  "match_confidence": "none",
  "notes": "Could not find official brand website for {brand}"
}}

If product not found on brand page:
{{
  "brand_page_found": true,
  "brand_page_url": "https://...",
  "products_found": [],
  "match_confidence": "none",
  "notes": "Brand page found but product '{product_name}' not available"
}}

=== CRITICAL RULES ===
✓ Search ONLY the brand's official website
✓ Return ALL matching products (let user choose if multiple)
✓ DO NOT include prices in any field
✓ Use exact product names from brand page
✓ Verify URLs are valid and direct to product pages

Begin web search now. Return ONLY valid JSON.
"""

    return prompt


def get_variant_extraction_prompt(product_name: str, product_url: str, variant_hint: str = None) -> str:
    """
    Generate prompt for extracting variants from confirmed product page

    Args:
        product_name: Confirmed product name
        product_url: Direct URL to product page
        variant_hint: Optional variant hint if user mentioned it

    Returns:
        Formatted prompt string for GPT-4o
    """

    variant_context = ""
    if variant_hint:
        variant_context = f"\nNote: User is interested in the '{variant_hint}' variant (if available)."

    prompt = f"""
TASK: EXTRACT ALL PRODUCT VARIANTS (NO PRICES!)

You are analyzing a confirmed product page to extract all available variants.

=== PRODUCT DETAILS ===
Product Name: {product_name}
Product URL: {product_url}{variant_context}

=== INSTRUCTIONS ===

Visit the product page and extract ALL available variants:

VARIANT TYPES TO LOOK FOR:
1. **Size/Volume**: 50ml, 100ml, 250ml, 500ml, etc.
2. **Weight**: 50g, 100g, 250g, 500g, 1kg, etc.
3. **Color/Shade**: Red, Blue, Nude, etc.
4. **Pack Size**: Single, Pack of 2, Pack of 3, etc.
5. **Other**: Travel size, Full size, Mini, Regular, etc.

EXTRACTION RULES:
✓ Extract ALL variants listed on the page
✓ DO NOT include prices
✓ Record the variant type (size, color, weight, etc.)
✓ Record the variant value (100ml, Red, Pack of 2, etc.)
✓ If available, record direct URL to each variant

=== EXPECTED OUTPUT FORMAT ===

Return valid JSON in this EXACT format:

{{
  "product_name": "{product_name}",
  "product_url": "{product_url}",
  "variants_found": true,
  "variants": [
    {{
      "type": "volume",
      "value": "100ml",
      "url": "https://truefrog.in/products/curl-shampoo-100ml"
    }},
    {{
      "type": "volume",
      "value": "250ml",
      "url": "https://truefrog.in/products/curl-shampoo-250ml"
    }},
    {{
      "type": "volume",
      "value": "500ml",
      "url": "https://truefrog.in/products/curl-shampoo-500ml"
    }}
  ],
  "total_variants": 3,
  "notes": "Found 3 size variants for this product"
}}

=== ERROR HANDLING ===

If no variants found (single variant product):
{{
  "product_name": "{product_name}",
  "product_url": "{product_url}",
  "variants_found": false,
  "variants": [],
  "total_variants": 0,
  "notes": "No variants available - single product only"
}}

=== CRITICAL RULES ===
✓ Extract ALL variants (don't limit to 3-5)
✓ DO NOT include prices, discounts, or monetary info
✓ Use consistent variant type names (volume, weight, color, pack_size)
✓ Verify URLs are valid
✓ If variant doesn't have separate URL, use main product URL

Begin web search and extraction now. Return ONLY valid JSON.
"""

    return prompt
