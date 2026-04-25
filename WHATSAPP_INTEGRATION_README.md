# MSG91 WhatsApp Integration for Django

Complete, secure, and admin-only WhatsApp API integration using MSG91.

## Features

✅ **Admin-Only Access** - All endpoints require superuser authentication
✅ **Secure API Communication** - SSL/TLS, proper error handling, logging
✅ **Template Management** - Create, approve, update, and delete templates
✅ **Message Sending** - Single and bulk message sending with rate limiting
✅ **Message Tracking** - Full audit trail of all messages and delivery status
✅ **Webhook Support** - Handle incoming webhooks from MSG91
✅ **Logging** - Comprehensive logging to file and console
✅ **Configuration Management** - Dynamic rate limiting and settings
✅ **Django Admin Interface** - Full admin panel for easy management

## Installation

### 1. Ensure WhatsApp App is Registered

The app has already been created in the project. Verify it's in `settings.py`:

```python
INSTALLED_APPS = [
    ...
    'WhatsApp.apps.WhatsappConfig',
]
```

### 2. Configure Environment Variables

Add the following to your `.env` file:

```env
# MSG91 WhatsApp Integration
MSG91_AUTH_KEY=your_msg91_auth_key_here
MSG91_INTEGRATED_NUMBER=+971501234567

# WhatsApp Configuration
WHATSAPP_ENABLE_LOGGING=true
WHATSAPP_MAX_RETRIES=3
WHATSAPP_REQUEST_TIMEOUT=30
```

**Getting Your Credentials:**
1. Visit [MSG91 Control Panel](https://control.msg91.com)
2. Navigate to WhatsApp > Integrations
3. Copy your Auth Key from API Documentation
4. Get your Integrated Number from WhatsApp Integration settings

### 3. Run Migrations

```bash
python manage.py makemigrations WhatsApp
python manage.py migrate WhatsApp
```

### 4. Create Superuser (if not exists)

```bash
python manage.py createsuperuser
```

### 5. Access Admin Panel

Visit: `http://localhost:8000/admin/`

## API Endpoints

All endpoints require authentication and admin privileges.

### Templates

#### List Templates
```
GET /api/whatsapp/templates/
```

Query Parameters:
- `approval_status` - Filter by status (PENDING, APPROVED, REJECTED, DISABLED)
- `language` - Filter by language code
- `category` - Filter by category
- `search` - Search by name or body text
- `ordering` - Order by field (-created_at, template_name, etc.)

Example:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/whatsapp/templates/?approval_status=APPROVED"
```

#### Create Template
```
POST /api/whatsapp/templates/
```

Request Body:
```json
{
  "template_name": "order_confirmation",
  "integrated_number": "+971501234567",
  "language": "en",
  "category": "TRANSACTIONAL",
  "header_format": "TEXT",
  "header_text": "Order Confirmation",
  "body_text": "Hello {{1}}, Your order #{{2}} has been confirmed!",
  "footer_text": "Thank you for shopping with us",
  "buttons": [
    {
      "type": "URL",
      "text": "Track Order",
      "url": "https://example.com/track/{{2}}"
    }
  ]
}
```

#### Approve Template
```
POST /api/whatsapp/templates/{id}/approve/
```

#### Reject Template
```
POST /api/whatsapp/templates/{id}/reject/

Body:
{
  "reason": "Grammar errors in body text"
}
```

#### Sync with MSG91
```
POST /api/whatsapp/templates/{id}/sync-with-msg91/
```

This creates the template in MSG91 and updates the local record.

#### Fetch All Templates from MSG91
```
GET /api/whatsapp/templates/sync-all-from-msg91/
```

### Messages

#### Send Single Message
```
POST /api/whatsapp/messages/send/
```

Request Body:
```json
{
  "template": "uuid-of-template",
  "recipient_number": "+971509876543",
  "variables": {
    "body_1": "Ahmed",
    "body_2": "12345"
  }
}
```

Response:
```json
{
  "success": true,
  "message": "Message sent successfully",
  "data": {
    "id": "uuid",
    "template": "uuid",
    "recipient_number": "+971509876543",
    "status": "SENT",
    "msg91_message_id": "msg_id_from_api",
    "sent_at": "2024-01-15T10:30:00Z",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

#### Send Bulk Messages
```
POST /api/whatsapp/messages/send-bulk/
```

Request Body:
```json
{
  "template_id": "uuid-of-template",
  "recipient_numbers": [
    "+971501234567",
    "+971509876543",
    "+971502345678"
  ],
  "variables_list": [
    {"body_1": "Ahmed", "body_2": "12345"},
    {"body_1": "Sara", "body_2": "12346"},
    {"body_1": "Ali", "body_2": "12347"}
  ]
}
```

Response:
```json
{
  "success": true,
  "message": "Bulk messages sent successfully (3 messages)",
  "sent_count": 3,
  "response": {
    "message_ids": ["msg_id_1", "msg_id_2", "msg_id_3"]
  }
}
```

#### List Messages
```
GET /api/whatsapp/messages/

Query Parameters:
- status: PENDING, SENT, DELIVERED, READ, FAILED
- template: template_uuid
- search: recipient_number or msg91_message_id
```

### Configuration

#### Get Configuration
```
GET /api/whatsapp/config/retrieve/
```

#### Update Configuration
```
PUT /api/whatsapp/config/update/
```

Request Body:
```json
{
  "is_active": true,
  "daily_limit": 10000,
  "monthly_limit": 300000
}
```

## Security Features

### 1. Authentication & Authorization
- All endpoints require JWT authentication
- Only superusers (admins) can access endpoints
- Custom permission classes ensure strict access control

```python
permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
```

### 2. Input Validation
- Serializers validate all input data
- Phone numbers validated for format
- Template names and content validated
- SQL injection protection via ORM

### 3. Secure API Communication
- SSL/TLS for all HTTP connections
- Auth key stored in environment variables (never hardcoded)
- Timeout configuration to prevent hanging requests
- Proper error handling without exposing sensitive data

### 4. Logging & Auditing
- All API calls logged to file and console
- Message sending audit trail with user tracking
- Failed requests logged with error details
- Separate log file for WhatsApp operations

### 5. Rate Limiting
- Configurable daily and monthly limits
- Per-template rate limiting support
- Bulk message size limits (max 1000 per batch)

### 6. Soft Deletes
- No hard delete of templates or messages
- Maintains complete audit trail
- Ability to restore deleted items
- Automatic filtering of deleted items in queries

## Database Schema

### WhatsAppTemplate
Stores WhatsApp message templates

```
- id (UUID, Primary Key)
- template_name (CharField, Unique)
- integrated_number (CharField)
- language (CharField) - en, ar, hi, ur
- category (CharField) - MARKETING, AUTHENTICATION, TRANSACTIONAL, UTILITY
- header_format (CharField) - TEXT, IMAGE, VIDEO, DOCUMENT, LOCATION
- header_text (TextField)
- header_example (JSONField)
- body_text (TextField)
- body_example (JSONField)
- footer_text (TextField)
- buttons (JSONField)
- is_approved (BooleanField)
- approval_status (CharField) - PENDING, APPROVED, REJECTED, DISABLED
- rejection_reason (TextField)
- msg91_template_id (CharField, Unique)
- created_by (ForeignKey to User)
- notes (TextField)
- created_at (DateTimeField)
- updated_at (DateTimeField)
- deleted_at (DateTimeField) - Soft delete
```

### WhatsAppMessage
Logs all sent messages

```
- id (UUID, Primary Key)
- template (ForeignKey to WhatsAppTemplate)
- recipient_number (CharField)
- variables (JSONField)
- status (CharField) - PENDING, SENT, DELIVERED, READ, FAILED
- msg91_message_id (CharField, Unique)
- response_data (JSONField)
- error_message (TextField)
- sent_at (DateTimeField)
- delivered_at (DateTimeField)
- read_at (DateTimeField)
- sent_by (ForeignKey to User)
- created_at (DateTimeField)
- updated_at (DateTimeField)
- deleted_at (DateTimeField) - Soft delete
```

### WhatsAppConfiguration
Stores configuration and rate limits

```
- integrated_number (CharField, Primary Key)
- is_active (BooleanField)
- daily_limit (IntegerField)
- monthly_limit (IntegerField)
- updated_at (DateTimeField)
- updated_by (ForeignKey to User)
```

### WhatsAppWebhookLog
Logs incoming webhooks from MSG91

```
- id (UUID, Primary Key)
- event_type (CharField)
- message (ForeignKey to WhatsAppMessage)
- payload (JSONField)
- is_processed (BooleanField)
- processing_error (TextField)
- created_at (DateTimeField)
- updated_at (DateTimeField)
- deleted_at (DateTimeField) - Soft delete
```

## Usage Examples

### Python/Requests

#### Send a Message
```python
import requests
import json

headers = {
    'Authorization': 'Bearer YOUR_JWT_TOKEN',
    'Content-Type': 'application/json'
}

payload = {
    'template': 'template-uuid-here',
    'recipient_number': '+971509876543',
    'variables': {
        'body_1': 'John',
        'body_2': 'ORDER-123'
    }
}

response = requests.post(
    'http://localhost:8000/api/whatsapp/messages/send/',
    headers=headers,
    json=payload
)

print(response.json())
```

#### Create a Template
```python
import requests

headers = {
    'Authorization': 'Bearer YOUR_JWT_TOKEN',
    'Content-Type': 'application/json'
}

payload = {
    'template_name': 'welcome_message',
    'integrated_number': '+971501234567',
    'language': 'en',
    'category': 'MARKETING',
    'body_text': 'Welcome {{1}} to our store!'
}

response = requests.post(
    'http://localhost:8000/api/whatsapp/templates/',
    headers=headers,
    json=payload
)

print(response.json())
```

### cURL

#### List Templates
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/api/whatsapp/templates/"
```

#### Send Bulk Messages
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "uuid",
    "recipient_numbers": ["+971501234567", "+971509876543"],
    "variables_list": [
      {"body_1": "Ahmed"},
      {"body_1": "Sara"}
    ]
  }' \
  "http://localhost:8000/api/whatsapp/messages/send-bulk/"
```

## Logging

Logs are stored in `logs/whatsapp.log`

### Log Format
```
INFO 2024-01-15 10:30:45,123 WhatsApp.services 12345 67890 MSG91 API Request: POST /api/v5/whatsapp/client-panel-template/
```

### Log Levels
- **INFO**: Normal operations, successful API calls
- **WARNING**: API errors, failed send attempts
- **ERROR**: System errors, exceptions

### Monitoring Logs
```bash
# Watch logs in real-time
tail -f logs/whatsapp.log

# Filter by specific event
grep "failed" logs/whatsapp.log
grep "MSG91 API Error" logs/whatsapp.log
```

## Error Handling

### Common Errors

| Status | Error | Solution |
|--------|-------|----------|
| 400 | Invalid phone number format | Ensure number has country code: +971... |
| 400 | Template not found or not approved | Verify template exists and approval_status is APPROVED |
| 401 | Unauthorized | Provide valid JWT token, must be superuser |
| 403 | Forbidden | Only superusers can access this endpoint |
| 500 | MSG91 API Error | Check MSG91_AUTH_KEY and MSG91_INTEGRATED_NUMBER in settings |

### Error Response Format
```json
{
  "success": false,
  "message": "Error description",
  "response": {
    "error_code": "ERR_CODE",
    "error_message": "Detailed error from MSG91"
  }
}
```

## Testing

Run tests:
```bash
python manage.py test WhatsApp
```

Run specific test:
```bash
python manage.py test WhatsApp.tests.WhatsAppTemplateTestCase.test_create_template
```

With coverage:
```bash
coverage run --source='WhatsApp' manage.py test WhatsApp
coverage report
coverage html
```

## Django Admin Interface

Access admin at: `http://localhost:8000/admin/`

Features:
- **Template Management**: Create, edit, approve, reject templates
- **Message Logs**: View sent messages with full audit trail
- **Configuration**: Manage rate limits and settings
- **Webhook Logs**: Monitor incoming webhooks
- **Batch Actions**: Approve/reject multiple templates
- **Filtering**: Filter by status, language, category
- **Search**: Full-text search on templates and messages

## API Rate Limiting

Rate limits are configurable per integrated number:

- **Daily Limit**: Default 10,000 messages
- **Monthly Limit**: Default 300,000 messages
- **Bulk Batch Size**: Max 1,000 messages per request

Update limits via admin panel or API:
```bash
curl -X PUT \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "daily_limit": 15000,
    "monthly_limit": 500000
  }' \
  "http://localhost:8000/api/whatsapp/config/update/"
```

## Troubleshooting

### MSG91 Credentials Not Found
```
Error: MSG91 credentials not configured in settings
```

**Solution**: Ensure `MSG91_AUTH_KEY` and `MSG91_INTEGRATED_NUMBER` are set in `.env`

### Template Sync Fails
```
Failed to sync template: Invalid template format
```

**Solution**: Verify template has body_text, check header_format is valid

### Messages Showing as FAILED
Check logs for MSG91 error details in `logs/whatsapp.log`

### Unauthorized Access
```
{"detail": "Authentication credentials were not provided."}
```

**Solution**: Include `Authorization: Bearer TOKEN` header with valid JWT

## Performance Considerations

- **Bulk Messages**: Send up to 1,000 at a time to avoid timeout
- **Database Indexes**: Message queries are indexed on recipient_number and status
- **Caching**: Template lookups can be cached for faster access
- **Connection Pooling**: HTTP connections timeout after 30 seconds (configurable)

## Security Best Practices

1. ✅ Never commit `.env` file to version control
2. ✅ Use HTTPS in production (not HTTP)
3. ✅ Rotate MSG91 auth keys regularly
4. ✅ Monitor `logs/whatsapp.log` for suspicious activity
5. ✅ Restrict admin access to trusted users only
6. ✅ Use strong database passwords
7. ✅ Enable database backups
8. ✅ Review sent messages regularly via admin panel

## Future Enhancements

- [ ] Async message sending with Celery
- [ ] Advanced analytics and reporting
- [ ] Template versioning
- [ ] A/B testing support
- [ ] Scheduled message sending
- [ ] Message personalization engine
- [ ] Integration with customer CRM
- [ ] SMS fallback for failed WhatsApp messages

## Support

For issues or questions:
1. Check logs in `logs/whatsapp.log`
2. Review Django admin for message status
3. Verify MSG91 account and credentials
4. Check internet connection and firewall

## License

This integration is part of the UAE E-commerce Backend project.
