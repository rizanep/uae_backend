# MSG91 WhatsApp Integration - Deployment Checklist

Complete checklist for deploying WhatsApp integration to production.

## Pre-Deployment

### Local Development Setup ✓
- [ ] WhatsApp app added to `INSTALLED_APPS` in settings.py
- [ ] MSG91 credentials configured in `.env`
- [ ] Migrations created and applied: `python manage.py migrate WhatsApp`
- [ ] Superuser created: `python manage.py createsuperuser`
- [ ] Test endpoints working locally
- [ ] Admin panel accessible at `/admin/`
- [ ] Logs directory created and writable

### Code Review ✓
- [ ] All endpoints have `IsAdminOrReadOnly` permission class
- [ ] Input validation in serializers
- [ ] Error handling in service layer
- [ ] Logging configured for all operations
- [ ] No hardcoded credentials anywhere
- [ ] Security headers configured
- [ ] CSRF protection enabled

### Testing ✓
- [ ] Unit tests pass: `python manage.py test WhatsApp`
- [ ] API endpoints tested with Postman/Insomnia
- [ ] Error cases tested (invalid phone, wrong template, etc.)
- [ ] Bulk sending tested (100+ messages)
- [ ] Rate limiting tested
- [ ] Permission checks tested (non-admin access denied)

## Staging Deployment

### Environment Setup ✓
- [ ] `.env` file configured with production MSG91 credentials
- [ ] Database backup created
- [ ] Static files collected: `python manage.py collectstatic --noinput`
- [ ] Migrations applied: `python manage.py migrate`
- [ ] Logs directory exists and writable
- [ ] DEBUG = False in settings

### Security Configuration ✓
- [ ] ALLOWED_HOSTS configured
- [ ] SECURE_SSL_REDIRECT = True
- [ ] SESSION_COOKIE_SECURE = True
- [ ] CSRF_COOKIE_SECURE = True
- [ ] SECURE_HSTS_SECONDS configured
- [ ] SECURE_HSTS_INCLUDE_SUBDOMAINS = True
- [ ] Secret key not exposed
- [ ] Database password complex and secure

### Service Verification ✓
- [ ] MSG91 API credentials verified
- [ ] Test message sent successfully
- [ ] Logs generated in `logs/whatsapp.log`
- [ ] Admin panel shows created template
- [ ] Delivery reports received

### Monitoring Setup ✓
- [ ] Log aggregation configured
- [ ] Error alerts set up
- [ ] API rate limiting configured
- [ ] Database backup scheduled
- [ ] Uptime monitoring enabled

## Production Deployment

### Pre-Launch Checks ✓
- [ ] All staging checks passed
- [ ] Performance testing completed
- [ ] Load testing completed (min 100 messages/sec)
- [ ] Backup and recovery tested
- [ ] Rollback plan documented
- [ ] Incident response plan ready

### Deployment Steps ✓
- [ ] Database backed up
- [ ] Code deployed
- [ ] Migrations applied
- [ ] Static files collected
- [ ] Services restarted
- [ ] Health checks passing
- [ ] Smoke tests completed

### Production Monitoring ✓
- [ ] Error rate normal
- [ ] Response times acceptable (< 2 sec)
- [ ] API logs flowing correctly
- [ ] WhatsApp messages delivering
- [ ] No critical errors in logs
- [ ] Admin panel responsive
- [ ] Database performance normal

### Documentation Updates ✓
- [ ] Runbook updated with WhatsApp procedures
- [ ] Escalation procedure documented
- [ ] API documentation published
- [ ] Common issues and solutions documented
- [ ] Team trained on using WhatsApp features

## Configuration Checklist

### Django Settings
```python
# settings.py
INSTALLED_APPS = [
    ...
    'WhatsApp.apps.WhatsappConfig',
]

# MSG91 Configuration
MSG91_AUTH_KEY = os.environ.get('MSG91_AUTH_KEY')
MSG91_INTEGRATED_NUMBER = os.environ.get('MSG91_INTEGRATED_NUMBER')
WHATSAPP_ENABLE_LOGGING = True

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}
```

### URL Configuration
```python
# core/urls.py
urlpatterns = [
    ...
    path('api/whatsapp/', include('WhatsApp.urls')),
]
```

### Environment Variables
```env
# .env
MSG91_AUTH_KEY=production_key_here
MSG91_INTEGRATED_NUMBER=+971501234567
WHATSAPP_ENABLE_LOGGING=true
WHATSAPP_MAX_RETRIES=3
WHATSAPP_REQUEST_TIMEOUT=30
```

## Verification Commands

Run these commands to verify setup:

### Test Connection
```bash
python manage.py whatsapp_manage test-connection
```

### Verify Complete Setup
```bash
python manage.py whatsapp_manage verify-setup
```

### List Templates
```bash
python manage.py whatsapp_manage list-templates
```

### Create Default Configuration
```bash
python manage.py whatsapp_manage create-config
```

## API Endpoint Verification

### Test Admin Authentication
```bash
# Get JWT token
curl -X POST http://localhost:8000/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"password"}'
```

### Test Template Creation
```bash
curl -X POST http://localhost:8000/api/whatsapp/templates/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "template_name":"test",
    "integrated_number":"+971501234567",
    "body_text":"Test"
  }'
```

### Test Message Sending
```bash
curl -X POST http://localhost:8000/api/whatsapp/messages/send/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "template":"template-uuid",
    "recipient_number":"+971509876543",
    "variables":{"body_1":"test"}
  }'
```

## Troubleshooting

### Issue: "MSG91 credentials not configured"

**Debug:**
```bash
python manage.py shell
>>> from django.conf import settings
>>> print(settings.MSG91_AUTH_KEY)
>>> print(settings.MSG91_INTEGRATED_NUMBER)
```

**Solution:**
- Check `.env` file has correct values
- Ensure `.env` is loaded before Django starts
- Verify credentials are not empty

### Issue: Migrations not applied

**Debug:**
```bash
python manage.py showmigrations WhatsApp
python manage.py showmigrations WhatsApp --plan
```

**Solution:**
```bash
python manage.py migrate WhatsApp --verbose
```

### Issue: Permission denied errors

**Debug:**
```bash
# Check user is superuser
python manage.py shell
>>> from django.contrib.auth.models import User
>>> user = User.objects.first()
>>> print(user.is_superuser)
```

**Solution:**
- Ensure accessing with superuser account
- Check JWT token is valid and not expired

### Issue: Messages not sending

**Debug:**
```bash
tail -f logs/whatsapp.log
# Check for error messages
grep "ERROR\|FAILED" logs/whatsapp.log
```

**Solution:**
- Verify template is APPROVED
- Check recipient number format (must have country code)
- Test MSG91 connection independently
- Check MSG91 account balance/limits

## Performance Optimization

### Database
- [ ] Add connection pooling
- [ ] Enable query caching
- [ ] Optimize indexes (already done)
- [ ] Regular vacuum and analyze

### API
- [ ] Enable pagination (already done)
- [ ] Add caching headers
- [ ] Implement rate limiting per IP
- [ ] Use CDN for static files

### Logging
- [ ] Use structured logging (JSON)
- [ ] Implement log rotation (already done)
- [ ] Archive old logs
- [ ] Use log aggregation service

### Celery (Optional)
```python
# For async message sending
@shared_task
def send_whatsapp_message(template_id, recipient, variables):
    # Async send implementation
    pass
```

## Security Hardening

### API Security
- [ ] Rate limiting by IP address
- [ ] API key rotation schedule
- [ ] Input sanitization
- [ ] Output encoding
- [ ] CORS properly configured

### Data Protection
- [ ] Encrypt sensitive database fields
- [ ] Audit logs for admin actions
- [ ] Data retention policy
- [ ] GDPR compliance for EU users
- [ ] PII handling procedures

### Access Control
- [ ] IP whitelisting for admin panel
- [ ] VPN requirement for admins
- [ ] Two-factor authentication
- [ ] Role-based access control
- [ ] Activity logging and alerts

## Disaster Recovery

### Backup Strategy
- [ ] Daily database backups
- [ ] Backup retention: 30 days
- [ ] Backup encryption
- [ ] Backup testing monthly
- [ ] Cross-region backup (optional)

### Restore Procedure
```bash
# Restore from backup
pg_restore -U user -d database backup_file.sql.gz
```

### Recovery Time Objectives
- [ ] RTO: 1 hour
- [ ] RPO: 1 hour
- [ ] Test recovery monthly

## Escalation Procedure

### Level 1: On-Call Engineer
- [ ] Check error logs
- [ ] Verify API connectivity
- [ ] Check MSG91 account status
- [ ] Restart affected services

### Level 2: Platform Team
- [ ] Database analysis
- [ ] Performance profiling
- [ ] Infrastructure investigation
- [ ] External vendor contact

### Level 3: Management
- [ ] Customer notification
- [ ] Business impact assessment
- [ ] Vendor escalation
- [ ] Post-incident review

## Post-Deployment

### Monitoring
- [ ] Dashboard configured
- [ ] Alerts configured
- [ ] Team notified of alerts
- [ ] On-call rotation schedule

### Documentation
- [ ] Runbook finalized
- [ ] API docs published
- [ ] Team trained
- [ ] FAQ documented

### Analytics
- [ ] Track successful sends
- [ ] Track delivery rates
- [ ] Monitor API latency
- [ ] Track error rates
- [ ] Cost per message tracking

## Sign-Off

- [ ] Product Manager: _____________ Date: _______
- [ ] DevOps Engineer: _____________ Date: _______
- [ ] Security Officer: _____________ Date: _______
- [ ] QA Lead: _____________ Date: _______

---

**Deployment Date**: _______
**Deployed By**: _______
**Approved By**: _______

**Notes**:
_________________________________________________
_________________________________________________
_________________________________________________
