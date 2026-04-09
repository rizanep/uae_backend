# Frontend Integration Documentation Index

Complete guide to implementing Google OAuth login in your frontend application.

---

## 📚 Documentation Files

### 1. **FRONTEND_INTEGRATION_SUMMARY.md** ⭐ START HERE
**For:** Frontend developers first getting started  
**Contains:** Quick overview, key features, what's done vs. what you need to do  
**Read Time:** 5 minutes  
**Best For:** Understanding the big picture

### 2. **GOOGLE_OAUTH_QUICK_REFERENCE.md**
**For:** Developers ready to implement  
**Contains:** 5-minute setup, credentials, API endpoints, quick test code  
**Read Time:** 10 minutes  
**Best For:** Getting up and running quickly

### 3. **GOOGLE_OAUTH_FRONTEND_GUIDE.md**
**For:** Complete implementation details  
**Contains:** Full architecture, step-by-step implementation, security best practices, troubleshooting  
**Read Time:** 30 minutes  
**Best For:** Understanding all details before coding

### 4. **GOOGLE_OAUTH_CODE_EXAMPLES.md**
**For:** Copy-paste ready code  
**Contains:** Complete working code for React, Vue, Next.js, Angular, Vanilla JS  
**Read Time:** Variable, pick your framework  
**Best For:** Actual implementation

---

## 🎯 Reading Path by Experience Level

### For Beginners
```
1. FRONTEND_INTEGRATION_SUMMARY.md (5 min)
   ↓
2. GOOGLE_OAUTH_QUICK_REFERENCE.md (10 min)
   ↓
3. GOOGLE_OAUTH_CODE_EXAMPLES.md (pick your framework)
   ↓
4. Code & Test
```

### For Experienced Developers
```
1. FRONTEND_INTEGRATION_SUMMARY.md (skim, 2 min)
   ↓
2. GOOGLE_OAUTH_QUICK_REFERENCE.md (5 min)
   ↓
3. GOOGLE_OAUTH_CODE_EXAMPLES.md (for your framework)
   ↓
4. Code & Test
```

### For Full Details
```
1. FRONTEND_INTEGRATION_SUMMARY.md
2. GOOGLE_OAUTH_FRONTEND_GUIDE.md (complete details)
3. GOOGLE_OAUTH_CODE_EXAMPLES.md (implementation)
4. GOOGLE_OAUTH_QUICK_REFERENCE.md (reference)
```

---

## 🔑 Key Information at a Glance

### Google OAuth Credentials
```
Client ID:    850588370229-jtaul330kpqmi0m239itt4jrodshko78.apps.googleusercontent.com
Redirect URI: http://localhost:8000/api/users/google/callback/
```

### Main Endpoint
```
POST /api/users/google/callback/
Content-Type: application/json

{
  "code": "Google_credential",
  "referral_code": "Optional_referral"
}
```

### What You Get Back
```
{
  "access": "JWT_token",
  "refresh": "JWT_refresh_token",
  "user": {
    "id": 123,
    "email": "user@gmail.com",
    "first_name": "John",
    "profile": {
      "profile_picture": "...",
      "preferred_language": "en"
    },
    "referral_code": "ABC12XYZ"
  }
}
```

---

## 📋 Quick Checklist

- [ ] Read FRONTEND_INTEGRATION_SUMMARY.md
- [ ] Choose your framework (React, Vue, Next.js, etc.)
- [ ] Review code examples for your framework
- [ ] Install Google Sign-In library
- [ ] Create login page with Google button
- [ ] Implement token storage & axios interceptor
- [ ] Create protected routes
- [ ] Implement logout
- [ ] Test locally with Google account
- [ ] Handle token refresh
- [ ] Test referral code feature (optional)
- [ ] Deploy to production with HTTPS

---

## 🚀 Framework-Specific Quick Start

### React
```bash
npm install @react-oauth/google axios
# Then: See GOOGLE_OAUTH_CODE_EXAMPLES.md → React with Hooks
```

### Vue 3
```bash
npm install vue3-google-login axios
# Then: See GOOGLE_OAUTH_CODE_EXAMPLES.md → Vue 3
```

### Next.js
```bash
npm install next-auth @react-oauth/google axios
# Then: See GOOGLE_OAUTH_CODE_EXAMPLES.md → Next.js
```

### Angular
```bash
npm install @react-oauth/google
# Then: See GOOGLE_OAUTH_CODE_EXAMPLES.md → Angular
```

### Vanilla JavaScript
```html
<script src="https://accounts.google.com/gsi/client" async defer></script>
```
See GOOGLE_OAUTH_CODE_EXAMPLES.md → Vanilla JavaScript

---

## 🎓 What You'll Learn

From these docs, you'll understand:

1. **OAuth Flow**
   - How Google OAuth 2.0 works
   - Authorization code exchange
   - Token management

2. **Frontend Integration**
   - How to initialize Google Sign-In
   - How to trigger the OAuth flow
   - How to handle responses

3. **Token Management**
   - Storing tokens securely
   - Using tokens in API requests
   - Handling token expiration
   - Refreshing expired tokens

4. **Security**
   - HTTP-only cookies
   - Secure token storage
   - CORS with credentials
   - Production HTTPS setup

5. **Features**
   - Auto user creation
   - Referral system
   - Reward coupons
   - Profile sync

---

## 🔗 Related Backend Files

These backend files support the frontend integration:

| Backend File | Purpose |
|--------------|---------|
| `Users/views.py` | OAuth callback, token endpoints |
| `Users/serializers.py` | User data serialization |
| `Users/models.py` | User & GoogleOAuthToken models |
| `core/settings.py` | Google OAuth configuration |
| `.env` | Credentials storage |

---

## 💬 Common Questions

**Q: Do I need to store credentials in my frontend?**  
A: No! Google OAuth handles that. You just receive credentials and store JWT tokens.

**Q: How secure is this?**  
A: Very! HTTP-only cookies + JWT tokens + HTTPS in production = secure.

**Q: What if token expires?**  
A: Implement token refresh. See GOOGLE_OAUTH_FRONTEND_GUIDE.md for details.

**Q: Can I use this with existing authentication?**  
A: Yes! This replaces username/password login, but you can keep both.

**Q: How do referrals work?**  
A: Optional. Include `referral_code` in callback request to link users for rewards.

---

## 🧪 Testing Checklist

### Local Testing
- [ ] Start backend: `python manage.py runserver`
- [ ] Start frontend: `npm run dev`
- [ ] Open login page in browser
- [ ] Click "Login with Google"
- [ ] Complete Google consent screen
- [ ] Check localStorage for tokens
- [ ] Verify redirect to dashboard
- [ ] Make API call with token

### Production Testing (Before Deploy)
- [ ] Test with HTTPS
- [ ] Test on actual domain
- [ ] Test token refresh
- [ ] Test logout
- [ ] Test with real Google account
- [ ] Verify cookies are secure

---

## 🆘 Troubleshooting

**Problem: CORS Error**
- Check: `withCredentials: true` in axios
- See: GOOGLE_OAUTH_FRONTEND_GUIDE.md → Error Responses

**Problem: 401 Unauthorized**
- Check: Token expiration
- See: GOOGLE_OAUTH_FRONTEND_GUIDE.md → Token Management

**Problem: User Not Created**
- Check: Backend logs
- Check: Google credential format
- See: FRONTEND_INTEGRATION_SUMMARY.md → Troubleshooting

**Problem: Redirect URL Mismatch**
- Check: Matches `http://localhost:8000/api/users/google/callback/` exactly
- See: GOOGLE_OAUTH_QUICK_REFERENCE.md

For more: GOOGLE_OAUTH_FRONTEND_GUIDE.md → Common Issues & Solutions

---

## 📞 Support Resources

1. **Google OAuth Documentation**
   https://developers.google.com/identity/gsi/web

2. **JWT Documentation**
   https://jwt.io/introduction

3. **Axios Documentation**
   https://axios-http.com/

4. **Framework-Specific Docs**
   - React: react.dev
   - Vue: vuejs.org
   - Next.js: nextjs.org
   - Angular: angular.io

5. **Your Backend Logs**
   ```bash
   python manage.py runserver
   # Watch for errors when testing login
   ```

---

## ✅ Final Checklist

Before you start coding:

- [ ] Read FRONTEND_INTEGRATION_SUMMARY.md
- [ ] Verify Google credentials (they're in the docs)
- [ ] Choose your framework
- [ ] Install required packages
- [ ] Understand the OAuth flow
- [ ] Have a Google account for testing
- [ ] Know where to find code examples
- [ ] Understand token management basics

---

## 🎯 End Goal

After following these docs, your frontend will have:

✅ **Google Login Button**
- User clicks to start OAuth
- Smooth user experience

✅ **Automatic User Account**
- Created on first login
- Email auto-verified
- Profile picture synced
- Language preference set

✅ **Protected Frontend Routes**
- Dashboard & checkout require login
- Auto-redirect to login if needed

✅ **Secure Token Management**
- Tokens in HTTP-only cookies
- Automatic token refresh
- Clean logout

✅ **API Integration**
- All requests include auth token
- Can access user profile, orders, coupons
- Can create orders, view rewards

---

## 🚀 Start Now!

1. **Read:** [FRONTEND_INTEGRATION_SUMMARY.md](./FRONTEND_INTEGRATION_SUMMARY.md)
2. **Learn:** [GOOGLE_OAUTH_QUICK_REFERENCE.md](./GOOGLE_OAUTH_QUICK_REFERENCE.md)
3. **Code:** [GOOGLE_OAUTH_CODE_EXAMPLES.md](./GOOGLE_OAUTH_CODE_EXAMPLES.md)

**Happy coding!** 🎉

---

## 📈 Implementation Timeline

### Day 1: Setup & Learn (2-3 hours)
- Read documentation
- Install packages
- Understand flow

### Day 2: Implement (4-6 hours)
- Create login page
- Add Google button
- Implement token storage
- Create dashboard

### Day 3: Protect & Polish (3-4 hours)
- Protect routes
- Add error handling
- Implement logout
- Test thoroughly

### Day 4: Production (1-2 hours)
- Update credentials for production
- Enable HTTPS
- Final testing
- Deploy

---

## 📊 Success Metrics

Your implementation is successful when:

✅ User can click "Login with Google"  
✅ Redirected to Google consent screen  
✅ Redirected back to dashboard on approval  
✅ User data displays on dashboard  
✅ Can view coupons and referral code  
✅ Can make authenticated API calls  
✅ Token refreshes when expired  
✅ Logout clears all data  
✅ Protected routes work correctly  
✅ Works on production with HTTPS  

**You're ready to go!** 🚀
