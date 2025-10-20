"""
Specification Generation Service
=================================

Knowmadics Procurement AI Assistant — Two-Variant Recommender (Generic)

This module generates exactly TWO procurement recommendations:
1. Within Budget - balanced configuration at or under budget
2. Stretch for Performance - better performance with controlled budget lift

Features:
- Upload and process documents (PDF, DOCX, XLSX, CSV)
- Extract scope from uploaded documents using LLM
- Generate TWO specification variants (within_budget, stretch_for_performance)
- Support for compliance requirements (NDAA, TAA, MIL-STD, IP ratings)
- Fully generic domain awareness (infers metrics from scope)
"""

from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from openai import OpenAI
import json
import logging
import os

logger = logging.getLogger(__name__)

# ============================================================================
# DATA MODELS
# ============================================================================

class Citation(BaseModel):
    file_id: str
    file_name: str
    quote: str
    page_hint: Optional[int] = None

class ScopeTrace(BaseModel):
    constraints: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)

class ScopeOut(BaseModel):
    summarized_bullets: List[str] = Field(default_factory=list)
    trace: ScopeTrace = Field(default_factory=ScopeTrace)

class Attachment(BaseModel):
    id: str
    name: str
    mime: str
    size: int
    summary: Optional[str] = None
    text_preview: Optional[str] = None

class FileUploadOut(BaseModel):
    attachments: List[Attachment]
    scope: ScopeOut

class SpecRequirement(BaseModel):
    key: str
    value: str

class CandidateVendor(BaseModel):
    name: str
    notes: Optional[str] = None

class SpecVariant(BaseModel):
    id: str
    title: str
    summary: str
    quantity: int
    est_unit_price_usd: float
    est_total_usd: float
    lead_time_days: int
    profile: str
    metrics: Dict[str, Any] = Field(default_factory=dict)
    must: List[SpecRequirement] = Field(default_factory=list)
    should: List[SpecRequirement] = Field(default_factory=list)
    nice: List[SpecRequirement] = Field(default_factory=list)
    preferred_vendors: Optional[List[CandidateVendor]] = None
    risks: Optional[List[str]] = None
    rationale_summary: List[str] = Field(default_factory=list)

class Recommendation(BaseModel):
    recommended_id: str
    reason: str
    scores: Dict[str, float] = Field(default_factory=lambda: {"within_budget": 0.0, "stretch_for_performance": 0.0})
    checks: Dict[str, bool] = Field(default_factory=lambda: {
        "within_budget_under_anchor": False,
        "stretch_within_range": False,
        "within_budget_suitable": True,
        "stretch_suitable": True
    })

class RecoOut(BaseModel):
    variants: List[SpecVariant]
    recommendation: Recommendation
    decision_notes: str

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def unit_anchor(pd: Dict[str, Any]) -> float:
    """Calculate unit price anchor from budget and quantity."""
    q = float(pd.get("quantity") or 1)
    b = float(pd.get("budget_total") or 0)
    return (b / q) if q > 0 else 0.0

def contains_compliance(scope: str, pd: Dict[str, Any]) -> bool:
    """Check if scope contains compliance requirements."""
    blob = f"{scope} {json.dumps(pd, ensure_ascii=False)}".lower()
    keys = ["ndaa","taa","mil-std","mil std","ip65","ip66","ip67","wide-temp","wide temperature","industrial","dfars","nist"]
    return any(k in blob for k in keys)

def scope_prompt(files: List[Dict[str, Any]]) -> str:
    """Generate prompt for scope extraction from uploaded files."""
    bundles = []
    for f in files:
        bundles.append({
            "id": f["id"], "name": f["name"],
            "text_excerpt": (f.get("text_preview") or "")[:6000]
        })
    schema = {
      "attachments": [{"id":"att-1","summary":"Comprehensive 2-4 sentence summary covering key points"}],
      "scope": {
        "summarized_bullets": ["...","..."],
        "trace": {
          "constraints": ["..."],
          "assumptions": ["..."],
          "open_questions": ["..."],
          "citations": [{"file_id":"att-1","file_name":"Scope.pdf","quote":"short quote","page_hint":3}]
        }
      }
    }
    return f"""
You are an expert procurement analyst helping a team create a comprehensive scope of work.

TASK: Analyze the uploaded documents and extract ALL critical information including:
- Technical specifications and requirements
- Quantities, budgets, and timelines
- Compliance requirements (NDAA, TAA, MIL-STD, IP ratings, etc.)
- Tables with product details, pricing, or specifications
- Vendor preferences
- Project objectives and success criteria

Return STRICT JSON only (no markdown, no explanations, no chain-of-thought).

Provide:
1) For each file: A COMPREHENSIVE 2-4 sentence summary that captures:
   - Main purpose/topic of the document
   - Key technical specifications or requirements mentioned
   - Any tables, pricing, or numerical data found
   - Important compliance or quality standards

2) A 'summarized_bullets' list (8-15 bullets) covering:
   - What product/service is being procured
   - Technical requirements (MUST have)
   - Quantity and budget constraints
   - Timeline/delivery requirements
   - Quality/compliance standards
   - Vendor preferences (if any)
   - Any special conditions or constraints
   
3) A 'trace' object with:
   - constraints: Hard requirements that cannot be changed
   - assumptions: Things assumed but not explicitly stated
   - open_questions: Unclear points that need clarification
   - citations: Key quotes from documents with page numbers

JSON schema to follow:
{json.dumps(schema, indent=2)}

FILES (with tables and structured data extracted):
{json.dumps(bundles, ensure_ascii=False, indent=2)}

IMPORTANT: 
- If tables are present, summarize their key data points
- Extract ALL numerical specifications (dimensions, speeds, capacities, etc.)
- Identify compliance requirements (NDAA, TAA, MIL-STD, IP ratings, temperature ranges)
- Be specific about quantities and pricing if mentioned
"""

def build_system_prompt(unit_anchor: float, quantity: int, stretch_low: float = 1.10, stretch_high: float = 1.25) -> str:
    """Deterministic, policy-driven prompt with single recommendation block."""
    return f"""
You are the Knowmadics Corporate Procurement AI Assistant preparing purchase-ready specs. Treat Knowmadics as buyer of record. Be auditable, deterministic, vendor-agnostic.

MISSION
- Generate exactly TWO variants and ONE recommendation:
  1) within_budget — viable at or below unit_anchor.
  2) stretch_for_performance — better suitability/performance within stretch_range.
  Then recommend ONE variant per policy.

HARD RULES
- STRICT JSON only (no markdown/prose).
- Exactly two variants (ids: within_budget, stretch_for_performance).
- Numeric units where possible (m, h, °C, W, GB, Gbps, mm).
- MUST = non-negotiables; move extras to SHOULD/NICE.
- Prefer short lead time, reputable vendors, compatibility with scope.
- Compliance if implied: NDAA §889, TAA, BAA, MIL-STD, IP, wide-temp, NIST/DFARS. Ensure at least one variant explicitly satisfies applicable items in MUST.

PRICING DISCIPLINE
- unit_anchor: {unit_anchor:.2f}; quantity: {quantity}; stretch_range: [{stretch_low:.2f}×, {stretch_high:.2f}×].
- within_budget.est_unit_price_usd <= unit_anchor.
- stretch_for_performance.est_unit_price_usd in [unit_anchor*{stretch_low:.2f}, unit_anchor*{stretch_high:.2f}].
- est_total_usd = est_unit_price_usd * quantity (money to 2 decimals).

DECISION POLICY (best short)
1) If within_budget is under anchor AND fully suitable (no critical gaps) AND strong performance (>=80) → recommend within_budget.
2) Else if within_budget has gaps (compatibility/compliance/lead-time) and stretch fixes them within stretch_range with higher performance → recommend stretch and state the specific reasons.
3) Else if both suitable → pick higher performance; tie-break by lower total cost, then faster lead time.
4) If neither fully suitable → pick lower risk and state remediation (e.g., increase anchor by X% to meet IP67 and -30–60°C).

SCHEMA (return exactly this shape; fill values)
{{
  "variants": [
    {{
      "id": "within_budget",
      "title": "Within Budget",
      "summary": "1–2 lines",
      "quantity": {quantity},
      "est_unit_price_usd": 0.0,
      "est_total_usd": 0.0,
      "lead_time_days": 30,
      "profile": "balanced",
      "metrics": {{ "Key Metric A": "", "Key Metric B": "", "Key Metric C": "" }},
      "must": [ {{ "key": "...", "value": "..." }} ],
      "should": [ {{ "key": "...", "value": "..." }} ],
      "nice": [ {{ "key": "...", "value": "..." }} ],
      "preferred_vendors": [ {{ "name": "Vendor", "notes": "" }} ],
      "risks": [],
      "rationale_summary": ["3 short bullets"]
    }},
    {{
      "id": "stretch_for_performance",
      "title": "Stretch for Performance",
      "summary": "1–2 lines",
      "quantity": {quantity},
      "est_unit_price_usd": 0.0,
      "est_total_usd": 0.0,
      "lead_time_days": 30,
      "profile": "performance",
      "metrics": {{ "Key Metric A": "", "Key Metric B": "", "Key Metric C": "" }},
      "must": [ {{ "key": "...", "value": "..." }} ],
      "should": [ {{ "key": "...", "value": "..." }} ],
      "nice": [ {{ "key": "...", "value": "..." }} ],
      "preferred_vendors": [ {{ "name": "Vendor", "notes": "" }} ],
      "risks": [],
      "rationale_summary": ["3 short bullets"]
    }}
  ],
  "recommendation": {{
    "recommended_id": "within_budget",
    "reason": "1–2 lines referencing suitability/performance/budget/lead time/compliance.",
    "scores": {{ "within_budget": 0, "stretch_for_performance": 0 }},
    "checks": {{
      "within_budget_under_anchor": true,
      "stretch_within_range": true,
      "within_budget_suitable": true,
      "stretch_suitable": true
    }}
  }},
  "decision_notes": "Concise, auditable justification; include remediation if no option fully meets scope."
}}

Return only the JSON.
""".strip()

def build_user_message(product_name: str, project_scope: str, budget_total_usd: float, quantity: int = 1, stretch_range: Tuple[float, float] = (1.10, 1.25), preferred_vendors: List[str] = None) -> str:
    """Build user message with procurement inputs."""
    payload = {
        "product_name": product_name,
        "project_scope": project_scope,
        "budget_total_usd": float(budget_total_usd),
        "quantity": int(quantity or 1),
        "stretch_range": [round(stretch_range[0], 2), round(stretch_range[1], 2)],
    }
    if preferred_vendors:
        payload["preferred_vendors"] = preferred_vendors[:6]
    return json.dumps(payload, ensure_ascii=False)

# ============================================================================
# SPECIFICATION GENERATION FUNCTIONS
# ============================================================================

def generate_scope_from_files(
    client: OpenAI,
    files: List[Dict[str, Any]],
    model: str = "gpt-4o-mini",
    token_logger: Optional[logging.Logger] = None
) -> FileUploadOut:
    """
    Generate scope summary from uploaded files.
    
    Args:
        client: OpenAI client instance
        files: List of file dictionaries with id, name, text_preview
        model: OpenAI model to use
        token_logger: Optional logger for token usage
        
    Returns:
        FileUploadOut with attachments and scope
    """
    user = scope_prompt(files)
    
    try:
        resp = client.chat.completions.create(
            model=model,
            temperature=0.2,
            max_tokens=900,
            messages=[
                {"role":"system","content": "Return STRICT JSON. Provide summaries, bullets, and a decision trace. Do not include chain-of-thought."},
                {"role":"user","content": user}
            ]
        )

        if resp.usage and token_logger:
            token_logger.info(json.dumps({
                "endpoint": "/api/files/upload",
                "model": model,
                "prompt_tokens": resp.usage.prompt_tokens,
                "completion_tokens": resp.usage.completion_tokens,
                "total_tokens": resp.usage.total_tokens
            }))

        content = extract_json_block(resp.choices[0].message.content or "{}")
        data = json.loads(content)

        att_map = {f["id"]: f for f in files}
        attachments: List[Attachment] = []
        for a in data.get("attachments", []):
            src = att_map.get(a.get("id"))
            if not src: continue
            attachments.append(Attachment(
                id=src.get("id", ""), 
                name=src.get("name", ""), 
                mime=src.get("mime", "application/octet-stream"), 
                size=src.get("size", 0),
                summary=a.get("summary") or "", 
                text_preview=src.get("text_preview") or ""
            ))

        scope = data.get("scope", {}) or {}
        bullets = scope.get("summarized_bullets") or []
        tr = scope.get("trace") or {}
        trace = ScopeTrace(
            constraints=tr.get("constraints") or [],
            assumptions=tr.get("assumptions") or [],
            open_questions=tr.get("open_questions") or [],
            citations=[Citation(**c) for c in (tr.get("citations") or []) if c.get("file_id")]
        )
        return FileUploadOut(attachments=attachments, scope=ScopeOut(summarized_bullets=bullets, trace=trace))

    except Exception as e:
        logger.error(f"Error in generate_scope_from_files: {e}")
        atts = [Attachment(
            id=f.get("id", ""), 
            name=f.get("name", ""), 
            mime=f.get("mime", "application/octet-stream"), 
            size=f.get("size", 0), 
            summary=(f.get("text_preview") or "")[:300], 
            text_preview=f.get("text_preview") or ""
        ) for f in files]
        scope = ScopeOut(summarized_bullets=["(Error summarizing) Paste the scope here manually."], trace=ScopeTrace())
        return FileUploadOut(attachments=atts, scope=scope)

def _coerce_two_variants(variants: List[Dict[str, Any]], qty: int, anchor: float) -> List[SpecVariant]:
    """Coerce LLM output to exactly TWO variants with proper structure."""
    out: List[SpecVariant] = []
    
    def _mk_default(fid: str, profile: str, unit_price: float, qty: int, summary: str) -> SpecVariant:
        return SpecVariant(
            id=fid,
            title="Within Budget" if fid == "within_budget" else "Stretch for Performance",
            summary=summary,
            quantity=qty,
            est_unit_price_usd=round(unit_price, 2),
            est_total_usd=round(unit_price * qty, 2),
            lead_time_days=30 if fid == "within_budget" else 28,
            profile=profile,
            metrics={},
            must=[],
            should=[],
            nice=[],
            preferred_vendors=[],
            risks=[],
            rationale_summary=["Fallback variant"]
        )
    
    if not variants:
        out.append(_mk_default("within_budget", "balanced", anchor, qty, "Anchor-based fallback"))
        out.append(_mk_default("stretch_for_performance", "performance", anchor * 1.15, qty, "15% stretch fallback"))
        return out
    
    def _normalize_variant(v: Dict[str, Any], fid: str, profile: str) -> SpecVariant:
        q = int(v.get("quantity") or qty or 1)
        u = float(v.get("est_unit_price_usd") or 0.0)
        t = float(v.get("est_total_usd") or (u * q))
        return SpecVariant(
            id=v.get("id", fid),
            title=v.get("title", "Within Budget" if fid == "within_budget" else "Stretch for Performance"),
            summary=v.get("summary", ""),
            quantity=q,
            est_unit_price_usd=u,
            est_total_usd=round(t, 2),
            lead_time_days=int(v.get("lead_time_days") or 30),
            profile=v.get("profile", profile),
            metrics=v.get("metrics") or {},
            must=[SpecRequirement(**x) for x in (v.get("must") or [])],
            should=[SpecRequirement(**x) for x in (v.get("should") or [])],
            nice=[SpecRequirement(**x) for x in (v.get("nice") or [])],
            preferred_vendors=[CandidateVendor(**x) for x in (v.get("preferred_vendors") or [])],
            risks=v.get("risks") or [],
            rationale_summary=[str(s) for s in (v.get("rationale_summary") or [])[:3]]
        )
    
    # Always return exactly TWO variants
    out.append(_normalize_variant(variants[0], "within_budget", "balanced") if len(variants) >= 1 
               else _mk_default("within_budget", "balanced", anchor, qty, "Anchor-based fallback"))
    out.append(_normalize_variant(variants[1], "stretch_for_performance", "performance") if len(variants) >= 2 
               else _mk_default("stretch_for_performance", "performance", anchor * 1.15, qty, "15% stretch fallback"))
    
    return out[:2]

def generate_recommendations(
    client: OpenAI,
    project_context: Dict[str, Any],
    product_details: Dict[str, Any],
    scope_bullets: List[str],
    uploaded_summaries: List[str],
    model: str = "gpt-4o-mini",  # Cheaper model for cost savings
    token_logger: Optional[logging.Logger] = None,
    stretch_range: Tuple[float, float] = (1.10, 1.25)
) -> RecoOut:
    """
    Generate exactly TWO specification variants using Knowmadics procurement AI.
    
    Args:
        client: OpenAI client instance
        project_context: Project context dictionary
        product_details: Product details dictionary (must include budget_total, quantity)
        scope_bullets: List of scope bullet points
        uploaded_summaries: List of file summaries
        model: OpenAI model to use (default: gpt-4o)
        token_logger: Optional logger for token usage
        stretch_range: (low, high) multipliers for stretch variant pricing
        
    Returns:
        RecoOut with exactly TWO variants and decision notes
    """
    qty = max(int(product_details.get("quantity") or 1), 1)
    budget = float(product_details.get("budget_total") or 0)
    anchor = unit_anchor(product_details)
    
    # Extract product name and build scope
    product_name = product_details.get("product_name") or product_details.get("item_name") or "Product"
    project_scope = "\n".join(scope_bullets) if scope_bullets else product_details.get("description", "")
    
    # Extract preferred vendors
    preferred_vendors = [v if isinstance(v, str) else v.get("name", "") 
                        for v in (product_details.get("preferred_vendors") or [])]
    
    # Build prompts
    sys_msg = build_system_prompt(anchor, qty, float(stretch_range[0]), float(stretch_range[1]))
    user_msg = build_user_message(product_name, project_scope, budget, qty, stretch_range, preferred_vendors)
    
    try:
        resp = client.chat.completions.create(
            model=model,
            temperature=0,  # Deterministic output
            max_tokens=1800,
            response_format={"type": "json_object"},  # Enforce JSON output
            messages=[
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": user_msg}
            ]
        )

        if resp.usage and token_logger:
            token_logger.info(json.dumps({
                "endpoint": "/api/generate_recommendations",
                "model": model,
                "prompt_tokens": resp.usage.prompt_tokens,
                "completion_tokens": resp.usage.completion_tokens,
                "total_tokens": resp.usage.total_tokens
            }))

        content = resp.choices[0].message.content or "{}"
        try:
            data = json.loads(content) if content else {}
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            logger.error(f"Content preview: {content[:500]}")
            # Try to extract JSON if wrapped in markdown
            content = extract_json_block(content)
            data = json.loads(content)
        
        variants = _coerce_two_variants(data.get("variants") or [], qty, anchor)
        
        # Ensure totals are correct
        for v in variants:
            v.est_unit_price_usd = round(float(v.est_unit_price_usd), 2)
            v.est_total_usd = round(v.est_unit_price_usd * int(v.quantity), 2)
        
        # Handle recommendation with fallback policy
        reco = data.get("recommendation") or {}
        if not reco or not reco.get("recommended_id"):
            # Apply default policy if LLM omitted recommendation
            within = next((x for x in variants if x.id == "within_budget"), variants[0])
            stretch = next((x for x in variants if x.id == "stretch_for_performance"), variants[1] if len(variants) > 1 else within)
            
            within_ok = within.est_unit_price_usd <= anchor
            stretch_ok = (anchor * stretch_range[0] <= stretch.est_unit_price_usd <= anchor * stretch_range[1])
            
            # Pick within_budget if it's under anchor and suitable, otherwise stretch
            pick = "within_budget" if within_ok else "stretch_for_performance"
            reason = "Within anchor and suitable baseline." if within_ok else "Within-budget option not viable; selecting stretch for better suitability."
            
            reco = {
                "recommended_id": pick,
                "reason": reason,
                "scores": {"within_budget": 85.0 if within_ok else 60.0, "stretch_for_performance": 75.0 if stretch_ok else 50.0},
                "checks": {
                    "within_budget_under_anchor": within_ok,
                    "stretch_within_range": stretch_ok,
                    "within_budget_suitable": True,
                    "stretch_suitable": True
                }
            }
        
        return RecoOut(
            variants=variants,
            recommendation=Recommendation(**reco),
            decision_notes=data.get("decision_notes", "Policy-based selection applied.")
        )

    except Exception as e:
        logger.error(f"Error in generate_recommendations: {e}")
        # Fallback: return two safe variants with default recommendation
        variants = _coerce_two_variants([], qty, anchor)
        for v in variants:
            v.est_total_usd = round(v.est_unit_price_usd * v.quantity, 2)
        
        default_reco = Recommendation(
            recommended_id="within_budget",
            reason="Fallback recommendation after error",
            scores={"within_budget": 50.0, "stretch_for_performance": 50.0},
            checks={
                "within_budget_under_anchor": True,
                "stretch_within_range": False,
                "within_budget_suitable": True,
                "stretch_suitable": True
            }
        )
        return RecoOut(variants=variants, recommendation=default_reco, decision_notes="Fallback after LLM error")

def get_fallback_scope(files: List[Dict[str, Any]]) -> FileUploadOut:
    """Generate fallback scope when LLM is unavailable."""
    scope = {
        "summarized_bullets": ["(LLM unavailable) Provide mission, constraints, qty, timeline here."],
        "trace": {
          "constraints": [], "assumptions": [], "open_questions": [], "citations": []
        }
    }
    atts = []
    for f in files:
        atts.append({
          "id": f["id"], "name": f["name"], "mime": f["mime"],
          "size": f["size"], "summary": (f.get("text_preview") or "")[:300],
          "text_preview": f.get("text_preview") or ""
        })
    return FileUploadOut(attachments=[Attachment(**a) for a in atts], scope=ScopeOut(**scope))

def get_fallback_recommendations(product_details: Dict[str, Any]) -> RecoOut:
    """Generate fallback recommendations when LLM is unavailable - returns exactly TWO variants."""
    q = int(product_details.get("quantity") or 1)
    a = unit_anchor(product_details) or 1000.0
    
    # Two variants: within_budget and stretch_for_performance
    variants = [
        SpecVariant(
            id="within_budget",
            title="Within Budget",
            summary="Budget-aligned fallback variant (no LLM available)",
            quantity=q,
            est_unit_price_usd=a,
            est_total_usd=round(a*q, 2),
            lead_time_days=30,
            profile="balanced",
            metrics={},
            must=[],
            should=[],
            nice=[],
            preferred_vendors=[],
            risks=[],
            rationale_summary=[
                "Heuristic around budget anchor",
                "No LLM available",
                "Adjust after search"
            ]
        ),
        SpecVariant(
            id="stretch_for_performance",
            title="Stretch for Performance",
            summary="15% budget stretch for better performance (no LLM available)",
            quantity=q,
            est_unit_price_usd=round(a * 1.15, 2),
            est_total_usd=round(a * 1.15 * q, 2),
            lead_time_days=28,
            profile="performance",
            metrics={},
            must=[],
            should=[],
            nice=[],
            preferred_vendors=[],
            risks=[],
            rationale_summary=[
                "15% budget lift for performance",
                "No LLM available",
                "Adjust after search"
            ]
        )
    ]
    
    # Add default recommendation
    fallback_reco = Recommendation(
        recommended_id="within_budget",
        reason="Recommending within budget as baseline fallback (LLM unavailable)",
        scores={"within_budget": 50.0, "stretch_for_performance": 50.0},
        checks={
            "within_budget_under_anchor": True,
            "stretch_within_range": True,
            "within_budget_suitable": True,
            "stretch_suitable": True
        }
    )
    
    return RecoOut(
        variants=variants,
        recommendation=fallback_reco,
        decision_notes="Fallback without LLM - configure OpenAI API key for intelligent recommendations"
    )

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def extract_json_block(text: str) -> str:
    """Extract JSON from text that may contain markdown code blocks."""
    import re
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z0-9]*", "", t).strip("` \n")
    s, e = t.find("{"), t.rfind("}")
    return t[s:e+1] if s!=-1 and e!=-1 and e>s else t
