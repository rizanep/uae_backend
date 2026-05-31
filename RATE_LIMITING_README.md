# Rate Limiting Implementation Guide

## Overview

A comprehensive, production-grade rate limiting system has been implemented for your Django REST Framework API using DRF's built-in throttling system with Redis caching support. This system prevents abuse, protects sensitive endpoints, and ensures fair resource distribution.

---

## Architecture

### Components

1. **`core/throttling.py`** - Throttle class definitions
   - User-based throttles (authenticated users)
   - IP-based throttles (anonymous users)
   - Scope-specific throttle classes for different endpoints
   - Combined throttle pairs for mixed authentication

2. **`core/rate_limit_utils.py`** - Utility functions and decorators
   - Rate limit check functions
   - View/action decorators for easy application
   - Helper functions for testing and monitoring
   - IP extraction with proxy support

3. **`core/rate_limit_monitoring.py`** - Monitoring and analytics
   - Violation logging
   - Admin monitoring APIs
   - Statistics dashboard APIs
   - Prometheus metrics preparation

4. **`core/settings.py`** - Configuration
   - DRF throttle settings
   - Rate limit configurations by scope
   - Cache backend setup

---

## Rate Limiting Configuration

### Global Settings

All rate limits are configured in `settings.py` under `REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']`:

```python
DEFAULT_THROTTLE_RATES = {
    # General API endpoints (default for all unauthenticated endpoints)
    'user_general': '1000/hour',      # Authenticated users
    'anon_general': '200/hour',       # Anonymous users per IP

    # Authentication operations
    'user_auth': '50/hour',           # Password changes, logout
    'anon_auth': '30/hour',           # Login attempts per IP

    # OTP operations (very strict - prevents brute force)
    'anon_otp': '5/hour',             # OTP requests/verification per IP

    # Order operations
    'user_order': '100/hour',         # Order creation

    # Payment operations (strict - fraud prevention)
    'user_payment': '30/hour',        # Payment initiation/verification

    # Review operations
    'user_review': '20/hour',         # Review creation/modification

    # Contact/Support messages (very strict)
    'user_contact': '10/hour',        # Support ticket submission
    'anon_contact': '3/hour',         # Anonymous contact per IP
}
```

### Time Periods Supported
- `second` - Per second
- `minute` - Per minute
- `hour` - Per hour (recommended)
- `day` - Per day

---

## Throttle Classes

### For Authenticated Users

| Class | Rate | Use Case |
|-------|------|----------|
| `UserGeneralThrottle` | 1000/hour | Default for general operations |
| `UserAuthThrottle` | 50/hour | Password changes, logout, token refresh |
| `UserOrderThrottle` | 100/hour | Order creation |
| `UserPaymentThrottle` | 30/hour | Payment operations |
| `UserReviewThrottle` | 20/hour | Review creation/updates |
| `UserContactThrottle` | 10/hour | Support messages |

### For Anonymous Users (IP-Based)

| Class | Rate | Use Case |
|-------|------|----------|
| `AnonGeneralThrottle` | 200/hour | Default for general operations |
| `AnonAuthThrottle` | 30/hour | Login, registration attempts |
| `AnonOTPThrottle` | 5/hour | OTP requests (very strict) |
| `AnonContactThrottle` | 3/hour | Support messages (very strict) |

### Combined Throttles

For endpoints that serve both authenticated and anonymous users:

```python
@throttle_classes([UserAuthThrottle(), AnonAuthThrottle()])
```

---

## Applied Endpoints

### Authentication Endpoints (Users App)

- **OTPRequestView** - `POST /api/users/otp/request/`
  - Throttle: `CombinedOTPThrottle` (5/hour per IP)
  - Prevents OTP spam and brute force

- **OTPLoginView** - `POST /api/users/otp/login/`
  - Throttle: `CombinedOTPThrottle` (5/hour per IP)
  - Prevents brute force OTP guessing

- **LogoutView** - `POST /api/users/logout/`
  - Throttle: `CombinedAuthThrottle` (50/hour user, 30/hour IP)

- **GoogleAuthCallbackView** - `POST /api/users/google/callback/`
  - Throttle: `CombinedAuthThrottle` (50/hour user, 30/hour IP)

- **VerifyNewContactView** - `POST /api/users/verify-contact/`
  - Throttle: `CombinedAuthThrottle` (50/hour user)

- **UserViewSet.change_password** - `POST /api/users/change_password/`
  - Throttle: `UserAuthThrottle`, `AnonAuthThrottle` (50/hour user, 30/hour IP)

### Order Endpoints (Orders App)

- **OrderViewSet.checkout** - `POST /api/orders/checkout/`
  - Throttle: `CombinedOrderThrottle` (100/hour user)
  - Prevents order flooding

- **OrderViewSet.verify_payment** - `POST /api/orders/{id}/verify_payment/`
  - Throttle: `CombinedPaymentThrottle` (30/hour user)
  - Fraud prevention

### Review Endpoints (Reviews App)

- **ReviewViewSet.create/update/destroy**
  - Throttle: `CombinedReviewThrottle` (20/hour user)
  - Prevents review spam

### Contact Endpoints (Notifications App)

- **ContactMessageViewSet.create** - `POST /api/notifications/contact-messages/`
  - Throttle: `CombinedContactThrottle` (10/hour user, 3/hour IP)
  - Prevents contact form spam

---

## Usage Examples

### 1. Applying Rate Limiting to a View

```python
from core.rate_limit_utils import throttle_auth_view
from rest_framework.views import APIView

@throttle_auth_view
class MyAuthView(APIView):
    """This view will use combined auth throttling"""
    pass
```

### 2. Applying to a ViewSet Action

```python
from rest_framework.decorators import action, throttle_classes
from core.throttling import UserOrderThrottle

class MyViewSet(viewsets.ModelViewSet):
    @throttle_classes([UserOrderThrottle()])
    @action(detail=False, methods=['post'])
    def my_action(self, request):
        # This action will be rate limited
        pass
```

### 3. Override Throttles by Action

```python
from rest_framework import viewsets

class MyViewSet(viewsets.ModelViewSet):
    def get_throttles(self):
        if self.action in ['create', 'update']:
            # Strict throttling for writes
            from core.throttling import UserReviewThrottle, AnonGeneralThrottle
            return [UserReviewThrottle(), AnonGeneralThrottle()]
        # Default throttling for reads
        return super().get_throttles()
```

### 4. Manual Rate Limit Check

```python
from core.rate_limit_utils import check_rate_limit
from rest_framework.response import Response

def my_view(request):
    is_allowed, remaining, retry_after = check_rate_limit(
        request, 
        scope='custom_scope',
        requests_limit=10,
        time_window=3600  # 1 hour
    )
    
    if not is_allowed:
        return Response(
            {'error': f'Rate limited. Retry after {retry_after}s'},
            status=429,
            headers={'Retry-After': str(retry_after)}
        )
    
    # Process request...
```

---

## Admin Monitoring APIs

### Check Rate Limit Status

**GET** `/api/admin/rate-limit/status/`

Query parameters:
- `user_id` - Check limits for a specific user
- `ip_address` - Check limits for a specific IP
- `scopes` - Comma-separated scopes to check

Example:
```bash
curl "http://localhost:8000/api/admin/rate-limit/status/?user_id=123&scopes=user_auth,user_order"
```

Response:
```json
{
    "client_ident": "user_123",
    "timestamp": "2026-03-08T12:34:56.789Z",
    "rate_limits": {
        "user_auth": {
            "current_requests": 15,
            "rate_config": "50/hour",
            "cache_key": "ratelimit:user_auth:user_123"
        },
        "user_order": {
            "current_requests": 5,
            "rate_config": "100/hour",
            "cache_key": "ratelimit:user_order:user_123"
        }
    }
}
```

### Reset Rate Limits

**POST** `/api/admin/rate-limit/status/`

Request body:
```json
{
    "user_id": 123,
    "scopes": "user_auth,user_order"
}
```

Response:
```json
{
    "client_ident": "user_123",
    "scopes_reset": 2,
    "total_scopes": 2,
    "timestamp": "2026-03-08T12:34:56.789Z"
}
```

### View Statistics

**GET** `/api/admin/rate-limit/stats/`

Shows current rate limiting configuration and cache backend.

---

## Cache Backend

### Using Redis (Production Recommended)

Configure Redis in `.env`:
```bash
USE_REDIS_CACHE=True
REDIS_CACHE_URL=redis://127.0.0.1:6379/1
```

### Using Local Memory Cache (Development)

Default uses Django's local memory cache:
```python
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "uae_backend",
    }
}
```

**Note:** Local memory cache works but doesn't persist across server restarts and doesn't work in multi-process environments. Use Redis for production.

---

## Response Headers

When rate limited, responses include:
- `Retry-After` - Seconds to wait before retrying

Example response (429 Too Many Requests):
```json
{
    "detail": "Request was throttled. Expected available in 3420 seconds."
}
```

---

## Logging

Rate limit violations are logged with warnings:

```
WARNING - Rate limit exceeded: UserAuthThrottle - User: 123 - IP: 192.168.1.1 - Path: /api/users/change_password/
WARNING - Rate limit triggered: POST /api/orders/checkout/ - IP: 192.168.1.1 - User: anonymous
```

To enable file logging, update `LOGGING` in settings or call:
```python
from core.rate_limit_monitoring import configure_rate_limit_logging
configure_rate_limit_logging()
```

---

## Best Practices

### 1. Choose Appropriate Limits

- **Read operations**: Higher limits (already have default 1000/hour)
- **Write operations**: Lower limits (20-100/hour depending on criticality)
- **Authentication**: Very strict (5-50/hour) to prevent brute force
- **Payment**: Extremely strict (30/hour) for fraud prevention

### 2. Monitor Violations

Regularly check for patterns in `rate_limit/stats/` API to adjust limits if needed.

### 3. Client Handling

Educate frontend developers to handle 429 responses:
```javascript
// Example: Retry with exponential backoff
async function retryWithBackoff(url, options, maxRetries = 3) {
    for (let i = 0; i < maxRetries; i++) {
        const response = await fetch(url, options);
        if (response.status !== 429) return response;
        
        const retryAfter = response.headers.get('Retry-After') || Math.pow(2, i);
        await new Promise(r => setTimeout(r, retryAfter * 1000));
    }
}
```

### 4. IP Whitelisting

For internal services:
```python
# In settings.py or middleware
RATE_LIMIT_WHITELIST_IPS = ['127.0.0.1', '10.0.0.0/8']
```

### 5. Gradually Tighten

Start with generous limits and gradually reduce based on monitoring data.

---

## Troubleshooting

### Rate Limits Not Working

1. Check `DEFAULT_THROTTLE_CLASSES` is set in `REST_FRAMEWORK`
2. Verify cache backend is working: `python manage.py shell`
   ```python
   from django.core.cache import cache
   cache.set('test', 'value')
   print(cache.get('test'))  # Should print 'value'
   ```
3. Ensure Redis is running (if using Redis): `redis-cli ping`

### Unable to Reach API After Rate Limit

1. Use admin API to reset limits
2. Clear Redis cache: `redis-cli FLUSHDB`
3. Or wait for the rate limit window to expire

### High False Positives

1. Check if X-Forwarded-For header is properly set by load balancer
2. Consider using user-based throttling instead of IP-based
3. Increase rate limits for that scope

---

## Security Considerations

1. **OTP Protection**: Very strict limits (5/hour) prevent brute force attacks
2. **Authentication Protection**: Rate limiting on login/registration prevents credential stuffing
3. **Payment Protection**: Strict limits (30/hour) prevent fraud attempts
4. **Distributed Attacks**: IP-based limits for anonymous users; upgrade to user-based after authentication
5. **Admin Bypass**: Can be configured in settings via `ENABLE_ADMIN_RATE_LIMIT`

---

## Future Enhancements

1. **Prometheus Integration**: Export metrics for monitoring
2. **Database Backend**: Store violations in database for long-term analysis
3. **Dynamic Rate Limiting**: Adjust limits based on system load
4. **Geolocation-Based**: Different limits by regions
5. **Machine Learning**: Detect suspicious patterns automatically
6. **GraphQL Support**: If adding GraphQL API

---

## File Structure

```
uae_backend/
├── core/
│   ├── throttling.py              # Throttle class definitions
│   ├── rate_limit_utils.py        # Utility functions and decorators
│   ├── rate_limit_monitoring.py   # Monitoring and analytics
│   ├── settings.py                # Updated with throttle config
│   └── urls.py                    # Added monitoring endpoints
├── Users/
│   └── views.py                   # Rate limiting applied to auth views
├── Orders/
│   └── views.py                   # Rate limiting on checkout/payment
├── Reviews/
│   └── views.py                   # Rate limiting on review operations
└── Notifications/
    └── views.py                   # Rate limiting on contact messages
```

---

## Support

For questions or issues:
1. Check the examples above
2. Review the inline documentation in `throttling.py`
3. Check logs: `tail -f logs/rate_limiting.log`
4. Use admin APIs to debug

---

**Implementation Date**: March 8, 2026  
**Status**: Production Ready  
**Redis Support**: Yes  
**Monitoring**: Yes  
**Admin API**: Yes
