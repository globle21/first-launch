"""
ComboPricingAgent - Calculates per-unit prices for combo products (SIMPLIFIED)
Two-stage process: Extract individual product MRPs → Calculate per-unit price

SIMPLIFIED APPROACH:
- Combo sale price comes from Apify scraping (no LLM extraction needed)
- LLM only extracts individual product MRPs from brand pages
- Formula: per_unit_price = (original_mrp / sum_mrps) × combo_sale_price
"""

from typing import Dict, Optional
try:
    from ..tools.combo_mrp_extractor import ComboProductMRPExtractor
except ImportError:
    from tools.combo_mrp_extractor import ComboProductMRPExtractor


class ComboPricingAgent:
    """
    Agent responsible for calculating per-unit prices of combo products (SIMPLIFIED)

    Workflow:
    1. Stage 1: Extract individual product MRPs from brand pages (Gemini 2.0 Flash + Google Search)
    2. Stage 2: Calculate per-unit price using simplified formula

    Simplified Formula:
    per_unit_price = (Original_Product_MRP / Sum_of_All_Product_MRPs) × Combo_Sale_Price
    """

    def __init__(self, google_api_key: Optional[str] = None, debug: bool = False):
        """
        Initialize combo pricing agent

        Args:
            google_api_key: Google API key (optional, reads from env if None)
            debug: Enable debug logging to see raw Gemini responses
        """
        self.mrp_extractor = ComboProductMRPExtractor(api_key=google_api_key, debug=debug)
        self.name = "ComboPricingAgent"
        self.debug = debug

    def calculate_combo_pricing(
        self,
        combo_url: str,
        combo_sale_price: float,
        brand: str,
        original_product_name: str,
        original_variant: str,
        brand_page_url: str = None
    ) -> Optional[Dict]:
        """
        Calculate per-unit price for original product in combo (SIMPLIFIED)

        Args:
            combo_url: URL of the combo product
            combo_sale_price: Current sale price of combo (from Apify data)
            brand: Brand name
            original_product_name: Name of the target product
            original_variant: Variant of target product
            brand_page_url: Optional brand website URL

        Returns:
            Dictionary with per-unit price and combo breakdown:
            {
                "per_unit_price": str,
                "combo_breakdown": {
                    "original_product_mrp": str,
                    "sum_of_mrps": str,
                    "products": [...]
                }
            }
            or None if calculation fails
        """
        print(f"\n{'='*70}")
        print(f"🤖 {self.name}: Calculating Per-Unit Price (SIMPLIFIED)")
        print(f"{'='*70}")

        # Stage 1: Extract individual product MRPs from brand pages
        print(f"\n📍 STAGE 1: Extracting individual product MRPs...")
        mrp_data = self.mrp_extractor.extract_product_mrps(
            combo_url=combo_url,
            combo_sale_price=combo_sale_price,
            brand=brand,
            original_product_name=original_product_name,
            original_variant=original_variant,
            brand_page_url=brand_page_url
        )

        if not mrp_data:
            print(f"❌ Failed to extract product MRPs")
            return None

        # Stage 2: Calculate per-unit price
        print(f"\n📍 STAGE 2: Calculating per-unit price...")
        try:
            result = self._calculate_price(mrp_data)
            self._display_result(result)
            return result

        except Exception as e:
            print(f"❌ Calculation failed: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return None

    def _calculate_price(self, mrp_data: Dict) -> Dict:
        """
        Calculate per-unit price using simplified formula

        Simplified Formula:
        per_unit_price = (Original_Product_MRP / Sum_of_All_Product_MRPs) × Combo_Sale_Price

        Args:
            mrp_data: MRP data from extraction stage
                {
                    "combo_url": str,
                    "combo_sale_price": float,
                    "original_product": {"name": str, "variant": str, "mrp": float},
                    "products": [{"name": str, "variant": str, "mrp": float}, ...],
                    "sum_of_mrps": float
                }

        Returns:
            Dictionary with calculation results (Option B format):
            {
                "per_unit_price": str,
                "combo_breakdown": {
                    "original_product_mrp": str,
                    "sum_of_mrps": str,
                    "products": [...]
                }
            }
        """
        # Extract values
        original_mrp = float(mrp_data["original_product"]["mrp"])
        sum_of_mrps = float(mrp_data["sum_of_mrps"])
        combo_sale_price = float(mrp_data["combo_sale_price"])

        # Apply simplified formula
        mrp_ratio = original_mrp / sum_of_mrps
        per_unit_price = mrp_ratio * combo_sale_price

        # Round to 2 decimal places
        per_unit_price = round(per_unit_price, 2)

        return {
            "per_unit_price": f"{per_unit_price:.2f}",
            "combo_breakdown": {
                "original_product_mrp": f"{original_mrp:.2f}",
                "sum_of_mrps": f"{sum_of_mrps:.2f}",
                "products": [
                    {
                        "name": product["name"],
                        "variant": product["variant"],
                        "mrp": f"{product['mrp']:.2f}"
                    }
                    for product in mrp_data["products"]
                ]
            },
            "calculation_details": {
                "combo_sale_price": combo_sale_price,
                "mrp_ratio": round(mrp_ratio, 4),
                "formula": f"({original_mrp:.2f} / {sum_of_mrps:.2f}) × {combo_sale_price:.2f} = {per_unit_price:.2f}"
            }
        }

    def _display_result(self, result: Dict):
        """
        Display calculation result

        Args:
            result: Calculation result dictionary
        """
        print(f"\n{'='*70}")
        print(f"✅ PER-UNIT PRICE CALCULATED")
        print(f"{'='*70}")
        print(f"\n💰 Per-Unit Price: ₹{result['per_unit_price']}")

        breakdown = result["combo_breakdown"]
        details = result["calculation_details"]

        print(f"\n📊 Calculation:")
        print(f"   Formula: {details['formula']}")
        print(f"   MRP Ratio: {details['mrp_ratio']}")

        print(f"\n📦 Combo Breakdown:")
        print(f"   Original Product MRP: ₹{breakdown['original_product_mrp']}")
        print(f"   Sum of All MRPs: ₹{breakdown['sum_of_mrps']}")
        print(f"   Products in Combo: {len(breakdown['products'])}")

        print(f"\n{'='*70}\n")
