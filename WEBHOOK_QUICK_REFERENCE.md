# Webhook Implementation Quick Reference

## What Was Added

### 1. **Webhook Endpoint**
- **URL**: `POST /api/orders/webhook/ziina/`
- **Purpose**: Receives real-time payment status updates from Ziina
- **Auto-authentication**: Allowed for all users (webhook is external)

### 2. **Security Features**
- **HMAC-SHA256 Verification**: Validates that webhooks come from Ziina
- **Constant-Time Comparison**: Prevents timing attacks
- **Atomic Transactions**: Ensures data consistency
- **Comprehensive Logging**: All events logged for audit trail

### 3. **Automatic Behavior**
When webhook indicates payment `COMPLETED`:
- ✅ Payment status → `SUCCESS`
- ✅ Order status → `PAID` (via signal)
- ✅ Receipt generated (via signal)
- ✅ Customer notified (via signal)

When webhook indicates payment `FAILED|EXPIRED|CANCELLED`:
- ✅ Payment status → `FAILED`
- ✅ Order remains `PENDING` (user can retry)

## Configuration

### Step 1: Set Webhook Secret
Add to `.env`:
```env
ZIINA_WEBHOOK_SECRET=your_webhook_secret_key
```

### Step 2: Register Webhook with Ziina
```bash
curl -X POST https://api-v2.ziina.com/api/webhook \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://yourdomain.com/api/orders/webhook/ziina/",
    "secret": "your_webhook_secret_key"
  }'
```

## Integration Summary

| Component | Change |
|-----------|--------|
| **views.py** | Added `ziina_webhook()` function + `verify_webhook_signature()` + imports |
| **urls.py** | Added webhook route mapping |
| **Security** | HMAC verification, constant-time comparison, atomic transactions |
| **Signals** | Existing signals handle payment_success → order update + receipt |

## Advantages Over Manual Polling

| Aspect | Webhook | verify_payment (polling) |
|--------|---------|------------------------|
| **Latency** | < 1 second | 30+ seconds |
| **API Calls** | Only on payment change | Every 30 seconds |
| **Server Load** | Lower | Higher |
| **User Experience** | Instant updates | Delayed |

## Key Methods

### HMAC Verification
```python
def verify_webhook_signature(request_body, signature, webhook_secret):
    """Validates webhook authenticity"""
    expected_signature = hmac.new(
        webhook_secret.encode(),
        request_body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected_signature)
```

### Webhook Handler
```python
@csrf_exempt
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@transaction.atomic
def ziina_webhook(request):
    """Processes payment_intent.status.updated events"""
    # 1. Verify signature
    # 2. Parse payload
    # 3. Find payment record
    # 4. Update status
    # 5. Signals handle order updates
```

## Webhook Payload Example

```json
{
  "event": "payment_intent.status.updated",
  "data": {
    "id": "pi_abc123xyz789",
    "status": "COMPLETED",
    "amount": 50000,
    "currency_code": "AED",
    "message": "Order #123"
  }
}
```

## Response Example

```json
{
  "success": true,
  "message": "Webhook processed successfully",
  "payment_id": 42,
  "order_id": 123,
  "status": "SUCCESS"
}
```

## Testing

### Test Signature Verification
```bash
# Create payload
PAYLOAD='{"event":"payment_intent.status.updated","data":{"id":"pi_test","status":"COMPLETED"}}'
SECRET="test_secret"

# Generate signature
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" -hex | awk '{print $2}')

# Send webhook
curl -X POST http://localhost:8000/api/orders/webhook/ziina/ \
  -H "X-Webhook-Signature: $SIGNATURE" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD"
```

## Monitoring

### Check Logs
```bash
# View webhook events
grep "Webhook processed" debug.log

# View errors
grep "Webhook processing error" debug.log

# View signature failures
grep "signature verification failed" debug.log
```

### Database Verification
```python
# Check payment status was updated
Payment.objects.filter(ziina_payment_intent_id='pi_abc123').values('status', 'provider_response')

# Check order was marked as PAID
Order.objects.filter(id=123).values('status')
```

## Status Changes Explained

| Event | Before | After | Order Status | Receipt | Notification |
|-------|--------|-------|--------------|---------|--------------|
| COMPLETED | PENDING | SUCCESS | PENDING→PAID | Created | Sent |
| FAILED | PENDING | FAILED | PENDING | Not created | Not sent |
| EXPIRED | PENDING | FAILED | PENDING | Not created | Not sent |
| CANCELLED | PENDING | FAILED | PENDING | Not created | Not sent |

## Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Payment updated |
| 400 | Bad payload | Check webhook format |
| 401 | Invalid signature | Verify secret matches |
| 404 | Payment not found | Check payment creation |
| 500 | Server error | Check logs |

## Files Modified

1. **Orders/views.py**
   - Added webhook handler function
   - Added signature verification function
   - Added imports for hmac, hashlib, json, transaction, csrf_exempt, api_view

2. **Orders/urls.py**
   - Added webhook URL pattern
   - Imported ziina_webhook function

3. **WEBHOOK_README.md** (new)
   - Complete webhook documentation

## No Changes Required To

- ✅ Payment Model - Already stores `ziina_payment_intent_id`
- ✅ Signals - Already handle payment success → order updates
- ✅ Order Model - Already has status field
- ✅ Receipt Model - Already exists and signals create it

## Deploying Webhooks

1. ✅ Update `.env` with `ZIINA_WEBHOOK_SECRET`
2. ✅ Deploy code changes (views.py, urls.py)
3. ✅ Register webhook with Ziina API
4. ✅ Test with manual webhook request (see Testing section)
5. ✅ Monitor logs for 24 hours
6. ✅ Once confident, disable manual `verify_payment` polling (optional)

Both webhook and polling can coexist - no conflicts!
