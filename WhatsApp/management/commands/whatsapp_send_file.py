"""
Django management command to send WhatsApp files
Usage: python manage.py whatsapp_send_file <file_path> <phone_number> [--caption "caption text"]
Example: python manage.py whatsapp_send_file report.pdf 918281740483 --caption "Monthly Report"
"""

import os
import json
import requests
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = 'Send files through WhatsApp'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to file to send')
        parser.add_argument('phone_number', type=str, help='Recipient phone number (with country code)')
        parser.add_argument('--caption', type=str, help='Optional caption for the file')

    def handle(self, *args, **options):
        file_path = options['file_path']
        phone_number = options['phone_number']
        caption = options.get('caption')
        
        # Get credentials
        auth_key = os.environ.get('MSG91_AUTH_KEY') or getattr(settings, 'MSG91_AUTH_KEY', None)
        integrated_number = os.environ.get('MSG91_INTEGRATED_NUMBER', '918281740483')
        
        if not auth_key:
            raise CommandError("MSG91_AUTH_KEY not configured in environment or settings")
        
        # Validate file
        if not os.path.exists(file_path):
            raise CommandError(f"File not found: {file_path}")
        
        file_size = os.path.getsize(file_path)
        if file_size > 100 * 1024 * 1024:  # 100MB limit
            raise CommandError(f"File size {file_size / 1024 / 1024:.2f}MB exceeds 100MB limit")
        
        # Get file info
        file_name = Path(file_path).name
        file_ext = Path(file_path).suffix.lower()
        
        self.stdout.write(self.style.WARNING(f"\n📤 Sending WhatsApp File"))
        self.stdout.write(f"   Recipient: {phone_number}")
        self.stdout.write(f"   File: {file_name}")
        self.stdout.write(f"   Size: {file_size / 1024:.2f} KB")
        if caption:
            self.stdout.write(f"   Caption: {caption}")
        self.stdout.write("")
        
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
            self.stdout.write("Sending to MSG91...")
            
            url = f"https://control.msg91.com/{endpoint}"
            
            with open(file_path, 'rb') as f:
                files = {
                    field_name: (file_name, f, mime_type)
                }
                
                headers = {'authkey': auth_key}
                response = requests.post(url, headers=headers, data=form_data, files=files, timeout=30, verify=True)
            
            result = response.json() if response.text else {}
            success = response.status_code in [200, 201]
            
            if success:
                message_id = result.get('message_id') or result.get('data', {}).get('message_id', 'N/A')
                self.stdout.write(self.style.SUCCESS(f"\n✅ File sent successfully!"))
                self.stdout.write(f"   Message ID: {message_id}")
                self.stdout.write(f"   Status Code: {response.status_code}\n")
            else:
                self.stdout.write(self.style.ERROR(f"\n❌ Failed to send file!"))
                self.stdout.write(f"   Status Code: {response.status_code}")
                self.stdout.write(f"   Response: {result}\n")
                raise CommandError("WhatsApp API returned error")
        
        except requests.exceptions.RequestException as e:
            raise CommandError(f"Request error: {str(e)}")
        except json.JSONDecodeError:
            raise CommandError(f"Invalid JSON response from MSG91")
        except Exception as e:
            raise CommandError(f"Error: {str(e)}")
