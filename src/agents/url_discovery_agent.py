"""
URLDiscoveryAgent - Specialized agent for URL discovery
Uses Claude 4.5 Haiku with web search to find maximum product URLs
"""

from typing import Dict, Optional
from ..tools.product_url_search import ProductURLSearchTool


class URLDiscoveryAgent:
    """
    Agent responsible for:
    1. Searching for product variant across all retailers
    2. Finding MAXIMUM URLs (20-50+ if available)
    3. Including combos/bundles with exact variant
    4. Excluding subscriptions
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize agent with ProductURLSearchTool

        Args:
            api_key: Anthropic API key (optional)
        """
        self.tool = ProductURLSearchTool(api_key=api_key)
        self.name = "URLDiscoveryAgent"

    def discover_urls(
        self,
        brand: str,
        product_name: str,
        variant: str,
        brand_product_url: Optional[str] = None
    ) -> Dict:
        """
        Discover maximum URLs for specific product variant

        Args:
            brand: Brand name
            product_name: Product name
            variant: Specific variant (e.g., "100ml")
            brand_product_url: Optional official brand URL

        Returns:
            Dictionary with discovered URLs and metadata
        """
        print("\n" + "="*70)
        print(f"🤖 {self.name}: Discovering product URLs")
        print("="*70)

        result = self.tool.discover_product_urls(
            brand=brand,
            product_name=product_name,
            variant=variant,
            brand_product_url=brand_product_url
        )

        return result

    def get_usage_stats(self) -> Dict:
        """Get API usage statistics"""
        return {
            "agent": self.name,
            "api_requests": self.tool.request_count,
            "web_searches": self.tool.search_count,
            "estimated_cost_usd": round(self.tool.search_count * 0.01, 4)  # $0.01 per web search
        }
