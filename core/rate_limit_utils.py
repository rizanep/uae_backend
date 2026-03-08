"""
Rate Limiting Utilities and Decorators
========================================

Provides helper functions and decorators for easily applying
rate limiting to viewsets and APIViews.

Usage:
    @throttle_auth_view
    class MyLoginView(APIView):
        ...
    
    @throttle_action('user_order')
    @action(detail=False, methods=['post'])
    def create_order(self, request):
        ...
"""

from functools import wraps
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from rest_framework.decorators import throttle_classes
from django.core.cache import cache
from django.utils.decorators import method_decorator
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# CUSTOM THROTTLE CHECK FUNCTIONS
# ============================================================================

def get_client_ip(request):
    """
    Extract client IP address from request.
    Handles X-Forwarded-For header for proxied requests.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def check_rate_limit(request, scope, requests_limit, time_window):
    """
    Manual rate limit check using cache.
    
    Args:
        request: Request object
        scope: Identifier for the rate limit scope (e.g., 'otp_request')
        requests_limit: Number of requests allowed
        time_window: Time window in seconds
    
    Returns:
        tuple: (is_allowed: bool, remaining_requests: int, retry_after: int)
    
    Example:
        is_allowed, remaining, retry_after = check_rate_limit(
            request, 'otp_request', 5, 3600
        )
        if not is_allowed:
            return Response(
                {'error': f'Rate limited. Retry after {retry_after}s'},
                status=429,
                headers={'Retry-After': str(retry_after)}
            )
    """
    # Build cache key
    if request.user.is_authenticated:
        client_ident = f"user_{request.user.id}"
    else:
        client_ident = f"ip_{get_client_ip(request)}"
    
    cache_key = f"ratelimit:{scope}:{client_ident}"
    
    # Get current request count
    current_count = cache.get(cache_key, 0)
    
    if current_count >= requests_limit:
        # Rate limit exceeded
        ttl = cache.ttl(cache_key) if hasattr(cache, 'ttl') else time_window
        logger.warning(
            f"Rate limit exceeded for {scope} - {client_ident} - "
            f"Requests: {current_count}/{requests_limit}"
        )
        return False, 0, ttl
    
    # Increment and set expiry
    new_count = current_count + 1
    cache.set(cache_key, new_count, time_window)
    
    remaining = requests_limit - new_count
    return True, remaining, 0


def should_apply_rate_limit(request, force=False):
    """
    Determine if rate limiting should be applied to this request.
    
    Returns False for:
    - Admin users (can bypass with ENABLE_ADMIN_RATE_LIMIT setting)
    - Health check endpoints
    
    Args:
        request: Request object
        force: If True, apply rate limit regardless of user role
    
    Returns:
        bool: Whether rate limiting should apply
    """
    from django.conf import settings
    
    if not force and request.user.is_authenticated:
        if request.user.is_superuser:
            enable_admin_limit = getattr(settings, 'ENABLE_ADMIN_RATE_LIMIT', False)
            if not enable_admin_limit:
                return False
    
    return True


# ============================================================================
# DECORATORS FOR VIEWS
# ============================================================================

def throttle_auth_view(view_class):
    """
    Apply authentication throttling to a view.
    Uses combined auth throttle (user + anon).
    
    Use for: Login, register, token refresh, password reset
    """
    from core.throttling import CombinedAuthThrottle
    
    return throttle_classes([CombinedAuthThrottle])(view_class)


def throttle_otp_view(view_class):
    """
    Apply very strict OTP throttling.
    
    Use for: OTP request, OTP verification
    """
    from core.throttling import CombinedOTPThrottle
    
    return throttle_classes([CombinedOTPThrottle])(view_class)


def throttle_payment_view(view_class):
    """
    Apply strict payment throttling.
    
    Use for: Payment initiation, payment verification, refunds
    """
    from core.throttling import CombinedPaymentThrottle
    
    return throttle_classes([CombinedPaymentThrottle])(view_class)


def throttle_order_view(view_class):
    """
    Apply order creation throttling.
    
    Use for: Order creation, order modification
    """
    from core.throttling import CombinedOrderThrottle
    
    return throttle_classes([CombinedOrderThrottle])(view_class)


def throttle_review_view(view_class):
    """
    Apply review/rating throttling.
    
    Use for: Create review, update review
    """
    from core.throttling import CombinedReviewThrottle
    
    return throttle_classes([CombinedReviewThrottle])(view_class)


def throttle_contact_view(view_class):
    """
    Apply contact submission throttling.
    
    Use for: Contact form submission, support tickets
    """
    from core.throttling import CombinedContactThrottle
    
    return throttle_classes([CombinedContactThrottle])(view_class)


def throttle_action(scope):
    """
    Decorator for throttling specific ViewSet actions.
    
    Usage:
        @throttle_action('user_auth')
        @action(detail=False, methods=['post'])
        def login(self, request):
            ...
    
    Args:
        scope: Throttle scope to apply
    """
    def decorator(func):
        # Get the throttle class for this scope
        from core import throttling
        
        # Map scopes to throttle classes
        scope_map = {
            'user_auth': [throttling.UserAuthThrottle(), throttling.AnonAuthThrottle()],
            'user_order': [throttling.UserOrderThrottle(), throttling.AnonGeneralThrottle()],
            'user_payment': [throttling.UserPaymentThrottle(), throttling.AnonGeneralThrottle()],
            'user_review': [throttling.UserReviewThrottle(), throttling.AnonGeneralThrottle()],
            'user_contact': [throttling.UserContactThrottle(), throttling.AnonContactThrottle()],
            'anon_otp': [throttling.UserAuthThrottle(), throttling.AnonOTPThrottle()],
            'user_general': [throttling.UserGeneralThrottle(), throttling.AnonGeneralThrottle()],
        }
        
        throttle_classes_list = scope_map.get(scope, [throttling.UserGeneralThrottle(), throttling.AnonGeneralThrottle()])
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # Apply throttle_classes decorator
        wrapper = throttle_classes(throttle_classes_list)(wrapper)
        return wrapper
    
    return decorator


# ============================================================================
# MIDDLEWARE FOR GLOBAL RATE LIMITING MONITORING
# ============================================================================

class RateLimitLoggingMiddleware:
    """
    Middleware to log rate limiting violations and monitor throttling.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.excluded_paths = ['/api/health/', '/static/', '/media/']
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Log 429 (Too Many Requests) responses
        if response.status_code == 429:
            logger.warning(
                f"Rate limit triggered: {request.method} {request.path} - "
                f"IP: {get_client_ip(request)} - "
                f"User: {getattr(request.user, 'id', 'anonymous')}"
            )
        
        return response


# ============================================================================
# TESTING UTILITIES
# ============================================================================

def reset_rate_limit_cache(request, scope):
    """
    Reset rate limit cache for a specific scope.
    Useful for testing and administrative functions.
    
    Args:
        request: Request object
        scope: Throttle scope to reset
    """
    if request.user.is_authenticated:
        client_ident = f"user_{request.user.id}"
    else:
        client_ident = f"ip_{get_client_ip(request)}"
    
    cache_key = f"ratelimit:{scope}:{client_ident}"
    cache.delete(cache_key)
    
    logger.info(f"Reset rate limit for {scope} - {client_ident}")


def get_rate_limit_status(request, scopes=None):
    """
    Get current rate limit status for a user/IP.
    
    Args:
        request: Request object
        scopes: List of scopes to check (default: all)
    
    Returns:
        dict: Rate limit information for each scope
    """
    from core import throttling
    
    if scopes is None:
        scopes = throttling.THROTTLE_RATES.keys()
    
    if request.user.is_authenticated:
        client_ident = f"user_{request.user.id}"
    else:
        client_ident = f"ip_{get_client_ip(request)}"
    
    status = {}
    for scope in scopes:
        cache_key = f"ratelimit:{scope}:{client_ident}"
        current_count = cache.get(cache_key, 0)
        rate = throttling.THROTTLE_RATES.get(scope, 'unknown')
        
        status[scope] = {
            'current_count': current_count,
            'rate': rate,
            'cache_key': cache_key,
        }
    
    return status
