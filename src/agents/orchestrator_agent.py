"""
OrchestratorAgent - Main coordinator using Gemini 2.5 Flash
Manages workflow, parses input, coordinates specialized agents
"""

import os
import json
import re
from typing import Dict, Optional
from google import genai


class OrchestratorAgent:
    """
    Main orchestrator agent using Gemini 2.5 Flash

    Current Responsibilities:
    1. Parse user input (extract brand, product, variant) - NO WEB SEARCH

    Deprecated Methods (no longer used):
    2. process_product_search_results() - DEPRECATED: Gemini 2.5 Flash now returns structured data
    3. process_variant_search_results() - DEPRECATED: Gemini 2.5 Flash now returns structured data

    IMPORTANT: This agent NEVER does web searches for product/variant discovery
    - Gemini 2.5 Flash (in ProductConfirmationAgent) does web searches AND structuring with Google Search grounding
    - OrchestratorAgent only parses user input (cheap and fast)
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize orchestrator with Gemini 2.5 Flash

        Args:
            api_key: Google API key (optional)
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")

        self.client = genai.Client(api_key=self.api_key)
        self.model = "gemini-2.5-flash"
        self.request_count = 0
        self.name = "OrchestratorAgent"

    def parse_user_input(self, user_query: str) -> Dict:
        """
        Parse user query to extract brand, product name, and variant

        Args:
            user_query: Raw user input from landing page

        Returns:
            Dictionary with parsed components
        """
        from ..prompts.orchestrator_prompts import get_input_parsing_prompt

        print("\n" + "="*70)
        print(f"🤖 {self.name}: Parsing user input")
        print("="*70)
        print(f"📝 User query: '{user_query}'")

        # Generate prompt
        prompt = get_input_parsing_prompt(user_query)

        try:
            # Call Gemini 2.5 Flash
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )

            self.request_count += 1

            response_text = response.text

            print("\n" + "="*70)
            print("📋 RAW PARSING RESULT:")
            print("="*70)
            print(response_text[:600] if len(response_text) > 600 else response_text)
            if len(response_text) > 600:
                print(f"\n... (truncated)")
            print()

            # Parse JSON response
            result = self._parse_json_response(response_text)

            if result:
                print("✅ Successfully parsed user input")
                parsed = result.get("parsed_data", {})
                print(f"   Brand: {parsed.get('brand')}")
                print(f"   Product: {parsed.get('product_name')}")
                print(f"   Variant: {parsed.get('variant') or 'Not specified'}")
                print(f"   Has variant: {parsed.get('has_variant')}")
                return result
            else:
                print("⚠️ Could not parse JSON, using fallback parser")
                # Fallback to simple parsing
                from ..utils.parsers import parse_user_query
                parsed = parse_user_query(user_query)
                return {
                    "original_query": user_query,
                    "parsed_data": parsed,
                    "confidence": "medium",
                    "notes": "Used fallback parser"
                }

        except Exception as e:
            print(f"❌ Parsing failed: {e}")
            # EMERGENCY FALLBACK: Use regex parser
            print("⚠️ Using emergency fallback parser (regex)")
            from ..utils.parsers import parse_user_query_fallback
            parsed = parse_user_query_fallback(user_query)
            return {
                "original_query": user_query,
                "parsed_data": parsed,
                "confidence": "low",
                "notes": f"Error during parsing: {str(e)} - Used fallback"
            }

    def process_product_search_results(self, raw_search_results: str, brand: str, product_name: str) -> Dict:
        """
        DEPRECATED: This method is no longer used.
        Gemini 2.5 Flash (in ProductConfirmationAgent) now returns structured JSON directly.

        This method was causing hallucinations (creating fake products/variants).
        Kept for backward compatibility but should not be called.

        Args:
            raw_search_results: Raw text from web search
            brand: Brand name
            product_name: Product name

        Returns:
            Dictionary with structured product candidates
        """
        print("⚠️ WARNING: process_product_search_results() is DEPRECATED and should not be called")

        processing_prompt = f"""
You are processing web search results to identify product candidates.

SEARCH RESULTS (from web search):
{raw_search_results}

USER IS LOOKING FOR:
Brand: {brand}
Product: {product_name}

TASK: Analyze the search results and extract ALL product candidates

Extract:
1. Brand page URL (official website)
2. ALL products that match or relate to "{product_name}"
3. For each product:
   - Exact product name (as shown on website)
   - Direct product URL
   - Brief description (1-2 sentences)

CRITICAL RULES:
✓ Extract information from the search results provided above
✓ DO NOT do any web searches yourself
✓ DO NOT include prices
✓ Include ALL products found - don't limit to just 1-2
✓ Include products with different formulations (e.g., "for Dry Hair", "for Normal Hair")
✓ Include all variations and types mentioned
✓ Return ONLY products from the official brand page
✓ Be EXHAUSTIVE - extract every product mentioned in the results

IMPORTANT: If the search results mention multiple products (e.g., 6-8 conditioners),
extract ALL of them. Don't stop after 2-3 products.

OUTPUT FORMAT (JSON):
{{
  "brand_page_found": true/false,
  "brand_page_url": "https://...",
  "products_found": [
    {{
      "name": "Complete Product Name",
      "url": "https://...",
      "description": "Brief description"
    }}
  ],
  "match_confidence": "high/medium/low",
  "notes": "Any relevant notes"
}}

Return ONLY valid JSON with ALL products found.
"""

        try:
            print(f"\n🤖 [{self.name}] Processing web search results...")

            response = self.client.models.generate_content(
                model=self.model,
                contents=processing_prompt
            )

            self.request_count += 1

            response_text = response.text

            print(f"✅ [{self.name}] Processing complete")

            # Parse JSON
            result = self._parse_json_response(response_text)

            if result:
                products = result.get("products_found", [])
                print(f"   Found {len(products)} product candidate(s)")
                return result
            else:
                print("⚠️ Could not parse processing results")
                return {
                    "brand_page_found": False,
                    "brand_page_url": None,
                    "products_found": [],
                    "match_confidence": "none",
                    "notes": "Failed to parse Gemini processing results"
                }

        except Exception as e:
            print(f"❌ [{self.name}] Processing failed: {e}")
            return {
                "brand_page_found": False,
                "brand_page_url": None,
                "products_found": [],
                "match_confidence": "none",
                "notes": f"Error: {str(e)}"
            }

    def process_variant_search_results(self, raw_variant_data: str, product_name: str) -> Dict:
        """
        DEPRECATED: This method is no longer used.
        Gemini 2.5 Flash (in ProductConfirmationAgent) now returns structured JSON directly.

        This method was causing hallucinations (creating fake variants).
        Kept for backward compatibility but should not be called.

        Args:
            raw_variant_data: Raw text from web search
            product_name: Product name

        Returns:
            Dictionary with structured variants (NO PRICES!)
        """
        print("⚠️ WARNING: process_variant_search_results() is DEPRECATED and should not be called")

        processing_prompt = f"""
You are processing web search results to extract product variants.

VARIANT DATA (from web search):
{raw_variant_data}

PRODUCT:
{product_name}

TASK: Extract ALL available variants

Look for:
- Size/Volume (100ml, 250ml, 500ml, etc.)
- Weight (50g, 100g, etc.)
- Color/Shade options
- Pack sizes (single, 2-pack, etc.)
- Any other variants

CRITICAL RULES:
✓ Extract information from the data provided above
✓ DO NOT do any web searches yourself
✓ DO NOT include prices, costs, or any monetary information
✓ Remove ALL price references from the data
✓ Include variant type (volume/weight/color/pack_size)
✓ Include variant value (100ml/Red/2-pack)
✓ Include direct URLs if available

OUTPUT FORMAT (JSON):
{{
  "product_name": "{product_name}",
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

IMPORTANT: NO PRICES! If you see price information in the data, REMOVE it completely.

Return ONLY valid JSON.
"""

        try:
            print(f"\n🤖 [{self.name}] Processing web search variant data...")
            print(f"🚫 Filtering out ALL price information...")

            response = self.client.models.generate_content(
                model=self.model,
                contents=processing_prompt
            )

            self.request_count += 1

            response_text = response.text

            print(f"✅ [{self.name}] Variant processing complete")

            # Parse JSON
            result = self._parse_json_response(response_text)

            if result:
                variants = result.get("variants", [])
                print(f"   Extracted {len(variants)} variant(s) (NO PRICES)")
                return result
            else:
                print("⚠️ Could not parse variant processing results")
                return {
                    "product_name": product_name,
                    "variants_found": False,
                    "variants": [],
                    "total_variants": 0,
                    "notes": "Failed to parse Gemini processing results"
                }

        except Exception as e:
            print(f"❌ [{self.name}] Variant processing failed: {e}")
            return {
                "product_name": product_name,
                "variants_found": False,
                "variants": [],
                "total_variants": 0,
                "notes": f"Error: {str(e)}"
            }

    def _parse_json_response(self, response_text: str) -> Optional[Dict]:
        """
        Parse JSON from Gemini response

        Args:
            response_text: Raw response text

        Returns:
            Parsed dictionary or None
        """
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Remove markdown
            cleaned = response_text
            cleaned = re.sub(r'```json\s*', '', cleaned)
            cleaned = re.sub(r'```\s*', '', cleaned)

            try:
                return json.loads(cleaned)
            except:
                # Extract JSON
                json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
                if json_match:
                    try:
                        return json.loads(json_match.group(0))
                    except:
                        pass
                return None

    def get_usage_stats(self) -> Dict:
        """Get API usage statistics"""
        return {
            "agent": self.name,
            "api_requests": self.request_count,
            "estimated_cost_usd": round(self.request_count * 0.0001, 6)  # Very low cost for Gemini Flash
        }
