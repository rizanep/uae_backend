# Google OAuth Login - Frontend Integration Guide

Complete guide for integrating Google OAuth login in your frontend application.

---

## 🎯 Overview

The backend has Google OAuth credentials configured and ready:
- **Client ID:** `850588370229-jtaul330kpqmi0m239itt4jrodshko78.apps.googleusercontent.com`
- **Redirect URI:** `http://localhost:8000/api/users/google/callback/`

The frontend needs to:
1. Initialize Google Sign-In
2. Trigger the Google OAuth flow
3. Send the authorization code to the backend
4. Receive JWT tokens and user data
5. Store tokens in cookies/localStorage
6. Handle optional referral code

---

## 📌 OAuth Flow Architecture

```
┌─────────────────┐
│   Frontend      │
│   (React/Vue)   │
└────────┬────────┘
         │
         │ 1. User clicks "Login with Google"
         │
         ▼
┌──────────────────────────┐
│  Google OAuth 2.0        │
│  - Consent Screen        │
│  - Authorization Code    │
└────────┬─────────────────┘
         │
         │ 2. Send code to backend
         │
         ▼
┌───────────────────────────────┐
│  Backend Callback              │
│  /api/users/google/callback/   │
│  - Exchange code for tokens    │
│  - Create/update user          │
│  - Issue JWT tokens            │
│  - Set HTTP-only cookies       │
└────────┬──────────────────────┘
         │
         │ 3. Receive JWT tokens + user data
         │
         ▼
┌──────────────────────┐
│  Frontend            │
│  - Store tokens      │
│  - Redirect to home  │
│  - Load user profile │
└──────────────────────┘
```

---

## 🔧 Implementation Steps

### Step 1: Install Google Sign-In Library

For React:
```bash
npm install @react-oauth/google
# or
npm install react-google-login
```

For Vue:
```bash
npm install vue3-google-login
```

For vanilla JS:
```html
<script src="https://accounts.google.com/gsi/client" async defer></script>
```

### Step 2: Initialize Google Sign-In (React Example)

```jsx
import { GoogleOAuthProvider, GoogleLogin } from '@react-oauth/google';

export default function App() {
  return (
    <GoogleOAuthProvider clientId="850588370229-jtaul330kpqmi0m239itt4jrodshko78.apps.googleusercontent.com">
      <LoginPage />
    </GoogleOAuthProvider>
  );
}
```

### Step 3: Create Login Component

#### React Implementation:
```jsx
import { GoogleLogin } from '@react-oauth/google';
import axios from 'axios';

export function GoogleLoginButton() {
  const handleGoogleSuccess = async (credentialResponse) => {
    try {
      const code = credentialResponse.credential; // JWT token from Google
      
      // Send to backend callback endpoint
      const response = await axios.post('http://localhost:8000/api/users/google/callback/', {
        code: code,
        referral_code: localStorage.getItem('referral_code') // Optional
      }, {
        withCredentials: true // Important: include cookies
      });

      // Store JWT tokens
      localStorage.setItem('access_token', response.data.access);
      localStorage.setItem('refresh_token', response.data.refresh);
      
      // Cookies are automatically set by backend
      
      // Store user info
      localStorage.setItem('user', JSON.stringify(response.data.user));

      // Redirect to home
      window.location.href = '/dashboard';
    } catch (error) {
      console.error('Google login failed:', error);
      alert(error.response?.data?.detail || 'Login failed');
    }
  };

  const handleGoogleError = () => {
    console.log('Login Failed');
  };

  return (
    <GoogleLogin
      onSuccess={handleGoogleSuccess}
      onError={handleGoogleError}
    />
  );
}
```

#### Vue Implementation:
```vue
<template>
  <div>
    <GoogleLogin
      :clientId="googleClientId"
      @success="handleGoogleSuccess"
      @error="handleGoogleError"
    />
  </div>
</template>

<script setup>
import { GoogleLogin } from '@react-oauth/google'; // Or use vue3-google-login
import axios from 'axios';

const googleClientId = '850588370229-jtaul330kpqmi0m239itt4jrodshko78.apps.googleusercontent.com';

async function handleGoogleSuccess(response) {
  try {
    const { data } = await axios.post(
      'http://localhost:8000/api/users/google/callback/',
      { code: response.credential },
      { withCredentials: true }
    );

    localStorage.setItem('access_token', data.access);
    localStorage.setItem('refresh_token', data.refresh);
    localStorage.setItem('user', JSON.stringify(data.user));

    window.location.href = '/dashboard';
  } catch (error) {
    console.error('Login failed:', error);
  }
}

function handleGoogleError() {
  console.error('Login failed');
}
</script>
```

#### Vanilla JavaScript:
```html
<div id="g_id_onload"
     data-client_id="850588370229-jtaul330kpqmi0m239itt4jrodshko78.apps.googleusercontent.com"
     data-callback="handleCredentialResponse">
</div>
<div class="g_id_signin" data-type="standard"></div>

<script>
async function handleCredentialResponse(response) {
  try {
    const result = await fetch('http://localhost:8000/api/users/google/callback/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        code: response.credential,
        referral_code: localStorage.getItem('referral_code')
      }),
      credentials: 'include' // Important: include cookies
    });

    const data = await result.json();
    
    localStorage.setItem('access_token', data.access);
    localStorage.setItem('refresh_token', data.refresh);
    localStorage.setItem('user', JSON.stringify(data.user));

    window.location.href = '/dashboard';
  } catch (error) {
    console.error('Login failed:', error);
  }
}

window.onload = function () {
  google.accounts.id.initialize({
    client_id: '850588370229-jtaul330kpqmi0m239itt4jrodshko78.apps.googleusercontent.com'
  });
  google.accounts.id.renderButton(
    document.querySelector('.g_id_signin'),
    { theme: 'outline', size: 'large' }
  );
};
</script>
```

---

## 🔗 API Endpoints

### Google OAuth Callback

**Endpoint:** `POST /api/users/google/callback/`

**Also accepts:** `GET /api/users/google/callback/?code=...`

**Request Body:**
```json
{
  "code": "Google_Authorization_Code_or_JWT_Token",
  "referral_code": "ABC12XYZ"  // Optional
}
```

**Successful Response (200 OK):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 123,
    "email": "user@gmail.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": null,
    "is_email_verified": true,
    "is_phone_verified": false,
    "google_id": "1234567890",
    "role": "user",
    "created_at": "2026-04-03T10:30:00Z",
    "profile": {
      "profile_picture": "...",
      "preferred_language": "en"
    },
    "referral_code": "ABC12XYZ"
  }
}
```

**Also sets HTTP-only cookies:**
- `access_token` - JWT access token (7 days)
- `refresh_token` - JWT refresh token (7 days)

**Error Response (400):**
```json
{
  "detail": "Failed to authenticate with Google",
  "error": "Invalid authorization code",
  "google_response": {...}
}
```

---

## 💾 Token Management

### Store Tokens
```javascript
// Option 1: localStorage (less secure but easier)
localStorage.setItem('access_token', response.data.access);
localStorage.setItem('refresh_token', response.data.refresh);

// Option 2: Memory (more secure but lost on refresh)
// Option 3: Rely on HTTP-only cookies (most secure)
// Recommended: Use cookies + memory for best security
```

### Use Access Token in Requests
```javascript
// Axios interceptor
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  withCredentials: true // Always include cookies
});

// Add token to headers
api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle token expiration
api.interceptors.response.use(
  response => response,
  async error => {
    if (error.response?.status === 401) {
      // Try to refresh token
      try {
        const refreshToken = localStorage.getItem('refresh_token');
        const response = await axios.post('http://localhost:8000/api/users/auth/refresh/', {
          refresh: refreshToken
        }, { withCredentials: true });

        localStorage.setItem('access_token', response.data.access);
        return api(error.config);
      } catch (refreshError) {
        // Redirect to login
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;
```

---

## 📱 With Referral Code

Enable referral rewards during Google login:

```javascript
// Before trigger login, store referral code
const referralCode = new URLSearchParams(window.location.search).get('ref');
if (referralCode) {
  localStorage.setItem('referral_code', referralCode);
}

// In login handler
const response = await axios.post('http://localhost:8000/api/users/google/callback/', {
  code: credentialResponse.credential,
  referral_code: localStorage.getItem('referral_code')
}, { withCredentials: true });

// After successful login, clear referral code
localStorage.removeItem('referral_code');
```

**Response will include referral info:**
```json
{
  "access": "...",
  "referral": {
    "success": true,
    "message": "Referral code applied successfully! Coupons have been added to your account."
  }
}
```

---

## 🔐 Security Best Practices

### ✅ Do's

1. **Always use HTTPS** in production
   ```javascript
   // Development
   GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/api/users/google/callback/
   
   // Production
   GOOGLE_OAUTH_REDIRECT_URI=https://yourdomain.com/api/users/google/callback/
   ```

2. **Enable secure cookies**
   ```javascript
   // Backend sets secure cookies automatically when DEBUG=False
   ```

3. **Use withCredentials in CORS requests**
   ```javascript
   axios.post(url, data, { withCredentials: true })
   ```

4. **Store sensitive tokens only in HTTP-only cookies**
   ```javascript
   // Let the backend handle secure cookies
   // Use localStorage only for non-sensitive data
   ```

5. **Handle token expiration gracefully**
   ```javascript
   // Implement token refresh mechanism
   ```

6. **Validate state parameter**
   ```javascript
   // The library handles this automatically
   ```

### ❌ Don'ts

1. ❌ Don't log tokens to console in production
2. ❌ Don't store tokens in localStorage alongside cookies
3. ❌ Don't send tokens in URLs
4. ❌ Don't use HTTP in production (use HTTPS)
5. ❌ Don't skip CORS credentials
6. ❌ Don't hardcode tokens in frontend

---

## 🚀 Complete Login Component Example (React)

```jsx
import React, { useState } from 'react';
import { GoogleOAuthProvider, GoogleLogin } from '@react-oauth/google';
import axios from 'axios';

const GOOGLE_CLIENT_ID = '850588370229-jtaul330kpqmi0m239itt4jrodshko78.apps.googleusercontent.com';

export function LoginPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleGoogleSuccess = async (credentialResponse) => {
    setLoading(true);
    setError(null);

    try {
      // Get referral code from URL if present
      const params = new URLSearchParams(window.location.search);
      const referralCode = params.get('ref');

      // Send code to backend
      const response = await axios.post(
        'http://localhost:8000/api/users/google/callback/',
        {
          code: credentialResponse.credential,
          referral_code: referralCode || undefined
        },
        { withCredentials: true }
      );

      const { access, refresh, user, referral } = response.data;

      // Store tokens
      localStorage.setItem('access_token', access);
      localStorage.setItem('refresh_token', refresh);
      localStorage.setItem('user', JSON.stringify(user));

      // Show success message
      if (referral?.success) {
        alert(referral.message);
      }

      // Redirect to dashboard
      window.location.href = '/dashboard';
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Login failed. Please try again.';
      setError(errorMsg);
      console.error('Google login error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleError = () => {
    setError('Google login failed. Please try again.');
  };

  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <div className="login-container">
        <h1>Login with Google</h1>
        
        {error && <div className="error-message">{error}</div>}
        
        <GoogleLogin
          onSuccess={handleGoogleSuccess}
          onError={handleGoogleError}
          disabled={loading}
        />
      </div>
    </GoogleOAuthProvider>
  );
}

export default LoginPage;
```

---

## 🧪 Testing the Integration

### Local Testing

1. **Update .env** for local development:
   ```env
   GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/api/users/google/callback/
   DEBUG=True
   ```

2. **Frontend URL should be:**
   - `http://localhost:3000` (React dev server)
   - `http://localhost:5173` (Vite dev server)

3. **Test flow:**
   ```bash
   1. Start backend: python manage.py runserver
   2. Start frontend: npm run dev
   3. Navigate to login page
   4. Click "Login with Google"
   5. Complete Google consent screen
   6. Check browser console for tokens
   7. Verify redirect to dashboard
   ```

### Postman Testing

```bash
# 1. Get authorization code from Google (manual process)
# Open in browser:
# https://accounts.google.com/o/oauth2/v2/auth?client_id=850588370229-jtaul330kpqmi0m239itt4jrodshko78.apps.googleusercontent.com&redirect_uri=http://localhost:8000/api/users/google/callback/&response_type=code&scope=email%20profile

# 2. Copy the 'code' parameter from redirect URL

# 3. Test in Postman:
POST http://localhost:8000/api/users/google/callback/
Content-Type: application/json

{
  "code": "4/0AeaYSH..."
}

# Response should contain access, refresh, and user data
```

### Debugging Tips

```javascript
// Log token details
const token = localStorage.getItem('access_token');
const decoded = JSON.parse(atob(token.split('.')[1]));
console.log('Token expires at:', new Date(decoded.exp * 1000));

// Check cookies
console.log('Cookies:', document.cookie);

// Verify CORS
console.log('withCredentials:', true);

// Test API call
fetch('http://localhost:8000/api/users/users/me/', {
  headers: {
    'Authorization': `Bearer ${token}`
  },
  credentials: 'include'
})
```

---

## 📋 Environment Variables (Frontend)

Create `.env` in your frontend root:

```env
VITE_API_URL=http://localhost:8000/api
VITE_GOOGLE_CLIENT_ID=850588370229-jtaul330kpqmi0m239itt4jrodshko78.apps.googleusercontent.com
```

Usage:
```javascript
const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
```

---

## 🔄 Logout Implementation

```javascript
function handleLogout() {
  // Clear tokens
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user');

  // Call backend logout (optional)
  axios.post('/api/users/auth/logout/', {}, {
    withCredentials: true
  });

  // Sign out from Google
  google.accounts.id.disableAutoSelect();

  // Redirect to login
  window.location.href = '/login';
}
```

---

## 🆘 Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| **CORS error** | Ensure `withCredentials: true` and backend CORS is configured |
| **Code is invalid** | Code expires in 10 minutes, must be exchanged immediately |
| **Token not in headers** | Check axios interceptor is attached, content-type is set |
| **Redirect URI mismatch** | Must match exactly: `http://localhost:8000/api/users/google/callback/` |
| **Cookie not set** | Must use HTTPS in production, use `secure=False` in DEBUG mode |
| **User not created** | Check backend logs, may be inactive or validation errors |
| **Referral not applied** | Include referral_code in callback request, check if user already referred |

---

## 📚 Resources

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Google Sign-In JavaScript Library](https://developers.google.com/identity/gsi/web)
- [React OAuth Library](https://www.npmjs.com/package/@react-oauth/google)
- [JWT Tokens Explanation](https://jwt.io/introduction)

---

## 📞 Backend API Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/users/google/callback/` | POST/GET | Exchange code for tokens and create user |
| `/api/users/auth/logout/` | POST | Logout and blacklist token |
| `/api/users/auth/refresh/` | POST | Refresh access token |
| `/api/users/users/me/` | GET | Get current user profile |

---

## ✅ Checklist

- [ ] Google OAuth credentials added to .env
- [ ] Frontend library installed (@react-oauth/google or vue3-google-login)
- [ ] Google Sign-In button component created
- [ ] Credentials sent to backend callback endpoint
- [ ] JWT tokens stored securely
- [ ] Token expiration handling implemented
- [ ] Axios/Fetch interceptor configured
- [ ] Logout functionality implemented
- [ ] CORS credentials enabled
- [ ] Error handling and user feedback added
- [ ] Tested in development environment
- [ ] HTTPS configured for production
- [ ] Referral code support (optional) implemented

**You're all set to integrate Google OAuth login!** 🎉
