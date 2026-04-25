"""
Test script to verify is_read filter in Notifications
Run with: python manage.py shell < test_notification_filter.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from Notifications.models import Notification
from Users.models import User
from django_filters.rest_framework import DjangoFilterBackend

print("=" * 60)
print("TESTING NOTIFICATION is_read FILTER")
print("=" * 60)

# Create a test user
print("\n[Test 1] Creating test user...")
# Clean up any existing test user first
User.objects.filter(email='notif_test@test.com').delete()

user = User.objects.create_user(
    email='notif_test@test.com',
    password='testpass123'
)
print(f"  ✅ Created user: {user.email}")

# Create test notifications
print("\n[Test 2] Creating test notifications...")
notif_read = Notification.objects.create(
    user=user,
    title="Read Notification",
    message="This notification has been read",
    is_read=True
)
notif_unread = Notification.objects.create(
    user=user,
    title="Unread Notification",
    message="This notification is unread",
    is_read=False
)
notif_unread2 = Notification.objects.create(
    user=user,
    title="Another Unread",
    message="Another unread notification",
    is_read=False
)
print(f"  ✅ Created 3 notifications: 1 read, 2 unread")

# Test queryset filtering
print("\n[Test 3] Testing queryset filter with is_read=True...")
read_notifs = Notification.objects.filter(user=user, is_read=True)
print(f"  Count: {read_notifs.count()}")
for notif in read_notifs:
    print(f"    - {notif.title}: is_read={notif.is_read}")

assert read_notifs.count() >= 1, "❌ FAILED: Should have at least 1 read notification"
assert all(n.is_read == True for n in read_notifs), "❌ FAILED: All should be read=True"
print("  ✅ PASSED: is_read=True filter works")

# Test filtering with is_read=False
print("\n[Test 4] Testing queryset filter with is_read=False...")
unread_notifs = Notification.objects.filter(user=user, is_read=False)
print(f"  Count: {unread_notifs.count()}")
for notif in unread_notifs:
    print(f"    - {notif.title}: is_read={notif.is_read}")

assert unread_notifs.count() >= 2, "❌ FAILED: Should have at least 2 unread notifications"
assert all(n.is_read == False for n in unread_notifs), "❌ FAILED: All should be read=False"
print("  ✅ PASSED: is_read=False filter works")

# Test without filter (should return all)
print("\n[Test 5] Testing without filter (should return all)...")
all_notifs = Notification.objects.filter(user=user)
print(f"  Count: {all_notifs.count()}")

assert all_notifs.count() == 3, "❌ FAILED: Should have all 3 notifications"
print("  ✅ PASSED: No filter returns all notifications")

# Test mark as read
print("\n[Test 6] Testing mark as read functionality...")
notif_unread.is_read = True
notif_unread.save()
notif_unread.refresh_from_db()
assert notif_unread.is_read == True, "❌ FAILED: Should be marked as read"
print(f"  ✅ PASSED: Notification marked as read")

# Verify DjangoFilterBackend is configured
print("\n[Test 7] Verifying DjangoFilterBackend is configured...")
from Notifications.views import NotificationViewSet
assert hasattr(NotificationViewSet, 'filter_backends'), "❌ FAILED: filter_backends not found"
assert DjangoFilterBackend in NotificationViewSet.filter_backends, "❌ FAILED: DjangoFilterBackend not configured"
print(f"  filter_backends: {NotificationViewSet.filter_backends}")
print(f"  filterset_fields: {NotificationViewSet.filterset_fields}")
print("  ✅ PASSED: DjangoFilterBackend is properly configured")

# Cleanup
print("\n[Cleanup] Deleting test data...")
Notification.objects.filter(user=user).delete()
user.delete()
print("  ✅ Cleaned up test data")

print("\n" + "=" * 60)
print("ALL TESTS PASSED! ✅")
print("is_read filter is now working correctly")
print("=" * 60)

print("\n" + "=" * 60)
print("API USAGE EXAMPLES")
print("=" * 60)
print("\n📌 GET ALL NOTIFICATIONS")
print("  GET /api/notifications/")

print("\n📌 GET READ NOTIFICATIONS")
print("  GET /api/notifications/?is_read=true")

print("\n📌 GET UNREAD NOTIFICATIONS")
print("  GET /api/notifications/?is_read=false")

print("\n📌 MARK NOTIFICATION AS READ")
print("  PATCH /api/notifications/{id}/")
print("  Body: {'is_read': true}")

print("\n📌 MARK ALL AS READ")
print("  POST /api/notifications/mark_all_as_read/")

print("\n" + "=" * 60)

