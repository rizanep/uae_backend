"""
Test FCM push notification with a specific token.
Run: python manage.py shell < test_fcm_push.py
"""
import django
django.setup()

from Notifications.push_service import send_push_to_tokens

token = "c0Mv9-yCQrKZkCj0y6tU5L:APA91bG3r16LBhpk2zVpJhaSRJyx97kJiWyccIHYEChMyeq5-JgD_DIZpvAyP3qDWd8a0BanLLFbtKGF7irL6uV9A1MzCxriJ20PZWvKYIv523Hn7TaTuUE"

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
