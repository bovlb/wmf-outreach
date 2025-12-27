# Deployment Guide

This guide covers deployment to Wikimedia Toolforge.

## Prerequisites

1. **Toolforge account**: Request access at https://wikitech.wikimedia.org
2. **Tool approved**: Create a tool via `toolforge tools create <toolname>`
3. **SSH access**: `ssh <username>@login.toolforge.org`

## Initial Setup

### 1. Clone repository on Toolforge

```bash
ssh <username>@login.toolforge.org
become <toolname>
cd ~
git clone <repository-url> .
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

## Starting the Service

### Option A: Using webservice command

```bash
# Start the webservice
webservice --backend=kubernetes python3.11 start
```

This will automatically look for and execute `toolforge/start.sh`.

### Option B: Custom buildpack (if needed)

If you need more control, create a `service.template`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ tool }}
spec:
  type: NodePort
  ports:
    - port: 8000
      protocol: TCP
      targetPort: 8000
  selector:
    name: {{ tool }}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ tool }}
spec:
  replicas: 1
  selector:
    matchLabels:
      name: {{ tool }}
  template:
    metadata:
      labels:
        name: {{ tool }}
    spec:
      containers:
        - name: {{ tool }}
          image: {{ image }}
          command: ["/data/project/{{ tool }}/toolforge/start.sh"]
          ports:
            - containerPort: 8000
          env:
            - name: PORT
              value: "8000"
```

## Accessing the Service

Your service will be available at:

```
https://<toolname>.toolforge.org
```

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
# Using kubectl
kubectl logs -l name=<toolname> --tail=100 -f

# Or webservice logs
webservice --backend=kubernetes logs
```

### Check service status

```bash
webservice --backend=kubernetes status
```

## Updating the Service

```bash
# 1. Pull latest changes
git pull

# 2. Install new dependencies (if any)
source venv/bin/activate
pip install -r requirements.txt

# 3. Restart service
webservice --backend=kubernetes restart
```

## Stopping the Service

```bash
webservice --backend=kubernetes stop
```

## Troubleshooting

### Service won't start

1. Check logs: `webservice --backend=kubernetes logs`
2. Verify Redis access: `redis-cli -h redis.svc.eqiad.wmflabs ping`
3. Check environment variables: `toolforge envvars list`

### Redis connection issues

```bash
# Test Redis connection
redis-cli -h redis.svc.eqiad.wmflabs -p 6379 ping
# Should return: PONG
```

### Port conflicts

The service uses the `$PORT` environment variable provided by Toolforge. Don't hardcode port numbers.

### Memory limits

Default Kubernetes pods have limited memory. If you need more:

```bash
# Request larger pod
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
```

### Increase worker count

Edit `toolforge/start.sh` to add more workers:

```bash
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --workers 4
```

## References

- [Toolforge Web Services](https://wikitech.wikimedia.org/wiki/Help:Toolforge/Web)
- [Toolforge Redis](https://wikitech.wikimedia.org/wiki/Help:Toolforge/Redis)
- [Toolforge Kubernetes](https://wikitech.wikimedia.org/wiki/Help:Toolforge/Kubernetes)
