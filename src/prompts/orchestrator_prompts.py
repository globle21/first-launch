"""
Prompts for Orchestrator (Gemini 2.5 Flash)
Task: Parse user input, coordinate workflow, manage confirmations
"""


def get_input_parsing_prompt(user_query: str) -> str:
    """
    Generate prompt for parsing user input to extract brand, product, variant

    Args:
        user_query: Raw user input from landing page

    Returns:
        Formatted prompt for Gemini 2.5 Flash
    """

    prompt = f"""
TASK: PARSE USER PRODUCT QUERY

You are analyzing a user's product search query to extract structured information.

=== USER QUERY ===
"{user_query}"

=== OBJECTIVE ===
Extract the following information:
1. **Brand name**: The company/brand that makes the product
2. **Product name**: The specific product (without brand and variant)
3. **Variant**: Specific variant mentioned (size, color, volume, etc.) - if any
4. **Has variant**: Boolean indicating if user mentioned a variant

=== PARSING RULES ===

**Brand Extraction**:
- Usually the first 1-2 words
- Examples: "Nykaa", "True Frog", "Mamaearth", "Plum", "Dot & Key"
- Can be single word or two words

**Product Name Extraction**:
- The core product description (without brand and variant)
- Examples: "Curl Shampoo", "Matte Lipstick", "Face Serum", "Hair Mask"
- Exclude brand name and variant info

**Variant Extraction**:
- Volume: 50ml, 100ml, 250ml, 500ml, 1L, etc.
- Weight: 50g, 100g, 250g, 500g, 1kg, etc.
- Color/Shade: Red, Blue, Nude, Crimson, etc.
- Size: Small, Medium, Large, S, M, L, XL, XXL
- Pack: 2-pack, 3-pack, Pack of 2, etc.
- Type: Travel size, Full size, Regular, Mini

**Examples**:

Input: "True Frog Curl Shampoo"
→ Brand: "True Frog"
→ Product: "Curl Shampoo"
→ Variant: null
→ Has variant: false

Input: "True Frog Curl Shampoo 100ml"
→ Brand: "True Frog"
→ Product: "Curl Shampoo"
→ Variant: "100ml"
→ Has variant: true

Input: "Nykaa Matte Lipstick Red"
→ Brand: "Nykaa"
→ Product: "Matte Lipstick"
→ Variant: "Red"
→ Has variant: true

Input: "Mamaearth Vitamin C Face Serum 30ml"
→ Brand: "Mamaearth"
→ Product: "Vitamin C Face Serum"
→ Variant: "30ml"
→ Has variant: true

=== EXPECTED OUTPUT FORMAT ===

Return valid JSON in this EXACT format:

{{
  "original_query": "{user_query}",
  "parsed_data": {{
    "brand": "True Frog",
    "product_name": "Curl Shampoo",
    "variant": "100ml",
    "has_variant": true
  }},
  "confidence": "high",
  "notes": "Successfully extracted all components"
}}

=== ERROR HANDLING ===

If parsing is ambiguous or uncertain:
{{
  "original_query": "{user_query}",
  "parsed_data": {{
    "brand": "...",
    "product_name": "...",
    "variant": null,
    "has_variant": false
  }},
  "confidence": "low",
  "notes": "Brand name unclear - may need user clarification"
}}

=== CRITICAL RULES ===
✓ Extract ONLY what's clearly present in the query
✓ Don't make assumptions about missing information
✓ Variant should be null if not mentioned (don't guess)
✓ Return valid JSON only

Parse the query now and return ONLY valid JSON.
"""

    return prompt
