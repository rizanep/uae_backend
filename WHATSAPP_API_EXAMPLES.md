# MSG91 WhatsApp API - Integration Examples

Complete working examples for integrating WhatsApp messaging into your application.

## Authentication

All API calls require a JWT token. First, authenticate:

### Get JWT Token

**cURL:**
```bash
curl -X POST http://localhost:8000/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "your_password"
  }'

# Response:
# {
#   "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#   "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
# }
```

**Python:**
```python
import requests

response = requests.post(
    'http://localhost:8000/api/users/login/',
    json={
        'email': 'admin@example.com',
        'password': 'your_password'
    }
)

token = response.json()['access']
print(f"Token: {token}")
```

**Node.js:**
```javascript
const axios = require('axios');

const loginResponse = await axios.post('http://localhost:8000/api/users/login/', {
  email: 'admin@example.com',
  password: 'your_password'
});

const token = loginResponse.data.access;
console.log('Token:', token);
```

---

## Template Management

### Create Template

**cURL:**
```bash
TOKEN="your_jwt_token"

curl -X POST http://localhost:8000/api/whatsapp/templates/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
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
  }'
```

**Python:**
```python
import requests
import json

token = "your_jwt_token"
headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

template = {
    'template_name': 'order_confirmation',
    'integrated_number': '+971501234567',
    'language': 'en',
    'category': 'TRANSACTIONAL',
    'header_format': 'TEXT',
    'header_text': 'Order Confirmation',
    'body_text': 'Hello {{1}}, Your order #{{2}} has been confirmed!',
    'footer_text': 'Thank you for shopping with us',
    'buttons': [
        {
            'type': 'URL',
            'text': 'Track Order',
            'url': 'https://example.com/track/{{2}}'
        }
    ]
}

response = requests.post(
    'http://localhost:8000/api/whatsapp/templates/',
    headers=headers,
    json=template
)

print(json.dumps(response.json(), indent=2))
```

**Node.js:**
```javascript
const axios = require('axios');

const token = 'your_jwt_token';
const headers = {
  Authorization: `Bearer ${token}`,
  'Content-Type': 'application/json'
};

const template = {
  template_name: 'order_confirmation',
  integrated_number: '+971501234567',
  language: 'en',
  category: 'TRANSACTIONAL',
  header_format: 'TEXT',
  header_text: 'Order Confirmation',
  body_text: 'Hello {{1}}, Your order #{{2}} has been confirmed!',
  footer_text: 'Thank you for shopping with us',
  buttons: [
    {
      type: 'URL',
      text: 'Track Order',
      url: 'https://example.com/track/{{2}}'
    }
  ]
};

const response = await axios.post(
  'http://localhost:8000/api/whatsapp/templates/',
  template,
  { headers }
);

console.log(JSON.stringify(response.data, null, 2));
```

### List Templates

**cURL:**
```bash
TOKEN="your_jwt_token"

# List all templates
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/whatsapp/templates/"

# Filter by approval status
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/whatsapp/templates/?approval_status=APPROVED"

# Search by name
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/whatsapp/templates/?search=order"
```

**Python:**
```python
import requests

token = "your_jwt_token"
headers = {'Authorization': f'Bearer {token}'}

# List all templates
response = requests.get(
    'http://localhost:8000/api/whatsapp/templates/',
    headers=headers
)

templates = response.json()['results']
for template in templates:
    print(f"Name: {template['template_name']}, Status: {template['approval_status']}")
```

**Node.js:**
```javascript
const axios = require('axios');

const token = 'your_jwt_token';
const headers = { Authorization: `Bearer ${token}` };

const response = await axios.get(
  'http://localhost:8000/api/whatsapp/templates/',
  { headers }
);

const templates = response.data.results;
templates.forEach(template => {
  console.log(`Name: ${template.template_name}, Status: ${template.approval_status}`);
});
```

### Approve Template

**cURL:**
```bash
TOKEN="your_jwt_token"
TEMPLATE_ID="uuid-of-template"

curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "http://localhost:8000/api/whatsapp/templates/$TEMPLATE_ID/approve/"
```

**Python:**
```python
import requests

token = "your_jwt_token"
template_id = "uuid-of-template"

headers = {'Authorization': f'Bearer {token}'}

response = requests.post(
    f'http://localhost:8000/api/whatsapp/templates/{template_id}/approve/',
    headers=headers
)

print(response.json())
```

**Node.js:**
```javascript
const axios = require('axios');

const token = 'your_jwt_token';
const templateId = 'uuid-of-template';

const response = await axios.post(
  `http://localhost:8000/api/whatsapp/templates/${templateId}/approve/`,
  {},
  { headers: { Authorization: `Bearer ${token}` } }
);

console.log(response.data);
```

### Sync Template with MSG91

**cURL:**
```bash
TOKEN="your_jwt_token"
TEMPLATE_ID="uuid-of-template"

curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  "http://localhost:8000/api/whatsapp/templates/$TEMPLATE_ID/sync-with-msg91/"
```

**Python:**
```python
import requests

token = "your_jwt_token"
template_id = "uuid-of-template"

headers = {'Authorization': f'Bearer {token}'}

response = requests.post(
    f'http://localhost:8000/api/whatsapp/templates/{template_id}/sync-with-msg91/',
    headers=headers
)

if response.json()['success']:
    print("Template synced successfully!")
    print(f"MSG91 Template ID: {response.json()['template_id']}")
else:
    print(f"Sync failed: {response.json()['message']}")
```

---

## Message Sending

### Send Single Message

**cURL:**
```bash
TOKEN="your_jwt_token"

curl -X POST http://localhost:8000/api/whatsapp/messages/send/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "template": "template-uuid-here",
    "recipient_number": "+971509876543",
    "variables": {
      "body_1": "Ahmed",
      "body_2": "ORDER-12345"
    }
  }'
```

**Python:**
```python
import requests

token = "your_jwt_token"
headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

message = {
    'template': 'template-uuid-here',
    'recipient_number': '+971509876543',
    'variables': {
        'body_1': 'Ahmed',
        'body_2': 'ORDER-12345'
    }
}

response = requests.post(
    'http://localhost:8000/api/whatsapp/messages/send/',
    headers=headers,
    json=message
)

print(response.json())
```

**Node.js:**
```javascript
const axios = require('axios');

const token = 'your_jwt_token';
const headers = {
  Authorization: `Bearer ${token}`,
  'Content-Type': 'application/json'
};

const message = {
  template: 'template-uuid-here',
  recipient_number: '+971509876543',
  variables: {
    body_1: 'Ahmed',
    body_2: 'ORDER-12345'
  }
};

const response = await axios.post(
  'http://localhost:8000/api/whatsapp/messages/send/',
  message,
  { headers }
);

console.log(response.data);
```

### Send Bulk Messages

**cURL:**
```bash
TOKEN="your_jwt_token"

curl -X POST http://localhost:8000/api/whatsapp/messages/send-bulk/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "template-uuid-here",
    "recipient_numbers": [
      "+971501234567",
      "+971509876543",
      "+971502345678"
    ],
    "variables_list": [
      {"body_1": "Ahmed", "body_2": "ORDER-001"},
      {"body_1": "Sara", "body_2": "ORDER-002"},
      {"body_1": "Ali", "body_2": "ORDER-003"}
    ]
  }'
```

**Python:**
```python
import requests

token = "your_jwt_token"
headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

bulk_message = {
    'template_id': 'template-uuid-here',
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

result = response.json()
print(f"Sent: {result['sent_count']} messages")
```

**Node.js:**
```javascript
const axios = require('axios');

const token = 'your_jwt_token';
const headers = {
  Authorization: `Bearer ${token}`,
  'Content-Type': 'application/json'
};

const bulkMessage = {
  template_id: 'template-uuid-here',
  recipient_numbers: [
    '+971501234567',
    '+971509876543',
    '+971502345678'
  ],
  variables_list: [
    { body_1: 'Ahmed', body_2: 'ORDER-001' },
    { body_1: 'Sara', body_2: 'ORDER-002' },
    { body_1: 'Ali', body_2: 'ORDER-003' }
  ]
};

const response = await axios.post(
  'http://localhost:8000/api/whatsapp/messages/send-bulk/',
  bulkMessage,
  { headers }
);

console.log(`Sent: ${response.data.sent_count} messages`);
```

### List Messages

**cURL:**
```bash
TOKEN="your_jwt_token"

# List all messages
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/whatsapp/messages/"

# Filter by status
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/whatsapp/messages/?status=DELIVERED"

# Search by recipient
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/whatsapp/messages/?search=971509876543"
```

**Python:**
```python
import requests

token = "your_jwt_token"
headers = {'Authorization': f'Bearer {token}'}

# Get delivered messages
response = requests.get(
    'http://localhost:8000/api/whatsapp/messages/?status=DELIVERED',
    headers=headers
)

messages = response.json()['results']
for msg in messages:
    print(f"To: {msg['recipient_number']}, Status: {msg['status']}")
```

---

## Real-World Examples

### Order Confirmation on Purchase

**Python (Django View):**
```python
from django.shortcuts import redirect
from WhatsApp.models import WhatsAppTemplate, WhatsAppMessage
from rest_framework.decorators import api_view

@api_view(['POST'])
def create_order(request):
    # ... create order logic ...
    order = Order.objects.create(...)
    
    # Send WhatsApp confirmation
    template = WhatsAppTemplate.objects.get(
        template_name='order_confirmation',
        is_approved=True
    )
    
    WhatsAppMessage.objects.create(
        template=template,
        recipient_number=order.customer.phone,
        variables={
            'body_1': order.customer.name,
            'body_2': order.order_number
        },
        sent_by=request.user
    )
    
    # Service will send message asynchronously
    return JsonResponse({'success': True})
```

### Bulk Marketing Campaign

**Python (Celery Task):**
```python
from celery import shared_task
from WhatsApp.models import WhatsAppTemplate, WhatsAppMessage
from django.contrib.auth.models import User

@shared_task
def send_marketing_campaign(template_id, user_ids):
    """Send marketing message to multiple users"""
    template = WhatsAppTemplate.objects.get(
        id=template_id,
        is_approved=True
    )
    
    users = User.objects.filter(id__in=user_ids)
    admin = User.objects.filter(is_superuser=True).first()
    
    messages = [
        WhatsAppMessage(
            template=template,
            recipient_number=user.phone,
            variables={'body_1': user.first_name},
            sent_by=admin
        )
        for user in users
    ]
    
    WhatsAppMessage.objects.bulk_create(messages)
    return f"Sent {len(messages)} messages"
```

### Message Status Webhook Handler

**Python (Django View):**
```python
from django.views.decorators.http import csrf_exempt
from django.http import JsonResponse
from WhatsApp.models import WhatsAppMessage

@csrf_exempt
def whatsapp_webhook(request):
    """Handle MSG91 webhook events"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    data = request.POST or json.loads(request.body)
    
    # Update message status
    msg_id = data.get('message_id')
    status = data.get('status')  # delivered, read, failed
    
    try:
        message = WhatsAppMessage.objects.get(msg91_message_id=msg_id)
        message.status = status.upper()
        
        if status == 'delivered':
            message.delivered_at = timezone.now()
        elif status == 'read':
            message.read_at = timezone.now()
        
        message.save()
        
        return JsonResponse({'success': True})
    except WhatsAppMessage.DoesNotExist:
        return JsonResponse({'error': 'Message not found'}, status=404)
```

### Error Handling Wrapper

**Python:**
```python
import requests
import logging

logger = logging.getLogger(__name__)

def send_whatsapp_with_retry(template_id, recipient, variables, max_retries=3):
    """Send WhatsApp message with retry logic"""
    from WhatsApp.models import WhatsAppMessage, WhatsAppTemplate
    
    template = WhatsAppTemplate.objects.get(id=template_id, is_approved=True)
    
    for attempt in range(max_retries):
        try:
            message = WhatsAppMessage.objects.create(
                template=template,
                recipient_number=recipient,
                variables=variables,
                status='PENDING'
            )
            
            # Attempt to send
            from WhatsApp.services import MSG91WhatsAppService
            service = MSG91WhatsAppService()
            success, response = service.send_message(
                template_name=template.template_name,
                recipient_number=recipient,
                variables=variables
            )
            
            if success:
                message.status = 'SENT'
                message.msg91_message_id = response.get('message_id')
                message.save()
                logger.info(f"Message sent to {recipient}")
                return True
            else:
                message.status = 'FAILED'
                message.error_message = response.get('message')
                message.save()
                logger.warning(f"Send failed (attempt {attempt+1}): {response}")
                
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                continue
        
        except Exception as e:
            logger.error(f"Error in attempt {attempt+1}: {str(e)}")
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)
    
    return False
```

---

## Error Handling

### Common Error Responses

**Unauthorized:**
```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Forbidden (Non-Admin):**
```json
{
  "detail": "You do not have permission to perform this action."
}
```

**Invalid Template:**
```json
{
  "success": false,
  "message": "Template not found or not approved",
  "response": {}
}
```

**Invalid Phone Number:**
```json
{
  "recipient_number": ["Invalid phone number format."]
}
```

### Error Handling in Python

```python
import requests
from requests.exceptions import RequestException

token = "your_jwt_token"
headers = {'Authorization': f'Bearer {token}'}

try:
    response = requests.post(
        'http://localhost:8000/api/whatsapp/messages/send/',
        headers=headers,
        json={
            'template': 'template-uuid',
            'recipient_number': '+971509876543',
            'variables': {'body_1': 'test'}
        },
        timeout=30
    )
    
    response.raise_for_status()  # Raise for 4xx, 5xx errors
    
    result = response.json()
    
    if result.get('success'):
        print(f"Message sent: {result['data']['id']}")
    else:
        print(f"Error: {result['message']}")
        
except requests.exceptions.HTTPError as e:
    print(f"HTTP Error: {e.response.status_code}")
    print(e.response.json())
except RequestException as e:
    print(f"Request Error: {str(e)}")
```

---

## Best Practices

1. **Always use try-except** when making API calls
2. **Implement exponential backoff** for retries
3. **Log all API calls** for debugging
4. **Cache templates** to avoid repeated lookups
5. **Batch bulk messages** (max 1000 per request)
6. **Validate phone numbers** before sending
7. **Use environment variables** for API credentials
8. **Handle rate limiting** with appropriate delays
9. **Monitor delivery rates** and error patterns
10. **Test in staging** before production

---

## Rate Limits

- API: 100 requests/minute per IP
- Bulk Messages: Max 1000 per request
- Daily Limit: Configurable (default 10,000)
- Monthly Limit: Configurable (default 300,000)

---

For more information, see [WHATSAPP_INTEGRATION_README.md](WHATSAPP_INTEGRATION_README.md)
