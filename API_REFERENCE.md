
## Products (Admin)

### Product Delivery Tiers
Manage quantity-based delivery rules.
*   **URL**: `/api/products/delivery-tiers/`
*   **Methods**: `GET`, `POST`
*   **Auth**: Admin only
*   **Body (Create)**:
    ```json
    {
      "product": 1,
      "min_quantity": 10,
      "delivery_days": 2
    }
    ```

### Product Discount Tiers
Manage quantity-based discount rules.
*   **URL**: `/api/products/discount-tiers/`
*   **Methods**: `GET`, `POST`
*   **Auth**: Admin only
*   **Body (Create)**:
    ```json
    {
      "product": 1,
      "min_quantity": 10,
      "discount_percentage": 10.00
    }
    ```
