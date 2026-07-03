# Product Unit Admin/API Guide

This backend now supports admin-managed product units.

Frontend compatibility is preserved:
- product responses still return `unit` as plain text
- admin/backend writes can use `unit_id`

## Admin Panel

Use Django admin at `django-admin/`.

### Add A Unit

1. Open `Product Units`
2. Click `Add Product Unit`
3. Fill:
   - `name`: example `box`, `tray`, `500g`
   - `is_active`
   - `sort_order`
4. Save

### Assign Unit To Product

1. Open `Products`
2. Edit or create a product
3. Select `Unit option`
4. Save

The backend automatically copies the selected unit name into the product `unit` text field, so existing frontend apps still receive the same format.

## Admin API

Base path:

```text
/api/products/
```

### 1. Create A Unit

Endpoint:

```text
POST /api/products/units/
```

Example request:

```json
{
  "name": "box",
  "is_active": true,
  "sort_order": 10
}
```

Example response:

```json
{
  "id": 4,
  "name": "box",
  "is_active": true,
  "sort_order": 10,
  "created_at": "2026-06-21T08:00:00Z",
  "updated_at": "2026-06-21T08:00:00Z"
}
```

### 2. List Units

Endpoint:

```text
GET /api/products/units/
```

Optional filters:
- `is_active=true`
- `search=box`

### 3. Assign A Unit To A Product

Endpoint:

```text
POST /api/products/products/
```

or update an existing product:

```text
PATCH /api/products/products/{id}/
```

Example create/update payload:

```json
{
  "category": 1,
  "name": "Salmon Box",
  "description": "Fresh salmon",
  "price": "25.00",
  "stock": 10,
  "is_available": true,
  "unit_id": 4
}
```

## Important Notes

- `unit_id` is for admin/backend writes
- `unit` is still returned as text in product responses
- existing products were backfilled automatically from current unit text values
- if a unit name is renamed in admin, linked products will keep their `unit` text in sync
