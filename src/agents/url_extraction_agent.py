"""
URLExtractionAgent - Extracts product details from product URLs
Uses Google Gemini 2.0 Flash with Google Search grounding
"""

import os
import json
from typing import Dict, Optional
from google import genai
from google.genai import types


class URLExtractionAgent:
    """
    Agent responsible for extracting product information from product URLs

    Workflow:
    1. Receives a product URL from user
    2. Uses Gemini with Google Search to visit the URL
    3. Extracts: brand, product name, variant
    4. Returns structured data for confirmation
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize URL extraction agent

        Args:
            api_key: Google API key (optional, reads from env if None)
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")

        self.client = genai.Client(api_key=self.api_key)
        self.model = "gemini-2.0-flash-exp"  # Gemini 2.0 Flash with Google Search
        self.request_count = 0
        self.name = "URLExtractionAgent"

    def extract_from_url(self, product_url: str) -> Dict:
        """
        Extract product details from a product URL

        Args:
            product_url: Full URL of the product page

        Returns:
            Dictionary with extracted product details
        """
        from ..prompts.url_extraction_prompts import get_url_extraction_prompt

        print("\n" + "="*70)
        print(f"🤖 {self.name}: Extracting product details from URL")
        print("="*70)
        print(f"🔗 URL: {product_url[:60]}...")

        # Validate URL format
        if not self._is_valid_url(product_url):
            print("❌ Invalid URL format")
            return {
                "success": False,
                "error": "Invalid URL format. Please provide a valid product URL starting with http:// or https://",
                "extraction_confidence": "none"
            }

        # Generate prompt
        prompt = get_url_extraction_prompt(product_url)

        try:
            print(f"🤖 Using Gemini 2.0 Flash with Google Search grounding")
            print(f"⏳ Extracting product information...")

            # Call Gemini with Google Search grounding
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,  # Low temperature for factual accuracy
                    response_mime_type="application/json",  # Force JSON output
                    tools=[types.Tool(google_search=types.GoogleSearch())]  # Enable Google Search
                )
            )

            self.request_count += 1

            # Extract response
            response_text = response.text

            # Parse JSON
            try:
                result = self._parse_extraction_response(response_text)

                if result and result.get("brand") and result.get("product_name"):
                    print(f"\n✅ Extraction successful!")
                    print(f"   Brand: {result['brand']}")
                    print(f"   Product: {result['product_name']}")
                    print(f"   Variant: {result.get('variant', 'N/A')}")
                    print(f"   Confidence: {result.get('extraction_confidence', 'unknown')}")

                    result["success"] = True
                    return result
                else:
                    print(f"❌ Incomplete extraction - missing required fields")
                    return {
                        "success": False,
                        "error": "Could not extract complete product information from URL",
                        "extraction_confidence": "none"
                    }

            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing failed: {e}")
                print(f"Raw response: {response_text[:500]}")
                return {
                    "success": False,
                    "error": f"Failed to parse extraction response: {str(e)}",
                    "extraction_confidence": "none"
                }

        except Exception as e:
            print(f"❌ URL extraction failed: {e}")
            return {
                "success": False,
                "error": f"Extraction error: {str(e)}",
                "extraction_confidence": "none"
            }

    def _is_valid_url(self, url: str) -> bool:
        """
        Validate URL format

        Args:
            url: URL string to validate

        Returns:
            True if valid, False otherwise
        """
        url_lower = url.lower().strip()
        return url_lower.startswith("http://") or url_lower.startswith("https://")

    def _parse_extraction_response(self, response_text: str) -> Optional[Dict]:
        """
        Parse Gemini's extraction response

        Args:
            response_text: Raw JSON response from Gemini

        Returns:
            Parsed dictionary or None
        """
        # Strategy 1: Direct JSON parse
        try:
            data = json.loads(response_text)
            return data
        except json.JSONDecodeError:
            pass

        # Strategy 2: Extract JSON from markdown
        try:
            if response_text.strip().startswith("```"):
                # Remove first ```
                temp = response_text.strip()[3:]
                # Find the first complete JSON object
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
                                return data
        except:
            pass

        # Strategy 3: Extract JSON object
        try:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start != -1 and end > start:
                json_str = response_text[start:end]
                data = json.loads(json_str)
                return data
        except:
            pass

        return None

    def get_usage_stats(self) -> Dict:
        """Get API usage statistics"""
        return {
            "agent": self.name,
            "model": self.model,
            "requests": self.request_count,
            "estimated_cost_usd": round(self.request_count * 0.0001, 4)  # ~$0.0001 per request
        }
