#!/usr/bin/env python
"""
Script to register webhook with Ziina payment gateway.
Run: python register_webhook.py
"""

import os
import json
import requests
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

# Get configuration
ZIINA_API_KEY = os.environ.get('ZIINA_ID')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '').strip('"')
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET')

print("=" * 70)
print("ZIINA WEBHOOK REGISTRATION")
print("=" * 70)

# Validate configuration
if not ZIINA_API_KEY:
    print("❌ ERROR: ZIINA_ID not found in .env file")
    exit(1)

if not WEBHOOK_URL:
    print("❌ ERROR: WEBHOOK_URL not found in .env file")
    exit(1)

if not WEBHOOK_SECRET:
    print("❌ ERROR: WEBHOOK_SECRET not found in .env file")
    exit(1)

print(f"\n✓ API Key: {ZIINA_API_KEY[:20]}...{ZIINA_API_KEY[-10:]}")
print(f"✓ Webhook URL: {WEBHOOK_URL}")
print(f"✓ Webhook Secret: {WEBHOOK_SECRET[:16]}...{WEBHOOK_SECRET[-8:]}")

# Prepare request
url = "https://api-v2.ziina.com/api/webhook"
headers = {
    "Authorization": f"Bearer {ZIINA_API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

payload = {
    "url": WEBHOOK_URL,
    "secret": WEBHOOK_SECRET
}

print(f"\n📡 Sending request to: {url}")
print(f"📦 Payload: {json.dumps(payload, indent=2)}")

try:
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    
    result = response.json()
    
    if result.get('success'):
        print("\n" + "=" * 70)
        print("✅ WEBHOOK REGISTRATION SUCCESSFUL!")
        print("=" * 70)
        print(f"\nResponse: {json.dumps(result, indent=2)}")
        print("\nYour webhook is now registered with Ziina:")
        print(f"  • Endpoint: {WEBHOOK_URL}")
        print(f"  • Event Type: payment_intent.status.updated")
        print(f"  • Signature Verification: Enabled (secret configured)")
        print("\n💡 Tips:")
        print("  1. Ziina will now send payment updates to your webhook")
        print("  2. All events are HMAC-SHA256 signed")
        print("  3. Check WEBHOOK_README.md for testing instructions")
        print("  4. Monitor logs for webhook events: grep 'Webhook' debug.log")
        exit(0)
    else:
        print("\n❌ WEBHOOK REGISTRATION FAILED")
        print(f"Response: {json.dumps(result, indent=2)}")
        exit(1)

except requests.exceptions.HTTPError as e:
    print(f"\n❌ HTTP ERROR: {e.response.status_code}")
    try:
        error_detail = e.response.json()
        print(f"Details: {json.dumps(error_detail, indent=2)}")
    except:
        print(f"Response: {e.response.text}")
    exit(1)

except requests.exceptions.RequestException as e:
    print(f"\n❌ REQUEST ERROR: {e}")
    exit(1)

except Exception as e:
    print(f"\n❌ UNEXPECTED ERROR: {e}")
    exit(1)
