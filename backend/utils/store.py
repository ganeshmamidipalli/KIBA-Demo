"""
In-memory session store for KPA One-Flow.
Handles temporary session storage with TTL.
"""

import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class SessionStore:
    """In-memory session store with TTL support."""
    
    def __init__(self, ttl_seconds: int = 1800):  # 30 minutes default
        self.ttl = ttl_seconds
        self._data: Dict[str, Dict[str, Any]] = {}
    
    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data by ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data or None if not found/expired
        """
        if not session_id:
            return None
            
        row = self._data.get(session_id)
        if not row:
            return None
            
        # Check TTL
        if self.ttl and time.time() - row.get("ts", 0) > self.ttl:
            logger.info(f"Session {session_id} expired, removing")
            del self._data[session_id]
            return None
            
        return row
    
    def set(self, session_id: str, value: Dict[str, Any]) -> None:
        """
        Set session data.
        
        Args:
            session_id: Session identifier
            value: Session data to store
        """
        if not session_id:
            return
            
        value["ts"] = value.get("ts") or time.time()
        self._data[session_id] = value
        logger.info(f"Session {session_id} stored with {len(value)} fields")
    
    def delete(self, session_id: str) -> None:
        """
        Delete session data.
        
        Args:
            session_id: Session identifier
        """
        if session_id in self._data:
            del self._data[session_id]
            logger.info(f"Session {session_id} deleted")
    
    def cleanup_expired(self) -> int:
        """
        Clean up expired sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        if not self.ttl:
            return 0
            
        current_time = time.time()
        expired_keys = [
            key for key, value in self._data.items()
            if current_time - value.get("ts", 0) > self.ttl
        ]
        
        for key in expired_keys:
            del self._data[key]
            
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired sessions")
            
        return len(expired_keys)
    
    def size(self) -> int:
        """Get current number of active sessions."""
        return len(self._data)
