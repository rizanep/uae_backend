# Google OAuth - Quick Setup Reference

## 🔑 Credentials (Already Configured)

```
Client ID:      850588370229-jtaul330kpqmi0m239itt4jrodshko78.apps.googleusercontent.com
Client Secret:  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
Redirect URI:   http://localhost:8000/api/users/google/callback/
(Production):   https://yourdomain.com/api/users/google/callback/
```

---

## 🚀 5-Minute Setup

### Frontend Installation

```bash
# For React
npm install @react-oauth/google axios

# For Vue
npm install vue3-google-login axios

# For vanilla JS
npm install axios
# CDN: <script src="https://accounts.google.com/gsi/client" async defer></script>
```

### 1. Initialize Google OAuth (React)

```jsx
import { GoogleOAuthProvider } from '@react-oauth/google';

<GoogleOAuthProvider clientId="850588370229-jtaul330kpqmi0m239itt4jrodshko78.apps.googleusercontent.com">
  <YourApp />
</GoogleOAuthProvider>
```

### 2. Add Login Button

```jsx
import { GoogleLogin } from '@react-oauth/google';

<GoogleLogin
  onSuccess={handleGoogleSuccess}
  onError={handleGoogleError}
/>
```

### 3. Send Code to Backend

```js
async function handleGoogleSuccess(credentialResponse) {
  const response = await axios.post(
    'http://localhost:8000/api/users/google/callback/',
    { code: credentialResponse.credential },
    { withCredentials: true }
  );

  localStorage.setItem('access_token', response.data.access);
  localStorage.setItem('user', JSON.stringify(response.data.user));
  window.location.href = '/dashboard';
}
```

### 4. Use Token in Requests

```js
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  withCredentials: true
});

api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export default api;
```

---

## 📊 Login Flow Diagram

```
User clicks "Login with Google"
           ↓
Frontend sends credential to backend
           ↓
Backend exchanges code for Google tokens
           ↓
Backend creates/updates user in database
           ↓
Backend issues JWT tokens & sets cookies
           ↓
Frontend stores tokens & redirects
           ↓
App ready to use!
```

---

## 🔌 API Endpoint

### POST /api/users/google/callback/

**Request:**
```json
{
  "code": "Google_authorization_code",
  "referral_code": "ABC12XYZ"  // Optional
}
```

**Response (200):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 123,
    "email": "user@gmail.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_email_verified": true,
    "google_id": "1234567890",
    "referral_code": "XYZ12ABC",
    "profile": { "preferred_language": "en" }
  }
}
```

**Cookies Set:**
- `access_token` (HTTP-only, 7 days)
- `refresh_token` (HTTP-only, 7 days)

---

## 🎯 What Gets Created

When user logs in with Google:

1. **User Account Created** (if new)
   - Email verified automatically
   - Profile picture downloaded
   - Language preference set (AR/EN)
   - Unique referral code generated
   - First order discount coupon created (10% off, 30 days)

2. **Google OAuth Token Stored**
   - Google access token
   - Google refresh token
   - Token expiry time

3. **JWT Tokens Issued**
   - Access token (short-lived)
   - Refresh token (long-lived)
   - Set as HTTP-only cookies

---

## 🔄 User Data Available After Login

```javascript
const user = JSON.parse(localStorage.getItem('user'));

console.log(user.id);                      // User ID
console.log(user.email);                   // Email
console.log(user.first_name);              // First name
console.log(user.last_name);               // Last name
console.log(user.phone_number);            // Phone (if added)
console.log(user.is_email_verified);       // true (from Google)
console.log(user.is_phone_verified);       // false (requires OTP)
console.log(user.google_id);               // Google ID
console.log(user.referral_code);           // Unique referral code
console.log(user.profile.profile_picture); // Profile pic URL
console.log(user.profile.preferred_language); // 'ar' or 'en'
console.log(user.created_at);              // Account creation time
```

---

## 💳 Automatic Rewards

When user logs in with referral code:

```javascript
// Store referral code before login
const ref = new URLSearchParams(window.location.search).get('ref');
localStorage.setItem('referral_code', ref);

// Include in callback request
const response = await axios.post('/api/users/google/callback/', {
  code: credential,
  referral_code: localStorage.getItem('referral_code')
});

// Response includes referral info
console.log(response.data.referral);
// {
//   "success": true,
//   "message": "Referral code applied successfully! Coupons have been added..."
// }
```

**Two coupons created:**
- Referee coupon: 15% off, min AED 100, 60 days
- Referrer coupon: 15% off, min AED 100, 60 days

---

## 🛡️ Security Notes

✅ **Secure by Default:**
- Tokens are HTTP-only (not accessible by JavaScript)
- Secure flag in production (HTTPS only)
- SameSite protection against CSRF
- Token expiration after 7 days

⚠️ **Keep These Safe:**
- Google Client Secret (backend only, never frontend)
- JWT Refresh Token (stored in HTTP-only cookie)
- User email/personal data

---

## 🧪 Quick Test

```bash
# 1. Start backend
cd /home/django_user/apps/uae_backend
python manage.py runserver

# 2. Open browser to frontend
http://localhost:3000/login  # or your frontend URL

# 3. Click "Login with Google"

# 4. Check console
localStorage.getItem('access_token')  // Should have JWT token
localStorage.getItem('user')          // Should have user data

# 5. Make API call
fetch('http://localhost:8000/api/users/users/1/', {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
  }
})
```

---

## 🚨 Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| **CORS Error** | Missing credentials | Add `withCredentials: true` |
| **401 Unauthorized** | Invalid/expired token | Refresh token using refresh endpoint |
| **Redirect mismatch** | Wrong redirect URI | Check .env and Google Console config |
| **User not created** | Email validation failed | Check backend logs |
| **No profile picture** | Download failed | Not critical, user can add later |

---

## 📱 Frontend Routes Needed

```
/login                          → Login page with Google button
/auth/google/callback          → Callback handler (receives code)
/dashboard                     → Protected route (redirected after login)
/logout                        → Logout handler
```

---

## 🔗 Related Endpoints

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/users/google/callback/` | POST | None | Exchange code for tokens |
| `/api/users/auth/logout/` | POST | JWT | Logout and blacklist token |
| `/api/users/auth/refresh/` | POST | None | Refresh expired token |
| `/api/users/users/me/` | GET | JWT | Get current user profile |
| `/api/users/users/{id}/` | GET/PUT | JWT | Get/update user |

---

## 📦 Package Versions (Recommended)

```json
{
  "@react-oauth/google": "^0.12.0",
  "axios": "^1.6.0",
  "react": "^18.0.0",
  "react-router-dom": "^6.0.0"
}
```

---

## 🎉 You're Ready!

Your frontend is ready to integrate Google OAuth. Follow the [complete guide](./GOOGLE_OAUTH_FRONTEND_GUIDE.md) for detailed implementation examples.

**Key Files:**
- Backend: `/api/users/google/callback/` - OAuth handler
- Backend Settings: `core/settings.py` - Google OAuth config
- User Model: `Users/models.py` - User & GoogleOAuthToken models
- Full Guide: `GOOGLE_OAUTH_FRONTEND_GUIDE.md` - Complete implementation

---

## 📞 Support

Need help? Check:
1. Backend logs: `python manage.py runserver` output
2. Browser console: `F12` → Network tab for API calls
3. Stored data: `localStorage` in browser DevTools
4. Google OAuth docs: https://developers.google.com/identity/gsi/web

**Everything is configured and ready to go!** 🚀
