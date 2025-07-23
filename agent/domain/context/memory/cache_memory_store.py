from typing import Dict, Any, Optional
import asyncio
from datetime import datetime, timedelta
import json


class CacheMemoryStore:
    """In-memory cache store with TTL support"""
    
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        
    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Set a value in cache with TTL"""
        
        async with self._lock:
            expires_at = datetime.utcnow() + timedelta(seconds=ttl)
            
            self.cache[key] = {
                "value": value,
                "expires_at": expires_at
            }
            
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        
        async with self._lock:
            if key not in self.cache:
                return None
                
            entry = self.cache[key]
            
            # Check if expired
            if datetime.utcnow() > entry["expires_at"]:
                del self.cache[key]
                return None
                
            return entry["value"]
            
    async def delete(self, key: str) -> bool:
        """Delete a key from cache"""
        
        async with self._lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
            
    async def clear_expired(self) -> int:
        """Clear expired entries and return count"""
        
        async with self._lock:
            now = datetime.utcnow()
            expired_keys = [
                key for key, entry in self.cache.items()
                if now > entry["expires_at"]
            ]
            
            for key in expired_keys:
                del self.cache[key]
                
            return len(expired_keys)
            
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        
        async with self._lock:
            now = datetime.utcnow()
            active_count = sum(
                1 for entry in self.cache.values()
                if now <= entry["expires_at"]
            )
            
            return {
                "total_keys": len(self.cache),
                "active_keys": active_count,
                "expired_keys": len(self.cache) - active_count
            }