# Webhook Logging Documentation

## Overview

Your webhook system now includes comprehensive logging with dedicated log files for:

1. **webhooks.log** - All webhook events and signature verification
2. **payments.log** - All payment-related operations
3. **debug.log** - General application logs

## Log Files Location

All log files are stored in: `/home/django_user/apps/uae_backend/logs/`

- `webhooks.log` - Webhook-specific events
- `payments.log` - Payment transactions
- `debug.log` - General debug information

## Log File Configuration

### File Properties
- **Max Size**: 10 MB per file
- **Backup Count**: 10 rotated backups
- **Format**: Verbose (timestamp, level, module, process, thread)
- **Auto-rotation**: Automatic when file reaches 10 MB

### Automatic Cleanup
Old log files are automatically rotated:
- When a log reaches 10 MB, it's renamed to `.1`, `.2`, etc.
- Only the 10 most recent backups are kept
- Oldest files are automatically deleted

## Log Entry Format

```
[LEVEL] YYYY-MM-DD HH:MM:SS [module] [process_id] [thread_id] Message
```

Example:
```
INFO 2026-04-04 14:32:15,123 Orders.views 12345 139876543210 Webhook processed: Payment #42 (Order #123) status updated from PENDING to SUCCESS
```

## What Gets Logged

### Webhook Logger (Orders.webhook)

#### Success Events
```
INFO 2026-04-04 14:32:15 Webhook processed: Payment #42 (Order #123) status updated from PENDING to SUCCESS
```

#### Errors
```
ERROR 2026-04-04 14:32:10 Invalid webhook payload: JSONDecodeError(...)
WARNING 2026-04-04 14:32:05 Webhook signature verification failed
WARNING 2026-04-04 14:32:00 Webhook signature missing but secret is configured
ERROR 2026-04-04 14:31:55 Webhook missing payment_intent_id
ERROR 2026-04-04 14:31:50 Webhook missing status
WARNING 2026-04-04 14:31:45 Payment not found for intent ID: pi_abc123
WARNING 2026-04-04 14:31:40 Unknown Ziina status: INVALID_STATUS
```

### Payment Logger (Orders.payment)

Payment-related operations (for future use in payment methods).

### General Logger (django)

Django framework logs and general application logs.

## Monitoring Webhooks

### View Real-Time Webhook Events

```bash
# Watch webhook log in real-time
tail -f logs/webhooks.log

# Watch all events matching a pattern
tail -f logs/webhooks.log | grep "Payment processed"

# View last 50 webhook events
tail -n 50 logs/webhooks.log
```

### Search for Specific Events

```bash
# Find all payment processing events
grep "Webhook processed" logs/webhooks.log

# Find all signature failures
grep "signature" logs/webhooks.log

# Find errors in webhooks
grep "ERROR" logs/webhooks.log

# Find warnings
grep "WARNING" logs/webhooks.log

# Find all events for a specific payment
grep "Payment #42" logs/webhooks.log

# Find all events for a specific order
grep "Order #123" logs/webhooks.log
```

### Get Statistics

```bash
# Count successful webhooks
grep "status updated from PENDING to SUCCESS" logs/webhooks.log | wc -l

# Count failed webhooks
grep "status updated from PENDING to FAILED" logs/webhooks.log | wc -l

# Count signature errors
grep "signature" logs/webhooks.log | wc -l

# Count total webhook events
wc -l logs/webhooks.log
```

### View Recent Activity

```bash
# Last 20 webhook events
tail -20 logs/webhooks.log

# Events from the last hour
grep "2026-04-04 14:" logs/webhooks.log

# Last webhook error
grep "ERROR" logs/webhooks.log | tail -1

# Last signature verification failure
grep "signature" logs/webhooks.log | tail -3
```

## Log Levels Explained

| Level | Color | Meaning | Examples |
|-------|-------|---------|----------|
| **INFO** | Green | Normal operation | "Webhook processed successfully" |
| **WARNING** | Yellow | Unusual but handled | "Signature missing", "Payment not found" |
| **ERROR** | Red | Problem occurred | "Invalid JSON", "Verification failed" |
| **DEBUG** | Blue | Detailed troubleshooting | (Not used in webhooks) |

## Parsing Logs Programmatically

### Extract Payment IDs Only

```bash
grep "Webhook processed" logs/webhooks.log | grep -o "Payment #[0-9]*" | sort | uniq
```

### Extract Order IDs Only

```bash
grep "Webhook processed" logs/webhooks.log | grep -o "Order #[0-9]*" | sort | uniq
```

### Count Events by Status

```bash
echo "=== Status Updates ===" && \
grep "PENDING to SUCCESS" logs/webhooks.log | wc -l && echo "Successful payments" && \
grep "PENDING to FAILED" logs/webhooks.log | wc -l && echo "Failed payments"
```

### Track Payment Processing Time

```bash
# For each webhook event, find matching order creation
grep "Webhook processed" logs/webhooks.log | head -5
```

## Troubleshooting with Logs

### Issue: Webhooks Not Being Received

Check logs for:
```bash
# See all webhook attempts
cat logs/webhooks.log

# Check for connection errors
grep "ERROR" logs/webhooks.log
```

### Issue: Signature Verification Failures

```bash
# View all signature-related events
grep -i "signature" logs/webhooks.log

# Check the exact error
grep "signature verification error" logs/webhooks.log
```

### Issue: Payment Not Updating

```bash
# Find the specific webhook event
grep "Order #123" logs/webhooks.log

# Check payment status update
grep "Payment #42" logs/webhooks.log

# Verify in database
# python manage.py shell
# >>> from Orders.models import Payment
# >>> Payment.objects.get(id=42).status
```

## Log Rotation Schedule

Logs are rotated **automatically** when they reach 10 MB:

1. `webhooks.log` → `webhooks.log.1`
2. `webhooks.log.1` → `webhooks.log.2`
3. ... (up to 10 backups)
4. `webhooks.log.10` → deleted

**No manual action required** - Django handles this automatically.

## Backup Webhooks Log

To backup the current webhook log:

```bash
# Create a timestamped backup
cp logs/webhooks.log logs/webhooks.log.backup.$(date +%Y%m%d_%H%M%S)

# Archive old logs
tar -czf logs/webhooks_$(date +%Y%m%d).tar.gz logs/webhooks.log.*
```

## Database vs Logs

| Information | Storage | Use Case |
|-------------|---------|----------|
| Payment status, amounts | Database | Business records, receipts |
| Webhook events, signatures | Logs | Debugging, audit trail |
| Order history | Database | Customer service |
| API calls, errors | Logs | Troubleshooting |

## Performance Notes

- Webhook logging is **asynchronous** (non-blocking)
- Log file rotation is **automatic**
- No database queries needed for logging
- Memory usage is minimal (rotating file handler)

## Security Notes

- ✅ Logs are stored on the server only
- ✅ Webhook secrets are **not logged** (only masked)
- ✅ Signature data is **not logged** (only success/failure)
- ✅ Customer payment details are **not logged**
- ✅ Log files should be **protected** from unauthorized access

## Integration with Monitoring

### Setup Log Monitoring (Optional)

```bash
# Email alerts on errors
tail -f logs/webhooks.log | grep "ERROR" | mail -s "Webhook Error Alert" admin@example.com

# Send to external logging service
# (Configure with ELK, Datadog, Sentry, etc.)
```

## Clearing Old Logs

### Remove All Old Backups

```bash
# Keep only current log
rm logs/webhooks.log.*
rm logs/payments.log.*
rm logs/debug.log.*
```

### Archive Logs for Compliance

```bash
# Archive to S3 or backups
tar -czf webhooks_archive_$(date +%Y%m).tar.gz logs/webhooks.log*
```

## Production Recommendations

1. ✅ Enable webhook logging (already configured)
2. ✅ Monitor webhook success rate daily
3. ✅ Set up alerts for ERROR entries
4. ✅ Archive logs monthly for compliance
5. ✅ Review logs weekly for patterns
6. ✅ Back up logs before clearing
