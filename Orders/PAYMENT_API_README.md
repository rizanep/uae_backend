# Admin Payment API

## Overview
The Admin Payment API provides comprehensive payment tracking and management for administrators. View all payments from all customers with detailed transaction information, filtering, searching, and sorting capabilities.

## Authentication & Permissions
- **Required Role:** Administrator (staff user)
- **Auth Method:** JWT Bearer Token (HTTP-only cookie)
- **Base URL:** `/api/orders/payments/`

## Endpoints

### List All Payments
```
GET /api/orders/payments/
```
Returns paginated list of all payments with customer and order details.

**Response Status:** `200 OK`

### Get Payment Details
```
GET /api/orders/payments/{payment_id}/
```
Retrieve detailed information for a specific payment.

**Response Status:** `200 OK`

## Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `payment_id` | Integer | Unique payment identifier |
| `order_id` | Integer | Associated order ID |
| `customer_id` | Integer | User/customer ID |
| `customer_name` | String | Full name or email |
| `customer_email` | String | Customer email address |
| `customer_phone` | String | Customer phone number |
| `amount` | Decimal | Payment amount (AED) |
| `payment_method` | String | ZIINA or COD |
| `payment_method_display` | String | Readable payment method |
| `status` | String | PENDING, SUCCESS, FAILED, REFUNDED |
| `payment_status_display` | String | Readable payment status |
| `order_status` | String | PENDING, PAID, PROCESSING, SHIPPED, DELIVERED, CANCELLED |
| `transaction_id` | String | Bank/gateway transaction ID |
| `ziina_payment_intent_id` | String | Ziina payment intent reference |
| `transaction_date` | DateTime | Payment creation timestamp |
| `updated_date` | DateTime | Last update timestamp |
| `provider_response` | JSON | Full Ziina API response |

## Query Parameters

### Filtering
```
GET /api/orders/payments/?status=SUCCESS&payment_method=ZIINA&order__status=DELIVERED
```

| Parameter | Values | Description |
|-----------|--------|-------------|
| `status` | PENDING, SUCCESS, FAILED, REFUNDED | Filter by payment status |
| `payment_method` | ZIINA, COD | Filter by payment method |
| `order__status` | PENDING, PAID, PROCESSING, SHIPPED, DELIVERED, CANCELLED | Filter by order status |
| `created_at` | ISO datetime | Filter by creation date |

### Searching
```
GET /api/orders/payments/?search=customer@example.com
```

Search across:
- `order__user__email` — Customer email
- `order__user__phone_number` — Customer phone
- `order__id` — Order ID
- `transaction_id` — Transaction reference

### Sorting
```
GET /api/orders/payments/?ordering=-created_at
```

| Parameter | Description |
|-----------|-------------|
| `ordering=created_at` | Oldest payments first |
| `ordering=-created_at` | **Newest payments first (default)** |
| `ordering=amount` | Lowest amount first |
| `ordering=-amount` | Highest amount first |
| `ordering=status` | Payment status A-Z |

## Example Requests

### Get all successful payments
```bash
curl -X GET "http://localhost:8000/api/orders/payments/?status=SUCCESS" \
  -H "Authorization: Bearer <jwt_token>"
```

### Search payments by customer email
```bash
curl -X GET "http://localhost:8000/api/orders/payments/?search=john@example.com" \
  -H "Authorization: Bearer <jwt_token>"
```

### Filter by ZIINA card payments (sorted by amount, descending)
```bash
curl -X GET "http://localhost:8000/api/orders/payments/?payment_method=ZIINA&ordering=-amount" \
  -H "Authorization: Bearer <jwt_token>"
```

### Get failed payments from last week
```bash
curl -X GET "http://localhost:8000/api/orders/payments/?status=FAILED&created_at=2026-03-27" \
  -H "Authorization: Bearer <jwt_token>"
```

### Retrieve specific payment details
```bash
curl -X GET "http://localhost:8000/api/orders/payments/42/" \
  -H "Authorization: Bearer <jwt_token>"
```

## Example Response

```json
{
  "count": 156,
  "next": "http://localhost:8000/api/orders/payments/?page=2",
  "previous": null,
  "results": [
    {
      "payment_id": 42,
      "order_id": 10,
      "customer_id": 5,
      "customer_name": "John Doe",
      "customer_email": "john.doe@example.com",
      "customer_phone": "+971501234567",
      "amount": "299.99",
      "payment_method": "ZIINA",
      "payment_method_display": "Ziina / Card",
      "status": "SUCCESS",
      "payment_status_display": "Success",
      "order_status": "DELIVERED",
      "transaction_id": "TXN_ABC123XYZ",
      "ziina_payment_intent_id": "pi_2K9xL4J8m5N3pQ6vZ",
      "transaction_date": "2026-04-03T14:30:45Z",
      "updated_date": "2026-04-03T14:31:12Z",
      "provider_response": {
        "id": "pi_2K9xL4J8m5N3pQ6vZ",
        "status": "COMPLETED",
        "amount": 29999,
        "currency_code": "AED"
      }
    }
  ]
}
```

## Status Codes

| Code | Meaning |
|------|---------|
| `200` | Success |
| `400` | Bad request (invalid parameters) |
| `401` | Unauthorized (missing/invalid token) |
| `403` | Forbidden (not admin) |
| `404` | Payment not found |
| `500` | Server error |

## Use Cases

### Monitor Payment Performance
```bash
GET /api/orders/payments/?status=FAILED&ordering=-created_at
```
Track failed payments to identify issues and follow up with customers.

### Daily Revenue Report
```bash
GET /api/orders/payments/?status=SUCCESS&ordering=-amount
```
View all successful payments sorted by amount for revenue tracking.

### Customer Payment History
```bash
GET /api/orders/payments/?search=customer_email@example.com
```
Find all payments associated with a specific customer.

### Payment Method Analytics
```bash
GET /api/orders/payments/?payment_method=ZIINA
GET /api/orders/payments/?payment_method=COD
```
Compare card vs. cash-on-delivery payment volumes.

## Pagination
Responses are paginated by default (typically 20 results per page).

```bash
GET /api/orders/payments/?page=1
GET /api/orders/payments/?page=2
```

Use the `next` and `previous` URLs in the response to navigate pages.

## Notes
- All monetary amounts are in **AED (UAE Dirham)**
- Timestamps are in **UTC (ISO 8601 format)**
- All endpoints require **admin authentication**
- Payment data is read-only (no POST, PUT, PATCH, DELETE)
- Queries are optimized with `select_related` to prevent N+1 problems
- Default ordering is by newest payments first

## Error Responses

### Unauthorized Access
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### Permission Denied
```json
{
  "detail": "You do not have permission to perform this action."
}
```

### Payment Not Found
```json
{
  "detail": "Not found."
}
```
