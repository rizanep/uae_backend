# Delivery Charge System Implementation

## Overview
The delivery charge system automatically calculates shipping fees based on order totals. Admins can configure the thresholds and charge amounts.

---

## ⚙️ **Default Configuration**
- **Free Shipping Threshold**: AED 40
- **Delivery Charge (Below Threshold)**: AED 10
- **Status**: Active by default

---

## 📊 **How It Works**

### Pricing Rules
```
Order Total         | Delivery Charge
<======================
< AED 40           | AED 10
>= AED 40          | FREE (0 AED)
```

### Example Scenarios

**Scenario 1: Low Order Value**
```
Cart Total:             AED 30
Discount (if any):      AED 0
After Discount:         AED 30
Delivery Charge:        AED 10  ← Applied (order < 40)
Tip Amount:             AED 0
========================================
Final Total:            AED 40
```

**Scenario 2: Meets Free Shipping Threshold**
```
Cart Total:             AED 50
Discount (coupon):      AED 10
After Discount:         AED 40
Delivery Charge:        FREE   ← Not applied (order >= 40)
Tip Amount:             AED 5
========================================
Final Total:            AED 45
```

**Scenario 3: High Order with Discount**
```
Cart Total:             AED 100
Discount (coupon):      AED 70
After Discount:         AED 30
Delivery Charge:        AED 10  ← Applied (order < 40 after discount)
Tip Amount:             AED 10
========================================
Final Total:            AED 50
```

---

## 🔄 **Order Total Calculation Flow**

```
1. Cart Total (sum of all items)
   ↓
2. Apply Coupon Discount (if provided)
   ↓
3. Calculate Delivery Charge (based on amount AFTER discount)
   ↓
4. Add Tip Amount
   ↓
5. Final Total = (Cart - Discount) + Delivery + Tip
```

---

## 📡 **API Endpoints**

### 1️⃣ **GET Delivery Charge Settings**
```
GET /api/orders/delivery_charge_settings/
Authorization: Admin only
```

**Response:**
```json
{
    "min_free_shipping_amount": "40.00",
    "delivery_charge": "10.00",
    "is_active": true,
    "updated_at": "2026-03-29T10:30:00Z",
    "message": "Current delivery charge configuration"
}
```

---

### 2️⃣ **UPDATE Delivery Charge Settings**
```
POST /api/orders/delivery_charge_settings/
Authorization: Admin only
Content-Type: application/json

{
    "min_free_shipping_amount": 50.00,
    "delivery_charge": 8.00,
    "is_active": true
}
```

**Response:**
```json
{
    "min_free_shipping_amount": "50.00",
    "delivery_charge": "8.00",
    "is_active": true,
    "updated_at": "2026-03-29T10:35:00Z",
    "message": "Delivery charge configuration updated successfully"
}
```

---

### 3️⃣ **Checkout Summary (Shows Delivery Charges)**
```
POST /api/orders/checkout_summary/
Content-Type: application/json

{
    "address_id": 1,
    "coupon_code": "SAVE20",
    "tip_amount": 50
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
    "delivery_charge": "0.00",      ← FREE (orders >= 40)
    "tip_amount": "50.00",
    "final_total": "450.00",
    "items_count": 5
}
```

---

### 4️⃣ **Checkout (Order Creation with Delivery Charges)**
```
POST /api/orders/checkout/
Content-Type: application/json

{
    "address_id": 1,
    "coupon_code": "SAVE20",
    "tip_amount": 50,
    "payment_method": "TELR",
    "preferred_delivery_date": "2026-04-10"
}
```

**Order Response includes:**
```json
{
    "id": 123,
    "status": "PENDING",
    "total_amount": "450.00",
    "tip_amount": "50.00",
    "coupon_code": "SAVE20",
    "discount_amount": "100.00",
    "delivery_charge": "0.00",      ← Stored in Order
    "items": [...],
    "payment": {...}
}
```

---

## 🗄️ **Database Schema**

### Order Model (Updated)
```python
class Order(models.Model):
    user = ForeignKey(User)
    total_amount = DecimalField()      # Final amount
    tip_amount = DecimalField()
    coupon = ForeignKey(Coupon, null=True)
    discount_amount = DecimalField()
    delivery_charge = DecimalField()   # ← NEW
    status = CharField()
    created_at = DateTimeField()
```

### DeliveryChargeConfig Model (New)
```python
class DeliveryChargeConfig(models.Model):
    min_free_shipping_amount = DecimalField(default=40.00)  # Threshold
    delivery_charge = DecimalField(default=10.00)           # Charge amount
    is_active = BooleanField(default=True)                  # Enable/disable
    updated_at = DateTimeField(auto_now=True)
    updated_by = ForeignKey(User, null=True)
```

---

## 🔐 **Admin Configuration**

### Django Admin Panel

1. **Navigate to**: Admin Dashboard → Orders → Delivery Charge Configuration
2. **Update Rules**:
   - `Min Free Shipping Amount`: Threshold (e.g., 40)
   - `Delivery Charge`: Amount to charge (e.g., 10)
   - `Is Active`: Toggle on/off

### Settings via API

Use the `/api/orders/delivery_charge_settings/` endpoint:

**Change Free Shipping Threshold to 50 AED:**
```bash
curl -X POST http://localhost:8000/api/orders/delivery_charge_settings/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "min_free_shipping_amount": 50.00,
    "delivery_charge": 10.00,
    "is_active": true
  }'
```

---

## 🧮 **Service Functions** (`coupon_service.py`)

### `get_delivery_charge(order_amount)`
Calculates delivery charge based on current configuration.

**Arguments:**
- `order_amount` (Decimal): The order/cart total after discount

**Returns:**
- `Decimal`: Delivery charge amount (0 for free shipping, or configured charge)

**Example:**
```python
from Orders.coupon_service import get_delivery_charge
from decimal import Decimal

# Order below threshold
charge = get_delivery_charge(Decimal('30.00'))  # Returns: 10.00

# Order at/above threshold
charge = get_delivery_charge(Decimal('50.00'))  # Returns: 0.00
```

---

## 📋 **Serializer Fields**

OrderSerializer now includes:
```python
"delivery_charge": DecimalField(read_only=True)
```

Example response:
```json
{
    "id": 123,
    "status": "PENDING",
    "total_amount": "450.00",
    "tip_amount": "50.00",
    "coupon_code": "SAVE20",
    "discount_amount": "100.00",
    "delivery_charge": "0.00",
    "items": [...],
    "created_at": "2026-03-29T10:00:00Z"
}
```

---

## ✅ **Calculation Order (Important)**

The total amount is calculated in this specific order:

1. **Cart Total** = Sum of all items
2. **Discount** = Apply coupon (based on cart total)
3. **After Discount** = Cart total - discount
4. **Delivery Charge** = Calculated based on AFTER DISCOUNT amount
5. **Tip** = Added as-is
6. **Final Total** = After Discount + Delivery Charge + Tip

**This ensures coupons are applied BEFORE delivery charges are calculated.**

---

## 🛡️ **Error Handling**

### Invalid Configuration Values
```json
{
    "error": "min_free_shipping_amount must be a valid decimal"
}
```

### Delivery Disabled
If `is_active = false`, delivery charge is always 0:
```python
if not config.is_active:
    return Decimal('0.00')
```

---

## 🧪 **Testing Scenarios**

### Test 1: Default Configuration (≥ AED 40 = Free)
```python
config = DeliveryChargeConfig.get_config()
assert config.min_free_shipping_amount == Decimal('40.00')
assert config.delivery_charge == Decimal('10.00')

charge = get_delivery_charge(Decimal('30.00'))
assert charge == Decimal('10.00')  # ✓ Charged

charge = get_delivery_charge(Decimal('40.00'))
assert charge == Decimal('0.00')   # ✓ Free shipping

charge = get_delivery_charge(Decimal('100.00'))
assert charge == Decimal('0.00')   # ✓ Free shipping
```

### Test 2: Changed Configuration (≥ AED 50 = Free)
```python
config = DeliveryChargeConfig.get_config()
config.min_free_shipping_amount = Decimal('50.00')
config.delivery_charge = Decimal('8.00')
config.save()

charge = get_delivery_charge(Decimal('40.00'))
assert charge == Decimal('8.00')   # ✓ Now charges AED 8

charge = get_delivery_charge(Decimal('50.00'))
assert charge == Decimal('0.00')   # ✓ Free at new threshold
```

### Test 3: Disable Delivery Charges
```python
config = DeliveryChargeConfig.get_config()
config.is_active = False
config.save()

charge = get_delivery_charge(Decimal('30.00'))
assert charge == Decimal('0.00')   # ✓ No charge even below threshold
```

### Test 4: Order Checkout with Delivery Charge
```
POST /api/orders/checkout/
{
    "address_id": 1,
    "tip_amount": 0,
    "coupon_code": null
}

# Cart: AED 30 → Should add AED 10 delivery charge
# Expected total: AED 40
```

---

## 🔄 **Migration Required**

```bash
python manage.py makemigrations Orders
python manage.py migrate Orders
```

This creates:
- `delivery_charge` field in Order model
- DeliveryChargeConfig model (singleton)

---

## 📝 **Admin Visibility**

The `DeliveryChargeConfig` is visible in Django admin with:
- ✅ Read/Write access to all fields
- ✅ Inline editing of threshold and charge
- ✅ Audit trail (updated_at, updated_by)
- ❌ Cannot be deleted (only one instance)
- ❌ Cannot add another instance

---

## 🚀 **Next Steps / Enhancements**

1. **Location-Based Delivery Charges** - Different charges by emirate
2. **Bulk Order Discount** - Different thresholds = different charges
3. **Promo Free Shipping** - Campaign-based free shipping overrides
4. **Multiple Delivery Options** - Standard, Express, Next-day
5. **Delivery Partner Integration** - Real shipping costs from extern API
6. **Analytics** - Track delivery fee impact on conversion rates

---

## 📌 **Key Points**

✅ Delivery charge is calculated **AFTER** discount is applied
✅ Delivery charge is **BEFORE** tip is added  
✅ Configuration is **centralized** in one model
✅ Admins can **toggle on/off** globally
✅ **Audit trail** tracks who changed what and when
✅ **No deletion** allowed (prevent accidents)
✅ Changes take effect **immediately** (no deploy needed)
