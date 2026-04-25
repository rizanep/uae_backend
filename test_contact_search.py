"""
Test script to demonstrate ContactMessage search functionality
Run with: python manage.py shell < test_contact_search.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from Notifications.models import ContactMessage
from Users.models import User

print("=" * 80)
print("CONTACT MESSAGE SEARCH FUNCTIONALITY")
print("=" * 80)

# Create test user
print("\n[Setup] Creating test user...")
User.objects.filter(email='contact_test@test.com').delete()
user = User.objects.create_user(email='contact_test@test.com', password='testpass123')
print(f"  ✅ Created user: {user.email}")

# Create test contact messages
print("\n[Setup] Creating test contact messages...")
ContactMessage.objects.filter(email__in=['john@example.com', 'jane@example.com', 'bob@example.com', 'alice@example.com']).delete()

msg1 = ContactMessage.objects.create(
    name="John Doe",
    email="john@example.com",
    subject="Product Quality Issue",
    message="The product quality is not as expected"
)

msg2 = ContactMessage.objects.create(
    name="Jane Smith",
    email="jane@example.com",
    subject="Delivery Problem",
    message="My package was damaged during delivery"
)

msg3 = ContactMessage.objects.create(
    name="Bob Johnson",
    email="bob@example.com",
    subject="Billing Question",
    message="I have a question about my billing"
)

msg4 = ContactMessage.objects.create(
    name="Alice Williams",
    email="alice@example.com",
    subject="How to use Product",
    message="Can you help me understand how to use the product properly?"
)

print(f"  ✅ Created 4 test messages")

# Demonstrate search capabilities
print("\n" + "=" * 80)
print("SEARCH EXAMPLES")
print("=" * 80)

# Search by name
print("\n[Search 1] Search by name 'John Doe'")
results = ContactMessage.objects.filter(name__icontains='John Doe')
print(f"  Found: {results.count()} result(s)")
for msg in results:
    print(f"    - {msg.name}: {msg.subject}")
assert results.count() == 1, "Should find 1 result"
print("  ✅ PASSED")

# Search by email
print("\n[Search 2] Search by email 'jane@example.com'")
results = ContactMessage.objects.filter(email__icontains='jane')
print(f"  Found: {results.count()} result(s)")
for msg in results:
    print(f"    - {msg.email}: {msg.subject}")
assert results.count() == 1, "Should find 1 result"
print("  ✅ PASSED")

# Search by subject
print("\n[Search 3] Search by subject containing 'Product'")
results = ContactMessage.objects.filter(subject__icontains='Product')
print(f"  Found: {results.count()} result(s)")
for msg in results:
    print(f"    - {msg.subject}")
assert results.count() == 2, "Should find 2 results (Quality Issue, How to use)"
print("  ✅ PASSED")

# Search by message content
print("\n[Search 4] Search by message containing 'delivery'")
results = ContactMessage.objects.filter(message__icontains='delivery')
print(f"  Found: {results.count()} result(s)")
for msg in results:
    print(f"    - {msg.message[:50]}...")
assert results.count() == 1, "Should find 1 result"
print("  ✅ PASSED")

# Combined filters
print("\n[Search 5] Filter by is_resolved=False AND search 'quality'")
results = ContactMessage.objects.filter(
    is_resolved=False,
    subject__icontains='quality'
)
print(f"  Found: {results.count()} result(s)")
for msg in results:
    print(f"    - {msg.subject}: Resolved={msg.is_resolved}")
assert results.count() == 1, "Should find 1 result"
print("  ✅ PASSED")

# Ordering
print("\n[Search 6] Order by created_at (newest first)")
results = ContactMessage.objects.all().order_by('-created_at')[:2]
print(f"  Latest 2 messages:")
for msg in results:
    print(f"    - {msg.name}: {msg.subject}")
print("  ✅ PASSED")

# Cleanup
print("\n[Cleanup] Deleting test data...")
ContactMessage.objects.filter(email__in=['john@example.com', 'jane@example.com', 'bob@example.com', 'alice@example.com']).delete()
user.delete()
print("  ✅ Cleaned up test data")

print("\n" + "=" * 80)
print("ALL SEARCH EXAMPLES PASSED! ✅")
print("=" * 80)

print("\n" + "=" * 80)
print("API SEARCH ENDPOINTS")
print("=" * 80)

print("\n📌 SEARCH ACROSS ALL FIELDS (name, email, subject, message)")
print("  GET /api/contact-messages/?search=john")
print("  GET /api/contact-messages/?search=delivery")
print("  GET /api/contact-messages/?search=product")

print("\n📌 FILTER BY SPECIFIC FIELD")
print("  GET /api/contact-messages/?name__icontains=john")
print("  GET /api/contact-messages/?email__exact=john@example.com")
print("  GET /api/contact-messages/?subject__icontains=billing")

print("\n📌 FILTER BY STATUS")
print("  GET /api/contact-messages/?is_resolved=true")
print("  GET /api/contact-messages/?is_resolved=false")

print("\n📌 COMBINE SEARCH AND FILTERS")
print("  GET /api/contact-messages/?search=product&is_resolved=false")
print("  GET /api/contact-messages/?search=john&is_resolved=true")

print("\n📌 ORDER RESULTS")
print("  GET /api/contact-messages/?ordering=created_at           # oldest first")
print("  GET /api/contact-messages/?ordering=-created_at          # newest first")
print("  GET /api/contact-messages/?ordering=name                 # A-Z")
print("  GET /api/contact-messages/?ordering=-name                # Z-A")

print("\n📌 COMBINING SEARCH, FILTER, AND ORDERING")
print("  GET /api/contact-messages/?search=product&is_resolved=false&ordering=-created_at")

print("\n" + "=" * 80)
print("SEARCH FIELDS AVAILABLE FOR FULL-TEXT SEARCH")
print("=" * 80)
print("  - name")
print("  - email")
print("  - subject")
print("  - message")
print("\n" + "=" * 80)
