# api.py
"""
FastAPI endpoint for vendor finder.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import logging

from .models import VendorFinderRequest, VendorFinderResponse
from .service import VendorFinderService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Vendor Finder API", version="1.0.0")

# Initialize service (with mock dependencies for now)
service = VendorFinderService()

@app.post("/vendor_finder", response_model=VendorFinderResponse)
async def vendor_finder(req: VendorFinderRequest):
    """
    Find vendors for a product recommendation.
    
    Args:
        req: Vendor finder request
        
    Returns:
        Vendor finder response
    """
    try:
        logger.info(f"🔍 Vendor finder request: {req.selected_name}")
        logger.info(f"   Query: {req.query}")
        logger.info(f"   Page: {req.page + 1}, Size: {req.page_size}")
        logger.info(f"   Top N: {req.top_n}, Batch: {req.batch_id}")
        
        response = service.handle(req)
        
        logger.info(f"✅ Found {response.summary['found']} vendors, returning {len(response.results)} on page {req.page + 1}")
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Vendor finder error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/vendor_finder/batches")
async def get_batches():
    """Get information about cached batches."""
    try:
        batch_info = service.get_batch_info()
        return JSONResponse({"batches": batch_info})
    except Exception as e:
        logger.error(f"❌ Batch info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/vendor_finder/batches/{batch_id}")
async def clear_batch(batch_id: str):
    """Clear a specific batch from cache."""
    try:
        success = service.clear_batch(batch_id)
        if success:
            return JSONResponse({"message": f"Batch {batch_id} cleared successfully"})
        else:
            raise HTTPException(status_code=500, detail="Failed to clear batch")
    except Exception as e:
        logger.error(f"❌ Clear batch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/vendor_finder/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse({"status": "healthy", "service": "vendor_finder"})

# Legacy endpoint for backward compatibility
@app.post("/api/vendor_finder")
async def legacy_vendor_finder(req: Request):
    """
    Legacy vendor finder endpoint for backward compatibility.
    """
    try:
        body = await req.json()
        
        # Convert legacy format to new format
        legacy_req = VendorFinderRequest(
            query=body.get("query", ""),
            selected_name=body.get("selected_name", ""),
            selected_specs=body.get("selected_specs", []),
            summary=body.get("summary", ""),
            page=body.get("page", 0),
            page_size=body.get("page_size", 20),
            top_n=body.get("top_n", 120),
            batch_id=body.get("batch_id"),
            refresh=body.get("refresh", False)
        )
        
        response = service.handle(legacy_req)
        
        # Convert response to legacy format
        legacy_response = {
            "query": response.query,
            "selected_name": response.selected_name,
            "selected_specs": response.selected_specs,
            "page": response.page,
            "page_size": response.page_size,
            "results": [
                {
                    "vendor_name": v.vendor_name,
                    "product_name": v.product_name,
                    "model": v.model,
                    "sku": v.sku,
                    "price": v.price,
                    "currency": v.currency,
                    "availability": v.availability,
                    "ships_to": v.ships_to,
                    "delivery_window_days": v.delivery_window_days,
                    "purchase_url": str(v.purchase_url),
                    "evidence_urls": [str(url) for url in v.evidence_urls],
                    "sales_email": v.sales_email,
                    "sales_phone": v.sales_phone,
                    "return_policy_url": str(v.return_policy_url) if v.return_policy_url else None,
                    "notes": v.notes,
                    "us_vendor_verification": {
                        "is_us_vendor": v.us_vendor_verification.is_us_vendor,
                        "method": v.us_vendor_verification.method,
                        "business_address": v.us_vendor_verification.business_address
                    },
                    "last_checked_utc": v.last_checked_utc
                }
                for v in response.results
            ],
            "summary": response.summary
        }
        
        return JSONResponse(legacy_response)
        
    except Exception as e:
        logger.error(f"❌ Legacy vendor finder error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
