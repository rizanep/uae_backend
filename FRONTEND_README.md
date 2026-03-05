# Frontend API Documentation

This document outlines the recent API updates and integration details for the frontend team.

## 1. Authentication & User Status

### Inactive User Handling
All authentication endpoints (Login, OTP Request, etc.) now check if the user is active.
- **Status Code**: `403 Forbidden`
- **Response Body**:
  ```json
  {
    "detail": "user is inactive pls contact support"
  }
  ```
- **Action**: If this error is received, redirect the user to a support contact page or show a modal explaining their account is inactive.

## 2. Products & Tiers

The product list API now includes tier information for delivery times and discounts based on quantity.

### Endpoint
- `GET /api/products/`
- `GET /api/products/{id}/`

### Response Fields
Each product object now includes:
- `delivery_tiers`: Array of rules for delivery time based on quantity.
- `discount_tiers`: Array of rules for discounts based on quantity.

**Example Product Object**:
```json
{
  "id": 1,
  "name": "Fresh Salmon",
  "price": "100.00",
  "stock": 50,
  "delivery_tiers": [
    {
      "min_quantity": 1,
      "delivery_days": 1
    },
    {
      "min_quantity": 10,
      "delivery_days": 3
    }
  ],
  "discount_tiers": [
    {
      "min_quantity": 5,
      "discount_percentage": "5.00"
    },
    {
      "min_quantity": 10,
      "discount_percentage": "10.00"
    }
  ]
}
```

## 3. Cart & Delivery Estimation

Before checkout, you can request an estimated delivery date based on the items currently in the user's cart. This calculation considers the `delivery_tiers` of all products in the cart.

### Estimate Delivery Endpoint
- **URL**: `/api/orders/estimate_delivery/`
- **Method**: `GET`
- **Auth**: Required

**Response**:
```json
{
  "estimated_delivery_date": "2023-10-25",
  "max_delivery_days": 3,
  "details": [
    {
      "product_id": 1,
      "product_name": "Fresh Salmon",
      "quantity": 12,
      "estimated_days": 3,
      "source": "tier"
    }
  ]
}
```

## 4. Orders & Checkout

### Checkout Endpoint
Create a new order from the user's cart.

- **URL**: `/api/orders/checkout/`
- **Method**: `POST`
- **Auth**: Required

**Request Body**:
```json
{
  "address_id": 1,
  "payment_method": "TELR",  // or "COD"
  "tip_amount": 10.00,       // Optional
  "preferred_delivery_date": "2023-10-26", // Optional (YYYY-MM-DD)
  "preferred_delivery_slot": "Morning",    // Optional
  "delivery_notes": "Leave at door"        // Optional
}
```

**Validation Notes**:
- `preferred_delivery_date`: Must be equal to or later than the `estimated_delivery_date`. If earlier, returns `400 Bad Request`.
- `tip_amount`: Added to the total.

**Response (Success)**:
```json
{
  "message": "Order created successfully.",
  "order_id": 123,
  "total_amount": 150.00,
  "payment_method": "TELR",
  "payment_url": "https://secure.telr.com/gateway/..." // Only for TELR
}
```

### Order Receipts
Once an order is paid (status `PAID` or `DELIVERED`), users can download receipts.

- **Image Receipt**: `GET /api/orders/{id}/receipt_image/` (Returns `image/png`)
- **PDF Receipt**: `GET /api/orders/{id}/receipt_pdf/` (Returns `application/pdf`)

## 5. Admin & Management

### Dashboard Analytics
- **URL**: `/api/orders/dashboard_analytics/`
- **Method**: `GET`
- **Auth**: Admin only
- **Data**: Returns aggregate data for users, orders, revenue, and top products.

### Update Order Status
- **URL**: `/api/orders/{id}/admin_update_status/`
- **Method**: `POST`
- **Body**: `{"status": "shipped", "notes": "Optional note"}`
