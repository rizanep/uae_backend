# MSG91 WhatsApp Integration - Quick Start Guide

Get up and running with WhatsApp messaging in 5 minutes!

## 📋 Prerequisites

- Django 6.0+ project running
- Superuser account created
- MSG91 account with WhatsApp integration enabled
- Your MSG91 Auth Key and Integrated Number

## 🚀 Quick Start (5 Minutes)

### Step 1: Configure Environment Variables

Update your `.env` file:

```env
MSG91_AUTH_KEY=your_actual_auth_key
MSG91_INTEGRATED_NUMBER=+971501234567
WHATSAPP_ENABLE_LOGGING=true
```

### Step 2: Run Migrations

```bash
python manage.py migrate WhatsApp
```

### Step 3: Create Templates in Django Admin

1. Visit: `http://localhost:8000/admin/`
2. Go to **WhatsApp > WhatsApp Templates**
3. Click **Add WhatsApp Template**
4. Fill in the form:
   - Template Name: `order_confirmation`
   - Integrated Number: `+971501234567`
   - Language: `English`
   - Category: `TRANSACTIONAL`
   - Body Text: `Hello {{1}}, Your order #{{2}} is confirmed!`
5. Click **Save**
6. Click **Sync with MSG91** button (near template name)

### Step 4: Approve the Template

Template will be pending approval. To approve:
1. In admin, select the template
2. Change Status to **APPROVED**
3. Click **Save**

Or use the API:
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  "http://localhost:8000/api/whatsapp/templates/YOUR_TEMPLATE_UUID/approve/"
```

### Step 5: Send Your First Message

#### Via Admin Panel

1. Go to **WhatsApp > WhatsApp Messages**
2. (Note: Messages are typically created via API)

#### Via API (Python)

```python
import requests
import json

# Get your JWT token first
auth_response = requests.post(
    'http://localhost:8000/api/users/login/',
    json={'email': 'admin@example.com', 'password': 'your_password'}
)
token = auth_response.json()['access']

# Send message
headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

message = {
    'template': 'template-uuid-from-admin',
    'recipient_number': '+971509876543',
    'variables': {
        'body_1': 'Ahmed',
        'body_2': 'ORD-12345'
    }
}

response = requests.post(
    'http://localhost:8000/api/whatsapp/messages/send/',
    headers=headers,
    json=message
)

print(json.dumps(response.json(), indent=2))
```

#### Via cURL

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "template": "template-uuid",
    "recipient_number": "+971509876543",
    "variables": {
      "body_1": "Ahmed",
      "body_2": "ORD-12345"
    }
  }' \
  "http://localhost:8000/api/whatsapp/messages/send/"
```

### Step 6: Check Message Status

In Django Admin:
1. Go to **WhatsApp > WhatsApp Messages**
2. View the message you just sent
3. Check the status (SENT, DELIVERED, READ, or FAILED)

## 📚 Common Tasks

### Create a Marketing Template

```python
import requests

token = "YOUR_JWT_TOKEN"
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

template = {
    'template_name': 'promotional_offer',
    'integrated_number': '+971501234567',
    'language': 'en',
    'category': 'MARKETING',
    'header_format': 'IMAGE',
    'header_text': 'Summer Sale',
    'body_text': 'Check out our summer collection! Save up to {{1}}%',
    'footer_text': 'Limited time offer',
    'buttons': [
        {
            'type': 'URL',
            'text': 'Shop Now',
            'url': 'https://example.com/summer-sale'
        }
    ]
}

response = requests.post(
    'http://localhost:8000/api/whatsapp/templates/',
    headers=headers,
    json=template
)

print(response.json())
```

### Send Bulk Messages

```python
import requests

token = "YOUR_JWT_TOKEN"
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

bulk_message = {
    'template_id': 'template-uuid',
    'recipient_numbers': [
        '+971501234567',
        '+971509876543',
        '+971502345678'
    ],
    'variables_list': [
        {'body_1': 'Ahmed', 'body_2': 'ORDER-001'},
        {'body_1': 'Sara', 'body_2': 'ORDER-002'},
        {'body_1': 'Ali', 'body_2': 'ORDER-003'}
    ]
}

response = requests.post(
    'http://localhost:8000/api/whatsapp/messages/send-bulk/',
    headers=headers,
    json=bulk_message
)

print(response.json())
```

### View Message Logs

```bash
# List all messages
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/api/whatsapp/messages/"

# Filter by status
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/api/whatsapp/messages/?status=DELIVERED"

# Search by recipient
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/api/whatsapp/messages/?search=971509876543"
```

## 🔍 Troubleshooting

### "MSG91 credentials not configured"

**Problem**: Error when trying to send messages

**Solution**: 
1. Check `.env` file has `MSG91_AUTH_KEY` and `MSG91_INTEGRATED_NUMBER`
2. Verify values are not empty
3. Restart Django server
4. Test credentials in MSG91 control panel

### "Template not found or not approved"

**Problem**: Message send fails with this error

**Solution**:
1. Verify template UUID is correct
2. Check template status in admin is **APPROVED**
3. Ensure you synced the template with MSG91 first

### "Invalid phone number format"

**Problem**: Error when sending to a recipient

**Solution**:
1. Phone must include country code: `+971...`
2. Phone must be 10-15 digits total
3. No spaces or dashes in number

### Messages Showing as FAILED

**Problem**: Messages sent but status is FAILED

**Solution**:
1. Check `logs/whatsapp.log` for error details
2. Common issues:
   - Template not approved
   - Invalid recipient number
   - API rate limit exceeded
   - MSG91 account issue

### "Unauthorized" Error

**Problem**: Getting 401 or 403 response

**Solution**:
1. Include valid JWT token in header: `Authorization: Bearer TOKEN`
2. Ensure user is superuser
3. Get fresh token if expired

## 📊 Monitoring

### View Logs

```bash
# Real-time logs
tail -f logs/whatsapp.log

# Recent errors
grep "ERROR\|FAILED" logs/whatsapp.log | tail -20

# Today's activity
grep "$(date +%Y-%m-%d)" logs/whatsapp.log
```

### Check Admin Dashboard

1. **Templates**: View all templates and their status
2. **Messages**: Track sent messages and delivery
3. **Configuration**: Monitor rate limits and usage
4. **Webhooks**: See incoming webhook events

## 🔐 Security Tips

1. ✅ Keep `.env` file private (add to `.gitignore`)
2. ✅ Use strong passwords for admin accounts
3. ✅ Rotate MSG91 API keys periodically
4. ✅ Monitor logs for suspicious activity
5. ✅ Use HTTPS in production (not HTTP)
6. ✅ Restrict admin panel access by IP if possible

## 📈 Next Steps

1. **Read full documentation**: [WHATSAPP_INTEGRATION_README.md](WHATSAPP_INTEGRATION_README.md)
2. **Explore API endpoints**: Test all endpoints in your preferred tool (Postman, Insomnia, etc.)
3. **Setup webhooks**: Configure MSG91 webhooks to get delivery updates
4. **Integrate with app**: Add WhatsApp messaging to your application features
5. **Setup monitoring**: Configure alerts for failed messages
6. **Performance tuning**: Optimize message batching and rate limiting

## 🎯 Example Use Cases

### 1. Order Notifications
```python
# When order is created
send_whatsapp_message(
    template='order_confirmation',
    customer_phone=order.customer.phone,
    variables={
        'body_1': order.customer.name,
        'body_2': order.order_number
    }
)
```

### 2. Delivery Updates
```python
# When order is shipped
send_whatsapp_message(
    template='order_shipped',
    customer_phone=order.customer.phone,
    variables={
        'body_1': order.customer.name,
        'body_2': tracking_number
    }
)
```

### 3. Marketing Campaigns
```python
# Send to multiple users
send_bulk_whatsapp(
    template='summer_sale',
    recipients=[user.phone for user in users_in_segment],
    variables=generate_variables_for_each_user()
)
```

## 📞 Support

**For issues:**
1. Check logs: `logs/whatsapp.log`
2. Review admin panel for message status
3. Verify MSG91 account is active
4. Check internet connectivity

**For questions:**
1. Read full documentation
2. Check Django admin interface
3. Review API examples in README

---

**Happy messaging! 🚀**
