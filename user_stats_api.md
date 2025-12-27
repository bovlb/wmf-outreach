## `GET /user_stats.json`

### Request

```http
GET https://outreachdashboard.wmflabs.org/user_stats.json?username=<username>
```

**Query parameters**

- `username` (string, required): Dashboard username to summarize (URL-encoded; spaces allowed).

---

### Response

**Content-Type:** `application/json`

**Top-level fields**

- `user_recent_uploads` (array): Recent Commons uploads attributed to the user.
- `courses_details` (array): Course enrollments (both instructor and student roles), with course identifiers and basic metadata.
- `as_instructor` (object): Aggregate stats for courses where the user is an instructor.
- `by_students` (object): Aggregate stats produced by the user’s students (across instructor courses).
- `as_student` (object): Aggregate stats for courses where the user is a student.
- `max_project` (string): Project name with the user’s maximum activity.

---

### `user_recent_uploads[]`

Schema for each item:

- `id` (number): Upload ID.
- `uploaded_at` (string, ISO-8601): Upload time.
- `usage_count` (number | null): Usage count.
- `url` (string): Commons file page URL.
- `thumburl` (string | null): Thumbnail URL.
- `file_name` (string): Filename.
- `uploader` (string): Uploader username.

---

### `courses_details[]`

Schema for each item:

- `course_id` (number)
- `course_title` (string)
- `course_school` (string)
- `course_term` (string)
- `user_count` (number)
- `user_role` (string)
- `course_slug` (string)

---

### `as_instructor`

Aggregate instructor stats:

- `course_string_prefix` (string)
- `courses_count` (number)
- `user_count` (number)
- `trained_percent` (string)

---

### `by_students`

Aggregate student output (string values often abbreviated with K/M):

- `word_count` (string)
- `references_count` (string)
- `view_sum` (string)
- `article_count` (string)
- `new_article_count` (string)
- `upload_count` (string)
- `uploads_in_use_count` (number)
- `upload_usage_count` (number)

---

### `as_student`

Aggregate stats for courses where user is a student:

- `course_string_prefix` (string)
- `individual_courses_count` (number)
- `individual_word_count` (string)
- `individual_references_count` (string)
- `individual_article_count` (string)
- `individual_upload_count` (string)
- `individual_upload_usage_count` (string)

---

### Notes

- Numeric values are inconsistently typed (numbers vs strings with K/M).
- Some fields may be `null`.
