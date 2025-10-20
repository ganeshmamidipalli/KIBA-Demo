# pipeline/paginate.py
"""
Pagination module for vendor finder.
Handles page slicing and pagination metadata.
"""

from typing import List, Dict, Tuple

class Paginator:
    """Handles pagination of vendor results."""
    
    def run(self, items: List[Dict], page: int, page_size: int) -> List[Dict]:
        """
        Paginate items based on page and page_size.
        
        Args:
            items: List of items to paginate
            page: Page number (0-based)
            page_size: Number of items per page
            
        Returns:
            List of items for the requested page
        """
        if not items:
            return []
        
        start = page * page_size
        end = start + page_size
        
        return items[start:end]

    def get_pagination_info(self, total_items: int, page: int, page_size: int) -> Dict:
        """
        Get pagination metadata.
        
        Args:
            total_items: Total number of items
            page: Current page (0-based)
            page_size: Items per page
            
        Returns:
            Dictionary with pagination information
        """
        total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0
        has_next = page < total_pages - 1
        has_prev = page > 0
        
        return {
            "total_items": total_items,
            "total_pages": total_pages,
            "current_page": page + 1,  # Convert to 1-based for display
            "page_size": page_size,
            "has_next": has_next,
            "has_prev": has_prev,
            "start_item": page * page_size + 1 if total_items > 0 else 0,
            "end_item": min((page + 1) * page_size, total_items)
        }

    def validate_pagination(self, page: int, page_size: int, max_page_size: int = 50) -> Tuple[int, int]:
        """
        Validate and normalize pagination parameters.
        
        Args:
            page: Page number (0-based)
            page_size: Items per page
            max_page_size: Maximum allowed page size
            
        Returns:
            Tuple of (validated_page, validated_page_size)
        """
        # Ensure page is non-negative
        validated_page = max(0, page)
        
        # Ensure page_size is within bounds
        validated_page_size = max(1, min(page_size, max_page_size))
        
        return validated_page, validated_page_size

    def get_page_range(self, current_page: int, total_pages: int, max_pages: int = 10) -> List[int]:
        """
        Get a range of page numbers to display in pagination UI.
        
        Args:
            current_page: Current page (1-based)
            total_pages: Total number of pages
            max_pages: Maximum number of page numbers to show
            
        Returns:
            List of page numbers to display
        """
        if total_pages <= 1:
            return [1] if total_pages == 1 else []
        
        # Calculate start and end of range
        half_range = max_pages // 2
        start = max(1, current_page - half_range)
        end = min(total_pages, start + max_pages - 1)
        
        # Adjust start if we're near the end
        if end - start + 1 < max_pages:
            start = max(1, end - max_pages + 1)
        
        return list(range(start, end + 1))

    def get_skip_take(self, page: int, page_size: int) -> Tuple[int, int]:
        """
        Get skip and take values for database queries.
        
        Args:
            page: Page number (0-based)
            page_size: Items per page
            
        Returns:
            Tuple of (skip, take)
        """
        skip = page * page_size
        take = page_size
        return skip, take
