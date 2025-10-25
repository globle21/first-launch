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

You are an e-commerce product query parser that extracts structured information from user search queries.

=== USER QUERY ===
"{user_query}"

=== OBJECTIVE ===
Parse the query to extract:
1. **Brand name**: The company/manufacturer of the product
2. **Product name**: The core product description (excluding brand and variants)
3. **Variant**: Any specific variant mentioned (size, color, volume, etc.)
4. **Has variant**: Boolean flag indicating if a variant was specified

=== PARSING METHODOLOGY ===

**STEP 1: Identify Brand**
- Brands typically appear at the beginning of the query
- Common patterns:
  * Single word: "Dove", "Nivea", "Nykaa"
  * Two words: "True Frog", "Dot & Key", "The Ordinary"
  * With special characters: "L'Oreal", "M&M's", "Johnson & Johnson"
- If uncertain about a brand name, consider the first 1-2 capitalized words
- Preserve special characters and punctuation in brand names

**STEP 2: Extract Product Name**
- The core product description after the brand
- Include descriptive attributes that are part of the product name:
  * "Curl Shampoo", "Anti-Aging Serum", "Vitamin C Face Wash"
- Exclude:
  * Brand name (already captured)
  * Variant information (sizes, colors, quantities)
- Keep product type modifiers: "Deep Conditioning", "Ultra Moisturizing", "Anti-Dandruff"

**STEP 3: Identify Variants**
Look for these variant patterns (usually at the end):
- **Volume**: 30ml, 50ml, 100ml, 250ml, 500ml, 1L, 1 liter, etc.
- **Weight**: 50g, 100g, 250g, 500g, 1kg, etc.
- **Color/Shade**: Red, Blue, Nude, Crimson, Pink, #01, Shade 5, etc.
- **Size**: Small, Medium, Large, S, M, L, XL, XXL, Mini, Travel size
- **Quantity**: 2-pack, 3-pack, Pack of 2, Combo, Set of 3
- **Special sizes**: Trial size, Sample, Travel pack, Economy pack, Family size

**Multiple Variants**: If multiple variants exist, combine them
- Example: "Red 100ml" → variant: "Red 100ml"
- Example: "Large Pack of 2" → variant: "Large Pack of 2"

**STEP 4: Validation**
- Ensure brand and product are separated correctly
- Check if variant information was incorrectly included in product name
- Set has_variant to true only if a variant was identified

=== PARSING EXAMPLES ===

Example 1:
Input: "Dove Beauty Bar 100g"
→ Brand: "Dove"
→ Product: "Beauty Bar"
→ Variant: "100g"
→ Has variant: true

Example 2:
Input: "L'Oreal Paris Revitalift Anti-Aging Cream"
→ Brand: "L'Oreal Paris"
→ Product: "Revitalift Anti-Aging Cream"
→ Variant: null
→ Has variant: false

Example 3:
Input: "The Ordinary Niacinamide 10% Serum 30ml"
→ Brand: "The Ordinary"
→ Product: "Niacinamide 10% Serum"
→ Variant: "30ml"
→ Has variant: true

Example 4:
Input: "Dot & Key Vitamin C Face Wash Travel Size Pack of 2"
→ Brand: "Dot & Key"
→ Product: "Vitamin C Face Wash"
→ Variant: "Travel Size Pack of 2"
→ Has variant: true

=== EDGE CASE HANDLING ===

1. **Unclear Brand Boundaries**: If uncertain where brand ends and product begins, use common sense about what sounds like a brand vs. product descriptor

2. **Missing Information**: 
   - If only product type given (e.g., "Shampoo"), set brand as null
   - If query is too vague, indicate in notes field

3. **Special Characters**: Preserve all punctuation and special characters exactly as they appear

4. **Abbreviations**: Keep as-is (don't expand "ml" to "milliliters")

=== OUTPUT FORMAT (REQUIRED) ===

You MUST return valid JSON in this EXACT format:

{{
  "original_query": "{user_query}",
  "parsed_data": {{
    "brand": "extracted brand or null",
    "product_name": "extracted product name or null",
    "variant": "extracted variant or null",
    "has_variant": true/false
  }}, 
  "confidence": "high/medium/low",
  "notes": "Brief explanation of parsing decisions or issues"
}}

=== CONFIDENCE LEVELS ===
- **high**: All components clearly identified
- **medium**: Most components identified, minor ambiguity
- **low**: Significant ambiguity, missing information, or unclear boundaries

=== CRITICAL REQUIREMENTS ===
✓ Return ONLY valid JSON - no additional text
✓ Use null for missing/unidentified components
✓ Preserve exact spelling and capitalization from the query
✓ Set has_variant to false when variant is null
✓ Include helpful notes about parsing decisions
✓ Do not guess or invent information not present in the query

Parse the query and return the JSON response:
"""

    return prompt
