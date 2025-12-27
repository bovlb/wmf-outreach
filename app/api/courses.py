"""Course-related API endpoints."""
from fastapi import APIRouter, HTTPException
from app.models.schemas import CourseUsersResponse, CourseDetails, CourseUser
from app.services.outreach import outreach_client
from app.services.refresh import refresh_manager
from app.cache.redis import cache, make_key
from app.config import settings

router = APIRouter()


@router.get("/courses/{school}/{title_slug}/users", response_model=CourseUsersResponse)
async def get_course_users(school: str, title_slug: str):
    """
    Get course users/roster with role separation.
    
    Returns facilitators (role >= 1) and participants (role == 0) separately.
    Handles duplicate enrollments by preferring highest role and latest enrollment.
    """
    slug = f"{school}/{title_slug}"
    cache_key = make_key("course_users", slug)
    
    # Try cache first with stale-while-revalidate
    cached_data, needs_refresh = await cache.get(
        cache_key,
        settings.course_users_cache_ttl,
    )
    
    if cached_data is not None:
        # Schedule background refresh if stale
        if needs_refresh:
            refresh_manager.schedule_refresh(
                cache_key,
                lambda: outreach_client.get_course_users(school, title_slug),
                settings.course_users_cache_ttl,
            )
        return _transform_course_users(slug, cached_data)
        
    # Cache miss - fetch fresh data
    raw_data = await outreach_client.get_course_users(school, title_slug)
    if raw_data is None:
        raise HTTPException(status_code=404, detail="Course not found or API error")
        
    # Cache the response
    await cache.set(cache_key, raw_data, settings.course_users_cache_ttl)
    
    return _transform_course_users(slug, raw_data)


@router.get("/courses/{school}/{title_slug}", response_model=CourseDetails)
async def get_course_details(school: str, title_slug: str):
    """
    Get course details including metadata and timeline.
    
    Useful for determining if a course is currently active.
    """
    slug = f"{school}/{title_slug}"
    cache_key = make_key("course", slug)
    
    # Try cache first with stale-while-revalidate
    cached_data, needs_refresh = await cache.get(
        cache_key,
        settings.course_cache_ttl,
    )
    
    if cached_data is not None:
        # Schedule background refresh if stale
        if needs_refresh:
            refresh_manager.schedule_refresh(
                cache_key,
                lambda: outreach_client.get_course_details(school, title_slug),
                settings.course_cache_ttl,
            )
        return _transform_course_details(cached_data)
        
    # Cache miss - fetch fresh data
    raw_data = await outreach_client.get_course_details(school, title_slug)
    if raw_data is None:
        raise HTTPException(status_code=404, detail="Course not found or API error")
        
    # Cache the response
    await cache.set(cache_key, raw_data, settings.course_cache_ttl)
    
    return _transform_course_details(raw_data)


def _transform_course_users(slug: str, raw_data: dict) -> CourseUsersResponse:
    """
    Transform raw course users into structured response.
    
    Handles duplicate enrollments by keeping the one with highest role
    and latest enrollment date.
    
    Args:
        slug: Course slug
        raw_data: Raw API response
        
    Returns:
        Structured course users response
    """
    users_raw = raw_data.get("course", {}).get("users", [])
    
    # Deduplicate by username, preferring highest role and latest enrollment
    users_by_name = {}
    for user_data in users_raw:
        username = user_data.get("username")
        if not username:
            continue
            
        if username not in users_by_name:
            users_by_name[username] = user_data
        else:
            existing = users_by_name[username]
            # Prefer higher role, then later enrollment
            if (user_data.get("role", 0) > existing.get("role", 0) or
                (user_data.get("role", 0) == existing.get("role", 0) and
                 user_data.get("enrolled_at", "") > existing.get("enrolled_at", ""))):
                users_by_name[username] = user_data
    
    # Parse into CourseUser objects
    all_users = [CourseUser(**data) for data in users_by_name.values()]
    
    # Separate facilitators (role >= 1) from participants (role == 0)
    facilitators = [u for u in all_users if u.role >= 1]
    participants = [u for u in all_users if u.role == 0]
    
    return CourseUsersResponse(
        slug=slug,
        facilitators=facilitators,
        participants=participants,
        all_users=all_users,
    )


def _transform_course_details(raw_data: dict) -> CourseDetails:
    """
    Transform raw course details into simplified response.
    
    Args:
        raw_data: Raw API response
        
    Returns:
        Simplified course details
    """
    course_data = raw_data.get("course", {})
    return CourseDetails(**course_data)
