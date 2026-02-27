# API Reference

This document provides a comprehensive reference for the UAE Ecommerce Backend API.

## Base URL
`/api/`

## Authentication
Most endpoints require authentication using JWT Tokens.
*   **Header**: `Authorization: Bearer <access_token>`
*   **Cookies**: `access_token` and `refresh_token` (HttpOnly) are set automatically on login/register.

---

## 1. Authentication & Users (`/api/auth/` & `/api/users/`)

### 1.1 Authentication

#### Login (Email/Password)
*   **URL**: `/api/auth/login/`
*   **Method**: `POST`
*   **Body**:
    ```json
    {
      "email": "user@example.com",
      "password": "secretpassword"
    }
    ```
*   **Response**:
    ```json
    {
      "access": "jwt_access_token",
      "refresh": "jwt_refresh_token",
      "user": { ...user_details... }
    }
    ```

#### Register (Email/Password)
*   **URL**: `/api/users/register/`
*   **Method**: `POST`
*   **Body**:
    ```json
    {
      "email": "newuser@example.com",
      "phone_number": "+971501234567",
      "password": "secretpassword",
      "password_confirm": "secretpassword",
      "first_name": "John",
      "last_name": "Doe"
    }
    ```

#### OTP Login/Register (Phone/Email)
1.  **Request OTP**
    *   **URL**: `/api/auth/otp/request/`
    *   **Method**: `POST`
    *   **Body**: `{"identifier": "+971501234567"}` (or email)
2.  **Verify OTP & Login**
    *   **URL**: `/api/auth/otp/login/`
    *   **Method**: `POST`
    *   **Body**:
        ```json
        {
          "identifier": "+971501234567",
          "otp": "123456"
        }
        ```

#### Google Auth
*   **URL**: `/api/auth/google/`
*   **Method**: `POST`
*   **Body**: `{"token": "google_id_token"}`

#### Logout
*   **URL**: `/api/auth/logout/`
*   **Method**: `POST`
*   **Body**: `{"refresh": "refresh_token"}` (Optional if using cookies)

### 1.2 User Profile

#### Get Current User
*   **URL**: `/api/users/me/`
*   **Method**: `GET`
*   **Auth**: Required

#### Update Profile
*   **URL**: `/api/users/me/`
*   **Method**: `PATCH`
*   **Body**:
    ```json
    {
      "first_name": "Jane",
      "profile": {
        "gender": "F",
        "date_of_birth": "1990-01-01"
      }
    }
    ```

#### Change Password
*   **URL**: `/api/users/me/change-password/`
*   **Method**: `POST`
*   **Body**:
    ```json
    {
      "old_password": "oldpass",
      "new_password": "newpass",
      "new_password_confirm": "newpass"
    }
    ```

### 1.3 User Management (Admin Only)

#### List All Users (Including Deleted)
*   **URL**: `/api/users/all/`
*   **Method**: `GET`
*   **Auth**: Admin Required

#### Restore Deleted User
*   **URL**: `/api/users/<id>/restore/`
*   **Method**: `POST`
*   **Auth**: Admin Required

#### Set User Role
*   **URL**: `/api/users/<id>/set-role/`
*   **Method**: `POST`
*   **Auth**: Admin Required
*   **Body**: `{"role": "admin"}` (or `customer`, `staff`)

### 1.4 Addresses (`/api/addresses/`)

#### List Addresses
*   **URL**: `/api/addresses/`
*   **Method**: `GET`

#### Create Address
*   **URL**: `/api/addresses/`
*   **Method**: `POST`
*   **Body**:
    ```json
    {
      "label": "Home",
      "full_name": "John Doe",
      "phone_number": "+971501234567",
      "building_name": "Burj Khalifa",
      "flat_villa_number": "101",
      "street_address": "Sheikh Zayed Rd",
      "area": "Downtown",
      "city": "Dubai",
      "emirate": "DUBAI",
      "country": "United Arab Emirates"
    }
    ```

#### Set Default
*   **URL**: `/api/addresses/<id>/set-default/`
*   **Method**: `POST`

---

## 2. Products (`/api/products/`)

### 2.1 Products

#### List Products
*   **URL**: `/api/products/products/`
*   **Method**: `GET`
*   **Query Params**:
    *   `search`: Name, description, SKU
    *   `category`: Category ID
    *   `category_slug`: Category Slug
    *   `min_price`, `max_price`: Price range
    *   `ordering`: `price`, `-price`, `created_at`

#### Product Detail
*   **URL**: `/api/products/products/<id>/`
*   **Method**: `GET`

#### New Arrivals
*   **URL**: `/api/products/products/new_arrivals/`
*   **Method**: `GET`

#### Related Products
*   **URL**: `/api/products/products/<id>/related/`
*   **Method**: `GET`

### 2.2 Product Management (Admin Only)

#### Create Product
*   **URL**: `/api/products/products/`
*   **Method**: `POST`
*   **Auth**: Admin Required
*   **Body**:
    ```json
    {
      "category": 1,
      "name": "IPhone 15",
      "description": "Latest model",
      "price": "3999.00",
      "stock": 50,
      "sku": "IPH-15-BLK",
      "expected_delivery_time": "Next Day"
    }
    ```

#### Update Product
*   **URL**: `/api/products/products/<id>/`
*   **Method**: `PATCH`
*   **Auth**: Admin Required

#### Delete Product
*   **URL**: `/api/products/products/<id>/`
*   **Method**: `DELETE`
*   **Auth**: Admin Required

### 2.3 Categories

#### List Categories
*   **URL**: `/api/products/categories/`
*   **Method**: `GET`

#### Create Category (Admin Only)
*   **URL**: `/api/products/categories/`
*   **Method**: `POST`
*   **Auth**: Admin Required
*   **Body**:
    ```json
    {
      "name": "Electronics",
      "slug": "electronics",
      "description": "Gadgets and devices"
    }
    ```

---

## 3. Cart (`/api/cart/`)

#### View Cart
*   **URL**: `/api/cart/my_cart/`
*   **Method**: `GET`
*   **Auth**: Required

#### Add Item
*   **URL**: `/api/cart/add_item/`
*   **Method**: `POST`
*   **Body**:
    ```json
    {
      "product": 1,
      "quantity": 2
    }
    ```

#### Update Quantity
*   **URL**: `/api/cart/update_item_quantity/`
*   **Method**: `POST`
*   **Body**:
    ```json
    {
      "product": 1,
      "quantity": 5
    }
    ```

#### Remove Item
*   **URL**: `/api/cart/remove_item/`
*   **Method**: `POST`
*   **Body**: `{"product": 1}`

#### Clear Cart
*   **URL**: `/api/cart/clear/`
*   **Method**: `POST`

---

## 4. Orders (`/api/orders/`)

#### List Orders
*   **URL**: `/api/orders/`
*   **Method**: `GET`
*   **Auth**: Required

#### Checkout
*   **URL**: `/api/orders/checkout/`
*   **Method**: `POST`
*   **Body**:
    ```json
    {
      "address_id": 1,
      "preferred_delivery_date": "2023-12-25",
      "preferred_delivery_slot": "9AM - 12PM",
      "delivery_notes": "Leave at reception"
    }
    ```
*   **Response**:
    ```json
    {
      "message": "Order created successfully.",
      "order_id": 123,
      "payment_url": "https://secure.telr.com/...",
      "total_amount": 500.00
    }
    ```

#### Cancel Order
*   **URL**: `/api/orders/<id>/cancel_order/`
*   **Method**: `POST`

#### Admin Update Status (Admin Only)
*   **URL**: `/api/orders/<id>/admin_update_status/`
*   **Method**: `POST`
*   **Auth**: Admin Required
*   **Body**:
    ```json
    {
      "status": "shipped",
      "notes": "Handed over to courier"
    }
    ```

---

## 5. Reviews (`/api/reviews/`)

#### List Reviews
*   **URL**: `/api/reviews/`
*   **Method**: `GET`
*   **Query Params**: `product=<id>`

#### Create Review
*   **URL**: `/api/reviews/`
*   **Method**: `POST`
*   **Auth**: Required
*   **Content-Type**: `multipart/form-data`
*   **Body**:
    *   `product`: 1
    *   `rating`: 5
    *   `comment`: "Great product!"
    *   `uploaded_images`: [file1, file2]

#### Toggle Visibility (Admin Only)
*   **URL**: `/api/reviews/<id>/toggle_visibility/`
*   **Method**: `POST`
*   **Auth**: Admin Required

---

## 6. Notifications (`/api/notifications/`)

#### List Notifications
*   **URL**: `/api/notifications/`
*   **Method**: `GET`
*   **Auth**: Required

#### Mark As Read
*   **URL**: `/api/notifications/<id>/mark_as_read/`
*   **Method**: `POST`

#### Mark All As Read
*   **URL**: `/api/notifications/mark_all_as_read/`
*   **Method**: `POST`
