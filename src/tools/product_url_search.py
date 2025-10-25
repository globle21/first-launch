"""
Product URL Search Tool - Uses Claude 4.5 Haiku with web search capability
"""

import os
import json
import re
from typing import Dict, List, Optional
from anthropic import Anthropic


class ProductURLSearchTool:
    """
    Tool for discovering product URLs across multiple retailers
    Uses Anthropic's Claude 4.5 Haiku with web search capability
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the tool with Anthropic API key

        Args:
            api_key: Anthropic API key (if None, reads from environment)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

        self.client = Anthropic(api_key=self.api_key)
        self.model = "claude-haiku-4-5"  # Claude 4.5 Haiku with web search
        self.request_count = 0
        self.search_count = 0  # Track web searches for cost estimation

    def discover_product_urls(
        self,
        brand: str,
        product_name: str,
        variant: str,
        brand_product_url: Optional[str] = None
    ) -> Dict:
        """
        Discover maximum URLs for specific product variant across web

        Args:
            brand: Brand name
            product_name: Product name
            variant: Specific variant (e.g., "100ml", "Red")
            brand_product_url: Optional official brand URL

        Returns:
            Dictionary with discovered URLs and metadata
        """
        from ..prompts.discovery_prompts import get_url_discovery_prompt

        # Generate prompt
        prompt = get_url_discovery_prompt(brand, product_name, variant, brand_product_url)

        try:
            print(f"\n🔍 Discovering URLs for {brand} {product_name} - {variant}...")
            print(f"🤖 Using Claude 4.5 Haiku with web search")
            print(f"🎯 Goal: Maximum URLs across all retailers")

            # Make API call with web search tool
            # Use higher max_uses for comprehensive search (aim for 20-50+ URLs)
            max_searches = 15  # Allow up to 15 web searches for maximum coverage

            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,  # Enough for comprehensive URL list with 3 fields per URL
                temperature=0,  # Deterministic output
                # NOTE: Extended thinking is DISABLED BY DEFAULT in Claude 4.5 Haiku
                # No thinking parameter needed - keeps responses fast and cost-effective
                # NO stop_sequences - rely on prompt instruction for JSON-only output
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                tools=[{
                    "type": "web_search_20250305",
                    "name": "web_search",
                    "max_uses": max_searches,  # 15 searches for maximum coverage
                    "user_location": {
                        "type": "approximate",
                        "country": "IN",  # India for local e-commerce
                        "timezone": "Asia/Kolkata"
                    }
                }]
            )

            self.request_count += 1

            # Count actual web searches performed
            tool_uses = 0
            for block in response.content:
                if hasattr(block, 'type') and block.type == 'tool_use':
                    if hasattr(block, 'name') and block.name == 'web_search':
                        tool_uses += 1

            # Fallback: estimate from max_searches if no tool_use blocks
            if tool_uses == 0:
                tool_uses = max_searches

            self.search_count += tool_uses
            print(f"🔍 Web searches performed: {tool_uses}")

            # Extract response text
            response_text = ""
            for block in response.content:
                if hasattr(block, 'text') and block.text:
                    response_text += block.text

            if not response_text:
                print("❌ Empty response from Claude API")
                return self._empty_result(brand, product_name, variant, "Empty API response")

            # Save raw response to file for debugging
            import tempfile
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_file = f"debug_claude_response_{timestamp}.txt"

            try:
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(f"=== CLAUDE RAW RESPONSE ===\n")
                    f.write(f"Timestamp: {timestamp}\n")
                    f.write(f"Product: {brand} {product_name} {variant}\n")
                    f.write(f"Response length: {len(response_text)} chars\n")
                    f.write(f"\n{response_text}\n")
                print(f"💾 Raw response saved to: {debug_file}")
            except:
                pass

            print("\n" + "="*70)
            print("📋 RAW RESPONSE FROM CLAUDE:")
            print("="*70)
            print(response_text[:1200] if len(response_text) > 1200 else response_text)
            if len(response_text) > 1200:
                print(f"\n... (truncated, total {len(response_text)} characters)")
            print()

            # Parse JSON response
            print("🔄 Attempting to parse JSON...")
            result = self._parse_json_response(response_text)

            if result and "urls" in result:
                urls = result.get("urls", [])
                print(f"✅ JSON parsing successful!")

                # If no URLs found, extract reason from Claude's explanation
                if len(urls) == 0:
                    failure_reason = self._extract_failure_reason(response_text)
                    print(f"⚠️ No URLs found: {failure_reason}")
                    return self._empty_result(brand, product_name, variant, failure_reason, response_text)

                print(f"✅ Successfully discovered {len(urls)} URLs")
                print(f"💰 Web search cost: ${self.search_count * 0.01:.4f}")
                print(f"📊 Search method: {tool_uses} web searches (batch mode - multiple URLs per search)")

                # Validate URL structure
                valid_urls = []
                for i, url_data in enumerate(urls):
                    if isinstance(url_data, dict) and "url" in url_data:
                        valid_urls.append(url_data)
                    else:
                        print(f"⚠️ Skipping invalid URL entry at index {i}: {url_data}")

                if len(valid_urls) != len(urls):
                    print(f"⚠️ Filtered out {len(urls) - len(valid_urls)} invalid entries")
                    urls = valid_urls

                # Show sample URLs
                print(f"\n📋 Sample URLs (first 5):")
                for i, url_data in enumerate(urls[:5], 1):
                    product_type = url_data.get('product_type', 'unknown')
                    variant = url_data.get('variant', 'unknown')
                    print(f"   {i}. {url_data.get('url', '')[:80]}... [{product_type}, {variant}]")
                if len(urls) > 5:
                    print(f"   ... and {len(urls) - 5} more")

                # Simplified metadata (3 fields only in URLs)
                result["urls"] = urls  # Use validated URLs
                result["search_metadata"] = {
                    "web_searches_performed": self.search_count,
                    "urls_per_search_avg": round(len(urls) / max(self.search_count, 1), 1),
                    "estimated_cost_usd": round(self.search_count * 0.01, 4)
                }

                return result

            else:
                print("❌ JSON parsing failed!")
                print(f"⚠️ Could not parse JSON response or no URLs found")
                print(f"📁 Check debug file for full response: {debug_file}")

                # Extract failure reason from Claude's response for user feedback
                failure_reason = self._extract_failure_reason(response_text)
                return self._empty_result(brand, product_name, variant, failure_reason, response_text)

        except Exception as e:
            print(f"❌ URL discovery failed: {e}")
            import traceback
            traceback.print_exc()
            return self._empty_result(brand, product_name, variant, f"Error: {str(e)}")

    def _parse_json_response(self, response_text: str) -> Optional[Dict]:
        """
        Parse JSON from API response with multiple fallback strategies
        Expected format: {"urls": [{"url": "...", "product_type": "...", "variant": "..."}]}

        Args:
            response_text: Raw API response

        Returns:
            Parsed dictionary or None
        """
        if not response_text or not response_text.strip():
            print("❌ Empty response text")
            return None

        # Strategy 1: Direct JSON parsing
        try:
            print("  📍 Strategy 1: Direct JSON parse...")
            data = json.loads(response_text)
            print("  ✅ Success!")
            return data
        except json.JSONDecodeError as e:
            print(f"  ❌ Failed: {e}")

        # Strategy 2: Remove markdown code blocks
        try:
            print("  📍 Strategy 2: Remove markdown blocks...")
            cleaned = response_text
            cleaned = re.sub(r'```json\s*', '', cleaned)
            cleaned = re.sub(r'```\s*', '', cleaned)
            cleaned = cleaned.strip()

            data = json.loads(cleaned)
            print("  ✅ Success!")
            return data
        except json.JSONDecodeError as e:
            print(f"  ❌ Failed: {e}")

        # Strategy 3: Extract JSON object from text
        try:
            print("  📍 Strategy 3: Extract JSON object...")
            # Find the first { and last }
            start = response_text.find('{')
            end = response_text.rfind('}')

            if start != -1 and end != -1 and end > start:
                json_str = response_text[start:end+1]
                data = json.loads(json_str)
                print("  ✅ Success!")
                return data
        except (json.JSONDecodeError, ValueError) as e:
            print(f"  ❌ Failed: {e}")

        # Strategy 4: Try to find and parse just the URLs array
        try:
            print("  📍 Strategy 4: Extract URLs array...")
            # Look for "urls": [...]
            urls_match = re.search(r'"urls"\s*:\s*(\[.*?\])', response_text, re.DOTALL)
            if urls_match:
                urls_json = urls_match.group(1)
                urls_list = json.loads(urls_json)
                print(f"  ✅ Success! Found {len(urls_list)} URLs")
                return {"urls": urls_list}
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"  ❌ Failed: {e}")

        # Strategy 5: Manual URL extraction
        print("  📍 Strategy 5: Manual URL extraction (fallback)...")
        result = self._extract_urls_from_text(response_text)
        if result:
            print(f"  ✅ Extracted {len(result.get('urls', []))} URLs via regex")
        else:
            print("  ❌ No URLs found")
        return result

    def _extract_urls_from_text(self, text: str) -> Optional[Dict]:
        """
        Fallback: Extract URLs from text using regex

        Args:
            text: Response text

        Returns:
            Dictionary with extracted URLs (3 fields only)
        """
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+[^\s<>"{}|\\^`\[\].,;:!?\'\")]'
        urls = re.findall(url_pattern, text)

        if urls:
            # Deduplicate
            unique_urls = list(set(urls))

            # Create minimal structure (3 fields only)
            url_list = []
            for url in unique_urls:
                url_list.append({
                    "url": url,
                    "product_type": "individual",
                    "variant": "unknown"
                })

            return {
                "urls": url_list
            }

        return None

    def _extract_failure_reason(self, response_text: str) -> str:
        """
        Extract Claude's explanation for why no URLs were found

        Args:
            response_text: Full response from Claude

        Returns:
            Extracted reason or generic message
        """
        if not response_text:
            return "No URLs found - empty response"

        # Keywords to identify relevant explanation sentences
        reason_keywords = [
            "out of stock", "out-of-stock", "sold out",
            "not available", "no longer available", "discontinued",
            "could not find", "no results", "limited availability",
            "no confirmed", "challenge is", "appears to",
            "search results show", "limited to", "only found"
        ]

        # Extract sentences containing these keywords
        sentences = response_text.replace('\n', ' ').split('.')
        relevant_sentences = []

        for sentence in sentences[:15]:  # Only check first 15 sentences
            sentence_lower = sentence.lower().strip()
            if any(keyword in sentence_lower for keyword in reason_keywords):
                # Clean up the sentence
                clean_sentence = sentence.strip()
                if len(clean_sentence) > 20 and len(clean_sentence) < 200:
                    relevant_sentences.append(clean_sentence)

        if relevant_sentences:
            # Return first 2 most relevant sentences
            reason = '. '.join(relevant_sentences[:2])
            if not reason.endswith('.'):
                reason += '.'
            return reason

        # Fallback: Try to extract the first substantive paragraph
        paragraphs = [p.strip() for p in response_text.split('\n\n') if p.strip()]
        for para in paragraphs[:3]:
            if len(para) > 50 and len(para) < 500:
                return para[:300] + ('...' if len(para) > 300 else '')

        return "No URLs found - Claude could not locate products matching the exact variant"

    def _empty_result(
        self,
        brand: str,
        product_name: str,
        variant: str,
        reason: str,
        raw_response: str = None
    ) -> Dict:
        """
        Create empty result structure with error info

        Args:
            brand: Brand name
            product_name: Product name
            variant: Variant
            reason: Error reason
            raw_response: Optional raw response for debugging

        Returns:
            Empty result dictionary (simplified structure)
        """
        result = {
            "urls": [],
            "error": reason,
            "search_metadata": {
                "web_searches_performed": self.search_count,
                "urls_per_search_avg": 0,
                "estimated_cost_usd": round(self.search_count * 0.01, 4)
            }
        }

        if raw_response:
            result["raw_response"] = raw_response[:500]  # Truncate for size

        return result
