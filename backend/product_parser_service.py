# product_parser_service.py
"""
Parse web search output text into structured product/vendor data for UI display
"""

import re
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
import os

def parse_vendors_with_llm(search_output: str, client: OpenAI) -> List[Dict[str, Any]]:
    """
    Use LLM to parse vendor search output into structured JSON.
    
    Args:
        search_output: Raw text output from web search
        client: OpenAI client
        
    Returns:
        List of structured vendor/product objects
    """
    
    parse_prompt = """
You are a data extraction assistant. Parse the vendor/product information from the search results into a JSON array.

For each vendor/product found, extract:
- vendor_name: Company/vendor name
- product_name: Specific product name/model
- location: Vendor location (city, state, or just state)
- price: Unit price in USD (as number, no $ symbol)
- total_price: Total price if mentioned (as number)
- lead_time_days: Lead time in days (as number, or null)
- in_stock: Boolean - true if in stock, false if backorder/pre-order
- purchase_link: HTTPS purchase URL
- contact: Contact method (email, phone, or URL)
- specs: Object with key technical specs mentioned
- compliance: Array of compliance items (NDAA, TAA, etc.)
- notes: Any additional relevant notes

Return ONLY a JSON array. If no vendors found, return empty array [].
Skip any entries that don't have at least vendor_name and product_name.

Example format:
[
  {
    "vendor_name": "CDW Government",
    "product_name": "NVIDIA A100 PCIe 40GB",
    "location": "Illinois",
    "price": 12500,
    "lead_time_days": 7,
    "in_stock": true,
    "purchase_link": "https://www.cdwg.com/...",
    "contact": "sales@cdwg.com",
    "specs": {"VRAM": "40GB", "Form Factor": "PCIe"},
    "compliance": ["NDAA compliant"],
    "notes": "Volume discounts available"
  }
]
"""
    
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=4000,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": parse_prompt},
                {"role": "user", "content": f"Parse this search output:\n\n{search_output[:8000]}"}  # Limit to 8k chars
            ]
        )
        
        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
        
        # Handle both {"products": [...]} and direct array
        if isinstance(data, dict):
            vendors = data.get("products", data.get("vendors", data.get("results", [])))
        else:
            vendors = data if isinstance(data, list) else []
        
        # Add IDs and validate
        validated = []
        for i, vendor in enumerate(vendors):
            if isinstance(vendor, dict) and vendor.get("vendor_name") and vendor.get("product_name"):
                vendor["id"] = f"vendor_{i+1}"
                vendor["score"] = 0.9 - (i * 0.05)  # Decreasing score for ranking
                validated.append(vendor)
        
        return validated[:20]  # Max 20 vendors
        
    except Exception as e:
        print(f"Error parsing vendors with LLM: {e}")
        return []


def parse_vendors_simple(search_output: str) -> List[Dict[str, Any]]:
    """
    Simple regex-based parsing as fallback.
    Looks for vendor names, prices, links in the text.
    """
    vendors = []
    
    # Try to find HTTPS links
    links = re.findall(r'https://[^\s<>"]+', search_output)
    
    # Try to find prices ($X,XXX or $XXX)
    prices = re.findall(r'\$[\d,]+(?:\.\d{2})?', search_output)
    
    # Simple heuristic: if we have links and prices, create vendor entries
    for i, link in enumerate(links[:10]):  # Max 10
        vendor = {
            "id": f"vendor_{i+1}",
            "vendor_name": f"Vendor {i+1}",
            "product_name": "Product (see link for details)",
            "location": "USA",
            "price": float(prices[i].replace('$', '').replace(',', '')) if i < len(prices) else None,
            "purchase_link": link,
            "in_stock": None,
            "score": 0.9 - (i * 0.05)
        }
        vendors.append(vendor)
    
    return vendors


def parse_search_results(
    search_output: str,
    client: Optional[OpenAI] = None
) -> List[Dict[str, Any]]:
    """
    Parse web search output into structured vendor/product data.
    
    Args:
        search_output: Raw text from web search
        client: Optional OpenAI client for LLM parsing
        
    Returns:
        List of structured vendor objects for UI display
    """
    if not search_output or len(search_output) < 50:
        return []
    
    # Try LLM parsing first (more accurate)
    if client:
        vendors = parse_vendors_with_llm(search_output, client)
        if vendors:
            return vendors
    
    # Fallback to simple regex parsing
    return parse_vendors_simple(search_output)

