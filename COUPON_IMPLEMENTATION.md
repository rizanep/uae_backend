# Coupon System Implementation Guide

## Overview
The coupon system enables users to apply discount codes during checkout, with comprehensive validation, calculation, and tracking.

---

## 🔄 **Coupon Application Flow**

### Step 1: Validate Coupon (Optional Pre-Checkout)
```
POST /api/orders/validate_coupon/
Content-Type: application/json

{
    "coupon_code": "SAVE20",
    "cart_total": 500.00
}
```

**Response:**
```json
{
    "success": true,
    "message": "Coupon 'SAVE20' is valid. Discount: 100.00",
    "coupon_code": "SAVE20",
    "discount_amount": "100.00",
    "discount_type": "percentage",
    "discount_percentage": 20,
    "cart_total": "500.00",
    "final_amount": "400.00"
}
```

---

### Step 2: Get Order Summary (Confirmation)
```
POST /api/orders/checkout_summary/
Content-Type: application/json

{
    "address_id": 1,
    "coupon_code": "SAVE20",
    "tip_amount": 50,
    "preferred_delivery_date": "2026-04-10",
    "preferred_delivery_slot": "9AM-12PM"
}
```

**Response:**
```json
{
    "success": true,
    "cart_total_before_discount": "500.00",
    "discount_amount": "100.00",
    "discount_type": "percentage",
    "discount_code": "SAVE20",
    "coupon_message": null,
    "cart_total_after_discount": "400.00",
    "tip_amount": "50.00",
    "final_total": "450.00",
    "items_count": 5
}
```

---

### Step 3: Checkout with Coupon
```
POST /api/orders/checkout/
Content-Type: application/json

{
    "address_id": 1,
    "coupon_code": "SAVE20",
    "tip_amount": 50,
    "payment_method": "TELR",
    "preferred_delivery_date": "2026-04-10",
    "preferred_delivery_slot": "9AM-12PM"
}
```

**Response:**
```json
{
    "message": "Order created successfully.",
    "order_id": 123,
    "payment_url": "https://telr.com/pay?ref=...",
    "total_amount": "450.00",
    "payment_method": "TELR"
}
```

---

## 📊 **Database Schema**

### Order Model Updates
```python
class Order(models.Model):
    # ... existing fields ...
    coupon = ForeignKey('Marketing.Coupon', null=True, blank=True)
    coupon_code = CharField(max_length=50, blank=True, null=True)
    discount_amount = DecimalField(default=0.00)
    total_amount = DecimalField()  # Final amount (after discount + tip)
```

### Coupon Model (Marketing App)
```python
class Coupon(SoftDeleteModel):
    code = CharField(unique=True)
    discount_type = CharField(choices=['percentage', 'fixed'])
    discount_value = DecimalField()
    min_order_amount = DecimalField(default=0)
    max_discount_amount = DecimalField(null=True)  # Cap on percentage
    
    valid_from = DateTimeField()
    valid_to = DateTimeField(null=True)
    is_active = BooleanField(default=True)
    
    usage_limit = PositiveIntegerField(null=True)
    used_count = PositiveIntegerField(default=0)
    
    assigned_user = ForeignKey(User, null=True)  # NULL = global coupon
    is_referral_reward = BooleanField(default=False)
    is_first_order_reward = BooleanField(default=False)
```

---

## 🔐 **Coupon Validation Logic**

The `coupon.is_valid(user, order_amount)` method checks:

1. ✅ `is_active = True`
2. ✅ Not expired (`valid_to > now`)
3. ✅ Not started yet (`valid_from <= now`)
4. ✅ Usage limit (`used_count < usage_limit`)
5. ✅ User assignment (`assigned_user = None OR assigned_user = current_user`)
6. ✅ Minimum order amount (`order_amount >= min_order_amount`)

---

## 💰 **Discount Calculation**

### Percentage Discount
```python
# SAVE20 coupon: 20% off, max AED 500
discount = order_amount * (20 / 100)  # AED 500 order = AED 100 discount
discount = min(discount, max_discount_amount=500)  # Cap at 500
discount = min(discount, order_amount)  # Cannot exceed order amount
```

### Fixed Amount Discount
```python
# SAVE100 coupon: AED 100 off
discount = 100
discount = min(discount, order_amount)  # Cannot exceed order amount
```

---

## 📡 **API Endpoints**

| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|----------------|
| `/orders/validate_coupon/` | POST | Validate coupon & calculate discount | Yes |
| `/orders/checkout_summary/` | POST | Get order summary with discounts | Yes |
| `/orders/checkout/` | POST | Create order with coupon | Yes |
| `/orders/{id}/` | GET | View order (includes coupon info) | Yes |
| `/marketing/coupons/` | GET | List user's assigned coupons | Yes |

---

## 🔄 **Coupon Usage Lifecycle**

```
1. User gets coupon (assigned_coupons field)
   ↓
2. User applies during checkout
   └─ validate_coupon() → Returns discount details
   ↓
3. User confirms at checkout_summary()
   ↓
4. User completes checkout()
   └─ Order.coupon = Coupon object
   └─ Order.discount_amount = calculated amount
   └─ Order.total_amount = final amount with discount
   ↓
5. Payment is verified
   └─ Coupon.used_count += 1  ← Incremented here
   ↓
6. Order completed
   └─ Coupon can be re-used if:
      - usage_limit > used_count
      - Still within valid_from/valid_to
```

---

## 🎯 **Special Coupon Types**

### Welcome Coupon (First Order)
- Auto-created on user registration
- Code: `WELCOME-{USER_ID}-{RANDOM}`
- 10% off
- Minimum: AED 50
- Valid: 30 days
- Limit: 1 use
- Assigned to: Specific user

```python
# Auto-created by signal after user registration
create_first_order_coupon(user)
```

### Referral Coupons
- Auto-created when referral link is used
- For referrer: `REF-R-{ID}-{RANDOM}` (15% off)
- For referee: `REF-F-{ID}-{RANDOM}` (discount)
- Valid: 60 days (referrer), 30 days (referee)
- Assigned to: Specific user

```python
# Auto-created by grant_referral_rewards()
apply_referral/
```

### Global/Marketing Coupons
- Created manually by admin
- Code: `SUMMER20`, `BLACKFRI`, `NEWYEAR`
- `assigned_user = NULL` (available to all users)
- Can have usage limits and validity periods

---

## ⚙️ **Service Functions** (`coupon_service.py`)

### `validate_and_calculate_coupon(coupon_code, user, order_amount)`
Validates coupon and calculates discount without modifying database.

**Returns:**
```python
{
    'success': bool,
    'message': str,
    'coupon': Coupon | None,
    'discount_amount': Decimal,
    'discount_type': str,
    'final_amount': Decimal
}
```

### `calculate_discount(coupon, order_amount)`
Pure calculation function for discount amount.

### `apply_coupon_to_order(order, coupon_code, user, cart_total)`
Applies coupon to order and updates order fields.

---

## 🛡️ **Error Handling**

### Invalid Coupon Code
```json
{
    "success": false,
    "message": "Coupon code \"INVALID\" not found.",
    "error": "Coupon code \"INVALID\" not found."
}
```

### Expired Coupon
```json
{
    "success": false,
    "message": "Coupon has expired",
    "error": "Coupon has expired"
}
```

### Usage Limit Exceeded
```json
{
    "success": false,
    "message": "Coupon usage limit reached",
    "error": "Coupon usage limit reached"
}
```

### Minimum Order Not Met
```json
{
    "success": false,
    "message": "Minimum order amount of 100.00 required",
    "error": "Minimum order amount of 100.00 required"
}
```

### User Not Assigned
```json
{
    "success": false,
    "message": "This coupon is not valid for your account",
    "error": "This coupon is not valid for your account"
}
```

---

## 🧪 **Testing Scenarios**

### Test 1: Basic Percentage Coupon
```bash
POST /api/orders/validate_coupon/
{
    "coupon_code": "SUMMER20",  # 20% off
    "cart_total": 500.00
}
# Expected: discount = 100.00, final = 400.00
```

### Test 2: Fixed Amount Coupon
```bash
POST /api/orders/validate_coupon/
{
    "coupon_code": "NEWYEAR",  # AED 100 fixed
    "cart_total": 500.00
}
# Expected: discount = 100.00, final = 400.00
```

### Test 3: Percentage with Max Cap
```bash
POST /api/orders/validate_coupon/
{
    "coupon_code": "BIGDISCOUNT",  # 50% off, max AED 200
    "cart_total": 1000.00
}
# Expected: discount = 200.00 (capped), final = 800.00
```

### Test 4: Personal Coupon (Assigned User)
```bash
# User A can use their WELCOME coupon
# User B cannot use User A's coupon (assigned_user mismatch)
```

### Test 5: Coupon Usage Limit
```bash
# Create coupon with usage_limit = 2
# Use it twice → used_count = 2
# Try to use it again → Error "usage limit reached"
```

---

## 📝 **Serializer Fields**

OrderSerializer now includes:
- `coupon` - ForeignKey reference
- `coupon_code` - Code used (string)
- `discount_amount` - Amount discounted

Example order response:
```json
{
    "id": 123,
    "status": "PENDING",
    "total_amount": "450.00",
    "tip_amount": "50.00",
    "coupon": 45,
    "coupon_code": "SAVE20",
    "discount_amount": "100.00",
    "items": [...],
    "payment": {...}
}
```

---

## 🔐 **Rate Limiting**

- `validate_coupon/` - Limited by `UserOrderThrottle` (100 req/hour)
- `checkout_summary/` - Limited by `UserOrderThrottle` (100 req/hour)
- `checkout/` - Limited by `UserOrderThrottle` (100 req/hour)

---

## 🚀 **Next Steps / Enhancements**

1. **Bulk Coupon Creation** - Admin endpoint to create coupons in bulk
2. **Coupon Analytics** - Track coupon usage, popularity, ROI
3. **Coupon Campaigns** - Link coupons to marketing campaigns
4. **Conditional Coupons** - Coupons by product category, user segment, etc.
5. **Coupon Combinations** - Allow stacking multiple coupons
6. **Refund Handling** - Handle coupon refunds if order is cancelled

---

## 🔍 **Migration Required**

```bash
python manage.py makemigrations Orders
python manage.py migrate Orders
```

This adds the three new fields to the Order model:
- `coupon` (ForeignKey)
- `coupon_code` (CharField)
- `discount_amount` (DecimalField)
