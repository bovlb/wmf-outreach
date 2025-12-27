"""User-related API endpoints."""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import UserStatsResponse, CourseEnrollment
from app.services.outreach import outreach_client
from app.services.refresh import refresh_manager
from app.cache.redis import cache, make_key
from app.config import settings

router = APIRouter()


@router.get("/users/{username}", response_model=UserStatsResponse)
async def get_user_courses(
    username: str,
    enrich: bool = Query(False, description="Enrich courses with active status and staff list")
):
    """
    Get courses for a given username.
    
    Returns simplified course enrollment information,
    indicating whether the user is a facilitator or participant.
    
    Args:
        username: Dashboard username to query
        enrich: If True, adds 'active' (boolean) and 'staff' (list of usernames) 
                to each course by fetching course details and users from cache
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
        return await _transform_user_stats(username, cached_data, enrich)
        
    # Cache miss - fetch fresh data
    raw_data = await outreach_client.get_user_stats(username)
    if raw_data is None:
        raise HTTPException(status_code=404, detail="User not found or API error")
        
    # Cache the response
    await cache.set(cache_key, raw_data, settings.user_cache_ttl)
    
    return await _transform_user_stats(username, raw_data, enrich)


async def _transform_user_stats(
    username: str, 
    raw_data: dict, 
    enrich: bool = False
) -> UserStatsResponse:
    """
    Transform raw user stats into simplified response.
    
    Args:
        username: Username being queried
        raw_data: Raw API response
        enrich: If True, add active status and staff list to courses
        
    Returns:
        Simplified user stats response
    """
    courses_details = raw_data.get("courses_details", [])
    courses = [CourseEnrollment(**course) for course in courses_details]
    
    # Enrich with active status and staff list if requested
    if enrich:
        courses = await _enrich_courses(courses)
    
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


async def _enrich_courses(courses: list[CourseEnrollment]) -> list[CourseEnrollment]:
    """
    Enrich courses with active status and staff list.
    
    Fetches course details and users from cache where possible.
    
    Args:
        courses: List of course enrollments
        
    Returns:
        Enriched course enrollments with active and staff fields
    """
    now = datetime.now(timezone.utc)
    
    for course in courses:
        # Parse slug to get school and title components
        slug_parts = course.course_slug.split("/", 1)
        if len(slug_parts) != 2:
            continue
            
        school, title_slug = slug_parts
        
        # Try to get course details from cache
        course_cache_key = make_key("course", course.course_slug)
        course_data, _ = await cache.get(course_cache_key, settings.course_cache_ttl)
        
        if course_data is None:
            # Fetch if not cached
            course_data = await outreach_client.get_course_details(school, title_slug)
            if course_data:
                await cache.set(course_cache_key, course_data, settings.course_cache_ttl)
        
        # Determine active status
        if course_data:
            course_info = course_data.get("course", {})
            # Prefer timeline dates, fall back to start/end
            start_str = course_info.get("timeline_start") or course_info.get("start")
            end_str = course_info.get("timeline_end") or course_info.get("end")
            
            try:
                # Parse ISO-8601 datetime strings
                start = datetime.fromisoformat(start_str.replace("Z", "+00:00")) if start_str else None
                end = datetime.fromisoformat(end_str.replace("Z", "+00:00")) if end_str else None
                
                if start and end:
                    course.active = start <= now <= end
                else:
                    course.active = None
            except (ValueError, AttributeError):
                course.active = None
        
        # Try to get course users from cache
        users_cache_key = make_key("course_users", course.course_slug)
        users_data, _ = await cache.get(users_cache_key, settings.course_users_cache_ttl)
        
        if users_data is None:
            # Fetch if not cached
            users_data = await outreach_client.get_course_users(school, title_slug)
            if users_data:
                await cache.set(users_cache_key, users_data, settings.course_users_cache_ttl)
        
        # Extract staff usernames (role >= 1)
        if users_data:
            users_raw = users_data.get("course", {}).get("users", [])
            
            # Deduplicate by username, preferring highest role
            users_by_name = {}
            for user_data in users_raw:
                user_username = user_data.get("username")
                if not user_username:
                    continue
                    
                if user_username not in users_by_name:
                    users_by_name[user_username] = user_data
                else:
                    existing = users_by_name[user_username]
                    if user_data.get("role", 0) > existing.get("role", 0):
                        users_by_name[user_username] = user_data
            
            # Filter to staff only (role >= 1)
            staff = [
                username 
                for username, user_data in users_by_name.items() 
                if user_data.get("role", 0) >= 1
            ]
            course.staff = sorted(staff)  # Sort for consistency
    
    return courses
