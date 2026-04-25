#!/usr/bin/env python
"""
Send WhatsApp files via MSG91 using approved templates
This is the proper approach - MSG91 WhatsApp requires templates for all messaging

There are two approaches:

Approach 1: Create template in MSG91 admin with media header
- Create WhatsApp template in MSG91 panel with document/image/video header
- Use template name to send messages
- Simplest once templates are set up

Approach 2: Use Dynamic WhatsApp Message API (if available)
- Some providers support dynamic messages without templates
- Check MSG91 documentation for latest endpoints

This script demonstrates Approach 1 (template-based)
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


class MSG91WhatsAppTemplateService:
    """
    Send WhatsApp messages using templates
    Templates allow media (images, documents, videos) with proper WhatsApp compliance
    """
    
    API_URL = "https://api.msg91.com/api/v5/whatsapp/whatsapp-outbound-message/bulk/"
    
    def __init__(self):
        self.auth_key = os.environ.get('MSG91_AUTH_KEY') or settings.MSG91_AUTH_KEY
        self.integrated_number = os.environ.get('MSG91_INTEGRATED_NUMBER', '')
        
        if not self.auth_key:
            raise ValueError("MSG91_AUTH_KEY not configured")
        if not self.integrated_number:
            self.integrated_number = settings.MSG91_INTEGRATED_NUMBER
    
    def send_via_template(
        self,
        template_name: str,
        recipient_number: str,
        template_params: dict = None,
        header_params: dict = None
    ) -> Tuple[bool, dict]:
        """
        Send WhatsApp message using a template
        
        Args:
            template_name: Name of the WhatsApp template created in MSG91 admin
            recipient_number: Phone number with country code
            template_params: Body parameters for the template {variable_name: value}
            header_params: Header parameters (for media templates)
                         Example: {"link": "https://example.com/document.pdf"}
        
        Returns:
            Tuple of (success, response_data)
            
        Example:
            service.send_via_template(
                "order_receipt",
                "918281740483",
                {"order_id": "12345", "total": "$99.99"},
                {"link": "https://s3.example.com/receipt.pdf"}
            )
        """
        
        # Clean phone number
        recipient_number = str(recipient_number).replace('-', '').replace(' ', '').replace('+', '')
        
        print(f"\n📤 Sending WhatsApp via Template:")
        print(f"   Template: {template_name}")
        print(f"   Recipient: {recipient_number}")
        if template_params:
            print(f"   Parameters: {template_params}")
        if header_params:
            print(f"   Header: {header_params}")
        
        # Build payload
        components = {}
        
        # Header component (for media)
        if header_params:
            components["header_1"] = header_params
        
        # Body component (for text parameters)
        if template_params:
            components["body_1"] = template_params
        
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
                    "namespace": None,
                    "to_and_components": [
                        {
                            "to": [recipient_number],
                            "components": components
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
            
            result = response.json() if response.text else {}
            
            success = response.status_code in [200, 201]
            
            if success:
                print(f"✅ Success! (Status: {response.status_code})")
                return True, result
            else:
                print(f"❌ Failed! (Status: {response.status_code})")
                print(f"   Response: {result}")
                return False, result
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return False, {"error": str(e)}


def main():
    """Demo showing template-based approach"""
    
    print("=" * 70)
    print("WhatsApp File Send via Templates (MSG91)")
    print("=" * 70)
    
    print("""
MSG91 WhatsApp API requires using templates for all messaging.

SETUP REQUIRED (in MSG91 Admin Panel):
1. Go to WhatsApp > Templates
2. Create a template with media in the header:
   - Name: "document_send" or similar
   - Header: Document/Image/Video
   - Body: Optional text with variables like "Hi {{1}}, here's your document"
   
3. Get the template name from MSG91 admin

Then use this script to send via the template.
""")
    
    print("\n" + "=" * 70)
    print("TEST: Sending via Template")
    print("=" * 70)
    
    try:
        service = MSG91WhatsAppTemplateService()
        
        # Mask auth key for display
        masked_key = service.auth_key[:9] + "***" if len(service.auth_key) > 9 else service.auth_key
        print(f"\n✅ Service initialized")
        print(f"   Auth Key: {masked_key}")
        print(f"   Integrated Number: {service.integrated_number}")
        
        # Example 1: Template without media
        print("\n" + "-" * 70)
        print("Example 1: Send template message")
        print("-" * 70)
        
        success, response = service.send_via_template(
            "hello_world",  # Template must exist in MSG91
            "918281740483",
            template_params={"name": "Django"},
            header_params=None
        )
        
        if success:
            print("✅ Message sent!")
        else:
            print("⚠️  Check template name and MSG91 credentials")
        
        # Example 2: Template with media header (document)
        print("\n" + "-" * 70)
        print("Example 2: Send template with document")
        print("-" * 70)
        print("""
To send a document:
1. Create template "document_send" in MSG91 admin with Document header
2. Call:
   service.send_via_template(
       "document_send",
       "918281740483",
       {"document_name": "Report.pdf", "date": "2024-01-01"},
       {"link": "https://s3.example.com/report.pdf"}
   )
""")
        
        # Example 3: Template with image
        print("\n" + "-" * 70)
        print("Example 3: Send template with image")
        print("-" * 70)
        print("""
To send an image:
1. Create template "image_send" in MSG91 admin with Image header
2. Call:
   service.send_via_template(
       "image_send",
       "918281740483",
       {"title": "Product Image"},
       {"link": "https://cdn.example.com/product.jpg"}
   )
""")
        
        print("\n" + "=" * 70)
        print("✅ Template Setup Complete")
        print("=" * 70)
        
        print("""
NEXT STEPS:
1. Go to MSG91 admin panel
2. Create WhatsApp templates with media headers
3. Use template names in this script

For detailed template setup, see: WHATSAPP_TEMPLATE_SETUP.md
""")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
