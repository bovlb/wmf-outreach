"""User-related API endpoints."""
from fastapi import APIRouter, HTTPException
from app.models.schemas import UserStatsResponse, CourseEnrollment
from app.services.outreach import outreach_client
from app.services.refresh import refresh_manager
from app.cache.redis import cache, make_key
from app.config import settings

router = APIRouter()


@router.get("/users/{username}", response_model=UserStatsResponse)
async def get_user_courses(username: str):
    """
    Get courses for a given username.
    
    Returns simplified course enrollment information,
    indicating whether the user is a facilitator or participant.
    """
    cache_key = make_key("user", username)
    
    # Try cache first with stale-while-revalidate
    cached_data, needs_refresh = await cache.get(
        cache_key,
        settings.user_cache_ttl,
    )
    
    if cached_data is not None:
        # Schedule background refresh if stale
        if needs_refresh:
            refresh_manager.schedule_refresh(
                cache_key,
                lambda: outreach_client.get_user_stats(username),
                settings.user_cache_ttl,
            )
        return _transform_user_stats(username, cached_data)
        
    # Cache miss - fetch fresh data
    raw_data = await outreach_client.get_user_stats(username)
    if raw_data is None:
        raise HTTPException(status_code=404, detail="User not found or API error")
        
    # Cache the response
    await cache.set(cache_key, raw_data, settings.user_cache_ttl)
    
    return _transform_user_stats(username, raw_data)


def _transform_user_stats(username: str, raw_data: dict) -> UserStatsResponse:
    """
    Transform raw user stats into simplified response.
    
    Args:
        username: Username being queried
        raw_data: Raw API response
        
    Returns:
        Simplified user stats response
    """
    courses_details = raw_data.get("courses_details", [])
    courses = [CourseEnrollment(**course) for course in courses_details]
    
    # Determine role status
    # role >= 1 means facilitator/instructor
    is_instructor = any(
        c.user_role != "student" or c.user_role == "instructor" 
        for c in courses
    )
    is_student = any(c.user_role == "student" for c in courses)
    
    return UserStatsResponse(
        username=username,
        courses=courses,
        is_instructor=is_instructor,
        is_student=is_student,
        max_project=raw_data.get("max_project"),
    )
