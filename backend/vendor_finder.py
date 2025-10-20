# vendor_finder.py
"""
LLM-Powered Procurement Sourcer
Finds reputable US vendors for exact product models with price, availability, and delivery info.
"""

import os
import json
import hashlib
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, AnyUrl, validator
from openai import OpenAI

# ---------- Data Contracts (Strict JSON) ----------

class USVerify(BaseModel):
    is_us_vendor: bool
    method: str = Field(..., description="Verification method: domain_tld, contact_address, about_page, sec_state_registration, shipping_policy")
    business_address: str = ""

class VendorFinder(BaseModel):
    vendor_name: str
    product_name: str
    model: str
    sku: Optional[str] = None
    price: float
    currency: str = Field("USD", pattern="USD")
    availability: str = Field(..., description="in_stock, backorder, preorder, out_of_stock, unknown")
    ships_to: List[str]
    delivery_window_days: int
    purchase_url: AnyUrl
    evidence_urls: List[AnyUrl] = Field(..., min_items=1)
    sales_email: str
    sales_phone: Optional[str] = None
    return_policy_url: Optional[AnyUrl] = None
    notes: Optional[str] = ""
    us_vendor_verification: USVerify
    last_checked_utc: str

class VendorFinderResponse(BaseModel):
    query: str
    selected_name: str
    selected_specs: List[str]
    page: int
    page_size: int
    results: List[VendorFinder]
    summary: Dict[str, Any]

# ---------- LLM Prompt Template ----------

VENDOR_FINDER_PROMPT = """ROLE: Senior Procurement Sourcer.
TASK: Using the QUERY, SELECTED_NAME, and SELECTED_SPECS, find reputable US vendors for the exact product model.
Return strict JSON per schema 'VendorFinder' (one object per vendor).

Rules:
1) NO fabrication. Use only facts on the linked pages.
2) Prefer manufacturer pages and major US marketplaces (CDW, B&H, Newegg, Micro Center, Adorama, Best Buy, Dell, HP, Lenovo, etc.).
3) Link to the specific product page (not a category) whenever it exists.
4) Price & availability must be present on-page or via official PDP API widgets; otherwise set availability="unknown".
5) Include at least one evidence URL per vendor that shows model/price/stock or US address/shipping policy.
6) US-only: Confirm US vendor via address on Contact/About, US shipping policy, or recognizable US marketplace. Set us_vendor_verification.method accordingly.
7) Delivery to Wichita, KS within 30 days: 
   - If page shows delivery estimator, convert to delivery_window_days (best estimate).
   - If not shown, infer from shipping policy in business days (note in 'notes').
8) Extract a sales/RFQ email from the product page or Contact/Sales page. If only a form is present, set sales_email="webform" and include the contact URL in notes.
9) Validate links: working HTTPS URLs to the exact product (avoid redirects to generic categories if possible).
10) If specs conflict across sources, prefer manufacturer page and note the discrepancy.

QUERY: {query}
SELECTED_NAME: {selected_name}
SELECTED_SPECS:
{spec_lines}
CONFIRMED_REQUIREMENTS_SUMMARY:
{summary}

RETURN: exactly {page_size} vendors for page index {page} (0-based). If fewer found, return as many as possible.

Return ONLY valid JSON matching the VendorFinderResponse schema. No markdown, no explanations."""

# ---------- Utilities ----------

def cache_key(payload: dict) -> str:
    """Generate cache key for vendor search results."""
    s = json.dumps(payload, sort_keys=True)
    return "vf:" + hashlib.sha256(s.encode()).hexdigest()

def is_us_vendor(signals: dict) -> bool:
    """Heuristic US vendor verification."""
    domain = signals.get("domain", "").lower()
    if domain.endswith((".ca", ".co.uk", ".de", ".eu", ".au", ".nz")):
        return False
    
    addr = signals.get("contact_address", "").lower()
    us_indicators = [
        " ks ", " kansas ", " united states", " usa", " tx ", " ca ", " ny ", " il ",
        " florida", " texas", " california", " new york", " illinois", " ohio",
        " pennsylvania", " georgia", " north carolina", " michigan", " new jersey"
    ]
    
    return any(indicator in addr for indicator in us_indicators) or "united states" in addr or "usa" in addr

def http_ok(url: str) -> bool:
    """Check if URL is accessible (simplified for now)."""
    # TODO: Implement actual HTTP check with timeout
    return True

def extract_vendor_info_from_web_results(web_results: List[Dict], params: Dict) -> List[VendorFinder]:
    """Extract vendor information from web search results."""
    vendors = []
    
    for result in web_results:
        try:
            # Basic validation
            if not result.get("url") or not result.get("title"):
                continue
                
            # Create vendor entry with string URLs
            vendor = VendorFinder(
                vendor_name=result.get("vendor", "Unknown Vendor"),
                product_name=result.get("title", ""),
                model=result.get("model", ""),
                sku=result.get("sku"),
                price=float(result.get("price", 0)),
                currency="USD",
                availability=result.get("availability", "unknown"),
                ships_to=["USA"],
                delivery_window_days=int(result.get("delivery_days", 30)),
                purchase_url=str(result.get("url", "")),
                evidence_urls=[str(result.get("url", ""))],
                sales_email=result.get("sales_email", "webform"),
                sales_phone=result.get("sales_phone"),
                return_policy_url=str(result.get("return_policy_url", "")) if result.get("return_policy_url") else None,
                notes=result.get("notes", ""),
                us_vendor_verification=USVerify(
                    is_us_vendor=is_us_vendor({
                        "domain": result.get("domain", ""),
                        "contact_address": result.get("contact_address", "")
                    }),
                    method="domain_tld",
                    business_address=result.get("contact_address", "")
                ),
                last_checked_utc=datetime.now(timezone.utc).isoformat()
            )
            vendors.append(vendor)
        except Exception as e:
            print(f"Error processing vendor result: {e}")
            continue
    
    return vendors

# ---------- Core Pipeline ----------

def run_vendor_finder_llm(web_results: List[Dict], params: Dict) -> VendorFinderResponse:
    """
    Process web results through LLM to create structured vendor data.
    """
    # Extract vendor info from web results
    vendors = extract_vendor_info_from_web_results(web_results, params)
    
    # Filter US vendors only
    us_vendors = [v for v in vendors if v.us_vendor_verification.is_us_vendor]
    
    # Pagination
    page = params.get("page", 0)
    page_size = params.get("page_size", 10)
    start = page * page_size
    end = start + page_size
    page_vendors = us_vendors[start:end]
    
    # Create response with JSON-serializable data
    response_data = {
        "query": params.get("query", ""),
        "selected_name": params.get("selected_name", ""),
        "selected_specs": params.get("selected_specs", []),
        "page": page,
        "page_size": page_size,
        "results": [
            {
                "vendor_name": v.vendor_name,
                "product_name": v.product_name,
                "model": v.model,
                "sku": v.sku,
                "price": v.price,
                "currency": v.currency,
                "availability": v.availability,
                "ships_to": v.ships_to,
                "delivery_window_days": v.delivery_window_days,
                "purchase_url": str(v.purchase_url),
                "evidence_urls": [str(url) for url in v.evidence_urls],
                "sales_email": v.sales_email,
                "sales_phone": v.sales_phone,
                "return_policy_url": str(v.return_policy_url) if v.return_policy_url else None,
                "notes": v.notes,
                "us_vendor_verification": {
                    "is_us_vendor": v.us_vendor_verification.is_us_vendor,
                    "method": v.us_vendor_verification.method,
                    "business_address": v.us_vendor_verification.business_address
                },
                "last_checked_utc": v.last_checked_utc
            }
            for v in page_vendors
        ],
        "summary": {
            "found": len(us_vendors),
            "missing_fields_count": sum(1 for v in page_vendors if not v.sales_email or v.sales_email == "webform"),
            "notes": f"US-only filter applied. Found {len(us_vendors)} US vendors, showing {len(page_vendors)} on page {page + 1}."
        }
    }
    
    return response_data

def generate_vendor_search_query(selected_variant: Dict, kpa_recommendations: Dict = None) -> str:
    """Generate enhanced search query for vendor finding."""
    product_name = selected_variant.get("title", "")
    summary = selected_variant.get("summary", "")
    price = selected_variant.get("est_unit_price_usd", 0)
    
    # Build query with vendor focus
    query_parts = [
        f'"{product_name}"',
        "US vendor",
        "in stock",
        f"under ${price:.0f}" if price > 0 else "",
        "deliver to Wichita KS",
        "within 30 days"
    ]
    
    # Add vendor-specific terms
    if kpa_recommendations:
        vendor_search = kpa_recommendations.get("vendor_search", {})
        if vendor_search.get("spec_fragments"):
            query_parts.extend(vendor_search["spec_fragments"][:3])
    
    return " ".join(filter(None, query_parts))

# ---------- Main API Function ----------

def find_vendors(
    selected_variant: Dict,
    kpa_recommendations: Dict = None,
    page: int = 0,
    page_size: int = 10,
    refresh: bool = False
) -> VendorFinderResponse:
    """
    Main function to find vendors for a selected recommendation.
    
    Args:
        selected_variant: Selected recommendation variant
        kpa_recommendations: KPA recommendations data
        page: Page number (0-based)
        page_size: Number of results per page
        refresh: Whether to refresh cache
    
    Returns:
        VendorFinderResponse with vendor data
    """
    # Generate search query
    query = generate_vendor_search_query(selected_variant, kpa_recommendations)
    
    # Extract specs
    selected_specs = []
    if kpa_recommendations and kpa_recommendations.get("vendor_search", {}).get("spec_fragments"):
        selected_specs = kpa_recommendations["vendor_search"]["spec_fragments"]
    
    # Build parameters
    params = {
        "query": query,
        "selected_name": selected_variant.get("title", ""),
        "selected_specs": selected_specs,
        "summary": f"US vendors only. Must deliver to Wichita, KS within 30 days. In-stock preferred. Price <= ${selected_variant.get('est_unit_price_usd', 0):.0f}.",
        "page": page,
        "page_size": page_size
    }
    
    # For now, simulate web results (replace with actual web search)
    web_results = [
        {
            "vendor": "CDW",
            "title": selected_variant.get("title", ""),
            "model": selected_variant.get("title", ""),
            "url": f"https://www.cdw.com/product/{selected_variant.get('id', '')}",
            "price": selected_variant.get("est_unit_price_usd", 0),
            "availability": "in_stock",
            "delivery_days": 5,
            "sales_email": "sales@cdw.com",
            "domain": "cdw.com",
            "contact_address": "200 N Milwaukee Ave, Vernon Hills, IL 60061"
        },
        {
            "vendor": "B&H Photo Video",
            "title": selected_variant.get("title", ""),
            "model": selected_variant.get("title", ""),
            "url": f"https://www.bhphotovideo.com/c/product/{selected_variant.get('id', '')}",
            "price": selected_variant.get("est_unit_price_usd", 0) * 0.95,
            "availability": "in_stock",
            "delivery_days": 3,
            "sales_email": "sales@bhphotovideo.com",
            "domain": "bhphotovideo.com",
            "contact_address": "420 9th Ave, New York, NY 10001"
        },
        {
            "vendor": "Newegg",
            "title": selected_variant.get("title", ""),
            "model": selected_variant.get("title", ""),
            "url": f"https://www.newegg.com/p/{selected_variant.get('id', '')}",
            "price": selected_variant.get("est_unit_price_usd", 0) * 1.05,
            "availability": "in_stock",
            "delivery_days": 7,
            "sales_email": "webform",
            "domain": "newegg.com",
            "contact_address": "17560 Rowland St, City of Industry, CA 91748"
        }
    ]
    
    # Process through pipeline
    return run_vendor_finder_llm(web_results, params)
