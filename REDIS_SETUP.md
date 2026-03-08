# Rate Limiting - Redis Configuration Guide

## Quick Start

For production, Redis is highly recommended for distributed rate limiting.

### 1. Install Redis (if not already installed)

#### Windows (using WSL or Docker)
```powershell
# Using WSL
wsl
sudo apt-get install redis-server
redis-server

# Or using Docker
docker run -d -p 6379:6379 redis:latest
```

#### Ubuntu/Debian
```bash
sudo apt-get install redis-server
sudo systemctl start redis-server
```

#### macOS
```bash
brew install redis
brew services start redis
```

### 2. Update Environment Variables

Create/update `.env` file in the project root:

```env
# Cache Configuration
USE_REDIS_CACHE=True
REDIS_CACHE_URL=redis://127.0.0.1:6379/1

# Celery Configuration (if using Celery)
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0
```

### 3. Update Django Settings (Already Done)

The project is already configured to use Redis. In `core/settings.py`:

```python
USE_REDIS_CACHE = os.environ.get("USE_REDIS_CACHE", "False").lower() == "true"

if USE_REDIS_CACHE:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": os.environ.get("REDIS_CACHE_URL", "redis://127.0.0.1:6379/1"),
            "TIMEOUT": CACHE_DEFAULT_TIMEOUT,
            "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
            "KEY_PREFIX": "uae_backend",
        }
    }
```

### 4. Test Redis Connection

```python
python manage.py shell

from django.core.cache import cache

# Test set and get
cache.set('test_key', 'test_value', 60)
print(cache.get('test_key'))  # Should print: test_value

# Verify rate limiting keys are being stored
import redis
r = redis.Redis.from_url('redis://127.0.0.1:6379/1')
keys = r.keys('ratelimit:*')
print(f"Found {len(keys)} rate limit keys")
```

## Troubleshooting

### Redis Connection Refused

```bash
# Check if Redis is running
redis-cli ping  # Should respond with PONG

# Start Redis if not running
redis-server

# Or check Windows Service
# For Docker: docker ps
```

### Rate Limiting Not Working in Production

1. Verify `USE_REDIS_CACHE=True` in `.env`
2. Verify `REDIS_CACHE_URL` is correct
3. Check Redis is accessible from application server
4. Run: `python manage.py shell` and test connection

### Multiple Django Instances

With multiple instances, ensure they all connect to the same Redis instance:

```env
# Same for all instances
REDIS_CACHE_URL=redis://redis-host:6379/1
```

## Advanced Configuration

### Redis Cluster (Production HA)

For high availability, use Redis Cluster:

```env
REDIS_CACHE_URL=rediscluster://node1:6379,node2:6379,node3:6379
```

Requires `redis-py-cluster` package:
```bash
pip install redis-py-cluster
```

### Redis Sentinel

For automatic failover:

```env
REDIS_CACHE_URL=sentinel://redis-sentinel:26379/mymaster/0
```

### Authentication

If Redis requires password:

```env
REDIS_CACHE_URL=redis://:password@127.0.0.1:6379/1
```

## Performance Tuning

### Redis Configuration File

Create `redis.conf`:

```conf
# Maximum memory policy - evict least recently used
maxmemory-policy allkeys-lru

# Set max memory (e.g., 256MB)
maxmemory 268435456

# Enable append-only file for persistence
appendonly yes
appendfsync everysec
```

Start with conf file:
```bash
redis-server /path/to/redis.conf
```

### Django Cache Timeout

Adjust in `.env`:

```env
CACHE_DEFAULT_TIMEOUT=300  # Seconds (default 5 minutes)
```

Or in settings:
```python
# settings.py
CACHE_DEFAULT_TIMEOUT = int(os.environ.get("CACHE_DEFAULT_TIMEOUT", "300"))
```

## Monitoring Redis

### Redis CLI

```bash
# Connect to Redis
redis-cli

# Check memory usage
redis_cli> INFO memory

# Check connected clients
redis-cli> INFO clients

# Monitor live commands
redis-cli> MONITOR

# Check rate limit keys
redis-cli> KEYS "ratelimit:*"
redis-cli> GET "ratelimit:user_auth:user_123"

# Clear specific keys
redis-cli> DEL ratelimit:*
```

### Redis Insight (GUI)

Free tool: https://redis.com/redis-enterprise/redis-insight/

Download and connect to your Redis instance for visual monitoring.

## Docker Setup (Optional)

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  redis:
    image: redis:latest
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  db:
    image: postgres:14
    environment:
      POSTGRES_DB: ecommerceuae
      POSTGRES_USER: ecommerce_user
      POSTGRES_PASSWORD: StrongPassword@123
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  redis_data:
  postgres_data:
```

Start:
```bash
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs redis
```

## Testing Rate Limits with Redis

```python
# Django shell
python manage.py shell

from django.core.cache import cache
from core.rate_limit_utils import check_rate_limit
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser

# Create a mock request
factory = RequestFactory()
request = factory.get('/')
request.user = AnonymousUser()
request.META['REMOTE_ADDR'] = '192.168.1.1'

# Test rate limiting
for i in range(6):
    is_allowed, remaining, retry = check_rate_limit(
        request, 'test_scope', 5, 3600
    )
    print(f"Request {i+1}: {'Allowed' if is_allowed else 'Blocked'} (Remaining: {remaining})")

# Expected output:
# Request 1: Allowed (Remaining: 4)
# Request 2: Allowed (Remaining: 3)
# Request 3: Allowed (Remaining: 2)
# Request 4: Allowed (Remaining: 1)
# Request 5: Allowed (Remaining: 0)
# Request 6: Blocked (Remaining: 0)
```

## Clearing Rate Limits

### Clear All Rate Limits

```python
# Django shell
python manage.py shell

from django.core.cache import cache

# Clear all rate limit keys
cache.delete_many(cache.keys('ratelimit:*'))

# Or via Redis CLI
redis-cli
> FLUSHDB  # Clears entire database (use with caution!)
> DEL ratelimit:*  # Clear only rate limit keys
```

### Clear for Specific User

```python
from django.core.cache import cache

# Clear all limits for a specific user
user_id = 123
cache.delete_many([
    f'ratelimit:user_auth:user_{user_id}',
    f'ratelimit:user_order:user_{user_id}',
    f'ratelimit:user_general:user_{user_id}',
])
```

## Debugging with Logs

Enable debug logging:

```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'logs/rate_limiting.log',
        },
    },
    'loggers': {
        'rate_limiting': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
```

Then run and watch logs:
```bash
tail -f logs/rate_limiting.log
```

## Production Checklist

- [ ] Redis installed and running
- [ ] `USE_REDIS_CACHE=True` in `.env`
- [ ] `REDIS_CACHE_URL` points to production Redis
- [ ] Redis persistence enabled (appendonly yes)
- [ ] Redis memory limits configured
- [ ] Monitoring in place (Redis Insight or similar)
- [ ] Backup strategy for Redis data
- [ ] Test rate limiting works end-to-end
- [ ] Admin APIs functional (`/api/admin/rate-limit/*`)
- [ ] Logging configured and monitored

---

**Note**: Make sure Redis is running before starting the Django application!
