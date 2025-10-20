# search_query_service.py
"""
Search Query Service - LLM-only query builder for Knowmadics Procurement
=========================================================================

Input: product_name, selected_variant (incl. metrics), delivery_location, delivery_window_days, budget
Output: {"solid_query": "...", "alternates": ["...", "..."], "display_subtitle": "..."}

Clean, minimal, uses responses.create with strict JSON schema.
"""

import os
import json
from typing import Dict, Any, Optional
from openai import OpenAI

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-2024-08-06")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STRICT JSON SCHEMA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

QUERY_SCHEMA = {
    "name": "query_pack",
    "strict": True,
    "schema": {
        "type": "object",
        "required": ["solid_query"],
        "properties": {
            "solid_query": {"type": "string", "maxLength": 200},
            "alternates": {"type": "array", "items": {"type": "string"}, "minItems": 0, "maxItems": 2},
            "display_subtitle": {"type": "string", "maxLength": 240}
        },
        "additionalProperties": False
    }
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SYSTEM PROMPT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SYSTEM_PROMPT = (
    "You are the Knowmadics Corporate Procurement AI Assistant (Query Builder).\n"
    "Goal: Produce ONE concise web search query (<= 22 words) that lands on buyable product pages.\n"
    "\n"
    "Use the user JSON (product_name, selected_variant with metrics, budget, delivery_window_days, delivery_location).\n"
    "Rules for solid_query:\n"
    "- Keep numeric/standard tokens from metrics (e.g., 8MP, IR 150m, IP67, IK10, 802.3at, ONVIF; 80GB HBM3; PCIe Gen5; 10GbE; PoE+).\n"
    "- Prefer domain terms buyers use (model/feature nouns), de-duplicate, natural order, <= 22 words.\n"
    "- Do NOT include location or timing words (city, state, delivery window); keep those out of the query text.\n"
    "- Do NOT inject constraint phrases (USA-only, valid links, in-stock) into the query text.\n"
    "- Avoid noisy tokens (review, reddit, youtube, forum, brochure, manual) unless explicitly present in user text.\n"
    "\n"
    "Also return:\n"
    "- alternates: up to two compact variations of the same query.\n"
    "- display_subtitle: short human line that mentions delivery window and city/state for UI context.\n"
    "\n"
    "Output STRICT JSON per schema only."
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN FUNCTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def generate_search_query(selection: Dict[str, Any], *, model: str = MODEL, key: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate search query from selected variant using LLM.
    
    Args:
        selection: Dictionary containing:
            - product_name: str
            - selected_variant: dict with id, quantity, metrics, must
            - budget_total_usd: float (optional)
            - delivery_window_days: int (optional)
            - delivery_location: dict with city, state (optional)
        model: OpenAI model to use
        key: OpenAI API key (optional, uses env var if not provided)
    
    Returns:
        Dictionary with:
            - solid_query: str (main search query)
            - alternates: list of str (alternative queries)
            - display_subtitle: str (UI subtitle with delivery info)
    
    Example selection:
    {
        "product_name": "Night Vision IP Camera",
        "selected_variant": {
            "id": "within_budget",
            "quantity": 12,
            "metrics": {
                "Resolution (MP)": 8,
                "IR range (m)": 150,
                "IP rating": "IP67",
                "Vandal rating": "IK10",
                "PoE class": "802.3at",
                "ONVIF": "Profile S/G/T"
            }
        },
        "budget_total_usd": 24000,
        "delivery_window_days": 30,
        "delivery_location": {"city": "Wichita", "state": "KS"}
    }
    """
    api_key = key or os.getenv("key") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        # Fallback if no API key
        metrics = selection.get("selected_variant", {}).get("metrics", {})
        product_name = selection.get("product_name", "product")
        metric_str = " ".join(str(v) for v in list(metrics.values())[:5])
        return {
            "solid_query": f"{product_name} {metric_str}",
            "alternates": [],
            "display_subtitle": "API key not configured"
        }
    
    client = OpenAI(api_key=api_key)
    
    try:
        # Use simple JSON mode (compatible with all SDK versions)
        resp = client.chat.completions.create(
            model=model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT + "\nReturn valid JSON with keys: solid_query, alternates, display_subtitle"},
                {"role": "user", "content": json.dumps(selection, ensure_ascii=False)}
            ],
            max_tokens=350
        )
        
        # Parse JSON response
        result = json.loads(resp.choices[0].message.content or "{}")
        
        # Ensure all required fields exist
        if "alternates" not in result:
            result["alternates"] = []
        if "display_subtitle" not in result:
            result["display_subtitle"] = ""
        
        return result
    
    except Exception as e:
        # Fallback on error
        import logging
        logging.error(f"Error generating search query: {e}")
        metrics = selection.get("selected_variant", {}).get("metrics", {})
        product_name = selection.get("product_name", "product")
        metric_str = " ".join(str(v) for v in list(metrics.values())[:5])
        return {
            "solid_query": f"{product_name} {metric_str}",
            "alternates": [],
            "display_subtitle": f"Error: {str(e)[:100]}"
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BACKWARDS COMPATIBILITY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def build_best_query(selection: Dict[str, Any], user_edit: str = "", **kwargs) -> Dict[str, Any]:
    """
    Backwards compatibility wrapper for existing server code.
    Calls generate_search_query and returns result in expected format.
    """
    # Filter kwargs to only pass supported parameters
    valid_kwargs = {}
    if 'model' in kwargs:
        valid_kwargs['model'] = kwargs['model']
    if 'key' in kwargs:
        valid_kwargs['key'] = kwargs['key']
    
    result = generate_search_query(selection, **valid_kwargs)
    
    # Add user_edit to query if provided
    if user_edit:
        result["solid_query"] = f"{result['solid_query']} {user_edit}".strip()
    
    # Ensure display_subtitle exists - build from delivery info if missing
    if not result.get("display_subtitle"):
        subtitle_parts = []
        
        delivery_location = selection.get("delivery_location")
        if delivery_location:
            city = delivery_location.get("city", "")
            state = delivery_location.get("state", "")
            if city and state:
                subtitle_parts.append(f"Delivery to {city}, {state}")
            elif state:
                subtitle_parts.append(f"Delivery to {state}")
        
        delivery_window = selection.get("delivery_window_days")
        if delivery_window:
            subtitle_parts.append(f"within {delivery_window} days")
        
        qty = selection.get("selected_variant", {}).get("quantity", 1)
        if qty > 1:
            subtitle_parts.append(f"Qty: {qty}")
        
        result["display_subtitle"] = " • ".join(subtitle_parts) if subtitle_parts else "USA delivery"
    
    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLI TEST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    selection = {
        "product_name": "Night Vision IP Camera",
        "selected_variant": {
            "id": "stretch_for_performance",
            "quantity": 12,
            "metrics": {
                "Resolution (MP)": 8,
                "IR range (m)": 150,
                "IP rating": "IP67",
                "Vandal rating": "IK10",
                "PoE class": "802.3at",
                "ONVIF": "Profile S/G/T"
            }
        },
        "budget_total_usd": 26000,
        "delivery_window_days": 30,
        "delivery_location": {"city": "Wichita", "state": "KS"}
    }
    out = generate_search_query(selection)
    print(json.dumps(out, indent=2))
