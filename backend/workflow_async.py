"""
Async Workflow for Web Interface
Modified workflow that uses SessionManager instead of CLI input()
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.state.workflow_state import WorkflowState, StageLog
from src.agents.orchestrator_agent import OrchestratorAgent
from src.agents.product_confirmation_agent import ProductConfirmationAgent
from src.agents.url_discovery_agent import URLDiscoveryAgent
from src.agents.url_extraction_agent import URLExtractionAgent

from session_manager import session_manager


def run_workflow_async(session_id: str, input_type: str, user_input: str):
    """
    Run workflow asynchronously with session-based confirmations
    This replaces CLI input() with session state checks
    """
    
    try:
        # Initialize workflow state based on input type
        if input_type == "keyword":
            _run_keyword_workflow(session_id, user_input)
        elif input_type == "url":
            _run_url_workflow(session_id, user_input)
        else:
            session_manager.set_failed(session_id, f"Invalid input type: {input_type}")
    
    except Exception as e:
        session_manager.set_failed(session_id, f"Workflow error: {str(e)}")
        session_manager.add_progress_log(session_id, {
            "stage": "error",
            "message": f"Critical error: {str(e)}",
            "status": "error"
        })


def _run_keyword_workflow(session_id: str, user_query: str):
    """Keyword-based workflow"""
    
    # Stage 1: Parse Input
    session_manager.add_progress_log(session_id, {
        "stage": "parsing",
        "message": f"Parsing query: {user_query}",
        "status": "started"
    })
    session_manager.update_session(session_id, current_stage="parsing")
    
    try:
        orchestrator = OrchestratorAgent()
        parse_result = orchestrator.parse_user_input(user_query)
        parsed_data = parse_result.get("parsed_data", {})
        
        extracted_brand = parsed_data.get("brand")
        extracted_product = parsed_data.get("product_name")
        extracted_variant = parsed_data.get("variant")
        has_variant = parsed_data.get("has_variant", False)
        
        session_manager.add_progress_log(session_id, {
            "stage": "parsing",
            "message": f"Extracted: {extracted_brand} - {extracted_product}",
            "status": "success",
            "data": parsed_data
        })
        
    except Exception as e:
        session_manager.set_failed(session_id, f"Parsing failed: {str(e)}")
        return
    
    # Stage 2: Search Brand Page & Product Confirmation
    session_manager.add_progress_log(session_id, {
        "stage": "product_search",
        "message": f"Searching for {extracted_brand} {extracted_product}",
        "status": "started"
    })
    session_manager.update_session(session_id, current_stage="product_search")
    
    try:
        agent = ProductConfirmationAgent(orchestrator_agent=orchestrator)
        search_result = agent.search_and_confirm_product(
            brand=extracted_brand,
            product_name=extracted_product,
            variant_hint=extracted_variant
        )
        
        products_found = search_result.get("products_found", [])
        
        session_manager.add_progress_log(session_id, {
            "stage": "product_search",
            "message": f"Found {len(products_found)} products",
            "status": "success"
        })
        
        # Handle product selection
        if len(products_found) == 0:
            session_manager.set_failed(session_id, "No products found")
            return
        
        elif len(products_found) == 1:
            # Auto-select
            confirmed_product = products_found[0]
            session_manager.add_progress_log(session_id, {
                "stage": "product_confirmation",
                "message": f"Auto-selected: {confirmed_product.get('name')}",
                "status": "success"
            })
        
        else:
            # Need user confirmation - WAIT FOR USER
            session_manager.set_product_confirmation_needed(session_id, products_found)
            session_manager.add_progress_log(session_id, {
                "stage": "product_confirmation",
                "message": f"Please select from {len(products_found)} products",
                "status": "waiting"
            })
            
            # WAIT for user confirmation
            _wait_for_product_confirmation(session_id)
            
            # Check if user confirmed or cancelled
            session = session_manager.get_session(session_id)
            if not session or session.status == "failed":
                return
            
            confirmed_product = products_found[session.confirmed_product_index]
            session_manager.add_progress_log(session_id, {
                "stage": "product_confirmation",
                "message": f"User selected: {confirmed_product.get('name')}",
                "status": "success"
            })
    
    except Exception as e:
        session_manager.set_failed(session_id, f"Product search failed: {str(e)}")
        return
    
    # Stage 3: Extract Variants (if needed)
    if has_variant:
        session_manager.add_progress_log(session_id, {
            "stage": "variant_extraction",
            "message": "Variant already specified, skipping extraction",
            "status": "skipped"
        })
        selected_variant = {"type": "user_specified", "value": extracted_variant}
    
    else:
        session_manager.add_progress_log(session_id, {
            "stage": "variant_extraction",
            "message": "Extracting product variants",
            "status": "started"
        })
        session_manager.update_session(session_id, current_stage="variant_extraction")
        
        try:
            variant_result = agent.extract_product_variants(
                product_name=confirmed_product.get("name"),
                product_url=confirmed_product.get("url"),
                variant_hint=extracted_variant
            )
            
            variants = variant_result.get("variants", [])
            
            if len(variants) == 0:
                selected_variant = {"type": "standard", "value": "standard"}
                session_manager.add_progress_log(session_id, {
                    "stage": "variant_extraction",
                    "message": "No variants found, using standard",
                    "status": "success"
                })
            
            elif len(variants) == 1:
                selected_variant = variants[0]
                session_manager.add_progress_log(session_id, {
                    "stage": "variant_extraction",
                    "message": f"Auto-selected: {selected_variant.get('value')}",
                    "status": "success"
                })
            
            else:
                # Need user confirmation - WAIT FOR USER
                session_manager.set_variant_confirmation_needed(session_id, variants)
                session_manager.add_progress_log(session_id, {
                    "stage": "variant_confirmation",
                    "message": f"Please select from {len(variants)} variants",
                    "status": "waiting"
                })
                
                # WAIT for user confirmation
                _wait_for_variant_confirmation(session_id)
                
                # Check if user confirmed or cancelled
                session = session_manager.get_session(session_id)
                if not session or session.status == "failed":
                    return
                
                selected_variant = variants[session.confirmed_variant_index]
                session_manager.add_progress_log(session_id, {
                    "stage": "variant_confirmation",
                    "message": f"User selected: {selected_variant.get('value')}",
                    "status": "success"
                })
        
        except Exception as e:
            session_manager.set_failed(session_id, f"Variant extraction failed: {str(e)}")
            return
    
    # Continue with URL discovery and pricing
    _continue_workflow(
        session_id=session_id,
        brand=extracted_brand,
        product_name=confirmed_product.get("name"),
        variant=selected_variant.get("value"),
        product_url=confirmed_product.get("url")
    )


def _run_url_workflow(session_id: str, product_url: str):
    """URL-based workflow"""
    
    # Stage 1: Extract from URL
    session_manager.add_progress_log(session_id, {
        "stage": "url_extraction",
        "message": f"Extracting details from URL",
        "status": "started"
    })
    session_manager.update_session(session_id, current_stage="url_extraction")
    
    try:
        url_agent = URLExtractionAgent()
        extraction_result = url_agent.extract_from_url(product_url)
        
        if not extraction_result.get("success"):
            session_manager.set_failed(session_id, extraction_result.get("error", "Extraction failed"))
            return
        
        extracted_brand = extraction_result.get("brand")
        extracted_product = extraction_result.get("product_name")
        extracted_variant = extraction_result.get("variant")
        
        # Need user confirmation - WAIT FOR USER
        session_manager.set_url_extraction_confirmation_needed(session_id, {
            "brand": extracted_brand,
            "product": extracted_product,
            "variant": extracted_variant
        })
        session_manager.add_progress_log(session_id, {
            "stage": "url_extraction_confirmation",
            "message": "Please confirm extracted details",
            "status": "waiting"
        })
        
        # WAIT for user confirmation
        _wait_for_url_extraction_confirmation(session_id)
        
        # Check if user confirmed or cancelled
        session = session_manager.get_session(session_id)
        if not session or session.status == "failed" or not session.url_extraction_confirmed:
            session_manager.set_failed(session_id, "User rejected extraction")
            return
        
        session_manager.add_progress_log(session_id, {
            "stage": "url_extraction_confirmation",
            "message": "User confirmed extraction",
            "status": "success"
        })
    
    except Exception as e:
        session_manager.set_failed(session_id, f"URL extraction failed: {str(e)}")
        return
    
    # Continue with URL discovery and pricing
    _continue_workflow(
        session_id=session_id,
        brand=extracted_brand,
        product_name=extracted_product,
        variant=extracted_variant,
        product_url=product_url
    )


def _continue_workflow(
    session_id: str,
    brand: str,
    product_name: str,
    variant: str,
    product_url: Optional[str] = None
):
    """Continue workflow with URL discovery and pricing"""
    
    # Stage 4: URL Discovery
    session_manager.add_progress_log(session_id, {
        "stage": "url_discovery",
        "message": f"Discovering URLs for {brand} {product_name} {variant}",
        "status": "started"
    })
    session_manager.update_session(session_id, current_stage="url_discovery")
    
    try:
        url_agent = URLDiscoveryAgent()
        discovery_result = url_agent.discover_urls(
            brand=brand,
            product_name=product_name,
            variant=variant,
            brand_product_url=product_url
        )
        
        urls = discovery_result.get("urls", [])
        
        session_manager.add_progress_log(session_id, {
            "stage": "url_discovery",
            "message": f"Found {len(urls)} URLs",
            "status": "success"
        })
        
        if len(urls) == 0:
            session_manager.set_failed(session_id, "No URLs found")
            return
    
    except Exception as e:
        session_manager.set_failed(session_id, f"URL discovery failed: {str(e)}")
        return
    
    # Stage 5: Price Scraping
    session_manager.add_progress_log(session_id, {
        "stage": "price_scraping",
        "message": f"Scraping prices for {len(urls)} URLs",
        "status": "started"
    })
    session_manager.update_session(session_id, current_stage="price_scraping")
    
    try:
        from src.agents.price_scraping_agent import PriceScrapingAgent
        price_agent = PriceScrapingAgent()
        
        result = price_agent.enrich_urls(discovered_urls=urls, max_workers=5)
        enriched_urls = result.get("enriched_urls", [])
        stats = result.get("stats", {})
        
        session_manager.add_progress_log(session_id, {
            "stage": "price_scraping",
            "message": f"Enriched {stats.get('scraped_successfully', 0)}/{len(urls)} URLs",
            "status": "success",
            "data": stats
        })
    
    except Exception as e:
        session_manager.set_failed(session_id, f"Price scraping failed: {str(e)}")
        return
    
    # Stage 6: Per-Unit Pricing
    session_manager.add_progress_log(session_id, {
        "stage": "per_unit_pricing",
        "message": "Calculating per-unit prices",
        "status": "started"
    })
    session_manager.update_session(session_id, current_stage="per_unit_pricing")
    
    try:
        from src.agents.combo_pricing_agent import ComboPricingAgent
        combo_agent = ComboPricingAgent()
        
        updated_urls = []
        for url_data in enriched_urls:
            product_type = url_data.get("product_type", "unknown")
            price = url_data.get("price")
            
            if price is None or price == "null":
                updated_urls.append(url_data)
                continue
            
            try:
                price_float = float(price)
            except (ValueError, TypeError):
                updated_urls.append(url_data)
                continue
            
            if product_type == "individual":
                url_data_copy = url_data.copy()
                url_data_copy["per_unit_price"] = f"{price_float:.2f}"
                updated_urls.append(url_data_copy)
            
            elif product_type == "combo":
                pricing_result = combo_agent.calculate_combo_pricing(
                    combo_url=url_data.get("url"),
                    combo_sale_price=price_float,
                    brand=brand,
                    original_product_name=product_name,
                    original_variant=variant,
                    brand_page_url=product_url
                )
                
                if pricing_result:
                    url_data_copy = url_data.copy()
                    url_data_copy["per_unit_price"] = pricing_result["per_unit_price"]
                    url_data_copy["combo_breakdown"] = pricing_result["combo_breakdown"]
                    updated_urls.append(url_data_copy)
                else:
                    url_data_copy = url_data.copy()
                    url_data_copy["per_unit_price"] = None
                    updated_urls.append(url_data_copy)
            else:
                updated_urls.append(url_data)
        
        session_manager.add_progress_log(session_id, {
            "stage": "per_unit_pricing",
            "message": "Per-unit pricing complete",
            "status": "success"
        })
    
    except Exception as e:
        session_manager.add_progress_log(session_id, {
            "stage": "per_unit_pricing",
            "message": f"Warning: {str(e)}",
            "status": "warning"
        })
        updated_urls = enriched_urls
    
    # Stage 7: Ranking
    session_manager.add_progress_log(session_id, {
        "stage": "ranking",
        "message": "Ranking products by price",
        "status": "started"
    })
    session_manager.update_session(session_id, current_stage="ranking")
    
    try:
        with_per_unit = [u for u in updated_urls if u.get("per_unit_price") not in [None, "null"]]
        without_per_unit = [u for u in updated_urls if u.get("per_unit_price") in [None, "null"]]
        
        with_per_unit.sort(key=lambda x: float(x.get("per_unit_price", 0)))
        
        ranked_urls = with_per_unit + without_per_unit
        
        session_manager.add_progress_log(session_id, {
            "stage": "ranking",
            "message": f"Ranked {len(ranked_urls)} products",
            "status": "success"
        })
    
    except Exception as e:
        session_manager.add_progress_log(session_id, {
            "stage": "ranking",
            "message": f"Warning: {str(e)}",
            "status": "warning"
        })
        ranked_urls = updated_urls
    
    # Complete
    session_manager.set_completed(session_id, ranked_urls)
    session_manager.add_progress_log(session_id, {
        "stage": "complete",
        "message": f"Workflow completed successfully with {len(ranked_urls)} results",
        "status": "success"
    })


def _wait_for_product_confirmation(session_id: str, timeout_seconds: int = 300):
    """Wait for user to confirm product selection"""
    start_time = time.time()
    
    while time.time() - start_time < timeout_seconds:
        session = session_manager.get_session(session_id)
        
        if not session:
            return
        
        if not session.needs_product_confirmation:
            # User has confirmed
            return
        
        if session.status == "failed":
            # User cancelled
            return
        
        time.sleep(1)
    
    # Timeout
    session_manager.set_failed(session_id, "Product confirmation timeout")


def _wait_for_variant_confirmation(session_id: str, timeout_seconds: int = 300):
    """Wait for user to confirm variant selection"""
    start_time = time.time()
    
    while time.time() - start_time < timeout_seconds:
        session = session_manager.get_session(session_id)
        
        if not session:
            return
        
        if not session.needs_variant_confirmation:
            # User has confirmed
            return
        
        if session.status == "failed":
            # User cancelled
            return
        
        time.sleep(1)
    
    # Timeout
    session_manager.set_failed(session_id, "Variant confirmation timeout")


def _wait_for_url_extraction_confirmation(session_id: str, timeout_seconds: int = 300):
    """Wait for user to confirm URL extraction"""
    start_time = time.time()
    
    while time.time() - start_time < timeout_seconds:
        session = session_manager.get_session(session_id)
        
        if not session:
            return
        
        if not session.needs_url_extraction_confirmation:
            # User has confirmed or rejected
            return
        
        time.sleep(1)
    
    # Timeout
    session_manager.set_failed(session_id, "URL extraction confirmation timeout")
