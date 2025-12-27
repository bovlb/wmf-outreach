"""Tests for course enrichment feature."""
import pytest
from datetime import datetime, timedelta
from app.models.schemas import CourseEnrollment
from app.api.users import _enrich_courses
from app.cache.redis import cache, make_key
from app.config import settings


@pytest.mark.asyncio
async def test_enrich_courses_with_cached_data():
    """Test enrichment when course data is already cached."""
    # Connect cache
    await cache.connect()
    
    try:
        # Create test course
        test_slug = "Test_School/Test_Course"
        test_course = CourseEnrollment(
            course_id=1,
            course_title="Test Course",
            course_school="Test_School",
            course_term="Spring",
            user_count=10,
            user_role="student",
            course_slug=test_slug,
        )
        
        # Mock course details in cache (active course)
        now = datetime.utcnow()
        start = now - timedelta(days=10)
        end = now + timedelta(days=10)
        
        course_details = {
            "course": {
                "timeline_start": start.isoformat() + "Z",
                "timeline_end": end.isoformat() + "Z",
            }
        }
        
        course_key = make_key("course", test_slug)
        await cache.set(course_key, course_details, settings.course_cache_ttl)
        
        # Mock course users in cache
        course_users = {
            "course": {
                "users": [
                    {"username": "Alice", "role": 1},
                    {"username": "Bob", "role": 2},
                    {"username": "Charlie", "role": 0},
                ]
            }
        }
        
        users_key = make_key("course_users", test_slug)
        await cache.set(users_key, course_users, settings.course_users_cache_ttl)
        
        # Enrich
        enriched = await _enrich_courses([test_course])
        
        # Verify
        assert len(enriched) == 1
        assert enriched[0].active is True
        assert enriched[0].staff == ["Alice", "Bob"]  # Sorted, role >= 1
        
    finally:
        # Cleanup
        await cache.disconnect()


@pytest.mark.asyncio
async def test_enrich_courses_inactive():
    """Test enrichment with an inactive course."""
    await cache.connect()
    
    try:
        test_slug = "Test_School/Inactive_Course"
        test_course = CourseEnrollment(
            course_id=2,
            course_title="Inactive Course",
            course_school="Test_School",
            course_term="Past",
            user_count=5,
            user_role="student",
            course_slug=test_slug,
        )
        
        # Course that ended yesterday
        now = datetime.utcnow()
        start = now - timedelta(days=30)
        end = now - timedelta(days=1)
        
        course_details = {
            "course": {
                "start": start.isoformat() + "Z",
                "end": end.isoformat() + "Z",
            }
        }
        
        course_key = make_key("course", test_slug)
        await cache.set(course_key, course_details, settings.course_cache_ttl)
        
        # Mock empty staff
        course_users = {
            "course": {
                "users": [
                    {"username": "Student1", "role": 0},
                    {"username": "Student2", "role": 0},
                ]
            }
        }
        
        users_key = make_key("course_users", test_slug)
        await cache.set(users_key, course_users, settings.course_users_cache_ttl)
        
        # Enrich
        enriched = await _enrich_courses([test_course])
        
        # Verify
        assert enriched[0].active is False
        assert enriched[0].staff == []  # No staff members
        
    finally:
        await cache.disconnect()
