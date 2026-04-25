#!/usr/bin/env python
"""
Test script to send PDF file through WhatsApp using MSG91 API
Usage: python test_whatsapp_file_send.py
"""

import os
import sys
import json
import requests
from pathlib import Path
from io import BytesIO

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from django.conf import settings


class WhatsAppFileService:
    """Send files through WhatsApp via MSG91 API"""
    
    CONTROL_URL = "https://control.msg91.com"
    
    def __init__(self):
        self.auth_key = os.environ.get('MSG91_AUTH_KEY') or settings.MSG91_AUTH_KEY
        self.integrated_number = os.environ.get('MSG91_INTEGRATED_NUMBER', '918281740483')
        
        if not self.auth_key:
            raise ValueError("MSG91_AUTH_KEY not configured")
    
    def _make_request(self, base_url, method, endpoint, data=None, files=None):
        """Make secure HTTPS request to MSG91"""
        url = f"{base_url}/{endpoint}"
        
        headers = {
            "authkey": self.auth_key,
        }
        
        if method == "POST":
            if files:
                # File upload - don't set Content-Type, requests will handle it
                response = requests.post(url, headers=headers, data=data, files=files, timeout=30, verify=True)
            else:
                # JSON request
                headers['Content-Type'] = 'application/json'
                response = requests.post(url, headers=headers, data=data, timeout=30, verify=True)
        else:
            response = requests.get(url, headers=headers, timeout=30, verify=True)
        
        try:
            return response.status_code, response.json()
        except:
            return response.status_code, {'raw': response.text}
    
    def send_document(self, recipient_number: str, file_path: str, caption: str = None):
        """
        Send document/PDF through WhatsApp
        
        Args:
            recipient_number: Phone number with country code (e.g., 918281740483)
            file_path: Path to the file to send
            caption: Optional caption for the document
        
        Returns:
            Tuple of (success, response_data)
        """
        
        # Verify file exists
        if not os.path.exists(file_path):
            return False, {"error": f"File not found: {file_path}"}
        
        file_size = os.path.getsize(file_path)
        
        # MSG91 limit is 100MB
        if file_size > 100 * 1024 * 1024:
            return False, {"error": "File size exceeds 100MB limit"}
        
        # Get file name and type
        file_name = Path(file_path).name
        file_type = Path(file_path).suffix.lower()
        
        # Determine MIME type
        mime_types = {
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.ppt': 'application/vnd.ms-powerpoint',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.txt': 'text/plain',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.mp4': 'video/mp4',
            '.mp3': 'audio/mpeg',
        }
        
        mime_type = mime_types.get(file_type, 'application/octet-stream')
        
        # Determine content type and field name
        if file_type in ['.jpg', '.jpeg', '.png', '.gif']:
            content_type = 'image'
            field_name = 'media'
        elif file_type in ['.mp4']:
            content_type = 'video'
            field_name = 'media'
        elif file_type in ['.mp3', '.wav']:
            content_type = 'audio'
            field_name = 'media'
        else:
            content_type = 'document'
            field_name = 'media'
        
        print(f"\n📤 Sending WhatsApp Document:")
        print(f"   Recipient: {recipient_number}")
        print(f"   File: {file_name}")
        print(f"   Size: {file_size / 1024:.2f} KB")
        print(f"   Type: {mime_type}")
        if caption:
            print(f"   Caption: {caption}")
        
        # Prepare form data
        form_data = {
            'authkey': self.auth_key,
            'integrated_number': self.integrated_number,
            'content_type': content_type,
            'payload': json.dumps({
                'messaging_product': 'whatsapp',
                'type': content_type,
                content_type: {
                    'caption': caption or file_name,
                },
                'to': [recipient_number]
            })
        }
        
        # Add file to request
        with open(file_path, 'rb') as f:
            files = {
                field_name: (file_name, f, mime_type)
            }
            
            status_code, response = self._make_request(
                self.CONTROL_URL,
                "POST",
                "api/v5/whatsapp/whatsapp-outbound-message/media/",
                data=form_data,
                files=files
            )
        
        success = status_code in [200, 201]
        
        if success:
            print(f"\n✅ Document sent successfully!")
            print(f"   Message ID: {response.get('message_id') or response.get('data', {}).get('message_id', 'N/A')}")
        else:
            print(f"\n❌ Failed to send document!")
            print(f"   Status: {status_code}")
            print(f"   Response: {response}")
        
        return success, response
    
    def send_image(self, recipient_number: str, image_path: str, caption: str = None):
        """Send image through WhatsApp"""
        
        if not os.path.exists(image_path):
            return False, {"error": f"File not found: {image_path}"}
        
        print(f"\n📸 Sending WhatsApp Image:")
        print(f"   Recipient: {recipient_number}")
        print(f"   Image: {Path(image_path).name}")
        if caption:
            print(f"   Caption: {caption}")
        
        form_data = {
            'authkey': self.auth_key,
            'integrated_number': self.integrated_number,
            'content_type': 'image',
            'payload': json.dumps({
                'messaging_product': 'whatsapp',
                'type': 'image',
                'image': {
                    'caption': caption or '',
                },
                'to': [recipient_number]
            })
        }
        
        file_name = Path(image_path).name
        
        with open(image_path, 'rb') as f:
            files = {
                'image': (file_name, f, 'image/jpeg')
            }
            
            status_code, response = self._make_request(
                self.CONTROL_URL,
                "POST",
                "api/v5/whatsapp/whatsapp-outbound-message/media/",
                data=form_data,
                files=files
            )
        
        success = status_code in [200, 201]
        
        if success:
            print(f"✅ Image sent successfully!")
        else:
            print(f"❌ Failed to send image!")
            print(f"   Status: {status_code}")
            print(f"   Response: {response}")
        
        return success, response
    
    def create_test_pdf(self, filename: str = "test_document.pdf"):
        """Create a simple test PDF file"""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import inch
        except ImportError:
            print("❌ reportlab not installed. Installing...")
            os.system("pip install reportlab")
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import inch
        
        # Create PDF
        pdf_path = filename
        c = canvas.Canvas(pdf_path, pagesize=letter)
        
        # Add content
        c.setFont("Helvetica-Bold", 24)
        c.drawString(1*inch, 10*inch, "Test WhatsApp Document")
        
        c.setFont("Helvetica", 12)
        c.drawString(1*inch, 9.5*inch, "This is a test PDF file sent via WhatsApp")
        c.drawString(1*inch, 9*inch, f"Sent to: 918281740483")
        
        from datetime import datetime
        c.drawString(1*inch, 8.5*inch, f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        c.setFont("Helvetica", 10)
        c.drawString(1*inch, 7.5*inch, "This document was generated by Django WhatsApp test script")
        
        # Add some sample content
        y_position = 7*inch
        sample_text = [
            "Sample Content:",
            "• Test line 1",
            "• Test line 2",
            "• Test line 3",
            "",
            "This PDF demonstrates file sending capability through WhatsApp"
        ]
        
        for line in sample_text:
            c.drawString(1*inch, y_position, line)
            y_position -= 0.3*inch
        
        c.save()
        
        print(f"✅ Test PDF created: {pdf_path}")
        return pdf_path


def main():
    """Main test function"""
    
    print("=" * 60)
    print("WhatsApp File Send Test Script")
    print("=" * 60)
    
    try:
        service = WhatsAppFileService()
        print(f"\n✅ Service initialized")
        print(f"   Auth Key: {service.auth_key[:10]}***")
        print(f"   Integrated Number: {service.integrated_number}")
        
    except Exception as e:
        print(f"❌ Failed to initialize service: {e}")
        return
    
    # Test 1: Create and send test PDF
    print("\n" + "=" * 60)
    print("TEST 1: Create and Send Test PDF")
    print("=" * 60)
    
    try:
        # Create test PDF
        pdf_file = "test_document.pdf"
        service.create_test_pdf(pdf_file)
        
        # Send it
        success, response = service.send_document(
            recipient_number="918281740483",
            file_path=pdf_file,
            caption="Test PDF from Django Script"
        )
        
        if success:
            print("\n✅ TEST 1 PASSED")
        else:
            print("\n❌ TEST 1 FAILED")
            print(f"   Error: {response}")
    
    except Exception as e:
        print(f"❌ TEST 1 ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Send existing file (if available)
    print("\n" + "=" * 60)
    print("TEST 2: Send Existing File")
    print("=" * 60)
    
    # Look for any PDF in current directory
    pdf_files = list(Path('.').glob('*.pdf'))
    if pdf_files and str(pdf_files[0]) != 'test_document.pdf':
        try:
            success, response = service.send_document(
                recipient_number="918281740483",
                file_path=str(pdf_files[0]),
                caption=f"Sending: {pdf_files[0].name}"
            )
            
            if success:
                print("\n✅ TEST 2 PASSED")
            else:
                print("\n❌ TEST 2 FAILED")
        except Exception as e:
            print(f"❌ TEST 2 ERROR: {e}")
    else:
        print("⏭️  Skipped (no additional PDF files found)")
    
    # Test 3: Verify recipient number format
    print("\n" + "=" * 60)
    print("TEST 3: Phone Number Validation")
    print("=" * 60)
    
    phone_numbers = [
        "918281740483",      # Valid: Indian number with country code
        "+918281740483",     # Valid: With + prefix
        "91-8281-740483",    # Invalid: With dashes
        "8281740483",        # Invalid: Without country code
    ]
    
    for phone in phone_numbers:
        # Basic validation
        digits_only = ''.join(filter(str.isdigit, phone))
        is_valid = len(digits_only) >= 10
        status = "✅" if is_valid else "❌"
        print(f"{status} {phone:20} → {digits_only}")
    
    print("\n" + "=" * 60)
    print("Tests Complete!")
    print("=" * 60)
    print("\nNotes:")
    print("• Make sure MSG91_AUTH_KEY is set in .env")
    print("• Make sure MSG91_INTEGRATED_NUMBER is set in .env")
    print("• Phone numbers should include country code (e.g., 918281740483)")
    print("• File size limit is 100MB")
    print("• Supported file types: PDF, Word, Excel, Images, Video, Audio")


if __name__ == "__main__":
    main()
