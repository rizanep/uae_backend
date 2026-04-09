# Ziina Payment Webhook Integration

## Overview

The webhook system provides real-time payment status notifications from Ziina. Instead of repeatedly polling the payment status, Ziina will send webhook events directly to your server when payment status changes.

**Event Type:** `payment_intent.status.updated`

## Setup Instructions

### 1. Configure Webhook Secret (Optional but Recommended)

Add to your `.env` file:

```env
ZIINA_WEBHOOK_SECRET=your_secret_key_here
```

The secret is used to verify the authenticity of webhook requests using HMAC-SHA256.

### 2. Register Webhook with Ziina

Use the Ziina API to register your webhook endpoint:

```bash
curl --request POST \
  --url https://api-v2.ziina.com/api/webhook \
  --header 'Authorization: Bearer YOUR_ZIINA_API_KEY' \
  --header 'Content-Type: application/json' \
  --data '{
    "url": "https://yourdomain.com/api/orders/webhook/ziina/",
    "secret": "your_secret_key_here"
  }'
```

**Parameters:**
- `url` (required): Your webhook endpoint URL
- `secret` (optional): Secret for HMAC signature verification

## Webhook Endpoint

**URL:** `POST /api/orders/webhook/ziina/`

## Webhook Payload Structure

```json
{
  "event": "payment_intent.status.updated",
  "data": {
    "id": "payment_intent_id",
    "status": "COMPLETED|FAILED|EXPIRED|CANCELLED",
    "amount": 50000,
    "currency_code": "AED",
    "message": "Order #123",
    "redirect_url": "https://..."
  }
}
```

## Webhook Headers

If a secret was configured, Ziina will include:

```
X-Webhook-Signature: <hmac_sha256_signature>
```

The signature is computed as:
```
HMAC-SHA256(request_body, webhook_secret)
```

## Payment Status Mapping

Ziina Status → Internal Status:
- `COMPLETED` → `SUCCESS`
- `FAILED` → `FAILED`
- `EXPIRED` → `FAILED`
- `CANCELLED` → `FAILED`

## Webhook Response

The endpoint responds with:

```json
{
  "success": true,
  "message": "Webhook processed successfully",
  "payment_id": 42,
  "order_id": 123,
  "status": "SUCCESS"
}
```

### Response Codes:
- `200 OK` - Webhook processed successfully
- `400 Bad Request` - Invalid payload or status
- `401 Unauthorized` - Missing or invalid signature
- `404 Not Found` - Payment record not found
- `500 Internal Server Error` - Server error

## Behavior on Payment Success

When a webhook indicates `COMPLETED` status:

1. **Payment Status Updated** → `SUCCESS`
2. **Order Status Updated** → `PAID` (automatic via signal)
3. **Receipt Generated** (automatic via signal)
4. **Notification Sent** to customer (automatic via signal)

## Behavior on Payment Failure

When a webhook indicates `FAILED`, `EXPIRED`, or `CANCELLED`:

1. **Payment Status Updated** → `FAILED`
2. **Order Status Remains** → `PENDING` (user can retry)
3. Customer can use the `retry_payment` endpoint to create a new payment

## Security Considerations

### HMAC Verification

Always enable webhook signature verification by configuring `ZIINA_WEBHOOK_SECRET`. This prevents:
- **Man-in-the-Middle Attacks**: Signatures can't be forged
- **Replay Attacks**: Tampered payloads won't have valid signatures
- **Unauthorized Access**: Only Ziina can send valid webhooks

### Implementation Details

The webhook handler:
- Uses constant-time comparison to prevent timing attacks
- Verifies signatures before processing payment
- Logs all webhook events for audit trails
- Uses atomic transactions to ensure data consistency
- Is exempt from CSRF protection (required for external webhooks)

## Testing Webhooks

### Test Webhook Signature Verification (Python)

```python
import hmac
import hashlib

webhook_secret = "your_secret_key"
request_body = b'{"event":"payment_intent.status.updated","data":{"id":"pi123","status":"COMPLETED"}}'

# Create expected signature
expected_signature = hmac.new(
    webhook_secret.encode(),
    request_body,
    hashlib.sha256
).hexdigest()

print(f"Expected Signature: {expected_signature}")

# This signature would be sent in the X-Webhook-Signature header
```

### Manual Test Request

```bash
# Create test webhook without signature
curl -X POST https://yourdomain.com/api/orders/webhook/ziina/ \
  -H "Content-Type: application/json" \
  -d '{
    "event": "payment_intent.status.updated",
    "data": {
      "id": "pi_test_123",
      "status": "COMPLETED",
      "amount": 50000,
      "currency_code": "AED"
    }
  }'
```

### Test with Signature

```bash
# Create signature
WEBHOOK_SECRET="your_secret"
PAYLOAD='{"event":"payment_intent.status.updated","data":{"id":"pi_test_123","status":"COMPLETED"}}'
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" -hex | awk '{print $2}')

# Send webhook with signature
curl -X POST https://yourdomain.com/api/orders/webhook/ziina/ \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Signature: $SIGNATURE" \
  -d "$PAYLOAD"
```

## Logging and Monitoring

All webhook events are logged to `django.log`. Check logs for:

- Webhook processing errors
- Signature verification failures
- Payment status updates
- Missing payment records

Example log entries:
```
[INFO] Webhook processed: Payment #42 (Order #123) status updated from PENDING to SUCCESS
[WARNING] Webhook signature verification failed
[ERROR] Payment not found for intent ID: pi_invalid_123
```

## Comparison: Webhook vs. Manual Polling

| Aspect | Webhook | Manual Polling |
|--------|---------|----------------|
| **Latency** | Immediate (< 1 second) | Up to polling interval (30+ seconds) |
| **Efficiency** | High - events only sent on change | Low - recurring API calls |
| **Reliability** | May retry on failure | Depends on polling loop |
| **Implementation** | Simple endpoint | Poll loop thread/task |
| **Cost** | Lower API usage | Higher API calls |

## Troubleshooting

### Webhook Not Received

1. Verify the webhook URL is publicly accessible
2. Check that the domain is in your `ALLOWED_HOSTS` setting
3. Verify Ziina webhook is registered with correct URL
4. Check firewall/network rules allow incoming requests

### "Webhook signature verification failed"

1. Verify `ZIINA_WEBHOOK_SECRET` matches Ziina configuration
2. Ensure the secret is exactly the same on both sides
3. Check for encoding issues (UTF-8)

### "Payment intent not found"

1. Ensure the payment was created with the correct `ziina_payment_intent_id`
2. Verify the webhook `id` field matches the payment record
3. Check database for orphaned payments

### Payment Status Not Updating

1. Verify the webhook endpoint is returning `success: true`
2. Check logs for processing errors
3. Verify atomic transaction is not being rolled back
4. Check order signals are properly connected

## Development Notes

- Webhook is exempt from CSRF protection (`@csrf_exempt`)
- Webhook doesn't require authentication (`permission_classes=[permissions.AllowAny]`)
- Webhook uses atomic transaction for consistency
- Provider response is stored as JSON for audit trail

## Additional Resources

- [Ziina API Documentation](https://api-v2.ziina.com)
- [HMAC-SHA256 Security Info](https://en.wikipedia.org/wiki/HMAC)
- [Django Signals Documentation](https://docs.djangoproject.com/en/stable/topics/signals/)
