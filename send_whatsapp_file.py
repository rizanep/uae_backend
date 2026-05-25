#!/usr/bin/env python
"""
Simple WhatsApp File Send Example
Usage: python send_whatsapp_file.py <file_path> <phone_number> [caption]
Example: python send_whatsapp_file.py report.pdf 918281740483 "Monthly Report"
"""

import os
import sys
import json
import requests
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from django.conf import settings


def send_whatsapp_file(file_path: str, phone_number: str, caption: str = None):
    """
    Send a file through WhatsApp
    
    Args:
        file_path: Path to file (PDF, Image, Video, etc.)
        phone_number: Recipient number with country code (e.g., 918281740483)
        caption: Optional caption for the file
    
    Returns:
        Dict with success status and message_id
    """
    
    # Get credentials
    auth_key = os.environ.get('MSG91_AUTH_KEY') or getattr(settings, 'MSG91_AUTH_KEY', None)
    integrated_number = os.environ.get('MSG91_INTEGRATED_NUMBER', '918281740483')
    
    if not auth_key:
        return {"success": False, "error": "MSG91_AUTH_KEY not configured"}
    
    # Verify file
    if not os.path.exists(file_path):
        return {"success": False, "error": f"File not found: {file_path}"}
    
    file_size = os.path.getsize(file_path)
    if file_size > 100 * 1024 * 1024:  # 100MB limit
        return {"success": False, "error": "File exceeds 100MB limit"}
    
    # Get file info
    file_name = Path(file_path).name
    file_ext = Path(file_path).suffix.lower()
    
    # MIME types
    mime_types = {
        '.pdf': 'application/pdf',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.mp4': 'video/mp4',
        '.mp3': 'audio/mpeg',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xls': 'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.txt': 'text/plain',
    }
    
    mime_type = mime_types.get(file_ext, 'application/octet-stream')
    
    # Determine content type and endpoint
    # All media types use the unified media endpoint
    if file_ext in ['.jpg', '.jpeg', '.png', '.gif']:
        content_type = 'image'
        endpoint = 'api/v5/whatsapp/whatsapp-outbound-message/media/'
        field_name = 'media'
    elif file_ext in ['.mp4']:
        content_type = 'video'
        endpoint = 'api/v5/whatsapp/whatsapp-outbound-message/media/'
        field_name = 'media'
    elif file_ext in ['.mp3', '.wav']:
        content_type = 'audio'
        endpoint = 'api/v5/whatsapp/whatsapp-outbound-message/media/'
        field_name = 'media'
    else:
        content_type = 'document'
        endpoint = 'api/v5/whatsapp/whatsapp-outbound-message/media/'
        field_name = 'media'
    
    # Prepare payload
    form_data = {
        'authkey': auth_key,
        'integrated_number': integrated_number,
        'content_type': content_type,
        'payload': json.dumps({
            'messaging_product': 'whatsapp',
            'type': content_type,
            content_type: {
                'caption': caption or file_name,
            },
            'to': [phone_number]
        })
    }
    
    # Send file
    try:
        url = f"https://control.msg91.com/{endpoint}"
        
        with open(file_path, 'rb') as f:
            files = {
                field_name: (file_name, f, mime_type)
            }
            
            headers = {'authkey': auth_key}
            response = requests.post(url, headers=headers, data=form_data, files=files, timeout=30, verify=True)
        
        result = response.json() if response.text else {}
        success = response.status_code in [200, 201]
        
        return {
            "success": success,
            "status_code": response.status_code,
            "message_id": result.get('message_id') or result.get('data', {}).get('message_id'),
            "response": result
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    """CLI usage"""
    
    if len(sys.argv) < 3:
        print("Usage: python send_whatsapp_file.py <file_path> <phone_number> [caption]")
        print("\nExample:")
        print("  python send_whatsapp_file.py report.pdf 918281740483 'Monthly Report'")
        print("  python send_whatsapp_file.py image.jpg 918281740483 'Check this out'")
        print("\nSupported files:")
        print("  • Documents: PDF, DOC, DOCX, XLS, XLSX, TXT")
        print("  • Images: JPG, JPEG, PNG, GIF")
        print("  • Video: MP4 (max 100MB)")
        print("  • Audio: MP3, WAV")
        return
    
    file_path = sys.argv[1]
    phone_number = sys.argv[2]
    caption = sys.argv[3] if len(sys.argv) > 3 else None
    
    print(f"\n📤 Sending WhatsApp File")
    print(f"   File: {file_path}")
    print(f"   To: {phone_number}")
    if caption:
        print(f"   Caption: {caption}")
    print()
    
    result = send_whatsapp_file(file_path, phone_number, caption)
    
    if result['success']:
        print(f"✅ File sent successfully!")
        print(f"   Message ID: {result.get('message_id', 'N/A')}")
    else:
        print(f"❌ Failed to send file!")
        print(f"   Error: {result.get('error', result.get('response', {}))}")


if __name__ == "__main__":
    main()
