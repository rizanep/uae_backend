# Admin Guide: Delivery Preferences and Management

This guide explains how admins configure delivery preferences (lead times), quantity-based discounts, and manage orders via API and the Django Admin panel.

## Delivery Preferences

- Delivery lead time is determined per product using quantity-based tiers.
- If no tier applies, the system may use the product’s `expected_delivery_time` as a fallback.
- Estimation logic picks the highest tier with `min_quantity <= ordered quantity`.

### Configure via Django Admin
- Go to Admin → Products → select a Product.
- Use the “Delivery Tiers” inline to add rows:
  - `min_quantity`: minimum quantity threshold.
  - `delivery_days`: number of days required.
- Save the product; tiers apply immediately to delivery estimation.

### Configure via API (Delivery Tiers)
- URL: `/api/products/delivery-tiers/`
- Methods: `GET`, `POST`, `PATCH`, `DELETE` (Admin only)
- Filter: `?product=<product_id>`
- Body (Create):
```json
{
  "product": 1,
  "min_quantity": 10,
  "delivery_days": 2
}
```
- Notes:
  - Unique per (`product`, `min_quantity`).
  - Order tiers by `min_quantity` ascending; system selects the highest matching tier.

### Product Fallback: expected_delivery_time
- Field: `expected_delivery_time` (on Product)
- Examples: `"30-60 mins"`, `"Next Day"`, `"2-3 Business Days"`.
- Used when no delivery tier matches; tiers take precedence when present.

## Quantity-Based Discounts

- Discounts reduce unit price based on ordered quantity.
- Logic mirrors delivery tiers: highest tier with `min_quantity <= quantity` applies.

### Configure via API (Discount Tiers)
- URL: `/api/products/discount-tiers/`
- Methods: `GET`, `POST`, `PATCH`, `DELETE` (Admin only)
- Filter: `?product=<product_id>`
- Body (Create):
```json
{
  "product": 1,
  "min_quantity": 10,
  "discount_percentage": 10.00
}
```
- Effect:
  - Cart item `unit_price = product.final_price - (final_price * discount_percentage / 100)`.
  - Subtotal = `unit_price * quantity`.

## Order Management

### Update Order Status
- URL: `/api/orders/{id}/admin_update_status/`
- Method: `POST` (Admin only)
- Body:
```json
{ "status": "shipped", "notes": "Optional note" }
```
- Valid statuses must match backend enum; change logs appear in status history.

### Dashboard Analytics
- URL: `/api/orders/dashboard_analytics/`
- Method: `GET` (Admin only)
- Returns aggregates for users, orders, revenue, cart metrics, and top products.

## Delivery Estimation (Reference)

- URL: `/api/orders/estimate_delivery/` (GET, Auth required)
- Computes earliest delivery date for the current cart:
  - Finds per-item tier by quantity.
  - Uses maximum `delivery_days` across items.
  - Earliest date = today + max days.
- Frontend validates `preferred_delivery_date` against this estimate during checkout.

## Best Practices

- Avoid overlapping or redundant tiers; keep `min_quantity` thresholds clear.
- Review `expected_delivery_time` only as a fallback; prefer tiers for predictability.
- Use filtering (`?product=ID`) to manage tiers for a specific product via API.
- After changes, verify estimation with a test cart matching intended quantities.

