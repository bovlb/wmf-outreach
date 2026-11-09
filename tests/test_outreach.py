"""Regression coverage for the Dashboard's user stats endpoint migration."""
import httpx
import pytest

from app.api.users import _transform_user_stats
from app.services.outreach import OutreachDashboardClient


def enrollment(role):
    return {
        "course_id": 123,
        "course_title": "Example Course",
        "course_school": "Example School",
        "course_term": "",
        "user_count": 10,
        "user_role": role,
        "course_slug": "Example_School/Example_Course",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("username", ["PegCult", "A user", "Éditor?name#tag&x=1/part"])
async def test_user_stats_uses_encoded_username_path(httpx_mock, username):
    from urllib.parse import quote

    client = OutreachDashboardClient()
    payload = {"courses_details": [enrollment("Student")], "max_project": "wikidata"}
    httpx_mock.add_response(
        url=f"{client.base_url}/users/{quote(username, safe='')}/stats.json",
        json=payload,
    )

    assert await client.get_user_stats(username) == payload
    assert httpx_mock.get_request().url.query == b""


@pytest.mark.asyncio
@pytest.mark.parametrize("status,content", [(404, b'{}'), (500, b'{}'), (200, b'<html>Error</html>')])
async def test_user_stats_errors_remain_fetch_failures(httpx_mock, status, content):
    httpx_mock.add_response(status_code=status, content=content)
    assert await OutreachDashboardClient().get_user_stats("Missing") is None


@pytest.mark.asyncio
async def test_user_stats_timeout_remains_fetch_failure(httpx_mock):
    httpx_mock.add_exception(httpx.ReadTimeout("Dashboard timeout"))
    assert await OutreachDashboardClient().get_user_stats("Example") is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "roles,instructor,student",
    [([], False, False), (["Student"], False, True), (["Instructor"], True, False),
     (["student"], False, True), (["instructor", "Student"], True, True)],
)
async def test_role_flags_accept_old_and_current_labels(roles, instructor, student):
    response = await _transform_user_stats(
        "Example", {"courses_details": [enrollment(role) for role in roles]}
    )
    assert response.is_instructor is instructor
    assert response.is_student is student
    assert [c.user_role for c in response.courses] == roles


@pytest.mark.asyncio
async def test_public_user_endpoints_keep_contract(httpx_mock, memory_cache):
    from app.main import app

    base = OutreachDashboardClient().base_url
    payload = {"courses_details": [enrollment("Student")], "max_project": "wikidata"}
    httpx_mock.add_response(url=f"{base}/users/Example/stats.json", json=payload)
    # Broad dates keep activity assertions independent of the test run date.
    httpx_mock.add_response(
        url=f"{base}/courses/Example_School/Example_Course/course.json",
        json={"course": {"start": "2000-01-01T00:00:00Z", "end": "2100-01-01T00:00:00Z",
                         "timeline_start": "2000-01-01T00:00:00Z", "timeline_end": "2100-01-01T00:00:00Z"}},
    )
    httpx_mock.add_response(
        url=f"{base}/courses/Example_School/Example_Course/users.json",
        json={"course": {"users": [{"username": "Facilitator", "role": 1}]}},
    )
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/users/Example")
        assert response.status_code == 200
        expected_course = {
            **enrollment("Student"), "active_event": None, "active_tracking": None,
            "staff": None, "start": None, "end": None, "timeline_start": None, "timeline_end": None,
        }
        assert response.json() == {
            "username": "Example", "courses": [expected_course],
            "is_instructor": False, "is_student": True, "max_project": "wikidata",
        }
        response = await client.get("/api/users/Example?enrich=true")
        assert response.status_code == 200
        course = response.json()["courses"][0]
        assert course["active_event"] is True
        assert course["active_tracking"] is True
        assert course["staff"] == ["Facilitator"]

        for suffix in ["", "?use_event_dates=true"]:
            response = await client.get(f"/api/users/Example/active-staff{suffix}")
            assert response.status_code == 200
            assert response.json() == {
                "username": "Example", "all_staff": ["Facilitator"],
                "courses": [{"course_slug": "Example_School/Example_Course",
                             "course_title": "Example Course", "staff": ["Facilitator"]}],
            }

        response = await client.get("/api/users/Example/status")
        assert response.status_code == 200
        assert response.json() == {
            "username": "Example", "has_any_courses": True, "has_active_event": True,
            "has_active_tracking": True, "active_event_count": 1, "tracked_count": 1,
            "total_courses": 1,
        }
    # Every route shares the same cached payload, with one upstream user lookup.
    assert len(httpx_mock.get_requests()) == 3
