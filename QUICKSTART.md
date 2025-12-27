# Quick Start Guide

Get the Outreach Dashboard Helper running locally in 5 minutes.

## Local Development Setup

### 1. Install Redis

**macOS:**
```bash
brew install redis
brew services start redis
```

**Linux:**
```bash
sudo apt-get install redis-server
sudo systemctl start redis
```

### 2. Set up Python environment

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env if needed (defaults work for local development)
```

### 4. Run the server

```bash
# Start uvicorn
uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000

## Testing the API

### Health check
```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "ok",
  "redis_connected": true,
  "uptime_seconds": 12.34
}
```

### Get user courses
```bash
curl http://localhost:8000/api/users/PegCult
```

Response:
```json
{
  "username": "PegCult",
  "courses": [
    {
      "course_id": 12345,
      "course_title": "Example Course",
      "course_school": "Example School",
      "course_term": "Fall 2025",
      "user_count": 42,
      "user_role": "instructor",
      "course_slug": "Example_School/Example_Course"
    }
  ],
  "is_instructor": true,
  "is_student": false,
  "max_project": "wikidata"
}
```

### Get course users
```bash
curl "http://localhost:8000/api/courses/Igbo_Wikimedian_User_Group,_WAFTAI/Wikidata_Days_IWUG_and_WAFTAI_2025_(November)/users"
```

### Get course details
```bash
curl "http://localhost:8000/api/courses/Igbo_Wikimedian_User_Group,_WAFTAI/Wikidata_Days_IWUG_and_WAFTAI_2025_(November)"
```

## Interactive API Documentation

FastAPI provides automatic interactive documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Debugging Tools

### Inspect raw API payloads
```bash
# View user stats payload
python scripts/inspect_payloads.py user USERNAME

# View course users payload
python scripts/inspect_payloads.py course-users SCHOOL TITLE_SLUG

# View course details payload
python scripts/inspect_payloads.py course-details SCHOOL TITLE_SLUG
```

### Preload cache
```bash
# Cache data for specific users
python scripts/preload_cache.py PegCult AnotherUser
```

### Monitor Redis
```bash
# Connect to Redis CLI
redis-cli

# View all cached keys
KEYS outreach:*

# View a specific cached value
GET outreach:user:USERNAME

# Monitor cache activity in real-time
MONITOR
```

## Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-httpx

# Run tests
pytest tests/
```

## Development Workflow

1. **Make changes** to Python files
2. **Server auto-reloads** (thanks to `--reload` flag)
3. **Test in browser** at http://localhost:8000/docs
4. **Check logs** in terminal

## Common Issues

### Redis connection refused
- Make sure Redis is running: `redis-cli ping` should return `PONG`
- Check Redis port in `.env` file

### Module not found
- Activate virtual environment: `source venv/bin/activate`
- Reinstall dependencies: `pip install -r requirements.txt`

### Slow responses
- First request to an endpoint is always slower (cache miss)
- Subsequent requests should be fast (served from cache)

## Next Steps

- Read [DEPLOYMENT.md](DEPLOYMENT.md) for Toolforge deployment
- Read the [API documentation](outreachdashboard_api_index.md) for API details
- Customize cache TTLs in `app/config.py`
- Add rate limiting or authentication as needed
