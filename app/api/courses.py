"""Course-related API endpoints."""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import CourseUsersResponse, CourseDetails, CourseUser
from app.services.outreach import outreach_client
from app.services.refresh import refresh_manager
from app.cache.redis import cache, make_key
from app.config import settings

router = APIRouter()


@router.get("/courses/{school}/{title_slug}/users", response_model=CourseUsersResponse)
async def get_course_users(
    school: str, 
    title_slug: str,
    enrich: bool = Query(False, description="Enrich with active status (event and tracking)")
):
    """
    Get course users/roster with role separation.
    
    Returns facilitators (role >= 1) and participants (role == 0) separately.
    Handles duplicate enrollments by preferring highest role and latest enrollment.
    
    Args:
        school: Course school slug
        title_slug: Course title slug  
        enrich: If True, adds active_event and active_tracking status
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
        response = _transform_course_users(slug, cached_data)
        
        if enrich:
            response = await _enrich_course_users(response, school, title_slug)
            
        return response
        
    # Cache miss - fetch fresh data
    raw_data = await outreach_client.get_course_users(school, title_slug)
    if raw_data is None:
        raise HTTPException(status_code=404, detail="Course not found or API error")
        
    # Cache the response
    await cache.set(cache_key, raw_data, settings.course_users_cache_ttl)
    
    response = _transform_course_users(slug, raw_data)
    
    if enrich:
        response = await _enrich_course_users(response, school, title_slug)
        
    return response


@router.get("/courses/{school}/{title_slug}", response_model=CourseDetails)
async def get_course_details(
    school: str, 
    title_slug: str,
    enrich: bool = Query(False, description="Enrich with active status and staff list")
):
    """
    Get course details including metadata and timeline.
    
    Useful for determining if a course is currently active.
    
    Args:
        school: Course school slug
        title_slug: Course title slug
        enrich: If True, adds active_event, active_tracking, and staff list
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
        response = _transform_course_details(cached_data)
        
        if enrich:
            response = await _enrich_course_details(response, school, title_slug)
            
        return response
        
    # Cache miss - fetch fresh data
    raw_data = await outreach_client.get_course_details(school, title_slug)
    if raw_data is None:
        raise HTTPException(status_code=404, detail="Course not found or API error")
        
    # Cache the response
    await cache.set(cache_key, raw_data, settings.course_cache_ttl)
    
    response = _transform_course_details(raw_data)
    
    if enrich:
        response = await _enrich_course_details(response, school, title_slug)
        
    return response


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


async def _enrich_course_users(
    response: CourseUsersResponse, 
    school: str, 
    title_slug: str
) -> CourseUsersResponse:
    """
    Enrich course users response with active status.
    
    Note: Active status is calculated in real-time and not cached.
    
    Args:
        response: CourseUsersResponse to enrich
        school: Course school slug
        title_slug: Course title slug
        
    Returns:
        Enriched response with active_event and active_tracking
    """
    slug = f"{school}/{title_slug}"
    
    # Get course details from cache or fetch
    course_cache_key = make_key("course", slug)
    course_data, _ = await cache.get(course_cache_key, settings.course_cache_ttl)
    
    if course_data is None:
        course_data = await outreach_client.get_course_details(school, title_slug)
        if course_data:
            await cache.set(course_cache_key, course_data, settings.course_cache_ttl)
    
    if course_data:
        course_info = course_data.get("course", {})
        now = datetime.now(timezone.utc)
        
        # Activity tracking dates
        tracking_start_str = course_info.get("start")
        tracking_end_str = course_info.get("end")
        
        # Event dates
        event_start_str = course_info.get("timeline_start")
        event_end_str = course_info.get("timeline_end")
        
        try:
            if tracking_start_str and tracking_end_str:
                tracking_start = datetime.fromisoformat(tracking_start_str.replace("Z", "+00:00"))
                tracking_end = datetime.fromisoformat(tracking_end_str.replace("Z", "+00:00"))
                response.active_tracking = tracking_start <= now <= tracking_end
                
            if event_start_str and event_end_str:
                event_start = datetime.fromisoformat(event_start_str.replace("Z", "+00:00"))
                event_end = datetime.fromisoformat(event_end_str.replace("Z", "+00:00"))
                response.active_event = event_start <= now <= event_end
        except (ValueError, AttributeError):
            pass
    
    return response


async def _enrich_course_details(
    response: CourseDetails,
    school: str,
    title_slug: str
) -> CourseDetails:
    """
    Enrich course details with active status and staff list.
    
    Note: Active status is calculated in real-time and not cached.
    
    Args:
        response: CourseDetails to enrich
        school: Course school slug
        title_slug: Course title slug
        
    Returns:
        Enriched response with active_event, active_tracking, and staff
    """
    now = datetime.now(timezone.utc)
    
    # Calculate active status (not cached since time-based)
    try:
        if response.start and response.end:
            tracking_start = datetime.fromisoformat(response.start.replace("Z", "+00:00"))
            tracking_end = datetime.fromisoformat(response.end.replace("Z", "+00:00"))
            response.active_tracking = tracking_start <= now <= tracking_end
            
        if response.timeline_start and response.timeline_end:
            event_start = datetime.fromisoformat(response.timeline_start.replace("Z", "+00:00"))
            event_end = datetime.fromisoformat(response.timeline_end.replace("Z", "+00:00"))
            response.active_event = event_start <= now <= event_end
    except (ValueError, AttributeError):
        pass
    
    # Get staff list from course users
    slug = f"{school}/{title_slug}"
    users_cache_key = make_key("course_users", slug)
    users_data, _ = await cache.get(users_cache_key, settings.course_users_cache_ttl)
    
    if users_data is None:
        users_data = await outreach_client.get_course_users(school, title_slug)
        if users_data:
            await cache.set(users_cache_key, users_data, settings.course_users_cache_ttl)
    
    if users_data:
        users_raw = users_data.get("course", {}).get("users", [])
        
        # Deduplicate by username, preferring highest role
        users_by_name = {}
        for user_data in users_raw:
            username = user_data.get("username")
            if not username:
                continue
                
            if username not in users_by_name:
                users_by_name[username] = user_data
            else:
                existing = users_by_name[username]
                if user_data.get("role", 0) > existing.get("role", 0):
                    users_by_name[username] = user_data
        
        # Filter to staff only (role >= 1)
        staff = [
            username 
            for username, user_data in users_by_name.items() 
            if user_data.get("role", 0) >= 1
        ]
        response.staff = sorted(staff)
    
    return response
