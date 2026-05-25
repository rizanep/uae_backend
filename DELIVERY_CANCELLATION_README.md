# Delivery Cancellation Request

This document explains how the delivery cancellation request system works — from submission by the delivery boy through admin review and the final outcome on the order.

---

## Overview

When a delivery cannot be completed (e.g. damaged product, customer unavailable, stock issue), the **delivery boy** submits a cancellation request. The request waits for **admin approval or rejection** before the order status changes. The customer always sees the latest order state and any attached cancel request.

---

## Status Flow

```
Order: SHIPPED or DELIVERED
        │
        ▼
Delivery Boy submits cancel request
        │
        ▼
DeliveryCancellationRequest.status = PENDING
Order.status = unchanged
        │
   ┌────┴────┐
   ▼         ▼
APPROVE    REJECT
   │         │
   ▼         ▼
Order →    Order stays
CANCELLED  unchanged
```

---

## Model: `DeliveryCancellationRequest`

| Field | Type | Description |
|---|---|---|
| `order` | OneToOneField → Order | The order being cancelled (one request per order) |
| `requested_by` | ForeignKey → User | The delivery boy who submitted the request |
| `reason` | TextField | Required — why cancellation is being requested |
| `status` | CharField | `PENDING` / `APPROVED` / `REJECTED` (default: PENDING) |
| `reviewed_by` | ForeignKey → User (nullable) | Admin who reviewed the request |
| `review_notes` | TextField (optional) | Admin's notes on the decision |
| `requested_at` | DateTimeField | Auto-set when request is created |
| `reviewed_at` | DateTimeField (nullable) | When the admin made the decision |

---

## API Endpoints

### 1. Delivery Boy — Submit Cancellation Request

**`POST /api/orders/{order_id}/delivery_update_status/`**

Who can call it: Authenticated delivery boy assigned to that order.

**Request body:**
```json
{
  "status": "CANCELLED",
  "reason": "Product was damaged during transport",
  "notes": "Will contact customer with replacement options"
}
```

- `status` must be `"CANCELLED"`
- `reason` is **required** — returns 400 if missing
- `notes` is optional

**Success response (202 Accepted):**
```json
{
  "message": "Cancellation request submitted for admin approval."
}
```

**Validations:**
- Only the delivery boy whose assignment is active on this order can submit
- Order must be in `SHIPPED` or `DELIVERED` status
- If a PENDING request already exists → 400 ("Cancellation request is already pending admin review")

**What happens:**
- Creates a `DeliveryCancellationRequest` with `status=PENDING`
- Order status does **not** change at this point

---

### 2. Admin — Approve or Reject

**`POST /api/orders/{order_id}/admin_review_cancel_request/`**

Who can call it: Admin users only.

**Request body:**
```json
{
  "decision": "approve",
  "review_notes": "Approved — customer was informed."
}
```

- `decision`: `"approve"` or `"reject"` (required)
- `review_notes`: optional text

**Success response (200 OK):**
```json
{
  "message": "Cancellation request approved."
}
```
or
```json
{
  "message": "Cancellation request rejected."
}
```

**Validations:**
- Cancel request must exist for that order (404 if not)
- Request must still be `PENDING` (400 if already approved/rejected)
- `decision` must be exactly `"approve"` or `"reject"` (400 otherwise)

**What happens on approve:**
- `Order.status` → `CANCELLED`
- `cancel_request.status` → `APPROVED`
- `cancel_request.reviewed_by` → current admin
- `cancel_request.reviewed_at` → now
- `cancel_request.review_notes` → notes provided

**What happens on reject:**
- Order status stays unchanged
- `cancel_request.status` → `REJECTED`
- Same audit fields set (reviewed_by, reviewed_at, review_notes)
- Delivery boy may submit a new request if needed

---

## What the Delivery Boy Sees

When the delivery boy fetches an order, the `delivery_cancel_request` field is embedded in the order response:

```json
{
  "id": 123,
  "status": "SHIPPED",
  "delivery_cancel_request": {
    "id": 45,
    "reason": "Product was damaged during transport",
    "status": "PENDING",
    "review_notes": null,
    "requested_at": "2026-05-01T10:30:00Z",
    "reviewed_at": null
  }
}
```

Possible `status` values:
- `PENDING` — waiting for admin to review
- `APPROVED` — admin approved, order is now CANCELLED
- `REJECTED` — admin rejected, order continues as before

If no cancel request exists, `delivery_cancel_request` is `null`.

---

## What the Admin Sees

### Django Admin Panel

Go to **Orders → Delivery Cancellation Requests** in the admin panel.

List columns shown: Order, Requested By, Status, Requested At, Reviewed By, Reviewed At

Filters: Status, Requested At, Reviewed At

Search: Order ID, delivery boy email, delivery boy phone number

The admin can see all pending requests, review the reason, and then call the API or use a front-end panel to approve or reject.

### Admin API — List All Cancellation Requests

**`GET /api/orders/cancel-requests/`**

Returns all cancellation requests across all orders, newest first.

**Response:**
```json
[
  {
    "id": 45,
    "order_id": 123,
    "order_status": "CANCELLED",
    "requested_by_email": "driver@example.com",
    "requested_by_phone": "+971501234567",
    "reason": "Product was damaged during transport",
    "status": "APPROVED",
    "review_notes": "Verified delivery attempts.",
    "reviewed_by_email": "admin@simakfresh.ae",
    "requested_at": "2026-05-01T10:30:00Z",
    "reviewed_at": "2026-05-01T11:00:00Z"
  }
]
```

**Query parameters:**

| Parameter | Description | Example |
|---|---|---|
| `status` | Filter by request status | `?status=PENDING` |
| `search` | Search by order ID, delivery boy email, or phone | `?search=driver@example.com` |
| `ordering` | Sort field (prefix `-` for descending) | `?ordering=-requested_at` |

**Retrieve a single request:**

`GET /api/orders/cancel-requests/{id}/`

### Admin API Flow

1. `GET /api/orders/cancel-requests/?status=PENDING` — see all pending requests
2. Note the `order_id` from the result
3. Call `POST /api/orders/{order_id}/admin_review_cancel_request/` with `decision`
4. Order status updates automatically on approval

---

## Notifications

When an order is `CANCELLED` (after admin approves), the existing order-status notification pipeline fires automatically via Django signals:

- **WhatsApp** — sends `order_status` template to the customer
- **Email** — sends order cancelled email to the customer
- **Push (FCM)** — sends push notification to the customer's devices
- **In-App** — creates an in-app notification for the customer

The delivery boy does not currently receive a notification on the admin decision (can be added as a future task).

---

## Permissions Summary

| Action | Role | Permission |
|---|---|---|
| Submit cancel request | Delivery Boy | IsAuthenticated + assigned to order |
| Approve / Reject | Admin | IsAdminUser |
| View order with cancel request | Customer | IsAuthenticated (own order) |
| View all requests in panel | Admin | Admin panel access |

---

## Example: Full End-to-End Flow

**Step 1 — Delivery boy encounters a problem:**
```bash
POST /api/orders/123/delivery_update_status/
Authorization: Bearer <delivery_boy_token>
Content-Type: application/json

{
  "status": "CANCELLED",
  "reason": "Customer was not home after 3 attempts. Product is perishable.",
  "notes": "Tried calling twice, no answer."
}
```
→ Response 202: `Cancellation request submitted for admin approval.`

**Step 2 — Admin reviews and approves:**
```bash
POST /api/orders/123/admin_review_cancel_request/
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "decision": "approve",
  "review_notes": "Verified delivery attempts, approved cancellation."
}
```
→ Response 200: `Cancellation request approved.`
→ Order 123 status is now `CANCELLED`
→ Customer receives WhatsApp + email + push notification

**Step 3 — Delivery boy checks order:**
```bash
GET /api/orders/123/
Authorization: Bearer <delivery_boy_token>
```
→ `delivery_cancel_request.status` is now `"APPROVED"` and `order.status` is `"CANCELLED"`
