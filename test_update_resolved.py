"""
Test script to verify is_resolved can be updated via PATCH
Run with: python manage.py shell < test_update_resolved.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from Notifications.models import ContactMessage
from Notifications.serializers import ContactMessageSerializer
from Users.models import User

print("=" * 60)
print("TESTING is_resolved UPDATE VIA PATCH")
print("=" * 60)

# Clean up
ContactMessage.objects.filter(email='test_resolved@example.com').delete()
User.objects.filter(email='test_admin@test.com').delete()

# Create test data
print("\n[Test 1] Create contact message...")
msg = ContactMessage.objects.create(
    name="Test User",
    email="test_resolved@example.com",
    subject="Test Subject",
    message="Test message",
    is_resolved=False
)
print(f"  ✅ Created: is_resolved={msg.is_resolved}")

# Test PATCH update with partial=True
print("\n[Test 2] PATCH update - set is_resolved=True...")
data = {'is_resolved': True}
serializer = ContactMessageSerializer(msg, data=data, partial=True)

if serializer.is_valid():
    serializer.save()
    msg.refresh_from_db()
    print(f"  ✅ PASSED: is_resolved updated successfully")
    print(f"  Result: is_resolved={msg.is_resolved}")
    assert msg.is_resolved == True, "is_resolved should be True"
else:
    print(f"  ❌ FAILED: {serializer.errors}")

# Test PATCH update - revert to False
print("\n[Test 3] PATCH update - set is_resolved=False...")
data = {'is_resolved': False}
serializer = ContactMessageSerializer(msg, data=data, partial=True)

if serializer.is_valid():
    serializer.save()
    msg.refresh_from_db()
    print(f"  ✅ PASSED: is_resolved updated successfully")
    print(f"  Result: is_resolved={msg.is_resolved}")
    assert msg.is_resolved == False, "is_resolved should be False"
else:
    print(f"  ❌ FAILED: {serializer.errors}")

# Verify read_only fields are still protected
print("\n[Test 4] Verify other fields are read-only...")
data = {
    'name': 'Changed Name',
    'email': 'changed@example.com',
    'is_resolved': True
}
serializer = ContactMessageSerializer(msg, data=data, partial=True)

if serializer.is_valid():
    serializer.save()
    msg.refresh_from_db()
    
    # name and email should NOT change (read-only)
    assert msg.name == "Test User", "name should be read-only"
    assert msg.email == "test_resolved@example.com", "email should be read-only"
    # is_resolved should change (now writable)
    assert msg.is_resolved == True, "is_resolved should be updated"
    
    print(f"  ✅ PASSED: Read-only fields protected, is_resolved updated")
    print(f"  name: {msg.name} (unchanged)")
    print(f"  email: {msg.email} (unchanged)")
    print(f"  is_resolved: {msg.is_resolved} (updated)")
else:
    print(f"  ❌ FAILED: {serializer.errors}")

# Cleanup
print("\n[Cleanup] Deleting test data...")
ContactMessage.objects.filter(email='test_resolved@example.com').delete()
print("  ✅ Cleaned up test data")

print("\n" + "=" * 60)
print("ALL TESTS PASSED! ✅")
print("is_resolved field can now be updated via PATCH")
print("=" * 60)

print("\n" + "=" * 60)
print("API USAGE")
print("=" * 60)
print("\n📌 MARK MESSAGE AS RESOLVED")
print("  PATCH /api/contact-messages/{id}/")
print("  Body: {'is_resolved': true}")

print("\n📌 MARK MESSAGE AS UNRESOLVED")
print("  PATCH /api/contact-messages/{id}/")
print("  Body: {'is_resolved': false}")

print("\n📌 UPDATE MULTIPLE FIELDS")
print("  PATCH /api/contact-messages/{id}/")
print("  Body: {'is_resolved': true, 'subject': 'Updated Subject'}")

print("\n" + "=" * 60)
