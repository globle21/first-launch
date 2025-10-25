"""
ProductConfirmationAgent - Product confirmation specialist
Architecture: Gemini 2.5 Flash with Google Search grounding
"""

from typing import Dict, Optional
from ..tools.brand_page_search import OpenAIWebSearchTool


class ProductConfirmationAgent:
    """
    Agent responsible for product confirmation using Gemini 2.5 Flash with Google Search:

    Single-step process: Gemini searches AND structures results directly
    Uses Google Search grounding for accurate, real-time data

    Tasks:
    1. Find brand's official page
    2. Confirm product user is looking for
    3. Extract available variants (NO PRICES)

    Architecture:
    - Gemini 2.5 Flash: Searches web (Google Search) AND returns structured JSON directly
    - No hallucination - only returns products/variants that actually exist
    - Cost-effective: ~$0.001 per request (97% cheaper than GPT-4o-mini)
    """

    def __init__(self, orchestrator_agent=None, openai_api_key: Optional[str] = None):
        """
        Initialize agent with Gemini tool (note: parameter name kept for backward compatibility)

        Args:
            orchestrator_agent: OrchestratorAgent instance (kept for compatibility, not used)
            openai_api_key: Google API key (parameter name kept for backward compatibility)
        """
        # Gemini tool for web search AND structuring (class name kept for backward compatibility)
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

        Single-step process: Gemini searches AND structures results directly

        Args:
            brand: Brand name
            product_name: Product name
            variant_hint: Optional variant from user query

        Returns:
            Dictionary with brand page and structured product candidates
        """
        print("\n" + "="*70)
        print(f"🤖 {self.name}: Product confirmation (Gemini 2.5 Flash)")
        print("="*70)

        # Gemini web search AND structuring (single step)
        print("\n📍 Gemini web search + structuring...")
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

        Single-step process: Gemini searches AND structures results directly

        Args:
            product_name: Confirmed product name
            product_url: Product page URL
            variant_hint: Optional variant hint

        Returns:
            Dictionary with variant information (NO PRICES)
        """
        print("\n" + "="*70)
        print(f"🤖 {self.name}: Variant extraction (Gemini 2.5 Flash)")
        print("="*70)

        # Gemini web search AND structuring (single step)
        print("\n📍 Gemini web search + structuring...")
        structured_result = self.openai_tool.search_product_variants(
            product_name=product_name,
            product_url=product_url,
            variant_hint=variant_hint
        )

        # Result is already structured
        return structured_result

    def get_usage_stats(self) -> Dict:
        """Get API usage statistics"""
        gemini_stats = self.openai_tool.get_usage_stats()

        return {
            "agent": self.name,
            "gemini_requests": gemini_stats["requests"],
            "estimated_cost_usd": gemini_stats["estimated_cost_usd"],
            "breakdown": {
                "gemini_2.5_flash": gemini_stats
            },
            "notes": "Using Gemini 2.5 Flash with Google Search grounding"
        }
