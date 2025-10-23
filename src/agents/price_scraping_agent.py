"""
PriceScrapingAgent - Orchestrates price scraping for discovered URLs
Uses Apify to enrich URLs with product details
"""

from typing import Dict, List, Optional
from ..tools.apify_price_scraper import ApifyPriceScraper


class PriceScrapingAgent:
    """
    Agent responsible for enriching discovered URLs with price data

    Workflow:
    1. Receives URLs from Claude URL discovery
    2. Orchestrates batch processing via Apify (20 URLs per batch)
    3. Executes batches concurrently for speed
    4. Enriches URLs with: name, price, currency, image, availability
    5. Returns enriched URLs with statistics

    Architecture:
    - Apify tool: Handles scraping and concurrent execution
    - This agent: Orchestrates the process and ensures data quality
    """

    def __init__(self, apify_api_key: Optional[str] = None):
        """
        Initialize price scraping agent

        Args:
            apify_api_key: Apify API key (optional, reads from env if None)
        """
        self.scraper = ApifyPriceScraper(api_key=apify_api_key)
        self.name = "PriceScrapingAgent"

    def enrich_urls(
        self,
        discovered_urls: List[Dict],
        max_workers: int = 5
    ) -> Dict:
        """
        Enrich discovered URLs with price and product data

        Args:
            discovered_urls: URLs from Claude discovery
                Format: [{"url": "...", "product_type": "...", "variant": "..."}]
            max_workers: Maximum concurrent batches (default: 5)

        Returns:
            Dictionary with enriched URLs and statistics
        """
        print("\n" + "="*70)
        print(f"🤖 {self.name}: Enriching URLs with price data")
        print("="*70)

        if not discovered_urls:
            print("⚠️ No URLs to enrich")
            return {
                "enriched_urls": [],
                "stats": self._empty_stats()
            }

        print(f"📋 Received {len(discovered_urls)} URLs from Claude")
        print(f"🎯 Strategy: Batch processing (20 URLs/batch) with concurrent execution")

        # Scrape prices using Apify
        result = self.scraper.scrape_urls_concurrent(
            urls=discovered_urls,
            max_workers=max_workers
        )

        # Validate results
        enriched_urls = result.get("enriched_urls", [])
        stats = result.get("stats", {})

        # Show sample enriched URLs
        self._display_samples(enriched_urls)

        return {
            "enriched_urls": enriched_urls,
            "stats": stats
        }

    def _display_samples(self, enriched_urls: List[Dict], sample_size: int = 5):
        """
        Display sample enriched URLs

        Args:
            enriched_urls: List of enriched URLs
            sample_size: Number of samples to display
        """
        if not enriched_urls:
            return

        print(f"\n📋 Sample Enriched URLs (first {sample_size}):")
        print("-" * 70)

        for i, url_data in enumerate(enriched_urls[:sample_size], 1):
            name = url_data.get("name", "N/A")
            price = url_data.get("price")
            currency = url_data.get("currency", "")
            availability = url_data.get("availability", "unknown")

            # Format price display
            if price:
                price_str = f"{currency} {price}"
            else:
                price_str = "N/A"

            # Availability emoji
            avail_emoji = {
                "in_stock": "✅",
                "out_of_stock": "❌",
                "unavailable": "⚠️"
            }.get(availability, "❓")

            print(f"{i}. {name[:50]}")
            print(f"   Price: {price_str} | Status: {avail_emoji} {availability}")
            print(f"   URL: {url_data.get('url', '')[:60]}...")
            print()

        if len(enriched_urls) > sample_size:
            print(f"... and {len(enriched_urls) - sample_size} more URLs")

    def _empty_stats(self) -> Dict:
        """Return empty statistics"""
        return {
            "total_urls": 0,
            "scraped_successfully": 0,
            "failed": 0,
            "batches_processed": 0,
            "duration_seconds": 0,
            "in_stock": 0,
            "out_of_stock": 0,
            "unavailable": 0
        }

    def get_usage_stats(self) -> Dict:
        """Get API usage statistics"""
        return {
            "agent": self.name,
            "tool": "Apify Price Scraper",
            "batch_size": self.scraper.batch_size,
            "notes": "Concurrent batch processing for speed optimization"
        }
