# SMS API Examples

Complete code examples for all SMS endpoints.

## Python

### Setup

```python
import requests
import json

BASE_URL = "http://localhost:8000/api/sms"
JWT_TOKEN = "your_jwt_token_here"

headers = {
    "Authorization": f"Bearer {JWT_TOKEN}",
    "Content-Type": "application/json"
}
```

### Create Template

```python
# Create SMS template
template_data = {
    "template_name": "order_confirmation",
    "template_content": "Hi {{CUSTOMER_NAME}}, order {{ORDER_ID}} confirmed. Amount: {{AMOUNT}} AED",
    "sender_id": "MYAPP",
    "sms_type": "TRANSACTIONAL",
    "dlt_template_id": ""  # Optional for India
}

response = requests.post(
    f"{BASE_URL}/templates/",
    headers=headers,
    json=template_data
)

if response.status_code == 201:
    template = response.json()
    print(f"Template created: {template['id']}")
    print(f"Character count: {template['character_count']}")
    print(f"SMS parts: {template['sms_parts']}")
else:
    print(f"Error: {response.json()}")
```

### Approve Template

```python
# Approve template
template_id = "your_template_id"

response = requests.post(
    f"{BASE_URL}/templates/{template_id}/approve/",
    headers=headers
)

if response.status_code == 200:
    result = response.json()
    print(f"Template approved: {result['template']['approval_status']}")
else:
    print(f"Error: {response.json()}")
```

### Create in MSG91

```python
# Create template in MSG91
response = requests.post(
    f"{BASE_URL}/templates/{template_id}/create-in-msg91/",
    headers=headers
)

if response.status_code == 200:
    result = response.json()
    print(f"Template created in MSG91: {result['template_id']}")
else:
    print(f"Error: {response.json()}")
```

### Send Single SMS

```python
# Send single SMS
message_data = {
    "template": template_id,
    "recipient_number": "+971501234567",
    "variables": {
        "CUSTOMER_NAME": "Ahmed Ali",
        "ORDER_ID": "ORD-2024-001",
        "AMOUNT": "299.99"
    },
    "short_url": False,
    "realtime_response": False
}

response = requests.post(
    f"{BASE_URL}/messages/send/",
    headers=headers,
    json=message_data
)

if response.status_code == 201:
    message = response.json()['data']
    print(f"SMS sent: {message['id']}")
    print(f"Status: {message['status']}")
    print(f"Message: {message['message_content']}")
else:
    print(f"Error: {response.json()}")
```

### Send Bulk SMS

```python
# Send bulk SMS to multiple recipients
bulk_data = {
    "template_id": template_id,
    "recipient_numbers": [
        "+971501234567",
        "+971502345678",
        "+971503456789",
        "+971504567890"
    ],
    "variables_list": [
        {
            "CUSTOMER_NAME": "Ahmed Ali",
            "ORDER_ID": "ORD-2024-001",
            "AMOUNT": "299.99"
        },
        {
            "CUSTOMER_NAME": "Sara Mohammed",
            "ORDER_ID": "ORD-2024-002",
            "AMOUNT": "149.99"
        },
        {
            "CUSTOMER_NAME": "Ali Hassan",
            "ORDER_ID": "ORD-2024-003",
            "AMOUNT": "499.99"
        },
        {
            "CUSTOMER_NAME": "Fatima Ibrahim",
            "ORDER_ID": "ORD-2024-004",
            "AMOUNT": "199.99"
        }
    ],
    "short_url": False
}

response = requests.post(
    f"{BASE_URL}/messages/send-bulk/",
    headers=headers,
    json=bulk_data
)

if response.status_code == 201:
    result = response.json()
    print(f"Bulk SMS sent: {result['sent_count']} messages")
else:
    print(f"Error: {response.json()}")
```

### List Templates

```python
# List all templates
response = requests.get(
    f"{BASE_URL}/templates/?approval_status=APPROVED",
    headers=headers
)

if response.status_code == 200:
    templates = response.json()['results']
    for template in templates:
        print(f"- {template['template_name']}: {template['character_count']} chars")
else:
    print(f"Error: {response.json()}")
```

### List Messages

```python
# List all sent messages
response = requests.get(
    f"{BASE_URL}/messages/?status=DELIVERED&ordering=-sent_at",
    headers=headers
)

if response.status_code == 200:
    messages = response.json()['results']
    for msg in messages:
        print(f"- {msg['recipient_number']}: {msg['status']} ({msg['sent_at']})")
else:
    print(f"Error: {response.json()}")
```

### Get Message Details

```python
# Get specific message details
message_id = "message_uuid"

response = requests.get(
    f"{BASE_URL}/messages/{message_id}/",
    headers=headers
)

if response.status_code == 200:
    message = response.json()
    print(f"Recipient: {message['recipient_number']}")
    print(f"Status: {message['status']}")
    print(f"Sent at: {message['sent_at']}")
    print(f"Delivered at: {message['delivered_at']}")
    print(f"Message: {message['message_content']}")
else:
    print(f"Error: {response.json()}")
```

### Get Configuration

```python
# Get SMS configuration
response = requests.get(
    f"{BASE_URL}/config/retrieve/",
    headers=headers
)

if response.status_code == 200:
    config = response.json()
    print(f"Sender ID: {config['sender_id']}")
    print(f"Active: {config['is_active']}")
    print(f"Daily limit: {config['daily_limit']}")
    print(f"Cost per SMS: {config['cost_per_sms']} AED")
else:
    print(f"Error: {response.json()}")
```

### Update Configuration

```python
# Update SMS configuration
config_update = {
    "daily_limit": 5000,
    "monthly_limit": 150000,
    "cost_per_sms": "0.60"
}

response = requests.put(
    f"{BASE_URL}/config/update/",
    headers=headers,
    json=config_update
)

if response.status_code == 200:
    config = response.json()
    print(f"Configuration updated")
else:
    print(f"Error: {response.json()}")
```

### Get SMS Logs

```python
# Get SMS delivery logs from MSG91
params = {
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
}

response = requests.get(
    f"{BASE_URL}/reports/logs/",
    headers=headers,
    params=params
)

if response.status_code == 200:
    result = response.json()
    print(f"Total logs: {result['count']}")
    for log in result['data']:
        print(f"- {log['recipient']}: {log['status']} ({log['submitted']})")
else:
    print(f"Error: {response.json()}")
```

## cURL

### Create Template

```bash
curl -X POST http://localhost:8000/api/sms/templates/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "welcome_sms",
    "template_content": "Welcome {{NAME}} to our service!",
    "sender_id": "MYAPP",
    "sms_type": "TRANSACTIONAL"
  }'
```

### Approve Template

```bash
curl -X POST http://localhost:8000/api/sms/templates/TEMPLATE_ID/approve/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Send SMS

```bash
curl -X POST http://localhost:8000/api/sms/messages/send/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "template": "TEMPLATE_ID",
    "recipient_number": "+971501234567",
    "variables": {
      "NAME": "Ahmed"
    }
  }'
```

### Send Bulk SMS

```bash
curl -X POST http://localhost:8000/api/sms/messages/send-bulk/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "TEMPLATE_ID",
    "recipient_numbers": ["+971501234567", "+971502345678"],
    "variables_list": [
      {"NAME": "Ahmed"},
      {"NAME": "Sara"}
    ]
  }'
```

### List Messages

```bash
curl -X GET "http://localhost:8000/api/sms/messages/?status=DELIVERED" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Get Configuration

```bash
curl -X GET http://localhost:8000/api/sms/config/retrieve/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Node.js

### Setup

```javascript
const axios = require('axios');

const api = axios.create({
  baseURL: 'http://localhost:8000/api/sms',
  headers: {
    'Authorization': `Bearer YOUR_JWT_TOKEN`,
    'Content-Type': 'application/json'
  }
});
```

### Create Template

```javascript
async function createTemplate() {
  try {
    const response = await api.post('/templates/', {
      template_name: 'order_confirmation',
      template_content: 'Hi {{NAME}}, your order {{ORDER}} is confirmed',
      sender_id: 'MYAPP',
      sms_type: 'TRANSACTIONAL'
    });
    
    console.log('Template created:', response.data.id);
    return response.data;
  } catch (error) {
    console.error('Error:', error.response.data);
  }
}
```

### Send SMS

```javascript
async function sendSMS(templateId, phoneNumber, variables) {
  try {
    const response = await api.post('/messages/send/', {
      template: templateId,
      recipient_number: phoneNumber,
      variables: variables
    });
    
    console.log('SMS sent:', response.data.data.id);
    console.log('Status:', response.data.data.status);
    return response.data;
  } catch (error) {
    console.error('Error:', error.response.data);
  }
}
```

### Send Bulk SMS

```javascript
async function sendBulkSMS(templateId, recipients) {
  try {
    const response = await api.post('/messages/send-bulk/', {
      template_id: templateId,
      recipient_numbers: recipients.map(r => r.phone),
      variables_list: recipients.map(r => r.variables)
    });
    
    console.log('Bulk SMS sent:', response.data.sent_count, 'messages');
    return response.data;
  } catch (error) {
    console.error('Error:', error.response.data);
  }
}
```

## Common Patterns

### Send OTP SMS

```python
# Create OTP template
otp_template = {
    "template_name": "otp_verification",
    "template_content": "Your OTP is {{OTP}}. Valid for 10 minutes.",
    "sender_id": "MYAPP",
    "sms_type": "OTP"
}

# Send OTP
import random
otp = str(random.randint(100000, 999999))

message = {
    "template": template_id,
    "recipient_number": phone_number,
    "variables": {"OTP": otp}
}

response = requests.post(f"{BASE_URL}/messages/send/", 
                        headers=headers, json=message)
```

### Send Promotional SMS

```python
# Create promotional template
promo_template = {
    "template_name": "flash_sale",
    "template_content": "Flash sale! {{DISCOUNT}}% off {{PRODUCT}}. Use code {{CODE}}",
    "sender_id": "MYAPP",
    "sms_type": "PROMOTIONAL"
}

# Send to customer list
customers = [
    {"phone": "+971501234567", "discount": 20, "product": "T-Shirt", "code": "FLASH20"},
    {"phone": "+971502345678", "discount": 30, "product": "Shoes", "code": "FLASH30"},
]

variables_list = [
    {"DISCOUNT": c["discount"], "PRODUCT": c["product"], "CODE": c["code"]}
    for c in customers
]

response = requests.post(
    f"{BASE_URL}/messages/send-bulk/",
    headers=headers,
    json={
        "template_id": template_id,
        "recipient_numbers": [c["phone"] for c in customers],
        "variables_list": variables_list
    }
)
```

## Error Handling

```python
def send_sms_safe(template_id, phone_number, variables):
    """Send SMS with error handling"""
    try:
        response = requests.post(
            f"{BASE_URL}/messages/send/",
            headers=headers,
            json={
                "template": template_id,
                "recipient_number": phone_number,
                "variables": variables
            },
            timeout=30
        )
        
        if response.status_code == 201:
            return {"success": True, "message_id": response.json()['data']['id']}
        
        elif response.status_code == 400:
            return {"success": False, "error": response.json()['message']}
        
        elif response.status_code == 403:
            return {"success": False, "error": "Insufficient permissions"}
        
        elif response.status_code == 404:
            return {"success": False, "error": "Template not found"}
        
        elif response.status_code == 500:
            return {"success": False, "error": "Server error"}
        
        else:
            return {"success": False, "error": f"Unexpected status: {response.status_code}"}
    
    except requests.Timeout:
        return {"success": False, "error": "Request timeout"}
    
    except Exception as e:
        return {"success": False, "error": str(e)}
```

## Rate Limiting

```python
# Check daily limit before sending
config_response = requests.get(f"{BASE_URL}/config/retrieve/", headers=headers)
config = config_response.json()

daily_limit = config['daily_limit']
cost_per_sms = config['cost_per_sms']

print(f"Daily limit: {daily_limit} messages")
print(f"Cost per SMS: {cost_per_sms} AED")
```
