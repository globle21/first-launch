"""
Prompts for ProductConfirmationAgent (Gemini 2.5 Flash with Google Search)
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
        Formatted prompt string for Gemini 2.5 Flash
    """

    variant_priority = ""
    search_strategy = f'"{brand} official website India"'

    if variant_hint:
        # OPTION B: Flexible Matching - Prioritize variant matches but include backups
        variant_priority = f"""

=== VARIANT MATCHING PRIORITY (CRITICAL) ===
⭐ User specifically requested variant: "{variant_hint}"
⭐ This is a HIGH PRIORITY requirement - focus search on this variant

SEARCH STRATEGY:
1. Primary search: "{brand} {variant_hint} {product_name}"
2. Verify products match the "{variant_hint}" variant exactly
3. PRIORITIZE products with "{variant_hint}" in name/description
4. If fewer than 3 matches found, include other related products as backup
5. RANK results: exact variant matches FIRST, then others

MATCHING RULES:
✓ "{variant_hint}" must be present in product name, title, or specifications
✓ Exact match preferred (e.g., "black" matches "Black Shoes")
✓ Close variants acceptable if exact not found (e.g., "black/white" for "black")
✗ Do NOT ignore the variant - it's not optional
✗ Generic products without variant info should be ranked lower
"""
        search_strategy = f'"{brand} {variant_hint} {product_name}"'

    prompt = f"""
TASK: FIND BRAND PAGE AND CONFIRM SPECIFIC PRODUCT MODELS

You are a product verification assistant with web search capabilities. Your task is to find SPECIFIC PRODUCT MODELS (not category pages) on official brand websites.

⚠️ CRITICAL REQUIREMENT: Only return individual products with unique model names/identifiers.
❌ DO NOT return category pages, filter pages, or generic product types.
✓ DO return specific models like "Air Force 1 '07", "Dunk Low Retro", "Precision V", etc.

=== INPUT PARAMETERS ===
Brand: {brand}
Product: {product_name}
Variant Requested: {variant_hint if variant_hint else "None (any variant acceptable)"}{variant_priority}

=== EXECUTION STEPS ===

STEP 1: SEARCH FOR OFFICIAL BRAND WEBSITE
Execute web search with query: {search_strategy}

Alternative searches if needed:
- "{brand} official website India"
- "{brand} official site"
- "{brand} India online store"
- "{brand} buy online official"

Identify the OFFICIAL brand website by looking for:
✓ Domain containing brand name
✓ .com, .in, or .co.in domains
✓ "Official" in title or description
✗ REJECT: Amazon, Flipkart, Nykaa, Myntra (these are marketplaces, not brand sites)
✗ REJECT: Review sites, blogs, social media pages

STEP 2: VERIFY AND EXPLORE BRAND WEBSITE
Once official site is identified:
1. Visit the brand's official website URL
2. Look for product catalog sections like:
   - "Products", "Shop", "Our Products"
   - "Categories", "Collections"
   - Search bar on the website

STEP 3: SEARCH FOR SPECIFIC PRODUCT MODELS (NOT CATEGORY PAGES)
Execute web search: "site:{{{{brand_domain}}}} {brand} {variant_hint + ' ' if variant_hint else ''}{product_name}"

CRITICAL: Find SPECIFIC PRODUCT MODELS with unique names/identifiers

✓ INCLUDE - Examples of VALID specific products:
  - Shoes: "Nike Air Force 1 '07", "Adidas Ultraboost 22", "Puma Suede Classic"
  - Beauty: "Maybelline Fit Me Foundation Shade 220", "Lakme 9to5 Lipstick Crimson Charm"
  - Electronics: "Sony WH-1000XM5", "Samsung Galaxy S24 Ultra", "Dell XPS 15 9530"
  - Food: "Nestlé KitKat 4-Finger Chocolate Bar", "Maggi 2-Minute Masala Noodles"
  - Clothing: "Levi's 501 Original Fit Jeans", "Nike Dri-FIT Running Shirt"

✓ INCLUDE: Products with unique identifiers, SKUs, or model numbers
✓ INCLUDE: Direct product pages with "Buy" or "Add to Cart" buttons
✓ INCLUDE: Products where you can see detailed specifications

✗ EXCLUDE - Examples of INVALID category/filter pages:
  - Generic categories: "Black Basketball Shoes", "Men's Shoes", "Running Shoes"
  - Filter pages: "Lipsticks Under ₹500", "Red Color Products"
  - Product types: "Shampoo", "Smartphones", "Laptops", "Jeans"
  - Collection pages: "New Arrivals", "Best Sellers", "Sale Items"
  - Size/color filters without model: "Large Shirts", "Blue Shoes"

Alternative product search strategies:
- Browse product categories → Click into individual products (NOT the category itself)
- Use site's internal search → Select specific products from results
- Search with variant: "{{{{brand_domain}}}} {product_name} {variant_hint if variant_hint else ''}"
- Look for model names/numbers in product titles

STEP 4: EXTRACT SPECIFIC PRODUCT DETAILS
For EACH specific product model found, collect:
1. **Full product name with model identifier** (e.g., "Nike Air Force 1 '07 Black" NOT just "Black Shoes")
2. Direct product page URL (must go to single product, not category)
3. Product description (1-2 sentences from product page)

PRODUCT VALIDATION DECISION TREE:

Ask yourself these questions for EACH product before including it:

1. Does the product name have a SPECIFIC model/identifier?
   - ✓ YES: "Air Force 1 '07", "Fit Me Foundation Shade 220", "Galaxy S24 Ultra"
   - ✗ NO: "Basketball Shoes", "Foundation", "Smartphones" → REJECT

2. Does the URL go to a SINGLE product page?
   - ✓ YES: URL like /product/air-force-1-07 or /p/fit-me-foundation-220
   - ✗ NO: URL like /category/shoes or /filter/black-products → REJECT

3. Can you see a "Buy" / "Add to Cart" / "Add to Bag" button on the page?
   - ✓ YES: It's a purchase page → INCLUDE
   - ✗ NO: It's likely a category/listing page → REJECT

4. Does the product name sound like a category or generic type?
   - ✓ NO: "Dunk Low Retro", "9to5 Lipstick Crimson" → INCLUDE
   - ✗ YES: "Black Shoes", "Lipsticks", "Men's Clothing" → REJECT

5. Would a customer know EXACTLY which product they're buying from the name alone?
   - ✓ YES: Specific enough → INCLUDE
   - ✗ NO: Too vague → REJECT

If you answer YES/NO/YES/NO/YES to all 5 questions → INCLUDE the product
If any answer doesn't match → REJECT the product

IMPORTANT: Do NOT collect or mention prices anywhere in your response.

=== REQUIRED JSON OUTPUT FORMAT ===

SCENARIO 1: Product(s) Found Successfully
{{
  "brand_page_found": "true",
  "brand_page_url": "https://[brand-website].com",
  "products_found": [
    {
      "name": "[exact product name from website]",
      "url": "https://[brand-website].com/products/[product-page]",
      "description": "[brief 1-2 sentence description]"
    }
  ],
  "match_confidence": "high",
  "notes": "Found [X] matching products on official brand website"
}}

SCENARIO 2: Brand Website Not Found
{{
  "brand_page_found": "false",
  "brand_page_url": null,
  "products_found": [],
  "match_confidence": "none",
  "notes": "Could not find official brand website for {brand}"
}}  

SCENARIO 3: Brand Found but Product Not Available
{{
  "brand_page_found": "true",
  "brand_page_url": "https://[brand-website].com",
  "products_found": [],
  "match_confidence": "none",
  "notes": "Brand page found but product '{product_name}' not available"
}}

SCENARIO 4: Multiple Specific Products Found (WITH VARIANT PRIORITIZATION)
{{
  "brand_page_found": "true",
  "brand_page_url": "https://nike.com/in",
  "products_found": [
    {
      "name": "Nike Air Force 1 '07 Black",
      "url": "https://nike.com/in/t/air-force-1-07-shoe-xxx",
      "description": "Classic basketball shoe with black leather upper. Exact match for black variant."
    },
    {
      "name": "Nike Dunk Low Retro Black/White",
      "url": "https://nike.com/in/t/dunk-low-retro-shoe-yyy",
      "description": "Iconic sneaker with black and white colorway. Contains requested black variant."
    },
    {
      "name": "Nike Court Vision Low Black",
      "url": "https://nike.com/in/t/court-vision-low-shoe-zzz",
      "description": "Modern court-inspired sneaker in all black. Exact match."
    }
  ],
  "match_confidence": "high",
  "notes": "Found 3 specific product models with black variant. All include model names (Air Force 1 '07, Dunk Low Retro, Court Vision Low)."
}}

SCENARIO 4 - WRONG (DO NOT DO THIS):
{{
  "brand_page_found": "true",
  "brand_page_url": "https://nike.com/in",
  "products_found": [
    {
      "name": "Black Basketball Shoes",  // ❌ WRONG - This is a category page
      "url": "https://nike.com/in/w/black-basketball-shoes-xxx",  // ❌ Category URL
      "description": "Collection of black basketball shoes"
    },
    {
      "name": "Men's Black Shoes",  // ❌ WRONG - Generic category
      "url": "https://nike.com/in/w/mens-black-shoes",  // ❌ Filter page
      "description": "Filter page showing multiple products"
    }
  ],
  "match_confidence": "low",
  "notes": "❌ INVALID - These are category pages, not specific products"
}}

=== CONFIDENCE LEVELS ===
- "high": Exact product match found with requested variant (if specified)
- "medium": Product found but variant doesn't match exactly, or multiple mixed options
- "low": Similar products found but not exact match, mostly backup options
- "none": No matching products found

=== VALIDATION CHECKLIST ===
Before returning JSON, verify:
□ Brand URL is the official website (not a marketplace)
□ Product URLs link directly to product pages (not category pages)
□ No prices are mentioned anywhere in the response
□ All found products are included (don't filter, let user choose)
□ JSON is valid and follows exact structure above
□ JSON contains ONLY these fields: brand_page_found, brand_page_url, products_found, match_confidence, notes
□ products_found array contains ONLY: name, url, description (no extra fields)

=== CRITICAL RULES FOR GEMINI ===
1. ALWAYS use web search - do not rely on training data for URLs
2. Find SPECIFIC PRODUCT MODELS - NOT category/filter pages
   ✓ Good: "Nike Air Force 1 '07 Black", "Nike Dunk Low Retro Black/White"
   ✗ Bad: "Black Basketball Shoes", "Men's Black Shoes", "Black Running Shoes"
3. IF VARIANT SPECIFIED: Prioritize exact variant matches, rank them first in results
4. Include ALL matching SPECIFIC products - exact matches first, then backup options
5. NEVER include price information in any field
6. NEVER include category pages, filter pages, or product listing pages
7. Each product MUST have a unique model name or identifier in the name field
8. If website requires login/subscription, note this in "notes" field
9. For Indian brands, prioritize .in domains
10. Return ONLY the JSON response, no additional text or explanation
11. Use exact text from websites for product names (preserve capitalization, spelling)
12. Verify all URLs go to INDIVIDUAL product pages (not category pages)
13. DO NOT add any extra fields to the JSON structure
14. Variant matching is NOT optional - when specified, it's a priority requirement

=== SPECIAL CASES ===
- If brand has multiple websites (.com and .in), prefer Indian (.in) version
- If product appears "out of stock", still include it in results
- **Variant Handling**:
  * When variant specified: Search specifically for that variant first
  * Rank exact variant matches at the top of products_found array
  * Include 2-3 backup options if available (but rank them lower)
  * If variant doesn't exist: show all available variants with note
  * Color variants (black, red, etc.): treat as critical search criteria
- For beauty/cosmetic products with shades, list each shade as separate product entry
- Multi-word variants: treat as single unit (e.g., "Pack of 2", "Travel Size")

=== ERROR HANDLING ===
If any error occurs during search:
{{
  "brand_page_found": "false",
  "brand_page_url": null,
  "products_found": [],
  "match_confidence": "none",
  "notes": "Error: [describe what went wrong]"
}}

=== FINAL CHECKLIST (Before submitting your response) ===

Before you return your JSON, verify EVERY product in products_found array:

□ Each product has a UNIQUE MODEL NAME or IDENTIFIER in the name field?
   Example: ✓ "Air Max 90" NOT ✗ "Running Shoes"

□ Each product URL goes to a SINGLE PRODUCT PAGE, not a category?
   Check the URL structure - does it have /product/, /p/, or specific product slug?

□ You can find "Add to Cart" or "Buy" button on each product page?
   If the page shows multiple products with filters, it's a category page → REMOVE IT

□ Product names are NOT generic categories?
   ✓ Keep: "Nike Air Force 1 '07 Black"
   ✗ Remove: "Black Basketball Shoes", "Men's Shoes"

□ Product names include SPECIFIC details (model, variant, color, size)?
   ✓ Keep: "Maybelline Fit Me Foundation Shade 220 Natural Beige"
   ✗ Remove: "Foundation", "Beige Foundation"

□ You did NOT include any pricing information?
   Double-check description field - no "₹", "$", "Rs", "price" mentions

If any product in your list fails ANY of these checks → REMOVE IT from products_found array

Execute web search now and return ONLY valid JSON response with the EXACT structure specified above.
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
        Formatted prompt string for Gemini 2.5 Flash
    """

    variant_context = ""
    if variant_hint:
        variant_context = f"\nNote: User is interested in the '{variant_hint}' variant (if available)."

    prompt = f"""
TASK: EXTRACT ALL PRODUCT VARIANTS (NO PRICES!)

You are analyzing a product page to extract all available variants. Use web search to visit the product page and identify all variant options.

=== INPUT PARAMETERS ===
Product Name: {product_name}
Product URL: {product_url}
User's Requested Variant (if any): {variant_context}

=== EXECUTION STEPS ===

STEP 1: ACCESS THE PRODUCT PAGE
Navigate to the provided URL: {product_url}
Verify the page has loaded and shows the product details.

STEP 2: IDENTIFY VARIANT SELECTOR ELEMENTS
Look for these common variant selector patterns on the page:
- Dropdown menus labeled: "Size", "Volume", "Color", "Shade", "Pack", "Quantity"
- Radio buttons or clickable options for different variants
- Product options section with buttons/links
- "Choose your size/color" sections
- Multiple product images showing different colors/shades

STEP 3: EXTRACT ALL VARIANT INFORMATION
For EACH variant option found, capture:

**Variant Categories to Extract:**
1. **Volume** (for liquids): 30ml, 50ml, 100ml, 250ml, 500ml, 1L, 1 Liter
2. **Weight** (for solids): 50g, 100g, 250g, 500g, 1kg, 1 Kilogram
3. **Color/Shade**: Specific color names, shade numbers, or codes
4. **Pack Size**: Single, Duo, Trio, Pack of 2, Pack of 3, Combo, Set
5. **Size**: Mini, Travel Size, Regular, Full Size, Small, Medium, Large
6. **Quantity**: 1 piece, 2 pieces, 3 pieces, etc.

STEP 4: DETERMINE VARIANT URLS
For each variant, check if:
- Clicking the variant changes the URL (capture the unique URL)
- Variants have separate product pages (capture each URL)
- All variants share the same URL (use the main product URL for all)

STEP 5: CLASSIFY VARIANT TYPES
Map each variant to the correct type:
- Anything with ml, liter, L → type: "volume"
- Anything with g, kg, gram, kilogram → type: "weight"  
- Color names or shade identifiers → type: "color"
- Pack/Set/Combo references → type: "pack_size"
- Size descriptors (Mini, Travel, etc.) → type: "size"
- Numeric quantities → type: "quantity"

=== REQUIRED JSON OUTPUT FORMAT ===

SCENARIO 1: Multiple Variants Found
{{
  "product_name": "{product_name}",
  "product_url": "{product_url}",
  "variants_found": true,
  "variants": [
    {
      "type": "volume",
      "value": "100ml",
      "url": "https://[full-variant-url]"
    },
    {
      "type": "volume", 
      "value": "250ml",
      "url": "https://[full-variant-url]"
    },
    {
      "type": "volume",
      "value": "500ml",
      "url": "https://[full-variant-url]"
    }
  ],
  "total_variants": 3,
  "notes": "Found 3 volume variants available"
}}

SCENARIO 2: No Variants (Single Product)
{{
  "product_name": "{product_name}",
  "product_url": "{product_url}",
  "variants_found": false,
  "variants": [],
  "total_variants": 0,
  "notes": "No variants available - single product only"
}}

SCENARIO 3: Multiple Variant Types (e.g., Size AND Color)
{{
  "product_name": "{product_name}",
  "product_url": "{product_url}",
  "variants_found": true,
  "variants": [
    {
      "type": "volume",
      "value": "100ml",
      "url": "https://[url]"
    },
    {
      "type": "volume",
      "value": "250ml",
      "url": "https://[url]"
    },
    {
      "type": "color",
      "value": "Red",
      "url": "https://[url]"
    },
    {
      "type": "color",
      "value": "Pink",
      "url": "https://[url]"
    }
  ],
  "total_variants": 4,
  "notes": "Found 2 volume variants and 2 color variants"
}}

=== VALIDATION CHECKLIST ===
Before returning JSON, verify:
□ All visible variants on the page are included
□ No price information appears anywhere in the response
□ Variant types use standard names: volume, weight, color, pack_size, size, quantity
□ total_variants matches the actual count in variants array
□ URLs are complete (include https://) and valid
□ JSON structure matches exactly (no extra fields)
□ variants_found is true if variants array has items, false if empty

=== STANDARDIZED TYPE NAMES ===
Use ONLY these type values:
- "volume" - for liquid measurements (ml, L)
- "weight" - for solid measurements (g, kg)
- "color" - for colors and shades
- "pack_size" - for multi-packs or sets
- "size" - for size descriptors (Mini, Travel, Regular)
- "quantity" - for numeric quantities

=== CRITICAL RULES FOR GEMINI ===
1. Visit the actual product page - do not guess variants
2. Extract ALL variants visible on the page (could be 1 to 50+)
3. NEVER include prices, discounts, or any monetary values
4. If variant URL is same as main URL, still include it
5. Do not skip variants even if they're "out of stock"
6. Return ONLY the JSON response, no explanatory text
7. Preserve exact variant names from the website
8. Count variants accurately for total_variants field

=== SPECIAL CASES ===
- **Lipstick/Makeup**: Each shade is a separate variant entry
- **Multipacks**: "Pack of 3" is one variant, not 3
- **Size + Color combos**: List each combination separately if they exist
- **Out of stock**: Still include the variant in the list
- **Price differences**: Ignore - we only care about variant options, not prices

=== ERROR HANDLING ===
If page cannot be accessed:
{{  
  "product_name": "{product_name}",
  "product_url": "{product_url}",
  "variants_found": false,
  "variants": [],
  "total_variants": 0,
  "notes": "Error: Could not access product page"
}}

Execute web search to visit the product page and return ONLY valid JSON with the EXACT structure specified above. 
"""

    return prompt
