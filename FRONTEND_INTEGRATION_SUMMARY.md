# Frontend Integration Summary - What You Need to Know

Quick overview for frontend developers getting started with Google OAuth login integration.

---

## 📌 What's Already Done (Backend)

✅ **Google OAuth Credentials Configured**
- Client ID configured in Django settings
- Client Secret securely stored in .env
- Redirect URI set up and ready
- Environment: `http://localhost:8000/api/users/google/callback/`

✅ **Backend Endpoints Ready**
- `POST /api/users/google/callback/` - Main OAuth endpoint
- `POST /api/users/auth/logout/` - Logout endpoint
- `POST /api/users/auth/refresh/` - Token refresh
- `GET /api/users/users/me/` - Get current user

✅ **User System**
- Auto-creates users on first Google login
- Auto-verifies email from Google
- Generates unique referral code per user
- Creates welcome discount coupon (10% off, 30 days)
- Stores Google profile picture & language preference
- Supports referral rewards system

✅ **Security**
- HTTP-only cookies for token storage
- JWT tokens with expiration
- CSRF protection
- Rate limiting on auth endpoints
- Token refresh mechanism

---

## 🎯 What You Need to Do (Frontend)

### 1. Install Google Sign-In Library

```bash
# React
npm install @react-oauth/google

# Vue
npm install vue3-google-login

# Vanilla/Angular
# Just include the Google API script tag
```

### 2. Initialize Google OAuth

```javascript
// React example (see code examples file for others)
<GoogleOAuthProvider clientId="850588370229-jtaul330kpqmi0m239itt4jrodshko78.apps.googleusercontent.com">
  <App />
</GoogleOAuthProvider>
```

### 3. Create Login Button

```jsx
<GoogleLogin
  onSuccess={handleGoogleSuccess}
  onError={handleGoogleError}
/>
```

### 4. Handle Success Response

```javascript
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

### 5. Protect Routes & Add Auth Headers

```javascript
// Add token to all API requests
api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

---

## 🚀 Key Features Your Users Get

### Automatic on Google Login:
- ✅ Account created instantly
- ✅ Email verified automatically
- ✅ Profile picture synced from Google
- ✅ Language preference set (AR/EN based on Google locale)
- ✅ Unique referral code generated
- ✅ Welcome discount created (10% off)
- ✅ JWT tokens issued

### Available After Login:
- User ID, email, name, phone (optional)
- Profile picture URL
- Referral code for inviting friends
- Available coupons (4+ endpoints to manage them)
- Email & phone verification status
- Referral reward details

---

## 📊 Data Flow

```
Frontend                          Backend                      Google
   |                                |                            |
   |------ credential (JWT) ------->|                            |
   |                                |------ exchange code ------->|
   |                                |<----- tokens + user info ---|
   |                                |
   |<--- JWT + user data + cookies---|
   |
   |------ API calls + JWT token ---->|
   |                                   |
   |<---- Protected resources ---------|
```

---

## 💾 Data Stored Locally

After successful login, your frontend has:

```javascript
localStorage.access_token      // JWT token (use in headers)
localStorage.refresh_token     // For token refresh
localStorage.user              // User object
  - id
  - email
  - first_name, last_name
  - phone_number (if added)
  - is_email_verified
  - is_phone_verified
  - google_id
  - referral_code
  - profile { picture, language }

// Cookies (automatic, HTTP-only)
document.cookie                // access_token
document.cookie                // refresh_token
```

---

## 🔗 All Available Endpoints

| Endpoint | Method | Auth? | Purpose |
|----------|--------|-------|---------|
| `/users/google/callback/` | POST | No | Exchange code for tokens |
| `/users/auth/logout/` | POST | JWT | Logout |
| `/users/auth/refresh/` | POST | No | Refresh expired token |
| `/users/users/me/` | GET | JWT | Get current user |
| `/users/users/{id}/` | GET/PUT | JWT | Get/update user |
| `/marketing/coupons/` | GET | JWT | List user's coupons |
| `/marketing/admin/coupons/` | GET/POST | Admin | Manage all coupons |
| `/orders/checkout/` | POST | JWT | Create order |
| `/orders/checkout_summary/` | POST | JWT | Preview order |

---

## ⚙️ Configuration Checklist

- [ ] Google Client ID added to frontend env
- [ ] Google Sign-In library installed
- [ ] Login page created with Google button
- [ ] Success handler redirects to dashboard
- [ ] Tokens stored in localStorage/cookies
- [ ] Auth interceptor adds token to requests
- [ ] Protected routes check for auth
- [ ] Logout clears tokens & redirects
- [ ] Error handling shows user feedback
- [ ] Referral code support (optional)
- [ ] CORS credentials enabled (`withCredentials: true`)
- [ ] API base URL configured

---

## 🧪 Test Locally

```bash
# Terminal 1: Start backend
cd /home/django_user/apps/uae_backend
python manage.py runserver

# Terminal 2: Start frontend
npm run dev

# Browser: Navigate to frontend login page
http://localhost:3000/login  # or your port

# Click "Login with Google"
# Complete Google consent
# Should redirect to dashboard with tokens
```

---

## 🆘 Troubleshooting Guide

| Problem | Debug Steps |
|---------|------------|
| **CORS error** | Check `withCredentials: true` in axios |
| **Token not in header** | Verify axios interceptor is attached |
| **401 Unauthorized** | Check token expiration, implement refresh |
| **Redirect mismatch** | Verify `http://localhost:8000/api/users/google/callback/` in env |
| **No coupons showing** | Check user's profile, try network tab |
| **User not logging in** | Check backend logs, verify credential format |
| **Profile picture missing** | Not critical, user can add later |

**Console checks:**
```javascript
localStorage.getItem('access_token')        // Should have JWT
localStorage.getItem('user')                // Should have user data
fetch('http://localhost:8000/api/users/users/me/', {
  headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
})  // Should return user
```

---

## 📚 Quick Code Snippets

### Axios Setup
```js
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  withCredentials: true,
});

api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export default api;
```

### Protected Route (React)
```jsx
<Route
  path="/dashboard"
  element={
    localStorage.getItem('access_token') ? (
      <Dashboard />
    ) : (
      <Navigate to="/login" />
    )
  }
/>
```

### Use API
```js
import api from './api/client';

// GET
const response = await api.get('/marketing/coupons/');

// POST
const order = await api.post('/orders/checkout/', orderData);

// PUT
const updated = await api.put('/users/users/1/', { phone_number: '+971...' });
```

---

## 📖 Documentation Files

| File | Content |
|------|---------|
| `GOOGLE_OAUTH_QUICK_REFERENCE.md` | 5-minute setup guide |
| `GOOGLE_OAUTH_FRONTEND_GUIDE.md` | Complete implementation guide |
| `GOOGLE_OAUTH_CODE_EXAMPLES.md` | Code for React, Vue, Next.js, Angular, Vanilla JS |

---

## 🎯 Next Steps

1. **Choose Your Framework** (React, Vue, Next.js, etc.)
2. **Follow Code Examples** for your framework
3. **Test Login Locally** with Google account
4. **Implement Protected Routes** in your app
5. **Add API Interceptors** for token management
6. **Display User Info** on dashboard
7. **Implement Logout** functionality
8. **Test Referral System** (optional)
9. **Deploy to Production** with HTTPS

---

## 🔐 Production Checklist

- [ ] Update `GOOGLE_OAUTH_REDIRECT_URI` to production domain
- [ ] Enable HTTPS (`secure=True` in cookies)
- [ ] Update Django `ALLOWED_HOSTS` with production domain
- [ ] Update CORS settings for production domain
- [ ] Update frontend `API_URL` to production API
- [ ] Update Google OAuth credentials redirect URI in Google Console
- [ ] Enable rate limiting (already done on backend)
- [ ] Set `DEBUG=False` in Django
- [ ] Use environment variables for secrets
- [ ] Test full login flow in production

---

## 💡 Remember

- **Google creates credentials on first login** (no separate signup needed)
- **Email is auto-verified** from Google account
- **Profile picture is auto-synced** from Google
- **Tokens expire in 7 days** (implement refresh)
- **HTTP-only cookies are most secure** (use them)
- **Always use HTTPS in production**
- **Test referral code for reward system**
- **Check backend logs** when frontend has issues

---

## 🚀 You're Ready!

Everything is configured on the backend. You just need to:
1. Add the Google button to your frontend
2. Send the code to `/api/users/google/callback/`
3. Store the tokens
4. Use tokens in API requests

**That's it!** The rest is automatic. 🎉

---

## 📞 Need Details?

- Full guide: See `GOOGLE_OAUTH_FRONTEND_GUIDE.md`
- Code examples: See `GOOGLE_OAUTH_CODE_EXAMPLES.md`
- Backend API: Check `/api/users/` endpoints
- Issues: Check backend logs first!

Happy coding! 🚀
