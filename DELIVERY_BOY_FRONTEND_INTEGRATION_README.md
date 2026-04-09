# Delivery Boy Frontend Integration README

This document explains the full Delivery Boy integration in the current backend, including:
- Delivery boy creation by admin
- Role-based login behavior
- Delivery dashboard and operational APIs
- Order assignment and status update APIs
- Cancellation approval flow
- Proof-of-delivery upload flow

## 1. Base URLs

API base:
- `/api/`

Orders API base:
- `/api/orders/`

Users API base:
- `/api/users/`

Main router configuration is in:
- `core/urls.py`
- `Orders/urls.py`
- `Users/urls.py`

## 2. Authentication and Role Behavior

The system uses JWT auth (Bearer token and cookie support). After login, frontend should route by `user.role`.

Role values currently supported:
- `admin`
- `user`
- `delivery_boy`

User payload includes `delivery_profile` when role is `delivery_boy`.

Relevant serializer:
- `Users/serializers.py`

Example user payload (delivery boy):
```json
{
  "id": 21,
  "email": "delivery.dubai@demo.com",
  "role": "delivery_boy",
  "delivery_profile": {
    "is_available": true,
    "assigned_emirates": ["dubai", "sharjah"],
    "assigned_emirates_display": ["Dubai", "Sharjah"],
    "vehicle_number": "DXB-1001",
    "identity_number": null,
    "emergency_contact": null,
    "notes": null
  }
}
```

## 3. Data Models Added for Delivery

Delivery-related models in:
- `Orders/models.py`
- `Users/models.py`

### 3.1 DeliveryBoyProfile
Stores delivery user-specific profile:
- `user` (OneToOne with User)
- `assigned_emirates` (JSON list)
- `is_available`
- `vehicle_number`, `identity_number`, `emergency_contact`, `notes`

### 3.2 DeliveryAssignment
Maps one order to one delivery boy:
- `order` (OneToOne)
- `delivery_boy`
- `assigned_by`
- `status`: `ASSIGNED`, `IN_TRANSIT`, `COMPLETED`
- `assigned_at`, `accepted_at`, `delivered_at`, `notes`

### 3.3 DeliveryProof
Delivery evidence:
- `order` (OneToOne)
- `assignment` (FK)
- `proof_image` (required on first DELIVERED transition)
- `signature_name`, `notes`, `uploaded_by`, `created_at`

### 3.4 DeliveryCancellationRequest
Delivery boy cancellation workflow:
- `order` (OneToOne)
- `requested_by`
- `reason`
- `status`: `PENDING`, `APPROVED`, `REJECTED`
- `reviewed_by`, `review_notes`, `requested_at`, `reviewed_at`

## 4. Admin: How to Create a Delivery Boy

There are 2 supported flows.

### Flow A: Django Admin Panel (recommended for operations)

Admin panel models:
- `Users/admin.py` (`UserAdmin`)
- `Users/admin.py` (`DeliveryBoyProfileAdmin`)

Steps:
1. Create user in admin panel with role = `delivery_boy`.
2. Open Delivery Boy Profile and set:
   - `assigned_emirates`
   - `is_available`
   - `vehicle_number` etc.

Notes:
- Signals auto-create delivery profile for delivery role users.
- Signal logic is in `Users/signals.py`.

### Flow B: API role update (admin token required)

Endpoint:
- `POST /api/users/users/{user_id}/set_role/`

Request:
```json
{
  "role": "delivery_boy"
}
```

Behavior:
- Sets role on existing user.
- Signal ensures delivery profile exists.

Important:
- There is currently no dedicated public API to edit `assigned_emirates` profile fields.
- Use Django admin (or internal tools) to manage profile emirate assignments.

## 5. Delivery APIs (for Frontend)

All delivery APIs are defined in:
- `Orders/views.py`

All examples below assume Authorization header:
```http
Authorization: Bearer <access_token>
```

### 5.1 Delivery Dashboard

Endpoint:
- `GET /api/orders/delivery_dashboard/`

Access:
- Delivery boy only.

Returns:
- delivery profile summary
- KPI cards
- recent assigned orders

Key KPI fields:
- `assigned_orders`
- `completed_today`
- `pending_assigned_orders`
- `available_orders_in_region`
- `completed_total`

### 5.2 Available Orders in Assigned Emirates

Endpoint:
- `GET /api/orders/available_orders/`

Access:
- Delivery boy only.

Returns unassigned orders filtered by:
- emirate in delivery boy assigned emirates
- status in `PAID`, `PROCESSING`
- no delivery assignment

### 5.3 Claim Order

Endpoint:
- `POST /api/orders/{order_id}/claim_order/`

Access:
- Delivery boy only.

Request (optional):
```json
{
  "notes": "Claiming now"
}
```

Behavior:
- Validates emirate coverage and availability.
- Creates `DeliveryAssignment`.
- If order status is `PAID`, updates it to `PROCESSING`.

Success response:
```json
{
  "message": "Order claimed successfully.",
  "order_id": 123,
  "assignment_id": 44
}
```

### 5.4 Delivery Boy Status Update (Shipped/Delivered/Cancel Request)

Endpoint:
- `POST /api/orders/{order_id}/delivery_update_status/`

Access:
- Delivery boy assigned to that order only.

#### A) Move to SHIPPED
Request:
```json
{
  "status": "SHIPPED",
  "notes": "Picked up from warehouse"
}
```

Rules:
- Allowed from `PAID` or `PROCESSING` only.
- Assignment status becomes `IN_TRANSIT`.

#### B) Move to DELIVERED (proof required)
Request as multipart/form-data:
- `status=DELIVERED`
- `proof_image=<file>` (required first time)
- `signature_name=<optional>`
- `proof_notes=<optional>`
- `notes=<optional>`

Rules:
- Allowed only when order is already `SHIPPED`.
- Assignment status becomes `COMPLETED`.
- Creates/updates `DeliveryProof`.

#### C) Request cancellation (admin approval required)
Request:
```json
{
  "status": "CANCELLED",
  "reason": "Customer unreachable after multiple attempts"
}
```

Rules:
- Delivery boy cannot directly cancel final order state.
- Creates or updates `DeliveryCancellationRequest` with `PENDING`.

### 5.5 Admin Review Cancellation Request

Endpoint:
- `POST /api/orders/{order_id}/admin_review_cancel_request/`

Access:
- Admin only.

Request:
```json
{
  "decision": "approve",
  "review_notes": "Approved after call center verification"
}
```

`decision` values:
- `approve`
- `reject`

Behavior:
- approve -> order status becomes `CANCELLED`, request status `APPROVED`
- reject -> request status `REJECTED`

### 5.6 Admin Assign Delivery Boy to Order

Endpoint:
- `POST /api/orders/{order_id}/admin_assign_delivery_boy/`

Access:
- Admin only.

Request:
```json
{
  "delivery_boy_id": 21,
  "notes": "Assigned manually from operations desk"
}
```

Rules:
- Delivery boy must have role `delivery_boy`.
- Delivery boy profile must exist.
- Delivery boy emirate assignment must include order shipping emirate.

Behavior:
- Creates/updates `DeliveryAssignment`.
- If created and order is `PAID`, order moves to `PROCESSING`.

## 6. Order Visibility Rules by Role

Order queryset behavior in `Orders/views.py`:

- `admin`:
  - Can see all orders.

- `delivery_boy`:
  - Can see:
    - orders assigned to self
    - unassigned `PAID`/`PROCESSING` orders in assigned emirates

- `user`:
  - Can see only own orders.

## 7. Frontend Screen Mapping (Recommended)

### Delivery Boy App/Web Screens
1. Dashboard
   - Use `GET /api/orders/delivery_dashboard/`

2. Available orders list
   - Use `GET /api/orders/available_orders/`

3. My assigned orders
   - Use standard orders list and filter `delivery_assignment.delivery_boy == self`

4. Claim action button
   - Use `POST /api/orders/{id}/claim_order/`

5. Status update action
   - Use `POST /api/orders/{id}/delivery_update_status/`

6. Delivered proof upload
   - multipart to `delivery_update_status`

7. Cancel request action
   - `delivery_update_status` with status `CANCELLED` + reason

### Admin Operations Screens
1. Create delivery boy account
   - Django admin (preferred) or user role API

2. Assign order to delivery boy
   - `POST /api/orders/{id}/admin_assign_delivery_boy/`

3. Review cancellation requests
   - `POST /api/orders/{id}/admin_review_cancel_request/`

## 8. Error Handling to Implement in Frontend

Common API error messages include:
- `Only delivery boys can access this dashboard.`
- `Delivery profile not found.`
- `Order emirate is outside your assigned coverage.`
- `Order is already assigned.`
- `proof_image is required for delivery confirmation.`
- `Cancellation request is already pending admin review.`
- `Selected delivery boy is not assigned to this emirate.`

Frontend should:
- Show exact backend message to operations users.
- Retry-safe UI for claim and cancel requests.
- Disable invalid status transitions in UI.

## 9. Demo Seed for Frontend Testing

A demo command exists in:
- `Orders/management/commands/seed_delivery_demo.py`

Run:
```bash
python manage.py seed_delivery_demo
```

Creates demo users:
- Admin: `delivery-admin@demo.com / Admin@123`
- Delivery Dubai: `delivery.dubai@demo.com / Delivery@123`
- Delivery Abu Dhabi: `delivery.abudhabi@demo.com / Delivery@123`
- Customer: `delivery.customer@demo.com / Customer@123`

Also creates sample orders and assignments for UI testing.

## 10. Migration Requirement

Delivery schema depends on these migrations:
- `Users/migrations/0008_deliveryboyprofile_and_role_update.py`
- `Orders/migrations/0007_delivery_models.py`

If needed:
```bash
python manage.py migrate
```

## 11. Current Limitations / Notes

1. No standalone REST endpoint yet for admin to directly edit `DeliveryBoyProfile.assigned_emirates`; use Django admin.
2. Cancellation by delivery is request-only, final cancel decision is admin-controlled.
3. Proof image is mandatory for first DELIVERED update when no existing proof exists.
4. All delivery endpoints are under `OrderViewSet` actions in `Orders/views.py`.

## 12. Quick API Checklist

- Delivery dashboard: `GET /api/orders/delivery_dashboard/`
- Available orders: `GET /api/orders/available_orders/`
- Claim order: `POST /api/orders/{id}/claim_order/`
- Delivery status update: `POST /api/orders/{id}/delivery_update_status/`
- Admin assign delivery: `POST /api/orders/{id}/admin_assign_delivery_boy/`
- Admin review cancel request: `POST /api/orders/{id}/admin_review_cancel_request/`
- Admin set user role: `POST /api/users/users/{id}/set_role/`

---

If needed, next step can be a Postman collection export format for these exact APIs and request bodies.
