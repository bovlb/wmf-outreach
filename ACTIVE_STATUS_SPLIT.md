# Active Status Split: Event vs Activity Tracking

## Overview

The Outreach Dashboard uses two different time windows for courses:
- **Event dates** (`timeline_start`/`timeline_end`): The actual event timeframe (e.g., editathon weekend)
- **Activity tracking** (`start`/`end`): Broader window for tracking contributions (e.g., semester-long course)

This implementation now properly distinguishes between these two concepts.

## Changes Made

### 1. Documentation Updates

**`course_details_api.md`**:
- Clarified that `start`/`end` are for **activity tracking**
- Clarified that `timeline_start`/`timeline_end` are for **event dates**

### 2. Schema Changes

**Two new boolean fields** replace the single `active` field:

- **`active_event`**: Boolean indicating if the event is currently happening
  - Uses `timeline_start` and `timeline_end`
  - Typically a narrower window (e.g., 1-day editathon)
  - `null` if event dates are not available

- **`active_tracking`**: Boolean indicating if activity tracking is active
  - Uses `start` and `end`
  - Typically a broader window (e.g., 3-month semester)
  - `null` if tracking dates are not available

**Applied to these schemas:**
- `CourseEnrollment` (user courses)
- `CourseDetails` (course details)
- `CourseUsersResponse` (course roster)

### 3. API Changes

#### `/api/users/{username}?enrich=true`
- Now returns both `active_event` and `active_tracking` for each course
- Both fields calculated in real-time (not cached)

#### `/api/users/{username}/active-staff`
- **New query parameter**: `use_event_dates` (boolean, default: `false`)
- **Default behavior**: Uses activity tracking dates (more inclusive)
- **With `use_event_dates=true`**: Uses event dates (narrower window)

Example:
```bash
# More inclusive (default) - uses activity tracking dates
curl http://localhost:8000/api/users/PegCult/active-staff

# Narrower window - uses event dates
curl "http://localhost:8000/api/users/PegCult/active-staff?use_event_dates=true"
```

#### `/api/courses/{school}/{title_slug}/users?enrich=true`
- **New feature**: Enrichment support added
- Returns `active_event` and `active_tracking` status
- Active status calculated in real-time (not cached)

#### `/api/courses/{school}/{title_slug}?enrich=true`
- **New feature**: Enrichment support added
- Returns `active_event`, `active_tracking`, and `staff` list
- Active status calculated in real-time (not cached)
- Staff list fetched from cache or API

### 4. Caching Strategy

**Important**: Active status is **never cached** because it's time-dependent.

**What is cached:**
- User stats
- Course details (dates themselves)
- Course users (staff lists)

**What is NOT cached:**
- `active_event` boolean (calculated from cached dates + current time)
- `active_tracking` boolean (calculated from cached dates + current time)

This ensures the active status is always accurate relative to the current time.

## Use Cases

### Scenario 1: Weekend Editathon

```
Event dates:     Nov 15-17, 2025 (weekend editathon)
Tracking dates:  Nov 1 - Dec 31, 2025 (2-month tracking window)
```

**On Nov 16:**
- `active_event`: `true` (during the editathon)
- `active_tracking`: `true` (tracking is active)

**On Nov 25:**
- `active_event`: `false` (editathon is over)
- `active_tracking`: `true` (still tracking contributions)

### Scenario 2: Semester Course

```
Event dates:     Not set (no specific event)
Tracking dates:  Sep 1 - Dec 15, 2025 (full semester)
```

**On Oct 1:**
- `active_event`: `null` (no event dates)
- `active_tracking`: `true` (tracking is active)

### Scenario 3: Finding Staff

**Use activity tracking (default)** when you want to find facilitators for:
- Ongoing support questions
- Long-term mentorship
- Course-related inquiries during the tracking period

**Use event dates** when you want to find facilitators for:
- Issues during the actual event
- Real-time event coordination
- Event-specific questions

## Migration Notes

### Breaking Changes

- **Field rename**: `active` → `active_event` + `active_tracking`
- Existing clients using `active` will need to update

### Backward Compatibility

**None** - This is a breaking change. Clients must update to use the new fields.

**Recommended migration:**
1. If you were using `active`, decide which semantic you need:
   - For event-specific logic → use `active_event`
   - For contribution tracking → use `active_tracking`
   - When in doubt → use `active_tracking` (more inclusive)

2. Update your code:
```javascript
// Old
if (course.active) { ... }

// New (using tracking)
if (course.active_tracking) { ... }

// New (using event)
if (course.active_event) { ... }

// New (both)
if (course.active_event || course.active_tracking) { ... }
```

## Examples

### Get enriched user courses
```bash
curl "http://localhost:8000/api/users/PegCult?enrich=true"
```

Response:
```json
{
  "username": "PegCult",
  "courses": [{
    "course_slug": "School/Course",
    "active_event": false,
    "active_tracking": true,
    "staff": ["Alice", "Bob"]
  }]
}
```

### Get staff from active courses (activity tracking)
```bash
curl http://localhost:8000/api/users/PegCult/active-staff
```

### Get staff from active courses (event dates)
```bash
curl "http://localhost:8000/api/users/PegCult/active-staff?use_event_dates=true"
```

### Get enriched course details
```bash
curl "http://localhost:8000/api/courses/SCHOOL/TITLE?enrich=true"
```

Response:
```json
{
  "title": "Example Course",
  "start": "2025-09-01T00:00:00Z",
  "end": "2025-12-15T00:00:00Z",
  "timeline_start": "2025-11-15T00:00:00Z",
  "timeline_end": "2025-11-17T00:00:00Z",
  "active_event": false,
  "active_tracking": true,
  "staff": ["Alice", "Bob"]
}
```

## Performance Impact

**No significant impact**:
- Date calculations are trivial (microseconds)
- Existing cache layers still used
- Active status not cached (by design - it's time-dependent)

## Testing

Updated tests to use new field names:
- `test_enrichment.py` - Updated to test both active fields
- `test_api.py` - Updated endpoint documentation check
