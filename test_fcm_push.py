"""
Test FCM push notification with a specific token.
Run: python test_fcm_push.py
"""
import os
import sys
import django

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from Notifications.push_service import send_push_to_tokens

token = "dcGXIRf0dEX7t6oZcLHhGp:APA91bGdW3NOmWxTmNPB2bpO-rCQM62rA9YyoiOqPcTZ1S4J0J4NjiGlO5IDvjbug_7fdlwsql-aF5cxSL7YwHcv4qhX9rGF1zGKZ5tCIJ-nRpdrU2FvPuY"

print("Sending test push notification...")
result = send_push_to_tokens(
    tokens=[token],
    title="simakfresh",
    body="welcome to simakfresh junaaid",
    data={"type": "test", "action": "open_home"},
)

print(f"Result: {result}")
if result["success_count"] > 0:
    print("SUCCESS — Notification delivered!")
else:
    print("FAILED — Check the token or Firebase config.")
