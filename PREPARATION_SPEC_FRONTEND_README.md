# Preparation Specification Frontend Integration

This document explains how to integrate the new product preparation specification feature on both admin side and user side.

It covers:
- how admin adds preparation specifications
- how frontend reads preparation specifications with product details
- how frontend sends selected preparation data to cart
- how checkout validates preparation selection
- how order details return the saved preparation data

## 1. Feature Summary

Some products can now have preparation specifications such as:

- Live (Packed in Air bag)
- Whole uncleaned, fresh caught (Packed with ice)
- Whole cleaned headon, fresh caught (Packed with ice)
- Whole cleaned headon centre open, fresh caught (Packed with ice)
- Whole cleaned headless, fresh caught (Packed with ice)

Each preparation specification includes:

- `name`
- `description`
- `image`
- `extra_price`
- `sort_order`

If a product has active preparation specifications, the user must select one before adding that product to cart.

The user can also send optional custom instructions.

## 2. Admin Side
<<<<<<< HEAD
aa
=======

>>>>>>> dev
Admin can manage preparation specifications via the REST API (requires admin token) or via Django admin.

### Admin REST Endpoints

All write endpoints require `IsAdminUser` (staff token).

| Method | URL | Description |
|--------|-----|-------------|
| `GET` | `/api/products/preparation-specs/?product={id}` | List all specs for a product (including inactive) |
| `POST` | `/api/products/preparation-specs/` | Create a new spec |
| `GET` | `/api/products/preparation-specs/{id}/` | Retrieve a spec |
| `PATCH` | `/api/products/preparation-specs/{id}/` | Update a spec |
| `DELETE` | `/api/products/preparation-specs/{id}/` | Delete a spec |

Nested alternative (product auto-set from URL):

| Method | URL | Description |
|--------|-----|-------------|
| `GET` | `/api/products/products/{id}/preparation-specs/` | List specs scoped to a product |
| `POST` | `/api/products/products/{id}/preparation-specs/` | Create spec (no need to send `product` in body) |

### Create / Update Spec Request Body

```json
{
  "product": 12,
  "name": "Whole cleaned headon",
  "description": "Fish cleaned with head on, packed with ice",
  "image": null,
  "extra_price": "5.00",
  "sort_order": 1,
  "is_active": true
}
```

When using the nested `POST /api/products/products/{id}/preparation-specs/` endpoint, `product` is set automatically — omit it from the body.

### Response Fields

| Field | Type | Notes |
|-------|------|-------|
| `id` | integer | Auto-assigned |
| `product` | integer | FK to product |
| `name` | string | Required |
| `description` | string | Optional |
| `image` | url / null | Upload via multipart or send null |
| `extra_price` | decimal | Default `0.00` |
| `sort_order` | integer | Lower = shown first |
| `is_active` | boolean | Inactive specs hidden from customers |
| `created_at` | datetime | Read-only |
| `updated_at` | datetime | Read-only |

### Recommended Admin Dashboard Flow

1. On **Add Product** — after saving the product, call `POST /api/products/products/{id}/preparation-specs/` for each spec row the admin defined.
2. On **Edit Product** — fetch existing specs with `GET /api/products/products/{id}/preparation-specs/`, diff with form state, then `POST` new rows, `PATCH` changed rows, `DELETE` removed rows.
3. Always send `sort_order` to control the display order shown to customers.

### Django Admin (alternative)

Specs can still be managed directly in Django admin:

- Open Django Admin → Products → select a product
- Add/edit rows in the `Product Preparation Specifications` inline section

### Important Note

Only specs with `is_active = true` are returned to customers in product detail/list APIs. Admin endpoints return all specs regardless of `is_active`.

## 3. Product Detail API

Frontend can read preparation specifications directly from product details.

### Endpoints

- `GET /api/products/`
- `GET /api/products/{id}/`

### Product Response Example

```json
{
  "id": 12,
  "category": 3,
  "category_name": "Fish",
  "name": "Hamour",
  "slug": "hamour",
  "description": "Fresh local hamour",
  "price": "45.00",
  "discount_price": "40.00",
  "final_price": "40.00",
  "stock": 22,
  "is_available": true,
  "image": "https://example.com/media/products/hamour.jpg",
  "sku": "hamour",
  "unit": "kg",
  "available_emirates": ["dubai", "sharjah"],
  "expected_delivery_time": "30-60 mins",
  "delivery_tiers": [],
  "discount_tiers": [],
  "average_rating": 4.7,
  "total_reviews": 11,
  "preparation_specifications": [
    {
      "id": 7,
      "name": "Live (Packed in Air bag)",
      "description": "Delivered live in secure air bag packaging.",
      "image": "https://example.com/media/preparation_specs/live.jpg",
      "extra_price": "0.00",
      "sort_order": 1
    },
    {
      "id": 8,
      "name": "Whole cleaned headon, fresh caught (Packed with ice)",
      "description": "Cleaned and packed with ice.",
      "image": "https://example.com/media/preparation_specs/headon.jpg",
      "extra_price": "5.00",
      "sort_order": 2
    }
  ],
  "created_at": "2026-04-26T11:00:00Z",
  "updated_at": "2026-04-26T11:00:00Z"
}
```

### Frontend Rule

If `preparation_specifications` is not empty:

- show a required selector
- do not allow add-to-cart until one option is selected
- allow user to enter optional instructions text

If `preparation_specifications` is empty:

- no preparation UI is required

## 4. Add To Cart API

When a product has preparation specifications, frontend must send the selected specification.

### Endpoint

- `POST /api/cart/add_item/`

### Request Body For Product With Preparation Spec

```json
{
  "product": 12,
  "quantity": 2,
  "preparation_specification": 8,
  "preparation_instructions": "Please clean properly and pack with extra ice"
}
```

### Request Body For Product Without Preparation Spec

```json
{
  "product": 15,
  "quantity": 1
}
```

### Success Response

```json
{
  "message": "Item added to cart.",
  "cart_item_id": 54
}
```

### Validation Errors

#### Missing preparation specification

```json
{
  "error": "Preparation specification is required for this product."
}
```

#### Invalid preparation specification

```json
{
  "error": "Invalid preparation specification for this product."
}
```

#### Product does not support preparation specifications

```json
{
  "error": "This product does not support preparation specifications."
}
```

#### Stock error

```json
{
  "error": "Only 3 items in stock."
}
```

## 5. Cart Response

Frontend can use cart API to show selected preparation option and price impact.

### Endpoint

- `GET /api/cart/my_cart/`

### Response Example

```json
{
  "id": 4,
  "user": 21,
  "items": [
    {
      "id": 54,
      "product": 12,
      "product_details": {
        "id": 12,
        "name": "Hamour",
        "final_price": "40.00",
        "preparation_specifications": [
          {
            "id": 7,
            "name": "Live (Packed in Air bag)",
            "description": "Delivered live in secure air bag packaging.",
            "image": "https://example.com/media/preparation_specs/live.jpg",
            "extra_price": "0.00",
            "sort_order": 1
          }
        ]
      },
      "preparation_specification": 8,
      "preparation_specification_details": {
        "id": 8,
        "name": "Whole cleaned headon, fresh caught (Packed with ice)",
        "description": "Cleaned and packed with ice.",
        "image": "https://example.com/media/preparation_specs/headon.jpg",
        "extra_price": "5.00",
        "sort_order": 2
      },
      "preparation_instructions": "Please clean properly and pack with extra ice",
      "quantity": 2,
      "base_unit_price": "40.00",
      "preparation_extra_price": "5.00",
      "unit_price": "45.00",
      "subtotal": "90.00",
      "created_at": "2026-04-26T11:45:00Z",
      "updated_at": "2026-04-26T11:45:00Z"
    }
  ],
  "total_price": "90.00",
  "total_items": 2,
  "created_at": "2026-04-26T11:40:00Z",
  "updated_at": "2026-04-26T11:45:00Z"
}
```

### Price Logic In Cart

- `base_unit_price` = product price after any quantity discount
- `preparation_extra_price` = extra charge for selected preparation option
- `unit_price` = `base_unit_price + preparation_extra_price`
- `subtotal` = `unit_price * quantity`

## 6. Update Cart Quantity

### Endpoint

- `POST /api/cart/update_item_quantity/`

### Recommended Request

Use `cart_item_id` because the same product may exist multiple times with different preparation selections.

```json
{
  "cart_item_id": 54,
  "quantity": 3
}
```

### Success Response

```json
{
  "message": "Quantity updated."
}
```

## 7. Remove Cart Item

### Endpoint

- `POST /api/cart/remove_item/`

### Recommended Request

```json
{
  "cart_item_id": 54
}
```

### Success Response

```json
{
  "message": "Item removed from cart."
}
```

## 8. Checkout Summary API

This endpoint validates cart state before final checkout and returns totals.

### Endpoint

- `POST /api/orders/checkout_summary/`

### Request Body

```json
{
  "address_id": 3,
  "coupon_code": "SAVE10",
  "tip_amount": 5
}
```

### Success Response

```json
{
  "success": true,
  "cart_total_before_discount": "90.00",
  "discount_amount": "10.00",
  "discount_type": "percentage",
  "discount_code": "SAVE10",
  "coupon_message": null,
  "cart_total_after_discount": "80.00",
  "delivery_charge": "5.00",
  "tip_amount": "5",
  "final_total": "90.00",
  "items_count": 1
}
```

### Preparation Validation Error

```json
{
  "error": "Preparation specification is missing or invalid for one or more cart items.",
  "preparation_details": [
    {
      "cart_item_id": 54,
      "product_id": 12,
      "product_name": "Hamour",
      "error": "Preparation specification is required for this product."
    }
  ]
}
```

## 9. Checkout API

This creates the order from the cart.

### Endpoint

- `POST /api/orders/checkout/`

### Request Body

```json
{
  "address_id": 3,
  "payment_method": "ZIINA",
  "tip_amount": 5,
  "coupon_code": "SAVE10",
  "preferred_delivery_date": "2026-04-27",
  "preferred_delivery_slot": 2,
  "delivery_notes": "Call before delivery",
  "device": "mobile"
}
```

### Payment Method Values

- `ZIINA`
- `COD`

### Success Response For ZIINA

```json
{
  "message": "Order created successfully.",
  "order_id": 101,
  "payment_url": "https://payment.example.com/redirect",
  "total_amount": "90.00",
  "payment_method": "ZIINA"
}
```

### Success Response For COD

```json
{
  "message": "Order created successfully. Please pay upon delivery.",
  "order_id": 101,
  "total_amount": "90.00",
  "payment_method": "COD"
}
```

### Common Checkout Errors

#### User not phone verified

```json
{
  "error": "Only verified users with a phone number can purchase products. Please verify your phone number to continue."
}
```

#### Invalid delivery slot

```json
{
  "error": "Invalid or inactive delivery time slot."
}
```

#### Invalid delivery date

```json
{
  "error": "Invalid date format. Use YYYY-MM-DD."
}
```

#### Preparation validation failure

```json
{
  "error": "Preparation specification is missing or invalid for one or more cart items.",
  "preparation_details": [
    {
      "cart_item_id": 54,
      "product_id": 12,
      "product_name": "Hamour",
      "error": "Selected preparation specification is no longer active."
    }
  ]
}
```

#### Stock validation failure

```json
{
  "error": "Insufficient stock for one or more products.",
  "stock_details": [
    {
      "product_id": 12,
      "product_name": "Hamour",
      "requested_quantity": 5,
      "available_stock": 2
    }
  ]
}
```

## 10. Order Details API

Frontend can show saved preparation details from order response.

### Endpoint

- `GET /api/orders/{id}/`

### Order Response Example

```json
{
  "id": 101,
  "status": "PENDING",
  "shipping_address": 3,
  "total_amount": "90.00",
  "tip_amount": "5.00",
  "discount_amount": "10.00",
  "delivery_charge": "5.00",
  "preferred_delivery_date": "2026-04-27",
  "preferred_delivery_slot": 2,
  "delivery_notes": "Call before delivery",
  "items": [
    {
      "id": 301,
      "product": 12,
      "product_name": "Hamour",
      "product_image": "https://example.com/media/products/hamour.jpg",
      "quantity": 2,
      "price": "40.00",
      "subtotal": "80.00",
      "preparation_specification": 8,
      "preparation_specification_name": "Whole cleaned headon, fresh caught (Packed with ice)",
      "preparation_extra_price": "5.00",
      "preparation_instructions": "Please clean properly and pack with extra ice",
      "total_with_preparation": "90.00"
    }
  ],
  "payment": {
    "transaction_id": null,
    "amount": "90.00",
    "status": "PENDING",
    "payment_method": "ZIINA",
    "receipt": null,
    "created_at": "2026-04-26T11:55:00Z"
  },
  "created_at": "2026-04-26T11:55:00Z",
  "updated_at": "2026-04-26T11:55:00Z",
  "user": 21
}
```

### Important Order Notes

- `price` in order item is the base product price after quantity discount
- `preparation_extra_price` is stored separately as a snapshot
- `preparation_specification_name` is also stored as a snapshot
- this means old orders remain correct even if admin later changes the preparation specification name or price

## 11. Recommended Frontend UX

### Product Detail Page

- Fetch product details
- If `preparation_specifications.length > 0`, render required radio buttons or dropdown
- Show `name`, `description`, `image`, and `extra_price`
- Show a textarea for optional instructions
- Disable add-to-cart until a preparation option is chosen

### Cart Page

- Show selected preparation name under each item
- Show preparation instructions if user entered them
- Show base price, extra price, and subtotal clearly
- Use `cart_item_id` for quantity update and remove actions

### Checkout Page

- Call `checkout_summary` before final checkout
- If backend returns `preparation_details`, redirect user to cart or show inline correction UI
- Only proceed to `checkout` after summary succeeds

## 12. Minimal Frontend Flow

### Step 1

Call `GET /api/products/{id}/`

### Step 2

Render preparation selector from `preparation_specifications`

### Step 3

Call `POST /api/cart/add_item/` with:

```json
{
  "product": 12,
  "quantity": 2,
  "preparation_specification": 8,
  "preparation_instructions": "Please clean properly"
}
```

### Step 4

Call `GET /api/cart/my_cart/`

### Step 5

Call `POST /api/orders/checkout_summary/`

### Step 6

Call `POST /api/orders/checkout/`

### Step 7

Call `GET /api/orders/{id}/` to show final saved order details including preparation specification

## 13. Quick Implementation Rules

- treat preparation selection as required only when `preparation_specifications` exists and is not empty
- always use `cart_item_id` for cart update/remove
- show `extra_price` next to each preparation option
- keep instructions optional
- use order detail response as the source of truth after checkout