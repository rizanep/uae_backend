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

token = "fxuNlf3mQGGjv4exwfR0pu:APA91bEAuN1jUBvrJmmhKD85onKjgz0mA2b6AjeeOLlRrBfFwTmfl0cWP7rH3gURwKxOZdXUP6LUbq8gMdGDEx609JS-hr2VshR9J_TJyeq4kFlIVC_NDFY"

print("Sending test push notification...")
result = send_push_to_tokens(
    tokens=[token],
    title="Simak Fresh Test 🐟",
    body="This is a test push notification from Simak Fresh!",
    data={"type": "test", "action": "open_home"},
)

print(f"Result: {result}")
if result["success_count"] > 0:
    print("SUCCESS — Notification delivered!")
else:
    print("FAILED — Check the token or Firebase config.")
