# Outreach Dashboard API notes (index)

This directory now contains three small markdown specs/notes files:

- [User stats API](user_stats_api.md) — **course membership lookup by username** (stats endpoint; useful for “what course is this user in?”)
- [Course details API](course_details_api.md) — **course metadata + timeline** (start/end/timeline fields; useful for “is this course active right now?”)
- [Course users API](course_users_api.md) — **roster + roles** (includes `role`; **`role >= 1` means facilitator/staff**; useful for “who are the course staff?”)

## How you can use these together

### 1) Find out what course a user is in
Use the *User stats API* to discover course(s) associated with a username, then follow the `slug`/course link into *Course details API* and *Course users API* as needed.

### 2) Find out whether a course is currently active
Use the *Course details API*:
- Prefer `timeline_start` / `timeline_end` (or `start` / `end` if you want the event window).
- `ended: true` is a strong hint it’s not active, but the date fields are the source of truth.

### 3) Find out who the course staff are
Use the *Course users API* and filter:
- **staff/facilitators:** `role >= 1`
- everyone else is participants (typically `role == 0`)
