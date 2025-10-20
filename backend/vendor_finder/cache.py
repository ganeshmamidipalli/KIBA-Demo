# cache.py
"""
Redis-based caching for vendor finder results with batch management.
"""

import json
import hashlib
import redis
from typing import Any, Dict, Optional

# Redis connection
r = redis.Redis(host="localhost", port=6379, decode_responses=True)
TTL_SECONDS = 60 * 60  # 1 hour

def cache_key(payload: Dict[str, Any], batch_id: Optional[str] = None) -> str:
    """Generate cache key for vendor finder request."""
    base = {
        "query": payload["query"],
        "selected_name": payload["selected_name"],
        "selected_specs": payload["selected_specs"],
        "summary": payload["summary"],
        "batch_id": batch_id or "default"
    }
    s = json.dumps(base, sort_keys=True)
    return "vf:" + hashlib.sha256(s.encode()).hexdigest()

def get_cached_candidates(key: str) -> Optional[Dict]:
    """Retrieve cached candidates from Redis."""
    try:
        cached = r.get(key)
        return json.loads(cached) if cached else None
    except Exception as e:
        print(f"Cache get error: {e}")
        return None

def set_cached_candidates(key: str, candidates: list) -> None:
    """Store candidates in Redis cache."""
    try:
        r.set(key, json.dumps({"candidates": candidates}), ex=TTL_SECONDS)
    except Exception as e:
        print(f"Cache set error: {e}")

def clear_batch_cache(batch_id: str) -> None:
    """Clear all cache entries for a specific batch."""
    try:
        pattern = f"vf:*batch_id\":\"{batch_id}\"*"
        keys = r.keys(pattern)
        if keys:
            r.delete(*keys)
    except Exception as e:
        print(f"Cache clear error: {e}")

def get_batch_info() -> Dict[str, Any]:
    """Get information about cached batches."""
    try:
        keys = r.keys("vf:*")
        batches = {}
        for key in keys:
            try:
                data = json.loads(r.get(key))
                batch_id = data.get("batch_id", "default")
                if batch_id not in batches:
                    batches[batch_id] = {
                        "candidate_count": len(data.get("candidates", [])),
                        "created_at": data.get("created_at", "unknown")
                    }
            except:
                continue
        return batches
    except Exception as e:
        print(f"Batch info error: {e}")
        return {}
