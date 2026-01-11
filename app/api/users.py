"""User-related API endpoints."""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import (
    UserStatsResponse, 
    CourseEnrollment, 
    UserActiveStaffResponse,
    ActiveCourseStaff,
    UserDashboardStatus
)
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


@router.get("/users/{username}/active-staff", response_model=UserActiveStaffResponse)
async def get_user_active_staff(
    username: str,
    use_event_dates: bool = Query(
        False, 
        description="Use event dates (timeline_start/end) instead of activity tracking dates (start/end). Default uses activity tracking (more inclusive)."
    )
):
    """
    Get all staff members from user's active courses.
    
    This is a convenience endpoint that returns a deduplicated list of all
    staff members (role >= 1) across all currently active courses where the
    user is enrolled.
    
    By default, uses activity tracking dates (start/end) which are more inclusive.
    Set use_event_dates=true to use event dates (timeline_start/end) instead.
    
    Returns:
        - all_staff: Sorted, deduplicated list of all staff usernames
        - courses: List of active courses with their staff members
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
    else:
        # Cache miss - fetch fresh data
        cached_data = await outreach_client.get_user_stats(username)
        if cached_data is None:
            raise HTTPException(status_code=404, detail="User not found or API error")
            
        # Cache the response
        await cache.set(cache_key, cached_data, settings.user_cache_ttl)
    
    # Get courses and enrich them
    courses_details = cached_data.get("courses_details", [])
    courses = [CourseEnrollment(**course) for course in courses_details]
    enriched_courses = await _enrich_courses(courses)
    
    # Filter to active courses with staff
    # Use activity tracking dates by default, event dates if requested
    active_courses_with_staff = []
    all_staff_set = set()
    
    for course in enriched_courses:
        is_active = course.active_event if use_event_dates else course.active_tracking
        if is_active is True and course.staff:
            active_courses_with_staff.append(
                ActiveCourseStaff(
                    course_slug=course.course_slug,
                    course_title=course.course_title,
                    staff=course.staff,
                )
            )
            all_staff_set.update(course.staff)
    
    return UserActiveStaffResponse(
        username=username,
        all_staff=sorted(all_staff_set),
        courses=active_courses_with_staff,
    )


@router.get("/users/{username}/status", response_model=UserDashboardStatus)
async def get_user_dashboard_status(username: str):
    """
    Get lightweight dashboard status for a user.
    
    This is a minimal endpoint optimized for quick checks to determine
    if a user has any dashboard presence and their activity status.
    
    Returns:
        - has_any_courses: Whether user has any course enrollments
        - has_active_event: Whether user has any courses with active events
        - has_active_tracking: Whether user has any courses being tracked
        - active_event_count: Number of courses with active events
        - tracked_count: Number of courses being tracked (includes active events)
        - total_courses: Total number of course enrollments
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
    else:
        # Cache miss - fetch fresh data
        cached_data = await outreach_client.get_user_stats(username)
        if cached_data is None:
            # User not found - return empty status
            return UserDashboardStatus(
                username=username,
                has_any_courses=False,
                has_active_event=False,
                has_active_tracking=False,
                active_event_count=0,
                tracked_count=0,
                total_courses=0,
            )
            
        # Cache the response
        await cache.set(cache_key, cached_data, settings.user_cache_ttl)
    
    # Get courses and enrich them
    courses_details = cached_data.get("courses_details", [])
    courses = [CourseEnrollment(**course) for course in courses_details]
    enriched_courses = await _enrich_courses(courses)
    
    # Calculate status
    total_courses = len(enriched_courses)
    active_event_count = sum(1 for c in enriched_courses if c.active_event is True)
    tracked_count = sum(1 for c in enriched_courses if c.active_tracking is True)
    
    return UserDashboardStatus(
        username=username,
        has_any_courses=total_courses > 0,
        has_active_event=active_event_count > 0,
        has_active_tracking=tracked_count > 0,
        active_event_count=active_event_count,
        tracked_count=tracked_count,
        total_courses=total_courses,
    )


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
    Sets both active_event (timeline dates) and active_tracking (start/end dates).
    
    Args:
        courses: List of course enrollments
        
    Returns:
        Enriched course enrollments with active_event, active_tracking, and staff fields
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
            
            # Activity tracking dates (start/end) - broader window
            tracking_start_str = course_info.get("start")
            tracking_end_str = course_info.get("end")
            
            # Event dates (timeline_start/end) - narrower window for actual event
            event_start_str = course_info.get("timeline_start")
            event_end_str = course_info.get("timeline_end")
            
            # Store the raw date strings for client-side use
            course.start = tracking_start_str
            course.end = tracking_end_str
            course.timeline_start = event_start_str
            course.timeline_end = event_end_str
            
            try:
                # Parse activity tracking dates
                if tracking_start_str and tracking_end_str:
                    tracking_start = datetime.fromisoformat(tracking_start_str.replace("Z", "+00:00"))
                    tracking_end = datetime.fromisoformat(tracking_end_str.replace("Z", "+00:00"))
                    course.active_tracking = tracking_start <= now <= tracking_end
                else:
                    course.active_tracking = None
                    
                # Parse event dates
                if event_start_str and event_end_str:
                    event_start = datetime.fromisoformat(event_start_str.replace("Z", "+00:00"))
                    event_end = datetime.fromisoformat(event_end_str.replace("Z", "+00:00"))
                    course.active_event = event_start <= now <= event_end
                else:
                    course.active_event = None
                    
            except (ValueError, AttributeError) as e:
                # If parsing fails, leave as None
                course.active_tracking = None
                course.active_event = None
        
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
