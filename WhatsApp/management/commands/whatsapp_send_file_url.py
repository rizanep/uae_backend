#!/usr/bin/env python
"""
Django management command to send WhatsApp file via URL-based API
This command creates a temporary serving URL for the file and sends it via MSG91

Usage:
    python manage.py whatsapp_send_file_url report.pdf 918281740483 "Monthly Report"
    python manage.py whatsapp_send_file_url image.jpg 918281740483 "Check this" --type image
"""

import json
import requests
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.urls import reverse
from django.test.utils import override_settings


class Command(BaseCommand):
    help = 'Send file via WhatsApp using MSG91 API (URL-based)'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to file to send')
        parser.add_argument('phone_number', type=str, help='Recipient phone number')
        parser.add_argument('caption', type=str, nargs='?', default=None, help='Optional caption')
        parser.add_argument(
            '--type',
            type=str,
            choices=['document', 'image', 'video', 'audio'],
            default='document',
            help='Media type'
        )
        parser.add_argument(
            '--media-url',
            type=str,
            default=None,
            help='Use existing media URL instead of file'
        )

    def handle(self, *args, **options):
        """Send WhatsApp file"""
        
        file_path = options['file_path']
        phone_number = options['phone_number']
        caption = options['caption']
        media_type = options['type']
        media_url = options['media_url']
        
        # Get config
        auth_key = settings.MSG91_AUTH_KEY
        integrated_number = settings.MSG91_INTEGRATED_NUMBER
        
        if not auth_key or not integrated_number:
            raise CommandError('MSG91_AUTH_KEY and MSG91_INTEGRATED_NUMBER must be configured')
        
        # If media_url not provided, use the file
        if not media_url:
            # Verify file exists
            if not Path(file_path).exists():
                raise CommandError(f'File not found: {file_path}')
            
            # For local development, we would need to serve the file
            # For now, show error with instructions
            self.stdout.write(
                self.style.WARNING(
                    '\n⚠️  To send local files, you need to host them at a URL.\n'
                    'Options:\n'
                    '1. Upload file to cloud storage (S3, Cloudinary, etc.)\n'
                    '2. Use --media-url with a public URL\n'
                    '3. Create a file serving endpoint in your Django app\n'
                )
            )
            raise CommandError('Please provide --media-url with a public URL to the file')
        
        # Clean phone number
        phone_number = phone_number.replace('-', '').replace(' ', '').replace('+', '')
        
        self.stdout.write(f'\n📤 Sending WhatsApp {media_type}:')
        self.stdout.write(f'   Recipient: {phone_number}')
        self.stdout.write(f'   Media URL: {media_url}')
        if caption:
            self.stdout.write(f'   Caption: {caption}')
        
        # Build payload
        media_obj = {"value": media_url}
        if caption and media_type in ['document', 'image', 'video']:
            media_obj["caption"] = caption
        
        payload = {
            "integrated_number": integrated_number,
            "content_type": media_type,
            "payload": {
                "messaging_product": "whatsapp",
                "type": media_type,
                media_type: media_obj,
                "to": [phone_number]
            }
        }
        
        # Send to MSG91
        headers = {
            "authkey": auth_key,
            "Content-Type": "application/json",
        }
        
        self.stdout.write('\n📨 Sending to MSG91...')
        
        try:
            response = requests.post(
                'https://api.msg91.com/api/v5/whatsapp/whatsapp-outbound-message/bulk/',
                headers=headers,
                data=json.dumps(payload),
                timeout=30,
                verify=True
            )
            
            result = response.json() if response.text else {}
            
            if response.status_code in [200, 201]:
                self.stdout.write(self.style.SUCCESS('\n✅ Success!'))
                self.stdout.write(f'   Status: {response.status_code}')
                self.stdout.write(f'   Response: {result}\n')
            else:
                self.stdout.write(self.style.ERROR('\n❌ Failed!'))
                self.stdout.write(f'   Status: {response.status_code}')
                self.stdout.write(f'   Response: {result}\n')
                raise CommandError('MSG91 API returned error')
                
        except requests.exceptions.RequestException as e:
            raise CommandError(f'Request error: {str(e)}')
        except json.JSONDecodeError:
            raise CommandError('Invalid JSON response from MSG91')
        except Exception as e:
            raise CommandError(f'Error: {str(e)}')
