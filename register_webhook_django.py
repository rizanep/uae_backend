#!/usr/bin/env python3
"""
Script to register webhook with Ziina payment gateway.
Run from Django shell: exec(open('register_webhook_django.py').read())
"""

import sys
import os
import json
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.conf import settings

print("=" * 70)
print("ZIINA WEBHOOK REGISTRATION")
print("=" * 70)

# Get configuration from Django settings
ZIINA_API_KEY = settings.ZIINA_API_KEY
ZIINA_WEBHOOK_SECRET = getattr(settings, 'ZIINA_WEBHOOK_SECRET', None)
WEBHOOK_URL = "https://187.77.189.139/api/orders/webhook/ziina/"

print(f"\n✓ API Key: {ZIINA_API_KEY[:20]}...{ZIINA_API_KEY[-10:]}")
print(f"✓ Webhook URL: {WEBHOOK_URL}")
if ZIINA_WEBHOOK_SECRET:
    print(f"✓ Webhook Secret: {ZIINA_WEBHOOK_SECRET[:16]}...{ZIINA_WEBHOOK_SECRET[-8:]}")

# Import requests
try:
    import requests
except ImportError:
    print("\n❌ ERROR: 'requests' module not installed")
    print("Install with: pip install requests")
    sys.exit(1)

# Prepare request
url = "https://api-v2.ziina.com/api/webhook"
headers = {
    "Authorization": f"Bearer {ZIINA_API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

payload = {
    "url": WEBHOOK_URL,
    "secret": ZIINA_WEBHOOK_SECRET
}

print(f"\n📡 Sending request to: {url}")
print(f"📦 Payload:\n{json.dumps(payload, indent=2)}")

try:
    print("\n⏳ Connecting to Ziina API...")
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    
    result = response.json()
    
    if result.get('success'):
        print("\n" + "=" * 70)
        print("✅ WEBHOOK REGISTRATION SUCCESSFUL!")
        print("=" * 70)
        print(f"\nResponse:\n{json.dumps(result, indent=2)}")
        print("\nYour webhook is now registered with Ziina:")
        print(f"  • Endpoint: {WEBHOOK_URL}")
        print(f"  • Event Type: payment_intent.status.updated")
        print(f"  • Signature Verification: Enabled")
        print("\n💡 Tips:")
        print("  1. Ziina will now send payment updates to your webhook")
        print("  2. All events are HMAC-SHA256 signed")
        print("  3. Check WEBHOOK_README.md for testing instructions")
        print("  4. Monitor logs: grep 'Webhook' debug.log")
        sys.exit(0)
    else:
        print("\n❌ WEBHOOK REGISTRATION FAILED")
        print(f"Response:\n{json.dumps(result, indent=2)}")
        print(f"\nError: {result.get('error', 'Unknown error')}")
        sys.exit(1)

except requests.exceptions.HTTPError as e:
    print(f"\n❌ HTTP ERROR {e.response.status_code}")
    try:
        error_detail = e.response.json()
        print(f"Details:\n{json.dumps(error_detail, indent=2)}")
    except:
        print(f"Response: {e.response.text}")
    sys.exit(1)

except requests.exceptions.ConnectionError as e:
    print(f"\n❌ CONNECTION ERROR: {e}")
    print("Please check:")
    print("  • Your internet connection")
    print("  • The Ziina API endpoint is accessible")
    sys.exit(1)

except requests.exceptions.Timeout as e:
    print(f"\n❌ TIMEOUT ERROR: Request timed out after 30 seconds")
    sys.exit(1)

except Exception as e:
    print(f"\n❌ UNEXPECTED ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
