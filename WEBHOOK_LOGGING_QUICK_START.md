# Webhook Logging Quick Start

## 📁 Log Files

All webhook logs are saved in: `/home/django_user/apps/uae_backend/logs/`

| File | Purpose | Max Size |
|------|---------|----------|
| `webhooks.log` | All webhook events | 10 MB (auto-rotates) |
| `payments.log` | Payment operations | 10 MB (auto-rotates) |
| `debug.log` | General application logs | 10 MB (auto-rotates) |

## 🔍 View Webhook Logs (Using Management Command)

### Latest 20 Events (Default)
```bash
cd /home/django_user/apps/uae_backend
python3 manage.py webhook_logs
```

### Last N Events
```bash
# View last 50 events
python3 manage.py webhook_logs --tail 50

# View last 100 events
python3 manage.py webhook_logs --tail 100
```

### Show Only Errors
```bash
python3 manage.py webhook_logs --errors
```

### Show Statistics
```bash
python3 manage.py webhook_logs --stats
```

Example output:
```
=== Webhook Log Statistics ===

Total log entries: 157
By Level:
  INFO:    150
  WARNING: 5
  ERROR:   2

Payment Processing:
  Successful: 42
  Failed: 3
  Unique Payments: 45
  Unique Orders: 44

Signature Issues: 0
Success Rate: 93.3%
```

### Search Specific Payment
```bash
# Find all events for Payment #42
python3 manage.py webhook_logs --search "Payment #42"

# Find all events for Order #123
python3 manage.py webhook_logs --search "Order #123"
```

### Show Only Payment Events
```bash
python3 manage.py webhook_logs --payments
```

## 📊 View Logs (Using Command Line)

### Watch Real-Time Logs
```bash
cd /home/django_user/apps/uae_backend
tail -f logs/webhooks.log
```

### View Last 20 Lines
```bash
tail -20 logs/webhooks.log
```

### View Last 50 Lines
```bash
tail -n 50 logs/webhooks.log
```

### View Specific Period
```bash
# Events from today (2026-04-04)
grep "2026-04-04" logs/webhooks.log

# Events from specific hour
grep "2026-04-04 14:" logs/webhooks.log
```

### Search Logs
```bash
# Find all successful payments
grep "to SUCCESS" logs/webhooks.log

# Find all failed payments
grep "to FAILED" logs/webhooks.log

# Find all errors
grep "ERROR" logs/webhooks.log

# Find signature issues
grep -i "signature" logs/webhooks.log

# Find missing payments
grep "not found" logs/webhooks.log
```

### Count Events
```bash
# Total webhook events
wc -l logs/webhooks.log

# Count successful payments
grep "to SUCCESS" logs/webhooks.log | wc -l

# Count failed payments
grep "to FAILED" logs/webhooks.log | wc -l

# Count errors
grep "ERROR" logs/webhooks.log | wc -l
```

### Extract Specific Data
```bash
# Extract all Payment IDs
grep "Webhook processed" logs/webhooks.log | grep -o "Payment #[0-9]*" | sort | uniq

# Extract all Order IDs
grep "Webhook processed" logs/webhooks.log | grep -o "Order #[0-9]*" | sort | uniq

# List unique payments in order of processing
grep "Webhook processed" logs/webhooks.log | tail -20 | grep -o "Payment #[0-9]*, Order #[0-9]*"
```

## 📈 Example Log Entries

### Successful Webhook
```
INFO 2026-04-04 14:32:15,234 Orders.webhook 12345 139876543210 Webhook processed: Payment #42 (Order #123) status updated from PENDING to SUCCESS
```

### Failed Signature Verification
```
WARNING 2026-04-04 14:31:45,123 Orders.webhook 12345 139876543210 Webhook signature verification failed
```

### Missing Payment
```
WARNING 2026-04-04 14:30:20,456 Orders.webhook 12345 139876543210 Payment not found for intent ID: pi_abc123xyz789
```

### Invalid Payload
```
ERROR 2026-04-04 14:29:10,789 Orders.webhook 12345 139876543210 Invalid webhook payload: JSONDecodeError(...)
```

## 🛠️ Troubleshooting

### Check if webhooks are being received
```bash
# Should have recent entries
tail -5 logs/webhooks.log
```

### Monitor for errors
```bash
# Watch for errors in real-time
tail -f logs/webhooks.log | grep "ERROR"
```

### Verify signature verification
```bash
# Most recent 5 webhook events
tail -5 logs/webhooks.log

# Should show successful signature verification
grep "Webhook processed" logs/webhooks.log | tail -1
```

### Check payment status updates
```bash
# Verify order #123 was processed via webhook
grep "Order #123" logs/webhooks.log
```

## 📋 Common Commands Summary

```bash
# View recent webhook activity
python3 manage.py webhook_logs

# Show statistics
python3 manage.py webhook_logs --stats

# Search for specific payment
python3 manage.py webhook_logs --search "Payment #42"

# View errors only
python3 manage.py webhook_logs --errors

# Watch live
tail -f logs/webhooks.log

# Count total events
wc -l logs/webhooks.log

# Find failed payments
grep "to FAILED" logs/webhooks.log | wc -l

# Export logs (backup)
cp logs/webhooks.log logs/webhooks.log.backup
```

## 🔐 Security Notes

- ✅ Logs don't contain actual webhook signatures
- ✅ Logs don't contain payment card details
- ✅ Logs don't contain customer sensitive data
- ✅ Only status updates are logged
- ✅ Server-side storage only

## 🚀 Production Monitoring

Recommended daily checks:

```bash
#!/bin/bash
# Daily webhook health check script

cd /home/django_user/apps/uae_backend

echo "=== Webhook Health Check ==="
echo ""

echo "Total events today:"
grep "$(date +%Y-%m-%d)" logs/webhooks.log | wc -l

echo ""
echo "Errors today:"
grep "$(date +%Y-%m-%d)" logs/webhooks.log | grep "ERROR" | wc -l

echo ""
echo "Signature failures:"
grep "$(date +%Y-%m-%d)" logs/webhooks.log | grep -i "signature" | wc -l

echo ""
echo "Success rate:"
python3 manage.py webhook_logs --stats | grep "Success Rate"

echo ""
echo "Latest event:"
tail -1 logs/webhooks.log
```

Save as `check_webhooks.sh` and run daily:
```bash
chmod +x check_webhooks.sh
./check_webhooks.sh  # Run anytime
```

## 📚 More Information

See **WEBHOOK_LOGGING.md** for:
- Detailed log format explanations
- Log rotation details
- Advanced parsing examples
- Integration with monitoring services
- Compliance and data retention
