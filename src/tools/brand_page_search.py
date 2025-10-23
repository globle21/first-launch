"""
OpenAI Web Search Tool - Uses GPT-4o for superior web search quality
Returns STRUCTURED results directly (no Gemini processing needed)
"""

import os
import json
from typing import Dict, Optional
from openai import OpenAI


class OpenAIWebSearchTool:
    """
    Web search specialist using GPT-4o

    Role: Performs web searches AND structures results directly
    Returns structured JSON - NO Gemini processing needed

    Used for:
    - Finding brand pages and products (Stage 2)
    - Finding variants on brand pages (Stage 3)
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenAI web search tool

        Args:
            api_key: OpenAI API key (if None, reads from environment)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4.1-mini"  # GPT-4o has superior web search
        self.request_count = 0

    def search_brand_and_product(
        self,
        brand: str,
        product_name: str,
        variant_hint: Optional[str] = None
    ) -> Dict:
        """
        Search for brand page and product using GPT-4o web search

        Returns STRUCTURED results directly - no Gemini processing needed

        Args:
            brand: Brand name (e.g., "True Frog")
            product_name: Product name (e.g., "Curl Shampoo")
            variant_hint: Optional variant hint from user query

        Returns:
            Dictionary with structured product candidates
        """

        # Build search instruction for GPT-4o
        variant_context = ""
        if variant_hint:
            variant_context = f"\nUser mentioned variant: {variant_hint}"

        search_instruction = f"""
Search the web COMPREHENSIVELY to find:

1. Official brand website for "{brand}"
   - Look for {brand}.in or {brand}.com domains
   - Prioritize official brand sites (not retailer sites)

2. Find ALL products matching "{product_name}" on the brand's website
   - Search the entire product catalog/shop section
   - Find EVERY variation and type of "{product_name}"
   - Look for different formulations (e.g., "for Dry Hair", "for Normal Hair", "for Oily Hair")
   - Check product listings, collections, and category pages
   - Get complete product names EXACTLY as shown on website
   - Get all WORKING product page URLs{variant_context}

CRITICAL INSTRUCTIONS:
✓ Be EXHAUSTIVE - find ALL products related to "{product_name}", not just 1-2
✓ ONLY include products that ACTUALLY EXIST on the website
✓ DO NOT hallucinate or create fake product variations
✓ Verify URLs are working and lead to actual product pages
✓ Get exact product names from the website - don't modify them
✓ If there's only ONE version of the product, return only that ONE product
✓ DO NOT include prices

OUTPUT FORMAT (JSON only):
{{
  "brand_page_found": true/false,
  "brand_page_url": "https://truefrog.in",
  "products_found": [
    {{
      "name": "Exact Product Name from Website",
      "url": "https://truefrog.in/products/exact-product-url",
      "description": "Brief description from website"
    }}
  ],
  "match_confidence": "high/medium/low",
  "notes": "Any relevant notes"
}}

IMPORTANT:
- Return ONLY products that actually exist on the brand's website
- Use exact product names from the website
- Verify all URLs are valid and working
- If only one product exists, return only one product
- DO NOT create fake variations

Return ONLY valid JSON.
"""

        try:
            print(f"\n🔍 [OpenAI] Searching for {brand} {product_name}...")
            print(f"🤖 Using GPT-4.1-mini with web search (superior quality)")

            # GPT-4o automatically uses web search when appropriate
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a web search assistant. Search the web and return ONLY factual information found on websites. Return structured JSON. DO NOT hallucinate or create fake data."
                    },
                    {
                        "role": "user",
                        "content": search_instruction
                    }
                ],
                temperature=0.1,  # Very low temperature for factual accuracy
                response_format={"type": "json_object"}  # Force JSON output
            )

            self.request_count += 1

            # Extract response
            response_text = response.choices[0].message.content

            print(f"✅ [OpenAI] Search complete")

            # Parse JSON
            try:
                result = json.loads(response_text)
                products = result.get("products_found", [])
                print(f"📋 Found {len(products)} product(s)")
                for i, product in enumerate(products, 1):
                    print(f"   {i}. {product.get('name', 'Unknown')}")

                return result

            except json.JSONDecodeError as e:
                print(f"⚠️ JSON parsing failed: {e}")
                print(f"Raw response: {response_text[:500]}")
                return {
                    "brand_page_found": False,
                    "brand_page_url": None,
                    "products_found": [],
                    "match_confidence": "none",
                    "notes": f"JSON parsing error: {str(e)}"
                }

        except Exception as e:
            print(f"❌ [OpenAI] Search failed: {e}")
            return {
                "brand_page_found": False,
                "brand_page_url": None,
                "products_found": [],
                "match_confidence": "none",
                "notes": f"Search error: {str(e)}"
            }

    def search_product_variants(
        self,
        product_name: str,
        product_url: str,
        variant_hint: Optional[str] = None
    ) -> Dict:
        """
        Search product page for available variants using GPT-4o web search

        Returns STRUCTURED variant data directly - no Gemini processing needed

        Args:
            product_name: Confirmed product name
            product_url: Direct URL to product page
            variant_hint: Optional variant hint from user

        Returns:
            Dictionary with structured variants (NO PRICES)
        """

        variant_context = ""
        if variant_hint:
            variant_context = f"\nUser is interested in: {variant_hint}"

        search_instruction = f"""
Visit this product page and find ALL available variants COMPREHENSIVELY:

Product: {product_name}
URL: {product_url}{variant_context}

CRITICAL: Search THOROUGHLY for ALL variants:
- Size/Volume options (50ml, 100ml, 200ml, 250ml, 500ml, 1L, etc.)
- Weight options (50g, 100g, 200g, 250g, 500g, 1kg, etc.)
- Color/Shade options (all color variations)
- Pack sizes (single, 2-pack, 3-pack, combo packs, etc.)
- Formulation types (different variants for different hair/skin types)
- Any other variant types available

SEARCH INSTRUCTIONS:
✓ Check dropdown menus, variant selectors, size options
✓ Look for "Select Size", "Choose Variant", "Available in" sections
✓ Check product details, specifications, and variant tables
✓ Find EVERY single variant option available - don't stop at 2-3
✓ Include variant-specific URLs if available
✓ Be EXHAUSTIVE - list ALL variants you find
✓ ONLY include variants that ACTUALLY EXIST on the product page
✓ DO NOT hallucinate or create fake variants
✓ DO NOT include prices

OUTPUT FORMAT (JSON only):
{{
  "product_name": "{product_name}",
  "product_url": "{product_url}",
  "variants_found": true/false,
  "variants": [
    {{
      "type": "volume",
      "value": "100ml",
      "url": "https://..." (optional)
    }},
    {{
      "type": "volume",
      "value": "250ml",
      "url": "https://..." (optional)
    }}
  ],
  "total_variants": 2,
  "notes": "Any relevant notes"
}}

IMPORTANT:
- Return ONLY variants that actually exist on the product page
- DO NOT create fake variations
- DO NOT include prices or monetary information
- Variant types: volume, weight, color, pack_size, formulation
- If only one variant exists, return only that one

Return ONLY valid JSON.
"""

        try:
            print(f"\n🔍 [OpenAI] Searching for variants of {product_name}...")
            print(f"🌐 URL: {product_url[:60]}...")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a web search assistant. Visit product pages and return ONLY factual variant information found. Return structured JSON. DO NOT hallucinate or create fake variants. DO NOT include prices."
                    },
                    {
                        "role": "user",
                        "content": search_instruction
                    }
                ],
                temperature=0.1,  # Very low temperature for factual accuracy
                response_format={"type": "json_object"}  # Force JSON output
            )

            self.request_count += 1

            # Extract response
            response_text = response.choices[0].message.content

            print(f"✅ [OpenAI] Variant search complete")

            # Parse JSON
            try:
                result = json.loads(response_text)
                variants = result.get("variants", [])
                print(f"📋 Found {len(variants)} variant(s) (NO PRICES)")
                for i, variant in enumerate(variants, 1):
                    print(f"   {i}. {variant.get('value', 'Unknown')} ({variant.get('type', 'unknown')})")

                return result

            except json.JSONDecodeError as e:
                print(f"⚠️ JSON parsing failed: {e}")
                print(f"Raw response: {response_text[:500]}")
                return {
                    "product_name": product_name,
                    "product_url": product_url,
                    "variants_found": False,
                    "variants": [],
                    "total_variants": 0,
                    "notes": f"JSON parsing error: {str(e)}"
                }

        except Exception as e:
            print(f"❌ [OpenAI] Variant search failed: {e}")
            return {
                "product_name": product_name,
                "product_url": product_url,
                "variants_found": False,
                "variants": [],
                "total_variants": 0,
                "notes": f"Search error: {str(e)}"
            }

    def get_usage_stats(self) -> Dict:
        """Get API usage statistics"""
        return {
            "tool": "OpenAI GPT-4o Web Search",
            "requests": self.request_count,
            "estimated_cost_usd": round(self.request_count * 0.03, 4)  # ~$0.03 per request
        }
