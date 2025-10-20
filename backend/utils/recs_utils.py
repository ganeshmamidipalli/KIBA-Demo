"""
Recommendations postprocessing utilities for KPA One-Flow.
Ensures proper sorting, scoring, and data validation.
"""
from typing import Dict, Any


def postprocess_recs(pack: Dict[str, Any]) -> Dict[str, Any]:
    """
    Postprocess recommendations to ensure proper sorting, scoring, and data validation.
    
    Args:
        pack: Raw recommendations pack from AI service
        
    Returns:
        Processed recommendations pack with guaranteed ordering and data
    """
    recs = pack.get("recommendations") or []
    
    # Ensure all recommendations have required fields and proper data types
    for r in recs:
        # Guarantee rationale/value_note present
        r.setdefault("value_note", "")
        r.setdefault("rationale", "")
        
        # Coerce score to float; missing or invalid -> 0
        try:
            r["score"] = float(r.get("score", 0))
        except (ValueError, TypeError):
            r["score"] = 0.0
            
        # Ensure estimated_price_usd is a number or null
        if "estimated_price_usd" in r and r["estimated_price_usd"] is not None:
            try:
                r["estimated_price_usd"] = float(r["estimated_price_usd"])
            except (ValueError, TypeError):
                r["estimated_price_usd"] = None
                
        # Ensure meets_budget is boolean
        if "meets_budget" not in r:
            r["meets_budget"] = True  # Default to True if not specified
            
        # Ensure specs is a list
        if not isinstance(r.get("specs"), list):
            r["specs"] = []
    
    # Sort by score (best -> least)
    recs.sort(key=lambda r: r["score"], reverse=True)
    
    # Update the pack
    pack["recommendations"] = recs
    pack["recommended_index"] = 0 if recs else -1
    pack.setdefault("schema_version", "1.0")
    pack.setdefault("selection_mode", "single_or_multi")
    
    return pack
