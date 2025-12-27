# Outreach Dashboard API — Course Users (`/users.json`)

Endpoint:

- `GET /courses/{school}/{course_slug}/users.json`

## What this returns

Top-level shape:

```json
{
  "course": {
    "users": [
      { /* user enrollment + contribution stats */ }
    ]
  }
}
```

Each element in `course.users` represents **a user enrollment record for this course**, with per-user stats and useful links.

## Role semantics (important)

The `role` field is an integer permission level for the course:

- `role >= 1` → **facilitator / instructor** (i.e., course staff)
- `role == 0` → **participant / student**

In your gadget/backend logic, treat `role >= 1` as “facilitator” for ping targets, access controls, and UI badges.

Notes:
- `role_description` is often `null` or `""` and should not be relied on.
- There may be other role values (e.g. higher numbers) depending on Dashboard configuration; safest rule is **`>= 1`**.

## User object fields

Common fields you can depend on:

- **Identity**
  - `id` (number): Dashboard user id
  - `username` (string): Wikimedia username
  - `admin` (boolean): Whether the user is a Dashboard admin (not a Wikidata admin)

- **Enrollment**
  - `enrolled_at` (ISO timestamp): enrollment time for this course
  - `role` (int): role level (see above)

- **Contribution stats (course-scoped)**
  - `character_sum_ms`, `character_sum_us`, `character_sum_draft` (numbers): character contributions by namespace buckets used by Dashboard
  - `references_count` (number)
  - `recent_revisions` (number)
  - `total_uploads` (number)

- **Flags**
  - `content_expert` (boolean)
  - `program_manager` (boolean)

- **Convenience URLs**
  - `contribution_url`: contributions on the course wiki (here Wikidata)
  - `sandbox_url`: user page prefix index on the course wiki
  - `global_contribution_url`: GU.C Toolforge profile

## Practical usage patterns

### 1) Get facilitators to ping
Filter to:

- `users.filter(u => u.role >= 1)`

Then build mentions/links for those usernames.

### 2) Detect course membership for a username
Case-sensitive matches are typical in Wikimedia, but in practice you may want a case-insensitive compare:

- Find any `u.username` matching your target.
- If present, the user is enrolled.
- Use `u.role` to decide badge text (facilitator vs participant).

### 3) Build a “course roster” view
Use:
- `username`
- `role`
- key stats (`references_count`, `character_sum_ms`, `total_uploads`)

### 4) Caveat: possible duplicate rows per username
In your provided sample, the same `username` (**PegCult**) appears twice with different `role` and different `enrolled_at` timestamps.

That implies:
- The API may return **multiple enrollment records per user**, e.g. role changes, re-enrollment, or data quirks.

**Recommendation:** when you need a unique roster keyed by username:
- Group by `username`
- Prefer the entry with the **highest `role`**, and if tied, the **latest `enrolled_at`**
- Optionally keep all rows for audit/debug output

## Minimal TypeScript shape

```ts
type CourseUsersResponse = {
  course: {
    users: CourseUser[];
  };
};

type CourseUser = {
  id: number;
  username: string;

  // enrollment
  enrolled_at: string; // ISO
  role: number;
  role_description: string | null;

  // flags
  content_expert: boolean;
  program_manager: boolean;
  admin: boolean;

  // stats
  character_sum_ms: number;
  character_sum_us: number;
  character_sum_draft: number;
  references_count: number;
  recent_revisions: number;
  total_uploads: number;

  // urls
  contribution_url: string;
  sandbox_url: string;
  global_contribution_url: string;
};
```

## Suggested normalization helper (pseudocode)

```js
function normalizeRoster(users) {
  const byName = new Map();

  for (const u of users) {
    const key = u.username;
    const prev = byName.get(key);

    if (!prev) {
      byName.set(key, u);
      continue;
    }

    // Prefer higher role, then later enrollment
    if (u.role > prev.role) {
      byName.set(key, u);
    } else if (u.role === prev.role) {
      if (Date.parse(u.enrolled_at) > Date.parse(prev.enrolled_at)) {
        byName.set(key, u);
      }
    }
  }

  return [...byName.values()];
}
```
