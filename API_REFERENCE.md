# API Reference

This document provides a comprehensive reference for the E-commerce API.
All API endpoints are prefixed with `/api/`.

## Authentication

### Login (JWT)
Obtain access and refresh tokens.

*   **URL**: `/api/auth/login/`
*   **Method**: `POST`
*   **Body**:
    ```json
    {
      "email": "user@example.com",
      "password": "securepassword"
    }
    ```
*   **Response**:
    ```json
    {
      "access": "ey...",
      "refresh": "ey...",
      "user": {
        "id": 1,
        "email": "user@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "role": "customer"
      }
    }
    ```

### Refresh Token
Refresh an expired access token using a refresh token.

*   **URL**: `/api/auth/refresh/`
*   **Method**: `POST`
*   **Body**:
    ```json
    {
      "refresh": "ey..."
    }
    ```
*   **Response**:
    ```json
    {
      "access": "ey..."
    }
    ```

### Logout
Blacklist the refresh token.

*   **URL**: `/api/auth/logout/`
*   **Method**: `POST`
*   **Body**:
    ```json
    {
      "refresh": "ey..."
    }
    ```
*   **Response**: `205 Reset Content`

### Google Auth
Callback for Google OAuth.

*   **URL**: `/api/auth/google/callback/`
*   **Method**: `POST`
*   **Body**:
    ```json
    {
      "code": "4/0A..."
    }
    ```

### OTP Login
Request and verify OTP.

1.  **Request OTP**
    *   **URL**: `/api/auth/otp/request/`
    *   **Method**: `POST`
    *   **Body**: `{"email": "..."}` or `{"phone_number": "..."}`
2.  **Login with OTP**
    *   **URL**: `/api/auth/otp/login/`
    *   **Method**: `POST`
    *   **Body**: `{"email": "...", "otp": "123456"}`

---

## Users

### User Profile
Manage the authenticated user's profile.

*   **URL**: `/api/users/me/`
*   **Method**: `GET`, `PATCH`
*   **Auth**: Required
*   **Response**:
    ```json
    {
      "id": 1,
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "phone_number": "+971500000000",
      "profile": {
        "avatar": "http://...",
        "bio": "..."
      }
    }
    ```

### Change Password
*   **URL**: `/api/users/change_password/`
*   **Method**: `POST`
*   **Body**:
    ```json
    {
      "old_password": "...",
      "new_password": "..."
    }
    ```

### Addresses
Manage user shipping addresses.

*   **List/Create**: `/api/users/addresses/` (`GET`, `POST`)
*   **Retrieve/Update/Delete**: `/api/users/addresses/{id}/` (`GET`, `PUT`, `PATCH`, `DELETE`)
*   **Body (Create/Update)**:
    ```json
    {
      "type": "home",
      "name": "Home Address",
      "line1": "Villa 123, Street 45",
      "line2": "Downtown",
      "city": "Dubai",
      "state": "Dubai",
      "country": "UAE",
      "postal_code": "00000",
      "phone_number": "+971501234567",
      "is_default": true
    }
    ```

---

## Products (Catalog)

### Categories
Browse product categories.

*   **List**: `/api/products/categories/` (`GET`)
*   **Detail**: `/api/products/categories/{id}/` (`GET`)
*   **Query Params**: `search`, `parent`

### Products
Browse and search products.

*   **List**: `/api/products/products/` (`GET`)
*   **Detail**: `/api/products/products/{id}/` (`GET`)
*   **Query Params**:
    *   `search`: Search by name, description, sku
    *   `category`: Filter by category ID
    *   `category_slug`: Filter by category slug
    *   `min_price`, `max_price`: Price range
    *   `ordering`: `price`, `-price`, `created_at`, `-created_at`

### Product Actions
*   **Related Products**: `/api/products/products/{id}/related/` (`GET`)
*   **New Arrivals**: `/api/products/products/new_arrivals/` (`GET`)

---

## Cart

Manage the user's shopping cart.

### Get Cart
*   **URL**: `/api/cart/my_cart/`
*   **Method**: `GET`
*   **Auth**: Required
*   **Response**:
    ```json
    {
      "id": 1,
      "items": [
        {
          "id": 10,
          "product": { "id": 5, "name": "..." },
          "quantity": 2,
          "subtotal": 200.0
        }
      ],
      "total_price": 200.0
    }
    ```

### Add Item
*   **URL**: `/api/cart/add_item/`
*   **Method**: `POST`
*   **Body**:
    ```json
    {
      "product": 5,
      "quantity": 1
    }
    ```

### Update Quantity
*   **URL**: `/api/cart/update_item_quantity/`
*   **Method**: `POST`
*   **Body**:
    ```json
    {
      "product": 5,
      "quantity": 3
    }
    ```

### Remove Item
*   **URL**: `/api/cart/remove_item/`
*   **Method**: `POST`
*   **Body**:
    ```json
    {
      "product": 5
    }
    ```

### Clear Cart
*   **URL**: `/api/cart/clear/`
*   **Method**: `POST`

---

## Orders

### Checkout (Create Order)
Create an order from the current cart.

*   **URL**: `/api/orders/checkout/`
*   **Method**: `POST`
*   **Auth**: Required
*   **Body**:
    ```json
    {
      "address_id": 1,
      "preferred_delivery_date": "2024-12-25",
      "preferred_delivery_slot": "morning",
      "delivery_notes": "Leave at reception",
      "payment_method": "TELR"  // or "COD"
    }
    ```
*   **Response (TELR)**:
    ```json
    {
      "message": "Order created successfully.",
      "order_id": 123,
      "payment_url": "https://secure.telr.com/gateway/...",
      "total_amount": 500.0,
      "payment_method": "TELR"
    }
    ```
*   **Response (COD)**:
    ```json
    {
      "message": "Order created successfully. Please pay upon delivery.",
      "order_id": 123,
      "total_amount": 500.0,
      "payment_method": "COD"
    }
    ```

### List Orders
*   **URL**: `/api/orders/`
*   **Method**: `GET`
*   **Auth**: Required

### Order Detail
*   **URL**: `/api/orders/{id}/`
*   **Method**: `GET`
*   **Auth**: Required

---

## Reviews

### List Reviews
*   **URL**: `/api/reviews/`
*   **Method**: `GET`
*   **Query Params**: `product={id}`, `user={id}`, `rating={1-5}`

### Create Review
*   **URL**: `/api/reviews/`
*   **Method**: `POST`
*   **Auth**: Required
*   **Body**:
    ```json
    {
      "product": 5,
      "rating": 5,
      "comment": "Great product!",
      "images": [...]
    }
    ```

---

## Notifications

### List Notifications
*   **URL**: `/api/notifications/`
*   **Method**: `GET`
*   **Auth**: Required

### Mark as Read
*   **Single**: `/api/notifications/{id}/mark_as_read/` (`POST`)
*   **All**: `/api/notifications/mark_all_as_read/` (`POST`)

---

## Marketing

### Banners/Media
Get active marketing banners.

*   **URL**: `/api/marketing/media/`
*   **Method**: `GET`
*   **Response**:
    ```json
    [
      {
        "id": 1,
        "title": "Summer Sale",
        "image": "http://...",
        "link": "/category/summer",
        "position": "home_hero"
      }
    ]
    ```
