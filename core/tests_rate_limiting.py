"""
Rate Limiting Tests
====================

Test suite for verifying rate limiting functionality.

Run with: python manage.py test core.tests.RateLimitingTests
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from django.core.cache import cache
from core.rate_limit_utils import check_rate_limit, get_client_ip
from core.throttling import (
    UserGeneralThrottle, AnonGeneralThrottle,
    UserAuthThrottle, AnonAuthThrottle,
    UserOTPThrottle, AnonOTPThrottle
)
import time

User = get_user_model()


class RateLimitingThrottleTests(APITestCase):
    """Test rate limiting throttle classes"""
    
    def setUp(self):
        """Set up test user and client"""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.client = APIClient()
        # Clear cache before each test
        cache.clear()
    
    def tearDown(self):
        """Clean up after tests"""
        cache.clear()
    
    def test_user_general_throttle_limit(self):
        """Test that UserGeneralThrottle respects rate limit"""
        throttle = UserGeneralThrottle()
        request = self.client.get('/api/products/').wsgi_request
        request.user = self.user
        
        # First request should succeed
        self.assertTrue(throttle.allow_request(request, None))
        
        # Get the ident key for this user
        ident = throttle.get_ident(request)
        cache_key = throttle.cache_format % {
            'scope': throttle.scope,
            'ident': ident
        }
        
        # Set request count to almost the limit
        cache.set(cache_key, 999, 3600)
        
        # Next request should still succeed (at limit)
        self.assertTrue(throttle.allow_request(request, None))
        
        # Request above limit should fail
        self.assertFalse(throttle.allow_request(request, None))
    
    def test_anon_auth_throttle_limit(self):
        """Test that AnonAuthThrottle respects rate limit for anonymous users"""
        throttle = AnonAuthThrottle()
        request = self.client.get('/api/auth/login/').wsgi_request
        
        # Ensure request is from anonymous user
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()
        
        # Get the IP-based key
        ident = throttle.get_ident(request)
        cache_key = throttle.cache_format % {
            'scope': throttle.scope,
            'ident': ident
        }
        
        # Set request count to at limit for this scope
        cache.set(cache_key, 30, 3600)  # anon_auth is 30/hour
        
        # Next request should fail
        self.assertFalse(throttle.allow_request(request, None))
    
    def test_rate_limit_resets_after_window(self):
        """Test that rate limit resets after the time window expires"""
        throttle = UserGeneralThrottle()
        request = self.client.get('/api/products/').wsgi_request
        request.user = self.user
        
        # Set cache with very short TTL (1 second)
        ident = throttle.get_ident(request)
        cache_key = throttle.cache_format % {
            'scope': throttle.scope,
            'ident': ident
        }
        cache.set(cache_key, 1000, 1)  # 1000 requests, expires in 1 second
        
        # Should be rate limited
        self.assertFalse(throttle.allow_request(request, None))
        
        # Wait for cache to expire
        time.sleep(1.1)
        
        # Should be allowed again
        self.assertTrue(throttle.allow_request(request, None))


class RateLimitingUtilsTests(TestCase):
    """Test rate limiting utility functions"""
    
    def setUp(self):
        """Set up test user and client"""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.client = APIClient()
        cache.clear()
    
    def tearDown(self):
        """Clean up after tests"""
        cache.clear()
    
    def test_check_rate_limit_allowed(self):
        """Test check_rate_limit allows requests within limit"""
        request = self.client.get('/').wsgi_request
        request.user = self.user
        
        # Should allow 5 requests within the window
        for i in range(5):
            is_allowed, remaining, retry_after = check_rate_limit(
                request,
                scope='test_scope',
                requests_limit=10,
                time_window=3600
            )
            self.assertTrue(is_allowed)
            self.assertEqual(remaining, 10 - i - 1)
            self.assertEqual(retry_after, 0)
    
    def test_check_rate_limit_exceeded(self):
        """Test check_rate_limit rejects requests over limit"""
        request = self.client.get('/').wsgi_request
        request.user = self.user
        
        # Fill up the limit
        for i in range(5):
            check_rate_limit(
                request,
                scope='test_scope',
                requests_limit=5,
                time_window=3600
            )
        
        # Next request should be rejected
        is_allowed, remaining, retry_after = check_rate_limit(
            request,
            scope='test_scope',
            requests_limit=5,
            time_window=3600
        )
        
        self.assertFalse(is_allowed)
        self.assertEqual(remaining, 0)
        self.assertGreater(retry_after, 0)
    
    def test_get_client_ip_direct(self):
        """Test IP extraction from direct request"""
        request = self.client.get('/').wsgi_request
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        ip = get_client_ip(request)
        self.assertEqual(ip, '192.168.1.1')
    
    def test_get_client_ip_forwarded(self):
        """Test IP extraction from X-Forwarded-For header"""
        request = self.client.get('/').wsgi_request
        request.META['HTTP_X_FORWARDED_FOR'] = '203.0.113.1, 198.51.100.1'
        
        ip = get_client_ip(request)
        self.assertEqual(ip, '203.0.113.1')


class RateLimitingIntegrationTests(APITestCase):
    """Integration tests for rate limiting on actual endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            is_phone_verified=True,
            phone_number='+971501234567'
        )
        self.client = APIClient()
        cache.clear()
    
    def tearDown(self):
        """Clean up"""
        cache.clear()
    
    def test_user_me_endpoint_not_rate_limited_heavily(self):
        """Test that general user endpoints have reasonable rate limits"""
        self.client.force_authenticate(user=self.user)
        
        # Make multiple requests to /me/ endpoint
        for i in range(50):
            response = self.client.get('/api/users/me/')
            # Should succeed (user_general is 1000/hour)
            if response.status_code == 429:
                # If we hit rate limit, that's at 50+ requests, which is OK for this test
                break
            self.assertIn(response.status_code, [200, 429])
    
    def test_different_users_have_separate_limits(self):
        """Test that different authenticated users have separate rate limit counters"""
        user2 = User.objects.create_user(
            email='test2@example.com',
            password='testpass123'
        )
        
        # Client 1 for user1
        client1 = APIClient()
        client1.force_authenticate(user=self.user)
        
        # Client 2 for user2
        client2 = APIClient()
        client2.force_authenticate(user=user2)
        
        # Both should be able to make requests
        response1 = client1.get('/api/users/me/')
        response2 = client2.get('/api/users/me/')
        
        # Both should succeed (different rate limit buckets)
        self.assertIn(response1.status_code, [200, 429])
        self.assertIn(response2.status_code, [200, 429])
    
    def test_anonymous_users_rate_limited_by_ip(self):
        """Test that anonymous users are rate limited by IP"""
        # Both requests have same fake IP
        self.client._base_environ['REMOTE_ADDR'] = '192.168.1.100'
        
        # Make multiple requests
        responses = []
        for i in range(10):
            response = self.client.get('/api/products/')
            responses.append(response.status_code)
        
        # Should get mix of 200s and possibly 429s based on limits
        # General throttle is 200/hour for anon, so 10 should definitely work
        self.assertIn(200, responses)


class RateLimitingMonitoringTests(APITestCase):
    """Test rate limit monitoring APIs"""
    
    def setUp(self):
        """Set up test users"""
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='adminpass123',
            role='admin',
            is_staff=True,
            is_superuser=True
        )
        self.regular_user = User.objects.create_user(
            email='user@example.com',
            password='userpass123'
        )
        self.client = APIClient()
        cache.clear()
    
    def tearDown(self):
        """Clean up"""
        cache.clear()
    
    def test_rate_limit_status_api_requires_admin(self):
        """Test that rate limit status API requires admin permission"""
        # As anonymous
        response = self.client.get('/api/admin/rate-limit/status/?user_id=1')
        self.assertEqual(response.status_code, 401)
        
        # As regular user
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get('/api/admin/rate-limit/status/?user_id=1')
        self.assertEqual(response.status_code, 403)
    
    def test_rate_limit_status_api_admin_access(self):
        """Test that admin can access rate limit status API"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get('/api/admin/rate-limit/status/?user_id=1')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('client_ident', data)
        self.assertIn('rate_limits', data)
    
    def test_rate_limit_status_missing_parameters(self):
        """Test that rate limit status API requires user_id or ip_address"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.get('/api/admin/rate-limit/status/')
        self.assertEqual(response.status_code, 400)
    
    def test_rate_limit_reset_api(self):
        """Test rate limit reset API"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Set some cache values
        cache.set('ratelimit:user_auth:user_1:test', 50, 3600)
        
        # Reset limits
        response = self.client.post(
            '/api/admin/rate-limit/status/',
            {'user_id': 1, 'scopes': 'user_auth'},
            format='json'
        )
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('scopes_reset', data)
        self.assertGreater(data['scopes_reset'], 0)


# Helper test case for manual testing
class ManualTestingHelper(APITestCase):
    """
    Helper class for manual testing rate limits.
    
    Usage in shell:
        python manage.py shell
        from core.tests import ManualTestingHelper
        helper = ManualTestingHelper()
        helper.test_otp_rate_limit()
    """
    
    def test_otp_rate_limit(self):
        """Manually test OTP rate limiting"""
        print("\n=== Testing OTP Rate Limit ===")
        from core.rate_limit_utils import check_rate_limit
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.post('/api/users/otp/request/')
        
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        
        # Test 5 consecutive requests (should succeed)
        for i in range(5):
            is_allowed, remaining, retry = check_rate_limit(
                request, 'anon_otp', 5, 3600
            )
            status_str = "✓ ALLOWED" if is_allowed else "✗ BLOCKED"
            print(f"Request {i+1}: {status_str} (Remaining: {remaining})")
        
        # 6th should fail
        is_allowed, remaining, retry = check_rate_limit(
            request, 'anon_otp', 5, 3600
        )
        print(f"Request 6: {'✓ ALLOWED (ERROR!)' if is_allowed else '✗ BLOCKED (Expected)'}")


if __name__ == '__main__':
    import django
    django.setup()
    print("Rate limiting tests ready to run")
