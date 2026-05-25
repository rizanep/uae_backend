# WhatsApp File Sending via MSG91 Templates - Complete Guide

## Overview

MSG91 WhatsApp API requires using **WhatsApp Message Templates** to send files. Templates are pre-approved message formats that ensure compliance with WhatsApp's policies.

**Key Points:**
- ✅ All WhatsApp messages must use templates
- ✅ Templates support media in headers (documents, images, videos)
- ✅ No direct file uploads - use template + media URL approach
- ✅ Files must be hosted at publicly accessible URLs

---

## Setup Process

### Step 1: Create WhatsApp Template in MSG91 Admin

1. **Access MSG91 Dashboard**
   - Log in to https://www.msg91.com/
   - Navigate to: WhatsApp > Templates

2. **Create New Template**
   - Click "Create Template"
   - Select Language: English
   - Choose Category: Document/Image/etc.

3. **Template Examples**

#### Example: Document Template
```
Template Name: order_receipt
Category: Document
Format: 
  Header: Document (for PDF/Word files)
  Body: Hi {{1}}, here's your {{2}} from {{3}}
  Footer: Sent via Django API
```

#### Example: Image Template
```
Template Name: product_image
Category: Image
Format:
  Header: Image (for JPG/PNG files)
  Body: Check out {{1}}: {{2}}
  CTA Button: View Details
```

#### Example: Video Template
```
Template Name: tutorial_video
Category: Video
Format:
  Header: Video
  Body: Watch {{1}} tutorial
  CTA Button: Watch Now
```

### Step 2: Get Template Information

After creation, note:
- Template Name (e.g., "order_receipt")
- Template ID (shown in admin)
- Namespace (usually auto-generated)
- Parameter count (number of {{1}}, {{2}}, etc.)

---

## Sending Files via Templates

### Approach 1: Using Python Script

```python
from test_whatsapp_template_send import MSG91WhatsAppTemplateService

service = MSG91WhatsAppTemplateService()

# Send document via template
success, response = service.send_via_template(
    template_name="order_receipt",
    recipient_number="918281740483",
    template_params={
        "1": "Invoice",
        "2": "2024",
        "3": "Company Name"
    },
    header_params={
        "link": "https://storage.googleapis.com/invoices/invoice-2024.pdf"
    }
)
```

### Approach 2: Using Django Management Command

```bash
python manage.py whatsapp_send_file_url \
  --media-url https://storage.example.com/document.pdf \
  --template order_receipt \
  918281740483 \
  "Invoice and payment details"
```

### Approach 3: Using cURL

```bash
curl -X POST https://api.msg91.com/api/v5/whatsapp/whatsapp-outbound-message/bulk/ \
  -H "authkey: YOUR_MSG91_AUTH_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "integrated_number": "971521204711",
    "content_type": "template",
    "payload": {
      "messaging_product": "whatsapp",
      "type": "template",
      "template": {
        "name": "order_receipt",
        "language": {
          "code": "en",
          "policy": "deterministic"
        },
        "to_and_components": [
          {
            "to": ["918281740483"],
            "components": {
              "header_1": {
                "link": "https://storage.example.com/invoice.pdf"
              },
              "body_1": {
                "1": "Invoice",
                "2": "2024"
              }
            }
          }
        ]
      }
    }
  }'
```

---

## Media URL Requirements

### Hosting Options

1. **Cloud Storage (Recommended)**
   - AWS S3: `https://mybucket.s3.amazonaws.com/document.pdf`
   - Google Cloud Storage: `https://storage.googleapis.com/mybucket/document.pdf`
   - Azure Blob: `https://myaccount.blob.core.windows.net/container/document.pdf`

2. **CDN Services**
   - Cloudflare: Upload and get public URL
   - Cloudinary: Upload media, get permanent URL
   - Firebase Storage: Public URL from console

3. **Your Own Server**
   - Upload files to Django `/media/whatsapp/` directory
   - Serve via Django's `FileResponse`
   - Use absolute URL: `https://yourdomain.com/media/whatsapp/file.pdf`

### URL Requirements
- ✅ Must be publicly accessible (no authentication)
- ✅ Must be HTTPS (no HTTP)
- ✅ File must be less than 100MB
- ✅ URL must be valid (404 errors will fail delivery)

---

## Supported File Types

### Documents
- PDF (`.pdf`)
- Microsoft Word (`.doc`, `.docx`)
- Microsoft Excel (`.xls`, `.xlsx`)
- Text (`.txt`)
- Maximum size: 100MB

### Images
- JPEG (`.jpg`, `.jpeg`)
- PNG (`.png`)
- GIF (`.gif`)
- Maximum size: 100MB

### Videos
- MP4 (`.mp4`)
- Maximum size: 100MB

### Audio
- MP3 (`.mp3`)
- WAV (`.wav`)
- Maximum size: 100MB

---

## API Response Format

### Successful Response (200/201)
```json
{
  "hasError": false,
  "data": {
    "id": "messageId_12345",
    "status": "submitted"
  }
}
```

### Error Response (400/401/404)
```json
{
  "hasError": true,
  "status": "fail",
  "errors": "Template 'invalid_template' not found"
}
```

### Common Errors
| Error | Cause | Solution |
|-------|-------|----------|
| "Template not found" | Wrong template name | Check template name in MSG91 admin |
| "Invalid parameters" | Wrong number of {{1}}, {{2}} | Match template parameters |
| "URL not accessible" | Media URL returns 404 | Verify file URL works in browser |
| "Invalid phone format" | Wrong phone number | Use format: country code + number |
| "Authentication failed" | Wrong API key | Check MSG91_AUTH_KEY in .env |

---

## Best Practices

### 1. Template Design
```
✅ Good: "Your invoice {{1}} is ready"
❌ Bad: "Your {{1}} {{2}} {{3}} {{4}} from {{5}}"
```

### 2. Media URLs
```
✅ Always use HTTPS
✅ Test URL in browser first
✅ Use CDN for reliability
❌ Don't use HTTP URLs
❌ Don't use localhost URLs
```

### 3. Phone Numbers
```
✅ 918281740483 (India, with country code)
✅ 971521204711 (UAE, with country code)
❌ 8281740483 (missing country code)
❌ +918281740483 (script removes + automatically)
```

### 4. Error Handling
```python
success, response = service.send_via_template(...)

if success:
    print("✅ Message sent successfully")
else:
    error = response.get('errors', 'Unknown error')
    print(f"❌ Failed: {error}")
    # Log to monitoring system
    # Retry with exponential backoff
```

---

## Troubleshooting

### Issue: "for now, only template is supported for bulk"
**Cause:** Trying to send without using a template  
**Solution:** Create template in MSG91 admin, use template name in API call

### Issue: URL returns 404 from MSG91
**Cause:** File URL is not accessible or HTTPS  
**Solution:**
1. Test URL in browser: `curl -I https://your-url`
2. Ensure file is publicly accessible
3. Use HTTPS, not HTTP

### Issue: "invalid_template" error
**Cause:** Template name doesn't exist or has typo  
**Solution:** Check exact template name in MSG91 admin (case-sensitive)

### Issue: Message not delivered to recipient
**Cause:** Phone number incorrect or not opted-in  
**Solution:**
1. Verify phone format (with country code)
2. Ensure recipient has contacted business before (WhatsApp requirement)
3. Check MSG91 delivery reports

---

## Django Integration

### Models (if storing templates)
```python
class WhatsAppTemplate(models.Model):
    name = models.CharField(max_length=100)  # e.g., "order_receipt"
    description = models.TextField()
    category = models.CharField(max_length=20)  # document, image, video, audio
    header_type = models.CharField(max_length=20)  # DOCUMENT, IMAGE, VIDEO, etc.
    param_count = models.IntegerField()  # Number of {{1}}, {{2}}, etc.
    msg91_template_id = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
```

### View Example
```python
from django.views import View
from django.http import JsonResponse

class SendDocumentView(View):
    def post(self, request):
        recipient = request.POST.get('phone')
        file_url = request.POST.get('url')
        template = request.POST.get('template', 'document_send')
        
        service = MSG91WhatsAppTemplateService()
        success, response = service.send_via_template(
            template_name=template,
            recipient_number=recipient,
            header_params={"link": file_url}
        )
        
        return JsonResponse({
            "success": success,
            "response": response
        })
```

---

## References

- MSG91 Documentation: https://www.msg91.com/
- WhatsApp Business API: https://developers.facebook.com/docs/whatsapp/
- Template Guidelines: Refer to MSG91 admin panel

---

## Quick Summary

1. **Create template** in MSG91 admin with media header
2. **Host file** at public HTTPS URL
3. **Send message** using template + URL via API
4. **Receive delivery status** in response

That's it! Files are now being sent through WhatsApp via MSG91.
