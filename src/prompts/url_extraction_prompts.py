"""
Prompts for URL Extraction using Google Gemini 2.0 Flash
Task: Extract brand, product name, and variant from a product URL
"""

def get_url_extraction_prompt(product_url: str) -> str:
    """
    Create prompt for Gemini to extract product details from URL

    Args:
        product_url: Full URL of the product page

    Returns:
        Formatted prompt string for Gemini with Google Search grounding
    """

    prompt = f"""Extract product information from this product page URL using web search.

🔗 PRODUCT URL:
{product_url}

📋 YOUR TASK:
Use Google Search to visit this product page and extract the following information:

1. **Brand Name**: The brand/manufacturer of the product
2. **Product Name**: The specific product name (e.g., "Shampoo for Curls", "Deep Conditioning Mask")
3. **Variant/Size**: The size, volume, weight, or variant (e.g., "250ml", "200g", "500ml")

⚠️ EXTRACTION RULES:
✅ Visit the EXACT URL provided to get current information
✅ Extract brand name exactly as shown on the product page
✅ Extract product name exactly as shown (don't modify or shorten)
✅ Extract variant/size with correct units (ml, g, kg, L, etc.)
✅ Look for variant in product title, specifications, or size selector
✅ Be precise and factual - only extract what you see on the page
✅ If any field is unclear, set extraction_confidence to "medium" or "low"

📊 OUTPUT FORMAT (JSON only, no explanations):

{{
  "brand": "Exact brand name from page",
  "product_name": "Exact product name from page",
  "variant": "Size/variant with units (e.g., 250ml, 200g)",
  "url": "{product_url}",
  "extraction_confidence": "high/medium/low",
  "notes": "Any relevant notes or clarifications"
}}

EXAMPLE OUTPUT:
{{
  "brand": "True Frog",
  "product_name": "Shampoo for Curls",
  "variant": "250ml",
  "url": "https://truefrog.in/products/shampoo-for-curls-250ml",
  "extraction_confidence": "high",
  "notes": "Extracted from product title and specifications"
}}

⚠️ IMPORTANT:
- Only extract from individual product pages (not combo/bundle pages)
- Use the exact spelling and capitalization from the page
- Include units with variant (ml, g, oz, etc.)
- Set confidence based on clarity of information
- Return ONLY valid JSON

Begin web search now and extract product information. Return ONLY JSON."""

    return prompt
