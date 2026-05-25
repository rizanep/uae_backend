# Google OAuth ID Token - Debugging Guide

## Error: "Not enough segments"

**Cause**: The backend received a token that doesn't have a valid JWT format (should be `header.payload.signature` with 2 dots).

---

## 🔍 What's a Valid Google ID Token?

A valid JWT token looks like:
```
eyJhbGciOiJSUzI1NiIsImtpZCI6IjEyMzQ1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIn0.signature_part
```

It has exactly **3 parts separated by 2 dots**:
1. `header` - algorithm & token type
2. `payload` - user claims (email, name, etc)
3. `signature` - cryptographic signature

---

## ✅ Correct Frontend Implementation

### React with @react-oauth/google

**Installation:**
```bash
npm install @react-oauth/google
```

**Setup (main.jsx or App.jsx):**
```jsx
import { GoogleOAuthProvider } from '@react-oauth/google';
import ReactDOM from 'react-dom/client';
import App from './App';

ReactDOM.createRoot(document.getElementById('root')).render(
  <GoogleOAuthProvider clientId="850588370229-jtaul330kpqmi0m239itt4jrodshko78.apps.googleusercontent.com">
    <App />
  </GoogleOAuthProvider>
);
```

**Login Component (LoginPage.jsx):**
```jsx
import { GoogleLogin } from '@react-oauth/google';
import axios from 'axios';

export function GoogleLoginButton() {
  const handleGoogleSuccess = async (credentialResponse) => {
    try {
      console.log('Google response:', credentialResponse);
      console.log('Token:', credentialResponse.credential);
      console.log('Token type:', typeof credentialResponse.credential);
      console.log('Token length:', credentialResponse.credential.length);
      console.log('Dot count:', (credentialResponse.credential.match(/\./g) || []).length);

      // Send token to backend
      const response = await axios.post(
        'http://localhost:8000/api/users/google/callback/',
        { code: credentialResponse.credential },
        { withCredentials: true }
      );

      // Success
      localStorage.setItem('access_token', response.data.access);
      localStorage.setItem('refresh_token', response.data.refresh);
      localStorage.setItem('user', JSON.stringify(response.data.user));

      window.location.href = '/dashboard';
    } catch (error) {
      console.error('Google login error:', error.response?.data || error.message);
      alert(`Login failed: ${error.response?.data?.detail || 'Unknown error'}`);
    }
  };

  const handleGoogleError = () => {
    console.error('Google Sign-In failed');
  };

  return (
    <GoogleLogin
      onSuccess={handleGoogleSuccess}
      onError={handleGoogleError}
      text="signin_with"
      size="large"
    />
  );
}
```

---

## 🛠️ Debugging Steps

### 1. Check Browser Console
Open DevTools (F12) and look for:
- Does `credentialResponse.credential` exist?
- What's the format? (should start with 3 parts separated by dots)
- Are there any JWT-related logs?

### 2. Inspect the Token
Run this in the browser console:
```js
// Assuming you have the credential response
const token = credentialResponse.credential;

// Should have 3 parts
const parts = token.split('.');
console.log('Part count:', parts.length); // Should be 3
console.log('Header:', atob(parts[0])); // Decode header
console.log('Payload:', atob(parts[1])); // Decode payload
```

### 3. Check Backend Logs
```bash
cd /home/django_user/apps/uae_backend
tail -f logs/django.log
```

Backend will show:
- Token format issues
- What it received
- Validation errors

### 4. Test with curl
```bash
# Decode a JWT (replace TOKEN with actual token)
python3 -c "
import base64, json
token = 'YOUR_TOKEN_HERE'
parts = token.split('.')
print('Header:', json.loads(base64.b64decode(parts[0] + '==')))
print('Payload:', json.loads(base64.b64decode(parts[1] + '==')))
"
```

---

## ❌ Common Issues

### Issue 1: Empty Token
**Problem**: `credentialResponse.credential` is empty or undefined
**Solution**: 
- Make sure `GoogleOAuthProvider` wraps your entire app
- Check that Client ID is correct
- Verify Google Sign-In button is inside the provider

### Issue 2: Token is not base64
**Problem**: Token doesn't have proper JWT structure
**Solution**:
- Ensure you're using `GoogleLogin` component, not custom implementation
- Update `@react-oauth/google` to latest version: `npm install --latest @react-oauth/google`

### Issue 3: CORS Error
**Problem**: Browser blocks the request
**Solution**:
Add to backend `settings.py`:
```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
]
```

---

## ✨ Working Example with Full Error Handling

```jsx
import { GoogleLogin } from '@react-oauth/google';
import axios from 'axios';

export function GoogleLoginButton() {
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState(null);

  const handleGoogleSuccess = async (credentialResponse) => {
    setLoading(true);
    setError(null);

    try {
      const token = credentialResponse.credential;

      // Validate token format
      const parts = token.split('.');
      if (parts.length !== 3) {
        throw new Error(`Invalid token format: expected 3 parts, got ${parts.length}`);
      }

      // Send to backend
      const response = await axios.post(
        'http://localhost:8000/api/users/google/callback/',
        { code: token },
        { withCredentials: true }
      );

      // Success
      localStorage.setItem('access_token', response.data.access);
      localStorage.setItem('refresh_token', response.data.refresh);
      localStorage.setItem('user', JSON.stringify(response.data.user));

      window.location.href = '/dashboard';
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message;
      setError(errorMsg);
      console.error('Google login failed:', errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <GoogleLogin
        onSuccess={handleGoogleSuccess}
        onError={() => setError('Google Sign-In failed')}
      />
      {error && <div style={{ color: 'red' }}>{error}</div>}
      {loading && <p>Loading...</p>}
    </div>
  );
}
```

---

## 📞 Still Having Issues?

Check:
1. **Browser console** for JWT validation output
2. **Backend logs** for token format details  
3. **Network tab** to see what's actually being sent
4. **Google API settings** to ensure credentials are correct

Share the exact backend error message for detailed debugging.
