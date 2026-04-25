# SMS Integration Guide

Complete SMS messaging integration using MSG91 API with Django, DRF, and admin-only endpoints.

## Overview

The SMS app provides secure, reliable SMS messaging capabilities:
- **Template Management**: Create, approve, and manage SMS templates
- **Message Sending**: Send single or bulk SMS (up to 10,000 recipients)
- **Delivery Tracking**: Real-time delivery status and webhooks
- **Admin-Only Access**: Superuser-restricted endpoints
- **Rate Limiting**: Daily/monthly message limits
- **DLT Compliance**: Support for India's DLT regulations
- **Audit Trail**: Complete message history and soft deletes

## Architecture

### Models

#### SMSTemplate
```python
- template_name: Unique template identifier (3-256 chars)
- template_content: Message text with {{VAR1}}, {{VAR2}} variables
- sender_id: Max 11 alphanumeric characters
- sms_type: NORMAL, TRANSACTIONAL, OTP, PROMOTIONAL
- dlt_template_id: Optional DLT template ID for India compliance
- is_approved: Boolean approval flag
- approval_status: PENDING, APPROVED, REJECTED, DISABLED
- msg91_template_id: Template ID from MSG91
- character_count: Auto-calculated from content
- sms_parts: Auto-calculated (160 chars per part)
```

#### SMSMessage
```python
- template: Foreign key to SMSTemplate
- recipient_number: Phone number (min 10 digits)
- variables: JSON variables for template rendering
- message_content: Rendered message text
- status: PENDING, SENT, DELIVERED, FAILED, BOUNCED
- msg91_message_id: Message ID from MSG91
- sent_at: Timestamp when sent
- delivered_at: Timestamp when delivered
- error_message: Error details if failed
- response_data: Raw MSG91 API response
```

#### SMSConfiguration
```python
- sender_id: Default sender ID
- is_active: Enable/disable SMS sending
- daily_limit: Max messages per day (0-1M)
- monthly_limit: Max messages per month (0-10M)
- cost_per_sms: Cost tracking per message
- enable_short_url: Enable shortened URLs in messages
- short_url_expiry: URL expiration time (seconds)
- enable_realtime_response: Request real-time delivery updates
```

#### SMSWebhookLog
```python
- event_type: Webhook event type from MSG91
- payload: Raw webhook JSON
- is_processed: Processing status flag
- message: Foreign key to SMSMessage
```

## API Endpoints

### Templates

#### Create Template
```
POST /api/sms/templates/
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "template_name": "order_confirmation",
  "template_content": "Hi {{VAR1}}, your order {{VAR2}} is confirmed",
  "sender_id": "MYAPP",
  "sms_type": "TRANSACTIONAL",
  "dlt_template_id": "1007234567890123456"  // Optional
}

Response: 201 CREATED
{
  "id": "uuid",
  "template_name": "order_confirmation",
  "character_count": 68,
  "sms_parts": 1,
  "approval_status": "PENDING",
  ...
}
```

#### List Templates
```
GET /api/sms/templates/?approval_status=APPROVED&sms_type=TRANSACTIONAL
Authorization: Bearer <jwt_token>

Query Parameters:
- approval_status: PENDING, APPROVED, REJECTED, DISABLED
- sms_type: NORMAL, TRANSACTIONAL, OTP, PROMOTIONAL
- search: Template name or content search

Response: 200 OK
{
  "count": 5,
  "next": null,
  "previous": null,
  "results": [...]
}
```

#### Retrieve Template
```
GET /api/sms/templates/{id}/
Authorization: Bearer <jwt_token>

Response: 200 OK
{...}
```

#### Update Template
```
PUT /api/sms/templates/{id}/
PATCH /api/sms/templates/{id}/
Authorization: Bearer <jwt_token>

{
  "template_content": "Updated content {{VAR1}}"
}

Response: 200 OK
{...}
```

#### Delete Template (Soft Delete)
```
DELETE /api/sms/templates/{id}/
Authorization: Bearer <jwt_token>

Response: 204 NO CONTENT
```

#### Approve Template
```
POST /api/sms/templates/{id}/approve/
Authorization: Bearer <jwt_token>

Response: 200 OK
{
  "success": true,
  "message": "Template approved successfully",
  "template": {...}
}
```

#### Reject Template
```
POST /api/sms/templates/{id}/reject/
Authorization: Bearer <jwt_token>

{
  "reason": "Content contains prohibited words"
}

Response: 200 OK
{
  "success": true,
  "message": "Template rejected successfully",
  "template": {...}
}
```

#### Create in MSG91
```
POST /api/sms/templates/{id}/create-in-msg91/
Authorization: Bearer <jwt_token>

Response: 200 OK
{
  "success": true,
  "message": "Template created in MSG91 successfully",
  "template_id": "1234567890"
}
```

### Messages

#### Send Single SMS
```
POST /api/sms/messages/send/
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "template": "template-uuid",
  "recipient_number": "+971501234567",
  "variables": {
    "VAR1": "Ahmed",
    "VAR2": "ORD-12345"
  },
  "short_url": false,
  "realtime_response": false
}

Response: 201 CREATED
{
  "id": "message-uuid",
  "template": "template-uuid",
  "recipient_number": "+971501234567",
  "status": "SENT",
  "message_content": "Hi Ahmed, your order ORD-12345 is confirmed",
  "sent_at": "2024-01-15T10:30:00Z",
  ...
}

Errors:
- 400: Invalid template, phone number, or variables
- 404: Template not found or not approved
- 403: Insufficient permissions
- 500: MSG91 API error
```

#### Send Bulk SMS
```
POST /api/sms/messages/send-bulk/
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "template_id": "template-uuid",
  "recipient_numbers": [
    "+971501234567",
    "+971502345678",
    "+971503456789"
  ],
  "variables_list": [
    {"VAR1": "Ahmed", "VAR2": "ORD-12345"},
    {"VAR1": "Sara", "VAR2": "ORD-12346"},
    {"VAR1": "Ali", "VAR2": "ORD-12347"}
  ],
  "short_url": false
}

Response: 201 CREATED
{
  "success": true,
  "message": "Bulk SMS sent successfully (3 messages)",
  "sent_count": 3,
  "response": {...}
}

Constraints:
- Max 10,000 recipients per request
- variables_list must match recipient_numbers length
- All recipients must have min 10 digits
```

#### List Messages
```
GET /api/sms/messages/?status=DELIVERED&created_at__gte=2024-01-01
Authorization: Bearer <jwt_token>

Query Parameters:
- status: PENDING, SENT, DELIVERED, FAILED, BOUNCED
- template: Filter by template ID
- created_at__gte: Created after date
- created_at__lte: Created before date
- ordering: -created_at (default), sent_at, recipient_number

Response: 200 OK
{
  "count": 150,
  "results": [...]
}
```

#### Retrieve Message
```
GET /api/sms/messages/{id}/
Authorization: Bearer <jwt_token>

Response: 200 OK
{
  "id": "message-uuid",
  "template": {...},
  "recipient_number": "+971501234567",
  "status": "DELIVERED",
  "delivered_at": "2024-01-15T10:35:00Z",
  "response_data": {...}
}
```

### Configuration

#### Get Configuration
```
GET /api/sms/config/retrieve/
Authorization: Bearer <jwt_token>

Response: 200 OK
{
  "id": 1,
  "sender_id": "MYAPP",
  "is_active": true,
  "daily_limit": 10000,
  "monthly_limit": 300000,
  "cost_per_sms": 0.50,
  "enable_short_url": false,
  "enable_realtime_response": false
}
```

#### Update Configuration
```
PUT /api/sms/config/update/
Authorization: Bearer <jwt_token>

{
  "daily_limit": 5000,
  "monthly_limit": 150000,
  "cost_per_sms": 0.60
}

Response: 200 OK
{...}
```

### Reports

#### Get SMS Logs
```
GET /api/sms/reports/logs/?start_date=2024-01-01&end_date=2024-01-31
Authorization: Bearer <jwt_token>

Query Parameters:
- start_date: YYYY-MM-DD (required)
- end_date: YYYY-MM-DD (required)

Response: 200 OK
{
  "success": true,
  "count": 500,
  "data": [
    {
      "msgid": "msg-id",
      "status": "DELIVERED",
      "sender": "MYAPP",
      "recipient": "971501234567",
      "submitted": "2024-01-15 10:30:00",
      "delivered": "2024-01-15 10:35:00"
    },
    ...
  ]
}
```

## Security

### Authentication
- All endpoints require JWT authentication
- Only superusers can access endpoints (IsAdminOrReadOnly permission)

### Input Validation
- Phone numbers: 10+ digits, non-digit chars removed except +
- Template names: 3-256 chars, alphanumeric, hyphen, underscore
- SMS content: 10-9999 characters
- Sender ID: Max 11 alphanumeric characters
- Variables format: {{VAR1}}, {{VAR2}}, etc.

### Data Protection
- Credentials stored in environment variables only
- SSL/TLS for all API requests
- Soft deletes maintain audit trail
- All operations logged without credentials

## Installation

### 1. Add SMS to INSTALLED_APPS

Edit `core/settings.py`:
```python
INSTALLED_APPS = [
    # ...
    'SMS',
]
```

### 2. Add SMS URLs

Edit `core/urls.py`:
```python
from django.urls import path, include

urlpatterns = [
    # ...
    path('api/sms/', include('SMS.urls')),
]
```

### 3. Set Environment Variables

Create `.env` file:
```
MSG91_AUTH_KEY=your_auth_key_here
MSG91_ROUTE=transactional
```

Or export in shell:
```bash
export MSG91_AUTH_KEY="your_auth_key_here"
export MSG91_ROUTE="transactional"
```

### 4. Run Migrations

```bash
python manage.py migrate SMS
```

### 5. Create Superuser

```bash
python manage.py createsuperuser
```

### 6. Test Connection

```bash
python manage.py sms_manage test-connection
```

## Usage Examples

### Create and Send SMS

```python
import requests
import json

# Create template
template_data = {
    "template_name": "order_delivered",
    "template_content": "Hello {{NAME}}, your order {{ORDER_ID}} has been delivered",
    "sender_id": "MYAPP",
    "sms_type": "TRANSACTIONAL"
}

response = requests.post(
    "http://localhost:8000/api/sms/templates/",
    json=template_data,
    headers={"Authorization": "Bearer YOUR_JWT_TOKEN"}
)
template = response.json()

# Approve template (admin only)
requests.post(
    f"http://localhost:8000/api/sms/templates/{template['id']}/approve/",
    headers={"Authorization": "Bearer YOUR_JWT_TOKEN"}
)

# Create in MSG91
requests.post(
    f"http://localhost:8000/api/sms/templates/{template['id']}/create-in-msg91/",
    headers={"Authorization": "Bearer YOUR_JWT_TOKEN"}
)

# Send SMS
message_data = {
    "template": template['id'],
    "recipient_number": "+971501234567",
    "variables": {
        "NAME": "Ahmed",
        "ORDER_ID": "ORD-12345"
    }
}

response = requests.post(
    "http://localhost:8000/api/sms/messages/send/",
    json=message_data,
    headers={"Authorization": "Bearer YOUR_JWT_TOKEN"}
)
message = response.json()
print(f"Message sent: {message['id']}")
```

### Send Bulk SMS

```python
bulk_data = {
    "template_id": "template-uuid",
    "recipient_numbers": [
        "+971501234567",
        "+971502345678",
        "+971503456789"
    ],
    "variables_list": [
        {"NAME": "Ahmed", "ORDER_ID": "ORD-12345"},
        {"NAME": "Sara", "ORDER_ID": "ORD-12346"},
        {"NAME": "Ali", "ORDER_ID": "ORD-12347"}
    ]
}

response = requests.post(
    "http://localhost:8000/api/sms/messages/send-bulk/",
    json=bulk_data,
    headers={"Authorization": "Bearer YOUR_JWT_TOKEN"}
)
result = response.json()
print(f"Sent {result['sent_count']} SMS messages")
```

## Admin Interface

Access Django admin at `/admin/`:

### SMS Templates
- Create, edit, delete templates
- Filter by approval status and type
- Bulk approve/reject templates
- View character count and SMS parts
- See template creation history

### SMS Messages
- View all sent messages
- Filter by status and template
- Search by phone number or message ID
- View delivery timestamps
- See error messages for failed SMS

### SMS Configuration
- Set default sender ID
- Configure rate limits
- Set cost per SMS
- Enable/disable features

### SMS Webhook Logs
- View all webhook events
- Check processing status
- See raw payload data
- Track message status updates

## Management Commands

### Test Connection
```bash
python manage.py sms_manage test-connection
```

### Verify Setup
```bash
python manage.py sms_manage verify-setup
```

### Sync Templates
```bash
python manage.py sms_manage sync-templates
python manage.py sms_manage sync-templates --template-id=template-uuid
```

## Rate Limiting

Configure in Admin:
- **Daily Limit**: Maximum SMS per day (default: 10,000)
- **Monthly Limit**: Maximum SMS per month (default: 300,000)

Check current usage in SMS dashboard.

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| 400 Invalid template | Template not approved | Approve template first |
| 404 Template not found | Invalid template ID | Check template ID |
| 403 Permission denied | Not superuser | Use admin account |
| 500 MSG91 API error | Invalid credentials | Check MSG91_AUTH_KEY |
| Invalid phone number | Less than 10 digits | Use valid E.164 format |

### Response Codes

- `201 CREATED`: SMS created/sent successfully
- `200 OK`: Request successful
- `400 BAD_REQUEST`: Invalid data
- `403 FORBIDDEN`: Insufficient permissions
- `404 NOT_FOUND`: Resource not found
- `500 INTERNAL_SERVER_ERROR`: Server error

## Troubleshooting

### SMS not sending
1. Verify template is approved
2. Check template created in MSG91
3. Verify MSG91_AUTH_KEY is set
4. Check daily/monthly limits not exceeded
5. Validate phone number format

### Webhook not updating status
1. Configure webhook URL in MSG91 dashboard
2. Verify webhook endpoint is accessible
3. Check firewall allows inbound webhook requests
4. Review logs for processing errors

### Character count incorrect
1. Template renders correctly with sample variables
2. Check for special characters
3. Verify VAR names in template

## DLT Compliance (India)

For Indian SMS, use DLT template ID:

```python
template_data = {
    "template_name": "otp_verification",
    "template_content": "Your OTP is {{OTP}}",
    "sender_id": "MYAPP",
    "sms_type": "OTP",
    "dlt_template_id": "1007234567890123456"  # DLT template ID
}
```

## Performance

### Bulk Sending
- Handle up to 10,000 recipients per request
- Uses database transactions for reliability
- Bulk create for efficiency
- Async processing for high volumes (configure Celery)

### Message Retrieval
- Database indexes on frequently queried fields
- Pagination enabled by default (20 per page)
- Filter and search for quick access

## API Rate Limiting

Configure in MSG91:
- Individual sending rate limits
- Adjust based on plan

## Support & Debugging

### Enable Debug Logging

Edit `core/settings.py`:
```python
LOGGING = {
    'version': 1,
    'handlers': {
        'sms_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/sms.log',
            'maxBytes': 1024000,
            'backupCount': 5,
        },
    },
    'loggers': {
        'SMS': {
            'handlers': ['sms_file'],
            'level': 'DEBUG',
        },
    },
}
```

### View Logs

```bash
tail -f logs/sms.log
```

## Next Steps

- [Quick Start Guide](SMS_QUICKSTART.md)
- [API Examples](SMS_API_EXAMPLES.md)
- [Deployment Checklist](SMS_DEPLOYMENT_CHECKLIST.md)
- [Implementation Summary](SMS_IMPLEMENTATION_SUMMARY.md)
