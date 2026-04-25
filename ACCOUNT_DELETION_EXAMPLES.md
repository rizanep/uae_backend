# Account Deletion API - Real-World Integration Examples

## Complete Frontend Example (React)

```jsx
import React, { useState } from 'react';
import axios from 'axios';

const AccountDeletionDialog = ({ isOpen, onClose, token }) => {
  const [step, setStep] = useState('warning'); // warning -> info -> password -> confirm -> success
  const [password, setPassword] = useState('');
  const [deleteMethod, setDeleteMethod] = useState('soft');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [deletionInfo, setDeletionInfo] = useState(null);

  const apiClient = axios.create({
    baseURL: '/api/users',
    headers: { Authorization: `Bearer ${token}` }
  });

  // Step 1: Get deletion info
  const fetchDeletionInfo = async () => {
    try {
      setLoading(true);
      setError('');
      const response = await apiClient.get('/users/account_deletion_info/');
      setDeletionInfo(response.data);
      setStep('info');
    } catch (err) {
      setError('Failed to load deletion information');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Step 2: Delete account
  const handleDelete = async () => {
    if (!password) {
      setError('Password is required');
      return;
    }

    try {
      setLoading(true);
      setError('');
      const response = await apiClient.post('/users/request_account_deletion/', {
        password: password,
        delete_method: deleteMethod,
        confirm_deletion: true
      });

      // Success
      setStep('success');
      
      // Clear auth tokens
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      
      // Redirect after 3 seconds
      setTimeout(() => {
        window.location.href = '/login';
      }, 3000);
    } catch (err) {
      if (err.response?.data?.password) {
        setError('Invalid password');
      } else if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError('Failed to delete account');
      }
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal overlay">
      <div className="modal-content">
        {/* Step 1: Warning */}
        {step === 'warning' && (
          <div>
            <h2>⚠️ Delete Account</h2>
            <p className="warning">
              This action cannot be undone!
            </p>
            <p>
              Your account and all related data will be deleted.
              Continue to see what will be deleted.
            </p>
            <div className="modal-actions">
              <button onClick={onClose} className="btn-secondary">Cancel</button>
              <button onClick={fetchDeletionInfo} className="btn-primary" disabled={loading}>
                {loading ? 'Loading...' : 'Continue'}
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Show what will be deleted */}
        {step === 'info' && deletionInfo && (
          <div>
            <h2>Review What Will Be Deleted</h2>
            <div className="deletion-summary">
              <p><strong>Account:</strong> {deletionInfo.user.email}</p>
              <hr />
              <p><strong>Related Data:</strong></p>
              <ul>
                <li>📦 Orders: {deletionInfo.related_data.orders}</li>
                <li>📍 Addresses: {deletionInfo.related_data.addresses}</li>
                <li>🛒 Cart Items: {deletionInfo.related_data.cart_items}</li>
                {deletionInfo.related_data.profile && <li>👤 Profile</li>}
              </ul>
              {deletionInfo.related_data.orders > 0 && (
                <div className="warning">
                  ⚠️ You have {deletionInfo.related_data.orders} order(s).
                  Orders cannot be deleted but will be anonymized.
                </div>
              )}
            </div>

            <div className="deletion-method">
              <h3>Deletion Method:</h3>
              <label>
                <input 
                  type="radio" 
                  value="soft" 
                  checked={deleteMethod === 'soft'}
                  onChange={(e) => setDeleteMethod(e.target.value)}
                />
                Soft Delete (Anonymize - recoverable for 30 days)
              </label>
              <label>
                <input 
                  type="radio" 
                  value="hard" 
                  checked={deleteMethod === 'hard'}
                  onChange={(e) => setDeleteMethod(e.target.value)}
                />
                Hard Delete (Permanent - cannot recover)
              </label>
            </div>

            <div className="modal-actions">
              <button onClick={() => setStep('warning')} className="btn-secondary">Back</button>
              <button onClick={() => setStep('password')} className="btn-primary">Continue</button>
            </div>
          </div>
        )}

        {/* Step 3: Password confirmation */}
        {step === 'password' && (
          <div>
            <h2>Confirm Your Password</h2>
            <p>We need your password to verify this is you.</p>
            
            {error && <div className="error-message">{error}</div>}
            
            <input
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleDelete()}
              disabled={loading}
              autoFocus
            />

            <div className="modal-actions">
              <button onClick={() => { setStep('info'); setPassword(''); }} className="btn-secondary">Back</button>
              <button onClick={() => setStep('confirm')} className="btn-primary" disabled={!password}>
                Next
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Final confirmation */}
        {step === 'confirm' && (
          <div>
            <h2>Final Confirmation</h2>
            <div className="danger-zone">
              <p>
                ⚠️ <strong>This is your last chance!</strong>
              </p>
              <p>
                Once you delete your account {deleteMethod === 'hard' ? '(permanently)' : '(even soft delete)'},
                you cannot recover most of your data.
              </p>
            </div>

            <label className="checkbox">
              <input type="checkbox" id="confirm-check" />
              I understand this action cannot be undone
            </label>

            <div className="modal-actions">
              <button onClick={() => setStep('password')} className="btn-secondary">Cancel</button>
              <button 
                onClick={handleDelete} 
                className="btn-danger" 
                disabled={loading || !document.getElementById('confirm-check')?.checked}
              >
                {loading ? 'Deleting...' : '🗑️ Delete My Account'}
              </button>
            </div>
          </div>
        )}

        {/* Step 5: Success */}
        {step === 'success' && (
          <div className="success-message">
            <h2>✅ Account Deleted Successfully</h2>
            <p>
              Your account has been {deleteMethod === 'soft' ? 'anonymized' : 'permanently deleted'}.
            </p>
            <p className="text-muted">
              A confirmation email has been sent.
            </p>
            <p className="text-muted">
              Redirecting to login in 3 seconds...
            </p>
            <div className="modal-actions">
              <button onClick={() => window.location.href = '/login'} className="btn-primary">
                Go to Login Now
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AccountDeletionDialog;
```

---

## Backend Integration Example (Django)

```python
# views.py or wherever you need to use it

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from Users.account_deletion_service import AccountDeletionService

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def custom_delete_endpoint(request):
    """Custom endpoint for account deletion with additional logic"""
    
    user = request.user
    password = request.data.get('password')
    delete_method = request.data.get('delete_method', 'soft')
    
    # Verify password
    if not user.check_password(password):
        return Response({'error': 'Invalid password'}, status=400)
    
    # Additional checks
    if user.is_superuser:
        return Response({'error': 'Superusers cannot be deleted'}, status=403)
    
    # Check for ongoing deliveries (if you have delivery boys)
    if hasattr(user, 'delivery_profile') and user.delivery_profile:
        from Orders.models import Order
        ongoing = Order.objects.filter(
            delivery_boy=user,
            status__in=['out_for_delivery', 'pending']
        ).count()
        if ongoing > 0:
            return Response(
                {'error': f'Cannot delete: {ongoing} ongoing deliveries'},
                status=403
            )
    
    # Perform deletion
    try:
        result = AccountDeletionService.delete_user_data(
            user=user,
            delete_method=delete_method,
            send_confirmation=True
        )
        return Response(result)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


# models.py - Optional: Track deletions

from django.db import models

class AccountDeletionLog(models.Model):
    """Track all account deletions for compliance"""
    
    user_id = models.IntegerField()
    user_email = models.EmailField()
    user_phone = models.CharField(max_length=20, blank=True)
    deletion_method = models.CharField(
        max_length=10,
        choices=[('soft', 'Soft'), ('hard', 'Hard')]
    )
    deletion_status = models.CharField(max_length=50)
    reason = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    deleted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-deleted_at']
        verbose_name = 'Account Deletion Log'
        verbose_name_plural = 'Account Deletion Logs'
    
    def __str__(self):
        return f"{self.user_email} - {self.deletion_status} - {self.deleted_at}"
```

---

## Complete API Test Script (Python)

```python
"""
Complete test script for Account Deletion API
Tests all scenarios: success, validation, errors
"""

import requests
import json
from time import sleep

class AccountDeletionAPITest:
    """Test suite for account deletion"""
    
    def __init__(self, base_url='http://localhost:8000', username='test@example.com', password='password'):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.token = None
    
    def setup(self):
        """Get JWT token"""
        response = requests.post(
            f'{self.base_url}/api/users/auth/login/',
            json={'email': self.username, 'password': self.password}
        )
        if response.status_code == 200:
            self.token = response.json()['access']
            print(f"✅ Authenticated as {self.username}")
        else:
            print(f"❌ Authentication failed: {response.text}")
            return False
        return True
    
    def headers(self):
        """Get headers with authorization"""
        return {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
    
    def test_deletion_info(self):
        """Test: Get deletion information"""
        print("\n" + "="*60)
        print("TEST: Get Deletion Information")
        print("="*60)
        
        response = requests.get(
            f'{self.base_url}/api/users/users/account_deletion_info/',
            headers=self.headers()
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS")
            print(f"  User: {data['user']['name']}")
            print(f"  Email: {data['user']['email']}")
            print(f"  Orders: {data['related_data']['orders']}")
            print(f"  Addresses: {data['related_data']['addresses']}")
            return True
        else:
            print(f"❌ FAILED: {response.text}")
            return False
    
    def test_delete_soft(self):
        """Test: Soft delete"""
        print("\n" + "="*60)
        print("TEST: Soft Delete (Anonymize)")
        print("="*60)
        
        payload = {
            'password': self.password,
            'delete_method': 'soft',
            'confirm_deletion': True
        }
        
        response = requests.post(
            f'{self.base_url}/api/users/users/request_account_deletion/',
            json=payload,
            headers=self.headers()
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS")
            print(f"  Deletion Status: {data['deletion_status']}")
            print(f"  Deleted At: {data['deleted_at']}")
            print(f"  Message: {data['message']}")
            return True
        else:
            print(f"❌ FAILED: {response.text}")
            return False
    
    def test_invalid_password(self):
        """Test: Invalid password should fail"""
        print("\n" + "="*60)
        print("TEST: Invalid Password Validation")
        print("="*60)
        
        payload = {
            'password': 'WrongPassword123!',
            'delete_method': 'soft',
            'confirm_deletion': True
        }
        
        response = requests.post(
            f'{self.base_url}/api/users/users/request_account_deletion/',
            json=payload,
            headers=self.headers()
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 400:
            print(f"✅ CORRECT: Invalid password rejected")
            return True
        else:
            print(f"❌ FAILED: Should reject invalid password")
            return False
    
    def run_all(self):
        """Run all tests"""
        print("\n" + "="*60)
        print("Account Deletion API - Test Suite")
        print("="*60)
        
        if not self.setup():
            return
        
        results = {
            'Get Deletion Info': self.test_deletion_info(),
            'Invalid Password': self.test_invalid_password(),
            'Soft Delete': self.test_delete_soft(),
        }
        
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        for test, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status}: {test}")


# Run tests
if __name__ == '__main__':
    tester = AccountDeletionAPITest(
        base_url='http://localhost:8000',
        username='testuser@example.com',
        password='TestPassword123!'
    )
    tester.run_all()
```

---

## Monitoring & Analytics

```python
# Dashboard code to monitor deletions

from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from Users.models import User

def deletion_statistics():
    """Get deletion statistics"""
    
    now = timezone.now()
    last_30_days = now - timedelta(days=30)
    last_year = now - timedelta(days=365)
    
    return {
        'last_30_days': User.objects.filter(
            deleted_at__gte=last_30_days
        ).count(),
        'last_year': User.objects.filter(
            deleted_at__gte=last_year
        ).count(),
        'total_deleted': User.objects.filter(
            deleted_at__isnull=False
        ).count(),
        'daily_average': (
            User.objects.filter(deleted_at__gte=last_year).count() / 365
        ),
    }

def get_deletion_reasons():
    """Analyze why users delete accounts"""
    # If you track deletion reasons in a log
    from Users.models import AccountDeletionLog
    
    return AccountDeletionLog.objects.values('deletion_method').annotate(
        count=Count('id')
    )
```

---

## Email Template (for deletion confirmation)

```html
<!-- emails/account_deleted.html -->

<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; }
        .container { max-width: 600px; margin: 0 auto; }
        .header { background-color: #f44336; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; }
        .warning { background-color: #fff3cd; padding: 10px; border-left: 4px solid #ffc107; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Account Deletion Confirmation</h2>
        </div>
        <div class="content">
            <p>Hello,</p>
            
            <p>This email confirms that your account has been successfully deleted.</p>
            
            <div class="warning">
                <strong>⚠️ Important:</strong>
                <p>This action is permanent. Your account and associated data have been removed from our system.</p>
            </div>
            
            <h3>What Was Deleted:</h3>
            <ul>
                <li>Your account and profile</li>
                <li>All personal information</li>
                <li>Saved addresses</li>
                <li>Cart items</li>
                <li>Authentication tokens</li>
            </ul>
            
            <h3>What Was Kept:</h3>
            <ul>
                <li>Order history (for record-keeping)</li>
                <li>Transaction records (for compliance)</li>
            </ul>
            
            <p><strong>Deletion Time:</strong> {{ deleted_at }}</p>
            <p><strong>Deletion Type:</strong> {{ deletion_type }}</p>
            
            <hr>
            
            <p>If you did not request this deletion or have any questions, please contact our support team:</p>
            <p>
                <strong>Email:</strong> support@example.com<br>
                <strong>Phone:</strong> +971-XX-XXXXXXX
            </p>
            
            <p>Best regards,<br>{{ APP_NAME }} Team</p>
        </div>
    </div>
</body>
</html>
```

---

## Production Checklist

- [ ] Email templates tested
- [ ] Backup retention set to 30+ days
- [ ] Audit logging enabled
- [ ] Error monitoring configured
- [ ] Support team briefed
- [ ] Privacy policy updated
- [ ] Frontend integration complete
- [ ] Load testing done
- [ ] Security review completed
- [ ] GDPR compliance verified

---

This gives you complete, production-ready code for implementing account deletion! 🎉
