# Course Enrichment Feature

## Overview

The `/api/users/{username}` endpoint supports an optional `enrich` query parameter that augments course data with additional information fetched from the course cache.

## Usage

```bash
# Without enrichment (default)
GET /api/users/{username}

# With enrichment
GET /api/users/{username}?enrich=true
```

## Enriched Fields

When `enrich=true`, each course in the response includes two additional fields:

### `active` (boolean | null)

Indicates whether the course is currently active based on timeline dates.

**Logic:**
1. Uses `timeline_start` and `timeline_end` from course details
2. Falls back to `start` and `end` if timeline fields are unavailable
3. Returns `true` if current UTC time is between start and end
4. Returns `null` if dates cannot be determined

**Example:**
```json
{
  "course_slug": "Example_School/Example_Course",
  "active": true
}
```

### `staff` (array of strings | null)

Sorted list of usernames with facilitator/instructor role (role ≥ 1).

**Logic:**
1. Fetches course users from cache or API
2. Deduplicates by username, preferring highest role
3. Filters users with `role >= 1`
4. Sorts alphabetically for consistency

**Example:**
```json
{
  "course_slug": "Example_School/Example_Course",
  "staff": ["Alice", "Bob", "Charlie"]
}
```

## Caching Behavior

The enrichment feature leverages the existing cache layers:

1. **User data**: Cached with `USER_CACHE_TTL` (default: 1 hour)
2. **Course details**: Cached with `COURSE_CACHE_TTL` (default: 24 hours)
3. **Course users**: Cached with `COURSE_USERS_CACHE_TTL` (default: 1 hour)

**Performance characteristics:**
- If course data is already cached: Fast (< 10ms overhead per course)
- If course data needs fetching: Slower (100-500ms per course)
- Course data is cached for future requests

**Recommendation:** Use enrichment when you need the extra data. The cache will make subsequent requests fast.

## Use Cases

### 1. Show only active courses

```javascript
const response = await fetch('/api/users/USERNAME?enrich=true');
const data = await response.json();
const activeCourses = data.courses.filter(c => c.active === true);
```

### 2. Find facilitators to ping

```javascript
const response = await fetch('/api/users/USERNAME?enrich=true');
const data = await response.json();

for (const course of data.courses) {
  if (course.staff && course.staff.length > 0) {
    console.log(`Course: ${course.course_title}`);
    console.log(`Staff: ${course.staff.join(', ')}`);
  }
}
```

### 3. Check if user is in an active course with specific staff

```javascript
const response = await fetch('/api/users/USERNAME?enrich=true');
const data = await response.json();

const activeCoursesWithTargetStaff = data.courses.filter(c => 
  c.active === true && 
  c.staff && 
  c.staff.includes('TargetFacilitator')
);
```

## Performance Considerations

### First Request (Cold Cache)

When enrichment is requested and course data is not cached:
- Additional API calls are made for each course
- Each call: ~200-500ms to Outreach Dashboard
- Total time: O(n × request_time) where n = number of courses

**Example:** User with 5 courses, none cached
- Base request: ~200ms
- Course enrichment: 5 × 300ms = 1500ms
- **Total: ~1700ms**

### Subsequent Requests (Warm Cache)

When course data is already cached:
- No additional API calls
- Pure cache lookups and processing
- Total overhead: < 10ms per course

**Example:** User with 5 courses, all cached
- Base request: ~5ms (from cache)
- Course enrichment: 5 × 2ms = 10ms
- **Total: ~15ms**

### Optimization Tips

1. **Pre-warm cache**: Use `scripts/preload_cache.py` for common courses
2. **Use selectively**: Only request enrichment when needed
3. **Client-side caching**: Cache enriched responses in your gadget
4. **Pagination**: If showing many users, consider fetching enrichment only for visible items

## Example Response

### Without Enrichment

```json
{
  "username": "ExampleUser",
  "courses": [
    {
      "course_id": 12345,
      "course_title": "Wikidata Editathon 2025",
      "course_school": "Example_University",
      "course_term": "Spring",
      "user_count": 25,
      "user_role": "student",
      "course_slug": "Example_University/Wikidata_Editathon_2025"
    }
  ],
  "is_instructor": false,
  "is_student": true,
  "max_project": "wikidata"
}
```

### With Enrichment (`?enrich=true`)

```json
{
  "username": "ExampleUser",
  "courses": [
    {
      "course_id": 12345,
      "course_title": "Wikidata Editathon 2025",
      "course_school": "Example_University",
      "course_term": "Spring",
      "user_count": 25,
      "user_role": "student",
      "course_slug": "Example_University/Wikidata_Editathon_2025",
      "active": true,
      "staff": ["Alice", "Bob"]
    }
  ],
  "is_instructor": false,
  "is_student": true,
  "max_project": "wikidata"
}
```

## Error Handling

If course enrichment fails for a specific course:
- The `active` field will be `null`
- The `staff` field will be `null`
- Other courses continue processing
- Base course data is still returned

This ensures partial failures don't break the entire response.
