# Outreach Dashboard Helper Backend

A small **FastAPI + Redis** backend for Wikimedia Toolforge that provides cached access to Outreach Dashboard data for use in gadgets and admin tools.

The primary use case is answering questions like:

- Is this user enrolled in any Outreach Dashboard courses?
- If so, what courses, and who are the facilitators?
- Which courses are currently active?

The Outreach Dashboard does not provide a stable public API for these queries. This service centralizes fetching logic, applies sensible caching, and exposes a simple JSON interface.

---

## API Endpoints

### `GET /api/users/{username}`

Get course enrollments for a user.

**Query parameters:**
- `enrich` (optional, boolean): If `true`, enriches each course with:
  - `active`: Boolean indicating if the course is currently active (start ≤ now ≤ end)
  - `staff`: Sorted list of usernames with role ≥ 1 (facilitators/instructors)

**Example:**
```bash
# Basic response
curl http://localhost:8000/api/users/PegCult

# Enriched with active status and staff list
curl http://localhost:8000/api/users/PegCult?enrich=true
```

**Response:**
```json
{
  "username": "PegCult",
  "courses": [
    {
      "course_id": 12345,
      "course_title": "Example Course",
      "course_school": "Example School",
      "course_term": "Fall 2025",
      "user_count": 42,
      "user_role": "student",
      "course_slug": "Example_School/Example_Course",
      "active": true,
      "staff": ["Facilitator1", "Facilitator2"]
    }
  ],
  "is_instructor": false,
  "is_student": true,
  "max_project": "wikidata"
}
```

### `GET /api/courses/{school}/{title_slug}/users`

Get course roster with facilitators and participants separated.

### `GET /api/courses/{school}/{title_slug}`

Get course details including timeline and metadata.

### `GET /health`

Health check endpoint.

---

## Design goals

- Fast responses for gadgets
- Minimal load on Outreach Dashboard
- Simple deployment on Toolforge
- No background jobs or cron dependencies
- Clear separation between user data and course data

The data changes slowly. The main source of churn is new users being queried, not frequent updates to course metadata.

---

## Architecture overview

- FastAPI for the HTTP API
- Redis for shared caching
- Async I/O throughout
- No persistent database
- No Server-Sent Events (by design)

### Caching model: stale-while-revalidate

Caching is implemented explicitly in application logic.

Each cache entry stores:
```json
{
  "fetched_at": <unix timestamp>,
  "data": <JSON payload>
}