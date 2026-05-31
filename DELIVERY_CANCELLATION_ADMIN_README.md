# Admin — Delivery Cancellation Requests

This document covers every API endpoint available to admin users for managing delivery cancellation requests, with full request and response examples.

---

## Base URL

All endpoints are under: `/api/orders/`

All requests require an admin token:
```
Authorization: Bearer <admin_token>
```

---

## Endpoints Summary

| Method | URL | Description |
|---|---|---|
| GET | `/api/orders/cancel-requests/` | List all cancellation requests |
| GET | `/api/orders/cancel-requests/{id}/` | Retrieve a single request |
| POST | `/api/orders/{order_id}/admin_review_cancel_request/` | Approve or reject a request |

---

## 1. List All Cancellation Requests

**`GET /api/orders/cancel-requests/`**

Returns all cancellation requests across all orders, newest first.

### Request

```http
GET /api/orders/cancel-requests/
Authorization: Bearer <admin_token>
```

### Response — 200 OK

```json
[
  {
    "id": 45,
    "order_id": 123,
    "order_status": "CANCELLED",
    "requested_by_email": "driver@simakfresh.ae",
    "requested_by_phone": "+971501234567",
    "reason": "Product was damaged during transport",
    "status": "APPROVED",
    "review_notes": "Verified delivery attempts, approved.",
    "reviewed_by_email": "admin@simakfresh.ae",
    "requested_at": "2026-05-01T10:30:00Z",
    "reviewed_at": "2026-05-01T11:00:00Z"
  },
  {
    "id": 46,
    "order_id": 124,
    "order_status": "SHIPPED",
    "requested_by_email": "driver2@simakfresh.ae",
    "requested_by_phone": "+971509876543",
    "reason": "Customer was not home after 3 attempts",
    "status": "PENDING",
    "review_notes": null,
    "reviewed_by_email": null,
    "requested_at": "2026-05-01T12:00:00Z",
    "reviewed_at": null
  }
]
```

### Response fields

| Field | Type | Description |
|---|---|---|
| `id` | int | Cancellation request ID |
| `order_id` | int | The order this request is for |
| `order_status` | string | Current status of the order |
| `requested_by_email` | string | Delivery boy's email |
| `requested_by_phone` | string \| null | Delivery boy's phone number |
| `reason` | string | Why cancellation was requested |
| `status` | string | `PENDING` / `APPROVED` / `REJECTED` |
| `review_notes` | string \| null | Admin's notes on the decision |
| `reviewed_by_email` | string \| null | Email of the admin who reviewed it |
| `requested_at` | datetime | When the request was submitted |
| `reviewed_at` | datetime \| null | When the admin reviewed it |

---

## 2. Filter, Search, and Sort

### Filter by status

```http
GET /api/orders/cancel-requests/?status=PENDING
GET /api/orders/cancel-requests/?status=APPROVED
GET /api/orders/cancel-requests/?status=REJECTED
```

### Search by delivery boy email, phone, or order ID

```http
GET /api/orders/cancel-requests/?search=driver@simakfresh.ae
GET /api/orders/cancel-requests/?search=+971501234567
GET /api/orders/cancel-requests/?search=124
```

### Sort results

```http
GET /api/orders/cancel-requests/?ordering=-requested_at    # newest first (default)
GET /api/orders/cancel-requests/?ordering=requested_at     # oldest first
GET /api/orders/cancel-requests/?ordering=-reviewed_at     # recently reviewed first
GET /api/orders/cancel-requests/?ordering=status           # alphabetical by status
```

### Combine filters

```http
GET /api/orders/cancel-requests/?status=PENDING&ordering=-requested_at
```

---

## 3. Retrieve a Single Request

**`GET /api/orders/cancel-requests/{id}/`**

### Request

```http
GET /api/orders/cancel-requests/46/
Authorization: Bearer <admin_token>
```

### Response — 200 OK

```json
{
  "id": 46,
  "order_id": 124,
  "order_status": "SHIPPED",
  "requested_by_email": "driver2@simakfresh.ae",
  "requested_by_phone": "+971509876543",
  "reason": "Customer was not home after 3 attempts",
  "status": "PENDING",
  "review_notes": null,
  "reviewed_by_email": null,
  "requested_at": "2026-05-01T12:00:00Z",
  "reviewed_at": null
}
```

### Response — 404 Not Found

```json
{
  "detail": "No DeliveryCancellationRequest matches the given query."
}
```

---

## 4. Approve a Cancellation Request

**`POST /api/orders/{order_id}/admin_review_cancel_request/`**

### Request

```http
POST /api/orders/124/admin_review_cancel_request/
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "decision": "approve",
  "review_notes": "Verified 3 delivery attempts. Customer confirmed unavailable."
}
```

- `decision`: **required** — must be `"approve"` or `"reject"`
- `review_notes`: optional free-text string

### Response — 200 OK

```json
{
  "message": "Cancellation request approved."
}
```

**Side effects:**
- `Order.status` → `CANCELLED`
- `DeliveryCancellationRequest.status` → `APPROVED`
- `reviewed_by` set to current admin
- `reviewed_at` set to current timestamp
- Django signal fires → customer receives WhatsApp + Email + FCM push notification for CANCELLED status

---

## 5. Reject a Cancellation Request

**`POST /api/orders/{order_id}/admin_review_cancel_request/`**

### Request

```http
POST /api/orders/124/admin_review_cancel_request/
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "decision": "reject",
  "review_notes": "Driver did not follow correct return procedure."
}
```

### Response — 200 OK

```json
{
  "message": "Cancellation request rejected."
}
```

**Side effects:**
- `Order.status` unchanged
- `DeliveryCancellationRequest.status` → `REJECTED`
- `reviewed_by` set to current admin
- `reviewed_at` set to current timestamp
- The delivery boy may submit a new request for the same order if needed

---

## 6. Error Responses

### No cancellation request exists for this order

**Condition:** The order has no associated `DeliveryCancellationRequest`.

```json
{
  "error": "Cancellation request not found."
}
```
Status: `404 Not Found`

---

### Request already reviewed

**Condition:** The request status is already `APPROVED` or `REJECTED`.

```json
{
  "error": "Only pending cancellation requests can be reviewed."
}
```
Status: `400 Bad Request`

---

### Invalid decision value

**Condition:** `decision` is missing, misspelled, or not `"approve"` / `"reject"`.

```json
{
  "error": "decision must be either 'approve' or 'reject'."
}
```
Status: `400 Bad Request`

---

### Unauthorized

**Condition:** Token is missing, expired, or belongs to a non-admin user.

```json
{
  "detail": "Authentication credentials were not provided."
}
```
or
```json
{
  "detail": "You do not have permission to perform this action."
}
```
Status: `401` / `403`

---

## 7. Typical Admin Workflow

**Step 1 — Check for new pending requests:**
```http
GET /api/orders/cancel-requests/?status=PENDING&ordering=-requested_at
```

**Step 2 — Read the reason and note the `order_id`.**

**Step 3 — Approve:**
```http
POST /api/orders/{order_id}/admin_review_cancel_request/
{ "decision": "approve", "review_notes": "..." }
```

or **Reject:**
```http
POST /api/orders/{order_id}/admin_review_cancel_request/
{ "decision": "reject", "review_notes": "..." }
```

**Step 4 — Confirm by fetching the single request:**
```http
GET /api/orders/cancel-requests/{id}/
```
`status` will now be `"APPROVED"` or `"REJECTED"`.

---

## 8. Django Admin Panel

Go to **Orders → Delivery Cancellation Requests** in the Django admin panel.

- **List columns:** Order, Requested By, Status, Requested At, Reviewed By, Reviewed At
- **Filters:** Status, Requested At, Reviewed At
- **Search:** Order ID, delivery boy email, delivery boy phone number
