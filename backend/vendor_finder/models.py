# models.py
"""
Pydantic models for the vendor finder system.
"""

from pydantic import BaseModel, Field, AnyUrl
from typing import List, Optional
from datetime import datetime

class USVerify(BaseModel):
    is_us_vendor: bool
    method: str
    business_address: str = ""

class VendorFinder(BaseModel):
    vendor_name: str
    product_name: str
    model: str
    sku: Optional[str] = None
    price: float
    currency: str = Field("USD", pattern="USD")
    availability: str  # in_stock/backorder/preorder/out_of_stock/unknown
    ships_to: List[str]
    delivery_window_days: int
    purchase_url: AnyUrl
    evidence_urls: List[AnyUrl]
    sales_email: str
    sales_phone: Optional[str] = None
    return_policy_url: Optional[AnyUrl] = None
    notes: Optional[str] = ""
    us_vendor_verification: USVerify
    last_checked_utc: str

class VendorFinderResponse(BaseModel):
    query: str
    selected_name: str
    selected_specs: List[str]
    page: int
    page_size: int
    results: List[VendorFinder]
    summary: dict

class VendorFinderRequest(BaseModel):
    query: str
    selected_name: str
    selected_specs: List[str]
    summary: str
    page: int = 0
    page_size: int = 20
    top_n: int = 120
    batch_id: Optional[str] = None
    refresh: bool = False
