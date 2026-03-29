# Frontend Integration Guide: Coupons & Delivery Charges

## 📋 Overview

This guide explains the **coupon system** and **delivery charge system** that have been integrated into the orders checkout flow. Both features automatically calculate discounts and shipping fees for your frontend.

---

## 🎯 **Quick Summary**

| Feature | Purpose | Complexity |
|---------|---------|-----------|
| **Coupons** | Apply discount codes to reduce order total | Medium |
| **Delivery Charges** | Automatic shipping fee calculation | Low |

---

## 📡 **API Endpoints Overview**

### **Coupon Endpoints**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/orders/validate_coupon/` | Validate & preview discount |
| POST | `/api/orders/checkout_summary/` | Get complete order breakdown |
| POST | `/api/orders/checkout/` | Create order (updated with coupon) |

### **Delivery Endpoints** (Admin Only)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/orders/delivery_charge_settings/` | Get current delivery settings |
| POST | `/api/orders/delivery_charge_settings/` | Update delivery settings (admin) |

---

## 🧭 **Core Workflow**

### **Step-by-Step Checkout Process**

```
1. User Adds Items to Cart
   ↓
2. Navigate to Checkout Page
   ↓
3. [OPTIONAL] Enter Coupon Code → Validate
   ↓
4. Show Order Summary (with discount & delivery)
   ↓
5. User Confirms
   ↓
6. Complete Checkout (create order)
   ↓
7. Payment Processing
```

---

## 💳 **Coupon System**

### **1️⃣ Validating a Coupon (Pre-Checkout)**

**Purpose**: Show user exactly how much they'll save BEFORE they complete checkout.

**Request:**
```bash
POST /api/orders/validate_coupon/
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN

{
    "coupon_code": "SAVE20",
    "cart_total": 500.00
}
```

**Successful Response** (Status 200):
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

**Error Response** (Status 400):
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

### **Error Messages You'll See:**

| Error | Meaning |
|-------|---------|
| `Coupon code "X" not found` | Code doesn't exist |
| `Coupon has expired` | Outside valid date range |
| `Coupon is not yet valid` | Before start date |
| `Coupon is inactive` | Admin disabled it |
| `Coupon usage limit reached` | Already used max times |
| `This coupon is not valid for your account` | Assigned to another user |
| `Minimum order amount of X required` | Order too small |

---

### **2️⃣ Showing Order Summary (Confirmation)**

**Purpose**: Display final breakdown with ALL charges before payment.

**Request:**
```bash
POST /api/orders/checkout_summary/
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN

{
    "address_id": 1,
    "coupon_code": "SAVE20",
    "tip_amount": 50,
    "preferred_delivery_date": "2026-04-10",
    "preferred_delivery_slot": "9AM-12PM"
}
```

**Response** (Status 200):
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

---

### **3️⃣ Creating Order with Coupon**

**Purpose**: Actually complete the order with the coupon applied.

**Request:**
```bash
POST /api/orders/checkout/
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN

{
    "address_id": 1,
    "coupon_code": "SAVE20",
    "tip_amount": 50,
    "payment_method": "TELR",
    "preferred_delivery_date": "2026-04-10",
    "preferred_delivery_slot": "9AM-12PM"
}
```

**Response** (Status 201):
```json
{
    "message": "Order created successfully.",
    "order_id": 123,
    "payment_url": "https://telr.com/pay?ref=...",
    "total_amount": "450.00",
    "payment_method": "TELR"
}
```

**Order also includes** (when you GET order):
```json
{
    "id": 123,
    "status": "PENDING",
    "total_amount": "450.00",
    "tip_amount": "50.00",
    "coupon_code": "SAVE20",
    "discount_amount": "100.00",
    "delivery_charge": "0.00",
    "items": [...]
}
```

---

## 🚚 **Delivery Charge System**

### **How It Works (Automatic)**

The delivery charge is **calculated automatically** when checkout is called.

**Rules:**
```
Order Total (after discount)    | Delivery Charge
==========================================
< AED 40                        | AED 10
>= AED 40                       | FREE (AED 0)
```

### **Examples:**

**Example 1: Small Order (Gets Charged)**
```
Cart:           AED 30
Discount:       -AED 0
After:          AED 30
Delivery:       +AED 10  ← CHARGED (order < 40)
Tip:            +AED 5
========================================
Final:          AED 45
```

**Example 2: Large Order (Free Shipping)**
```
Cart:           AED 100
Discount:       -AED 20
After:          AED 80
Delivery:       +AED 0   ← FREE (order >= 40)
Tip:            +AED 10
========================================
Final:          AED 90
```

**Example 3: Coupon Makes It Below Threshold**
```
Cart:           AED 50
Discount:       -AED 30 (coupon)
After:          AED 20
Delivery:       +AED 10  ← CHARGED (order < 40 after discount)
Tip:            +AED 5
========================================
Final:          AED 35
```

### **Important**: Delivery charge is based on **AFTER discount amount**, not original cart.

---

## 🛠️ **Frontend Implementation Steps**

### **Step 1: Display Cart Page**

Show:
- List of items
- Subtotal
- "Apply Coupon" input field (optional)

---

### **Step 2: Add Coupon Validation (Optional)**

Add an input field where user can paste coupon code:

```html
<!-- HTML Example -->
<input 
    type="text" 
    id="couponInput" 
    placeholder="Enter coupon code"
/>
<button onclick="validateCoupon()">Apply Coupon</button>
<div id="discountMessage"></div>
```

```javascript
// JavaScript Example
async function validateCoupon() {
    const couponCode = document.getElementById('couponInput').value;
    const cartTotal = calculateCartTotal(); // Your cart calculation
    
    try {
        const response = await fetch('/api/orders/validate_coupon/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({
                coupon_code: couponCode,
                cart_total: cartTotal
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Show discount details
            document.getElementById('discountMessage').innerHTML = `
                <p style="color: green;">
                    ✓ Coupon applied! You save: AED ${data.discount_amount}
                </p>
            `;
            // Store coupon for later use
            localStorage.setItem('selectedCoupon', couponCode);
        } else {
            document.getElementById('discountMessage').innerHTML = `
                <p style="color: red;">
                    ✗ ${data.message}
                </p>
            `;
        }
    } catch (error) {
        console.error('Error validating coupon:', error);
    }
}
```

---

### **Step 3: Show Order Summary (Before Payment)**

Before proceeding to payment, call `checkout_summary` to show final breakdown:

```javascript
async function showOrderSummary() {
    const addressId = document.getElementById('addressSelect').value;
    const couponCode = localStorage.getItem('selectedCoupon') || '';
    const tipAmount = document.getElementById('tipInput').value || 0;
    
    try {
        const response = await fetch('/api/orders/checkout_summary/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({
                address_id: addressId,
                coupon_code: couponCode,
                tip_amount: tipAmount,
                preferred_delivery_date: '2026-04-10',
                preferred_delivery_slot: '9AM-12PM'
            })
        });
        
        const data = await response.json();
        
        // Display breakdown
        document.getElementById('summary').innerHTML = `
            <div class="order-summary">
                <p>Subtotal: AED ${data.cart_total_before_discount}</p>
                ${data.discount_amount > 0 ? `
                    <p style="color: green;">
                        Discount (${data.discount_code}): -AED ${data.discount_amount}
                    </p>
                ` : ''}
                <hr>
                <p>After Discount: AED ${data.cart_total_after_discount}</p>
                ${data.delivery_charge > 0 ? `
                    <p>Delivery Charge: AED ${data.delivery_charge}</p>
                ` : `
                    <p style="color: green;">Delivery: FREE ✓</p>
                `}
                <p>Tip: AED ${data.tip_amount}</p>
                <hr>
                <h3>Total: AED ${data.final_total}</h3>
            </div>
        `;
    } catch (error) {
        console.error('Error fetching summary:', error);
    }
}
```

---

### **Step 4: Complete Checkout**

When user clicks "Pay Now", call the checkout endpoint:

```javascript
async function completeCheckout() {
    const addressId = document.getElementById('addressSelect').value;
    const couponCode = localStorage.getItem('selectedCoupon') || '';
    const tipAmount = document.getElementById('tipInput').value || 0;
    const paymentMethod = document.querySelector('input[name="payment"]:checked').value;
    
    try {
        const response = await fetch('/api/orders/checkout/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({
                address_id: addressId,
                coupon_code: couponCode,
                tip_amount: tipAmount,
                payment_method: paymentMethod,
                preferred_delivery_date: '2026-04-10',
                preferred_delivery_slot: '9AM-12PM'
            })
        });
        
        const data = await response.json();
        
        if (data.order_id) {
            if (paymentMethod === 'TELR') {
                // Redirect to payment
                window.location.href = data.payment_url;
            } else if (paymentMethod === 'COD') {
                // Show confirmation
                alert('Order created! Pay upon delivery.');
                window.location.href = `/order/${data.order_id}`;
            }
        }
    } catch (error) {
        console.error('Error completing checkout:', error);
    }
}
```

---

## 📝 **Form Example**

Here's a simple checkout form:

```html
<form onsubmit="completeCheckout(event)">
    <!-- Address Selection -->
    <div class="form-group">
        <label>Delivery Address:</label>
        <select id="addressSelect" required>
            <option value="">Select address...</option>
            <option value="1">Home (Main Street)</option>
            <option value="2">Office (Downtown)</option>
        </select>
    </div>

    <!-- Coupon Code -->
    <div class="form-group">
        <label>Coupon Code (Optional):</label>
        <div class="input-group">
            <input 
                type="text" 
                id="couponInput" 
                placeholder="e.g., SAVE20"
            />
            <button type="button" onclick="validateCoupon()">
                Apply
            </button>
        </div>
        <div id="discountMessage"></div>
    </div>

    <!-- Delivery Preferences -->
    <div class="form-group">
        <label>Preferred Delivery Date:</label>
        <input type="date" name="date" required/>
    </div>

    <div class="form-group">
        <label>Preferred Delivery Slot:</label>
        <select name="slot" required>
            <option value="9AM-12PM">9AM - 12PM</option>
            <option value="2PM-5PM">2PM - 5PM</option>
            <option value="6PM-9PM">6PM - 9PM</option>
        </select>
    </div>

    <!-- Tip Amount -->
    <div class="form-group">
        <label>Tip (Optional):</label>
        <input 
            type="number" 
            id="tipInput" 
            placeholder="0.00"
            step="0.01"
            min="0"
        />
    </div>

    <!-- Payment Method -->
    <div class="form-group">
        <label>Payment Method:</label>
        <input type="radio" name="payment" value="TELR" checked/> Card
        <input type="radio" name="payment" value="COD"/> Cash on Delivery
    </div>

    <!-- Order Summary (before submit) -->
    <div id="summary"></div>

    <!-- Submit -->
    <button type="submit">Complete Order</button>
</form>

<script>
function completeCheckout(event) {
    event.preventDefault();
    showOrderSummary().then(() => {
        // After summary is shown, ask for confirmation
        if (confirm('Confirm this order?')) {
            // Call checkout API
        }
    });
}
</script>
```

---

## ✅ **Checklist for Frontend Implementation**

- [ ] Add coupon input field on checkout page
- [ ] Add validate coupon button
- [ ] Call `/validate_coupon/` when user enters code
- [ ] Display discount message (success/error)
- [ ] Add "Show Summary" button before payment
- [ ] Call `/checkout_summary/` to fetch breakdown
- [ ] Display: subtotal, discount, delivery charge, tip, **final total**
- [ ] Implement checkout form with all fields
- [ ] Call `/checkout/` API on form submit
- [ ] Handle both TELR (redirect to payment_url) and COD responses
- [ ] Show order confirmation page

---

## 🔐 **Authentication**

All endpoints except public ones require:
```
Authorization: Bearer YOUR_JWT_TOKEN
```

Get your token from login:
```javascript
const loginResponse = await fetch('/api/users/login/', {
    method: 'POST',
    body: JSON.stringify({
        email: 'user@example.com',
        password: 'password'
    })
});

const { access } = await loginResponse.json();
localStorage.setItem('token', access);
```

---

## 🧪 **Test Coupons**

Ask the backend team for test coupon codes:
- `SAVE20` - 20% off
- `WELCOME-USER-123` - Welcome coupon
- `SUMMER20` - Summer sale

---

## 📊 **Response Structure Reference**

### **Validate Coupon Response**
```json
{
    "success": boolean,
    "message": string,
    "coupon_code": string,
    "discount_amount": string (decimal),
    "discount_type": "percentage" | "fixed",
    "discount_percentage": number (optional),
    "cart_total": string (decimal),
    "final_amount": string (decimal)
}
```

### **Checkout Summary Response**
```json
{
    "success": boolean,
    "cart_total_before_discount": string,
    "discount_amount": string,
    "discount_type": string | null,
    "discount_code": string | null,
    "coupon_message": string | null,
    "cart_total_after_discount": string,
    "delivery_charge": string,
    "tip_amount": string,
    "final_total": string,
    "items_count": number
}
```

### **Checkout Response**
```json
{
    "message": string,
    "order_id": number,
    "payment_url": string (only for TELR),
    "total_amount": string,
    "payment_method": "TELR" | "COD"
}
```

### **Order Details Response** (GET /api/orders/{id}/)
```json
{
    "id": number,
    "status": string,
    "total_amount": string,
    "tip_amount": string,
    "coupon_code": string | null,
    "discount_amount": string,
    "delivery_charge": string,
    "items": [...],
    "payment": {...}
}
```

---

## 🐛 **Debugging Tips**

1. **Check Browser Console**: Look for network errors
2. **Verify Token**: Make sure you're sending valid JWT
3. **Check Address**: Make sure address_id belongs to current user
4. **Minimum Order**: Some coupons require minimum amount
5. **Test Coupon First**: Use validate endpoint before checkout

---

## 🔄 **Common Flows**

### **Flow 1: Simple Checkout (No Coupon)**
```
Cart Page
  ↓
Checkout Page (address, tip, date)
  ↓
POST /checkout_summary/ (no coupon_code)
  ↓
Show Summary
  ↓
POST /checkout/ (no coupon_code)
  ↓
Pay or Confirm
```

### **Flow 2: With Coupon**
```
Cart Page (show coupon input)
  ↓
User enters code → POST /validate_coupon/
  ↓
Show discount preview
  ↓
Checkout Page
  ↓
POST /checkout_summary/ (with coupon_code)
  ↓
Show Summary (with discount line)
  ↓
POST /checkout/ (with coupon_code)
  ↓
Pay or Confirm
```

### **Flow 3: Coupon Validation Error**
```
User enters invalid code
  ↓
POST /validate_coupon/ → success: false
  ↓
Show error message
  ↓
User can retry or skip coupon
  ↓
Continue checkout without coupon
```

---

## 💡 **Best Practices**

1. **Always validate before checkout** - Don't assume coupon is valid
2. **Show delivery preview** - Let users see if they get free shipping
3. **Clear error messages** - Tell users why coupon failed
4. **Store coupon in session** - Don't ask again on summary page
5. **Handle network errors** - Show retry options
6. **Mobile friendly** - Ensure all inputs work on small screens
7. **Accessibility** - Use proper labels and ARIA attributes

---

## 📞 **Support**

If you encounter issues:
1. Check the API response status code
2. Look at error message in response
3. Verify all required fields are sent
4. Check that user is authenticated
5. Ensure address belongs to current user

---

## 🚀 **Summary**

**You now have:**
- ✅ Coupon validation with preview
- ✅ Order summary with breakdowns
- ✅ Automatic delivery charge calculation
- ✅ Flexible checkout with multiple payment methods

**Frontend needs to:**
1. Add coupon input & validation
2. Show order summary before payment
3. Call checkout with coupon code
4. Handle payment/delivery confirmation

---

**Version**: 1.0  
**Last Updated**: March 29, 2026  
**Backend Ready**: ✓ Yes
