"""Script to preload cache with common queries."""
import asyncio
import sys
from app.cache.redis import cache
from app.services.outreach import outreach_client
from app.config import settings


async def preload_user(username: str):
    """Preload user stats into cache."""
    print(f"Preloading user: {username}")
    data = await outreach_client.get_user_stats(username)
    if data:
        key = f"outreach:user:{username}"
        await cache.set(key, data, settings.user_cache_ttl)
        print(f"  ✓ Cached {username}")
    else:
        print(f"  ✗ Failed to fetch {username}")


async def main(usernames: list[str]):
    """Main preload function."""
    await cache.connect()
    
    try:
        for username in usernames:
            await preload_user(username)
    finally:
        await cache.disconnect()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python preload_cache.py <username1> [username2] ...")
        sys.exit(1)
        
    usernames = sys.argv[1:]
    asyncio.run(main(usernames))
