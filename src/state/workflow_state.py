"""
LangGraph State Definition for Product Discovery Workflow
Multi-stage workflow: Input Parsing → Product Confirmation → Variant Selection → URL Discovery
"""

from typing import TypedDict, Optional, List, Dict, Any, Annotated
from dataclasses import dataclass, asdict
import operator


@dataclass
class StageLog:
    """Structured log entry for each workflow stage"""
    stage: str
    status: str  # 'started', 'success', 'error', 'waiting_user', 'skipped'
    timestamp: str
    duration_seconds: Optional[float] = None
    message: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v is not None}


class WorkflowState(TypedDict):
    """
    State schema for the landing page product discovery workflow

    Flow:
    1. User enters text query → parse_user_input
    2. ProductConfirmationAgent searches brand page → find product
    3. If variant not specified → extract variants → wait for user selection
    4. URLDiscoveryAgent searches for URLs → return results
    5. PriceScrapingAgent enriches URLs with prices → return enriched results
    6. Rank products by price → individual (low→high) → combo (low→high) → null
    """

    # ==================== INPUT STAGE ====================
    # User's raw input from landing page
    user_query: str  # e.g., "True Frog Curl Shampoo" or "True Frog Curl Shampoo 100ml"
    session_id: str

    # Input type tracking (for URL-based input feature)
    input_type: str  # "keyword" or "url"
    product_url: Optional[str]  # Original URL if input was URL-based
    url_extraction_confidence: Optional[str]  # Confidence of URL extraction ("high", "medium", "low")

    # ==================== PARSING STAGE ====================
    # Extracted from user query by Orchestrator
    extracted_brand: Optional[str]  # e.g., "True Frog"
    extracted_product_name: Optional[str]  # e.g., "Curl Shampoo"
    extracted_variant: Optional[str]  # e.g., "100ml" (if user mentioned it)
    has_variant_in_query: bool  # True if user specified variant upfront

    # ==================== PRODUCT CONFIRMATION STAGE ====================
    # Results from ProductConfirmationAgent (GPT-4o web search)
    brand_page_url: Optional[str]  # Official brand website
    brand_page_found: bool

    # List of potential product matches from brand page
    product_candidates: List[Dict[str, Any]]  # [{"name": "...", "url": "...", "description": "..."}]

    # User's confirmed product selection
    confirmed_product: Optional[Dict[str, Any]]
    user_confirmed_product: bool  # True when user confirms

    # ==================== VARIANT SELECTION STAGE ====================
    # Available variants extracted from brand page (NO PRICES)
    available_variants: List[Dict[str, Any]]  # [{"type": "size", "value": "100ml", "url": "..."}, ...]

    # User's selected variant (or auto-selected if specified in query)
    selected_variant: Optional[Dict[str, Any]]
    user_confirmed_variant: bool  # True when variant is confirmed

    # ==================== URL DISCOVERY STAGE ====================
    # Results from URLDiscoveryAgent (Claude 4.5 Haiku web search)
    discovered_urls: List[Dict[str, Any]]  # All matching URLs across retailers
    # Format: [{"url": "...", "product_type": "individual/combo", "variant": "..."}]

    total_urls_found: int

    # ==================== PRICE SCRAPING STAGE ====================
    # Results from PriceScrapingAgent (Apify web scraping)
    enriched_urls: List[Dict[str, Any]]  # URLs enriched with price, name, image, availability
    # Format: [{"url": "...", "product_type": "...", "variant": "...",
    #           "name": "...", "price": "...", "currency": "...",
    #           "image": "...", "availability": "in_stock/out_of_stock/unavailable"}]

    # Price scraping statistics
    price_scraping_stats: Dict[str, Any]
    # Format: {"total_urls": 50, "scraped_successfully": 48, "failed": 2,
    #          "batches_processed": 5, "duration_seconds": 22.5,
    #          "in_stock": 45, "out_of_stock": 3, "unavailable": 2}

    # ==================== WORKFLOW METADATA ====================
    workflow_start_time: str
    workflow_end_time: Optional[str]
    total_duration_seconds: Optional[float]

    # Current stage in workflow
    current_stage: str  # "parsing", "product_confirmation", "variant_selection", "url_discovery", "price_scraping", "product_ranking", "complete"

    # Structured logs (accumulated across stages)
    logs: Annotated[List[Dict[str, Any]], operator.add]

    # Error tracking
    errors: Annotated[List[str], operator.add]

    # Completion flag
    completed_successfully: bool

    # ==================== USER INTERACTION FLAGS ====================
    # Flags to control workflow routing
    needs_product_confirmation: bool  # True if multiple product candidates found
    needs_variant_selection: bool  # True if variant not in query and multiple variants exist

    # ==================== API COST TRACKING ====================
    api_costs: Dict[str, float]  # {"gpt4o": 0.03, "claude": 0.12, "gemini": 0.0001, "total": 0.1501}
