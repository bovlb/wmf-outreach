# Outreach Dashboard Helper Backend

A small **FastAPI + Redis** backend for Wikimedia Toolforge that provides cached access to Outreach Dashboard data for use in gadgets and admin tools.

The primary use case is answering questions like:

- Is this user enrolled in any Outreach Dashboard courses?
- If so, what courses, and who are the facilitators?
- Which courses are currently active?

The Outreach Dashboard does not provide a stable public API for these queries. This service centralizes fetching logic, applies sensible caching, and exposes a simple JSON interface.

**Includes:** A MediaWiki gadget that displays course staff information as a tab on user pages. See [GADGET.md](GADGET.md) for installation and testing instructions.

---

## API Endpoints

### `GET /api/users/{username}`

Get course enrollments for a user.

**Query parameters:**
- `enrich` (optional, boolean): If `true`, enriches each course with:
  - `active_event`: Boolean indicating if the event is currently happening (timeline_start ≤ now ≤ timeline_end)
  - `active_tracking`: Boolean indicating if activity tracking is active (start ≤ now ≤ end) - typically broader window
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
      "active_event": false,
      "active_tracking": true,
      "staff": ["Facilitator1", "Facilitator2"]
    }
  ],
  "is_instructor": false,
  "is_student": true,
  "max_project": "wikidata"
}
```

**Note:** `active_event` and `active_tracking` represent different time windows:
- **Event dates** (timeline_start/end): The actual event timeframe (e.g., editathon weekend)
- **Activity tracking** (start/end): Broader window for tracking contributions (e.g., semester-long course)

### `GET /api/users/{username}/active-staff`

Get all staff members from a user's active courses.

**Query parameters:**
- `use_event_dates` (optional, boolean, default: false): If `true`, uses event dates (timeline_start/end) instead of activity tracking dates (start/end). Default uses activity tracking which is more inclusive.

**Response:**
```json
{
  "username": "PegCult",
  "all_staff": ["Alice", "Bob", "Charlie"],
  "courses": [
    {
      "course_slug": "Example_School/Example_Course",
      "course_title": "Example Course",
      "staff": ["Alice", "Bob"]
    },
    {
      "course_slug": "Another_School/Another_Course",
      "course_title": "Another Course",
      "staff": ["Bob", "Charlie"]
    }
  ]
}
```

This endpoint:
- By default, uses activity tracking dates (start/end) - more inclusive
- Set `use_event_dates=true` to use event dates (timeline_start/end) - narrower window
- Only includes currently active courses
- Deduplicates staff across all active courses
- Returns sorted, unique list of staff usernames
- Useful for pinging or notifying course facilitators

### `GET /api/courses/{school}/{title_slug}/users`

Get course roster with facilitators and participants separated.

**Query parameters:**
- `enrich` (optional, boolean): If `true`, adds `active_event` and `active_tracking` status

### `GET /api/courses/{school}/{title_slug}`

Get course details including timeline and metadata.

**Query parameters:**
- `enrich` (optional, boolean): If `true`, adds `active_event`, `active_tracking`, and `staff` list

### `GET /health`

Health check endpoint.

---

## Design goals

- Fast responses for gadgets
- Minimal load on Outreach Dashboard
- Simple deployment on Toolforge
- No background jobs or cron dependencies
- Clear separation between user data and course data
- Includes MediaWiki gadget for displaying course staff

The data changes slowly. The main source of churn is new users being queried, not frequent updates to course metadata.

---

## MediaWiki Gadget

The service includes a MediaWiki gadget that adds a "Course staff" tab to user-related pages. The tab only appears for users enrolled in currently active courses.

**Features:**
- Automatically detects user pages, user talk pages, contributions pages
- Shows all active courses and their staff members
- Links to Outreach Dashboard and user talk pages
- One-click copy of ping template for all staff members
- Fully client-side (no MediaWiki extension needed)

**See:** [GADGET.md](GADGET.md) for installation instructions and [test-gadget.html](test-gadget.html) for local testing.

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