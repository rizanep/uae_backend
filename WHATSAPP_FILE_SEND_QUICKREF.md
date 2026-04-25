# WhatsApp File Send - Quick Reference

## Quick Start (30 seconds)

```bash
# 1. Setup environment (one time)
export MSG91_AUTH_KEY="your_key_here"
export MSG91_INTEGRATED_NUMBER="918281740483"

# 2. Send file
python send_whatsapp_file.py report.pdf 918281740483 "My Report"
```

## Three Ways to Send Files

### Method 1: Simple Python Script ⚡ FASTEST
```bash
python send_whatsapp_file.py <file> <phone> [caption]
```
**Best for:** Quick tests, one-off sends

### Method 2: Full Test Script 🧪 COMPLETE
```bash
python test_whatsapp_file_send.py
```
**Best for:** Testing, debugging, learning

### Method 3: Django Command 🏢 PRODUCTION
```bash
python manage.py whatsapp_send_file <file> <phone> --caption "caption"
```
**Best for:** Production, integration, logging

---

## Examples

### Send PDF
```bash
python send_whatsapp_file.py invoice.pdf 918281740483 "Invoice #2024-001"
```

### Send Image
```bash
python send_whatsapp_file.py screenshot.jpg 918281740483 "Check this"
```

### Send Video
```bash
python send_whatsapp_file.py demo.mp4 918281740483 "Product Demo"
```

### Send Document
```bash
python send_whatsapp_file.py contract.docx 918281740483 "Contract to sign"
```

---

## Phone Number Examples

| Country | Format | Example |
|---------|--------|---------|
| India | +91 | 918281740483 |
| UAE | +971 | 971501234567 |
| USA | +1 | 13105551234 |
| UK | +44 | 442071838750 |
| Saudi | +966 | 966501234567 |

---

## Supported File Types

| Category | Extensions | Limit |
|----------|-----------|-------|
| Documents | .pdf, .doc, .docx, .xls, .xlsx, .txt | 100MB |
| Images | .jpg, .jpeg, .png, .gif | 100MB |
| Video | .mp4 | 100MB |
| Audio | .mp3, .wav | 100MB |

---

## Success Response
```
✅ File sent successfully!
   Message ID: 1234567890
```

## Troubleshooting

| Error | Fix |
|-------|-----|
| MSG91_AUTH_KEY not configured | `export MSG91_AUTH_KEY="..."` |
| File not found | Use absolute path or check file exists |
| Invalid phone number | Add country code (e.g., 918281740483) |
| File exceeds limit | Compress file or split |
| Connection timeout | Check internet, verify MSG91 is reachable |

---

## Files Created

```
uae_backend/
├── send_whatsapp_file.py                    # Simple CLI
├── test_whatsapp_file_send.py               # Full test suite
├── WHATSAPP_FILE_SEND_GUIDE.md              # Full documentation
├── WHATSAPP_FILE_SEND_QUICKREF.md           # This file
└── WhatsApp/management/commands/
    └── whatsapp_send_file.py                # Django command
```

---

## Environment Setup

### Option 1: .env file
```
MSG91_AUTH_KEY=your_key_here
MSG91_INTEGRATED_NUMBER=918281740483
```

### Option 2: Export in terminal
```bash
export MSG91_AUTH_KEY="your_key_here"
export MSG91_INTEGRATED_NUMBER="918281740483"
```

### Option 3: Django settings
```python
# settings.py
MSG91_AUTH_KEY = os.environ.get('MSG91_AUTH_KEY')
MSG91_INTEGRATED_NUMBER = os.environ.get('MSG91_INTEGRATED_NUMBER', '918281740483')
```

---

## Common Tasks

### Generate Test PDF and Send
```bash
python test_whatsapp_file_send.py
```

### Send Invoice to Customer
```bash
python send_whatsapp_file.py invoice_2024_001.pdf 918281740483 "Your Invoice"
```

### Send Report to Manager
```bash
python manage.py whatsapp_send_file monthly_report.pdf 971501234567 --caption "Monthly Report - April 2024"
```

### Send Bulk Files (script)
```bash
for phone in 918281740483 918281740484 918281740485; do
  python send_whatsapp_file.py report.pdf $phone "Monthly Report"
done
```

### Check Message Status
```bash
# View logs
tail -f logs/whatsapp.log | grep "document"

# Or check response Message ID
python send_whatsapp_file.py file.pdf 918281740483 | grep "Message ID"
```

---

## API Reference

### Endpoint: Send Document
```
POST https://control.msg91.com/api/v5/whatsapp/whatsapp-outbound-message/document/
```

### Headers
```
authkey: <MSG91_AUTH_KEY>
```

### Form Data
```json
{
  "authkey": "your_key",
  "integrated_number": "918281740483",
  "content_type": "document",
  "payload": {
    "messaging_product": "whatsapp",
    "type": "document",
    "document": {"caption": "File caption"},
    "to": ["918281740483"]
  }
}
```

### Success Response (200)
```json
{
  "message_id": "1234567890",
  "message": "Message sent successfully"
}
```

---

## Need Help?

1. **Check Configuration:**
   ```bash
   python manage.py shell
   >>> from django.conf import settings
   >>> print(settings.MSG91_AUTH_KEY)
   >>> print(settings.MSG91_INTEGRATED_NUMBER)
   ```

2. **Test Connection:**
   ```bash
   python test_whatsapp_file_send.py
   ```

3. **View Logs:**
   ```bash
   tail -f logs/whatsapp.log
   ```

4. **Check File:**
   ```bash
   ls -lh report.pdf
   file report.pdf
   ```

5. **Validate Phone:**
   ```bash
   echo "918281740483" | grep -oE '[0-9]{10,}'
   ```

---

## Tips & Best Practices

✅ **DO:**
- Use absolute paths for files
- Include country code in phone numbers
- Add meaningful captions
- Test with small files first
- Keep auth key in environment variables
- Log all send attempts

❌ **DON'T:**
- Hardcode credentials
- Use invalid phone numbers
- Send files > 100MB
- Use spaces/special chars in paths
- Send to non-WhatsApp numbers
- Retry too many times

---

## Links

- [Full Guide](WHATSAPP_FILE_SEND_GUIDE.md)
- [MSG91 Documentation](https://control.msg91.com/docs)
- [WhatsApp Business Guide](https://www.whatsapp.com/business)

---

**Version:** 1.0  
**Updated:** April 2024  
**Status:** ✅ Production Ready
