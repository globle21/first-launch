"""
LangGraph Workflow for Product Discovery
Multi-agent orchestration with optimized single-step architecture

ARCHITECTURE:
1. Gemini 2.5 Flash: Parse user input only (cheap)
2. OpenAI GPT-4o: Web search + structuring (superior quality, no hallucination)
3. Claude 4.5 Haiku: URL discovery (fast, cost-effective, Sonnet-4 performance)
4. Apify: Price scraping (concurrent batch processing, ~$0.025 per URL)

WORKFLOW:
  User Input
      ↓
  [Gemini] Parse → brand, product, variant
      ↓
  [OpenAI] Web search + structure → products list (NO PRICES)
      ↓
  User confirms product
      ↓
  [OpenAI] Web search + structure → variants list (NO PRICES!)
      ↓
  User selects variant
      ↓
  [Claude 4.5 Haiku] URL discovery → 20-50+ URLs
      ↓
  [Apify] Price scraping → enrich URLs with price/name/image (concurrent batches)
      ↓
  [Ranking] Sort by price → individual (low→high) → combo (low→high) → null price

KEY IMPROVEMENTS:
- Removed Gemini processing layer (was causing hallucinations)
- OpenAI now returns structured JSON directly
- No fake products/variants - only what actually exists
- Faster workflow (one less processing step)
- More accurate (GPT doesn't hallucinate like Gemini did)
- Concurrent price scraping (20 URLs/batch, multiple batches in parallel)
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from langgraph.graph import StateGraph, START, END

from .state.workflow_state import WorkflowState, StageLog
from .agents.orchestrator_agent import OrchestratorAgent
from .agents.product_confirmation_agent import ProductConfirmationAgent
from .agents.url_discovery_agent import URLDiscoveryAgent
from .agents.url_extraction_agent import URLExtractionAgent


# Results directory
RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)
(RESULTS_DIR / "product_confirmations").mkdir(exist_ok=True)
(RESULTS_DIR / "url_discoveries").mkdir(exist_ok=True)


# ============================================================================
# WORKFLOW NODES
# ============================================================================

def node_parse_input(state: WorkflowState) -> Dict:
    """
    Node 1: Parse user input to extract brand, product, variant
    Uses: OrchestratorAgent (Gemini 2.5 Flash)
    """
    stage_name = "input_parsing"
    start_time = datetime.now()

    log_entry = StageLog(
        stage=stage_name,
        status="started",
        timestamp=start_time.isoformat(),
        message=f"Parsing user query: '{state['user_query']}'"
    )

    try:
        # Initialize Orchestrator
        orchestrator = OrchestratorAgent()

        # Parse user input
        parse_result = orchestrator.parse_user_input(state["user_query"])

        # Extract parsed components
        parsed_data = parse_result.get("parsed_data", {})

        duration = (datetime.now() - start_time).total_seconds()

        log_entry.status = "success"
        log_entry.duration_seconds = duration
        log_entry.message = f"Extracted: {parsed_data.get('brand')} - {parsed_data.get('product_name')}"
        log_entry.metadata = {
            "confidence": parse_result.get("confidence", "unknown"),
            "has_variant": parsed_data.get("has_variant", False)
        }

        return {
            "extracted_brand": parsed_data.get("brand"),
            "extracted_product_name": parsed_data.get("product_name"),
            "extracted_variant": parsed_data.get("variant"),
            "has_variant_in_query": parsed_data.get("has_variant", False),
            "current_stage": "product_confirmation",
            "logs": [log_entry.to_dict()]
        }

    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        error_msg = str(e)

        log_entry.status = "error"
        log_entry.error = error_msg
        log_entry.duration_seconds = duration

        return {
            "current_stage": "failed",
            "logs": [log_entry.to_dict()],
            "errors": [f"[{stage_name}] {error_msg}"]
        }


def node_search_brand_page(state: WorkflowState) -> Dict:
    """
    Node 2: Search brand page and find product
    Architecture: OpenAI searches and structures directly
    """
    stage_name = "brand_page_search"
    start_time = datetime.now()

    log_entry = StageLog(
        stage=stage_name,
        status="started",
        timestamp=start_time.isoformat(),
        message=f"Searching brand page for {state['extracted_brand']}"
    )

    try:
        # Initialize Orchestrator (Gemini processor)
        orchestrator = OrchestratorAgent()

        # Initialize ProductConfirmationAgent (OpenAI direct structuring)
        agent = ProductConfirmationAgent(orchestrator_agent=orchestrator)

        # Search brand page (OpenAI search + structuring directly)
        search_result = agent.search_and_confirm_product(
            brand=state["extracted_brand"],
            product_name=state["extracted_product_name"],
            variant_hint=state.get("extracted_variant")
        )

        duration = (datetime.now() - start_time).total_seconds()

        brand_page_found = search_result.get("brand_page_found", False)
        products_found = search_result.get("products_found", [])

        log_entry.status = "success" if brand_page_found else "error"
        log_entry.duration_seconds = duration
        log_entry.message = f"Brand page {'found' if brand_page_found else 'not found'}, {len(products_found)} products"
        log_entry.metadata = {
            "brand_page_url": search_result.get("brand_page_url"),
            "num_products": len(products_found),
            "match_confidence": search_result.get("match_confidence", "unknown")
        }

        # Handle product selection
        confirmed_product = None
        user_confirmed = False

        if len(products_found) == 0:
            # No products found
            print("❌ No matching products found on brand page")
        elif len(products_found) == 1:
            # Auto-select the only product
            confirmed_product = products_found[0]
            user_confirmed = True
            print(f"✅ Auto-selected only product: {confirmed_product.get('name')}")
        else:
            # Multiple products - ask user to select
            print(f"\n🔍 Found {len(products_found)} product options:")
            print("-" * 70)
            for i, product in enumerate(products_found, 1):
                product_name = product.get('name', 'Unknown')
                product_url = product.get('url', '')
                print(f"{i}. {product_name}")
                print(f"   URL: {product_url[:60]}...")
            print("-" * 70)

            while True:
                try:
                    choice = input(f"\n👉 Select product (1-{len(products_found)}): ").strip()
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(products_found):
                        confirmed_product = products_found[choice_idx]
                        user_confirmed = True
                        print(f"✅ Selected: {confirmed_product.get('name')}")
                        break
                    else:
                        print(f"⚠️  Please enter a number between 1 and {len(products_found)}")
                except ValueError:
                    print("⚠️  Please enter a valid number")
                except KeyboardInterrupt:
                    print("\n❌ User cancelled selection")
                    return {
                        "current_stage": "failed",
                        "logs": [log_entry.to_dict()],
                        "errors": ["User cancelled product selection"]
                    }

        return {
            "brand_page_url": search_result.get("brand_page_url"),
            "brand_page_found": brand_page_found,
            "product_candidates": products_found,
            "confirmed_product": confirmed_product,
            "user_confirmed_product": user_confirmed,
            "current_stage": "variant_extraction" if confirmed_product else "failed",
            "logs": [log_entry.to_dict()]
        }

    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        error_msg = str(e)

        log_entry.status = "error"
        log_entry.error = error_msg
        log_entry.duration_seconds = duration

        return {
            "brand_page_found": False,
            "current_stage": "failed",
            "logs": [log_entry.to_dict()],
            "errors": [f"[{stage_name}] {error_msg}"]
        }


def node_extract_variants(state: WorkflowState) -> Dict:
    """
    Node 3: Extract variants from confirmed product page
    Architecture: OpenAI searches and structures directly (no prices)
    """
    stage_name = "variant_extraction"
    start_time = datetime.now()

    log_entry = StageLog(
        stage=stage_name,
        status="started",
        timestamp=start_time.isoformat()
    )

    # Check if we should skip (variant already in query or no product confirmed)
    if state.get("has_variant_in_query"):
        log_entry.status = "skipped"
        log_entry.message = "User already specified variant, skipping extraction"
        return {
            "current_stage": "url_discovery",
            "needs_variant_selection": False,
            "logs": [log_entry.to_dict()]
        }

    if not state.get("confirmed_product"):
        log_entry.status = "skipped"
        log_entry.message = "No product confirmed, skipping variant extraction"
        return {
            "current_stage": "failed",
            "logs": [log_entry.to_dict()],
            "errors": ["No product confirmed before variant extraction"]
        }

    try:
        # Initialize Orchestrator (only for input parsing)
        orchestrator = OrchestratorAgent()

        # Initialize ProductConfirmationAgent (OpenAI direct structuring)
        agent = ProductConfirmationAgent(orchestrator_agent=orchestrator)

        confirmed_product = state["confirmed_product"]
        product_name = confirmed_product.get("name", "")
        product_url = confirmed_product.get("url", "")

        # Extract variants (OpenAI search + structuring directly, no prices)
        variant_result = agent.extract_product_variants(
            product_name=product_name,
            product_url=product_url,
            variant_hint=state.get("extracted_variant")
        )

        duration = (datetime.now() - start_time).total_seconds()

        variants = variant_result.get("variants", [])
        variants_found = variant_result.get("variants_found", False)

        log_entry.status = "success"
        log_entry.duration_seconds = duration
        log_entry.message = f"Found {len(variants)} variants" if variants_found else "No variants found"
        log_entry.metadata = {
            "total_variants": len(variants),
            "variants_found": variants_found
        }

        # Handle variant selection
        selected_variant = None
        variant_confirmed = False

        if len(variants) == 0:
            # No variants found - product has single version
            selected_variant = {"type": "standard", "value": "standard"}
            variant_confirmed = True
            print(f"✅ No variants found - using standard version")
        elif len(variants) == 1:
            # Auto-select the only variant
            selected_variant = variants[0]
            variant_confirmed = True
            print(f"✅ Auto-selected only variant: {selected_variant.get('value')}")
        else:
            # Multiple variants - ask user to select
            print(f"\n🎯 Found {len(variants)} variant options:")
            print("-" * 70)
            for i, variant in enumerate(variants, 1):
                variant_type = variant.get('type', 'Unknown')
                variant_value = variant.get('value', 'Unknown')
                print(f"{i}. {variant_value} ({variant_type})")
            print("-" * 70)

            while True:
                try:
                    choice = input(f"\n👉 Select variant (1-{len(variants)}): ").strip()
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(variants):
                        selected_variant = variants[choice_idx]
                        variant_confirmed = True
                        print(f"✅ Selected: {selected_variant.get('value')}")
                        break
                    else:
                        print(f"⚠️  Please enter a number between 1 and {len(variants)}")
                except ValueError:
                    print("⚠️  Please enter a valid number")
                except KeyboardInterrupt:
                    print("\n❌ User cancelled selection")
                    return {
                        "current_stage": "failed",
                        "logs": [log_entry.to_dict()],
                        "errors": ["User cancelled variant selection"]
                    }

        return {
            "available_variants": variants,
            "selected_variant": selected_variant,
            "user_confirmed_variant": variant_confirmed,
            "current_stage": "url_discovery" if selected_variant else "failed",
            "logs": [log_entry.to_dict()]
        }

    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        error_msg = str(e)

        log_entry.status = "error"
        log_entry.error = error_msg
        log_entry.duration_seconds = duration

        return {
            "current_stage": "failed",
            "logs": [log_entry.to_dict()],
            "errors": [f"[{stage_name}] {error_msg}"]
        }


def node_discover_urls(state: WorkflowState) -> Dict:
    """
    Node 4: Discover product URLs across retailers
    Uses: URLDiscoveryAgent (Claude 4.5 Haiku)
    """
    stage_name = "url_discovery"
    start_time = datetime.now()

    log_entry = StageLog(
        stage=stage_name,
        status="started",
        timestamp=start_time.isoformat()
    )

    # Validate we have required data
    if not state.get("confirmed_product") and not state.get("selected_variant"):
        log_entry.status = "skipped"
        log_entry.message = "No product/variant confirmed, skipping URL discovery"
        return {
            "current_stage": "failed",
            "logs": [log_entry.to_dict()],
            "errors": ["No product or variant confirmed before URL discovery"]
        }

    try:
        # Initialize agent
        agent = URLDiscoveryAgent()

        # Get confirmed product details
        confirmed_product = state.get("confirmed_product", {})
        product_name = confirmed_product.get("name", state["extracted_product_name"])  # Use confirmed product name, fallback to extracted
        product_url = confirmed_product.get("url")

        # Determine variant to search for
        variant = None
        if state.get("selected_variant"):
            variant = state["selected_variant"].get("value")
        elif state.get("extracted_variant"):
            variant = state["extracted_variant"]
        else:
            # No variant specified - use product without variant
            variant = "standard"  # Generic fallback

        # Discover URLs using CONFIRMED product name (not original extracted name)
        discovery_result = agent.discover_urls(
            brand=state["extracted_brand"],
            product_name=product_name,  # Use confirmed product name
            variant=variant,
            brand_product_url=product_url
        )

        duration = (datetime.now() - start_time).total_seconds()

        urls = discovery_result.get("urls", [])
        total_urls = len(urls)

        log_entry.status = "success"
        log_entry.duration_seconds = duration
        log_entry.message = f"Discovered {total_urls} URLs across retailers"
        log_entry.metadata = {
            "total_urls": total_urls,
            "platforms_searched": discovery_result.get("search_summary", {}).get("platforms_searched", 0),
            "web_searches": agent.tool.search_count
        }

        return {
            "discovered_urls": urls,
            "total_urls_found": total_urls,
            "current_stage": "complete",
            "logs": [log_entry.to_dict()]
        }

    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        error_msg = str(e)

        log_entry.status = "error"
        log_entry.error = error_msg
        log_entry.duration_seconds = duration

        return {
            "discovered_urls": [],
            "total_urls_found": 0,
            "current_stage": "failed",
            "logs": [log_entry.to_dict()],
            "errors": [f"[{stage_name}] {error_msg}"]
        }


def node_scrape_prices(state: WorkflowState) -> Dict:
    """
    Node 5: Scrape prices and product details from discovered URLs
    Uses: PriceScrapingAgent (Apify with concurrent batch processing)
    """
    stage_name = "price_scraping"
    start_time = datetime.now()

    log_entry = StageLog(
        stage=stage_name,
        status="started",
        timestamp=start_time.isoformat()
    )

    # Validate we have URLs to scrape
    discovered_urls = state.get("discovered_urls", [])
    if not discovered_urls:
        log_entry.status = "skipped"
        log_entry.message = "No URLs discovered, skipping price scraping"
        return {
            "enriched_urls": [],
            "price_scraping_stats": {},
            "current_stage": "price_scraping",
            "logs": [log_entry.to_dict()]
        }

    try:
        # Initialize PriceScrapingAgent
        from .agents.price_scraping_agent import PriceScrapingAgent
        agent = PriceScrapingAgent()

        # Enrich URLs with price data (concurrent batch processing)
        result = agent.enrich_urls(
            discovered_urls=discovered_urls,
            max_workers=5  # Process up to 5 batches concurrently
        )

        duration = (datetime.now() - start_time).total_seconds()

        enriched_urls = result.get("enriched_urls", [])
        stats = result.get("stats", {})

        log_entry.status = "success"
        log_entry.duration_seconds = duration
        log_entry.message = f"Enriched {stats.get('scraped_successfully', 0)}/{stats.get('total_urls', 0)} URLs with price data"
        log_entry.metadata = stats

        return {
            "enriched_urls": enriched_urls,
            "price_scraping_stats": stats,
            "current_stage": "price_scraping",
            "logs": [log_entry.to_dict()]
        }

    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        error_msg = str(e)

        log_entry.status = "error"
        log_entry.error = error_msg
        log_entry.duration_seconds = duration

        return {
            "enriched_urls": [],
            "price_scraping_stats": {},
            "current_stage": "failed",
            "logs": [log_entry.to_dict()],
            "errors": [f"[{stage_name}] {error_msg}"]
        }


def node_calculate_per_unit_prices(state: WorkflowState) -> Dict:
    """
    Node 6: Calculate per-unit prices for all products
    - For combo products with non-null price: Calculate using ComboPricingAgent
    - For individual products with non-null price: Set per_unit_price = price
    - Returns enriched_urls with per_unit_price fields
    """
    stage_name = "per_unit_pricing"
    start_time = datetime.now()

    log_entry = StageLog(
        stage=stage_name,
        status="started",
        timestamp=start_time.isoformat()
    )

    # Get enriched URLs
    enriched_urls = state.get("enriched_urls", [])

    if not enriched_urls:
        log_entry.status = "skipped"
        log_entry.message = "No enriched URLs to process"
        return {
            "current_stage": "per_unit_pricing",
            "logs": [log_entry.to_dict()]
        }

    try:
        print(f"\n{'='*70}")
        print(f"💰 CALCULATING PER-UNIT PRICES")
        print(f"{'='*70}")
        print(f"Total products to process: {len(enriched_urls)}")

        # Import combo pricing agent
        from .agents.combo_pricing_agent import ComboPricingAgent
        combo_agent = ComboPricingAgent()

        # Get workflow context
        brand = state.get("extracted_brand")
        original_product_name = state.get("confirmed_product", {}).get("name") or state.get("extracted_product_name")
        original_variant = state.get("selected_variant", {}).get("value") or state.get("extracted_variant")
        brand_page_url = state.get("brand_page_url")

        # Process each URL
        updated_urls = []
        combos_processed = 0
        combos_successful = 0
        individuals_processed = 0

        for url_data in enriched_urls:
            product_type = url_data.get("product_type", "unknown")
            price = url_data.get("price")

            # Skip products with null price
            if price is None or price == "null":
                updated_urls.append(url_data)
                continue

            # Convert price to float
            try:
                price_float = float(price)
            except (ValueError, TypeError):
                updated_urls.append(url_data)
                continue

            # INDIVIDUAL PRODUCT: per_unit_price = price
            if product_type == "individual":
                url_data_copy = url_data.copy()
                url_data_copy["per_unit_price"] = f"{price_float:.2f}"
                updated_urls.append(url_data_copy)
                individuals_processed += 1

            # COMBO PRODUCT: Calculate per-unit price
            elif product_type == "combo":
                combos_processed += 1
                combo_url = url_data.get("url")

                print(f"\n📦 Processing combo {combos_processed}: {combo_url[:60]}...")

                # Calculate combo pricing
                pricing_result = combo_agent.calculate_combo_pricing(
                    combo_url=combo_url,
                    combo_sale_price=price_float,
                    brand=brand,
                    original_product_name=original_product_name,
                    original_variant=original_variant,
                    brand_page_url=brand_page_url
                )

                if pricing_result:
                    # Add per_unit_price and combo_breakdown
                    url_data_copy = url_data.copy()
                    url_data_copy["per_unit_price"] = pricing_result["per_unit_price"]
                    url_data_copy["combo_breakdown"] = pricing_result["combo_breakdown"]
                    updated_urls.append(url_data_copy)
                    combos_successful += 1
                    print(f"✅ Per-unit price: ₹{pricing_result['per_unit_price']}")
                else:
                    # If calculation fails, set per_unit_price to null
                    url_data_copy = url_data.copy()
                    url_data_copy["per_unit_price"] = None
                    url_data_copy["combo_breakdown"] = None
                    updated_urls.append(url_data_copy)
                    print(f"❌ Failed to calculate per-unit price")

            else:
                # Unknown product type
                updated_urls.append(url_data)

        duration = (datetime.now() - start_time).total_seconds()

        log_entry.status = "success"
        log_entry.duration_seconds = duration
        log_entry.message = f"Calculated per-unit prices for {individuals_processed} individual + {combos_successful}/{combos_processed} combo products"
        log_entry.metadata = {
            "total_products": len(enriched_urls),
            "individuals_processed": individuals_processed,
            "combos_processed": combos_processed,
            "combos_successful": combos_successful,
            "combos_failed": combos_processed - combos_successful
        }

        print(f"\n✅ Per-unit pricing complete:")
        print(f"   Individual products: {individuals_processed}")
        print(f"   Combo products: {combos_successful}/{combos_processed}")
        print(f"{'='*70}\n")

        return {
            "enriched_urls": updated_urls,
            "current_stage": "per_unit_pricing",
            "logs": [log_entry.to_dict()]
        }

    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        error_msg = str(e)

        log_entry.status = "error"
        log_entry.error = error_msg
        log_entry.duration_seconds = duration

        print(f"⚠️ Per-unit pricing failed: {error_msg}")
        print(f"   Continuing with original prices")

        # Return original enriched_urls if calculation fails
        return {
            "current_stage": "per_unit_pricing",
            "logs": [log_entry.to_dict()],
            "errors": [f"[{stage_name}] {error_msg}"]
        }


def node_rank_products(state: WorkflowState) -> Dict:
    """
    Node 7: Rank enriched URLs by per-unit price (UPDATED)
    Sorting logic:
    1. All products with per_unit_price (individual + combo, sorted by per_unit_price: lowest to highest)
    2. Products with null per_unit_price (at the end)
    """
    stage_name = "product_ranking"
    start_time = datetime.now()

    log_entry = StageLog(
        stage=stage_name,
        status="started",
        timestamp=start_time.isoformat()
    )

    # Get enriched URLs
    enriched_urls = state.get("enriched_urls", [])

    if not enriched_urls:
        log_entry.status = "skipped"
        log_entry.message = "No enriched URLs to rank"
        return {
            "current_stage": "product_ranking",
            "logs": [log_entry.to_dict()]
        }

    try:
        print(f"\n{'='*70}")
        print(f"📊 RANKING PRODUCTS BY PER-UNIT PRICE")
        print(f"{'='*70}")
        print(f"Total products to rank: {len(enriched_urls)}")

        # Separate by per_unit_price availability
        with_per_unit_price = []
        without_per_unit_price = []

        for url_data in enriched_urls:
            per_unit_price = url_data.get("per_unit_price")

            if per_unit_price is None or per_unit_price == "null":
                without_per_unit_price.append(url_data)
            else:
                with_per_unit_price.append(url_data)

        # Sort products with per_unit_price (lowest to highest)
        # This includes both individual and combo products
        with_per_unit_price.sort(key=lambda x: float(x.get("per_unit_price", 0)))

        # Concatenate: products with per_unit_price → products without per_unit_price
        ranked_urls = with_per_unit_price + without_per_unit_price

        duration = (datetime.now() - start_time).total_seconds()

        log_entry.status = "success"
        log_entry.duration_seconds = duration
        log_entry.message = f"Ranked {len(ranked_urls)} products by per-unit price"
        log_entry.metadata = {
            "with_per_unit_price": len(with_per_unit_price),
            "without_per_unit_price": len(without_per_unit_price)
        }

        print(f"✅ Ranking complete:")
        print(f"   Products with per-unit price: {len(with_per_unit_price)}")
        print(f"   Products without per-unit price: {len(without_per_unit_price)}")
        print(f"{'='*70}\n")

        return {
            "enriched_urls": ranked_urls,  # Replace with ranked list
            "current_stage": "product_ranking",
            "logs": [log_entry.to_dict()]
        }

    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        error_msg = str(e)

        log_entry.status = "error"
        log_entry.error = error_msg
        log_entry.duration_seconds = duration

        # If ranking fails, return original unsorted list
        print(f"⚠️ Ranking failed: {error_msg}")
        print(f"   Returning unsorted list")

        return {
            "current_stage": "product_ranking",
            "logs": [log_entry.to_dict()],
            "errors": [f"[{stage_name}] {error_msg}"]
        }


def node_finalize(state: WorkflowState) -> Dict:
    """
    Final node: Calculate duration, set completion status
    """
    try:
        start_time = datetime.fromisoformat(state["workflow_start_time"])
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()

        has_errors = bool(state.get("errors"))
        has_urls = bool(state.get("discovered_urls"))
        has_enriched_urls = bool(state.get("enriched_urls"))
        completed_successfully = not has_errors and has_urls and has_enriched_urls

        return {
            "workflow_end_time": end_time.isoformat(),
            "total_duration_seconds": total_duration,
            "completed_successfully": completed_successfully,
            "current_stage": "complete",
            "logs": [{
                "stage": "finalize",
                "status": "success" if completed_successfully else "completed_with_errors",
                "timestamp": end_time.isoformat(),
                "duration_seconds": total_duration,
                "message": f"Workflow completed in {total_duration:.2f}s"
            }]
        }

    except Exception as e:
        return {
            "workflow_end_time": datetime.now().isoformat(),
            "completed_successfully": False,
            "current_stage": "failed",
            "errors": [f"Finalization error: {str(e)}"]
        }


def node_extract_from_url(state: WorkflowState) -> Dict:
    """
    Node 0 (URL workflow only): Extract product details from URL
    Uses: URLExtractionAgent (Gemini 2.0 Flash)
    """
    stage_name = "url_extraction"
    start_time = datetime.now()

    log_entry = StageLog(
        stage=stage_name,
        status="started",
        timestamp=start_time.isoformat(),
        message=f"Extracting from URL: {state['product_url']}"
    )

    try:
        # Initialize URL Extraction Agent
        url_agent = URLExtractionAgent()

        # Extract details from URL
        extraction_result = url_agent.extract_from_url(state["product_url"])

        if not extraction_result.get("success"):
            error_msg = extraction_result.get("error", "Unknown error")
            log_entry.status = "error"
            log_entry.error = error_msg
            log_entry.duration_seconds = (datetime.now() - start_time).total_seconds()

            print(f"\n❌ URL extraction failed: {error_msg}")
            print("💡 Please use keyword-based input instead.")

            return {
                "current_stage": "failed",
                "logs": [log_entry.to_dict()],
                "errors": [f"[{stage_name}] {error_msg}"]
            }

        # Extract details
        extracted_brand = extraction_result.get("brand")
        extracted_product = extraction_result.get("product_name")
        extracted_variant = extraction_result.get("variant")
        extraction_confidence = extraction_result.get("extraction_confidence", "unknown")

        print(f"\n✅ Extraction successful!")
        print(f"   Brand: {extracted_brand}")
        print(f"   Product: {extracted_product}")
        print(f"   Variant: {extracted_variant}")
        print(f"   Confidence: {extraction_confidence}")

        # Ask user for confirmation
        print("\n" + "-"*80)
        print("📍 Confirm extracted details")
        print("-"*80)
        print(f"\n✨ Extracted product details:")
        print(f"   Brand: {extracted_brand}")
        print(f"   Product: {extracted_product}")
        print(f"   Variant: {extracted_variant}")
        print()

        while True:
            confirmation = input("Is this correct? (yes/no): ").strip().lower()

            if confirmation in ["yes", "y"]:
                print("\n✅ Details confirmed!")
                break
            elif confirmation in ["no", "n"]:
                print("\n❌ Details not confirmed.")
                print("💡 Please use keyword-based input instead, or provide a different URL.")

                log_entry.status = "error"
                log_entry.error = "User rejected extraction"
                log_entry.duration_seconds = (datetime.now() - start_time).total_seconds()

                return {
                    "current_stage": "failed",
                    "logs": [log_entry.to_dict()],
                    "errors": ["User rejected URL extraction"]
                }
            else:
                print("⚠️  Please answer 'yes' or 'no'")

        duration = (datetime.now() - start_time).total_seconds()

        log_entry.status = "success"
        log_entry.duration_seconds = duration
        log_entry.message = f"Extracted: {extracted_brand} - {extracted_product} - {extracted_variant}"
        log_entry.metadata = {
            "confidence": extraction_confidence,
            "brand": extracted_brand,
            "product": extracted_product,
            "variant": extracted_variant
        }

        # Pre-populate state to skip product confirmation and variant extraction
        return {
            "extracted_brand": extracted_brand,
            "extracted_product_name": extracted_product,
            "extracted_variant": extracted_variant,
            "has_variant_in_query": True,
            "url_extraction_confidence": extraction_confidence,
            # Skip product confirmation stage - product is confirmed from URL
            "confirmed_product": {
                "name": extracted_product,
                "url": state["product_url"],
                "description": f"Extracted from URL: {extracted_brand} {extracted_product} {extracted_variant}"
            },
            "user_confirmed_product": True,
            # Skip variant extraction stage - variant is extracted from URL
            "selected_variant": {
                "type": "extracted_from_url",
                "value": extracted_variant,
                "url": state["product_url"]
            },
            "user_confirmed_variant": True,
            "current_stage": "url_discovery",
            "logs": [log_entry.to_dict()]
        }

    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        error_msg = str(e)

        log_entry.status = "error"
        log_entry.error = error_msg
        log_entry.duration_seconds = duration

        print(f"\n❌ URL extraction error: {error_msg}")

        return {
            "current_stage": "failed",
            "logs": [log_entry.to_dict()],
            "errors": [f"[{stage_name}] {error_msg}"]
        }


# ============================================================================
# WORKFLOW BUILDER
# ============================================================================

def create_workflow() -> StateGraph:
    """
    Create and compile the LangGraph workflow

    Flow:
        START → parse_input → search_brand → extract_variants → discover_urls →
        scrape_prices → calculate_per_unit_prices → rank_products → finalize → END
    """

    # Create state graph
    builder = StateGraph(WorkflowState)

    # Add nodes
    builder.add_node("parse_input", node_parse_input)
    builder.add_node("search_brand", node_search_brand_page)
    builder.add_node("extract_variants", node_extract_variants)
    builder.add_node("discover_urls", node_discover_urls)
    builder.add_node("scrape_prices", node_scrape_prices)
    builder.add_node("calculate_per_unit_prices", node_calculate_per_unit_prices)
    builder.add_node("rank_products", node_rank_products)
    builder.add_node("finalize", node_finalize)

    # Define edges (sequential flow)
    builder.add_edge(START, "parse_input")
    builder.add_edge("parse_input", "search_brand")
    builder.add_edge("search_brand", "extract_variants")
    builder.add_edge("extract_variants", "discover_urls")
    builder.add_edge("discover_urls", "scrape_prices")
    builder.add_edge("scrape_prices", "calculate_per_unit_prices")
    builder.add_edge("calculate_per_unit_prices", "rank_products")
    builder.add_edge("rank_products", "finalize")
    builder.add_edge("finalize", END)

    # Compile
    workflow = builder.compile()

    return workflow


def create_url_workflow() -> StateGraph:
    """
    Create and compile the LangGraph workflow for URL-based input

    Flow:
        START → extract_from_url → discover_urls → scrape_prices →
        calculate_per_unit_prices → rank_products → finalize → END

    This workflow skips parse_input, search_brand, and extract_variants
    because the URL extraction provides all needed information upfront.
    """

    # Create state graph
    builder = StateGraph(WorkflowState)

    # Add nodes (reuses existing nodes from keyword workflow)
    builder.add_node("extract_from_url", node_extract_from_url)
    builder.add_node("discover_urls", node_discover_urls)
    builder.add_node("scrape_prices", node_scrape_prices)
    builder.add_node("calculate_per_unit_prices", node_calculate_per_unit_prices)
    builder.add_node("rank_products", node_rank_products)
    builder.add_node("finalize", node_finalize)

    # Define edges (sequential flow)
    builder.add_edge(START, "extract_from_url")
    builder.add_edge("extract_from_url", "discover_urls")
    builder.add_edge("discover_urls", "scrape_prices")
    builder.add_edge("scrape_prices", "calculate_per_unit_prices")
    builder.add_edge("calculate_per_unit_prices", "rank_products")
    builder.add_edge("rank_products", "finalize")
    builder.add_edge("finalize", END)

    # Compile
    workflow = builder.compile()

    return workflow


# ============================================================================
# WORKFLOW EXECUTION
# ============================================================================

def run_workflow(user_query: str, session_id: str = None) -> Dict[str, Any]:
    """
    Execute the product discovery workflow (keyword-based input)

    Args:
        user_query: User's product search query
        session_id: Optional session ID

    Returns:
        Final workflow state
    """

    # Generate session ID
    if not session_id:
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    print("\n" + "="*80)
    print("🚀 PRODUCT DISCOVERY WORKFLOW (KEYWORD-BASED)")
    print("="*80)
    print(f"📝 Query: '{user_query}'")
    print(f"🆔 Session: {session_id}")
    print("="*80)
    print()

    # Initialize workflow
    workflow = create_workflow()

    # Prepare initial state
    initial_state: WorkflowState = {
        "user_query": user_query,
        "session_id": session_id,
        "input_type": "keyword",
        "product_url": None,
        "url_extraction_confidence": None,
        "extracted_brand": None,
        "extracted_product_name": None,
        "extracted_variant": None,
        "has_variant_in_query": False,
        "brand_page_url": None,
        "brand_page_found": False,
        "product_candidates": [],
        "confirmed_product": None,
        "user_confirmed_product": False,
        "available_variants": [],
        "selected_variant": None,
        "user_confirmed_variant": False,
        "discovered_urls": [],
        "total_urls_found": 0,
        "enriched_urls": [],
        "price_scraping_stats": {},
        "workflow_start_time": datetime.now().isoformat(),
        "workflow_end_time": None,
        "total_duration_seconds": None,
        "current_stage": "parsing",
        "logs": [],
        "errors": [],
        "completed_successfully": False,
        "needs_product_confirmation": False,
        "needs_variant_selection": False,
        "api_costs": {}
    }

    try:
        # Run workflow
        result = workflow.invoke(initial_state)

        # Print summary
        print_workflow_summary(result)

        # Save results
        save_workflow_results(result)

        return result

    except Exception as e:
        print(f"\n❌ Workflow execution failed: {e}")
        import traceback
        traceback.print_exc()
        raise


def run_workflow_from_url(product_url: str, session_id: str = None) -> Dict[str, Any]:
    """
    Execute the product discovery workflow (URL-based input)
    NOW USES LANGGRAPH - Consistent with keyword workflow!

    Workflow:
        START → extract_from_url → discover_urls → scrape_prices → 
        calculate_per_unit_prices → rank_products → finalize → END

    Args:
        product_url: Product page URL
        session_id: Optional session ID

    Returns:
        Final workflow state (same structure as keyword workflow)
    """

    # Generate session ID
    if not session_id:
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    print("\n" + "="*80)
    print("🚀 PRODUCT DISCOVERY WORKFLOW (URL-BASED)")
    print("="*80)
    print(f"🔗 URL: {product_url}")
    print(f"🆔 Session: {session_id}")
    print("="*80)
    print()

    # Initialize URL workflow (uses LangGraph)
    workflow = create_url_workflow()

    # Prepare initial state (similar to keyword workflow)
    initial_state: WorkflowState = {
        "user_query": product_url,  # URL as query
        "session_id": session_id,
        "input_type": "url",
        "product_url": product_url,
        "url_extraction_confidence": None,
        "extracted_brand": None,
        "extracted_product_name": None,
        "extracted_variant": None,
        "has_variant_in_query": False,
        "brand_page_url": None,
        "brand_page_found": False,
        "product_candidates": [],
        "confirmed_product": None,
        "user_confirmed_product": False,
        "available_variants": [],
        "selected_variant": None,
        "user_confirmed_variant": False,
        "discovered_urls": [],
        "total_urls_found": 0,
        "enriched_urls": [],
        "price_scraping_stats": {},
        "workflow_start_time": datetime.now().isoformat(),
        "workflow_end_time": None,
        "total_duration_seconds": None,
        "current_stage": "url_extraction",
        "logs": [],
        "errors": [],
        "completed_successfully": False,
        "needs_product_confirmation": False,
        "needs_variant_selection": False,
        "api_costs": {}
    }

    try:
        # Run workflow (SAME AS KEYWORD WORKFLOW!)
        result = workflow.invoke(initial_state)

        # Print summary
        print_workflow_summary(result)

        # Save results
        save_workflow_results(result)

        return result

    except Exception as e:
        print(f"\n❌ Workflow execution failed: {e}")
        import traceback
        traceback.print_exc()
        raise


def print_workflow_summary(state: Dict[str, Any]):
    """Print summary of workflow execution"""

    print("\n" + "="*80)
    print("📊 WORKFLOW SUMMARY")
    print("="*80)

    status = "✅ SUCCESS" if state.get("completed_successfully") else "⚠️ FAILED"
    print(f"Status: {status}")
    print(f"Duration: {state.get('total_duration_seconds', 0):.2f}s")
    print(f"Session: {state.get('session_id')}")

    print("\n📋 STAGES:")
    print("-"*80)
    for log in state.get("logs", []):
        stage = log.get("stage", "unknown")
        status_icon = {
            "started": "🔄",
            "success": "✅",
            "error": "❌",
            "skipped": "⏭️"
        }.get(log.get("status"), "❓")

        duration = log.get("duration_seconds")
        duration_str = f" ({duration:.2f}s)" if duration else ""

        message = log.get("message", "")

        print(f"{status_icon} {stage.upper()}{duration_str}")
        if message:
            print(f"   {message}")

    # Show results
    urls = state.get("discovered_urls", [])
    if urls:
        print(f"\n🔗 URLS FOUND: {len(urls)}")
        print("-"*80)
        for i, url_data in enumerate(urls[:10], 1):
            url = url_data.get("url", "")
            product_type = url_data.get("product_type", "unknown")
            variant = url_data.get("variant", "")
            print(f"{i}. [{product_type}] {url[:60]}... ({variant})")
        if len(urls) > 10:
            print(f"... and {len(urls) - 10} more")

    print("\n" + "="*80)


def save_workflow_results(state: Dict[str, Any]):
    """Save workflow results to JSON file"""

    session_id = state.get("session_id", "unknown")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    result_file = RESULTS_DIR / f"workflow_{session_id}_{timestamp}.json"

    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

    print(f"💾 Results saved: {result_file}")
