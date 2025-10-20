"""
Prompt templates for KPA One-Flow AI interactions.
"""

SYSTEM_PROMPT = """
You are the Knowmadics Procurement AI Assistant (KPA).
- For INTAKE: ask 3–6 targeted, non-redundant follow-ups; stop when confident.
- For RECS: produce 1–5 concise, scored, vendor-search-ready options.
- Always output STRICT JSON per provided schema.
- Focus on procurement-specific requirements and technical specifications.
- Consider budget constraints and vendor availability.
""".strip()

def intake_prompt(product_name: str, budget: float, quantity: int, scope: str) -> str:
    """Generate prompt for intake phase."""
    return f"""PRODUCT_NAME: {product_name}
BUDGET_USD: {budget}
QUANTITY: {quantity}
SCOPE_AND_NOTES:
{scope}

TASK: Stage 1 intake. Ask only essential follow-ups (3–6). 
Avoid repeats or boilerplate. Summarize normalized requirements. 
Return JSON per INTAKE schema."""

def recs_prompt(product_name: str, budget: float, quantity: int, confirmed_summary: str) -> str:
    """Generate prompt for recommendations phase."""
    return f"""CONFIRMED_REQUIREMENTS_SUMMARY:
{confirmed_summary}

PRODUCT_NAME: {product_name}
BUDGET_USD: {budget}
QUANTITY: {quantity}

TASK: Produce 1–5 recommendations ordered by overall fit. 
Include score (0..100), budget fit, vendor_search fields. 
Return JSON per SEARCH_READY_RECS schema. No links."""
