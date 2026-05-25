# OTP Authentication & Contact Update API

This document details the API endpoints for OTP-based authentication and contact (Email/Phone) updates.

## 1. Request OTP

Use this endpoint to request an OTP for login or for updating contact details.

- **URL:** `/api/auth/otp/request/`
- **Method:** `POST`
- **Auth Required:** No (for login) / Yes (optional, if context requires it)

### Payload Parameters

| Parameter      | Type   | Required | Description                                      |
| :------------- | :----- | :------- | :----------------------------------------------- |
| `otp_type`     | String | Yes      | Must be `"email"` or `"phone"`.                  |
| `email`        | String | Conditional | Required if `otp_type` is `"email"`.             |
| `phone_number` | String | Conditional | Required if `otp_type` is `"phone"`.             |

### Example Request (Email)

```json
{
    "otp_type": "email",
    "email": "user@example.com"
}
```

### Example Request (Phone)

```json
{
    "otp_type": "phone",
    "phone_number": "+1234567890"
}
```

### Success Response

```json
{
    "detail": "OTP sent to email",
    "otp_type": "email",
    "contact": "user@example.com",
    "expires_in_minutes": 5
}
```

---

## 2. Login with OTP

Use this endpoint to log in using the OTP received. Upon successful login, the user's contact method (email or phone) will be automatically marked as **verified**.

- **URL:** `/api/auth/otp/login/`
- **Method:** `POST`
- **Auth Required:** No

### Payload Parameters

| Parameter      | Type   | Required | Description                                      |
| :------------- | :----- | :------- | :----------------------------------------------- |
| `otp_type`     | String | Yes      | `"email"` or `"phone"`.                          |
| `otp_code`     | String | Yes      | The 6-digit OTP code received.                   |
| `email`        | String | Conditional | Required if `otp_type` is `"email"`.             |
| `phone_number` | String | Conditional | Required if `otp_type` is `"phone"`.             |

### Example Request

```json
{
    "otp_type": "email",
    "email": "user@example.com",
    "otp_code": "123456"
}
```

### Success Response

Returns JWT tokens and user data.

```json
{
    "access": "ey...",
    "refresh": "ey...",
    "user": {
        "id": 1,
        "email": "user@example.com",
        "is_email_verified": true,
        ...
    }
}
```

---

## 3. Verify & Update Contact Information

Use this endpoint to verify a new email or phone number and update the user's profile.
**Note:** You must first request an OTP for the *new* contact information using the `/api/auth/otp/request/` endpoint.

- **URL:** `/api/auth/otp/verify-update/`
- **Method:** `POST`
- **Auth Required:** Yes (User must be logged in)

### Payload Parameters

| Parameter      | Type   | Required | Description                                      |
| :------------- | :----- | :------- | :----------------------------------------------- |
| `otp_type`     | String | Yes      | `"email"` or `"phone"`.                          |
| `otp_code`     | String | Yes      | The 6-digit OTP code sent to the **new** contact.|
| `email`        | String | Conditional | The **new** email address (if updating email).   |
| `phone_number` | String | Conditional | The **new** phone number (if updating phone).    |

### Example Request (Update Email)

1.  User requests OTP for `new-email@example.com` via `/api/auth/otp/request/`.
2.  User submits verification to this endpoint:

```json
{
    "otp_type": "email",
    "email": "new-email@example.com",
    "otp_code": "654321"
}
```

### Success Response

```json
{
    "detail": "Email updated successfully.",
    "user": {
        "id": 1,
        "email": "new-email@example.com",
        "is_email_verified": true,
        ...
    }
}
```

### Error Responses

*   **400 Bad Request:**
    *   "This email is already in use."
    *   "Invalid or expired OTP."
    *   "OTP does not match the provided email."
