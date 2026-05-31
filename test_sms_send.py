#!/usr/bin/env python3
"""
Test script: Send a single SMS via MSG91 Flow API.
Usage: python test_sms_send.py
"""

import requests
import json

AUTHKEY     = "499105AowuvQcFIY0Y69e6226dP1"
TEMPLATE_ID = "69f76af5f1d7dd63ff0419c2"
MOBILE      = "918281740483"   # recipient number (no +)
OTP_VALUE   = "123456"         # sample OTP / VAR1 value

payload = {
    "template_id": TEMPLATE_ID,
    "short_url": "0",
    "recipients": [
        {
            "mobiles": MOBILE,
            "VAR1": OTP_VALUE,
        }
    ]
}

headers = {
    "accept": "application/json",
    "authkey": AUTHKEY,
    "content-type": "application/json",
}

print("=" * 60)
print("MSG91 SMS Test")
print("=" * 60)
print(f"To      : {MOBILE}")
print(f"Template: {TEMPLATE_ID}")
print(f"VAR1    : {OTP_VALUE}")
print("-" * 60)

response = requests.post(
    "https://control.msg91.com/api/v5/flow",
    headers=headers,
    data=json.dumps(payload),
)

print(f"HTTP Status : {response.status_code}")
try:
    print(f"Response    : {json.dumps(response.json(), indent=2)}")
except Exception:
    print(f"Response    : {response.text}")

print("=" * 60)
