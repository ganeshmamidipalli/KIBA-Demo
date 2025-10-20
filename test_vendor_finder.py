#!/usr/bin/env python3
"""
Test script for vendor finder pipeline debugging
"""

import sys
import os
sys.path.append('backend')

from vendor_finder.pipeline.retriever import Retriever
from vendor_finder.pipeline.extractor import Extractor
from vendor_finder.pipeline.validator import Validator
from vendor_finder.pipeline.ranker import Ranker
from vendor_finder.pipeline.paginate import Paginator

def test_pipeline():
    print("🔍 TESTING VENDOR FINDER PIPELINE")
    print("=" * 50)
    
    # Initialize components
    retriever = Retriever()
    extractor = Extractor()
    validator = Validator()
    ranker = Ranker()
    paginator = Paginator()
    
    # Test data
    query = "Sonos One"
    selected_specs = ["Voice control", "Multi-room capability"]
    top_n = 10
    
    print(f"📤 Query: {query}")
    print(f"📤 Specs: {selected_specs}")
    print(f"📤 Top N: {top_n}")
    
    # Step 1: Retrieve URLs
    print("\n🔍 Step 1: Retrieving URLs...")
    urls = retriever.run(query, selected_specs, top_n)
    print(f"✅ Retrieved {len(urls)} URLs")
    for i, url in enumerate(urls[:3]):  # Show first 3
        print(f"   {i+1}. {url}")
    
    # Step 2: Extract data from URLs
    print("\n🔍 Step 2: Extracting data...")
    candidates = []
    for i, url in enumerate(urls):
        print(f"  Processing {i+1}/{len(urls)}: {url}")
        candidate = extractor.run(url)
        if candidate:
            print(f"    ✅ Extracted: {candidate.get('vendor_name', 'Unknown')}")
            candidates.append(candidate)
        else:
            print(f"    ❌ Extraction failed")
    
    print(f"✅ Extracted {len(candidates)} candidates")
    
    # Step 3: Validate candidates
    print("\n🔍 Step 3: Validating candidates...")
    validated = []
    for i, candidate in enumerate(candidates):
        print(f"  Validating {i+1}/{len(candidates)}: {candidate.get('vendor_name', 'Unknown')}")
        validated_candidate = validator.run(candidate, selected_specs)
        if validated_candidate:
            print(f"    ✅ Validated")
            validated.append(validated_candidate)
        else:
            print(f"    ❌ Validation failed")
    
    print(f"✅ Validated {len(validated)} candidates")
    
    # Step 4: Rank candidates
    print("\n🔍 Step 4: Ranking candidates...")
    ranked = ranker.run(validated)
    print(f"✅ Ranked {len(ranked)} candidates")
    
    # Step 5: Paginate
    print("\n🔍 Step 5: Paginating...")
    page_size = 5
    page = 0
    page_results = paginator.run(ranked, page, page_size)
    print(f"✅ Paginated: {len(page_results)} results on page {page + 1}")
    
    # Show results
    print("\n🏪 FINAL RESULTS:")
    if page_results:
        for i, vendor in enumerate(page_results):
            print(f"\n{i+1}. {vendor['vendor_name']}")
            print(f"   Product: {vendor['product_name']}")
            print(f"   Price: ${vendor['price']:.2f}")
            print(f"   Availability: {vendor['availability']}")
            print(f"   Delivery: {vendor['delivery_window_days']} days")
            print(f"   Sales Email: {vendor['sales_email']}")
            print(f"   US Verified: {vendor['us_vendor_verification']['is_us_vendor']}")
    else:
        print("❌ No results found")
    
    print("\n🎉 Pipeline test complete!")

if __name__ == "__main__":
    test_pipeline()
