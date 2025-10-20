# nl_search_instruction_service.py
# Build ONE natural-language search instruction from a selected recommendation.
# This runs automatically in the backend - user never sees it!
# The query includes constant constraints (USA vendors, HTTPS, in-stock, delivery) + variable product specs

from __future__ import annotations
import os, json
from typing import Dict, Any, Optional
from openai import OpenAI

MODEL = os.getenv("OPENAI_MODEL_QUERY", "gpt-4o-2024-08-06")

def generate_natural_search_instruction(
    selection: Dict[str, Any],
    *,
    key: Optional[str] = None,
    model: str = MODEL
) -> str:
    """
    Build a VERY DETAILED, COMPREHENSIVE natural language search instruction automatically.
    
    Creates long, thorough queries for best search results.
    
    The instruction ALWAYS includes these MANDATORY CONSTANT constraints:
    - USA-based authorized vendors only that ship from the USA
    - Valid HTTPS purchase links with direct purchase capability
    - USD pricing (no foreign currency)
    - In stock OR firm lead time ≤ delivery_window_days
    - Delivery to specific city, state within delivery window
    - Budget per unit and total quantity
    - Results count (default 20)
    
    PLUS the COMPLETE VARIABLE part from selected recommendation:
    - Full product purpose and domain context (what it's used for)
    - ALL numeric/standard specs from metrics (every single one)
    - ALL compliance/non-negotiables (NDAA, TAA, etc.)
    - ALL strong preferences (should-have features)
    - Nice-to-have features for bonus consideration
    
    Returns: Very detailed natural language instruction string (500-1000 words typical)
    """
    
    # Extract ALL data from selection
    product_name = selection.get("product_name", "product")
    product_category = selection.get("product_category", "")
    product_purpose = selection.get("product_purpose", "")  # Why they need it
    
    variant = selection.get("selected_variant", {})
    variant_summary = variant.get("summary", "")
    metrics = variant.get("metrics", {})
    must_constraints = variant.get("must", [])
    should_constraints = variant.get("should", [])
    nice_constraints = variant.get("nice", [])
    quantity = variant.get("quantity", 1)
    budget_per_unit = variant.get("est_unit_price_usd", selection.get("budget_total_usd", 0))
    
    # Delivery information (from product details in app)
    delivery_window = selection.get("delivery_window_days", 30)
    delivery_loc = selection.get("delivery_location", {})
    city = delivery_loc.get("city", "Wichita")  # Default to Wichita, KS
    state = delivery_loc.get("state", "KS")
    
    # Results limit
    results_limit = selection.get("results_limit", 20)
    
    # Build very detailed, comprehensive instruction
    parts = []
    
    # 1. Start with detailed purchase intent and purpose
    intro = f"I want to buy {product_name}"
    
    # Add product purpose/domain context if available
    if product_purpose:
        intro += f" for {product_purpose}"
    elif variant_summary:
        intro += f" ({variant_summary})"
    
    # Add category context if available
    if product_category:
        intro += f" in the {product_category} category"
    
    parts.append(intro + ".")
    
    # 2. Add detailed product description and use case
    if variant_summary and not product_purpose:
        parts.append(f"Product description: {variant_summary}.")
    
    # 3. Add COMPLETE specifications section with ALL metrics
    if metrics:
        parts.append("Technical specifications required:")
        
        spec_details = []
        for key, value in metrics.items():
            if value and str(value).lower() not in ["", "none", "n/a", "null"]:
                # Format clearly with units
                if isinstance(value, (int, float)):
                    spec_details.append(f"{key} must be {value}")
                else:
                    spec_details.append(f"{key} should be {value}")
        
        if spec_details:
            parts.append("; ".join(spec_details) + ".")
    
    # 4. Add CRITICAL MANDATORY requirements (MUST constraints)
    if must_constraints:
        parts.append("CRITICAL MANDATORY REQUIREMENTS (non-negotiable):")
        
        must_details = []
        for constraint in must_constraints:
            if isinstance(constraint, dict):
                key_val = constraint.get("key", "")
                value_val = constraint.get("value", "")
                if value_val:
                    must_details.append(f"The product MUST {value_val}")
                elif key_val:
                    must_details.append(f"Must meet {key_val} requirement")
            elif isinstance(constraint, str) and constraint:
                must_details.append(f"Must have {constraint}")
        
        if must_details:
            parts.append(" ".join(must_details) + ".")
    
    # 5. Add STRONG PREFERENCES (should-have features)
    if should_constraints:
        parts.append("STRONG PREFERENCES (highly desired features):")
        
        should_details = []
        for constraint in should_constraints:
            if isinstance(constraint, dict):
                key_val = constraint.get("key", "")
                value_val = constraint.get("value", "")
                if value_val:
                    should_details.append(f"Strongly prefer {key_val}: {value_val}")
                elif key_val:
                    should_details.append(f"Prefer {key_val}")
            elif isinstance(constraint, str) and constraint:
                should_details.append(f"Prefer {constraint}")
        
        if should_details:
            parts.append("; ".join(should_details) + ".")
    
    # 6. Add NICE-TO-HAVE features (bonus considerations)
    if nice_constraints:
        nice_parts = []
        for constraint in nice_constraints:
            if isinstance(constraint, dict):
                key_val = constraint.get("key", "")
                value_val = constraint.get("value", "")
                if value_val:
                    nice_parts.append(f"{key_val}: {value_val}")
                elif key_val:
                    nice_parts.append(key_val)
            elif isinstance(constraint, str) and constraint:
                nice_parts.append(constraint)
        
        if nice_parts:
            parts.append(f"BONUS FEATURES (nice to have, not required): {', '.join(nice_parts)}.")
    
    # 7. MANDATORY VENDOR CONSTRAINTS (always enforced)
    parts.append("\nVENDOR REQUIREMENTS (strictly enforced):")
    parts.append("I need vendors that meet ALL of the following criteria:")
    
    vendor_requirements = []
    vendor_requirements.append("1) USA-based authorized vendors ONLY - no international sellers")
    vendor_requirements.append("2) Must ship products from USA warehouses/facilities (not dropship from overseas)")
    vendor_requirements.append("3) Must be authorized distributors or manufacturers (no gray market)")
    vendor_requirements.append("4) Must provide valid, working HTTPS purchase links (no HTTP or broken links)")
    vendor_requirements.append("5) Must accept USD pricing (no foreign currency conversions required)")
    vendor_requirements.append(f"6) Product must be IN STOCK with immediate availability OR firm lead time ≤ {delivery_window} days (no estimates or 'call for availability')")
    vendor_requirements.append(f"7) Must be able to deliver to {city}, {state} within {delivery_window} days from order")
    vendor_requirements.append("8) Must have clear contact information (phone, email, or chat support)")
    vendor_requirements.append("9) Must display pricing publicly or provide instant quote capability")
    vendor_requirements.append("10) Prefer vendors with government/enterprise purchasing programs")
    
    parts.append(" ".join(vendor_requirements))
    
    # 8. Quantity and budget constraints
    parts.append(f"\nQUANTITY & BUDGET: I need to purchase {quantity} unit(s).")
    if budget_per_unit > 0:
        parts.append(f"Budget per unit: ${budget_per_unit:,.2f} USD.")
        total_budget = budget_per_unit * quantity
        parts.append(f"Total budget: ${total_budget:,.2f} USD.")
    
    # 9. Delivery specifics
    parts.append(f"\nDELIVERY REQUIREMENTS:")
    parts.append(f"Ship to: {city}, {state}.")
    parts.append(f"Required delivery window: {delivery_window} days or less from order placement.")
    parts.append("Shipping method: Vendor's choice (ground, air, freight) as long as delivery window is met.")
    parts.append("Include shipping costs in pricing if possible, or note them separately.")
    
    # 10. Output format instructions
    parts.append(f"\nOUTPUT FORMAT: Return exactly {results_limit} vendor options, ranked by best overall match.")
    parts.append("For each vendor, include:")
    parts.append("- Vendor name and location")
    parts.append("- Direct HTTPS purchase link")
    parts.append("- Exact unit price in USD")
    parts.append("- Total price for requested quantity")
    parts.append("- Current stock status or specific lead time")
    parts.append("- Shipping time to delivery location")
    parts.append("- Contact method (phone/email/chat)")
    parts.append("- Any relevant compliance certifications")
    
    # 11. Search quality instructions
    parts.append("\nSEARCH QUALITY: Prioritize vendors with:")
    parts.append("- Exact spec matches over partial matches")
    parts.append("- In-stock availability over backorder")
    parts.append("- Faster delivery times")
    parts.append("- Better pricing (closer to budget)")
    parts.append("- Established reputation (enterprise/government sales)")
    parts.append("- Complete product information and documentation")
    
    # Join all parts into one natural paragraph
    instruction = " ".join(parts)
    
    # Clean up spacing around punctuation
    instruction = instruction.replace(" .", ".").replace(" ,", ",")
    instruction = instruction.replace("  ", " ")
    
    return instruction.strip()


def generate_short_query(selection: Dict[str, Any]) -> str:
    """
    Generate a short keyword query (for logging/display purposes).
    This is optional - just for debugging/logs.
    """
    product_name = selection.get("product_name", "")
    variant = selection.get("selected_variant", {})
    metrics = variant.get("metrics", {})
    
    # Take first 3-4 key metrics
    keywords = [product_name]
    for key, value in list(metrics.items())[:4]:
        if isinstance(value, (int, float)):
            keywords.append(f"{value}{key[:4]}")
        else:
            keywords.append(str(value))
    
    return " ".join(keywords)[:100]

