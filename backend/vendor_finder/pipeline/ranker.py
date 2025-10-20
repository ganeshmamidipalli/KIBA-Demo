# pipeline/ranker.py
"""
Ranking module for vendor finder.
Ranks vendors by stock status, price, delivery time, and manufacturer proximity.
"""

from typing import List, Dict

class Ranker:
    """Ranks vendors by multiple criteria."""
    
    def run(self, candidates: List[Dict]) -> List[Dict]:
        """
        Rank candidates by multiple criteria.
        
        Args:
            candidates: List of vendor candidates
            
        Returns:
            Ranked list of candidates
        """
        def ranking_key(candidate):
            """
            Generate ranking key for sorting.
            Lower values = higher priority.
            """
            # 1. Stock status (in_stock = 0, others = 1)
            stock_priority = 0 if candidate.get("availability") == "in_stock" else 1
            
            # 2. Price (lower is better)
            price = float(candidate.get("price", 0))
            
            # 3. Delivery time (shorter is better)
            delivery_days = candidate.get("delivery_window_days", 999)
            
            # 4. Manufacturer proximity (manufacturer = 0, others = 1)
            notes = candidate.get("notes", "").lower()
            is_manufacturer = any(keyword in notes for keyword in [
                "manufacturer", "mfr", "direct", "official", "oem"
            ])
            mfr_priority = 0 if is_manufacturer else 1
            
            # 5. Vendor reputation (known vendors = 0, others = 1)
            vendor_name = candidate.get("vendor_name", "").lower()
            known_vendors = [
                "cdw", "bh photo", "newegg", "micro center", "insight",
                "amazon", "best buy", "adorama", "connection", "zones",
                "wwt", "shi", "softcat", "optiv", "guidepoint"
            ]
            reputation_priority = 0 if any(known in vendor_name for known in known_vendors) else 1
            
            # 6. Sales contact quality (direct email = 0, webform = 1)
            sales_email = candidate.get("sales_email", "")
            contact_priority = 0 if sales_email and sales_email != "webform" else 1
            
            return (
                stock_priority,      # In stock first
                price,               # Lower price first
                delivery_days,       # Faster delivery first
                mfr_priority,        # Manufacturer first
                reputation_priority, # Known vendors first
                contact_priority     # Direct contact first
            )
        
        return sorted(candidates, key=ranking_key)

    def _calculate_stock_score(self, candidate: Dict) -> int:
        """Calculate stock availability score."""
        availability = candidate.get("availability", "unknown")
        stock_scores = {
            "in_stock": 0,
            "backorder": 1,
            "preorder": 2,
            "out_of_stock": 3,
            "unknown": 4
        }
        return stock_scores.get(availability, 4)

    def _calculate_price_score(self, candidate: Dict) -> float:
        """Calculate price score (lower is better)."""
        price = float(candidate.get("price", 0))
        return price if price > 0 else float('inf')

    def _calculate_delivery_score(self, candidate: Dict) -> int:
        """Calculate delivery time score (lower is better)."""
        delivery_days = candidate.get("delivery_window_days", 999)
        return delivery_days

    def _calculate_manufacturer_score(self, candidate: Dict) -> int:
        """Calculate manufacturer proximity score."""
        notes = candidate.get("notes", "").lower()
        vendor_name = candidate.get("vendor_name", "").lower()
        
        # Check for manufacturer indicators
        mfr_indicators = [
            "manufacturer", "mfr", "direct", "official", "oem",
            "factory", "headquarters", "corporate"
        ]
        
        if any(indicator in notes for indicator in mfr_indicators):
            return 0
        
        if any(indicator in vendor_name for indicator in mfr_indicators):
            return 0
        
        return 1

    def _calculate_reputation_score(self, candidate: Dict) -> int:
        """Calculate vendor reputation score."""
        vendor_name = candidate.get("vendor_name", "").lower()
        
        # Tier 1: Premium enterprise vendors
        tier1_vendors = ["cdw", "insight", "wwt", "shi", "softcat", "optiv", "guidepoint"]
        if any(vendor in vendor_name for vendor in tier1_vendors):
            return 0
        
        # Tier 2: Well-known retailers
        tier2_vendors = ["bh photo", "newegg", "micro center", "amazon", "best buy", "adorama"]
        if any(vendor in vendor_name for vendor in tier2_vendors):
            return 1
        
        # Tier 3: Other vendors
        return 2

    def _calculate_contact_score(self, candidate: Dict) -> int:
        """Calculate sales contact quality score."""
        sales_email = candidate.get("sales_email", "")
        
        if not sales_email:
            return 2
        
        if sales_email == "webform":
            return 1
        
        # Direct email contact
        return 0

    def rank_by_criteria(self, candidates: List[Dict], criteria: List[str]) -> List[Dict]:
        """
        Rank candidates by specific criteria.
        
        Args:
            candidates: List of vendor candidates
            criteria: List of criteria to rank by
            
        Returns:
            Ranked list of candidates
        """
        def multi_criteria_key(candidate):
            scores = []
            
            for criterion in criteria:
                if criterion == "stock":
                    scores.append(self._calculate_stock_score(candidate))
                elif criterion == "price":
                    scores.append(self._calculate_price_score(candidate))
                elif criterion == "delivery":
                    scores.append(self._calculate_delivery_score(candidate))
                elif criterion == "manufacturer":
                    scores.append(self._calculate_manufacturer_score(candidate))
                elif criterion == "reputation":
                    scores.append(self._calculate_reputation_score(candidate))
                elif criterion == "contact":
                    scores.append(self._calculate_contact_score(candidate))
            
            return tuple(scores)
        
        return sorted(candidates, key=multi_criteria_key)
