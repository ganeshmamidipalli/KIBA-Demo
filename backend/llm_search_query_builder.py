# llm_search_query_builder.py
"""
LLM-Based Search Query Builder
Uses GPT-4o with a strict system prompt to generate comprehensive procurement search queries
"""

import os
import json
from typing import Dict, Any, Optional
from openai import OpenAI

MODEL = os.getenv("OPENAI_MODEL_QUERY", "gpt-4o-mini")  # Cheaper model for cost efficiency

SYSTEM_PROMPT = """
You are the Knowmadics Corporate Procurement AI Assistant (Natural-Language Query Builder).

MISSION
From the user's JSON input (selected recommendation + delivery info), output ONE clean, single-paragraph instruction that a web-search agent can execute directly. It MUST begin with: "I want to buy ..."

CRITICAL REQUIREMENT: If the JSON contains a "vendor_focus" field, you MUST include that exact text in your query. This is MANDATORY.

HARD RULES (ARD RULES) - MUST FOLLOW:
- No URLs/links in any output. Vendor names only.
- Keep responses skimmable (bullets, short sentences).
- Ask minimal questions; once enough is known, produce the decision pack.
- If stretch has weak benefit, switch to alternate.
- Honor Knowmadics policy context; flag exceptions explicitly.

INPUT
- The user message will contain a JSON object with any of the following keys:
  product_name, product_purpose, domain_terms, specs (dict), compliance (list),
  budget_per_unit_usd, quantity, results_count, delivery_city, delivery_state,
  delivery_window_days, usa_only (bool), notes (free text), vendor_focus (string).
- Treat unknown/missing fields as absent. Do NOT invent facts.
- The vendor_focus field contains specific vendor names to include in the query - USE THIS EXACTLY.

OUTPUT (STRICT)
- Exactly ONE paragraph. No bullets, no headers, no pre/post text, no code fences, no quotes.
- First sentence MUST start with "I want to buy ...".
- Include ONLY concrete constraints present in the JSON, plus the mandatory USA constraints below.
- Use concise purchasing language, not explanations.

CONTENT RULES
1) Product & purpose
   - Name the product clearly; include product_purpose and any domain_terms to disambiguate use cases.
2) Key specs
   - From specs, include materially decisive numeric/standard attributes (e.g., VRAM GB, bandwidth GB/s, CUDA cores, PCIe generation/lanes, watts/TDP, form factor, rack units, interface, memory type/speed, storage capacity, OS/driver requirements).
   - Normalize units (GB, TB, GB/s, W, PCIe x16 Gen4, 1U, etc.). Do not add specs that are not in the JSON.
3) Commercial constraints
   - If results_count present, request that many; else default to 10.
   - If budget_per_unit_usd present, include it as a per-unit budget cap.
   - If quantity present, include exact quantity to purchase.
4) Delivery
   - If delivery_city/state present, include both.
   - If delivery_window_days present, require "in stock" OR a clear lead time ≤ that window.
5) USA-only & intent (ALWAYS include)
   - "Show USA-based authorized vendors only that ship from the USA."
   - "Include valid HTTPS purchase links" and "USD pricing."
6) Availability
   - Require "In stock" or a stated lead time; reject vague availability.
7) Vendor Focus (MANDATORY)
   - If vendor_focus field is present, you MUST include it in your query
   - Copy the vendor_focus text EXACTLY as provided
   - This field contains specific vendor names that MUST appear in the final query
8) Style
   - Single paragraph, declarative, procurement-oriented, no fluff, no placeholders, no hallucinated brands/models.

DEFAULTS
- results_count: 10 if missing (focus on quality over quantity).
- Omit any category (specs/compliance/budget/delivery) if not present in the JSON—do NOT infer.

EXAMPLES (FORMAT ONLY — DO NOT COPY VALUES)
I want to buy 8 NVIDIA H100 PCIe accelerators for LLM fine-tuning and hosting, each with 80 GB HBM, PCIe Gen5 x16, ≥2.0 TB/s memory bandwidth, and 350 W TDP; target budget is ≤ $28,000 per unit; deliver to Austin, TX within 14 days with in-stock units or confirmed lead time ≤ 14 days. Show USA-based authorized vendors only that ship from the USA. Focus on NVIDIA direct sales plus category-leading enterprise resellers/VARs including CDW, SHI, Insight, Connection, Zones, B&H, WWT. Include valid HTTPS purchase links, USD pricing, and availability status. Return up to 10 results.

I want to buy 4 1U rack servers for on-prem vector DB, each with dual AMD EPYC, 512 GB DDR5, 2× 3.84 TB NVMe, dual 25GbE, and TPM 2.0; deliver to Reston, VA within 21 days with in-stock or lead time ≤ 21 days. Show USA-based authorized vendors only that ship from the USA. Focus on manufacturer direct sales plus category-leading enterprise resellers/VARs including CDW, SHI, Insight, Connection, Zones, WWT. Include valid HTTPS purchase links, USD pricing, and availability status. Return up to 10 results.

I want to buy 100 CrowdStrike Falcon Complete licenses for comprehensive endpoint detection and response, with a target budget of ≤ $8.99 per unit; deliver to Reston, VA within 14 days with in-stock units or confirmed lead time ≤ 14 days. Show USA-based authorized vendors only that ship from the USA. Focus on Optiv, CDW, SHI, GuidePoint Security, Insight, Carahsoft (public sector), Softcat (USA only). Include valid HTTPS purchase links, USD pricing, and availability status. Return up to 10 results.
"""


def build_query_json(selection: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform the selection data into the JSON format expected by the LLM.
    
    Args:
        selection: Full selection dict from frontend
        
    Returns:
        Simplified JSON for LLM query builder
    """
    variant = selection.get("selected_variant", {})
    delivery = selection.get("delivery_location", {})
    
    # Extract product purpose from various possible fields
    product_purpose = (
        selection.get("product_purpose") or
        selection.get("product_description") or
        variant.get("summary", "")
    )
    
    # Extract domain terms
    domain_terms = selection.get("domain_terms", [])
    category = selection.get("product_category", "")
    if category and category not in domain_terms:
        domain_terms = [category] + domain_terms
    
    # Build compliance list from MUST constraints
    compliance = []
    for req in variant.get("must", []):
        if isinstance(req, dict):
            value = req.get("value", "")
            if value:
                compliance.append(value)
        elif isinstance(req, str):
            compliance.append(req)
    
    # Add should constraints as notes
    should_notes = []
    for req in variant.get("should", []):
        if isinstance(req, dict):
            key = req.get("key", "")
            value = req.get("value", "")
            if value:
                should_notes.append(f"Prefer {key}: {value}")
        elif isinstance(req, str):
            should_notes.append(f"Prefer {req}")
    
    # Enhanced vendor search information from KPA recommendations
    vendor_search_info = selection.get("vendor_search", {})
    if vendor_search_info:
        # Add vendor search specific information
        if vendor_search_info.get("model_name"):
            product_name = vendor_search_info.get("model_name")
        else:
            product_name = selection.get("product_name", "")
        
        # Add spec fragments as domain terms
        spec_fragments = vendor_search_info.get("spec_fragments", [])
        if spec_fragments:
            domain_terms.extend(spec_fragments)
        
        # Add region hint to delivery info
        region_hint = vendor_search_info.get("region_hint")
        if region_hint and not delivery.get("city"):
            # Parse region hint for city/state if possible
            if "USA" in region_hint or "United States" in region_hint:
                delivery["state"] = "USA"
            elif "," in region_hint:
                parts = region_hint.split(",")
                if len(parts) >= 2:
                    delivery["city"] = parts[0].strip()
                    delivery["state"] = parts[1].strip()
        
        # Add budget hint if available
        budget_hint = vendor_search_info.get("budget_hint_usd")
        if budget_hint and not variant.get("est_unit_price_usd"):
            variant["est_unit_price_usd"] = budget_hint
    else:
        product_name = selection.get("product_name", "")
    
    # Determine product category for vendor optimization
    product_category = determine_product_category(product_name, domain_terms)
    
    # Add vendor optimization notes based on product category
    vendor_notes = get_vendor_optimization_notes(product_category)
    if vendor_notes:
        should_notes.append(vendor_notes)
    
    # Add explicit vendor focus field for LLM
    vendor_focus = get_vendor_focus_instruction(product_category, product_name)
    
    query_json = {
        "product_name": product_name,
        "product_purpose": product_purpose,
        "domain_terms": domain_terms,
        "specs": variant.get("metrics", {}),
        "compliance": compliance,
        "budget_per_unit_usd": variant.get("est_unit_price_usd", 0),
        "quantity": variant.get("quantity", 1),
        "results_count": selection.get("results_limit", 10),  # Focus on quality over quantity
        "delivery_city": delivery.get("city", ""),
        "delivery_state": delivery.get("state", ""),
        "delivery_window_days": selection.get("delivery_window_days", 30),
        "usa_only": True,  # Always true
        "notes": " ".join(should_notes) if should_notes else "",
        "product_category": product_category,  # For vendor optimization
        "vendor_focus": vendor_focus  # Explicit vendor focus instruction
    }
    
    # Remove empty values
    return {k: v for k, v in query_json.items() if v}


def determine_product_category(product_name: str, domain_terms: list) -> str:
    """
    Determine product category for vendor optimization.
    
    Args:
        product_name: Name of the product
        domain_terms: List of domain-specific terms
        
    Returns:
        Product category string
    """
    product_lower = product_name.lower()
    terms_lower = [term.lower() for term in domain_terms]
    all_terms = [product_lower] + terms_lower
    
    # GPU/Graphics cards
    if any(term in " ".join(all_terms) for term in ["gpu", "graphics", "rtx", "gtx", "nvidia", "amd", "radeon", "cuda", "tensor"]):
        return "gpu"
    
    # Security software/SaaS
    if any(term in " ".join(all_terms) for term in ["security", "firewall", "antivirus", "endpoint", "siem", "soar", "xdr", "edr", "mdr", "saas"]):
        return "security_saas"
    
    # Servers/Hardware
    if any(term in " ".join(all_terms) for term in ["server", "rack", "1u", "2u", "blade", "chassis", "cpu", "epyc", "xeon", "intel", "amd"]):
        return "hardware"
    
    # Storage
    if any(term in " ".join(all_terms) for term in ["storage", "nas", "san", "ssd", "nvme", "raid", "disk", "drive"]):
        return "storage"
    
    # Networking
    if any(term in " ".join(all_terms) for term in ["switch", "router", "firewall", "network", "ethernet", "wifi", "wireless", "cable"]):
        return "networking"
    
    # Default to hardware
    return "hardware"


def get_vendor_optimization_notes(product_category: str) -> str:
    """
    Get vendor optimization notes based on product category.
    
    Args:
        product_category: Category of the product
        
    Returns:
        Vendor optimization notes string
    """
    vendor_mapping = {
        "gpu": "Focus on manufacturer direct sales plus category-leading enterprise resellers/VARs including CDW, SHI, Insight, Connection, Zones, B&H, WWT",
        "security_saas": "Focus on Optiv, CDW, SHI, GuidePoint Security, Insight, Carahsoft (public sector), Softcat (USA only)",
        "hardware": "Focus on manufacturer direct sales plus category-leading enterprise resellers/VARs including CDW, SHI, Insight, Connection, Zones, WWT",
        "storage": "Focus on manufacturer direct sales plus category-leading enterprise resellers/VARs including CDW, SHI, Insight, Connection, Zones, WWT",
        "networking": "Focus on manufacturer direct sales plus category-leading enterprise resellers/VARs including CDW, SHI, Insight, Connection, Zones, WWT"
    }
    
    return vendor_mapping.get(product_category, "Focus on manufacturer direct sales plus category-leading enterprise resellers/VARs including CDW, SHI, Insight, Connection, Zones, WWT")


def get_vendor_focus_instruction(product_category: str, product_name: str) -> str:
    """
    Get explicit vendor focus instruction for the LLM.
    
    Args:
        product_category: Category of the product
        product_name: Name of the product
        
    Returns:
        Vendor focus instruction string
    """
    # Extract manufacturer name from product name
    manufacturer = ""
    if "nvidia" in product_name.lower():
        manufacturer = "NVIDIA"
    elif "dell" in product_name.lower():
        manufacturer = "Dell"
    elif "hp" in product_name.lower():
        manufacturer = "HP"
    elif "cisco" in product_name.lower():
        manufacturer = "Cisco"
    elif "crowdstrike" in product_name.lower():
        manufacturer = "CrowdStrike"
    elif "microsoft" in product_name.lower():
        manufacturer = "Microsoft"
    
    if product_category == "gpu":
        if manufacturer:
            return f"Focus on {manufacturer} direct sales plus category-leading enterprise resellers/VARs including CDW, SHI, Insight, Connection, Zones, B&H, WWT"
        else:
            return "Focus on manufacturer direct sales plus category-leading enterprise resellers/VARs including CDW, SHI, Insight, Connection, Zones, B&H, WWT"
    elif product_category == "security_saas":
        return "Focus on Optiv, CDW, SHI, GuidePoint Security, Insight, Carahsoft (public sector), Softcat (USA only)"
    else:
        if manufacturer:
            return f"Focus on {manufacturer} direct sales plus category-leading enterprise resellers/VARs including CDW, SHI, Insight, Connection, Zones, WWT"
        else:
            return "Focus on manufacturer direct sales plus category-leading enterprise resellers/VARs including CDW, SHI, Insight, Connection, Zones, WWT"


def generate_search_query_with_llm(
    selection: Dict[str, Any],
    *,
    key: Optional[str] = None,
    model: str = MODEL
) -> str:
    """
    Generate comprehensive search query using LLM with strict system prompt.
    
    This produces intelligent, well-formatted queries that follow procurement best practices.
    
    Args:
        selection: Full selection dict from frontend with variant, delivery, etc.
        key: OpenAI API key (optional, uses env var if not provided)
        model: Model to use (default: gpt-4o-2024-08-06)
        
    Returns:
        Single-paragraph comprehensive search instruction
    """
    client = OpenAI(api_key=key or os.getenv("OPENAI_API_KEY"))
    
    # Transform selection into clean JSON for LLM
    query_json = build_query_json(selection)
    
    # Call LLM with strict system prompt
    try:
        resp = client.chat.completions.create(
            model=model,
            temperature=0,  # Deterministic
            max_tokens=800,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(query_json, ensure_ascii=False, indent=2)}
            ]
        )
        
        query = resp.choices[0].message.content or ""
        
        # Clean up any accidental formatting
        query = query.strip()
        if query.startswith('"') and query.endswith('"'):
            query = query[1:-1]
        if query.startswith('```') or query.endswith('```'):
            # Remove code fences if LLM added them
            query = query.replace('```', '').strip()
        
        return query
        
    except Exception as e:
        # Fallback to simple query if LLM fails
        product = query_json.get("product_name", "product")
        specs = query_json.get("specs", {})
        spec_str = " ".join(str(v) for v in list(specs.values())[:5])
        return f"I want to buy {product} {spec_str}. Show USA-based authorized vendors only that ship from the USA. Include valid HTTPS purchase links and USD pricing."


# Backwards compatibility wrapper
def generate_natural_search_instruction(
    selection: Dict[str, Any],
    *,
    key: Optional[str] = None,
    model: str = MODEL
) -> str:
    """
    Wrapper for backwards compatibility.
    Calls the new LLM-based query builder.
    """
    return generate_search_query_with_llm(selection, key=key, model=model)

