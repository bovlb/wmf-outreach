# Toolforge project structure (recommended)

This document outlines a **practical, WMF-aligned structure** for a Toolforge-hosted project using Python and FastAPI. It assumes:
- read-only access to public Wikimedia services
- no sensitive data
- Redis (Toolforge) for caching
- SQLite (dev) / MariaDB (prod) via SQLAlchemy (optional)

---

## Repository layout

```
tool-name/
├── README.md
├── pyproject.toml
├── poetry.lock              # or requirements.txt
├── toolforge/
│   ├── start.sh              # entrypoint for webservice
│   ├── jobs.yaml             # (optional) cron / jobs
│   └── uwsgi.ini             # if using uwsgi instead of ASGI
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI app
│   ├── config.py             # env + Toolforge config
│   ├── cache/
│   │   ├── __init__.py
│   │   └── redis.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── users.py           # /users/*
│   │   ├── courses.py         # /courses/*
│   │   └── health.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── outreach.py        # outbound HTTP calls
│   │   └── refresh.py         # stale/refresh logic
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py         # pydantic response models
│   └── util/
│       ├── __init__.py
│       └── timing.py
├── scripts/
│   ├── preload_cache.py
│   └── inspect_payloads.py
└── tests/
    └── test_api.py
```

---

## Key files

### `toolforge/start.sh`
```sh
#!/bin/bash
exec webservice --backend=kubernetes python3.11 -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### `app/main.py`
- create FastAPI app
- include routers
- register startup/shutdown hooks
- health check

### `app/config.py`
- reads environment variables
- Toolforge defaults
- Redis host/port
- cache TTLs

---

## Environment & secrets

Toolforge uses **Kubernetes + env vars**.

Use:
```sh
toolforge envvars create REDIS_HOST redis.svc.eqiad.wmflabs
toolforge envvars create REDIS_PORT 6379
```

Avoid:
- committing secrets
- embedding credentials in code

---

## Caching model (recommended)

| Data type | TTL | Strategy |
|----------|-----|----------|
| User lookup | 1 hour | stale-while-revalidate |
| Course metadata | 24h–7d | long-lived |
| Course roster | 1–6h | refresh on access |

Redis keys should be **namespaced**:
```
outreach:user:{username}
outreach:course:{slug}
outreach:course_users:{slug}
```

---

## Jobs vs webservice

- Use **webservice** for APIs
- Use **jobs** for:
  - cache warmups
  - backfills
  - integrity checks

---

## Logging

- Use stdout/stderr
- Structured logs if possible
- Avoid PII

---

## What *not* to do

- Don’t scrape HTML if JSON exists
- Don’t assume undocumented APIs are stable
- Don’t expose raw third-party payloads to gadgets
- Don’t trust counts as numbers without normalization

---

## References

- https://wikitech.wikimedia.org/wiki/Help:Toolforge
- https://wikitech.wikimedia.org/wiki/Help:Toolforge/Web
- https://wikitech.wikimedia.org/wiki/Help:Toolforge/Redis
