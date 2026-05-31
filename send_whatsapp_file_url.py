#!/usr/bin/env python
"""
Send WhatsApp file via MSG91 API using URL-based media
This is the correct approach - MSG91 expects media URLs, not direct file uploads

Usage: 
    # Send file via direct URL
    python send_whatsapp_file_url.py https://example.com/document.pdf 918281740483 "My Document"
    
    # Or send file from local path (will create a temporary serve)
    python send_whatsapp_file_url.py /path/to/file.pdf 918281740483 "My Document"
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


class MSG91WhatsAppFileService:
    """
    Send files through WhatsApp via MSG91 using URL-based media
    MSG91 doesn't support direct file uploads - it requires a URL to the media
    """
    
    API_URL = "https://api.msg91.com/api/v5/whatsapp/whatsapp-outbound-message/bulk/"
    
    def __init__(self):
        self.auth_key = os.environ.get('MSG91_AUTH_KEY') or settings.MSG91_AUTH_KEY
        self.integrated_number = os.environ.get('MSG91_INTEGRATED_NUMBER', '')
        
        if not self.auth_key:
            raise ValueError("MSG91_AUTH_KEY not configured")
        if not self.integrated_number:
            self.integrated_number = settings.MSG91_INTEGRATED_NUMBER
    
    def _make_request(self, payload_dict: dict) -> Tuple[int, dict]:
        """Make HTTPS request to MSG91"""
        headers = {
            "authkey": self.auth_key,
            "Content-Type": "application/json",
        }
        
        payload = json.dumps(payload_dict)
        
        try:
            response = requests.post(
                self.API_URL,
                headers=headers,
                data=payload,
                timeout=30,
                verify=True
            )
            
            try:
                return response.status_code, response.json()
            except:
                return response.status_code, {"raw": response.text}
                
        except requests.exceptions.RequestException as e:
            return 0, {"error": str(e)}
    
    def send_file_via_url(
        self,
        media_url: str,
        recipient_number: str,
        media_type: str = "document",
        caption: str = None
    ) -> Tuple[bool, dict]:
        """
        Send file via WhatsApp using a media URL
        
        Args:
            media_url: Full URL to the media file (e.g., https://example.com/file.pdf)
            recipient_number: Phone number with country code
            media_type: Type of media - 'document', 'image', 'video', 'audio'
            caption: Optional caption for the media
        
        Returns:
            Tuple of (success, response_data)
        """
        
        # Validate inputs
        if not media_url.startswith(('http://', 'https://')):
            return False, {"error": "media_url must be a valid HTTP/HTTPS URL"}
        
        if media_type not in ['document', 'image', 'video', 'audio']:
            return False, {"error": f"Invalid media_type: {media_type}"}
        
        # Clean recipient number (remove formatting)
        recipient_number = recipient_number.replace('-', '').replace(' ', '').replace('+', '')
        
        print(f"\n📤 Sending WhatsApp {media_type.capitalize()}:")
        print(f"   Recipient: {recipient_number}")
        print(f"   Media URL: {media_url}")
        if caption:
            print(f"   Caption: {caption}")
        
        # Build payload
        media_obj = {
            "value": media_url
        }
        
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
        
        print(f"\n📨 Sending to MSG91...")
        status_code, response = self._make_request(payload)
        
        success = status_code in [200, 201]
        
        if success:
            print(f"✅ Success! (Status: {status_code})")
        else:
            print(f"❌ Failed! (Status: {status_code})")
            print(f"   Response: {response}")
        
        return success, response


def main():
    """Main entry point"""
    
    if len(sys.argv) < 3:
        print("❌ Missing arguments!")
        print("\nUsage:")
        print("  python send_whatsapp_file_url.py <media_url> <phone_number> [caption] [type]")
        print("\nExamples:")
        print("  python send_whatsapp_file_url.py https://example.com/doc.pdf 918281740483 'Report'")
        print("  python send_whatsapp_file_url.py https://example.com/photo.jpg 918281740483 'Check this' image")
        print("\nSupported media types: document, image, video, audio")
        return 1
    
    media_url = sys.argv[1]
    phone_number = sys.argv[2]
    caption = sys.argv[3] if len(sys.argv) > 3 else None
    media_type = sys.argv[4] if len(sys.argv) > 4 else "document"
    
    try:
        service = MSG91WhatsAppFileService()
        success, response = service.send_file_via_url(
            media_url,
            phone_number,
            media_type,
            caption
        )
        
        if not success:
            print(f"\nError response: {response}")
            return 1
        
        print("\n✅ File sent successfully!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
