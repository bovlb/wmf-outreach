# Deployment Guide

This guide covers deployment to Wikimedia Toolforge.

## Prerequisites

1. **Toolforge account**: Request access at https://wikitech.wikimedia.org
2. **Tool approved**: Create a tool via `toolforge tools create <toolname>`
3. **SSH access**: `ssh <username>@login.toolforge.org`

## Deployment Methods

Toolforge supports two deployment approaches. The **buildpack method** (recommended) is simpler and more modern.

---

## Method 1: Buildpack Deployment (Recommended)

This method builds a container image directly from your Git repository.

### 1. Connect to Toolforge

```bash
ssh <username>@login.toolforge.org
become <toolname>
```

### 2. Configure environment variables

```bash
# Set Redis configuration
toolforge envvars create REDIS_HOST redis.svc.eqiad.wmflabs
toolforge envvars create REDIS_PORT 6379

# Optional: customize cache TTLs
toolforge envvars create USER_CACHE_TTL 3600
toolforge envvars create COURSE_CACHE_TTL 86400
```

### 3. Build from Git repository

```bash
# Build the container image from your Git repository
toolforge build start https://github.com/bovlb/wmf-outreach.git
```

This will:
- Clone the repository
- Detect Python and install dependencies from `requirements.txt`
- Build a container image
- Tag it for use with webservice

You can check build status:
```bash
toolforge build show
```

### 4. Start the webservice

```bash
# Start using the built image
toolforge webservice buildservice start
```

### 5. Access your service

Your service will be available at:
```
https://<toolname>.toolforge.org
```

### Updating with buildpack

When you push changes to your Git repository:

```bash
# Rebuild from latest Git
toolforge build start https://github.com/bovlb/wmf-outreach.git

# Restart the webservice to use new image
toolforge webservice buildservice restart
```

---

## Method 2: Traditional Deployment (Alternative)

## Method 2: Traditional Deployment (Alternative)

This method involves manually cloning the repository and managing dependencies.

### 1. Clone repository on Toolforge

```bash
ssh <username>@login.toolforge.org
become <toolname>
cd ~
git clone https://github.com/bovlb/wmf-outreach.git .
```

### 2. Install dependencies

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 3. Configure environment

```bash
# Set Redis configuration
toolforge envvars create REDIS_HOST redis.svc.eqiad.wmflabs
toolforge envvars create REDIS_PORT 6379

# Optional: customize cache TTLs
toolforge envvars create USER_CACHE_TTL 3600
toolforge envvars create COURSE_CACHE_TTL 86400
```

### 4. Make start script executable

```bash
chmod +x toolforge/start.sh
```

### 5. Start the webservice

```bash
# Start using traditional method
webservice --backend=kubernetes python3.11 start
```

This will automatically execute `toolforge/start.sh`.

### Updating with traditional method

```bash
# Pull latest changes
git pull

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Restart service
webservice --backend=kubernetes restart
```

---

## Testing Endpoints

```bash
# Health check
curl https://<toolname>.toolforge.org/health

# User courses
curl https://<toolname>.toolforge.org/api/users/USERNAME

# Course users
curl https://<toolname>.toolforge.org/api/courses/SCHOOL/TITLE_SLUG/users

# Course details
curl https://<toolname>.toolforge.org/api/courses/SCHOOL/TITLE_SLUG
```

## Monitoring

### View logs

```bash
# For buildpack deployment
toolforge webservice buildservice logs

# For traditional deployment
webservice --backend=kubernetes logs

# Or using kubectl directly
kubectl logs -l name=<toolname> --tail=100 -f
```

### Check service status

```bash
# For buildpack deployment
toolforge webservice buildservice status

# For traditional deployment
webservice --backend=kubernetes status
```

### Check build status

```bash
# Only for buildpack method
toolforge build show
toolforge build logs
```

## Stopping the Service

```bash
# For buildpack deployment
toolforge webservice buildservice stop

# For traditional deployment
webservice --backend=kubernetes stop
```

## Troubleshooting

### Build fails

```bash
# Check build logs
toolforge build logs

# Common issues:
# - Missing requirements.txt
# - Invalid Python version in requirements
# - Dependency conflicts
```

### Service won't start

1. Check logs: `toolforge webservice buildservice logs`
2. Verify Redis access: `redis-cli -h redis.svc.eqiad.wmflabs ping`
3. Check environment variables: `toolforge envvars list`
4. Verify build completed: `toolforge build show`

### Redis connection issues

```bash
# Test Redis connection
redis-cli -h redis.svc.eqiad.wmflabs -p 6379 ping
# Should return: PONG
```

### Port conflicts

The service uses the `$PORT` environment variable provided by Toolforge. Don't hardcode port numbers.

### Memory or resource limits

If you need more resources with buildpack:

```bash
# The buildpack method uses standard Kubernetes resources
# Contact Toolforge admins if you need increased limits
```

For traditional method with custom jobs:

```bash
toolforge jobs run --command "./toolforge/start.sh" --image python3.11 --mem 1Gi my-job
```

## Cache Management

### Preload common queries

```bash
source venv/bin/activate
python scripts/preload_cache.py USERNAME1 USERNAME2 ...
```

### Clear cache

```bash
# Connect to Redis
redis-cli -h redis.svc.eqiad.wmflabs

# List all keys
KEYS outreach:*

# Delete specific key
DEL outreach:user:USERNAME

# Delete all outreach keys
EVAL "return redis.call('del', unpack(redis.call('keys', 'outreach:*')))" 0
```

## Security Notes

1. **CORS**: The service allows all origins by default. For production, update `app/main.py` to restrict origins:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://www.wikidata.org",
        "https://wikidata.org",
    ],
    ...
)
```

2. **Rate limiting**: Consider adding rate limiting for production use.

3. **Authentication**: The Outreach Dashboard API doesn't require authentication, but you may want to add API keys for your service.

## Performance Tuning

### Adjust cache TTLs

Modify environment variables based on your usage patterns:

```bash
# Shorter TTL for frequently changing data
toolforge envvars create USER_CACHE_TTL 1800  # 30 minutes

# Longer TTL for stable data
toolforge envvars create COURSE_CACHE_TTL 604800  # 7 days

# Restart to apply changes
toolforge webservice buildservice restart  # or webservice --backend=kubernetes restart
```

### Increase worker count

Edit `toolforge/start.sh` to add more workers:

```bash
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --workers 4
```

Then rebuild and restart:
```bash
# For buildpack
toolforge build start https://github.com/bovlb/wmf-outreach.git
toolforge webservice buildservice restart

# For traditional
git pull
webservice --backend=kubernetes restart
```

## Comparison: Buildpack vs Traditional

| Feature | Buildpack (Recommended) | Traditional |
|---------|------------------------|-------------|
| **Setup complexity** | Low - one command | High - manual steps |
| **Updates** | Rebuild from Git | Pull + restart |
| **Reproducibility** | High - containerized | Medium - depends on env |
| **Disk usage** | Low - no local clone needed | Higher - full repo + venv |
| **Debugging** | Check build logs | Direct file access |
| **Best for** | Production, CI/CD | Development, customization |

## References

- [Toolforge Build Service](https://wikitech.wikimedia.org/wiki/Help:Toolforge/Build_Service)
- [Toolforge Web Services](https://wikitech.wikimedia.org/wiki/Help:Toolforge/Web)
- [Toolforge Redis](https://wikitech.wikimedia.org/wiki/Help:Toolforge/Redis)
- [Toolforge Kubernetes](https://wikitech.wikimedia.org/wiki/Help:Toolforge/Kubernetes)
