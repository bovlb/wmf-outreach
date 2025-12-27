# Outreach Dashboard Helper Backend

A small **FastAPI + Redis** backend for Wikimedia Toolforge that provides cached access to Outreach Dashboard data for use in gadgets and admin tools.

The primary use case is answering questions like:

- Is this user enrolled in any Outreach Dashboard courses?
- If so, what courses, and who are the facilitators?

The Outreach Dashboard does not provide a stable public API for these queries. This service centralizes fetching logic, applies sensible caching, and exposes a simple JSON interface.

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