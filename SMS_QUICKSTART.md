# SMS Integration Quick Start (5 Minutes)

Get SMS working in 5 minutes.

## Step 1: Install (1 minute)

Add to `core/settings.py`:
```python
INSTALLED_APPS = [
    # ...
    'SMS',
]
```

Add to `core/urls.py`:
```python
urlpatterns = [
    # ...
    path('api/sms/', include('SMS.urls')),
]
```

## Step 2: Configure (1 minute)

Set environment variables (`.env` or export):
```bash
MSG91_AUTH_KEY=your_key_here
MSG91_ROUTE=transactional
```

## Step 3: Migrate (1 minute)

```bash
python manage.py migrate SMS
```

## Step 4: Test (1 minute)

```bash
python manage.py sms_manage test-connection
```

Should show: `✓ MSG91 connection successful!`

## Step 5: Send SMS (1 minute)

Get JWT token for superuser:
```bash
curl -X POST http://localhost:8000/api/token/ \
  -d "username=admin&password=your_password"
```

Create template:
```bash
curl -X POST http://localhost:8000/api/sms/templates/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "welcome",
    "template_content": "Welcome {{NAME}}!",
    "sender_id": "MYAPP",
    "sms_type": "TRANSACTIONAL"
  }'
```

Copy template ID from response.

Approve template in Django admin:
- Go to `/admin/SMS/smstemplate/`
- Select template
- Click "Approve selected templates"
- Save

Send SMS:
```bash
curl -X POST http://localhost:8000/api/sms/messages/send/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "template": "YOUR_TEMPLATE_ID",
    "recipient_number": "+971501234567",
    "variables": {
      "NAME": "Ahmed"
    }
  }'
```

Done! SMS sent successfully.

## Troubleshooting

**"MSG91 connection failed"**
- Check MSG91_AUTH_KEY is correct
- Verify internet connection

**"Template not found"**
- Make sure template is approved
- Check template ID is correct

**"Invalid phone number"**
- Phone must be 10+ digits
- Use international format (+971...)

**"Permission denied"**
- Must be superuser
- Check JWT token is valid

## Next Steps

- [Full API Guide](SMS_INTEGRATION_README.md)
- [API Examples](SMS_API_EXAMPLES.md)
- [Python SDK](SMS_PYTHON_SDK.md)
