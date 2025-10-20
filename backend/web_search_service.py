# web_search_service.py
"""
Web search service with OpenAI o4-mini model and rate limit handling.
"""

import os
import time
import logging
from typing import Dict, Any
from openai import OpenAI

logger = logging.getLogger(__name__)

def search_products_web(
    client: OpenAI,
    query: str,
    max_retries: int = 3,
    **kwargs
) -> Dict[str, Any]:
    """
    Web search using OpenAI o4-mini with web_search tool.
    Includes automatic rate limit retry with exponential backoff.
    
    Args:
        client: OpenAI client instance
        query: Search query/prompt
        max_retries: Maximum number of retry attempts (default: 3)
    
    Returns:
        Dict with output_text and status
    """
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Web search attempt {attempt + 1}/{max_retries}")
            
            # Use the new responses API with web_search tool
            resp = client.responses.create(
                model="o4-mini",
                reasoning={"effort": "medium"},  # low | medium | high
                input=query,
                tools=[{"type": "web_search"}],
                tool_choice="auto"
            )
            
            # Success - return the output
            output_text = resp.output_text
            logger.info(f"Web search successful, output length: {len(output_text)} chars")
            
            return {
                "output_text": output_text,
                "status": "ok"
            }
            
        except Exception as e:
            error_str = str(e)
            
            # Check if it's a rate limit error
            if "rate_limit_exceeded" in error_str or "429" in error_str:
                # Extract wait time if available
                wait_time = _extract_wait_time(error_str)
                
                if attempt < max_retries - 1:
                    # Exponential backoff: 2^attempt seconds (2, 4, 8...)
                    backoff = max(wait_time, 2 ** attempt)
                    logger.warning(f"Rate limit hit. Retrying in {backoff}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(backoff)
                    continue
                else:
                    # Last attempt failed
                    logger.error(f"Rate limit exceeded after {max_retries} attempts")
                    return {
                        "output_text": f"Rate limit exceeded. Please try again in a few seconds.\n\nDetails: {error_str}",
                        "status": "rate_limit_error"
                    }
            else:
                # Other error - return immediately
                logger.error(f"Web search error: {error_str}")
                return {
                    "output_text": f"Error: {error_str}",
                    "status": "error"
                }
    
    # Should never reach here, but just in case
    return {
        "output_text": "Search failed after maximum retries.",
        "status": "error"
    }


def _extract_wait_time(error_message: str) -> float:
    """
    Extract wait time from rate limit error message.
    Example: "Please try again in 3.984s"
    """
    import re
    match = re.search(r"try again in ([\d.]+)s", error_message)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    return 0.0


def get_fallback_web_search() -> Dict[str, Any]:
    """Fallback when API unavailable."""
    return {
        "output_text": "OpenAI API key not configured.",
        "status": "error"
    }
