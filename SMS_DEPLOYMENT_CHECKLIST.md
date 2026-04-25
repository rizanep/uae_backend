# SMS Deployment Checklist

Complete checklist for deploying SMS to production.

## Pre-Deployment Setup

- [ ] MSG91 account created and verified
- [ ] MSG91 API credentials obtained
- [ ] Authentication key noted: `MSG91_AUTH_KEY`
- [ ] Route selected: `MSG91_ROUTE` (transactional/promotional)

## Code Setup

- [ ] SMS app added to `INSTALLED_APPS`
- [ ] SMS URLs added to `core/urls.py`
- [ ] All SMS models created and migrated
- [ ] Database indexes created
- [ ] Admin interface configured

## Environment Variables

- [ ] `MSG91_AUTH_KEY` set in `.env`
- [ ] `MSG91_ROUTE` set in `.env`
- [ ] All secrets in environment, not in code
- [ ] `.env` file not committed to git
- [ ] `.env.example` created with dummy values

## Database

- [ ] Migrations applied: `python manage.py migrate SMS`
- [ ] Database tables created
- [ ] Indexes verified in database
- [ ] Backup taken before production deployment

## Security

- [ ] All SMS endpoints require superuser authentication
- [ ] JWT tokens configured and tested
- [ ] SSL/TLS enabled for API calls
- [ ] CORS settings configured if needed
- [ ] Rate limiting configured (if using DRF throttling)
- [ ] Input validation tested for edge cases

## Templates

- [ ] At least one SMS template created
- [ ] Template approved in admin
- [ ] Template created in MSG91
- [ ] Variables validated (VAR1, VAR2 format)
- [ ] Character count verified
- [ ] SMS parts calculated correctly

## Testing

- [ ] `python manage.py sms_manage test-connection` passes
- [ ] `python manage.py sms_manage verify-setup` passes
- [ ] Single SMS send tested
- [ ] Bulk SMS send tested (small batch)
- [ ] Delivery status tracked
- [ ] Error handling tested
- [ ] Admin interface accessible
- [ ] All API endpoints tested with valid JWT token

## Configuration

- [ ] Sender ID configured
- [ ] Daily limit set appropriately
- [ ] Monthly limit set appropriately
- [ ] Cost per SMS configured for tracking
- [ ] Short URL feature enabled/disabled as needed
- [ ] Realtime response enabled/disabled as needed

## Monitoring & Logging

- [ ] Logging configured to file
- [ ] Log rotation configured (max 5MB, 5 backup files)
- [ ] Log file path: `logs/sms.log`
- [ ] Debug mode set to False in production
- [ ] Error logging verified
- [ ] Warning logging verified

## Production Server

- [ ] Django DEBUG = False
- [ ] ALLOWED_HOSTS configured
- [ ] HTTPS/SSL enabled
- [ ] Static files collected: `python manage.py collectstatic`
- [ ] Database optimized
- [ ] Backup scripts configured
- [ ] Monitoring/alerting configured

## Webhook Configuration

- [ ] Webhook URL configured in MSG91 dashboard
- [ ] Webhook endpoint secured
- [ ] Firewall allows inbound webhook requests
- [ ] Webhook handler created (optional)
- [ ] Webhook logging configured

## Performance

- [ ] Connection pooling configured (if using celery)
- [ ] Bulk send batch sizes optimized
- [ ] Database query optimization verified
- [ ] Caching configured if needed
- [ ] Load testing performed (optional)

## Documentation

- [ ] README updated with SMS information
- [ ] API documentation generated
- [ ] Team trained on SMS endpoints
- [ ] Incident response plan documented
- [ ] Troubleshooting guide created

## Backup & Recovery

- [ ] Database backup schedule set
- [ ] Backup retention policy defined
- [ ] Recovery procedure documented
- [ ] Disaster recovery plan created

## Go-Live Checklist

- [ ] All items above completed
- [ ] Stakeholder approval obtained
- [ ] Rollback plan documented
- [ ] On-call support scheduled
- [ ] Monitoring alerts active
- [ ] Documentation accessible

## Post-Deployment

- [ ] Monitor SMS sending rate
- [ ] Check error logs daily
- [ ] Verify webhooks are processed
- [ ] Monitor delivery rates
- [ ] Track cost per SMS
- [ ] Review customer feedback
- [ ] Weekly analytics review

## Scaling (If Needed)

- [ ] Connection pool size tuned
- [ ] Database read replicas configured
- [ ] Caching layer added (Redis)
- [ ] Celery async tasks configured
- [ ] Rate limiting tuned
- [ ] Load balancing configured

## Maintenance

- [ ] Monthly template review
- [ ] Quarterly security audit
- [ ] Annual cost review
- [ ] Performance optimization review
- [ ] Documentation updates

## Troubleshooting Reference

### SMS not sending
```bash
# Check connection
python manage.py sms_manage test-connection

# Verify setup
python manage.py sms_manage verify-setup

# Check logs
tail -f logs/sms.log
```

### View Django admin
```
http://your-domain.com/admin/SMS/
```

### Database check
```bash
python manage.py dbshell
SELECT COUNT(*) FROM SMS_smstemplate;
SELECT COUNT(*) FROM SMS_smsmessage;
```

### Environment variables
```bash
echo $MSG91_AUTH_KEY
echo $MSG91_ROUTE
```

## Support Contacts

- MSG91 Support: support@msg91.com
- Django Support: docs.djangoproject.com
- DRF Support: www.django-rest-framework.org

## Sign-Off

- [ ] Dev Lead Approved: _____________ Date: _______
- [ ] QA Lead Approved: _____________ Date: _______
- [ ] DevOps Lead Approved: _____________ Date: _______
- [ ] Product Owner Approved: _____________ Date: _______

---

**Deployment Date**: ________________

**Deployed By**: ________________

**Status**: [ ] Ready for Production [ ] Hold [ ] Rollback

## Notes

_Additional deployment notes or issues_

```
_______________________
_______________________
_______________________
```
