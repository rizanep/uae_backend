# Rate Limiting - Quick Start Guide

## For API Users/Frontend Developers

### What Changed?
Your API now has **rate limiting** to prevent abuse and ensure fair resource usage.

### What You Need to Know

1. **You might get 429 errors** (Too Many Requests)
   ```json
   {
       "detail": "Request was throttled. Expected available in 3420 seconds."
   }
   ```

2. **Check the `Retry-After` header**
   - Tells you how many seconds to wait
   - Example: `Retry-After: 3420`

3. **Implement retry logic** (recommended)
   ```javascript
   async function makeRequest(url, options) {
       const response = await fetch(url, options);
       
       if (response.status === 429) {
           const retryAfter = response.headers.get('Retry-After');
           console.log(`Rate limited. Retry after ${retryAfter} seconds`);
           
           // Wait and retry
           await sleep(retryAfter * 1000);
           return makeRequest(url, options); // Retry
       }
       
       return response;
   }
   ```

### Current Limits

| Operation | Limit | Why |
|-----------|-------|-----|
| Browse products | 1000/hour | No restriction for browsing |
| Login attempt | 30/hour (per IP) | Prevent brute force |
| Password change | 50/hour | Security |
| OTP request | 5/hour | Prevent spam |
| Place order | 100/hour | Prevent DOS |
| Payment | 30/hour | Fraud prevention |
| Submit review | 20/hour | Prevent spam |
| Contact form | 3/hour (per IP) | Prevent spam |

### What This Means

- **For normal users**: No impact, limits are very high
- **For attackers/bots**: Immediate blocking
- **For bulk operations**: Plan requests over time

### Example: Handling 429

```javascript
// Better: With exponential backoff
async function retryWithBackoff(url, options, maxRetries = 3) {
    for (let attempt = 0; attempt < maxRetries; attempt++) {
        const response = await fetch(url, options);
        
        if (response.status === 429) {
            const retryAfter = parseInt(response.headers.get('Retry-After')) || Math.pow(2, attempt);
            console.log(`Attempt ${attempt + 1}: Rate limited, waiting ${retryAfter}s...`);
            await sleep(retryAfter * 1000);
            continue;
        }
        
        return response;
    }
    throw new Error('Max retries exceeded');
}
```

---

## For Backend Developers

### Adding Rate Limiting to New Endpoints

#### Option 1: Use Decorators (Easiest)
```python
from core.rate_limit_utils import throttle_auth_view
from rest_framework.views import APIView

@throttle_auth_view
class MyAuthView(APIView):
    """This view has auth rate limiting"""
    def post(self, request):
        pass
```

#### Option 2: ViewSet Actions
```python
from rest_framework import viewsets
from rest_framework.decorators import action, throttle_classes
from core.throttling import UserAuthThrottle

class MyViewSet(viewsets.ModelViewSet):
    @throttle_classes([UserAuthThrottle()])
    @action(detail=False, methods=['post'])
    def my_action(self, request):
        pass
```

#### Option 3: Override get_throttles()
```python
from rest_framework import viewsets
from core.throttling import UserReviewThrottle, AnonGeneralThrottle

class MyViewSet(viewsets.ModelViewSet):
    def get_throttles(self):
        if self.action in ['create', 'update']:
            return [UserReviewThrottle(), AnonGeneralThrottle()]
        return super().get_throttles()
```

### Available Decorators

```python
from core.rate_limit_utils import (
    throttle_auth_view,      # 50/hr user, 30/hr IP
    throttle_otp_view,       # 5/hr per IP
    throttle_payment_view,   # 30/hr user
    throttle_order_view,     # 100/hr user
    throttle_review_view,    # 20/hr user
    throttle_contact_view,   # 10/hr user, 3/hr IP
)
```

### Testing Rate Limits

```python
from django.test import TestCase
from rest_framework.test import APIClient

class MyRateLimitTest(TestCase):
    def test_rate_limit(self):
        client = APIClient()
        
        # Make requests until limited
        for i in range(100):
            response = client.post('/api/my-endpoint/')
            
            if response.status_code == 429:
                print(f"Rate limited after {i} requests")
                break
            
            self.assertIn(response.status_code, [200, 201])
```

### Customizing Limits

Edit `core/settings.py`:

```python
REST_FRAMEWORK = {
    # ... other config ...
    'DEFAULT_THROTTLE_RATES': {
        'user_general': '1000/hour',     # Change this
        'user_auth': '50/hour',          # Or this
        'anon_otp': '5/hour',            # Or this
        # ... etc
    },
}
```

---

## For DevOps/Admins

### Production Setup

1. **Enable Redis** (recommended)
   ```bash
   # Install Redis
   sudo apt-get install redis-server
   redis-server
   ```

2. **Configure .env**
   ```env
   USE_REDIS_CACHE=True
   REDIS_CACHE_URL=redis://localhost:6379/1
   ```

3. **Verify**
   ```bash
   python manage.py check  # Should pass
   redis-cli ping          # Should respond PONG
   ```

### Monitoring

#### Check Rate Limits for a User
```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  "http://api.example.com/api/admin/rate-limit/status/?user_id=123"
```

#### Reset Rate Limits
```bash
curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"user_id": 123}' \
  "http://api.example.com/api/admin/rate-limit/status/"
```

#### View Statistics
```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  "http://api.example.com/api/admin/rate-limit/stats/"
```

### Troubleshooting

**Problem**: Rate limits not working
```bash
python manage.py check  # Check for errors
redis-cli ping          # Verify Redis is running
```

**Problem**: "Too strict, users complaining"
```python
# In core/settings.py, increase the limits
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['user_general'] = '2000/hour'
```

**Problem**: Clear all rate limits
```bash
redis-cli FLUSHDB  # Warning: clears all Redis data!
# Or specifically:
redis-cli DEL ratelimit:*
```

---

## Performance Tips

### For Frontend
- Batch requests when possible
- Implement exponential backoff retry
- Cache responses on client side
- Respect rate limit headers

### For Backend
- Use Redis (not local memory) in production
- Monitor rate limit violations
- Adjust limits based on real usage data
- Don't put multiple endpoints at same limit

### For DevOps
- Monitor Redis memory usage
- Set up alerts for high violation rates
- Review logs weekly
- Adjust limits quarterly

---

## FAQ

**Q: Will this break my app?**  
A: No. Normal users won't hit the limits. Only abusive traffic is blocked.

**Q: What if a legitimate user hits the limit?**  
A: Rate limits are very forgiving. If you hit them, you're either:
- Making lots of API requests (bad practice - cache results)
- DoS attacking (that's the point!)
- Testing/bulk operations (contact admin to whitelist)

**Q: Can I disable rate limiting?**  
A: Yes, but not recommended. Remove `DEFAULT_THROTTLE_CLASSES` from settings.

**Q: Why such strict limits on OTP and payments?**  
A: Security. These are high-value/high-risk operations that need protection.

**Q: Can I adjust limits per user?**  
A: Currently no, but you can reset individual users via admin API.

**Q: Do I need Redis?**  
A: No, but local cache doesn't work across multiple servers.

---

## Limits Reference Card

```
BROWSING                      AUTHENTICATION
├─ General: 1000/hr          ├─ Login: 30/hr
├─ Products: 1000/hr         ├─ OTP Request: 5/hr
├─ Reviews: 1000/hr          ├─ OTP Verify: 5/hr
└─ Categories: 1000/hr       ├─ Password Change: 50/hr
                             └─ Token Refresh: 50/hr

ACTIONS                       SENSITIVE OPS
├─ Create Review: 20/hr       ├─ Checkout: 100/hr
├─ Create Order: 100/hr       ├─ Payment: 30/hr
├─ Create Cart Item: 1000/hr  └─ Contact Form: 3/hr (anon)
└─ Contact Form: 10/hr

All limits are PER HOUR and PER USER (or per IP for anonymous)
```

---

## Documentation

For detailed info:
- **Frontend help**: Check API error responses
- **Backend help**: See `RATE_LIMITING_README.md`
- **DevOps help**: See `REDIS_SETUP.md`
- **Code reference**: See `core/throttling.py` docstrings

---

## Need Help?

1. Check this guide
2. Try `python manage.py check`
3. Check application logs
4. Review `RATE_LIMITING_README.md`
5. Contact the development team

---

**That's it!** Rate limiting is now active and protecting your API. 🛡️
