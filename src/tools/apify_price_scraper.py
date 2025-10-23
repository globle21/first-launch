"""
Apify Price Scraper - Extracts product prices and details from URLs
Uses Apify Actor with concurrent batch processing for speed
"""

import os
import time
from typing import Dict, List, Optional
from apify_client import ApifyClient
from concurrent.futures import ThreadPoolExecutor, as_completed


class ApifyPriceScraper:
    """
    Tool for scraping product prices and details using Apify

    Features:
    - Batch processing (20 URLs per batch for optimal speed)
    - Concurrent execution (multiple batches in parallel)
    - Error handling (marks unavailable/out of stock products)
    - Enriches URLs with: name, price, currency, image, availability
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Apify price scraper

        Args:
            api_key: Apify API key (if None, reads from environment)
        """
        self.api_key = api_key or os.getenv("APIFY_TOKEN")
        if not self.api_key:
            raise ValueError("APIFY_TOKEN not found in environment variables")

        self.client = ApifyClient(self.api_key)
        self.actor_id = '2APbAvDfNDOWXbkWf'
        self.batch_size = 20  # Optimal batch size for speed

    def scrape_batch(
        self,
        urls: List[str],
        batch_number: int = 1,
        timeout: int = 300
    ) -> List[Dict]:
        """
        Scrape a batch of up to 20 URLs using Apify

        Args:
            urls: List of URLs to scrape (max 20 for optimal speed)
            batch_number: Batch identifier for logging
            timeout: Maximum time to wait (seconds)

        Returns:
            List of dictionaries with scraped data
        """
        if len(urls) > self.batch_size:
            print(f"⚠️ Batch {batch_number}: Trimming {len(urls)} URLs to {self.batch_size}")
            urls = urls[:self.batch_size]

        try:
            print(f"\n🔍 [Batch {batch_number}] Scraping {len(urls)} URLs via Apify...")

            # Prepare input using user's specified format
            actor_input = {
                "detailsUrls": [{"url": url} for url in urls],
                "scrapeMode": "AUTO"
            }

            # Run the actor and wait for completion
            run = self.client.actor(self.actor_id).call(
                run_input=actor_input,
                timeout_secs=timeout
            )

            # Get the dataset ID from the run
            dataset_id = run.get('defaultDatasetId')

            if not dataset_id:
                print(f"❌ [Batch {batch_number}] No dataset ID returned")
                return self._create_empty_results(urls)

            # Fetch results from the dataset
            dataset_items = self.client.dataset(dataset_id).list_items().items

            if not dataset_items:
                print(f"⚠️ [Batch {batch_number}] No data returned")
                return self._create_empty_results(urls)

            print(f"✅ [Batch {batch_number}] Successfully scraped {len(dataset_items)} products")
            return dataset_items

        except Exception as e:
            print(f"❌ [Batch {batch_number}] Scraping failed: {e}")
            return self._create_empty_results(urls)

    def scrape_urls_concurrent(
        self,
        urls: List[Dict],
        max_workers: int = 5
    ) -> Dict:
        """
        Scrape all URLs concurrently in batches of 20

        Args:
            urls: List of URL dictionaries from Claude
                  Format: [{"url": "...", "product_type": "...", "variant": "..."}]
            max_workers: Maximum concurrent batches (default: 5)

        Returns:
            Dictionary with enriched URLs and statistics
        """
        start_time = time.time()

        # Extract URL strings for scraping
        url_strings = [url_data["url"] for url_data in urls]

        print(f"\n{'='*70}")
        print(f"💰 APIFY PRICE SCRAPING")
        print(f"{'='*70}")
        print(f"Total URLs: {len(url_strings)}")
        print(f"Batch size: {self.batch_size} URLs per batch")

        # Split into batches of 20
        batches = []
        for i in range(0, len(url_strings), self.batch_size):
            batch = url_strings[i:i + self.batch_size]
            batches.append((batch, i // self.batch_size + 1))  # (urls, batch_number)

        print(f"Total batches: {len(batches)}")
        print(f"Concurrent workers: {min(max_workers, len(batches))}")

        # Execute batches concurrently
        all_results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all batches
            future_to_batch = {
                executor.submit(self.scrape_batch, batch_urls, batch_num): batch_num
                for batch_urls, batch_num in batches
            }

            # Collect results as they complete
            for future in as_completed(future_to_batch):
                batch_num = future_to_batch[future]
                try:
                    batch_results = future.result()
                    all_results.extend(batch_results)
                except Exception as e:
                    print(f"❌ [Batch {batch_num}] Failed to get results: {e}")

        # Merge Apify data with original URL data from Claude
        enriched_urls = self._merge_data(urls, all_results)

        # Calculate statistics
        duration = time.time() - start_time
        stats = self._calculate_stats(enriched_urls, len(batches), duration)

        print(f"\n{'='*70}")
        print(f"✅ PRICE SCRAPING COMPLETE")
        print(f"{'='*70}")
        print(f"Total URLs: {stats['total_urls']}")
        print(f"Successfully scraped: {stats['scraped_successfully']}")
        print(f"In stock: {stats['in_stock']}")
        print(f"Out of stock: {stats['out_of_stock']}")
        print(f"Unavailable: {stats['unavailable']}")
        print(f"Duration: {stats['duration_seconds']:.1f}s")
        print(f"{'='*70}\n")

        return {
            "enriched_urls": enriched_urls,
            "stats": stats
        }

    def _merge_data(
        self,
        original_urls: List[Dict],
        apify_results: List[Dict]
    ) -> List[Dict]:
        """
        Merge Claude URL data with Apify scraping results

        Args:
            original_urls: Original URLs from Claude with product_type and variant
            apify_results: Scraped data from Apify

        Returns:
            List of enriched URL dictionaries
        """
        # Create URL lookup for Apify results
        apify_lookup = {}
        for result in apify_results:
            url = result.get("url", "")
            if url:
                apify_lookup[url] = result

        # Merge data
        enriched = []
        for original in original_urls:
            url = original["url"]
            apify_data = apify_lookup.get(url)

            # Start with original data from Claude
            enriched_url = {
                "url": url,
                "product_type": original.get("product_type", "unknown"),
                "variant": original.get("variant", "unknown")
            }

            # Add Apify data if available
            if apify_data:
                offers = apify_data.get("offers", {})

                # Determine availability
                if offers and offers.get("price"):
                    availability = "in_stock"
                    price = offers.get("price")
                    currency = offers.get("priceCurrency", "INR")
                else:
                    availability = "out_of_stock"
                    price = None
                    currency = None

                enriched_url.update({
                    "name": apify_data.get("name", "N/A"),
                    "price": price,
                    "currency": currency,
                    "image": apify_data.get("image", "N/A"),
                    "availability": availability
                })
            else:
                # URL failed to scrape
                enriched_url.update({
                    "name": "N/A",
                    "price": None,
                    "currency": None,
                    "image": "N/A",
                    "availability": "unavailable"
                })

            enriched.append(enriched_url)

        return enriched

    def _calculate_stats(
        self,
        enriched_urls: List[Dict],
        batches_processed: int,
        duration: float
    ) -> Dict:
        """
        Calculate scraping statistics

        Args:
            enriched_urls: List of enriched URLs
            batches_processed: Number of batches processed
            duration: Total duration in seconds

        Returns:
            Statistics dictionary
        """
        total = len(enriched_urls)
        in_stock = sum(1 for u in enriched_urls if u.get("availability") == "in_stock")
        out_of_stock = sum(1 for u in enriched_urls if u.get("availability") == "out_of_stock")
        unavailable = sum(1 for u in enriched_urls if u.get("availability") == "unavailable")
        scraped = in_stock + out_of_stock  # Successfully scraped (even if out of stock)

        return {
            "total_urls": total,
            "scraped_successfully": scraped,
            "failed": unavailable,
            "batches_processed": batches_processed,
            "duration_seconds": round(duration, 2),
            "in_stock": in_stock,
            "out_of_stock": out_of_stock,
            "unavailable": unavailable
        }

    def _create_empty_results(self, urls: List[str]) -> List[Dict]:
        """
        Create empty results for failed batch

        Args:
            urls: List of URLs that failed to scrape

        Returns:
            List of empty result dictionaries
        """
        return [{
            "url": url,
            "name": "N/A",
            "offers": {},
            "image": "N/A"
        } for url in urls]
