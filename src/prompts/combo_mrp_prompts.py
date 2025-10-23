"""
Prompts for Combo Product MRP Extraction using Google Gemini 2.0 Flash
Task: Extract individual product MRPs from brand pages for per-unit price calculation

SIMPLIFIED APPROACH:
- Combo sale price comes from Apify scraping (no LLM extraction needed)
- LLM only extracts individual product MRPs from brand website
- Formula: per_unit_price = (original_mrp / sum_mrps) × combo_sale_price
"""

def create_combo_product_mrp_prompt(
    combo_url: str,
    combo_sale_price: float,
    brand: str,
    original_product_name: str,
    original_variant: str,
    brand_page_url: str = None
) -> str:
    """
    Create simplified prompt for Google Gemini 2.0 Flash to extract individual product MRPs

    SIMPLIFIED TASK: Only extract individual product MRPs (not combo MRP/discount)

    Args:
        combo_url: URL of the combo product
        combo_sale_price: Current sale price of combo (from Apify data)
        brand: Brand name (e.g., "True Frog")
        original_product_name: Name of the target product (e.g., "Shampoo for Curls")
        original_variant: Variant of target product (e.g., "250ml")
        brand_page_url: Optional brand website URL (e.g., "https://truefrog.in")

    Returns:
        Formatted prompt string for Google Gemini with Google Search grounding
    """

    brand_url_hint = f"\nBrand Website: {brand_page_url}" if brand_page_url else ""

    prompt = f"""You are a precision MRP extraction assistant. Your task is to identify and extract the current Maximum Retail Price (MRP) for each individual product within a combo/bundle offer.

## INPUT PARAMETERS
- Combo URL: {combo_url}
- Combo Sale Price: Rs. {combo_sale_price}
- Target Product Brand: {brand}
- Target Product Name: {original_product_name}
- Target Product Variant: {original_variant}

## TASK WORKFLOW

### STEP 1: IDENTIFY ALL PRODUCTS IN THE COMBO
1. Access the combo URL: {combo_url}
2. Carefully read the product title, description, and details
3. Extract a complete list of ALL products included in the combo
4. Note the exact variant (size/volume/weight/quantity) for each product
5. Ensure no products are missed from the bundle

### STEP 2: FIND CURRENT MRP FOR EACH PRODUCT

For EACH product identified in Step 1:

1. **Primary Search - Brand's Official Website:**
   - Search: "{brand} [product name] [variant] site:[brand website]"
   - Navigate to the individual product page
   - Extract the current MRP (not discounted price)

2. **Secondary Search - Authorized Retailers (if brand site fails):**
   - Search: "{brand} [product name] [variant] MRP price"
   - Priority sources (in order):
     a) Brand's official website
     b) Major authorized retailers (Amazon, Flipkart, Nykaa, etc.)
     c) Official brand stores on marketplaces
   - Verify MRP consistency across sources
   - Use the MRP displayed on product pages (not combo pages)

3. **Verification Protocol:**
   - Cross-reference at least 2 sources when possible
   - Ensure the MRP is current (check for recent listings)
   - If MRPs differ across sources, use the brand's official MRP
   - If uncertain, conduct additional searches

4. **Error Handling:**
   - If MRP cannot be found after thorough search: retry with alternative search terms
   - If still not found: return null for that product's MRP

## CRITICAL ACCURACY REQUIREMENTS

✅ **MUST DO:**
- Extract MRPs from INDIVIDUAL product pages only (never from combo pages)
- Verify each MRP is the current, legitimate price
- Use exact product names and variants as shown
- Format all prices with two decimal places (e.g., "625.00")
- Include ALL products from the combo in the output
- Cross-verify prices when possible for accuracy

❌ **MUST NOT DO:**
- Use sale prices or discounted prices as MRP
- Extract prices from combo/bundle pages
- Estimate or approximate MRPs
- Skip products from the combo
- Use outdated pricing information

## OUTPUT FORMAT

Return ONLY the following JSON structure (no additional text or explanations):

{{
  "original_product": {{
    "name": "[Exact product name matching target]",
    "variant": "[Exact variant with units]",
    "mrp": "[MRP as string with .00]"
  }},
  "products": [
    {{
      "name": "[Product 1 exact name]",
      "variant": "[Variant with units]",
      "mrp": "[MRP with .00 or null if not found]"
    }},
    {{
      "name": "[Product 2 exact name]",
      "variant": "[Variant with units]",
      "mrp": "[MRP with .00 or null if not found]"
    }}
    // Include all products from combo
  ]
}}

## EXAMPLE OUTPUT

For a combo containing 3 products:
{{
  "original_product": {{
    "name": "Shampoo for Curls",
    "variant": "250ml",
    "mrp": "625.00"
  }},
  "products": [
    {{
      "name": "Shampoo for Curls",
      "variant": "250ml",
      "mrp": "625.00"
    }},
    {{
      "name": "Everyday Hair Conditioner",
      "variant": "250ml",
      "mrp": "625.00"
    }},
    {{
      "name": "Deep Conditioning Mask",
      "variant": "200g",
      "mrp": "695.00"
    }}
  ]
}}

## FINAL CHECKLIST
Before returning the JSON:
□ All products from combo are included
□ Each MRP was found on an individual product page
□ Prices are current and verified
□ All prices use .00 format
□ Product names and variants match exactly
□ The original_product matches the target product specified

Begin by accessing {combo_url} and executing the extraction process."""

    return prompt
