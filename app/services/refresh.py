"""Background refresh logic for stale-while-revalidate."""
import asyncio
from typing import Callable, Any, Optional
from app.cache.redis import cache


class RefreshManager:
    """Manages background refresh tasks for stale cache entries."""
    
    def __init__(self):
        """Initialize refresh manager."""
        self.pending_refreshes = set()
        
    def schedule_refresh(
        self,
        key: str,
        refresh_func: Callable[[], Any],
        ttl: int,
    ):
        """
        Schedule a background refresh for a stale cache entry.
        
        Args:
            key: Cache key to refresh
            refresh_func: Async function to fetch fresh data
            ttl: TTL for the refreshed data
        """
        # Avoid duplicate refresh tasks
        if key in self.pending_refreshes:
            return
            
        self.pending_refreshes.add(key)
        asyncio.create_task(self._do_refresh(key, refresh_func, ttl))
        
    async def _do_refresh(
        self,
        key: str,
        refresh_func: Callable[[], Any],
        ttl: int,
    ):
        """
        Execute background refresh.
        
        Args:
            key: Cache key to refresh
            refresh_func: Async function to fetch fresh data
            ttl: TTL for the refreshed data
        """
        try:
            fresh_data = await refresh_func()
            if fresh_data is not None:
                await cache.set(key, fresh_data, ttl)
        except Exception as e:
            print(f"Error refreshing cache key {key}: {e}")
        finally:
            self.pending_refreshes.discard(key)


# Global refresh manager
refresh_manager = RefreshManager()
