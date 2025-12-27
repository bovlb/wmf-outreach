## `GET /courses/{school}/{title_slug}` (course details JSON)

### Request

```http
GET https://outreachdashboard.wmflabs.org/courses/{school}/<title_slug>
```

**Path parameters**

- `{school}`: Course “school/organization” slug component (example: `Igbo_Wikimedian_User_Group,_WAFTAI`)
- `{title_slug}`: Course title slug component (example: `Wikidata_Days_IWUG_and_WAFTAI_2025_(November)`)

**Notes**
- This endpoint (as observed) returns JSON at the *non-`.json`* course URL.

---

### Response

**Content-Type:** `application/json`

Top-level object:

- `course` (object): Full course record, including metadata, flags, wiki configuration, aggregate stats, and update logs.

---

### `course` core fields (metadata)

- `id` (number): Internal course ID.
- `title` (string)
- `description` (string)
- `start` (string, ISO-8601 datetime, UTC)
- `end` (string, ISO-8601 datetime, UTC)
- `school` (string)
- `subject` (string)
- `slug` (string): Combined slug matching the request path.
- `url` (string|null): External URL (nullable)
- `type` (string): Course type (example: `Editathon`)
- `term` (string): Term label (example: `November`)
- `created_at` (string, ISO-8601 datetime)
- `updated_at` (string, ISO-8601 datetime)
- `published` (boolean)
- `private` (boolean)
- `ended` (boolean)
- `closed` (boolean)
- `enroll_url` (string): Enrollment URL for this course.

Time/timeline related:

- `timeline_start` / `timeline_end` (string, ISO-8601 datetime)
- `use_start_and_end_times` (boolean)
- `weekdays` (string): 7-character string of `0/1` flags (observed: `"0000000"`)
- `day_exceptions` (string)
- `no_day_exceptions` (boolean)

Counts (mixed typing; see notes):

- `student_count` (number)
- `trained_count` (number)
- `article_count` (number)
- `created_count` (string) — e.g. `"873"`
- `edited_count` (string) — e.g. `"1.7K"`
- `edit_count` (string) — e.g. `"21.6K"`
- `word_count` (string) — e.g. `"1.4M"`
- `references_count` (string) — e.g. `"6.44K"`
- `view_count` (string) — e.g. `"5.45K"`
- `character_sum` (number)
- `character_sum_human` (string) — e.g. `"7.24M"`

Uploads:

- `upload_count` (number)
- `uploads_in_use_count` (number)
- `upload_usages_count` (number)

---

### Wiki configuration

- `home_wiki` (object)
  - `id` (number)
  - `language` (string|null)
  - `project` (string) — e.g. `"wikidata"`
- `wikis` (array of objects)
  - `language` (string|null)
  - `project` (string)
- `namespaces` (array): Observed empty.
- `wiki_string_prefix` (string): e.g. `"articles_wikidata"`
- `wiki_edits_enabled` / `home_wiki_edits_enabled` (boolean)

---

### Flags and feature toggles

- `flags` (object): Mixed configuration and operational metadata, including:
  - `academic_system` (null or string)
  - `format` (string)
  - `timeslice_duration.default` (number seconds)
  - multiple `*_enabled` toggles (timeline/wiki_edits/online_volunteers/etc.)
  - `edit_settings` (object): `wiki_course_page_enabled`, `assignment_edits_enabled`, `enrollment_edits_enabled`
  - update operational fields such as `event_sync`, `average_update_delay`, and per-update logs

---

### Update tracking

- `needs_update` (boolean)
- `update_until` (string, ISO-8601 datetime)
- `updates` (object)
  - `average_delay` (number)
  - `last_update` (object): `start_time`, `end_time`, `error_count`, `processed`, `reprocessed`, etc.

Additionally, `flags.update_logs` contains a map keyed by update number with similar timing and processed counts.

---

### Course statistics

- `course_stats` (object)
  - `id` (number)
  - `stats_hash` (object): keyed by wiki domain (example: `"www.wikidata.org"`) → map of metric name → string counts

Example metric keys include:

- `items created`, `claims created`, `labels added`, `descriptions added`, `references added`, `total revisions`, etc.

---

### Sensitive / access-controlled fields

- `passcode` (string): Returned in the response (redacted in your sample). Treat as sensitive.
- `canUploadSyllabus` (boolean)

---

### Notes / gotchas

- Many “counts” are strings with `K/M` suffixes while others are numbers. Treat all counts as strings unless you normalize.
- `flags.update_logs` is a nested structure with dynamic keys (stringified integers).
- The endpoint returns a *very large* payload; cache it longer than user lookups.
- The presence of `passcode` means you should be careful about what you return to gadgets (strip it server-side).
