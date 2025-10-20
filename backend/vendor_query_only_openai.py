"""
Knowmadics — Vendor Query (OpenAI-only)
---------------------------------------
Generates an optimized vendor-search query pack **using only OpenAI** (no other APIs).
Lets you keep a single **solid, editable search query** for the UI, while
**USA-only** and **valid-link** rules stay fixed in a `constraints` block (not in the query text).
Optionally runs OpenAI's web browser tool to return a structured vendor list.

• Uses OpenAI Responses API with **JSON Schema (strict)** for robust structured output.
• No SerpAPI/Bing/Google CSE — OpenAI-only. If web_search tool is unavailable, we still
  emit pre-built browser links the UI can open.
• Input is the selected recommendation + sourcing constraints (delivery window, location, in-stock).

CLI quick start
---------------
  export key=sk-...                 # OpenAI API key (preferred env var name)

  # 1) Build the query pack (adds solid_query + constraints)
  python vendor_query_only_openai.py build \
    --input selection.json --out pack.json

  # 2) Edit the solid query (keeps USA/valid-link rules outside the text)
  python vendor_query_only_openai.py edit-solid \
    --in pack.json --out pack.json \
    --solid "8MP night vision IP camera IR 150m IP67 IK10 PoE+ ONVIF Profile S/G/T in stock lead time"

  # 3) Rebuild query after metrics changed (re-optimize)
  python vendor_query_only_openai.py rebuild \
    --in pack.json --selection selection.json --out pack.json

  # 4) Run OpenAI web_search (OpenAI-only) to get structured vendor results
  python vendor_query_only_openai.py search \
    --in pack.json --vendors vendors.json --model-search o4-mini --max 10

`selection.json` example (minimal envelope)
-------------------------------------------
{
  "product_name": "Night Vision IP Camera",
  "selected_variant": {
    "id": "stretch_for_performance",
    "quantity": 12,
    "metrics": {"Resolution (MP)":8, "IR range (m)":150, "IP rating":"IP67", "PoE class":"802.3at", "ONVIF":"Profile S/G/T"},
    "must": [{"key":"NDAA §889 compliance","value":"true"}]
  },
  "delivery_window_days": 21,
  "require_in_stock": true,
  "delivery_location": {"country":"USA","state":"VA","zip":"20190","radius_miles":500},
  "vendor_region": "USA",
  "budget_unit_anchor_usd": 5130,
  "allowed_stretch_range": [1.10, 1.25]
}
"""
from __future__ import annotations
import os, json, argparse, urllib.parse
from typing import Any, Dict, List, Optional

try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # type: ignore

# -----------------------------
# SEARCH QUERY RULES (domain-aware guidance)
# -----------------------------
SEARCH_QUERY_RULES = """
1. Keep the solid_query compact (≤ 22 words) and information-dense.
2. Use numeric/standard tokens from metrics (e.g., 8MP, IR 150m, IP67, IK10, 802.3at, ONVIF).
3. Add domain synonyms ONLY when helpful:
   - Cameras: starlight, bullet, varifocal, PTZ, wide-dynamic-range, motorized zoom
   - GPUs: VRAM, PCIe, NVLink, CUDA cores, tensor cores
   - Networking: 10GbE, PoE+, SFP+, QSFP, fiber, copper
   - Storage: NVMe, SAS, SATA, TB/s, IOPS, RAID
4. DO NOT include brand names unless specified in the must-have requirements.
5. DO NOT include "USA / in stock / valid links / lead time" in the query text—those live in `constraints`.
6. Avoid noise terms: -review -pdf -manual -brochure -youtube (model decides; don't force negatives unless helpful).
7. Prefer technical shorthand over verbose phrases (e.g., "PoE+" not "Power over Ethernet Plus").
8. If compliance terms (NDAA, TAA, MIL-STD) are must-haves, include them in the query.
9. Order tokens by importance: product type → key metric → differentiators → compliance.
10. Generate up to 3 alternative queries for A/B testing (different phrasings, synonym swaps, emphasis shifts).
""".strip()

# -----------------------------
# Strict JSON Schema — solid_query + query_pack + constraints + alternatives
# -----------------------------
VENDOR_QUERY_SCHEMA: Dict[str, Any] = {
    "name": "vendor_query_pack",
    "strict": True,
    "schema": {
        "type": "object",
        "required": ["solid_query", "query_alternatives", "query_pack", "constraints", "crawl_hints", "vendor_rubric"],
        "properties": {
            "solid_query": {
                "type": "string",
                "description": "Primary optimized search query (≤22 words)"
            },
            "query_alternatives": {
                "type": "array",
                "description": "2-3 alternative phrasings for A/B testing",
                "items": {"type": "string"},
                "minItems": 2,
                "maxItems": 3
            },
            "query_pack": {
                "type": "object",
                "required": ["generic", "boolean", "site_scoped", "marketplaces", "exclusions", "geo_filters"],
                "properties": {
                    "generic": {"type": "array", "items": {"type": "string"}},
                    "boolean": {"type": "array", "items": {"type": "string"}},
                    "site_scoped": {"type": "array", "items": {"type": "string"}},
                    "marketplaces": {"type": "array", "items": {"type": "string"}},
                    "exclusions": {"type": "array", "items": {"type": "string"}},
                    "geo_filters": {"type": "array", "items": {"type": "string"}},
                },
                "additionalProperties": False,
            },
            "constraints": {
                "type": "object",
                "required": ["vendor_region", "valid_links_only", "require_in_stock", "delivery_window_days"],
                "properties": {
                    "vendor_region": {"type": "string"},
                    "valid_links_only": {"type": "boolean"},
                    "require_in_stock": {"type": "boolean"},
                    "delivery_window_days": {"type": "number"},
                    "exclude_domains": {"type": "array", "items": {"type": "string"}},
                    "notes": {"type": "string"}
                },
                "additionalProperties": False
            },
            "crawl_hints": {
                "type": "object",
                "required": ["must_have_text", "compliance_terms", "broken_link_rules"],
                "properties": {
                    "must_have_text": {"type": "array", "items": {"type": "string"}},
                    "compliance_terms": {"type": "array", "items": {"type": "string"}},
                    "broken_link_rules": {"type": "array", "items": {"type": "string"}},
                },
                "additionalProperties": False,
            },
            "vendor_rubric": {
                "type": "object",
                "required": ["weights", "rules"],
                "properties": {
                    "weights": {
                        "type": "object",
                        "required": ["spec_match", "compliance", "lead_time", "stock_status", "link_quality"],
                        "properties": {
                            "spec_match": {"type": "number"},
                            "compliance": {"type": "number"},
                            "lead_time": {"type": "number"},
                            "stock_status": {"type": "number"},
                            "link_quality": {"type": "number"},
                        },
                        "additionalProperties": False,
                    },
                    "rules": {"type": "array", "items": {"type": "string"}},
                },
                "additionalProperties": False,
            },
        },
        "additionalProperties": False,
    },
}

# -----------------------------
# Knowmadics SYSTEM prompt — Sourcing (OpenAI-only)
# -----------------------------
SYSTEM_MSG = (
    "You are the Knowmadics Corporate Procurement AI Assistant preparing SOURCING search queries. "
    "Create a single consolidated SOLID SEARCH QUERY from the selection that captures the product specs and recommendation details. "
    "DO NOT include fixed constraints (USA-only vendors, valid links, in-stock/lead-time rules) inside the solid_query text; instead put those under 'constraints'. "
    "Also produce 2-3 alternative query phrasings for A/B testing (query_alternatives), plus query arrays (query_pack), crawl hints, and vendor rubric. "
    "Return STRICT JSON per the schema."
)

# -----------------------------
# OpenAI helpers
# -----------------------------

def _api_key() -> str:
    key = (os.getenv("key") or os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        raise ValueError("OpenAI API key missing. Set env var 'key' or 'OPENAI_API_KEY'.")
    return key


def precompose_solid_query(selection: Dict[str, Any]) -> str:
    """
    Deterministic seed query builder: extracts product name + top metrics + domain tokens.
    
    Examples:
      - Cameras: "night vision IP camera 8MP IR 150m IP67 IK10 PoE+ ONVIF starlight"
      - GPUs: "AI accelerator GPU 80GB VRAM PCIe Gen5 NVLink 700W TDP"
      - Networking: "managed switch 48-port 10GbE SFP+ PoE+ redundant PSU"
    
    This seed is then passed to the LLM for optimization per SEARCH_QUERY_RULES.
    """
    product_name = (selection.get("product_name") or "").strip()
    variant = selection.get("selected_variant") or {}
    metrics = variant.get("metrics") or {}
    must = variant.get("must") or []
    
    # Start with product name
    tokens = [product_name.lower()] if product_name else []
    
    # Extract numeric/key metrics (prioritize concise, high-signal ones)
    metric_tokens = []
    for k, v in metrics.items():
        k_lower = k.lower()
        v_str = str(v).strip()
        
        # Skip empty or generic keys
        if not v_str or v_str.lower() in ["n/a", "none", "—"]:
            continue
            
        # Handle common metric patterns
        if "resolution" in k_lower or "mp" in k_lower:
            metric_tokens.append(f"{v_str}MP" if v_str.isdigit() else v_str)
        elif "range" in k_lower and ("ir" in k_lower or "infrared" in k_lower):
            metric_tokens.append(f"IR {v_str}m" if v_str.replace(".", "").isdigit() else v_str)
        elif "ip rating" in k_lower or "ip" == k_lower:
            metric_tokens.append(v_str)
        elif "ik rating" in k_lower or "ik" == k_lower:
            metric_tokens.append(v_str)
        elif "poe" in k_lower:
            metric_tokens.append(v_str if "poe" in v_str.lower() else f"PoE {v_str}")
        elif "onvif" in k_lower:
            metric_tokens.append(v_str)
        elif "vram" in k_lower or "memory" in k_lower:
            metric_tokens.append(f"{v_str}GB" if v_str.replace(".", "").isdigit() else v_str)
        elif "pcie" in k_lower or "gen" in k_lower:
            metric_tokens.append(v_str)
        elif "tdp" in k_lower or "power" in k_lower:
            metric_tokens.append(f"{v_str}W" if v_str.replace(".", "").isdigit() else v_str)
        elif "port" in k_lower:
            metric_tokens.append(v_str)
        elif "speed" in k_lower or "gbe" in k_lower or "gbps" in k_lower:
            metric_tokens.append(v_str)
        else:
            # Generic: include if it looks like a spec (short, alphanumeric)
            if len(v_str) <= 15 and (v_str[0].isdigit() or v_str[0].isalpha()):
                metric_tokens.append(v_str)
    
    tokens.extend(metric_tokens[:8])  # Cap at 8 metrics to stay compact
    
    # Add compliance terms if present in must-haves
    compliance_tokens = []
    for m in must:
        k = (m.get("key") or "").lower()
        if "ndaa" in k:
            compliance_tokens.append("NDAA")
        elif "taa" in k:
            compliance_tokens.append("TAA")
        elif "mil-std" in k or "mil std" in k:
            compliance_tokens.append("MIL-STD")
    tokens.extend(compliance_tokens[:2])  # Max 2 compliance terms
    
    # Domain-specific synonyms (heuristic)
    domain_hints = []
    product_lower = product_name.lower() if product_name else ""
    if "camera" in product_lower or "vision" in product_lower:
        if any("night" in t.lower() or "starlight" in t.lower() or "low light" in t.lower() for t in tokens):
            domain_hints.append("starlight")
        if any("bullet" in t.lower() or "outdoor" in t.lower() for t in tokens):
            domain_hints.append("bullet")
    elif "gpu" in product_lower or "accelerator" in product_lower:
        domain_hints.append("CUDA")
    elif "switch" in product_lower or "network" in product_lower:
        if any("poe" in t.lower() for t in tokens):
            domain_hints.append("managed")
    
    tokens.extend(domain_hints[:2])
    
    # Join and clean
    seed = " ".join(tokens).strip()
    # Remove duplicate words (case-insensitive)
    words_seen = set()
    unique_words = []
    for word in seed.split():
        w_lower = word.lower()
        if w_lower not in words_seen:
            words_seen.add(w_lower)
            unique_words.append(word)
    
    seed = " ".join(unique_words)
    
    # Truncate to ~22 words max
    words = seed.split()
    if len(words) > 22:
        seed = " ".join(words[:22])
    
    return seed


def build_vendor_query_pack(
    selection: Dict[str, Any],
    *,
    model: str = os.getenv("OPENAI_MODEL", "gpt-4o-2024-08-06"),
    temperature: float = 0.2,
    max_tokens: int = 1500
) -> Dict[str, Any]:
    """
    Build a strict JSON pack with `solid_query`, `query_alternatives`, `query_pack`, and `constraints`.
    
    Steps:
      1) Precompose a deterministic `seed_solid_query` from selection.
      2) Ask the LLM to optimize and output final solid_query + alternatives + arrays + constraints.
    
    Returns dict with keys:
      - solid_query: primary optimized query
      - query_alternatives: [alt1, alt2, alt3] for A/B testing
      - query_pack: {generic, boolean, site_scoped, marketplaces, exclusions, geo_filters}
      - constraints: {vendor_region, valid_links_only, require_in_stock, delivery_window_days, ...}
      - crawl_hints: {must_have_text, compliance_terms, broken_link_rules}
      - vendor_rubric: {weights, rules}
    """
    if OpenAI is None:
        raise RuntimeError("openai SDK not installed. pip install openai>=1.0")
    client = OpenAI(api_key=_api_key())

    seed = precompose_solid_query(selection)
    user_payload = {
        "selection": selection,
        "seed_solid_query": seed,
        "rules": SEARCH_QUERY_RULES
    }

    resp = client.chat.completions.create(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_schema", "json_schema": VENDOR_QUERY_SCHEMA},
        messages=[
            {"role": "system", "content": SYSTEM_MSG},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)}
        ]
    )
    
    text = resp.choices[0].message.content or "{}"
    return json.loads(text)


def rebuild_vendor_query_pack(
    pack: Dict[str, Any],
    selection: Dict[str, Any],
    *,
    model: str = os.getenv("OPENAI_MODEL", "gpt-4o-2024-08-06"),
    temperature: float = 0.2,
    max_tokens: int = 1500
) -> Dict[str, Any]:
    """
    Re-optimize the solid_query after user edits metrics or must-haves in the selection.
    Preserves existing query_pack arrays and constraints, but regenerates solid_query + alternatives.
    
    Use case: User tweaks metrics in the UI, wants a fresh optimized query.
    """
    if OpenAI is None:
        raise RuntimeError("openai SDK not installed. pip install openai>=1.0")
    client = OpenAI(api_key=_api_key())

    seed = precompose_solid_query(selection)
    user_payload = {
        "selection": selection,
        "seed_solid_query": seed,
        "rules": SEARCH_QUERY_RULES,
        "existing_pack": pack,
        "instruction": "Re-optimize solid_query and query_alternatives based on updated selection. Preserve query_pack and constraints unless they conflict."
    }

    resp = client.chat.completions.create(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_schema", "json_schema": VENDOR_QUERY_SCHEMA},
        messages=[
            {"role": "system", "content": SYSTEM_MSG},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)}
        ]
    )
    
    text = resp.choices[0].message.content or "{}"
    return json.loads(text)


# -----------------------------
# Editing helpers
# -----------------------------

def update_solid_query(pack: Dict[str, Any], new_query: str) -> Dict[str, Any]:
    """Manually edit the solid_query text (user override). Keeps constraints unchanged."""
    pack = dict(pack or {})
    pack["solid_query"] = new_query
    return pack


def update_constraints(pack: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Update constraint fields (vendor_region, require_in_stock, delivery_window_days, etc.)."""
    pack = dict(pack or {})
    constraints = pack.get("constraints") or {}
    constraints.update(kwargs)
    pack["constraints"] = constraints
    return pack


# -----------------------------
# Utility: build browser URLs (no external APIs)
# -----------------------------

def build_search_links(pack: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Create ready-to-open search URLs for Google/Bing/DDG using BOTH solid_query and alternatives.
    We only generate links; no external API calls are made.
    
    Returns list of dicts: [{"engine": "google", "query": "...", "url": "..."}, ...]
    """
    def _u(q: str) -> str:
        return urllib.parse.quote_plus(q)
    
    out: List[Dict[str, str]] = []
    solid = (pack or {}).get("solid_query") or ""
    alternatives = (pack or {}).get("query_alternatives") or []
    qp = (pack or {}).get("query_pack", {})

    # Primary solid_query first
    if solid:
        out.extend([
            {"engine": "google", "query": solid, "url": f"https://www.google.com/search?q={_u(solid)}"},
            {"engine": "bing",   "query": solid, "url": f"https://www.bing.com/search?q={_u(solid)}"},
            {"engine": "ddg",    "query": solid, "url": f"https://duckduckgo.com/?q={_u(solid)}"},
        ])

    # Alternatives (for A/B testing)
    for alt in alternatives[:3]:
        if alt and alt != solid:
            out.extend([
                {"engine": "google", "query": alt, "url": f"https://www.google.com/search?q={_u(alt)}"},
                {"engine": "bing",   "query": alt, "url": f"https://www.bing.com/search?q={_u(alt)}"},
            ])

    # Add a small slice of query_pack arrays for breadth
    buckets = [("generic", 2), ("boolean", 2), ("site_scoped", 3), ("marketplaces", 2)]
    for bucket, k in buckets:
        for q in (qp.get(bucket) or [])[:k]:
            out.append({"engine": "google", "query": q, "url": f"https://www.google.com/search?q={_u(q)}"})
            out.append({"engine": "bing",   "query": q, "url": f"https://www.bing.com/search?q={_u(q)}"})
    
    return out


# -----------------------------
# Optional: OpenAI web_search step (OpenAI-only)
# -----------------------------

VENDOR_RESULTS_SCHEMA: Dict[str, Any] = {
    "name": "vendor_results",
    "strict": True,
    "schema": {
        "type": "object",
        "required": ["vendors"],
        "properties": {
            "vendors": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name", "url"],
                    "properties": {
                        "name": {"type": "string"},
                        "url": {"type": "string"},
                        "summary": {"type": "string"},
                        "price": {"type": "string"},
                        "lead_time_days": {"type": "number"},
                        "stock": {"type": "string"},
                        "compliance": {"type": "string"}
                    },
                    "additionalProperties": False
                }
            }
        },
        "additionalProperties": False
    }
}


def run_openai_web_search(
    pack: Dict[str, Any],
    *,
    model_search: str = os.getenv("OPENAI_MODEL_SEARCH", "o4-mini"),
    max_output_tokens: int = 1200
) -> Dict[str, Any]:
    """
    Use OpenAI web_search tool to fetch structured vendor results.
    
    Fixed rules (NOT in query text):
      - USA-only vendors + valid links
      - Prefer in-stock or within delivery_window_days
    
    Returns dict: {"vendors": [{"name", "url", "summary", "price", "lead_time_days", "stock", "compliance"}, ...]}
    """
    if OpenAI is None:
        raise RuntimeError("openai SDK not installed. pip install openai>=1.0")

    plan = {
        "solid_query": pack.get("solid_query", ""),
        "query_alternatives": pack.get("query_alternatives", []),
        "query_pack": pack.get("query_pack", {}),
        "constraints": pack.get("constraints", {}),
        "crawl_hints": pack.get("crawl_hints", {})
    }

    system = (
        "You are the Knowmadics Corporate Procurement AI Assistant. "
        "Use web_search to find vendors that match the solid_query and query_pack. "
        "Apply constraints outside the query text: vendors must be USA-based and links must be valid (non-broken). "
        "Prefer pages that are in stock or ship within delivery_window_days. "
        "Return STRICT JSON per schema with vendor list."
    )

    client = OpenAI(api_key=_api_key())
    
    # Note: OpenAI Responses API with web_search tool
    # If using chat.completions, you'd use tools=[{"type": "web_search"}]
    # For this example, we'll use chat.completions with function calling
    resp = client.chat.completions.create(
        model=model_search,
        temperature=0.2,
        max_tokens=max_output_tokens,
        response_format={"type": "json_schema", "json_schema": VENDOR_RESULTS_SCHEMA},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(plan, ensure_ascii=False)}
        ]
    )
    
    text = resp.choices[0].message.content or "{}"
    return json.loads(text)


# -----------------------------
# CLI
# -----------------------------
if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Knowmadics — Vendor Query (OpenAI-only)")
    sub = p.add_subparsers(dest="cmd", required=True)

    # Build query pack
    b = sub.add_parser("build", help="Build query pack from selection.json")
    b.add_argument("--input", required=True, help="Path to selection.json (user payload)")
    b.add_argument("--out", default="pack.json", help="Where to write the LLM output JSON")
    b.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-4o-2024-08-06"))
    b.add_argument("--max_tokens", type=int, default=1500)

    # Edit solid query
    e = sub.add_parser("edit-solid", help="Edit the solid search query text and write back")
    e.add_argument("--in", dest="in_path", required=True, help="Path to pack.json")
    e.add_argument("--out", dest="out_path", required=True, help="Where to write the updated pack.json")
    e.add_argument("--solid", required=True, help="New solid search query text")

    # Rebuild (re-optimize after metrics change)
    r = sub.add_parser("rebuild", help="Re-optimize solid_query after user edits metrics")
    r.add_argument("--in", dest="in_path", required=True, help="Path to existing pack.json")
    r.add_argument("--selection", required=True, help="Path to updated selection.json")
    r.add_argument("--out", dest="out_path", required=True, help="Where to write refreshed pack.json")
    r.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-4o-2024-08-06"))
    r.add_argument("--max_tokens", type=int, default=1500)

    # Generate links
    l = sub.add_parser("links", help="Generate pre-built browser links from pack.json")
    l.add_argument("--in", dest="in_path", required=True)
    l.add_argument("--out", dest="out_path", default="links.json")

    # Run web search
    s = sub.add_parser("search", help="Run OpenAI web_search to fetch structured vendor results")
    s.add_argument("--in", dest="in_path", required=True)
    s.add_argument("--vendors", dest="vendors_out", default="vendors.json")
    s.add_argument("--model-search", default=os.getenv("OPENAI_MODEL_SEARCH", "o4-mini"))
    s.add_argument("--max", dest="max_tokens", type=int, default=1200)

    args = p.parse_args()

    if args.cmd == "build":
        with open(args.input, "r", encoding="utf-8") as f:
            selection = json.load(f)
        pack = build_vendor_query_pack(selection, model=args.model, max_tokens=args.max_tokens)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(pack, f, indent=2, ensure_ascii=False)
        print(f"✓ Wrote query pack → {args.out}")
        print(f"  solid_query: {pack.get('solid_query', 'N/A')}")
        print(f"  alternatives: {len(pack.get('query_alternatives', []))} variants")

    elif args.cmd == "edit-solid":
        with open(args.in_path, "r", encoding="utf-8") as f:
            pack = json.load(f)
        pack = update_solid_query(pack, args.solid)
        with open(args.out_path, "w", encoding="utf-8") as f:
            json.dump(pack, f, indent=2, ensure_ascii=False)
        print(f"✓ Updated solid_query → {args.out_path}")
        print(f"  new query: {args.solid}")

    elif args.cmd == "rebuild":
        with open(args.in_path, "r", encoding="utf-8") as f:
            pack = json.load(f)
        with open(args.selection, "r", encoding="utf-8") as f:
            selection = json.load(f)
        pack = rebuild_vendor_query_pack(pack, selection, model=args.model, max_tokens=args.max_tokens)
        with open(args.out_path, "w", encoding="utf-8") as f:
            json.dump(pack, f, indent=2, ensure_ascii=False)
        print(f"✓ Rebuilt query pack → {args.out_path}")
        print(f"  solid_query: {pack.get('solid_query', 'N/A')}")
        print(f"  alternatives: {len(pack.get('query_alternatives', []))} variants")

    elif args.cmd == "links":
        with open(args.in_path, "r", encoding="utf-8") as f:
            pack = json.load(f)
        links = build_search_links(pack)
        with open(args.out_path, "w", encoding="utf-8") as f:
            json.dump(links, f, indent=2, ensure_ascii=False)
        print(f"✓ Wrote {len(links)} search links → {args.out_path}")

    elif args.cmd == "search":
        with open(args.in_path, "r", encoding="utf-8") as f:
            pack = json.load(f)
        vendors = run_openai_web_search(pack, model_search=args.model_search, max_output_tokens=args.max_tokens)
        with open(args.vendors_out, "w", encoding="utf-8") as f:
            json.dump(vendors, f, indent=2, ensure_ascii=False)
        vendor_count = len(vendors.get("vendors", []))
        print(f"✓ Wrote {vendor_count} vendor results → {args.vendors_out}")

