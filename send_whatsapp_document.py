#!/usr/bin/env python
"""
Practical Example: Send PDF file via WhatsApp using MSG91 Templates

This script demonstrates a real-world scenario:
- You have a PDF file to send
- You need to send it to a recipient via WhatsApp
- MSG91 handles delivery

Setup:
1. Create a WhatsApp template in MSG91 admin called "pdf_document"
   - Header: Document
   - Body: "Hi {{1}}, here's your {{2}}"
   
2. Host your PDF at a public HTTPS URL (e.g., AWS S3, Google Cloud Storage)

3. Run this script with the file URL and recipient number
"""

import os
import sys
import json
import requests
from pathlib import Path
from typing import Tuple

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from django.conf import settings


class WhatsAppFileService:
    """Service to send files via WhatsApp templates"""
    
    API_URL = "https://api.msg91.com/api/v5/whatsapp/whatsapp-outbound-message/bulk/"
    
    def __init__(self):
        self.auth_key = os.environ.get('MSG91_AUTH_KEY') or settings.MSG91_AUTH_KEY
        self.integrated_number = os.environ.get('MSG91_INTEGRATED_NUMBER', '')
        
        if not self.auth_key:
            raise ValueError("MSG91_AUTH_KEY not configured")
        if not self.integrated_number:
            self.integrated_number = settings.MSG91_INTEGRATED_NUMBER
    
    def send_document(
        self,
        template_name: str,
        recipient_number: str,
        document_url: str,
        document_name: str = "Document",
        recipient_name: str = "User"
    ) -> Tuple[bool, dict]:
        """
        Send a document via WhatsApp template
        
        Args:
            template_name: WhatsApp template name (must be created in MSG91 admin)
            recipient_number: Phone number with country code (e.g., 918281740483)
            document_url: Public HTTPS URL to the document
            document_name: Name of document for display
            recipient_name: Name of recipient for personalization
        """
        
        # Clean phone number
        recipient_number = str(recipient_number).replace('-', '').replace(' ', '').replace('+', '')
        
        print(f"\n📄 Sending Document via WhatsApp")
        print(f"   Template: {template_name}")
        print(f"   Recipient: {recipient_name} ({recipient_number})")
        print(f"   Document: {document_name}")
        print(f"   URL: {document_url}")
        
        # Build API payload
        payload = {
            "integrated_number": self.integrated_number,
            "content_type": "template",
            "payload": {
                "messaging_product": "whatsapp",
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {
                        "code": "en",
                        "policy": "deterministic"
                    },
                    "to_and_components": [
                        {
                            "to": [recipient_number],
                            "components": {
                                "header_1": {
                                    "link": document_url
                                },
                                "body_1": {
                                    "1": recipient_name,
                                    "2": document_name
                                }
                            }
                        }
                    ]
                }
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
            
            try:
                result = response.json() if response.text else {}
            except:
                result = {"raw": response.text}
            
            success = response.status_code in [200, 201]
            
            if success:
                print(f"✅ Success! (Status: {response.status_code})")
                if isinstance(result, dict):
                    msg_id = result.get('data', {})
                    if isinstance(msg_id, dict):
                        msg_id = msg_id.get('id', 'N/A')
                    print(f"   Message ID: {msg_id}")
                return True, result
            else:
                print(f"❌ Failed! (Status: {response.status_code})")
                if isinstance(result, dict):
                    error_msg = result.get('errors') or result.get('error') or str(result)
                else:
                    error_msg = str(result)
                print(f"   Error: {error_msg}")
                return False, result
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return False, {"error": str(e)}


def main():
    """Demo script"""
    
    print("=" * 70)
    print("WhatsApp File Send - Practical Example")
    print("=" * 70)
    
    print("""
PREREQUISITES:
1. MSG91 account with WhatsApp integration enabled
2. WhatsApp template created in MSG91 admin (see below)
3. PDF file hosted at public HTTPS URL

STEP 1: Create WhatsApp Template in MSG91
=========================================
1. Go to MSG91 Dashboard > WhatsApp > Templates
2. Click "Create New Template"
3. Fill in:
   - Template Name: "pdf_document"
   - Category: Select Document
   - Header: Document (fixed)
   - Body: "Hi {{1}}, here's your {{2}}"
   - Language: English
4. Click Create
5. Wait for approval (usually quick)

STEP 2: Host PDF at Public URL
==============================
Options:
a) AWS S3:        https://mybucket.s3.amazonaws.com/report.pdf
b) Google Cloud:  https://storage.googleapis.com/mybucket/report.pdf
c) Cloudinary:    https://res.cloudinary.com/user/image/upload/report.pdf
d) Your Server:   https://yourdomain.com/files/report.pdf

STEP 3: Send Document (shown below)
==================================
""")
    
    print("\n" + "=" * 70)
    print("TEST: Sending Real Document")
    print("=" * 70)
    
    try:
        service = WhatsAppFileService()
        
        # Mask auth key for display
        masked_key = service.auth_key[:9] + "***"
        print(f"\n✅ Service initialized")
        print(f"   Auth Key: {masked_key}")
        print(f"   Integrated Number: {service.integrated_number}")
        
        # Example: Send a real document
        print("\n" + "-" * 70)
        print("Scenario: Sending Invoice to Customer")
        print("-" * 70)
        
        success, response = service.send_document(
            template_name="pdf_document",  # Must exist in MSG91 admin
            recipient_number="918281740483",
            document_url="https://www.w3.org/WAI/WCAG21/Techniques/pdf/img/table1.pdf",
            document_name="Invoice #2024-001",
            recipient_name="Ahmed"
        )
        
        if success:
            print("\n✅ Document send initiated successfully!")
            print("   WhatsApp message with PDF will be delivered to the recipient")
        else:
            print("\n⚠️  Send failed")
            if "template" in str(response).lower():
                print("   Hint: Template 'pdf_document' not found")
                print("   Action: Create this template in MSG91 admin first")
            print(f"   Full response: {response}")
        
        # Show more examples
        print("\n" + "-" * 70)
        print("More Examples")
        print("-" * 70)
        
        examples = [
            {
                "template": "receipt_document",
                "name": "Receipt #2024-100",
                "recipient": "Fatima",
                "phone": "971521111111"
            },
            {
                "template": "report_document",
                "name": "Monthly Report Jan 2024",
                "recipient": "Ahmad",
                "phone": "971502222222"
            },
            {
                "template": "contract_document",
                "name": "Service Agreement",
                "recipient": "Sara",
                "phone": "971503333333"
            }
        ]
        
        print("\nYou can send to multiple recipients:")
        for example in examples:
            print(f"""
# Send to {example['recipient']}
service.send_document(
    template_name="{example['template']}",
    recipient_number="{example['phone']}",
    document_url="https://storage.example.com/document.pdf",
    document_name="{example['name']}",
    recipient_name="{example['recipient']}"
)""")
        
        print("\n" + "=" * 70)
        print("Summary")
        print("=" * 70)
        
        print("""
✅ WORKING:
  - Template-based WhatsApp messaging
  - Media delivery via URL
  - Personalized messages with recipient name
  - Automatic WhatsApp delivery

📋 NEXT STEPS:
  1. Create 'pdf_document' template in MSG91 admin
  2. Get your PDF URL (from S3, Cloudinary, or your server)
  3. Use script to send: service.send_document(...)
  4. Recipient receives PDF in WhatsApp chat

💡 TIPS:
  - Test with small files first
  - Use HTTPS URLs only
  - Keep document names under 100 characters
  - Check MSG91 delivery reports for confirmation

For more details, see: WHATSAPP_TEMPLATE_SEND_GUIDE.md
""")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Check MSG91_AUTH_KEY in .env")
        print("2. Check MSG91_INTEGRATED_NUMBER in .env")
        print("3. Verify template exists in MSG91 admin")
        return 1


if __name__ == "__main__":
    sys.exit(main())
