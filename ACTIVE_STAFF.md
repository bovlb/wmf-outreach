# Active Staff Endpoint

## Overview

The `/api/users/{username}/active-staff` endpoint provides a convenient way to get all staff members from a user's currently active courses in a single request.

## Endpoint

```
GET /api/users/{username}/active-staff
```

## Response Schema

```json
{
  "username": "string",
  "all_staff": ["string"],
  "courses": [
    {
      "course_slug": "string",
      "course_title": "string",
      "staff": ["string"]
    }
  ]
}
```

## Fields

- **`username`**: The queried username
- **`all_staff`**: Sorted, deduplicated list of all staff usernames across active courses
- **`courses`**: List of active courses with their staff members
  - **`course_slug`**: Course identifier (school/title)
  - **`course_title`**: Human-readable course title
  - **`staff`**: Sorted list of staff usernames for this course

## What "Active" Means

A course is considered active if:
- Current UTC time is between `timeline_start` and `timeline_end` (or `start` and `end` if timeline fields unavailable)
- The comparison is: `start <= now <= end`

## Use Cases

### 1. Ping all course facilitators

When a user needs help or has a question, ping all staff from their active courses:

```javascript
const response = await fetch('/api/users/USERNAME/active-staff');
const data = await response.json();

// Generate wiki mentions
const mentions = data.all_staff.map(user => `{{ping|${user}}}`).join(' ');
console.log(mentions);
```

### 2. Check if specific facilitator is available

```javascript
const response = await fetch('/api/users/USERNAME/active-staff');
const data = await response.json();

if (data.all_staff.includes('TargetFacilitator')) {
  console.log('Target facilitator is in an active course!');
}
```

### 3. Show course-specific staff

```javascript
const response = await fetch('/api/users/USERNAME/active-staff');
const data = await response.json();

data.courses.forEach(course => {
  console.log(`${course.course_title}: ${course.staff.join(', ')}`);
});
```

### 4. Count staff per active course

```bash
curl -s http://localhost:8000/api/users/USERNAME/active-staff | \
  jq '.courses[] | {title: .course_title, staff_count: (.staff | length)}'
```

## Performance

This endpoint:
- Fetches user stats (cached with 1-hour TTL)
- Enriches courses with activity status and staff (uses course caches)
- Filters to only active courses
- Deduplicates staff across courses

**Typical response time:**
- Cold cache: ~500ms - 2s (depends on number of courses)
- Warm cache: ~10-50ms

## Comparison to Other Endpoints

| Endpoint | Use When | Returns |
|----------|----------|---------|
| `/users/{username}` | Need basic course list | Course enrollments without enrichment |
| `/users/{username}?enrich=true` | Need full course details | All courses with active status and staff |
| `/users/{username}/active-staff` | Only need staff from active courses | Deduplicated staff list |

The `/active-staff` endpoint is more efficient when you only care about staff members and don't need inactive course data.

## Example Response

```json
{
  "username": "ExampleStudent",
  "all_staff": [
    "Alice",
    "Bob",
    "Charlie"
  ],
  "courses": [
    {
      "course_slug": "University_A/Wikidata_Workshop_2025",
      "course_title": "Wikidata Workshop 2025",
      "staff": ["Alice", "Bob"]
    },
    {
      "course_slug": "University_B/Wikipedia_Editathon",
      "course_title": "Wikipedia Editathon",
      "staff": ["Bob", "Charlie"]
    }
  ]
}
```

In this example:
- "Bob" appears in both courses but only once in `all_staff`
- Both courses are currently active (within their start/end dates)
- Three unique staff members total

## Error Cases

| Status | Meaning |
|--------|---------|
| 404 | User not found or Outreach Dashboard API error |
| 200 with empty arrays | User exists but has no active courses with staff |

## Caching

Uses the same cache layers as other endpoints:
- User stats: 1 hour TTL
- Course details: 24 hour TTL
- Course users: 1 hour TTL

Subsequent requests for the same user are fast due to caching.
