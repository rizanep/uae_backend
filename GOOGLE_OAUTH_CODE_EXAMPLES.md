# Google OAuth Login - Code Examples by Framework

Complete, ready-to-copy code examples for popular frontend frameworks.

---

## 📚 Table of Contents

1. [React with Hooks](#react-with-hooks)
2. [Next.js](#nextjs)
3. [Vue 3 with Composition API](#vue-3)
4. [Vanilla JavaScript](#vanilla-javascript)
5. [Angular](#angular)

---

## React with Hooks

### Installation

```bash
npm install @react-oauth/google axios react-router-dom
```

### 1. API Client Setup

**api/client.js**
```javascript
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

export const apiClient = axios.create({
  baseURL: API_URL,
  withCredentials: true,
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle token expiration
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        const response = await axios.post(
          `${API_URL}/users/auth/refresh/`,
          { refresh: refreshToken },
          { withCredentials: true }
        );

        localStorage.setItem('access_token', response.data.access);
        originalRequest.headers.Authorization = `Bearer ${response.data.access}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;
```

### 2. Google OAuth Context

**context/AuthContext.js**
```javascript
import React, { createContext, useState, useCallback } from 'react';
import { apiClient } from '../api/client';

export const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const stored = localStorage.getItem('user');
    return stored ? JSON.parse(stored) : null;
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleGoogleSuccess = useCallback(async (credentialResponse) => {
    setLoading(true);
    setError(null);

    try {
      const referralCode = localStorage.getItem('referral_code');

      const response = await apiClient.post('/users/google/callback/', {
        code: credentialResponse.credential,
        referral_code: referralCode || undefined,
      });

      const { access, refresh, user: userData, referral } = response.data;

      localStorage.setItem('access_token', access);
      localStorage.setItem('refresh_token', refresh);
      localStorage.setItem('user', JSON.stringify(userData));
      localStorage.removeItem('referral_code');

      setUser(userData);

      if (referral?.success) {
        setError(null);
      }

      return userData;
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Login failed. Please try again.';
      setError(errorMsg);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    setLoading(true);
    try {
      await apiClient.post('/users/auth/logout/');
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
      setUser(null);
      setError(null);
      setLoading(false);
    }
  }, []);

  const value = {
    user,
    setUser,
    loading,
    setLoading,
    error,
    setError,
    handleGoogleSuccess,
    logout,
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
```

### 3. Login Component

**components/LoginPage.jsx**
```jsx
import { GoogleOAuthProvider, GoogleLogin } from '@react-oauth/google';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import '../styles/LoginPage.css';

const GOOGLE_CLIENT_ID = process.env.REACT_APP_GOOGLE_CLIENT_ID || 
  '850588370229-jtaul330kpqmi0m239itt4jrodshko78.apps.googleusercontent.com';

export function LoginPage() {
  const navigate = useNavigate();
  const { handleGoogleSuccess, error, loading } = useAuth();

  const onSuccess = async (credentialResponse) => {
    try {
      await handleGoogleSuccess(credentialResponse);
      navigate('/dashboard');
    } catch (err) {
      console.error('Login failed:', err);
    }
  };

  const onError = () => {
    console.error('Google login failed');
  };

  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <div className="login-page">
        <div className="login-container">
          <h1>Welcome to SIMAK FRESH</h1>
          <p>Login with your Google account</p>

          {error && <div className="error-message">{error}</div>}

          <div className="google-login">
            <GoogleLogin
              onSuccess={onSuccess}
              onError={onError}
              disabled={loading}
            />
          </div>

          <div className="login-info">
            <h3>First time here?</h3>
            <p>
              Sign in with Google to create your account instantly. 
              Your email will be verified automatically.
            </p>
            <ul>
              <li>✓ Auto-verified email</li>
              <li>✓ Welcome discount (10% off)</li>
              <li>✓ Referral rewards program</li>
              <li>✓ Fast checkout</li>
            </ul>
          </div>
        </div>
      </div>
    </GoogleOAuthProvider>
  );
}

export default LoginPage;
```

### 4. Protected Route

**components/ProtectedRoute.jsx**
```jsx
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
}
```

### 5. Dashboard Component

**pages/Dashboard.jsx**
```jsx
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';
import { useEffect, useState } from 'react';

export function Dashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [coupons, setCoupons] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchCoupons();
  }, []);

  const fetchCoupons = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get('/marketing/coupons/');
      setCoupons(response.data.results || response.data);
    } catch (error) {
      console.error('Failed to fetch coupons:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Welcome, {user?.first_name}! 👋</h1>
        <button onClick={handleLogout} className="btn-logout">
          Logout
        </button>
      </header>

      <div className="user-info">
        <div className="info-card">
          <h3>Email</h3>
          <p>{user?.email}</p>
        </div>
        <div className="info-card">
          <h3>Referral Code</h3>
          <p>{user?.referral_code}</p>
        </div>
      </div>

      <section className="coupons-section">
        <h2>Your Available Coupons</h2>
        {loading ? (
          <p>Loading coupons...</p>
        ) : coupons.length > 0 ? (
          <div className="coupons-grid">
            {coupons.map((coupon) => (
              <div key={coupon.id} className="coupon-card">
                <h3>{coupon.code}</h3>
                <p>{coupon.description}</p>
                <div className="coupon-details">
                  <span>
                    {coupon.discount_type === 'percentage'
                      ? `${coupon.discount_value}% off`
                      : `AED ${coupon.discount_value} off`}
                  </span>
                  <span>Min: AED {coupon.min_order_amount}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p>No coupons available</p>
        )}
      </section>
    </div>
  );
}
```

### 6. App Setup

**App.jsx**
```jsx
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { LoginPage } from './pages/LoginPage';
import { Dashboard } from './pages/Dashboard';
import { ProtectedRoute } from './components/ProtectedRoute';

function App() {
  return (
    <Router>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AuthProvider>
    </Router>
  );
}

export default App;
```

### 7. Environment Variables

**.env**
```env
REACT_APP_API_URL=http://localhost:8000/api
REACT_APP_GOOGLE_CLIENT_ID=850588370229-jtaul330kpqmi0m239itt4jrodshko78.apps.googleusercontent.com
```

---

## Next.js

### Installation

```bash
npm install @react-oauth/google axios next-auth
```

### API Routes Handler

**pages/api/auth/google-callback.js**
```javascript
import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { code, referral_code } = req.body;

    const response = await axios.post(
      `${API_URL}/users/google/callback/`,
      {
        code,
        referral_code,
      },
      {
        withCredentials: true,
      }
    );

    const { access, refresh, user } = response.data;

    // Set secure HTTP-only cookies
    res.setHeader(
      'Set-Cookie',
      [
        `access_token=${access}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${7 * 24 * 60 * 60}`,
        `refresh_token=${refresh}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${7 * 24 * 60 * 60}`,
      ]
    );

    return res.status(200).json({
      success: true,
      user,
      access,
    });
  } catch (error) {
    console.error('Google callback error:', error);
    return res.status(error.response?.status || 400).json({
      error: error.response?.data?.detail || 'Authentication failed',
    });
  }
}
```

### Login Component

**components/GoogleLoginButton.jsx**
```jsx
import { GoogleOAuthProvider, GoogleLogin } from '@react-oauth/google';
import { useRouter } from 'next/router';
import { useState } from 'react';
import axios from 'axios';

export function GoogleLoginButton() {
  const router = useRouter();
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSuccess = async (credentialResponse) => {
    setLoading(true);
    setError(null);

    try {
      const response = await axios.post('/api/auth/google-callback', {
        code: credentialResponse.credential,
        referral_code: localStorage.getItem('referral_code'),
      });

      localStorage.setItem('user', JSON.stringify(response.data.user));
      localStorage.removeItem('referral_code');

      router.push('/dashboard');
    } catch (err) {
      setError(err.response?.data?.error || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <GoogleOAuthProvider clientId="850588370229-jtaul330kpqmi0m239itt4jrodshko78.apps.googleusercontent.com">
      <div className="login-container">
        {error && <div className="error">{error}</div>}
        <GoogleLogin
          onSuccess={handleSuccess}
          onError={() => setError('Login failed')}
          disabled={loading}
        />
      </div>
    </GoogleOAuthProvider>
  );
}
```

### Middleware for Protected Routes

**middleware.js**
```javascript
import { NextResponse } from 'next/server';

export function middleware(request) {
  const token = request.cookies.get('access_token');

  if (!token && request.nextUrl.pathname.startsWith('/dashboard')) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/dashboard/:path*'],
};
```

---

## Vue 3

### Installation

```bash
npm install vue3-google-login axios
```

### API Composable

**composables/useApi.js**
```javascript
import axios from 'axios';
import { ref } from 'vue';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export const apiClient = axios.create({
  baseURL: API_URL,
  withCredentials: true,
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export function useApi() {
  const loading = ref(false);
  const error = ref(null);

  return {
    apiClient,
    loading,
    error,
  };
}
```

### Auth Composable

**composables/useAuth.js**
```javascript
import { ref, computed } from 'vue';
import { apiClient } from './useApi';

const user = ref(JSON.parse(localStorage.getItem('user') || 'null'));
const isAuthenticated = computed(() => !!user.value);

export function useAuth() {
  const loading = ref(false);
  const error = ref(null);

  async function googleLogin(credential, referralCode = null) {
    loading.value = true;
    error.value = null;

    try {
      const response = await apiClient.post('/users/google/callback/', {
        code: credential,
        referral_code: referralCode,
      });

      const { access, refresh, user: userData } = response.data;

      localStorage.setItem('access_token', access);
      localStorage.setItem('refresh_token', refresh);
      localStorage.setItem('user', JSON.stringify(userData));

      user.value = userData;
      return userData;
    } catch (err) {
      error.value = err.response?.data?.detail || 'Login failed';
      throw err;
    } finally {
      loading.value = false;
    }
  }

  function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    user.value = null;
  }

  return {
    user,
    isAuthenticated,
    loading,
    error,
    googleLogin,
    logout,
  };
}
```

### Login Page

**pages/LoginPage.vue**
```vue
<template>
  <div class="login-page">
    <div class="login-container">
      <h1>Welcome to SIMAK FRESH</h1>
      <p>Login with your Google account</p>

      <div v-if="error" class="error-message">{{ error }}</div>

      <GoogleLogin
        :clientId="googleClientId"
        @success="handleGoogleSuccess"
        @error="handleGoogleError"
      />
    </div>
  </div>
</template>

<script setup>
import { GoogleLogin } from 'vue3-google-login';
import { useAuth } from '../composables/useAuth';
import { useRouter } from 'vue-router';

const router = useRouter();
const { googleLogin, error, loading } = useAuth();

const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

async function handleGoogleSuccess(response) {
  try {
    await googleLogin(response.credential);
    router.push('/dashboard');
  } catch (err) {
    console.error('Login failed:', err);
  }
}

function handleGoogleError() {
  console.error('Google login failed');
}
</script>

<style scoped>
.login-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-container {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
  max-width: 400px;
  width: 100%;
}

.error-message {
  background: #fee;
  color: #c33;
  padding: 0.75rem;
  border-radius: 4px;
  margin-bottom: 1rem;
}
</style>
```

### Environment Variables

**.env.local**
```env
VITE_API_URL=http://localhost:8000/api
VITE_GOOGLE_CLIENT_ID=850588370229-jtaul330kpqmi0m239itt4jrodshko78.apps.googleusercontent.com
```

---

## Vanilla JavaScript

### HTML

**index.html**
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SIMAK FRESH - Login</title>
  <script src="https://accounts.google.com/gsi/client" async defer></script>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      margin: 0;
      padding: 0;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      min-height: 100vh;
      display: flex;
      justify-content: center;
      align-items: center;
    }

    .login-container {
      background: white;
      padding: 2rem;
      border-radius: 8px;
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
      max-width: 400px;
      width: 100%;
    }

    h1 {
      margin-top: 0;
      color: #333;
    }

    .error {
      background: #fee;
      color: #c33;
      padding: 0.75rem;
      border-radius: 4px;
      margin-bottom: 1rem;
      display: none;
    }

    .error.show {
      display: block;
    }

    .google-login {
      margin: 2rem 0;
    }

    .loading {
      text-align: center;
      padding: 2rem;
      color: #666;
    }
  </style>
</head>
<body>
  <div class="login-container">
    <h1>Welcome to SIMAK FRESH</h1>
    <p>Login with your Google account</p>

    <div id="error-message" class="error"></div>

    <div id="g_id_onload"
         data-client_id="850588370229-jtaul330kpqmi0m239itt4jrodshko78.apps.googleusercontent.com"
         data-callback="handleCredentialResponse">
    </div>
    <div class="g_id_signin" data-type="standard" data-size="large"></div>
  </div>

  <script src="./auth.js"></script>
</body>
</html>
```

### JavaScript

**auth.js**
```javascript
const API_URL = 'http://localhost:8000/api';

// Handle Google credential response
window.handleCredentialResponse = async function (response) {
  const errorDiv = document.getElementById('error-message');
  errorDiv.classList.remove('show');

  try {
    const referralCode = localStorage.getItem('referral_code');

    const apiResponse = await fetch(`${API_URL}/users/google/callback/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify({
        code: response.credential,
        referral_code: referralCode,
      }),
    });

    if (!apiResponse.ok) {
      const errorData = await apiResponse.json();
      throw new Error(errorData.detail || 'Login failed');
    }

    const data = await apiResponse.json();

    // Store tokens
    localStorage.setItem('access_token', data.access);
    localStorage.setItem('refresh_token', data.refresh);
    localStorage.setItem('user', JSON.stringify(data.user));
    localStorage.removeItem('referral_code');

    // Redirect
    window.location.href = '/dashboard.html';
  } catch (error) {
    console.error('Login error:', error);
    errorDiv.textContent = error.message;
    errorDiv.classList.add('show');
  }
};

// Initialize Google Sign-In
window.onload = function () {
  google.accounts.id.initialize({
    client_id: '850588370229-jtaul330kpqmi0m239itt4jrodshko78.apps.googleusercontent.com',
  });

  google.accounts.id.renderButton(
    document.querySelector('.g_id_signin'),
    {
      theme: 'outline',
      size: 'large',
    }
  );
};

// API Helper Functions
class API {
  constructor(baseURL) {
    this.baseURL = baseURL;
  }

  async request(endpoint, options = {}) {
    const token = localStorage.getItem('access_token');
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(`${this.baseURL}${endpoint}`, {
      ...options,
      headers,
      credentials: 'include',
    });

    if (response.status === 401) {
      this.handleTokenExpired();
    }

    return response;
  }

  async get(endpoint) {
    return this.request(endpoint, { method: 'GET' });
  }

  async post(endpoint, data) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  handleTokenExpired() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    window.location.href = '/login.html';
  }
}

const api = new API(API_URL);
```

### Dashboard

**dashboard.html**
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Dashboard - SIMAK FRESH</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      margin: 0;
      padding: 20px;
      background: #f5f5f5;
    }

    .dashboard {
      max-width: 1000px;
      margin: 0 auto;
    }

    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: white;
      padding: 2rem;
      border-radius: 8px;
      margin-bottom: 2rem;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    button {
      background: #667eea;
      color: white;
      border: none;
      padding: 0.75rem 1.5rem;
      border-radius: 4px;
      cursor: pointer;
      font-size: 1rem;
    }

    button:hover {
      background: #764ba2;
    }

    .user-info {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 1rem;
      margin-bottom: 2rem;
    }

    .card {
      background: white;
      padding: 1.5rem;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    .coupons {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 1rem;
    }

    .loading {
      text-align: center;
      padding: 2rem;
      color: #666;
    }
  </style>
</head>
<body>
  <div class="dashboard">
    <div class="header">
      <div>
        <h1 id="greeting">Welcome!</h1>
        <p id="email"></p>
      </div>
      <button onclick="logout()">Logout</button>
    </div>

    <div class="user-info">
      <div class="card">
        <h3>Email</h3>
        <p id="user-email"></p>
      </div>
      <div class="card">
        <h3>Referral Code</h3>
        <p id="referral-code"></p>
      </div>
    </div>

    <div class="card">
      <h2>Your Coupons</h2>
      <div id="coupons-list" class="coupons"></div>
    </div>
  </div>

  <script src="./auth.js"></script>
  <script>
    // Load user data
    function loadDashboard() {
      const user = JSON.parse(localStorage.getItem('user'));

      if (!user) {
        window.location.href = '/login.html';
        return;
      }

      document.getElementById('greeting').textContent = `Welcome, ${user.first_name}!`;
      document.getElementById('user-email').textContent = user.email;
      document.getElementById('referral-code').textContent = user.referral_code;

      fetchCoupons();
    }

    async function fetchCoupons() {
      const couponsList = document.getElementById('coupons-list');
      couponsList.innerHTML = '<div class="loading">Loading coupons...</div>';

      try {
        const response = await api.get('/marketing/coupons/');
        const data = await response.json();

        if (response.ok) {
          const coupons = data.results || data;

          if (coupons.length === 0) {
            couponsList.innerHTML = '<p>No coupons available</p>';
            return;
          }

          couponsList.innerHTML = coupons
            .map(
              (coupon) => `
            <div class="card">
              <h3>${coupon.code}</h3>
              <p>${coupon.description}</p>
              <p>
                <strong>
                  ${
                    coupon.discount_type === 'percentage'
                      ? `${coupon.discount_value}% off`
                      : `AED ${coupon.discount_value} off`
                  }
                </strong>
              </p>
              <p>Min order: AED ${coupon.min_order_amount}</p>
            </div>
          `
            )
            .join('');
        }
      } catch (error) {
        couponsList.innerHTML = '<p>Failed to load coupons</p>';
        console.error('Error:', error);
      }
    }

    function logout() {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
      window.location.href = '/login.html';
    }

    // Load on page load
    loadDashboard();
  </script>
</body>
</html>
```

---

## Angular

### Installation

```bash
npm install @react-oauth/google axios
```

### Auth Service

**services/auth.service.ts**
```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable } from 'rxjs';
import { environment } from '../environments/environment';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private apiUrl = environment.apiUrl;
  private userSubject = new BehaviorSubject<any>(this.getUserFromStorage());
  public user$ = this.userSubject.asObservable();

  constructor(private http: HttpClient) {}

  googleLogin(credential: string, referralCode?: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/users/google/callback/`, {
      code: credential,
      referral_code: referralCode,
    });
  }

  handleLoginSuccess(data: any): void {
    localStorage.setItem('access_token', data.access);
    localStorage.setItem('refresh_token', data.refresh);
    localStorage.setItem('user', JSON.stringify(data.user));
    this.userSubject.next(data.user);
  }

  private getUserFromStorage(): any {
    const user = localStorage.getItem('user');
    return user ? JSON.parse(user) : null;
  }

  logout(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    this.userSubject.next(null);
  }

  getUser(): Observable<any> {
    return this.user$;
  }

  isAuthenticated(): boolean {
    return !!localStorage.getItem('access_token');
  }
}
```

### Login Component

**components/login/login.component.ts**
```typescript
import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';

declare const google: any;

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css'],
})
export class LoginComponent {
  error: string = '';

  constructor(
    private authService: AuthService,
    private router: Router
  ) {}

  ngOnInit(): void {
    google.accounts.id.initialize({
      client_id:
        '850588370229-jtaul330kpqmi0m239itt4jrodshko78.apps.googleusercontent.com',
      callback: this.handleLogin.bind(this),
    });

    google.accounts.id.renderButton(
      document.getElementById('googleDiv'),
      { theme: 'outline', size: 'large' }
    );
  }

  handleLogin(response: any): void {
    this.authService.googleLogin(response.credential).subscribe(
      (data) => {
        this.authService.handleLoginSuccess(data);
        this.router.navigate(['/dashboard']);
      },
      (error) => {
        this.error = error.error?.detail || 'Login failed';
      }
    );
  }
}
```

---

This provides complete, production-ready code examples for all major frameworks! 🎉
