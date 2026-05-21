# Product Notifications Admin API

## Overview

The Product Notifications Admin API allows administrators to track and manage users who have requested notifications for out-of-stock products. This feature ensures reliable notification tracking with the following guarantees:

- **Duplicate Prevention**: Multiple clicks by the same user for the same product count as only one notification
- **Automatic Clearing**: Notifications are automatically marked as sent when stock is restocked
- **Admin Only**: All admin endpoints are restricted to authenticated staff users
- **Detailed Tracking**: Admin can see user IDs, names, emails, and phone numbers

## Features

### 1. User Notification Registration
Users can request notifications when a product is out of stock. The system ensures:
- Only one notification per user per product (enforced by `unique_together` constraint)
- Multiple clicks don't create duplicate entries
- Automatic deduplication using Django's `get_or_create()` method

### 2. Stock Restock Auto-Clearing
When stock is restored:
- All pending notifications are automatically sent via:
  - Email notification
  - WhatsApp message
  - Push notification
- Notifications are marked as `notified=True`
- Next API call will only show truly pending notifications

### 3. Admin Viewing
Administrators can:
- View count of users requesting notifications for a product
- See all user details (ID, name, email, phone)
- Filter by notification status
- Track notification sending history

## API Endpoints

### Get Notifying Users (Admin Only)

**Endpoint:**
```
GET /api/products/products/{product_id}/notifying-users/
```

**Authentication Required:** Yes (Admin/Staff only)

**Method:** GET

**Response Format:**
```json
{
  "product_id": 1,
  "product_name": "Fresh Hamour Fish",
  "pending_notifications_count": 5,
  "notifying_users": [
    {
      "id": 1,
      "user_id": 101,
      "user_name": "Ahmed",
      "user_email": "ahmed@example.com",
      "user_phone": "+971501234567",
      "created_at": "2026-05-17T10:30:45Z",
      "notified": false
    },
    {
      "id": 2,
      "user_id": 102,
      "user_name": "Fatima",
      "user_email": "fatima@example.com",
      "user_phone": "+971509876543",
      "created_at": "2026-05-17T11:15:22Z",
      "notified": false
    }
  ]
}
```

**Response Fields:**
- `product_id` (integer): ID of the product
- `product_name` (string): Name of the product
- `pending_notifications_count` (integer): Number of users with pending notifications
- `notifying_users` (array): Array of notification objects

**Notification Object Fields:**
- `id` (integer): Unique notification record ID
- `user_id` (integer): The user's ID in the system
- `user_name` (string): User's first name
- `user_email` (string): User's email address
- `user_phone` (string): User's phone number
- `created_at` (datetime): Timestamp when notification request was created
- `notified` (boolean): Whether this notification has been sent

**Status Codes:**
- `200 OK`: Successfully retrieved notifying users
- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: Not an admin/staff user
- `404 Not Found`: Product doesn't exist

### Register Notification Request (User)

**Endpoint:**
```
POST /api/products/products/{product_id}/notify-stock/
```

**Authentication Required:** Yes (Any authenticated user)

**Method:** POST

**Request Body:**
```json
{}
```

**Response Format (Success - Created):**
```json
{
  "detail": "You will be notified when this product comes back in stock.",
  "created": true
}
```

**Response Format (Success - Already Registered):**
```json
{
  "detail": "You will be notified when this product comes back in stock.",
  "created": false
}
```

**Response Codes:**
- `200 OK`: Notification registered (or already exists)
- `400 Bad Request`: Product is currently in stock
- `401 Unauthorized`: Not authenticated
- `404 Not Found`: Product doesn't exist

---

## Data Model

### ProductNotification Model

```python
class ProductNotification(models.Model):
    user = ForeignKey('Users.User', on_delete=models.CASCADE)
    product = ForeignKey('Product', on_delete=models.CASCADE)
    created_at = DateTimeField(auto_now_add=True)
    notified = BooleanField(default=False)
    
    class Meta:
        unique_together = ['user', 'product']  # Prevents duplicates
```

**Key Constraints:**
- `unique_together = ['user', 'product']`: Ensures one notification per user per product
- `on_delete=models.CASCADE`: Deletes notifications when user or product is deleted

---

## Usage Examples

### Example 1: Check Notifying Users for a Product

**Request:**
```bash
curl -X GET "http://localhost:8000/api/products/products/42/notifying-users/" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
  "product_id": 42,
  "product_name": "Premium Hammour - 2kg",
  "pending_notifications_count": 3,
  "notifying_users": [
    {
      "id": 15,
      "user_id": 205,
      "user_name": "Mohammed",
      "user_email": "m.khan@example.com",
      "user_phone": "+971505555555",
      "created_at": "2026-05-17T08:22:10Z",
      "notified": false
    }
  ]
}
```

### Example 2: User Requests Notification

**Request:**
```bash
curl -X POST "http://localhost:8000/api/products/products/42/notify-stock/" \
  -H "Authorization: Bearer USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Response (First Time):**
```json
{
  "detail": "You will be notified when this product comes back in stock.",
  "created": true
}
```

**Response (Subsequent Clicks - Same User):**
```json
{
  "detail": "You will be notified when this product comes back in stock.",
  "created": false
}
```

### Example 3: Stock Restocked - Auto Clearing

When admin updates product stock from 0 to a positive number:

```python
# In Django admin or via API:
product = Product.objects.get(id=42)
product.stock = 100
product.save()  # Triggers _notify_stock_availability()
```

**What happens automatically:**
1. All pending notifications for product_id=42 are retrieved
2. Each user receives:
   - Email notification
   - WhatsApp message
   - Push notification
3. All notification records are marked with `notified=True`
4. Subsequent calls to `/notifying-users/` will show `pending_notifications_count: 0`

---

## Query Examples

### Get All Pending Notifications (Django Shell)

```python
from Products.models import ProductNotification, Product

# Get pending notifications for a specific product
product = Product.objects.get(id=42)
pending = ProductNotification.objects.filter(
    product=product,
    notified=False
).select_related('user')

for notification in pending:
    print(f"{notification.user.first_name} ({notification.user.id})")

# Get count
count = pending.count()
print(f"Total pending: {count}")
```

### Get All Notified Users (Historical)

```python
# See which users were already notified
notified = ProductNotification.objects.filter(
    product=product,
    notified=True
).select_related('user')
```

---

## Workflow Diagram

```
┌─────────────────────┐
│  User Clicks        │
│  "Notify Me"        │
│  (Product OOS)      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────┐
│ Creates ProductNotification │
│ (notified=False)            │
│ unique_together prevents    │
│ duplicate entries           │
└──────────┬──────────────────┘
           │
      ┌────┴────┐
      │          │
      ▼          ▼
   USER   ADMIN VIEW
  waits   checks list
   for    via API
  stock   /notifying-users/
   │          │
   │    ┌─────────────────┐
   │    │ Returns count & │
   │    │ user details    │
   │    │ (admin only)    │
   │    └─────────────────┘
   │
   ▼
┌──────────────────────────┐
│ Admin Restocks Product   │
│ stock: 0 → 100           │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────────┐
│ Auto Notification Trigger    │
│ _notify_stock_availability() │
└──────────┬───────────────────┘
           │
      ┌────┼────┬────┐
      │    │    │    │
      ▼    ▼    ▼    ▼
    Email  WA  Push  Mark
    sent   sent sent notified=True
      │    │    │    │
      └────┴────┴────┘
           │
           ▼
┌──────────────────────────────┐
│ ProductNotification updated  │
│ notified=True               │
│ Listed as "historical"      │
└──────────────────────────────┘
```

---

## Security & Permissions

### Permission Classes

All admin endpoints use `permission_classes=[permissions.IsAdminUser]`:
- User must be authenticated
- User must have `is_staff=True`
- User must have `is_superuser=True` (for some views)

### Data Privacy

- Only admins can see user contact details (email, phone)
- Users can only create notifications for products that are currently out of stock
- Historical notification data is retained for audit purposes

---

## Database Optimization

### Indexes

The ProductNotification model benefits from:
- Primary key index on `id`
- Foreign key indexes on `user_id` and `product_id`
- Unique constraint index on `(user_id, product_id)`

### Query Optimization

The admin endpoint uses:
- `select_related('user')`: Reduces N+1 queries for user data
- `filter(notified=False)`: Only fetches pending notifications
- `order_by('-created_at')`: Most recent first

---

## Error Handling

### Common Errors

**1. Not Admin**
```json
{
  "detail": "Permission denied."
}
```
Status: 403

**2. Product Not Found**
```json
{
  "detail": "Product not found."
}
```
Status: 404

**3. Product In Stock (User Registration)**
```json
{
  "detail": "Product is currently in stock."
}
```
Status: 400

**4. Not Authenticated**
```json
{
  "detail": "Authentication credentials were not provided."
}
```
Status: 401

---

## Testing

### Test Cases

```python
# Test 1: Duplicate prevention
user = User.objects.get(id=1)
product = Product.objects.get(id=42)

# First click
notification1, created1 = ProductNotification.objects.get_or_create(
    user=user, product=product
)
assert created1 == True

# Second click - same user, same product
notification2, created2 = ProductNotification.objects.get_or_create(
    user=user, product=product
)
assert created2 == False
assert notification1.id == notification2.id  # Same notification

# Test 2: Admin can view
response = admin_client.get(
    f'/api/products/products/{product.id}/notifying-users/'
)
assert response.status_code == 200
assert response.data['pending_notifications_count'] == 1

# Test 3: User blocked from viewing
response = user_client.get(
    f'/api/products/products/{product.id}/notifying-users/'
)
assert response.status_code == 403
```

---

## Monitoring & Alerts

### Key Metrics

- Total pending notifications per product
- Average time to restock
- Notification delivery success rate
- Users per product notification request

### Suggested Alerts

1. More than 100 pending notifications for one product
2. Notification not sent for > 24 hours after restock
3. Duplicate notification attempts by same user (should be 0)

---

## Troubleshooting

### Issue: Notifications not clearing after restock

**Solution:**
1. Check if `_notify_stock_availability()` is being called in `Product.save()`
2. Verify stock change was from 0 to positive
3. Check Celery tasks are running (email/WhatsApp notifications)
4. Review notification logs

### Issue: Duplicate entries appearing

**Solution:**
1. Should not happen due to `unique_together` constraint
2. If it does, database integrity issue - run:
   ```sql
   SELECT user_id, product_id, COUNT(*) 
   FROM products_productnotification
   GROUP BY user_id, product_id
   HAVING COUNT(*) > 1;
   ```

### Issue: Admin can't see users

**Solution:**
1. Ensure admin user has `is_staff=True`
2. Check database for `select_related('user')` working
3. Verify user records exist (not soft-deleted)

---

## Changelog

### Version 1.0 (2026-05-17)

- Initial implementation of Product Notifications Admin API
- Added `/notifying-users/` endpoint for admin viewing
- Auto-clearing of notifications on stock restock
- Duplicate prevention via unique constraints
- Complete user details tracking

---

## Related Documentation

- [Product API Reference](./PRODUCTS_README.md)
- [Notifications System](./Notifications/)
- [Firebase Push Notifications](./FRONTEND_INTEGRATION_GUIDE.md)
- [WhatsApp Integration](./WHATSAPP_INTEGRATION_README.md)

