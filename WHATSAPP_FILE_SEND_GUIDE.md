# WhatsApp File Send - Test & Usage Guide

Send PDF, images, videos, and other files through WhatsApp using MSG91 API.

## Prerequisites

1. **MSG91 Account** with WhatsApp integration enabled
2. **Environment Variables** configured:
   ```bash
   MSG91_AUTH_KEY=your_auth_key
   MSG91_INTEGRATED_NUMBER=918281740483  # Your WhatsApp business number
   ```

3. **Python Requests Library** installed:
   ```bash
   pip install requests
   ```

## Available Scripts

### 1. Full Test Script (`test_whatsapp_file_send.py`)

Complete test suite with multiple test cases including PDF generation.

**Usage:**
```bash
python test_whatsapp_file_send.py
```

**Features:**
- ✅ Creates sample test PDF automatically
- ✅ Sends to phone number
- ✅ Validates phone number format
- ✅ Tests with existing files
- ✅ Comprehensive logging

**Output:**
```
============================================================
WhatsApp File Send Test Script
============================================================

✅ Service initialized
   Auth Key: xxxxxxxxxx***
   Integrated Number: 918281740483

============================================================
TEST 1: Create and Send Test PDF
============================================================

✅ Test PDF created: test_document.pdf

📤 Sending WhatsApp Document:
   Recipient: 918281740483
   File: test_document.pdf
   Size: 28.50 KB
   Type: application/pdf
   Caption: Test PDF from Django Script

✅ Document sent successfully!
   Message ID: 1234567890
```

### 2. Simple CLI Script (`send_whatsapp_file.py`)

Lightweight command-line tool for sending individual files.

**Usage:**
```bash
# Send PDF with caption
python send_whatsapp_file.py report.pdf 918281740483 "Monthly Report"

# Send image
python send_whatsapp_file.py photo.jpg 918281740483 "Vacation photo"

# Send without caption
python send_whatsapp_file.py document.pdf 918281740483
```

**Supported File Types:**
- Documents: PDF, DOC, DOCX, XLS, XLSX, TXT
- Images: JPG, JPEG, PNG, GIF
- Video: MP4 (max 100MB)
- Audio: MP3, WAV

**Example:**
```bash
$ python send_whatsapp_file.py invoice.pdf 918281740483 "Invoice #INV-2024-001"

📤 Sending WhatsApp File
   File: invoice.pdf
   To: 918281740483
   Caption: Invoice #INV-2024-001

✅ File sent successfully!
   Message ID: 1234567890
```

### 3. Django Management Command (`manage.py whatsapp_send_file`)

Integrated Django command for production use.

**Usage:**
```bash
# Basic usage
python manage.py whatsapp_send_file report.pdf 918281740483

# With caption
python manage.py whatsapp_send_file report.pdf 918281740483 --caption "Monthly Report"

# Send multiple files
python manage.py whatsapp_send_file invoice.pdf 918281740483 --caption "Invoice"
python manage.py whatsapp_send_file receipt.pdf 918281740484 --caption "Receipt"
```

**Advantages:**
- ✅ Django settings integration
- ✅ Better error handling
- ✅ Logging integration
- ✅ Production-ready

**Example:**
```bash
$ python manage.py whatsapp_send_file report.pdf 918281740483 --caption "Monthly Report"

📤 Sending WhatsApp File
   Recipient: 918281740483
   File: report.pdf
   Size: 512.50 KB
   Caption: Monthly Report

Sending to MSG91...
✅ File sent successfully!
   Message ID: 1234567890
   Status Code: 200
```

## File Size Limits

| Type | Limit |
|------|-------|
| Documents | 100 MB |
| Images | 100 MB |
| Video | 100 MB |
| Audio | 100 MB |

## Phone Number Format

Use international format with country code:

✅ **Valid:**
- `918281740483` (India: +91)
- `13105551234` (USA: +1)
- `442071838750` (UK: +44)
- `971501234567` (UAE: +971)

❌ **Invalid:**
- `8281740483` (missing country code)
- `+91-8281-740483` (with dashes)
- `91 8281 740483` (with spaces)

## Testing Steps

### Step 1: Verify Configuration
```bash
# Check environment variables
echo $MSG91_AUTH_KEY
echo $MSG91_INTEGRATED_NUMBER

# Or in Django shell
python manage.py shell
>>> from django.conf import settings
>>> settings.MSG91_AUTH_KEY
>>> settings.MSG91_INTEGRATED_NUMBER
```

### Step 2: Create Test PDF
```bash
python test_whatsapp_file_send.py
# This will create test_document.pdf automatically
```

### Step 3: Send Test File
```bash
python send_whatsapp_file.py test_document.pdf 918281740483 "Test from Script"
```

### Step 4: Verify Delivery
- Check recipient's WhatsApp
- Verify message ID in response
- Check logs: `tail -f logs/whatsapp.log`

## API Response Examples

### Success Response (200/201)
```json
{
  "success": true,
  "status_code": 200,
  "message_id": "1234567890",
  "response": {
    "message_id": "1234567890",
    "message": "Message sent successfully"
  }
}
```

### Error Response
```json
{
  "success": false,
  "status_code": 400,
  "error": "Invalid phone number format",
  "response": {
    "message": "Invalid recipient"
  }
}
```

## Common Errors & Solutions

### Error: MSG91_AUTH_KEY not configured
**Solution:**
```bash
# Set in .env
export MSG91_AUTH_KEY="your_key_here"

# Or in Django settings
MSG91_AUTH_KEY = os.environ.get('MSG91_AUTH_KEY', 'default_key')
```

### Error: File not found
**Solution:**
```bash
# Use absolute path
python send_whatsapp_file.py /home/user/documents/report.pdf 918281740483

# Or relative from project root
python send_whatsapp_file.py ./media/report.pdf 918281740483
```

### Error: Invalid phone number
**Solution:**
```bash
# Add country code
# Wrong: 8281740483
# Right: 918281740483

# Remove special characters
# Wrong: +91-8281-740483
# Right: 918281740483
```

### Error: File exceeds size limit
**Solution:**
```bash
# Compress file before sending
# For PDF: Use online compressor or ghostscript
gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/ebook -dNOPAUSE -dQUIET -dBATCH -sOutputFile=output.pdf input.pdf

# For images: Use ImageMagick
convert image.jpg -resize 50% compressed_image.jpg

# For video: Use FFmpeg
ffmpeg -i video.mp4 -vf scale=1280:720 -crf 25 compressed_video.mp4
```

### Error: timeout or connection error
**Solution:**
```bash
# Check internet connection
ping control.msg91.com

# Verify firewall allows HTTPS (port 443)
nc -zv control.msg91.com 443

# Try with increased timeout (modify script)
timeout=60  # Default is 30 seconds
```

## Integration with Django Views

Send files directly from your views:

```python
from pathlib import Path
import requests
import json

def send_invoice(request, invoice_id):
    """Send invoice via WhatsApp"""
    
    invoice = Invoice.objects.get(id=invoice_id)
    
    # Generate PDF (your implementation)
    pdf_path = generate_invoice_pdf(invoice)
    
    # Send via WhatsApp
    auth_key = settings.MSG91_AUTH_KEY
    phone = invoice.customer.whatsapp_number
    
    with open(pdf_path, 'rb') as f:
        files = {'document': (Path(pdf_path).name, f, 'application/pdf')}
        data = {
            'authkey': auth_key,
            'integrated_number': '918281740483',
            'content_type': 'document',
            'payload': json.dumps({
                'messaging_product': 'whatsapp',
                'type': 'document',
                'document': {'caption': f'Invoice {invoice.number}'},
                'to': [phone]
            })
        }
        
        response = requests.post(
            'https://control.msg91.com/api/v5/whatsapp/whatsapp-outbound-message/document/',
            headers={'authkey': auth_key},
            data=data,
            files=files
        )
    
    if response.status_code == 200:
        invoice.whatsapp_sent = True
        invoice.save()
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False, 'error': response.text}, status=400)
```

## Production Deployment

1. **Use Django Management Command** - Most reliable
2. **Add to Celery Tasks** - For async sending
3. **Error Handling** - Wrap in try-except
4. **Logging** - Log all send attempts
5. **Rate Limiting** - Implement queue limits
6. **Validation** - Always validate phone numbers

### Example Celery Task

```python
from celery import shared_task
from django.conf import settings
import requests

@shared_task
def send_whatsapp_file_async(file_path, phone_number, caption=None):
    """Async WhatsApp file send"""
    
    try:
        auth_key = settings.MSG91_AUTH_KEY
        
        with open(file_path, 'rb') as f:
            files = {'document': (Path(file_path).name, f, 'application/pdf')}
            data = {
                'authkey': auth_key,
                'integrated_number': '918281740483',
                'content_type': 'document',
                'payload': json.dumps({
                    'messaging_product': 'whatsapp',
                    'type': 'document',
                    'document': {'caption': caption or Path(file_path).name},
                    'to': [phone_number]
                })
            }
            
            response = requests.post(
                'https://control.msg91.com/api/v5/whatsapp/whatsapp-outbound-message/document/',
                headers={'authkey': auth_key},
                data=data,
                files=files,
                timeout=30
            )
        
        return {
            'success': response.status_code == 200,
            'message_id': response.json().get('message_id')
        }
    
    except Exception as e:
        return {'success': False, 'error': str(e)}
```

## Monitoring & Logging

Check WhatsApp logs:
```bash
# View logs
tail -f logs/whatsapp.log

# Filter send attempts
grep "document" logs/whatsapp.log

# Count sent messages
grep "Document sent successfully" logs/whatsapp.log | wc -l
```

## Support

For issues:
1. Check MSG91 dashboard for account status
2. Verify API key is active
3. Check phone number is properly integrated
4. Review MSG91 documentation: https://control.msg91.com/docs
5. Contact MSG91 support: support@msg91.com
