# Admin Coupons & Rewards Management API

Admin-only endpoints for managing coupons and reward configurations.

---

## Authentication
All endpoints require:
- **Authentication**: Valid JWT token
- **Permission**: Admin user (`is_staff=True` or `role="admin"`)

---

## 1. Admin Coupons Management

### Base URL
```
POST/GET/PUT/DELETE /api/marketing/admin/coupons/
```

### 1.1 List All Coupons
```http
GET /api/marketing/admin/coupons/
```

**Query Parameters:**
- `is_active` - Filter by active status (true/false)
- `discount_type` - Filter by type (percentage/fixed)
- `is_referral_reward` - Filter referral coupons (true/false)
- `is_first_order_reward` - Filter first order coupons (true/false)
- `assigned_user` - Filter by user ID
- `valid_from`, `valid_to` - Filter by validity period
- `ordering` - Sort by (created_at, updated_at, discount_value, used_count)
- `search` - Search by code, description, or email

**Response:**
```json
{
  "count": 150,
  "next": "...",
  "previous": "...",
  "results": [
    {
      "id": 1,
      "code": "SAVE20",
      "description": "Summer sale - 20% off",
      "discount_type": "percentage",
      "discount_value": "20.00",
      "min_order_amount": "100.00",
      "max_discount_amount": "500.00",
      "valid_from": "2026-04-01T00:00:00Z",
      "valid_to": "2026-06-30T23:59:59Z",
      "is_active": true,
      "usage_limit": 1000,
      "used_count": 245,
      "assigned_user": null,
      "assigned_user_email": null,
      "is_referral_reward": false,
      "is_first_order_reward": false,
      "created_at": "2026-04-01T10:30:00Z",
      "updated_at": "2026-04-15T14:20:00Z",
      "deleted_at": null
    }
  ]
}
```

### 1.2 Create New Coupon
```http
POST /api/marketing/admin/coupons/
```

**Request Body:**
```json
{
  "code": "WELCOME30",
  "description": "Welcome discount for new users",
  "discount_type": "percentage",
  "discount_value": "30.00",
  "min_order_amount": "50.00",
  "max_discount_amount": "200.00",
  "valid_from": "2026-04-03T00:00:00Z",
  "valid_to": "2026-05-03T23:59:59Z",
  "is_active": true,
  "usage_limit": 500,
  "assigned_user": null,
  "is_referral_reward": false,
  "is_first_order_reward": false
}
```

**Response:** (201 Created)
```json
{
  "id": 151,
  "code": "WELCOME30",
  "description": "Welcome discount for new users",
  "discount_type": "percentage",
  "discount_value": "30.00",
  "min_order_amount": "50.00",
  "max_discount_amount": "200.00",
  "valid_from": "2026-04-03T00:00:00Z",
  "valid_to": "2026-05-03T23:59:59Z",
  "is_active": true,
  "usage_limit": 500,
  "used_count": 0,
  "assigned_user": null,
  "assigned_user_email": null,
  "is_referral_reward": false,
  "is_first_order_reward": false,
  "created_at": "2026-04-03T12:00:00Z",
  "updated_at": "2026-04-03T12:00:00Z",
  "deleted_at": null
}
```

### 1.3 Update Coupon
```http
PUT /api/marketing/admin/coupons/{id}/
PATCH /api/marketing/admin/coupons/{id}/
```

**Request Body (partial update):**
```json
{
  "discount_value": "35.00",
  "valid_to": "2026-05-10T23:59:59Z",
  "usage_limit": 300
}
```

**Response:** (200 OK)
```json
{
  "id": 151,
  "code": "WELCOME30",
  "discount_value": "35.00",
  "valid_to": "2026-05-10T23:59:59Z",
  "usage_limit": 300,
  ...
}
```

### 1.4 Soft Delete Coupon
```http
POST /api/marketing/admin/coupons/{id}/soft_delete/
```

**Response:** (200 OK)
```json
{
  "detail": "Coupon soft deleted successfully."
}
```

### 1.5 Restore Deleted Coupon
```http
POST /api/marketing/admin/coupons/{id}/restore/
```

**Response:** (200 OK)
```json
{
  "detail": "Coupon restored successfully."
}
```

### 1.6 Coupon Statistics
```http
GET /api/marketing/admin/coupons/stats/
```

**Response:**
```json
{
  "total_coupons": 150,
  "active_coupons": 120,
  "referral_coupons": 45,
  "first_order_coupons": 30,
  "total_redeemed": 1240
}
```

---

## 2. Reward Configuration Management

### Base URL
```
GET/PUT /api/marketing/admin/rewards/
```

All reward configuration endpoints operate on a singleton resource (only one config exists).

### 2.1 View Current Reward Configuration
```http
GET /api/marketing/admin/rewards/
```

**Response:**
```json
{
  "first_order_discount_type": "percentage",
  "first_order_discount_value": "10.00",
  "first_order_min_amount": "50.00",
  "first_order_validity_days": 30,
  "referral_discount_type": "percentage",
  "referral_discount_value": "15.00",
  "referral_min_amount": "100.00",
  "referral_validity_days": 60,
  "referral_usage_limit": 1,
  "referrer_discount_value": "15.00",
  "referrer_validity_days": 60,
  "max_discount_percentage": null,
  "is_referral_active": true,
  "is_first_order_active": true,
  "updated_by": 1,
  "updated_by_email": "admin@example.com",
  "updated_at": "2026-04-03T10:00:00Z"
}
```

### 2.2 Update Reward Configuration
```http
PUT /api/marketing/admin/rewards/
PATCH /api/marketing/admin/rewards/
```

**Request Body (update all or partial fields):**
```json
{
  "first_order_discount_value": "15.00",
  "referral_discount_value": "20.00",
  "referrer_discount_value": "20.00",
  "referral_min_amount": "150.00",
  "referral_validity_days": 90,
  "max_discount_percentage": "500.00",
  "is_referral_active": true,
  "is_first_order_active": true
}
```

**Response:** (200 OK)
```json
{
  "detail": "Reward configuration updated successfully.",
  "config": {
    "first_order_discount_value": "15.00",
    "referral_discount_value": "20.00",
    "referrer_discount_value": "20.00",
    "referral_min_amount": "150.00",
    "referral_validity_days": 90,
    "max_discount_percentage": "500.00",
    "is_referral_active": true,
    "is_first_order_active": true,
    "updated_by": 1,
    "updated_by_email": "admin@example.com",
    "updated_at": "2026-04-03T14:30:00Z",
    ...
  }
}
```

### 2.3 Reset to Defaults
```http
POST /api/marketing/admin/rewards/reset_to_defaults/
```

Resets all reward configuration to factory defaults:
- First Order: 10% off, min AED 50, 30 days
- Referral: 15% off, min AED 100, 60 days, 1 use limit
- Referrer: 15% off, 60 days

**Response:** (200 OK)
```json
{
  "detail": "Reward configuration reset to defaults.",
  "config": {
    "first_order_discount_type": "percentage",
    "first_order_discount_value": "10.00",
    "first_order_min_amount": "50.00",
    "first_order_validity_days": 30,
    "referral_discount_type": "percentage",
    "referral_discount_value": "15.00",
    "referral_min_amount": "100.00",
    "referral_validity_days": 60,
    "referral_usage_limit": 1,
    "referrer_discount_value": "15.00",
    "referrer_validity_days": 60,
    "max_discount_percentage": null,
    "is_referral_active": true,
    "is_first_order_active": true,
    "updated_at": "2026-04-03T14:45:00Z",
    ...
  }
}
```

---

## Field Descriptions

### Coupon Fields
- **code**: Unique coupon code (required)
- **description**: Coupon description and terms
- **discount_type**: "percentage" or "fixed"
- **discount_value**: 0-100 for percentage, any amount for fixed
- **min_order_amount**: Minimum cart total to use coupon
- **max_discount_amount**: Cap on discount for percentage coupons
- **valid_from**: When coupon becomes valid
- **valid_to**: When coupon expires
- **is_active**: Enable/disable coupon
- **usage_limit**: Max times coupon can be used (null = unlimited)
- **used_count**: Current redemption count (read-only)
- **assigned_user**: Restrict to specific user (null = global)
- **is_referral_reward**: Mark as referral reward
- **is_first_order_reward**: Mark as first order reward

### Reward Configuration Fields
- **first_order_discount_type**: Discount type for new users
- **first_order_discount_value**: Discount percentage/amount
- **first_order_min_amount**: Minimum order to use
- **first_order_validity_days**: Days valid from account creation
- **referral_discount_type**: Discount type for referrals
- **referral_discount_value**: Discount for referee
- **referral_min_amount**: Minimum order to use
- **referral_validity_days**: Days valid from referral
- **referral_usage_limit**: Max uses per coupon
- **referrer_discount_value**: Discount for referrer
- **referrer_validity_days**: Days valid for referrer
- **max_discount_percentage**: Optional cap on percentage discounts
- **is_referral_active**: Enable/disable referral system
- **is_first_order_active**: Enable/disable first order rewards

---

## Examples

### Example 1: Create First Order Coupon Template
```bash
curl -X POST http://localhost:8000/api/marketing/admin/coupons/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "FIRST50",
    "description": "50% off for first order",
    "discount_type": "percentage",
    "discount_value": "50.00",
    "min_order_amount": "100.00",
    "valid_from": "2026-04-03T00:00:00Z",
    "valid_to": "2026-12-31T23:59:59Z",
    "is_active": true,
    "usage_limit": 9999,
    "is_first_order_reward": true
  }'
```

### Example 2: Update Referral Reward Configuration
```bash
curl -X PATCH http://localhost:8000/api/marketing/admin/rewards/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "referral_discount_value": "25.00",
    "referrer_discount_value": "25.00",
    "referral_validity_days": 90
  }'
```

### Example 3: View Coupon Stats
```bash
curl -X GET http://localhost:8000/api/marketing/admin/coupons/stats/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Error Responses

### 400 Bad Request
```json
{
  "discount_value": ["Percentage discount must be between 0 and 100."]
}
```

### 403 Forbidden
```json
{
  "detail": "You do not have permission to perform this action."
}
```

### 404 Not Found
```json
{
  "detail": "Not found."
}
```

---

## Next Steps

1. Run migrations to create the RewardConfiguration model:
   ```bash
   python manage.py makemigrations Marketing
   python manage.py migrate
   ```

2. Access admin endpoints at:
   - Coupons: `/api/marketing/admin/coupons/`
   - Rewards: `/api/marketing/admin/rewards/`

3. Use the configuration endpoints to adjust reward scales in real-time
