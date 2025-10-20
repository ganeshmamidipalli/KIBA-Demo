# service.py
"""
Main service orchestrator for vendor finder.
Coordinates pipeline steps and handles caching.
"""

from typing import List, Dict, Optional
from datetime import datetime, timezone

from .models import VendorFinder, VendorFinderResponse, VendorFinderRequest
from .cache import cache_key, get_cached_candidates, set_cached_candidates
from .pipeline.retriever import Retriever
from .pipeline.extractor import Extractor
from .pipeline.validator import Validator
from .pipeline.ranker import Ranker
from .pipeline.paginate import Paginator

class VendorFinderService:
    """Main service orchestrator for vendor finder."""
    
    def __init__(self, web_search=None, http_client=None, parsers=None, contact_scraper=None):
        self.retriever = Retriever(web_search)
        self.extractor = Extractor(http_client, parsers)
        self.validator = Validator(contact_scraper)
        self.ranker = Ranker()
        self.paginator = Paginator()

    def handle(self, req: VendorFinderRequest) -> VendorFinderResponse:
        """
        Handle vendor finder request.
        
        Args:
            req: Vendor finder request
            
        Returns:
            Vendor finder response
        """
        # Generate cache key
        key = cache_key(req.dict(), req.batch_id)
        
        # Check cache first (unless refresh requested)
        if not req.refresh:
            cached = get_cached_candidates(key)
            if cached:
                candidates = cached["candidates"]
                return self._respond(req, candidates)
        
        # Retrieve candidate URLs
        print(f"🔍 Retrieving up to {req.top_n} candidate URLs...")
        urls = self.retriever.run(req.query, req.selected_specs, req.top_n)
        print(f"✅ Retrieved {len(urls)} candidate URLs")
        
        # Extract and validate candidates
        print(f"🔍 Extracting and validating {len(urls)} candidates...")
        vetted = []
        
        for i, url in enumerate(urls):
            print(f"  Processing {i+1}/{len(urls)}: {url}")
            
            # Extract data from URL
            candidate = self.extractor.run(url)
            if not candidate:
                print(f"    ❌ Extraction failed")
                continue
            
            # Validate candidate
            validated = self.validator.run(candidate, req.selected_specs)
            if not validated:
                print(f"    ❌ Validation failed")
                continue
            
            vetted.append(validated)
            print(f"    ✅ Validated: {validated.get('vendor_name', 'Unknown')}")
        
        print(f"✅ Validated {len(vetted)} candidates")
        
        # Rank candidates
        print(f"🔍 Ranking {len(vetted)} candidates...")
        ranked = self.ranker.run(vetted)
        print(f"✅ Ranked candidates")
        
        # Cache results
        print(f"💾 Caching {len(ranked)} candidates...")
        set_cached_candidates(key, ranked)
        print(f"✅ Cached candidates")
        
        return self._respond(req, ranked)

    def _respond(self, req: VendorFinderRequest, all_candidates: List[Dict]) -> VendorFinderResponse:
        """
        Create response from request and candidates.
        
        Args:
            req: Original request
            all_candidates: All validated candidates
            
        Returns:
            Vendor finder response
        """
        # Paginate results
        page_items = self.paginator.run(all_candidates, req.page, req.page_size)
        
        # Convert to VendorFinder objects
        results = []
        for item in page_items:
            try:
                # Ensure all required fields are present
                vendor_data = self._ensure_required_fields(item)
                vendor = VendorFinder(**vendor_data)
                results.append(vendor)
            except Exception as e:
                print(f"Error creating VendorFinder object: {e}")
                continue
        
        # Create summary
        summary = {
            "found": len(all_candidates),
            "missing_fields_count": sum(
                1 for item in page_items 
                if not item.get("sales_email") or item.get("sales_email") == "webform"
            ),
            "notes": f"US-only + link-valid. Cached list length={len(all_candidates)}. top_n={req.top_n} applied.",
            "pagination": self.paginator.get_pagination_info(
                len(all_candidates), req.page, req.page_size
            )
        }
        
        return VendorFinderResponse(
            query=req.query,
            selected_name=req.selected_name,
            selected_specs=req.selected_specs,
            page=req.page,
            page_size=req.page_size,
            results=results,
            summary=summary
        )

    def _ensure_required_fields(self, item: Dict) -> Dict:
        """Ensure all required fields are present in vendor data."""
        # Set defaults for required fields
        defaults = {
            "vendor_name": "Unknown Vendor",
            "product_name": "Unknown Product",
            "model": "Unknown Model",
            "sku": None,
            "price": 0.0,
            "currency": "USD",
            "availability": "unknown",
            "ships_to": ["USA"],
            "delivery_window_days": 7,
            "purchase_url": "",
            "evidence_urls": [],
            "sales_email": "webform",
            "sales_phone": None,
            "return_policy_url": None,
            "notes": "",
            "us_vendor_verification": {
                "is_us_vendor": True,
                "method": "domain_tld",
                "business_address": ""
            },
            "last_checked_utc": datetime.now(timezone.utc).isoformat()
        }
        
        # Merge with defaults
        result = {**defaults, **item}
        
        # Ensure evidence_urls is a list
        if not isinstance(result["evidence_urls"], list):
            result["evidence_urls"] = [result["evidence_urls"]] if result["evidence_urls"] else []
        
        # Ensure ships_to is a list
        if not isinstance(result["ships_to"], list):
            result["ships_to"] = [result["ships_to"]] if result["ships_to"] else ["USA"]
        
        return result

    def get_batch_info(self) -> Dict[str, any]:
        """Get information about cached batches."""
        from .cache import get_batch_info
        return get_batch_info()

    def clear_batch(self, batch_id: str) -> bool:
        """Clear a specific batch from cache."""
        from .cache import clear_batch_cache
        try:
            clear_batch_cache(batch_id)
            return True
        except Exception as e:
            print(f"Error clearing batch {batch_id}: {e}")
            return False
