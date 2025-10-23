"""
Combo Product MRP Extractor - Extracts individual product MRPs from brand pages
Uses Google Gemini 2.5 Flash with Google Search grounding

SIMPLIFIED APPROACH:
- Combo sale price comes from Apify scraping (no LLM extraction needed)
- LLM only extracts individual product MRPs from brand website
- Python calculates: per_unit_price = (original_mrp / sum_mrps) × combo_sale_price
"""

import os
import json
from typing import Dict, Optional
from google import genai
from google.genai import types
try:
    from ..prompts.combo_mrp_prompts import create_combo_product_mrp_prompt
except ImportError:
    from prompts.combo_mrp_prompts import create_combo_product_mrp_prompt


class ComboProductMRPExtractor:
    """
    Tool for extracting individual product MRPs from brand pages using Google Gemini 2.5 Flash

    Simplified Functionality:
    - Takes combo_sale_price from Apify data (no extraction needed)
    - Extracts individual product MRPs from brand website
    - Returns structured data for per-unit price calculation
    """

    def __init__(self, api_key: Optional[str] = None, debug: bool = False):
        """
        Initialize combo product MRP extractor

        Args:
            api_key: Google API key (if None, reads from environment)
            debug: Enable debug logging to see raw responses
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")

        self.client = genai.Client(api_key=self.api_key)
        self.model = "gemini-2.5-flash"  # Gemini 2.5 Flash with Google Search grounding
        self.debug = debug

    def extract_product_mrps(
        self,
        combo_url: str,
        combo_sale_price: float,
        brand: str,
        original_product_name: str,
        original_variant: str,
        brand_page_url: str = None
    ) -> Optional[Dict]:
        """
        Extract individual product MRPs from brand pages (simplified)

        Args:
            combo_url: URL of the combo product
            combo_sale_price: Current sale price of combo (from Apify data)
            brand: Brand name
            original_product_name: Name of the target product
            original_variant: Variant of target product
            brand_page_url: Optional brand website URL

        Returns:
            Dictionary with product MRPs:
            {
                "combo_url": str,
                "combo_sale_price": float,
                "original_product": {"name": str, "variant": str, "mrp": float},
                "products": [{"name": str, "variant": str, "mrp": float}, ...],
                "sum_of_mrps": float
            }
            or None if extraction fails
        """
        try:
            print(f"\n{'='*70}")
            print(f"💰 COMBO PRODUCT MRP EXTRACTION (SIMPLIFIED)")
            print(f"{'='*70}")
            print(f"Combo URL: {combo_url[:60]}...")
            print(f"Combo Sale Price: ₹{combo_sale_price} (from Apify)")
            print(f"Target: {brand} {original_product_name} - {original_variant}")
            print(f"🤖 Using Google Gemini 2.5 Flash with Google Search grounding")

            # Create simplified prompt
            prompt = create_combo_product_mrp_prompt(
                combo_url=combo_url,
                combo_sale_price=combo_sale_price,
                brand=brand,
                original_product_name=original_product_name,
                original_variant=original_variant,
                brand_page_url=brand_page_url
            )

            # Call Gemini with Google Search grounding enabled
            print(f"⏳ Extracting individual product MRPs from brand pages...")

            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,  # Low temperature for factual accuracy
                    tools=[types.Tool(google_search=types.GoogleSearch())]  # Enable Google Search grounding
                    # Note: response_mime_type cannot be used with tools in Gemini 2.5 Flash
                )
            )

            # Extract response text
            response_text = response.text

            if not response_text:
                print("❌ No text response from Gemini")
                return None

            # Debug: Print raw response
            if self.debug:
                print(f"\n{'='*70}")
                print(f"🔍 DEBUG: Raw Gemini Response")
                print(f"{'='*70}")
                print(response_text)
                print(f"{'='*70}\n")

            # Parse JSON response
            mrp_data = self._parse_mrp_response(response_text)

            if mrp_data:
                # Calculate sum of MRPs
                sum_of_mrps = sum(float(product["mrp"]) for product in mrp_data["products"])

                # Build result
                result = {
                    "combo_url": combo_url,
                    "combo_sale_price": combo_sale_price,
                    "original_product": {
                        "name": mrp_data["original_product"]["name"],
                        "variant": mrp_data["original_product"]["variant"],
                        "mrp": float(mrp_data["original_product"]["mrp"])
                    },
                    "products": [
                        {
                            "name": product["name"],
                            "variant": product["variant"],
                            "mrp": float(product["mrp"])
                        }
                        for product in mrp_data["products"]
                    ],
                    "sum_of_mrps": sum_of_mrps
                }

                self._display_mrp_data(result)
                return result
            else:
                print("❌ Failed to parse MRP data")
                return None

        except Exception as e:
            print(f"❌ MRP extraction failed: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return None

    def _parse_mrp_response(self, response_text: str) -> Optional[Dict]:
        """
        Parse Gemini's response to extract MRP data

        Args:
            response_text: Raw response from Gemini

        Returns:
            Parsed MRP data dictionary or None
        """
        # Strategy 1: Direct JSON parse
        try:
            data = json.loads(response_text)
            if self._validate_mrp_data(data):
                return data
        except json.JSONDecodeError:
            pass

        # Strategy 2: Extract JSON from markdown (```json)
        try:
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_str = response_text[start:end].strip()
                data = json.loads(json_str)
                if self._validate_mrp_data(data):
                    return data
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
                                data = json.loads(json_str)
                                if self._validate_mrp_data(data):
                                    return data
                                break
        except Exception as e:
            pass

        # Strategy 4: Extract JSON object
        try:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start != -1 and end > start:
                json_str = response_text[start:end]
                data = json.loads(json_str)
                if self._validate_mrp_data(data):
                    return data
        except:
            pass

        print(f"⚠️ All parsing strategies failed")
        if self.debug:
            print(f"Raw response: {response_text[:500]}")
        return None

    def _validate_mrp_data(self, data: Dict) -> bool:
        """
        Validate MRP data structure (simplified format)

        Args:
            data: Parsed data dictionary

        Returns:
            True if valid, False otherwise
        """
        # Check required fields
        if "original_product" not in data or "products" not in data:
            return False

        # Validate original_product
        original = data.get("original_product", {})
        if not all(k in original for k in ["name", "variant", "mrp"]):
            return False

        # Validate products list
        products = data.get("products", [])
        if not products or not isinstance(products, list):
            return False

        for product in products:
            if not all(k in product for k in ["name", "variant", "mrp"]):
                return False

        return True

    def _display_mrp_data(self, mrp_data: Dict):
        """
        Display extracted MRP data

        Args:
            mrp_data: Extracted MRP data dictionary
        """
        print(f"\n✅ PRODUCT MRPs EXTRACTED:")
        print(f"-" * 70)

        # Original product
        original = mrp_data["original_product"]
        print(f"\n🎯 Original Product (target):")
        print(f"   {original['name']} - {original['variant']}")
        print(f"   MRP: ₹{original['mrp']:.2f}")

        # All products in combo
        print(f"\n📦 All Products in Combo:")
        for i, product in enumerate(mrp_data["products"], 1):
            print(f"   {i}. {product['name']} - {product['variant']}")
            print(f"      MRP: ₹{product['mrp']:.2f}")

        # Summary
        print(f"\n💰 Summary:")
        print(f"   Sum of All MRPs: ₹{mrp_data['sum_of_mrps']:.2f}")
        print(f"   Combo Sale Price: ₹{mrp_data['combo_sale_price']:.2f} (from Apify)")
        print(f"   MRP Ratio: {original['mrp']:.2f} / {mrp_data['sum_of_mrps']:.2f} = {original['mrp'] / mrp_data['sum_of_mrps']:.4f}")
        print(f"\n{'-' * 70}")
