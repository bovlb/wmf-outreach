"""Health check endpoint."""
import time
from fastapi import APIRouter
from app.models.schemas import HealthResponse
from app.cache.redis import cache

router = APIRouter()

# Track startup time
START_TIME = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns basic system status and Redis connectivity.
    """
    redis_connected = False
    
    if cache.redis:
        try:
            await cache.redis.ping()
            redis_connected = True
        except Exception:
            pass
            
    return HealthResponse(
        status="ok" if redis_connected else "degraded",
        redis_connected=redis_connected,
        uptime_seconds=time.time() - START_TIME,
    )
