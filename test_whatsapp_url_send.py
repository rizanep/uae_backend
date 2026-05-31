#!/usr/bin/env python
"""
Test script for sending WhatsApp files via MSG91 using URL-based media
MSG91 WhatsApp API requires media to be hosted at URLs, not direct file uploads

This script demonstrates:
1. Creating test files (PDF, image, etc.)
2. Serving them locally or via URL
3. Sending via WhatsApp using MSG91 API
"""

import os
import sys
import json
import requests
from pathlib import Path
from io import BytesIO
from threading import Thread
import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from django.conf import settings


class MSG91WhatsAppURLService:
    """Send WhatsApp files via URL-based media"""
    
    API_URL = "https://api.msg91.com/api/v5/whatsapp/whatsapp-outbound-message/bulk/"
    
    def __init__(self):
        self.auth_key = os.environ.get('MSG91_AUTH_KEY') or settings.MSG91_AUTH_KEY
        self.integrated_number = os.environ.get('MSG91_INTEGRATED_NUMBER', '')
        
        if not self.auth_key:
            raise ValueError("MSG91_AUTH_KEY not configured")
        if not self.integrated_number:
            self.integrated_number = settings.MSG91_INTEGRATED_NUMBER
        
        # Mask auth key for display
        masked_key = self.auth_key[:9] + "***" if len(self.auth_key) > 9 else self.auth_key
        print(f"   Auth Key: {masked_key}")
        print(f"   Integrated Number: {self.integrated_number}")
    
    def send_via_url(self, media_url, recipient_number, media_type="document", caption=None):
        """Send file via WhatsApp using URL"""
        
        # Clean phone number
        recipient_number = str(recipient_number).replace('-', '').replace(' ', '').replace('+', '')
        
        print(f"\n📤 Sending WhatsApp {media_type}:")
        print(f"   Recipient: {recipient_number}")
        print(f"   Media URL: {media_url}")
        if caption:
            print(f"   Caption: {caption}")
        
        # Build payload
        media_obj = {"value": media_url}
        if caption and media_type in ['document', 'image', 'video']:
            media_obj["caption"] = caption
        
        payload = {
            "integrated_number": self.integrated_number,
            "content_type": media_type,
            "payload": {
                "messaging_product": "whatsapp",
                "type": media_type,
                media_type: media_obj,
                "to": [recipient_number]
            }
        }
        
        headers = {
            "authkey": self.auth_key,
            "Content-Type": "application/json",
        }
        
        print(f"\n📨 Sending to MSG91...")
        
        try:
            response = requests.post(
                self.API_URL,
                headers=headers,
                data=json.dumps(payload),
                timeout=30,
                verify=True
            )
            
            result = response.json() if response.text else {}
            
            if response.status_code in [200, 201]:
                print(f"✅ Success! (Status: {response.status_code})")
                return True, result
            else:
                print(f"❌ Failed! (Status: {response.status_code})")
                print(f"   Response: {result}")
                return False, result
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return False, {"error": str(e)}


def create_test_pdf():
    """Create a test PDF file"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        pdf_path = "test_document.pdf"
        c = canvas.Canvas(pdf_path, pagesize=letter)
        c.drawString(100, 750, "Test WhatsApp File Send")
        c.drawString(100, 730, "This is a test PDF document")
        c.drawString(100, 710, f"Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        c.drawString(100, 650, "---")
        c.drawString(100, 630, "To send files via WhatsApp, MSG91 requires:")
        c.drawString(100, 610, "1. File hosted at a publicly accessible URL")
        c.drawString(100, 590, "2. Send the URL via the bulk messaging API")
        c.drawString(100, 570, "3. Specify media type (document, image, video, audio)")
        c.save()
        
        print(f"✅ Test PDF created: {pdf_path}")
        return pdf_path
    except ImportError:
        print("❌ reportlab not installed. Install with: pip install reportlab")
        return None


def main():
    """Main test runner"""
    
    print("=" * 60)
    print("WhatsApp File Send Test (URL-Based API)")
    print("=" * 60)
    
    print("\n✅ Service initialized")
    
    try:
        service = MSG91WhatsAppURLService()
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return 1
    
    print("\n" + "=" * 60)
    print("TEST 1: Understanding the URL-Based Approach")
    print("=" * 60)
    
    print("""
MSG91 WhatsApp API works with URLs, not direct file uploads.

Step 1: Create a test PDF
""")
    
    pdf_file = create_test_pdf()
    
    print("""
Step 2: Host the file at a URL
   Options:
   a) Upload to cloud storage (S3, Cloudinary, Google Cloud Storage)
   b) Use a file hosting service (File.io, Send.firefox.com)
   c) Host on your own server
   d) Use ngrok/localtunnel to expose local server (for development)

Step 3: Send via MSG91 using the file URL

Example with a public file URL:
""")
    
    # Example with a real public file
    print("\n" + "=" * 60)
    print("TEST 2: Sending via Public File URL (Example)")
    print("=" * 60)
    
    example_url = "https://www.w3.org/WAI/WCAG21/Techniques/pdf/img/table1.pdf"
    print(f"\nUsing example PDF from W3C: {example_url}")
    
    success, response = service.send_via_url(
        example_url,
        "918281740483",
        "document",
        "Test PDF from Django"
    )
    
    if success:
        print("\n✅ TEST 2 PASSED")
    else:
        print("\n⚠️  TEST 2: File might not have been sent")
        print("   Check your MSG91 credentials and phone number")
    
    print("\n" + "=" * 60)
    print("TEST 3: Sending Different Media Types")
    print("=" * 60)
    
    test_urls = [
        ("https://via.placeholder.com/300x300.png", "image", "Test Image"),
        ("https://commondatastorage.googleapis.com/gtv-videos-library/sample/BigBuckBunny.mp4", "video", "Sample Video"),
    ]
    
    for url, media_type, caption in test_urls:
        print(f"\nTesting {media_type}...")
        # Don't actually send in tests to avoid rate limiting
        # Just show the structure
        print(f"   URL: {url}")
        print(f"   Type: {media_type}")
        print(f"   Caption: {caption}")
    
    print("\n" + "=" * 60)
    print("✅ Test Complete")
    print("=" * 60)
    
    print("""
Summary:
- MSG91 WhatsApp API works with media URLs (not direct uploads)
- Host your files on a publicly accessible server
- Use the URL when sending via WhatsApp

Quick Start:
1. Upload PDF to cloud storage (e.g., S3, Cloudinary)
2. Get the public URL
3. Run: python send_whatsapp_file_url.py <URL> <phone_number> "caption"

Or use the management command:
python manage.py whatsapp_send_file_url --media-url <URL> <phone_number> "caption"
""")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
