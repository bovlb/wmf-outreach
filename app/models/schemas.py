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
    active_event: Optional[bool] = None
    active_tracking: Optional[bool] = None
    staff: Optional[List[str]] = None
    start: Optional[str] = None
    end: Optional[str] = None
    timeline_start: Optional[str] = None
    timeline_end: Optional[str] = None


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
    active_event: Optional[bool] = None
    active_tracking: Optional[bool] = None


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
    active_event: Optional[bool] = None
    active_tracking: Optional[bool] = None
    staff: Optional[List[str]] = None
    
    class Config:
        """Pydantic config."""
        populate_by_name = True


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    redis_connected: bool
    uptime_seconds: float


class ActiveCourseStaff(BaseModel):
    """Staff information for an active course."""
    course_slug: str
    course_title: str
    staff: List[str]


class UserActiveStaffResponse(BaseModel):
    """Response containing all staff from user's active courses."""
    username: str
    all_staff: List[str]
    courses: List[ActiveCourseStaff]


class UserDashboardStatus(BaseModel):
    """Lightweight user dashboard status for quick checks."""
    username: str
    has_any_courses: bool
    has_active_event: bool
    has_active_tracking: bool
    active_event_count: int
    tracked_count: int
    total_courses: int
