"""
ProductConfirmationAgent - Product confirmation specialist
Architecture: OpenAI searches AND structures (no Gemini processing needed)
"""

from typing import Dict, Optional
from ..tools.brand_page_search import OpenAIWebSearchTool


class ProductConfirmationAgent:
    """
    Agent responsible for product confirmation using OpenAI GPT-4o:

    Single-step process: OpenAI GPT-4o searches AND structures results directly
    No Gemini processing needed - GPT returns ready-to-use JSON

    Tasks:
    1. Find brand's official page
    2. Confirm product user is looking for
    3. Extract available variants (NO PRICES)

    Architecture:
    - OpenAI tool: Searches web AND returns structured JSON directly
    - No hallucination - only returns products/variants that actually exist
    """

    def __init__(self, orchestrator_agent=None, openai_api_key: Optional[str] = None):
        """
        Initialize agent with OpenAI tool

        Args:
            orchestrator_agent: OrchestratorAgent instance (kept for compatibility, not used)
            openai_api_key: OpenAI API key (optional)
        """
        # OpenAI tool for web search AND structuring
        self.openai_tool = OpenAIWebSearchTool(api_key=openai_api_key)

        # Keep orchestrator reference for compatibility (but don't use it)
        self.orchestrator = orchestrator_agent

        self.name = "ProductConfirmationAgent"

    def search_and_confirm_product(
        self,
        brand: str,
        product_name: str,
        variant_hint: Optional[str] = None
    ) -> Dict:
        """
        Search brand page and find matching products

        Single-step process: OpenAI searches AND structures results directly

        Args:
            brand: Brand name
            product_name: Product name
            variant_hint: Optional variant from user query

        Returns:
            Dictionary with brand page and structured product candidates
        """
        print("\n" + "="*70)
        print(f"🤖 {self.name}: Product confirmation (OpenAI direct)")
        print("="*70)

        # OpenAI web search AND structuring (single step)
        print("\n📍 OpenAI web search + structuring...")
        structured_result = self.openai_tool.search_brand_and_product(
            brand=brand,
            product_name=product_name,
            variant_hint=variant_hint
        )

        # Result is already structured - no Gemini processing needed
        return structured_result

    def extract_product_variants(
        self,
        product_name: str,
        product_url: str,
        variant_hint: Optional[str] = None
    ) -> Dict:
        """
        Extract variants for confirmed product

        Single-step process: OpenAI searches AND structures results directly

        Args:
            product_name: Confirmed product name
            product_url: Product page URL
            variant_hint: Optional variant hint

        Returns:
            Dictionary with variant information (NO PRICES)
        """
        print("\n" + "="*70)
        print(f"🤖 {self.name}: Variant extraction (OpenAI direct)")
        print("="*70)

        # OpenAI web search AND structuring (single step)
        print("\n📍 OpenAI web search + structuring...")
        structured_result = self.openai_tool.search_product_variants(
            product_name=product_name,
            product_url=product_url,
            variant_hint=variant_hint
        )

        # Result is already structured - no Gemini processing needed
        return structured_result

    def get_usage_stats(self) -> Dict:
        """Get API usage statistics"""
        openai_stats = self.openai_tool.get_usage_stats()

        return {
            "agent": self.name,
            "openai_requests": openai_stats["requests"],
            "gemini_requests": 0,  # No longer using Gemini for product/variant processing
            "estimated_cost_usd": openai_stats["estimated_cost_usd"],
            "breakdown": {
                "openai": openai_stats
            },
            "notes": "Gemini processing removed - OpenAI returns structured results directly"
        }
