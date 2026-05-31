# Coupons & Rewards API � Request / Response Reference

Complete JSON examples for coupon validation, checkout, user wallet, referral rewards, and admin management.

**Base URL:** `https://simakfresh.ae` (or your server origin)

**Auth header (protected endpoints):**
```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

---

## Table of contents

1. [Coupon model fields](#coupon-model-fields)
2. [Discount calculation](#discount-calculation)
3. [User � My coupons](#1-user--my-coupons)
4. [User � Apply referral code](#2-user--apply-referral-code)
5. [Orders � Validate coupon](#3-orders--validate-coupon)
6. [Orders � Checkout summary](#4-orders--checkout-summary)
7. [Orders � Checkout (place order)](#5-orders--checkout-place-order)
8. [Orders � Order detail (coupon fields)](#6-orders--order-detail-coupon-fields)
9. [Admin � Coupons CRUD](#7-admin--coupons-crud)
10. [Admin � Coupon actions](#8-admin--coupon-actions)
11. [Admin � Coupon stats](#9-admin--coupon-stats)
12. [Admin � Reward configuration](#10-admin--reward-configuration)
13. [Error responses](#error-responses)

---

## Coupon model fields

| Field | Type | Description |
|-------|------|-------------|
| `code` | string | Unique code (auto-uppercased on validate/checkout) |
| `discount_type` | `"percentage"` \| `"fixed"` | How discount is calculated |
| `discount_value` | decimal string | % (0�100) or fixed AED amount |
| `min_order_amount` | decimal string | Minimum cart subtotal before discount |
| `max_discount_amount` | decimal string \| null | **Cap in AED** for `%` coupons only |
| `valid_from` / `valid_to` | ISO datetime | Validity window (`valid_to` null = no expiry) |
| `usage_limit` | int \| null | Max redemptions (`null` = unlimited) |
| `used_count` | int | Times used (read-only) |
| `assigned_user` | user id \| null | If set, only that user may use the coupon |
| `is_active` | boolean | Must be `true` to apply |
| `is_referral_reward` | boolean | System flag |
| `is_first_order_reward` | boolean | System flag |

---

## Discount calculation

**Percentage** (with optional cap):

```
raw_discount = cart_total � (discount_value / 100)
if max_discount_amount:
    discount = min(raw_discount, max_discount_amount)
else:
    discount = raw_discount
discount = min(discount, cart_total)
```

**Example:** 10% off, cart **AED 1,000**, `max_discount_amount` = **50**

| Step | Value |
|------|-------|
| Raw 10% | AED 100 |
| After cap | **AED 50** |
| Final cart | AED 950 |

**Fixed:** `discount = min(discount_value, cart_total)`

---

## 1. User � My coupons

List coupons assigned to the logged-in user (welcome, referral, admin-assigned).

```http
GET /api/marketing/coupons/
Authorization: Bearer <token>
```

### Response `200 OK`

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 42,
      "code": "WELCOME-504-a3f2",
      "description": "Welcome Gift! Enjoy a discount on your first order.",
      "discount_type": "percentage",
      "discount_value": "10.00",
      "min_order_amount": "50.00",
      "max_discount_amount": null,
      "valid_from": "2026-05-29T05:48:06.730290Z",
      "valid_to": "2026-06-28T05:48:06.730290Z",
      "is_active": true,
      "usage_limit": 1,
      "used_count": 0,
      "assigned_user": 504,
      "is_referral_reward": false,
      "is_first_order_reward": true,
      "created_at": "2026-05-29T05:48:06.730290Z"
    },
    {
      "id": 43,
      "code": "REF-E-504-b7c1",
      "description": "Referral Bonus for joining via friend@example.com",
      "discount_type": "percentage",
      "discount_value": "15.00",
      "min_order_amount": "100.00",
      "max_discount_amount": "75.00",
      "valid_from": "2026-05-29T05:48:06.730290Z",
      "valid_to": "2026-07-28T05:48:06.730290Z",
      "is_active": true,
      "usage_limit": 1,
      "used_count": 0,
      "assigned_user": 504,
      "is_referral_reward": true,
      "is_first_order_reward": false,
      "created_at": "2026-05-29T05:48:07.102000Z"
    }
  ]
}
```

### Get one coupon

```http
GET /api/marketing/coupons/42/
Authorization: Bearer <token>
```

### Response `200 OK`

```json
{
  "id": 42,
  "code": "WELCOME-504-a3f2",
  "description": "Welcome Gift! Enjoy a discount on your first order.",
  "discount_type": "percentage",
  "discount_value": "10.00",
  "min_order_amount": "50.00",
  "max_discount_amount": null,
  "valid_from": "2026-05-29T05:48:06.730290Z",
  "valid_to": "2026-06-28T05:48:06.730290Z",
  "is_active": true,
  "usage_limit": 1,
  "used_count": 0,
  "assigned_user": 504,
  "is_referral_reward": false,
  "is_first_order_reward": true,
  "created_at": "2026-05-29T05:48:06.730290Z"
}
```

### Response `401 Unauthorized`

```json
{
  "detail": "Authentication credentials were not provided."
}
```

---

## 2. User � Apply referral code

Grants referral coupons to referrer and referee when a valid code is applied.

```http
POST /api/marketing/coupons/apply_referral/
Authorization: Bearer <token>
Content-Type: application/json
```

### Request body

```json
{
  "referral_code": "AB12CD34"
}
```

### Response `200 OK`

```json
{
  "detail": "Referral code applied successfully. Coupons granted!"
}
```

### Response `400 Bad Request` � already referred

```json
{
  "detail": "You have already been referred."
}
```

### Response `400 Bad Request` � self-referral

```json
{
  "detail": "You cannot refer yourself."
}
```

### Response `404 Not Found` � invalid code

```json
{
  "detail": "Invalid referral code."
}
```

---

## 3. Orders � Validate coupon

Preview discount before checkout. **Requires authenticated user with items in cart logic only via `cart_total` in body** (cart is not loaded; you send the total).

```http
POST /api/orders/validate_coupon/
Authorization: Bearer <token>
Content-Type: application/json
```

### Request body

```json
{
  "coupon_code": "SAVE10",
  "cart_total": "1000.00"
}
```

### Response `200 OK` � valid percentage coupon (with cap)

Coupon: **10%**, `max_discount_amount` = **50**, cart **1000**

```json
{
  "success": true,
  "message": "Coupon \"SAVE10\" is valid. Discount: 50.00",
  "coupon_code": "SAVE10",
  "discount_amount": "50.00",
  "discount_type": "percentage",
  "discount_percentage": 10.0,
  "cart_total": "1000.00",
  "final_amount": "950.00"
}
```

### Response `200 OK` � valid fixed coupon

Coupon: **AED 25** off, cart **200**

```json
{
  "success": true,
  "message": "Coupon \"FLAT25\" is valid. Discount: 25.00",
  "coupon_code": "FLAT25",
  "discount_amount": "25.00",
  "discount_type": "fixed",
  "cart_total": "200.00",
  "final_amount": "175.00"
}
```

### Response `400 Bad Request` � invalid / expired coupon

```json
{
  "success": false,
  "message": "Coupon has expired",
  "coupon_code": "SAVE10",
  "discount_amount": "0.00",
  "discount_type": "percentage",
  "cart_total": "1000.00",
  "final_amount": "1000.00"
}
```

Other possible `message` values:

- `"Coupon is inactive"`
- `"Coupon is not yet valid"`
- `"Coupon usage limit reached"`
- `"This coupon is not valid for your account"`
- `"Minimum order amount of 100.00 required"`
- `"Coupon code \"XYZ\" not found."`

### Response `400 Bad Request` � missing fields

```json
{
  "error": "coupon_code is required."
}
```

```json
{
  "error": "cart_total must be greater than 0."
}
```

---

## 4. Orders � Checkout summary

Full price breakdown from the **server cart** (address required). Invalid coupon does **not** fail the request; see `coupon_message`.

```http
POST /api/orders/checkout_summary/
Authorization: Bearer <token>
Content-Type: application/json
```

### Request body

```json
{
  "address_id": 12,
  "coupon_code": "SAVE10",
  "tip_amount": "10.00",
  "preferred_delivery_date": "2026-05-30",
  "preferred_delivery_slot": 3
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `address_id` | Yes | User's saved address |
| `coupon_code` | No | Uppercased automatically |
| `tip_amount` | No | Default `0` |
| `preferred_delivery_date` | No | `YYYY-MM-DD` |
| `preferred_delivery_slot` | No | Delivery time slot ID |

### Response `200 OK` � coupon applied

```json
{
  "success": true,
  "cart_total_before_discount": "1000.00",
  "discount_amount": "50.00",
  "discount_type": "percentage",
  "discount_code": "SAVE10",
  "coupon_message": null,
  "cart_total_after_discount": "950.00",
  "delivery_charge": "0.00",
  "tip_amount": "10.00",
  "final_total": "960.00",
  "items_count": 4
}
```

`final_total` = `cart_total_after_discount` + `delivery_charge` + `tip_amount`

### Response `200 OK` � invalid coupon (warning only)

```json
{
  "success": true,
  "cart_total_before_discount": "1000.00",
  "discount_amount": "0.00",
  "discount_type": null,
  "discount_code": "BADCODE",
  "coupon_message": "Warning: Coupon code \"BADCODE\" not found.",
  "cart_total_after_discount": "1000.00",
  "delivery_charge": "15.00",
  "tip_amount": "0.00",
  "final_total": "1015.00",
  "items_count": 4
}
```

### Response `400 Bad Request` � phone not verified

```json
{
  "error": "Only verified users with a phone number can purchase products."
}
```

### Response `400 Bad Request` � empty cart

```json
{
  "error": "Cart is empty."
}
```

### Response `400 Bad Request` � insufficient stock

```json
{
  "error": "Insufficient stock for one or more products.",
  "stock_details": [
    {
      "product_id": 5,
      "product_name": "Salmon Fillet",
      "requested_quantity": 3,
      "available_stock": 1
    }
  ]
}
```

---

## 5. Orders � Checkout (place order)

Creates the order. **Invalid coupon blocks checkout** (unlike `checkout_summary`).

```http
POST /api/orders/checkout/
Authorization: Bearer <token>
Content-Type: application/json
```

### Request body � card / Ziina

```json
{
  "address_id": 12,
  "coupon_code": "SAVE10",
  "tip_amount": "10.00",
  "payment_method": "ZIINA",
  "device": "ios",
  "preferred_delivery_date": "2026-05-30",
  "preferred_delivery_slot": 3,
  "delivery_notes": "Ring the bell"
}
```

### Request body � cash on delivery

```json
{
  "address_id": 12,
  "coupon_code": "SAVE10",
  "tip_amount": "10.00",
  "payment_method": "COD",
  "preferred_delivery_date": "2026-05-30",
  "preferred_delivery_slot": 3
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `payment_method` | No | `"ZIINA"` (default) or `"COD"` |
| `device` | No | `"mobile"`, `"android"`, `"ios"` ? app payment URLs for Ziina |

### Response `201 Created` � Ziina

```json
{
  "message": "Order created successfully.",
  "order_id": 128,
  "payment_url": "https://pay.ziina.com/...",
  "total_amount": "960.00",
  "payment_method": "ZIINA"
}
```

### Response `201 Created` � COD

```json
{
  "message": "Order created successfully. Please pay upon delivery.",
  "order_id": 128,
  "total_amount": "960.00",
  "payment_method": "COD"
}
```

### Response `400 Bad Request` � coupon error

```json
{
  "error": "Coupon error: Minimum order amount of 100.00 required"
}
```

### Response `400 Bad Request` � coupon not found

```json
{
  "error": "Coupon error: Coupon code \"BADCODE\" not found."
}
```

> **Note:** On successful checkout with a coupon, the coupon is marked `is_active: false` and `used_count` is incremented immediately (single-use behavior per checkout in current code).

---

## 6. Orders � Order detail (coupon fields)

```http
GET /api/orders/128/
Authorization: Bearer <token>
```

### Response `200 OK` (coupon-related fields)

```json
{
  "id": 128,
  "status": "PENDING",
  "total_amount": "960.00",
  "tip_amount": "10.00",
  "coupon": 15,
  "coupon_code": "SAVE10",
  "discount_amount": "50.00",
  "delivery_charge": "0.00",
  "items": [],
  "created_at": "2026-05-29T10:00:00Z"
}
```

---

## 7. Admin � Coupons CRUD

**Permission:** `IsAdminUser` (`is_staff=True`)

### List coupons

```http
GET /api/marketing/admin/coupons/?is_active=true&discount_type=percentage&search=SAVE
Authorization: Bearer <admin_token>
```

### Response `200 OK`

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 15,
      "code": "SAVE10",
      "description": "10% off � max AED 50 discount",
      "discount_type": "percentage",
      "discount_value": "10.00",
      "min_order_amount": "50.00",
      "max_discount_amount": "50.00",
      "valid_from": "2026-05-01T00:00:00Z",
      "valid_to": "2026-12-31T23:59:59Z",
      "is_active": true,
      "usage_limit": 1000,
      "used_count": 12,
      "assigned_user": null,
      "assigned_user_email": null,
      "is_referral_reward": false,
      "is_first_order_reward": false,
      "created_at": "2026-05-01T08:00:00Z",
      "updated_at": "2026-05-15T12:00:00Z",
      "deleted_at": null
    }
  ]
}
```

### Create coupon (10% with max discount cap)

```http
POST /api/marketing/admin/coupons/
Authorization: Bearer <admin_token>
Content-Type: application/json
```

#### Request body

```json
{
  "code": "SAVE10",
  "description": "10% off � maximum AED 50 discount",
  "discount_type": "percentage",
  "discount_value": "10.00",
  "min_order_amount": "50.00",
  "max_discount_amount": "50.00",
  "valid_from": "2026-05-01T00:00:00Z",
  "valid_to": "2026-12-31T23:59:59Z",
  "is_active": true,
  "usage_limit": 1000,
  "assigned_user": null,
  "is_referral_reward": false,
  "is_first_order_reward": false
}
```

#### Response `201 Created`

```json
{
  "id": 15,
  "code": "SAVE10",
  "description": "10% off � maximum AED 50 discount",
  "discount_type": "percentage",
  "discount_value": "10.00",
  "min_order_amount": "50.00",
  "max_discount_amount": "50.00",
  "valid_from": "2026-05-01T00:00:00Z",
  "valid_to": "2026-12-31T23:59:59Z",
  "is_active": true,
  "usage_limit": 1000,
  "used_count": 0,
  "assigned_user": null,
  "assigned_user_email": null,
  "is_referral_reward": false,
  "is_first_order_reward": false,
  "created_at": "2026-05-29T10:30:00Z",
  "updated_at": "2026-05-29T10:30:00Z",
  "deleted_at": null
}
```

### Create fixed-amount coupon

#### Request body

```json
{
  "code": "FLAT25",
  "description": "AED 25 off orders over AED 100",
  "discount_type": "fixed",
  "discount_value": "25.00",
  "min_order_amount": "100.00",
  "max_discount_amount": null,
  "valid_from": "2026-05-01T00:00:00Z",
  "valid_to": null,
  "is_active": true,
  "usage_limit": null,
  "assigned_user": 504,
  "is_referral_reward": false,
  "is_first_order_reward": false
}
```

### Update coupon (partial)

```http
PATCH /api/marketing/admin/coupons/15/
Authorization: Bearer <admin_token>
Content-Type: application/json
```

#### Request body

```json
{
  "max_discount_amount": "75.00",
  "usage_limit": 500
}
```

#### Response `200 OK`

```json
{
  "id": 15,
  "code": "SAVE10",
  "description": "10% off � maximum AED 50 discount",
  "discount_type": "percentage",
  "discount_value": "10.00",
  "min_order_amount": "50.00",
  "max_discount_amount": "75.00",
  "valid_from": "2026-05-01T00:00:00Z",
  "valid_to": "2026-12-31T23:59:59Z",
  "is_active": true,
  "usage_limit": 500,
  "used_count": 12,
  "assigned_user": null,
  "assigned_user_email": null,
  "is_referral_reward": false,
  "is_first_order_reward": false,
  "created_at": "2026-05-01T08:00:00Z",
  "updated_at": "2026-05-29T11:00:00Z",
  "deleted_at": null
}
```

### Delete coupon

```http
DELETE /api/marketing/admin/coupons/15/
Authorization: Bearer <admin_token>
```

#### Response `204 No Content`

(empty body)

---

## 8. Admin � Coupon actions

### Soft delete

```http
POST /api/marketing/admin/coupons/15/soft_delete/
Authorization: Bearer <admin_token>
```

#### Response `200 OK`

```json
{
  "detail": "Coupon soft deleted successfully."
}
```

### Restore

```http
POST /api/marketing/admin/coupons/15/restore/
Authorization: Bearer <admin_token>
```

#### Response `200 OK`

```json
{
  "detail": "Coupon restored successfully."
}
```

### Deactivate

```http
POST /api/marketing/admin/coupons/15/deactivate/
Authorization: Bearer <admin_token>
```

#### Response `200 OK`

```json
{
  "detail": "Coupon deactivated successfully.",
  "is_active": false
}
```

### Activate

```http
POST /api/marketing/admin/coupons/15/activate/
Authorization: Bearer <admin_token>
```

#### Response `200 OK`

```json
{
  "detail": "Coupon activated successfully.",
  "is_active": true
}
```

---

## 9. Admin � Coupon stats

```http
GET /api/marketing/admin/coupons/stats/
Authorization: Bearer <admin_token>
```

### Response `200 OK`

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

## 10. Admin � Reward configuration

Singleton settings for auto-generated welcome/referral coupons (stored in DB; auto-coupon creation uses hardcoded defaults in `Marketing/services.py` unless updated separately).

### Get configuration

```http
GET /api/marketing/admin/rewards/
Authorization: Bearer <admin_token>
```

### Response `200 OK`

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
  "updated_by_email": "admin@simakfresh.ae",
  "updated_at": "2026-05-29T08:00:00Z"
}
```

### Update configuration (partial)

```http
PATCH /api/marketing/admin/rewards/
Authorization: Bearer <admin_token>
Content-Type: application/json
```

#### Request body

```json
{
  "first_order_discount_value": "15.00",
  "referral_discount_value": "20.00",
  "max_discount_percentage": "100.00",
  "is_referral_active": true
}
```

#### Response `200 OK`

```json
{
  "detail": "Reward configuration updated successfully.",
  "config": {
    "first_order_discount_type": "percentage",
    "first_order_discount_value": "15.00",
    "first_order_min_amount": "50.00",
    "first_order_validity_days": 30,
    "referral_discount_type": "percentage",
    "referral_discount_value": "20.00",
    "referral_min_amount": "100.00",
    "referral_validity_days": 60,
    "referral_usage_limit": 1,
    "referrer_discount_value": "15.00",
    "referrer_validity_days": 60,
    "max_discount_percentage": "100.00",
    "is_referral_active": true,
    "is_first_order_active": true,
    "updated_by": 1,
    "updated_by_email": "admin@simakfresh.ae",
    "updated_at": "2026-05-29T11:30:00Z"
  }
}
```

> `max_discount_percentage` on reward config is **not** applied automatically at checkout today. Use per-coupon `max_discount_amount` for enforced caps.

---

## Error responses

### `401 Unauthorized`

```json
{
  "detail": "Authentication credentials were not provided."
}
```

### `403 Forbidden` (admin endpoints)

```json
{
  "detail": "You do not have permission to perform this action."
}
```

### `400 Bad Request` (admin validation)

```json
{
  "discount_value": [
    "Percentage discount must be between 0 and 100."
  ]
}
```

### `404 Not Found`

```json
{
  "detail": "Not found."
}
```

---

## Quick reference � all endpoints

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| `GET` | `/api/marketing/coupons/` | User | List my coupons |
| `GET` | `/api/marketing/coupons/{id}/` | User | Coupon detail |
| `POST` | `/api/marketing/coupons/apply_referral/` | User | Apply referral code |
| `POST` | `/api/orders/validate_coupon/` | User | Preview discount |
| `POST` | `/api/orders/checkout_summary/` | User | Full checkout breakdown |
| `POST` | `/api/orders/checkout/` | User | Place order with coupon |
| `GET` | `/api/orders/{id}/` | User | Order with coupon fields |
| `GET` | `/api/marketing/admin/coupons/` | Admin | List all coupons |
| `POST` | `/api/marketing/admin/coupons/` | Admin | Create coupon |
| `GET/PATCH/PUT/DELETE` | `/api/marketing/admin/coupons/{id}/` | Admin | CRUD single coupon |
| `POST` | `/api/marketing/admin/coupons/{id}/soft_delete/` | Admin | Soft delete |
| `POST` | `/api/marketing/admin/coupons/{id}/restore/` | Admin | Restore |
| `POST` | `/api/marketing/admin/coupons/{id}/activate/` | Admin | Activate |
| `POST` | `/api/marketing/admin/coupons/{id}/deactivate/` | Admin | Deactivate |
| `GET` | `/api/marketing/admin/coupons/stats/` | Admin | Statistics |
| `GET/PATCH/PUT` | `/api/marketing/admin/rewards/` | Admin | Reward config |

---

## Related files

- `Marketing/models.py` � `Coupon`, `RewardConfiguration`
- `Orders/coupon_service.py` � validation & discount math
- `Marketing/ADMIN_COUPONS_API.md` � admin-focused supplement
- `COUPON_IMPLEMENTATION.md` � implementation notes
