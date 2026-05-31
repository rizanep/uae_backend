# API Quick Reference Card

## 🔗 Base URL
```
https://your-api.com/api
```

---

## 1️⃣ VALIDATE COUPON

**Endpoint:**
```
POST /orders/validate_coupon/
```

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

**Request:**
```json
{
    "coupon_code": "SAVE20",
    "cart_total": 500.00
}
```

**Success (200):**
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

**Error (400):**
```json
{
    "success": false,
    "message": "Coupon code \"INVALID\" not found.",
    "discount_amount": "0.00",
    "discount_type": null,
    "cart_total": "500.00",
    "final_amount": "500.00"
}
```

**Possible Errors:**
- `Coupon code "X" not found`
- `Coupon has expired`
- `Coupon is not yet valid`
- `Coupon usage limit reached`
- `This coupon is not valid for your account`
- `Minimum order amount of X required`

---

## 2️⃣ CHECKOUT SUMMARY

**Endpoint:**
```
POST /orders/checkout_summary/
```

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

**Request:**
```json
{
    "address_id": 1,
    "coupon_code": "SAVE20",
    "tip_amount": 50.00,
    "preferred_delivery_date": "2026-04-10",
    "preferred_delivery_slot": "9AM-12PM"
}
```

**Response (200):**
```json
{
    "success": true,
    "cart_total_before_discount": "500.00",
    "discount_amount": "100.00",
    "discount_type": "percentage",
    "discount_code": "SAVE20",
    "coupon_message": null,
    "cart_total_after_discount": "400.00",
    "delivery_charge": "0.00",
    "tip_amount": "50.00",
    "final_total": "450.00",
    "items_count": 5
}
```

**Error Response (400 - Insufficient Stock):**
```json
{
    "error": "Insufficient stock for one or more products.",
    "stock_details": [
        {
            "product_id": 123,
            "product_name": "Fresh Fish",
            "requested_quantity": 5,
            "available_stock": 2
        }
    ]
}
```

**What It Shows:**
- `cart_total_before_discount` - Original cart value
- `discount_amount` - How much you save
- `cart_total_after_discount` - After coupon applied
- `delivery_charge` - Shipping (0 if >= 40, else 10)
- `tip_amount` - Optional tip
- `final_total` - What user pays

**Validations:**
- ✅ Stock availability checked for all cart items
- ✅ Returns detailed error if any product is out of stock

---

## 3️⃣ CREATE ORDER (CHECKOUT)

**Endpoint:**
```
POST /orders/checkout/
```

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

**Request:**
```json
{
    "address_id": 1,
    "coupon_code": "SAVE20",
    "tip_amount": 50.00,
    "payment_method": "TELR",
    "preferred_delivery_date": "2026-04-10",
    "preferred_delivery_slot": "9AM-12PM"
}
```

**Response (201):**
```json
{
    "message": "Order created successfully.",
    "order_id": 123,
    "payment_url": "https://telr.com/pay?ref=...",
    "total_amount": "450.00",
    "payment_method": "TELR"
}
```

**Payment Methods:**
- `TELR` - Redirect to payment URL
- `COD` - Cash on delivery (no URL)

---

## 4️⃣ GET ORDER DETAILS

**Endpoint:**
```
GET /orders/{order_id}/
```

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

**Response (200):**
```json
{
    "id": 123,
    "status": "PENDING",
    "total_amount": "450.00",
    "tip_amount": "50.00",
    "coupon_code": "SAVE20",
    "discount_amount": "100.00",
    "delivery_charge": "0.00",
    "items": [
        {
            "id": 1,
            "product_name": "Fresh Fish",
            "quantity": 2,
            "price": "150.00",
            "subtotal": "300.00"
        }
    ],
    "payment": {
        "transaction_id": "TXN123",
        "amount": "450.00",
        "status": "PENDING"
    }
}
```

---

## 5️⃣ DELIVERY CHARGE SETTINGS (ADMIN ONLY)

**GET Current Settings:**
```
GET /orders/delivery_charge_settings/
```

**Response (200):**
```json
{
    "min_free_shipping_amount": "40.00",
    "delivery_charge": "10.00",
    "is_active": true,
    "updated_at": "2026-03-29T10:30:00Z",
    "message": "Current delivery charge configuration"
}
```

**UPDATE Settings (Admin):**
```
POST /orders/delivery_charge_settings/

{
    "min_free_shipping_amount": 50.00,
    "delivery_charge": 8.00,
    "is_active": true
}
```

---

## 6️⃣ PAYMENT REFUND ENDPOINTS (ADMIN ONLY)

**Create Refund:**
```
POST /orders/payments/{payment_id}/create_refund/

{
    "amount": 100.00,
    "reason": "Customer request"
}
```

**Response (200):**
```json
{
    "refund_id": "REF123456789",
    "status": "INITIATED",
    "amount": "100.00",
    "message": "Refund initiated successfully"
}
```

**Get Refund Status:**
```
GET /orders/payments/{payment_id}/refund_status/
```

**Response (200):**
```json
{
    "refund_id": "REF123456789",
    "status": "COMPLETED",
    "amount": "100.00",
    "processed_at": "2024-01-15T14:30:00Z",
    "message": "Refund completed successfully"
}
```

**Notes:**
- Only admin users can access these endpoints
- Refunds are processed through Ziina Payment Gateway
- Status values: `INITIATED`, `PROCESSING`, `COMPLETED`, `FAILED`
- Amount must be less than or equal to original payment amount

---

## 7️⃣ PROMOTIONAL CONTENT API

**Get Delivery Offers:**
```
GET /marketing/promotional/delivery_offers/
```

**Response (200):**
```json
{
    "free_delivery_text": "Purchase for AED 40 or above for FREE delivery",
    "next_delivery_slot_text": "Order before 8:00 AM to get delivery between 11:00 - 12:00",
    "current_time": "2024-01-15T07:30:00+04:00"
}
```

**Notes:**
- Returns dynamic promotional texts based on current delivery settings
- Time-based delivery slot suggestions
- No authentication required (public endpoint)

---

### Order Status Values
```
"PENDING"      - Order created, waiting for payment
"PAID"         - Payment received
"PROCESSING"   - Being prepared
"SHIPPED"      - On way to customer
"DELIVERED"    - Received by customer
"CANCELLED"    - Cancelled by user/admin
```

### Payment Methods
```
"TELR"  - Credit/Debit card (online)
"COD"   - Cash on delivery
```

### Discount Types
```
"percentage"  - Discount is percentage (e.g., 20%)
"fixed"       - Discount is fixed amount (e.g., AED 100)
```

---

## 🔄 CALCULATION ORDER (IMPORTANT)

```
1. Cart Total (sum of items)
2. - Discount Amount (if coupon)
3. = After Discount
4. + Delivery Charge (calculated on step 3)
5. + Tip Amount
6. = Final Total
```

**Example:**
```
500.00 (cart) 
- 100.00 (discount)
= 400.00
+ 0.00 (delivery, because >= 40)
+ 50.00 (tip)
= 450.00 (final)
```

---

## ❌ HTTP STATUS CODES

| Code | Meaning |
|------|---------|
| 200 | Success (GET) |
| 201 | Created (POST order) |
| 400 | Bad request (validation error) |
| 401 | Unauthorized (need token) |
| 404 | Not found |
| 500 | Server error |

---

## 🛡️ AUTHENTICATION

All endpoints require JWT token in header:

```javascript
// Get token from login
const loginRes = await fetch('/api/users/login/', {
    method: 'POST',
    body: JSON.stringify({
        email: 'user@example.com',
        password: 'password'
    })
});

const { access } = await loginRes.json();

// Use in requests
const headers = {
    'Authorization': `Bearer ${access}`,
    'Content-Type': 'application/json'
};
```

---

## 💰 DELIVERY CHARGE RULES

```
Order Total (after discount)
├─ < AED 40.00 → Charge AED 10.00
└─ >= AED 40.00 → FREE (AED 0.00)
```

**Note**: Calculated AFTER coupon discount, BEFORE tip.

---

## ⚡ CURL EXAMPLES

### Validate Coupon
```bash
curl -X POST https://api.com/api/orders/validate_coupon/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "coupon_code": "SAVE20",
    "cart_total": 500.00
  }'
```

### Get Summary
```bash
curl -X POST https://api.com/api/orders/checkout_summary/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "address_id": 1,
    "coupon_code": "SAVE20",
    "tip_amount": 50
  }'
```

### Create Order
```bash
curl -X POST https://api.com/api/orders/checkout/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "address_id": 1,
    "coupon_code": "SAVE20",
    "tip_amount": 50,
    "payment_method": "TELR"
  }'
```

---

## 🧪 TEST DATA

**Test Coupons:**
- `SAVE20` - 20% off, min AED 0
- `WELCOME-USER-123` - 10% off first order
- `SUMMER20` - 20% off summer items

**Test Addresses:**
```
Address ID 1: Home Address
Address ID 2: Work Address
```

---

## 📱 JAVASCRIPT SNIPPETS

### Validate Coupon
```javascript
const validateCoupon = async (code, total) => {
    const res = await fetch('/api/orders/validate_coupon/', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${localStorage.token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            coupon_code: code,
            cart_total: total
        })
    });
    return res.json();
};
```

### Get Summary
```javascript
const getCheckoutSummary = async (addressId, coupon, tip) => {
    const res = await fetch('/api/orders/checkout_summary/', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${localStorage.token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            address_id: addressId,
            coupon_code: coupon || '',
            tip_amount: tip || 0
        })
    });
    return res.json();
};
```

### Create Order
```javascript
const createOrder = async (data) => {
    const res = await fetch('/api/orders/checkout/', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${localStorage.token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    });
    return res.json();
};
```

---

## 🔍 DEBUGGING CHECKLIST

- [ ] Token is valid and not expired
- [ ] Address ID belongs to current user
- [ ] Coupon code is spelled correctly
- [ ] Cart total is a valid number
- [ ] Payment method is TELR or COD
- [ ] All required fields are sent
- [ ] Headers include Authorization and Content-Type
- [ ] Response status is not 400/401/500

---

## 📞 SUPPORT

**HTTP 400 Bad Request:**
- Check all fields are sent correctly
- Verify coupon code spelling
- Ensure address belongs to user

**HTTP 401 Unauthorized:**
- Token is missing or expired
- Add Authorization header

**HTTP 404 Not Found:**
- Address doesn't exist
- Order ID is wrong

**HTTP 500 Server Error:**
- Backend issue - contact backend team

---

**Last Updated**: March 29, 2026
