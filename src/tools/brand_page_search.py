"""
Brand Page Search Tool - Uses Gemini 2.5 Flash with Google Search grounding (REAL-TIME DATA)
Returns STRUCTURED results directly (no post-processing needed)

IMPLEMENTATION:
- Uses newer Gemini SDK with Google Search grounding for real-time accuracy
- Format: genai.Client(api_key) → client.models.generate_content()
- Ensures product/variant data is current and not cached/outdated
- Google Search provides live web data for accurate product availability
"""

import os
import json
import re
from typing import Dict, Optional
from google import genai
from google.genai import types


class OpenAIWebSearchTool:
    """
    Web search specialist using Gemini 2.5 Flash with Google Search grounding

    Role: Performs web searches AND structures results directly
    Returns structured JSON - NO post-processing needed

    Used for:
    - Finding brand pages and products (Stage 2)
    - Finding variants on brand pages (Stage 3)
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize brand page search tool

        Args:
            api_key: Google API key (if None, reads from environment)
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")

        self.client = genai.Client(api_key=self.api_key)
        self.model = "gemini-2.5-flash"  # Gemini 2.5 Flash with Google Search grounding
        self.request_count = 0

    def search_brand_and_product(
        self,
        brand: str,
        product_name: str,
        variant_hint: Optional[str] = None
    ) -> Dict:
        """
        Search for brand page and product using Gemini 2.5 Flash with Google Search

        Returns STRUCTURED results directly - no post-processing needed

        Args:
            brand: Brand name (e.g., "True Frog")
            product_name: Product name (e.g., "Curl Shampoo")
            variant_hint: Optional variant hint from user query

        Returns:
            Dictionary with structured product candidates
        """

        # Build search instruction for Gemini with variant prioritization
        variant_priority = ""
        if variant_hint:
            variant_priority = f"""
VARIANT MATCHING PRIORITY (CRITICAL):
⭐ User specifically mentioned variant: "{variant_hint}"
⭐ PRIORITIZE products that match this variant
⭐ Search specifically for: "{brand} {variant_hint} {product_name}"
⭐ First find products with "{variant_hint}" in the name or description
⭐ If few matches found (<3), then include other related products as backup
⭐ Rank products: exact variant matches first, then others
"""

        search_instruction = f"""
Search the web COMPREHENSIVELY using Google Search to find:

1. Official brand website for "{brand}"
   - Look for {brand}.in or {brand}.com domains
   - Prioritize official brand sites (not retailer sites like Amazon, Flipkart)
   - Verify it's the actual brand website

2. Find products matching "{product_name}" on the brand's website{variant_priority}

SEARCH STRATEGY:
✓ Search for: "{brand} {product_name}" on brand's official website
✓ Search product catalog/shop section thoroughly
✓ Find EVERY variation and type available
✓ Look for different formulations (e.g., "for Dry Hair", "for Normal Hair", "for Oily Hair")
✓ Check product listings, collections, and category pages
✓ Get complete product names EXACTLY as shown on website
✓ Get all WORKING product page URLs

CRITICAL INSTRUCTIONS:
✓ Be EXHAUSTIVE - find ALL relevant products, not just 1-2
✓ ONLY include products that ACTUALLY EXIST on the website
✓ DO NOT hallucinate or create fake product variations
✓ Verify URLs are working and lead to actual product pages
✓ Get exact product names from the website - don't modify them
✓ If there's only ONE version of the product, return only that ONE product
✓ DO NOT include prices
✓ Use Google Search to verify information accuracy

OUTPUT FORMAT (JSON only):
{{{{
  "brand_page_found": true/false,
  "brand_page_url": "https://brand-website.in",
  "products_found": [
    {{{{
      "name": "Exact Product Name from Website",
      "url": "https://brand-website.in/products/exact-product-url",
      "description": "Brief description from website"
    }}}}
  ],
  "match_confidence": "high/medium/low",
  "notes": "Any relevant notes about the search"
}}}}

IMPORTANT:
- Return ONLY products that actually exist on the brand's website
- Use exact product names from the website
- Verify all URLs are valid and working
- If only one product exists, return only one product
- DO NOT create fake variations
- PRIORITIZE variant matching if variant hint provided

Return ONLY valid JSON.
"""

        try:
            print(f"\n🔍 [Gemini] Searching for {brand} {product_name}...")
            if variant_hint:
                print(f"🎯 Prioritizing variant: {variant_hint}")
            print(f"🤖 Using Gemini 2.5 Flash with Google Search grounding")

            # Call Gemini with Google Search grounding
            response = self.client.models.generate_content(
                model=self.model,
                contents=search_instruction,
                config=types.GenerateContentConfig(
                    temperature=0.1,  # Slightly more creative for better search results
                    tools=[types.Tool(google_search=types.GoogleSearch())]  # Enable Google Search
                )
            )

            self.request_count += 1

            # Extract response
            response_text = response.text

            print(f"✅ [Gemini] Search complete")

            # Parse JSON (handle markdown blocks)
            result = self._parse_json_response(response_text)

            if result:
                products = result.get("products_found", [])
                print(f"📋 Found {len(products)} product(s)")
                for i, product in enumerate(products, 1):
                    print(f"   {i}. {product.get('name', 'Unknown')}")
                return result
            else:
                print(f"⚠️ JSON parsing failed")
                print(f"Raw response: {response_text[:500]}")
                return {
                    "brand_page_found": False,
                    "brand_page_url": None,
                    "products_found": [],
                    "match_confidence": "none",
                    "notes": "Failed to parse Gemini response"
                }

        except Exception as e:
            print(f"❌ [Gemini] Search failed: {e}")
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
        Search product page for available variants using Gemini 2.5 Flash with Google Search

        Returns STRUCTURED variant data directly - no post-processing needed

        Args:
            product_name: Confirmed product name
            product_url: Direct URL to product page
            variant_hint: Optional variant hint from user

        Returns:
            Dictionary with structured variants (NO PRICES)
        """

        variant_priority = ""
        if variant_hint:
            variant_priority = f"""
VARIANT MATCHING PRIORITY (CRITICAL):
⭐ User specifically mentioned variant: "{variant_hint}"
⭐ PRIORITIZE finding this specific variant
⭐ If variant exists, ensure it's included in results
⭐ If few variants found (<3), include other available options as backup
"""

        search_instruction = f"""
Visit this product page using Google Search and find ALL available variants COMPREHENSIVELY:

Product: {product_name}
URL: {product_url}{variant_priority}

CRITICAL: Search THOROUGHLY for ALL variants:
- Size/Volume options (50ml, 100ml, 200ml, 250ml, 500ml, 1L, etc.)
- Weight options (50g, 100g, 200g, 250g, 500g, 1kg, etc.)
- Color/Shade options (all color variations)
- Pack sizes (single, 2-pack, 3-pack, combo packs, etc.)
- Formulation types (different variants for different hair/skin types)
- Any other variant types available

SEARCH INSTRUCTIONS:
✓ Use Google Search to access and analyze the product page
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
{{{{
  "product_name": "{product_name}",
  "product_url": "{product_url}",
  "variants_found": true/false,
  "variants": [
    {{{{
      "type": "volume",
      "value": "100ml",
      "url": "https://..." (optional)
    }}}},
    {{{{
      "type": "volume",
      "value": "250ml",
      "url": "https://..." (optional)
    }}}}
  ],
  "total_variants": 2,
  "notes": "Any relevant notes"
}}}}

IMPORTANT:
- Return ONLY variants that actually exist on the product page
- DO NOT create fake variations
- DO NOT include prices or monetary information
- Variant types: volume, weight, color, pack_size, formulation
- If only one variant exists, return only that one
- PRIORITIZE variant matching if variant hint provided

Return ONLY valid JSON.
"""

        try:
            print(f"\n🔍 [Gemini] Searching for variants of {product_name}...")
            if variant_hint:
                print(f"🎯 Prioritizing variant: {variant_hint}")
            print(f"🌐 URL: {product_url[:60]}...")

            # Call Gemini with Google Search grounding
            response = self.client.models.generate_content(
                model=self.model,
                contents=search_instruction,
                config=types.GenerateContentConfig(
                    temperature=0.1,  # Low temperature for factual accuracy
                    tools=[types.Tool(google_search=types.GoogleSearch())]  # Enable Google Search
                )
            )

            self.request_count += 1

            # Extract response
            response_text = response.text

            print(f"✅ [Gemini] Variant search complete")

            # Parse JSON (handle markdown blocks)
            result = self._parse_json_response(response_text)

            if result:
                variants = result.get("variants", [])
                print(f"📋 Found {len(variants)} variant(s) (NO PRICES)")
                for i, variant in enumerate(variants, 1):
                    print(f"   {i}. {variant.get('value', 'Unknown')} ({variant.get('type', 'unknown')})")
                return result
            else:
                print(f"⚠️ JSON parsing failed")
                print(f"Raw response: {response_text[:500]}")
                return {
                    "product_name": product_name,
                    "product_url": product_url,
                    "variants_found": False,
                    "variants": [],
                    "total_variants": 0,
                    "notes": "Failed to parse Gemini response"
                }

        except Exception as e:
            print(f"❌ [Gemini] Variant search failed: {e}")
            return {
                "product_name": product_name,
                "product_url": product_url,
                "variants_found": False,
                "variants": [],
                "total_variants": 0,
                "notes": f"Search error: {str(e)}"
            }

    def _parse_json_response(self, response_text: str) -> Optional[Dict]:
        """
        Parse JSON from Gemini response (handles markdown blocks)

        Args:
            response_text: Raw response from Gemini

        Returns:
            Parsed dictionary or None
        """
        # Strategy 1: Direct JSON parse
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # Strategy 2: Extract JSON from markdown (```json)
        try:
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_str = response_text[start:end].strip()
                return json.loads(json_str)
        except:
            pass

        # Strategy 3: Extract JSON from markdown (``` without language)
        try:
            if response_text.strip().startswith("```"):
                temp = response_text.strip()[3:]
                start = temp.find("{")
                if start != -1:
                    # Count braces to find matching closing brace
                    brace_count = 0
                    for i in range(start, len(temp)):
                        if temp[i] == '{':
                            brace_count += 1
                        elif temp[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_str = temp[start:i+1]
                                return json.loads(json_str)
        except:
            pass

        # Strategy 4: Extract JSON object
        try:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start != -1 and end > start:
                json_str = response_text[start:end]
                return json.loads(json_str)
        except:
            pass

        return None

    def get_usage_stats(self) -> Dict:
        """Get API usage statistics"""
        return {
            "tool": "Gemini 2.5 Flash with Google Search",
            "requests": self.request_count,
            "estimated_cost_usd": round(self.request_count * 0.001, 6)  # ~$0.001 per request
        }
