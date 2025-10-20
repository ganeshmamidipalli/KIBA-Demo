"""
Procurement recommendations service for KPA One-Flow.
Generates final product recommendations based on confirmed requirements.
"""

import json
import re
import logging
from typing import Dict, Any
from services.openai_client import client
from services.schema_definitions import SEARCH_READY_RECS_SCHEMA
from services.prompt_templates import SYSTEM_PROMPT, recs_prompt

logger = logging.getLogger(__name__)

def run_recommendations(product_name: str, budget: float, quantity: int, summary: str) -> Dict[str, Any]:
    """
    Generate product recommendations based on confirmed requirements.
    
    Args:
        product_name: Name of the product/service
        budget: Budget in USD
        quantity: Quantity needed
        summary: Confirmed requirements summary
        
    Returns:
        Dict with recommendations and metadata
    """
    try:
        # Check if client is available (for testing)
        if client is None:
            logger.info("OpenAI client not available, using fallback recommendations")
            unit_price = budget / quantity if quantity > 0 else budget
            return {
                "schema_version": "1.0",
                "summary": f"Recommendations for {product_name} based on your requirements",
                "recommendations": [
                    {
                        "id": "budget-option-1",
                        "name": f"Standard {product_name}",
                        "specs": ["Basic specifications", "Standard performance", "Essential features"],
                        "estimated_price_usd": unit_price * 0.8,
                        "meets_budget": True,
                        "value_note": "Good value for money, meets basic requirements",
                        "rationale": "Fits within budget while providing essential functionality",
                        "score": 85.0,
                        "vendor_search": {
                            "model_name": f"Standard {product_name}",
                            "spec_fragments": ["standard", "basic", "essential"],
                            "region_hint": "USA",
                            "budget_hint_usd": unit_price * 0.8,
                            "query_seed": f"standard {product_name} budget"
                        }
                    },
                    {
                        "id": "premium-option-1",
                        "name": f"Premium {product_name}",
                        "specs": ["High-end specifications", "Premium performance", "Advanced features"],
                        "estimated_price_usd": unit_price * 1.2,
                        "meets_budget": False,
                        "value_note": "Premium option with advanced features",
                        "rationale": "Higher performance and features, slightly over budget",
                        "score": 75.0,
                        "vendor_search": {
                            "model_name": f"Premium {product_name}",
                            "spec_fragments": ["premium", "high-end", "advanced"],
                            "region_hint": "USA",
                            "budget_hint_usd": unit_price * 1.2,
                            "query_seed": f"premium {product_name} high-end"
                        }
                    }
                ],
                "recommended_index": 0,
                "selection_mode": "single_or_multi",
                "disclaimer": "These are fallback recommendations for testing purposes."
            }
        
        payload = recs_prompt(product_name, budget, quantity, summary)
        
        # Use OpenAI responses API with structured output
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=2000,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": SEARCH_READY_RECS_SCHEMA["name"],
                    "schema": SEARCH_READY_RECS_SCHEMA["schema"],
                    "strict": SEARCH_READY_RECS_SCHEMA["strict"]
                }
            },
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": payload}
            ]
        )
        
        # Parse response
        content = resp.choices[0].message.content
        if not content:
            raise ValueError("Empty response from OpenAI")
            
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in recommendations: {e}")
            logger.error(f"Content: {content[:500]}")
            raise ValueError(f"Invalid JSON response: {e}")
        
        # Ensure IDs and defaults
        recommendations = parsed.get("recommendations", [])
        for i, rec in enumerate(recommendations):
            if not rec.get("id"):
                # Generate ID from name
                base = re.sub(r"[^a-z0-9]+", "-", (rec.get("name") or f"rec-{i+1}").lower()).strip("-")
                rec["id"] = f"{base}-{i+1}"
        
        # Set defaults
        parsed.setdefault("schema_version", "1.0")
        parsed.setdefault("selection_mode", "single_or_multi")
        parsed.setdefault("disclaimer", "Recommendations are AI-generated and should be verified before procurement.")
        
        # Ensure recommended_index is valid
        if "recommended_index" not in parsed or parsed["recommended_index"] >= len(recommendations):
            parsed["recommended_index"] = 0
            
        logger.info(f"Recommendations generated: {len(recommendations)} options")
        return parsed
        
    except Exception as e:
        logger.error(f"Error in run_recommendations: {e}")
        # Return fallback response
        return {
            "schema_version": "1.0",
            "summary": f"Basic recommendations for {product_name}",
            "recommendations": [
                {
                    "id": "fallback-1",
                    "name": f"Standard {product_name}",
                    "specs": ["Basic specifications"],
                    "estimated_price_usd": budget / quantity if quantity > 0 else budget,
                    "meets_budget": True,
                    "value_note": "Fallback recommendation",
                    "rationale": "Basic option due to processing error",
                    "score": 50.0,
                    "vendor_search": {
                        "model_name": product_name,
                        "spec_fragments": [product_name],
                        "region_hint": "USA",
                        "budget_hint_usd": budget,
                        "query_seed": product_name
                    }
                }
            ],
            "recommended_index": 0,
            "selection_mode": "single_or_multi",
            "disclaimer": "Fallback recommendation due to processing error."
        }
