"""Pydantic schemas for API responses."""
from typing import Optional, List, Any
from pydantic import BaseModel, Field


class CourseEnrollment(BaseModel):
    """Course enrollment information from user stats."""
    course_id: int
    course_title: str
    course_school: str
    course_term: str
    user_count: int
    user_role: str
    course_slug: str
    active: Optional[bool] = None
    staff: Optional[List[str]] = None


class UserStatsResponse(BaseModel):
    """Simplified user stats response."""
    username: str
    courses: List[CourseEnrollment]
    is_instructor: bool
    is_student: bool
    max_project: Optional[str] = None


class CourseUser(BaseModel):
    """User enrollment in a course."""
    id: int
    username: str
    role: int
    enrolled_at: str
    admin: bool = False
    content_expert: bool = False
    program_manager: bool = False
    character_sum_ms: int = 0
    character_sum_us: int = 0
    references_count: int = 0
    recent_revisions: int = 0
    total_uploads: int = 0


class CourseUsersResponse(BaseModel):
    """Course users/roster response."""
    slug: str
    facilitators: List[CourseUser]
    participants: List[CourseUser]
    all_users: List[CourseUser]


class CourseDetails(BaseModel):
    """Simplified course details."""
    id: int
    title: str
    description: str
    school: str
    slug: str
    start: str
    end: str
    timeline_start: Optional[str] = None
    timeline_end: Optional[str] = None
    published: bool
    private: bool
    ended: bool
    closed: bool
    course_type: str = Field(alias="type")
    term: str
    student_count: int = 0
    
    class Config:
        """Pydantic config."""
        populate_by_name = True


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    redis_connected: bool
    uptime_seconds: float
