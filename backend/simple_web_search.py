#!/usr/bin/env python3
"""
Simple Web Search Module
Strict web_search via OpenAI Responses API with JSON Schema output
"""

import os
import json
import re
from typing import List, Dict, Any
from openai import OpenAI

SYSTEM_PROMPT = (
    "ROLE: Senior Procurement Sourcer.\n"
    "TASK: Given a procurement query and categories, return ONLY strict JSON per schema.\n"
    "Rules:\n"
    "1) Official product/vendor links only (no forums, no random blogs).\n"
    "2) All vendors must ship from within the USA.\n"
    "3) Prefer US manufacturers and reputable US marketplaces (CDW, B&H, Newegg, Micro Center, Best Buy, Dell, HP, Lenovo, etc.).\n"
    "4) Include price if available on-page; otherwise set availability='unknown'.\n"
    "5) Evidence URLs must be to the exact product or policy pages supporting the data.\n"
)

# Minimal multicategory schema (single category used by our flow)
MULTICATEGORY_SCHEMA: Dict[str, Any] = {
    "name": "MultiCategorySchema",
    "schema": {
        "type": "object",
        "properties": {
            "categories": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "budget_usd": {"type": "number"},
                        "vendors": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "vendor_name": {"type": "string"},
                                    "product_name": {"type": "string"},
                                    "model": {"type": "string"},
                                    "sku": {"type": ["string", "null"]},
                                    "price": {"type": ["number", "null"]},
                                    "currency": {"type": "string"},
                                    "availability": {"type": "string"},
                                    "ships_to": {"type": "array", "items": {"type": "string"}},
                                    "delivery_window_days": {"type": ["integer", "null"]},
                                    "purchase_url": {"type": "string"},
                                    "evidence_urls": {"type": "array", "items": {"type": "string"}},
                                    "sales_email": {"type": ["string", "null"]},
                                    "sales_phone": {"type": ["string", "null"]},
                                    "return_policy_url": {"type": ["string", "null"]},
                                    "notes": {"type": ["string", "null"]},
                                    "us_vendor_verification": {
                                        "type": "object",
                                        "properties": {
                                            "is_us_vendor": {"type": "boolean"},
                                            "method": {"type": "string"},
                                            "business_address": {"type": "string"}
                                        },
                                        "required": ["is_us_vendor", "method"]
                                    },
                                    "last_checked_utc": {"type": "string"}
                                },
                                "required": [
                                    "vendor_name","product_name","model","price","currency",
                                    "availability","ships_to","delivery_window_days","purchase_url",
                                    "evidence_urls","us_vendor_verification","last_checked_utc"
                                ]
                            }
                        }
                    },
                    "required": ["name", "budget_usd", "vendors"]
                }
            }
        },
        "required": ["categories"]
    }
}

_CACHE: Dict[str, List[Dict[str, Any]]] = {}

def _cache_key(product_name: str, specs: List[str], max_results: int) -> str:
    return json.dumps({"p": product_name, "s": specs, "n": max_results}, sort_keys=True)

def _build_input_text(product_name: str, specs: List[str], max_results: int) -> str:
    spec_text = ", ".join(specs) if specs else ""
    # Style requested by user: precise, official links, US-only, exact vendor count
    return (
        "multi-category procurement for a US company; official links only; all vendors must ship from within the USA. "
        f"Categories: [{{\"name\":\"{product_name}\",\"budget_usd\":0}}]. "
        f"Goal: \"i want the best {product_name} based on these specifications ({spec_text}) with links with ~{max_results} vendors.\""
    )

def search_vendors_for_product(product_name: str, specs: List[str], budget: float, max_results: int = 10, refresh: bool = False) -> List[Dict[str, Any]]:
    """Search for vendors using OpenAI web_search with strict JSON schema output.

    Caching: results are cached per (product_name, specs, max_results). If refresh is False and
    a cached result exists, the cached result is returned without calling web_search again.
    """
    try:
        # Cache short-circuit unless refresh requested
        key = _cache_key(product_name, specs, max_results)
        if not refresh and key in _CACHE:
            return _CACHE[key]

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ OPENAI_API_KEY not set")
            return []

        client = OpenAI(api_key=api_key)

        input_text = _build_input_text(product_name, specs, max_results)

        resp = client.responses.create(
            model="o4-mini",
            reasoning={"effort": "medium"},
            instructions=SYSTEM_PROMPT,
            tools=[{"type": "web_search"}],
            tool_choice={"type": "web_search"},
            response_format={
                "type": "json_schema",
                "json_schema": MULTICATEGORY_SCHEMA
            },
            input=input_text,
            max_output_tokens=2000
        )

        raw = resp.output_text
        data = json.loads(raw)
        categories = data.get("categories", [])
        vendors_out: List[Dict[str, Any]] = []
        if categories:
            # Use the first category (we send only one)
            for v in categories[0].get("vendors", [])[:max_results]:
                # Map to our expected structure for the frontend/server
                vendors_out.append({
                    "vendor_name": v.get("vendor_name", "Unknown Vendor"),
                    "product_name": v.get("product_name", product_name),
                    "model": v.get("model", product_name),
                    "sku": v.get("sku") or None,
                    "price": float(v.get("price") or 0),
                    "currency": v.get("currency", "USD"),
                    "availability": v.get("availability", "unknown"),
                    "ships_to": v.get("ships_to", ["USA"]),
                    "delivery_window_days": int(v.get("delivery_window_days") or 30),
                    "purchase_url": v.get("purchase_url", ""),
                    "evidence_urls": v.get("evidence_urls", []),
                    "sales_email": v.get("sales_email"),
                    "sales_phone": v.get("sales_phone"),
                    "return_policy_url": v.get("return_policy_url"),
                    "notes": v.get("notes", "Found via web search"),
                    "us_vendor_verification": {
                        "is_us_vendor": bool(v.get("us_vendor_verification", {}).get("is_us_vendor", True)),
                        "method": v.get("us_vendor_verification", {}).get("method", "web_search"),
                        "business_address": v.get("us_vendor_verification", {}).get("business_address", "United States")
                    },
                    "last_checked_utc": v.get("last_checked_utc") or "2025-01-01T00:00:00Z"
                })

        print(f"✅ Found {len(vendors_out)} vendors via strict web_search")
        vendors_out = vendors_out[:max_results]
        _CACHE[key] = vendors_out
        return vendors_out

    except Exception as e:
        print(f"❌ Web search error: {e}")
        return []

def parse_vendor_response(response_text: str, product_name: str, budget: float) -> List[Dict[str, Any]]:
    """Deprecated: kept for backward compatibility (not used with strict schema)."""
    try:
        data = json.loads(response_text)
        cats = data.get("categories", [])
        if not cats:
            return []
        return cats[0].get("vendors", [])
    except Exception:
        return []

def extract_vendor_info(line: str, product_name: str, budget: float) -> Dict[str, Any]:
    """Deprecated: no longer used with strict schema mode."""
    return {}

def get_fallback_vendors(product_name: str, budget: float, count: int) -> List[Dict[str, Any]]:
    """Deprecated fallback. Returns empty to avoid non-official links."""
    return []
