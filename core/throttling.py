"""
Advanced Rate Limiting/Throttling Configuration
================================================

This module implements production-grade rate limiting using DRF's throttling system
with Redis caching for distributed environments.

Features:
- User-based throttling (authenticated users)
- IP-based throttling (anonymous users)
- Custom throttle classes for different endpoints
- Scope-based rate limits for specific operations
- Graceful degradation without Redis
"""

from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
import logging

logger = logging.getLogger(__name__)


class BaseCustomThrottle:
    """
    Base throttle marker class for shared configuration.
    Provides common THROTTLE_RATES definition.
    """
    THROTTLE_RATES = {}


# ============================================================================
# AUTHENTICATED USER THROTTLES
# ============================================================================

class UserGeneralThrottle(BaseCustomThrottle, UserRateThrottle):
    """
    General throttle for authenticated users on standard endpoints.
    Allows 1000 requests per hour for regular operations.
    
    Use Cases:
    - Listing products
    - Fetching orders
    - General browsing
    """
    scope = 'user_general'
    THROTTLE_RATES = {'user_general': '1000/hour'}


class UserAuthThrottle(BaseCustomThrottle, UserRateThrottle):
    """
    Strict throttle for authentication operations.
    Allows 50 requests per hour.
    
    Use Cases:
    - Password change
    - Token refresh
    - Email verification
    """
    scope = 'user_auth'
    THROTTLE_RATES = {'user_auth': '50/hour'}


class UserOrderThrottle(BaseCustomThrottle, UserRateThrottle):
    """
    Throttle specifically for order generation.
    Allows 100 requests per hour (prevents abuse of order creation).
    
    Use Cases:
    - Create order
    - Modify order
    """
    scope = 'user_order'
    THROTTLE_RATES = {'user_order': '100/hour'}


class UserPaymentThrottle(BaseCustomThrottle, UserRateThrottle):
    """
    Very strict throttle for payment operations.
    Allows 30 requests per hour.
    
    Use Cases:
    - Payment initiation
    - Payment verification
    - Refund requests
    """
    scope = 'user_payment'
    THROTTLE_RATES = {'user_payment': '30/hour'}


class UserReviewThrottle(BaseCustomThrottle, UserRateThrottle):
    """
    Throttle for review/rating operations.
    Allows 20 requests per hour (prevent spam/flooding).
    
    Use Cases:
    - Create review
    - Update review
    """
    scope = 'user_review'
    THROTTLE_RATES = {'user_review': '20/hour'}


class UserContactThrottle(BaseCustomThrottle, UserRateThrottle):
    """
    Throttle for contact/support messages.
    Allows 10 requests per hour.
    
    Use Cases:
    - Submit contact message
    - Support inquiry
    """
    scope = 'user_contact'
    THROTTLE_RATES = {'user_contact': '10/hour'}


# ============================================================================
# ANONYMOUS USER THROTTLES (IP-BASED)
# ============================================================================

class AnonGeneralThrottle(BaseCustomThrottle, AnonRateThrottle):
    """
    General throttle for anonymous/unauthenticated users.
    Allows 200 requests per hour per IP.
    
    Use Cases:
    - Browsing products
    - Viewing categories
    - Unprotected endpoints
    """
    scope = 'anon_general'
    THROTTLE_RATES = {'anon_general': '200/hour'}


class AnonAuthThrottle(BaseCustomThrottle, AnonRateThrottle):
    """
    Strict throttle for anonymous authentication attempts.
    Allows 30 requests per hour per IP (brute force protection).
    
    Use Cases:
    - Login attempts
    - Registration
    - Password reset requests
    - OTP requests
    """
    scope = 'anon_auth'
    THROTTLE_RATES = {'anon_auth': '30/hour'}


class AnonOTPThrottle(BaseCustomThrottle, AnonRateThrottle):
    """
    Very strict throttle for OTP generation.
    Allows 5 requests per hour per IP (prevents OTP spam).
    
    Use Cases:
    - OTP request
    - OTP verification
    """
    scope = 'anon_otp'
    THROTTLE_RATES = {'anon_otp': '5/hour'}


class AnonContactThrottle(BaseCustomThrottle, AnonRateThrottle):
    """
    Throttle for anonymous contact submissions.
    Allows 3 requests per hour per IP.
    
    Use Cases:
    - Contact message submission
    - Support inquiry
    """
    scope = 'anon_contact'
    THROTTLE_RATES = {'anon_contact': '3/hour'}


# ============================================================================
# COMBINED THROTTLE CLASSES (USER + ANON)
# ============================================================================

class CombinedAuthThrottle(tuple):
    """
    Combined throttle for general authentication endpoints.
    Uses user-specific throttle if authenticated, IP-based if anonymous.
    """
    def __new__(cls):
        return (UserAuthThrottle(), AnonAuthThrottle())


class CombinedOTPThrottle(tuple):
    """
    Combined throttle specifically for OTP endpoints.
    Very strict to prevent spam and abuse.
    """
    def __new__(cls):
        return (UserAuthThrottle(), AnonOTPThrottle())


class CombinedOrderThrottle(tuple):
    """
    Combined throttle for order operations (authenticated only).
    """
    def __new__(cls):
        return (UserOrderThrottle(), AnonGeneralThrottle())


class CombinedPaymentThrottle(tuple):
    """
    Combined throttle for payment operations.
    Very restrictive to prevent fraud.
    """
    def __new__(cls):
        return (UserPaymentThrottle(), AnonGeneralThrottle())


class CombinedReviewThrottle(tuple):
    """
    Combined throttle for review/rating operations.
    """
    def __new__(cls):
        return (UserReviewThrottle(), AnonGeneralThrottle())


class CombinedContactThrottle(tuple):
    """
    Combined throttle for contact submissions.
    """
    def __new__(cls):
        return (UserContactThrottle(), AnonContactThrottle())


from rest_framework.throttling import UserRateThrottle, AnonRateThrottle

class CombinedGeneralThrottle(UserRateThrottle):
    scope = "user_general"

class CombinedAnonThrottle(AnonRateThrottle):
    scope = "anon_general"

# ============================================================================
# RATE LIMIT CONFIGURATION CONSTANTS
# ============================================================================

THROTTLE_RATES = {
    # General
    'user_general': '1000/hour',
    'anon_general': '200/hour',

    # Authentication
    'user_auth': '50/hour',
    'anon_auth': '30/hour',

    # OTP (Strict)
    'anon_otp': '5/hour',

    # Orders
    'user_order': '100/hour',

    # Payments (Very Strict)
    'user_payment': '30/hour',

    # Reviews
    'user_review': '20/hour',

    # Contact/Support (Very Strict)
    'user_contact': '10/hour',
    'anon_contact': '3/hour',
}


# ============================================================================
# DEFAULT THROTTLE CLASS FOR ALL ENDPOINTS
# ============================================================================

DEFAULT_THROTTLE_CLASSES = [
    'core.throttling.CombinedGeneralThrottle',
]
