# pipeline/retriever.py
"""
URL retrieval module for vendor finder.
Returns up to top_n candidate URLs based on query + specs.
"""

from typing import List, Dict, Any
import re

class Retriever:
    """Returns up to top_n candidate URLs based on query + specs."""
    
    def __init__(self, web_search_service=None):
        self.web_search = web_search_service

    def run(self, query: str, selected_specs: List[str], top_n: int) -> List[str]:
        """
        Retrieve candidate URLs for vendor search.
        
        Args:
            query: Search query string
            selected_specs: List of specification requirements
            top_n: Maximum number of candidates to retrieve
            
        Returns:
            List of candidate URLs
        """
        # For now, simulate web search results
        # In production, this would integrate with actual web search service
        urls = self._simulate_web_search(query, selected_specs, top_n)
        
        # Filter to only PDP-like URLs
        pdp_urls = [url for url in urls if self._looks_like_pdp(url)]
        
        # Return up to top_n URLs
        return pdp_urls[:top_n]

    def _simulate_web_search(self, query: str, selected_specs: List[str], top_n: int) -> List[str]:
        """Generate realistic product URLs for testing with real data."""
        # For now, return some realistic product URLs that we know exist
        # In production, this would use a real search API or web scraping service
        
        product_urls = []
        
        # Sonos One URLs (if query contains "sonos")
        if "sonos" in query.lower():
            product_urls = [
                "https://www.amazon.com/Sonos-One-Smart-Speaker-Alexa/dp/B075M8Q6B6",
                "https://www.bestbuy.com/site/sonos-one-gen-2-smart-speaker-with-alexa-built-in-white/6336598.p",
                "https://www.bhphotovideo.com/c/product/1433317-REG/sonos_one_black_smart_speaker.html",
                "https://www.adorama.com/sononeblk.html",
                "https://www.cdw.com/product/sonos-one-smart-speaker/5430000"
            ]
        # NVIDIA RTX 4090 URLs
        elif "rtx" in query.lower() and "4090" in query.lower():
            product_urls = [
                "https://www.amazon.com/NVIDIA-GeForce-RTX-4090-Founders/dp/B0BG5VYQ3G",
                "https://www.bestbuy.com/site/nvidia-geforce-rtx-4090-24gb-gddr6x-graphics-card/6521430.p",
                "https://www.newegg.com/p/pl?d=rtx+4090",
                "https://www.bhphotovideo.com/c/search?Ntt=rtx+4090",
                "https://www.microcenter.com/search/search_results.aspx?Ntt=rtx+4090"
            ]
        # Amazon Echo Studio URLs
        elif "echo" in query.lower() and "studio" in query.lower():
            product_urls = [
                "https://www.amazon.com/Echo-Studio-High-fidelity-speaker-3D-audio/dp/B07FZ8S74R",
                "https://www.bestbuy.com/site/amazon-echo-studio-smart-speaker-with-alexa-charcoal/6356200.p",
                "https://www.bhphotovideo.com/c/product/1505000-REG/amazon_echo_studio_smart_speaker.html"
            ]
        # Google Nest Audio URLs
        elif "nest" in query.lower() and "audio" in query.lower():
            product_urls = [
                "https://www.amazon.com/Google-Nest-Audio-Smart-Speaker/dp/B08C7KG5LP",
                "https://www.bestbuy.com/site/google-nest-audio-smart-speaker-with-google-assistant-chalk/6418599.p",
                "https://www.bhphotovideo.com/c/product/1595000-REG/google_nest_audio_smart_speaker.html"
            ]
        else:
            # Generic fallback URLs
            product_urls = [
                "https://www.amazon.com/s?k=" + query.replace(" ", "+"),
                "https://www.bestbuy.com/site/searchpage.jsp?st=" + query.replace(" ", "+"),
                "https://www.newegg.com/p/pl?d=" + query.replace(" ", "+"),
                "https://www.bhphotovideo.com/c/search?Ntt=" + query.replace(" ", "+"),
                "https://www.microcenter.com/search/search_results.aspx?Ntt=" + query.replace(" ", "+")
            ]
        
        return product_urls[:top_n]

    def _extract_product_id(self, query: str) -> str:
        """Extract a product ID from the query for URL generation."""
        # Simple extraction - in production this would be more sophisticated
        query_lower = query.lower()
        if "rtx" in query_lower and "4090" in query_lower:
            return "rtx-4090-founders-edition"
        elif "sonos" in query_lower and "one" in query_lower:
            return "sonos-one"
        elif "nest" in query_lower and "audio" in query_lower:
            return "google-nest-audio"
        elif "echo" in query_lower and "studio" in query_lower:
            return "amazon-echo-studio"
        else:
            return "product-12345"

    @staticmethod
    def _looks_like_pdp(url: str) -> bool:
        """
        Check if URL looks like a product detail page or search page.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL looks like a PDP or search page
        """
        if not url.startswith("https://"):
            return False
            
        # Allow search pages and product pages
        url_lower = url.lower()
        
        # Good patterns for vendor websites
        good_patterns = [
            "cdw.com",
            "bhphotovideo.com", 
            "newegg.com",
            "microcenter.com",
            "insight.com",
            "amazon.com",
            "bestbuy.com",
            "adorama.com",
            "connection.com",
            "zones.com",
            "wwt.com",
            "shi.com",
            "softcat.com",
            "optiv.com",
            "guidepointsecurity.com"
        ]
        
        return any(pattern in url_lower for pattern in good_patterns)

    def _get_vendor_from_url(self, url: str) -> str:
        """Extract vendor name from URL."""
        domain_mapping = {
            "cdw.com": "CDW",
            "bhphotovideo.com": "B&H Photo Video",
            "newegg.com": "Newegg",
            "microcenter.com": "Micro Center",
            "insight.com": "Insight",
            "amazon.com": "Amazon",
            "bestbuy.com": "Best Buy",
            "adorama.com": "Adorama",
            "connection.com": "Connection",
            "zones.com": "Zones",
            "wwt.com": "WWT",
            "shi.com": "SHI",
            "softcat.com": "Softcat",
            "optiv.com": "Optiv",
            "guidepointsecurity.com": "GuidePoint Security"
        }
        
        for domain, vendor in domain_mapping.items():
            if domain in url:
                return vendor
        
        return "Unknown Vendor"
