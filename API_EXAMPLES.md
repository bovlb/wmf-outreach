# API Examples (curl)

This file contains practical curl examples for testing the API.

## Health Check

```bash
curl http://localhost:8000/health
```

## User Endpoints

### Get user courses (basic)
```bash
curl http://localhost:8000/api/users/PegCult
```

### Get user courses (enriched with active status and staff)
```bash
curl "http://localhost:8000/api/users/PegCult?enrich=true"
```

### Pretty-print JSON output
```bash
curl "http://localhost:8000/api/users/PegCult?enrich=true" | jq
```

### Filter to only active courses (using jq)
```bash
curl -s "http://localhost:8000/api/users/PegCult?enrich=true" | \
  jq '.courses[] | select(.active == true)'
```

### Get staff list for all courses
```bash
curl -s "http://localhost:8000/api/users/PegCult?enrich=true" | \
  jq '.courses[] | {title: .course_title, staff: .staff}'
```

### Count active vs inactive courses
```bash
curl -s "http://localhost:8000/api/users/PegCult?enrich=true" | \
  jq '[.courses[] | .active] | group_by(.) | 
      map({status: (.[0] // "unknown"), count: length})'
```

## Course Endpoints

### Get course users/roster
```bash
curl "http://localhost:8000/api/courses/Igbo_Wikimedian_User_Group,_WAFTAI/Wikidata_Days_IWUG_and_WAFTAI_2025_(November)/users"
```

### Get only facilitators
```bash
curl -s "http://localhost:8000/api/courses/SCHOOL/TITLE/users" | \
  jq '.facilitators'
```

### Count facilitators and participants
```bash
curl -s "http://localhost:8000/api/courses/SCHOOL/TITLE/users" | \
  jq '{facilitators: (.facilitators | length), participants: (.participants | length)}'
```

### Get course details
```bash
curl "http://localhost:8000/api/courses/Igbo_Wikimedian_User_Group,_WAFTAI/Wikidata_Days_IWUG_and_WAFTAI_2025_(November)"
```

### Check if course is currently active
```bash
curl -s "http://localhost:8000/api/courses/SCHOOL/TITLE" | \
  jq '{title: .title, ended: .ended, start: .start, end: .end}'
```

## Advanced Examples

### Find all courses where user is a facilitator
```bash
curl -s "http://localhost:8000/api/users/USERNAME?enrich=true" | \
  jq '.courses[] | select(.user_role == "instructor" or .staff != null and (.staff | index("USERNAME")))'
```

### Get summary of user's involvement
```bash
curl -s "http://localhost:8000/api/users/USERNAME?enrich=true" | \
  jq '{
    username: .username,
    is_instructor: .is_instructor,
    is_student: .is_student,
    total_courses: (.courses | length),
    active_courses: ([.courses[] | select(.active == true)] | length),
    courses_as_student: ([.courses[] | select(.user_role == "student")] | length),
    courses_as_instructor: ([.courses[] | select(.user_role != "student")] | length)
  }'
```

### List all staff across all of a user's courses
```bash
curl -s "http://localhost:8000/api/users/USERNAME?enrich=true" | \
  jq '[.courses[].staff // [] | .[]] | unique | sort'
```

### Performance test (time the request)
```bash
time curl -s "http://localhost:8000/api/users/USERNAME?enrich=true" > /dev/null
```

### Compare enriched vs non-enriched response time
```bash
echo "Without enrichment:"
time curl -s "http://localhost:8000/api/users/USERNAME" > /dev/null

echo "With enrichment (first time - may fetch data):"
time curl -s "http://localhost:8000/api/users/USERNAME?enrich=true" > /dev/null

echo "With enrichment (second time - should be cached):"
time curl -s "http://localhost:8000/api/users/USERNAME?enrich=true" > /dev/null
```

## Production Examples (Toolforge)

Replace `localhost:8000` with your Toolforge URL:

```bash
# Production URL format
TOOL_URL="https://your-tool-name.toolforge.org"

# Health check
curl "${TOOL_URL}/health"

# Get enriched user data
curl "${TOOL_URL}/api/users/PegCult?enrich=true"
```

## Using with HTTPie (alternative to curl)

```bash
# Install httpie: pip install httpie

# Basic request
http localhost:8000/api/users/PegCult

# With query parameter
http localhost:8000/api/users/PegCult enrich==true

# Pretty output is default!
```

## Using in Browser

```
http://localhost:8000/docs
```

Opens the interactive Swagger UI where you can test all endpoints with a UI.
