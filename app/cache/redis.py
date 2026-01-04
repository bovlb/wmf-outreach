"""Redis cache implementation with stale-while-revalidate pattern."""
import json
import time
from typing import Optional, Any, Dict
import redis.asyncio as redis
from app.config import settings


class RedisCache:
    """Redis-based cache with stale-while-revalidate support."""
    
    def __init__(self):
        """Initialize Redis connection."""
        self.redis: Optional[redis.Redis] = None
        self.key_prefix = settings.redis_key_prefix
        
    def _make_key(self, key: str) -> str:
        """Add prefix to key for multi-tenant isolation."""
        return f"{self.key_prefix}{key}"
        
    async def connect(self):
        """Establish Redis connection."""
        self.redis = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            decode_responses=True,
        )
        
    async def disconnect(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            
    async def get(self, key: str, max_age: int) -> tuple[Optional[Any], bool]:
        """
        Get cached value with stale-while-revalidate semantics.
        
        Args:
            key: Cache key (will be prefixed automatically)
            max_age: Maximum age in seconds before data is considered fresh
            
        Returns:
            Tuple of (data, needs_refresh)
            - data: The cached data (or None if not found)
            - needs_refresh: True if data is stale but within grace period
        """
        if not self.redis:
            return None, False
            
        prefixed_key = self._make_key(key)
        raw = await self.redis.get(prefixed_key)
        if not raw:
            return None, False
            
        try:
            cached = json.loads(raw)
            fetched_at = cached.get("fetched_at", 0)
            data = cached.get("data")
            
            now = time.time()
            age = now - fetched_at
            
            # Within fresh period
            if age <= max_age:
                return data, False
                
            # Within stale grace period
            stale_max_age = max_age * settings.stale_ttl_multiplier
            if age <= stale_max_age:
                return data, True
                
            # Too old, treat as miss
            return None, False
            
        except (json.JSONDecodeError, KeyError):
            return None, False
            
    async def set(self, key: str, data: Any, ttl: int):
        """
        Store data in cache with timestamp.
        
        Args:
            key: Cache key (will be prefixed automatically)
            data: Data to cache
            ttl: Time to live in seconds
        """
        if not self.redis:
            return
            
        cached = {
            "fetched_at": time.time(),
            "data": data,
        }
        
        # Set expiry to stale grace period
        expire = int(ttl * settings.stale_ttl_multiplier)
        prefixed_key = self._make_key(key)
        await self.redis.setex(prefixed_key, expire, json.dumps(cached))
        
    async def delete(self, key: str):
        """Delete a cache entry."""
        if self.redis:
            prefixed_key = self._make_key(key)
            await self.redis.delete(prefixed_key)
            
    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        if not self.redis:
            return False
        prefixed_key = self._make_key(key)
        return await self.redis.exists(prefixed_key) > 0


# Global cache instance
cache = RedisCache()


def make_key(*parts: str) -> str:
    """
    Create a namespaced cache key.
    
    Args:
        *parts: Key components
        
    Returns:
        Formatted cache key
    """
    return "outreach:" + ":".join(parts)
