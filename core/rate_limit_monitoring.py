"""
Rate Limiting Monitoring and Analytics
========================================

Provides monitoring, logging, and analytics capabilities for rate limiting.
Includes:
- Rate limit violation logging
- Cache monitoring
- DashboardAPI for admin to check rate limit status
- Prometheus metrics preparation
"""

import logging
from django.core.cache import cache
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


# ============================================================================
# RATE LIMIT VIOLATION LOGGER
# ============================================================================

class RateLimitViolationLogger:
    """
    Tracks and logs rate limit violations for monitoring and analysis.
    Stores violations in cache with TTL for temporary storage.
    """
    
    VIOLATION_KEY_PREFIX = "ratelimit:violation"
    VIOLATION_TTL = 86400  # 24 hours
    
    @classmethod
    def log_violation(cls, request, scope, throttle_cls_name):
        """
        Log a rate limit violation.
        
        Args:
            request: Request object
            scope: Throttle scope that was exceeded
            throttle_cls_name: Name of the throttle class
        """
        from core.rate_limit_utils import get_client_ip
        
        violation_data = {
            'timestamp': datetime.now().isoformat(),
            'scope': scope,
            'throttle_class': throttle_cls_name,
            'user_id': getattr(request.user, 'id', None),
            'ip_address': get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', 'unknown'),
            'path': request.path,
            'method': request.method,
            'is_authenticated': request.user.is_authenticated,
        }
        
        # Create unique violation key
        if request.user.is_authenticated:
            client_ident = f"user_{request.user.id}"
        else:
            client_ident = f"ip_{get_client_ip(request)}"
        
        violation_key = f"{cls.VIOLATION_KEY_PREFIX}:{scope}:{client_ident}:{datetime.now().timestamp()}"
        
        # Store violation
        cache.set(violation_key, violation_data, cls.VIOLATION_TTL)
        
        # Log warning
        logger.warning(
            f"Rate limit violation - Scope: {scope}, "
            f"User: {violation_data['user_id']}, "
            f"IP: {violation_data['ip_address']}, "
            f"Path: {violation_data['path']}"
        )
        
        return violation_data
    
    @classmethod
    def get_violations(cls, scope=None, user_id=None, limit=100):
        """
        Retrieve rate limit violations.
        
        Args:
            scope: Filter by throttle scope
            user_id: Filter by user ID
            limit: Maximum number of results
        
        Returns:
            list: Violation records
        """
        violations = []
        pattern = f"{cls.VIOLATION_KEY_PREFIX}:*"
        
        # Note: This requires explicit cache key/pattern search capability
        # May need to manually track or use a database for production
        logger.info(f"Rate limit violation query - Scope: {scope}, User: {user_id}")
        
        return violations


# ============================================================================
# RATE LIMIT MONITORING API
# ============================================================================

class RateLimitStatusAPI(APIView):
    """
    Admin API to check rate limit status for users/IPs.
    Only accessible to admin users.
    """
    permission_classes = [permissions.IsAdminUser]
    
    def get(self, request):
        """
        Get rate limit status for a specific user or IP.
        
        Query parameters:
            - user_id: Check rate limit for specific user
            - ip_address: Check rate limit for specific IP
            - scopes: Comma-separated list of scopes to check
        
        Returns:
            dict: Rate limit information
        """
        from core.rate_limit_utils import get_client_ip
        
        user_id = request.query_params.get('user_id')
        ip_address = request.query_params.get('ip_address')
        scopes_param = request.query_params.get('scopes')
        
        if not (user_id or ip_address):
            return Response(
                {'error': 'Either user_id or ip_address parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Build client identifier
        if user_id:
            client_ident = f"user_{user_id}"
        else:
            client_ident = f"ip_{ip_address}"
        
        # Get scopes to check
        if scopes_param:
            scopes = scopes_param.split(',')
        else:
            from core import throttling
            scopes = list(throttling.THROTTLE_RATES.keys())
        
        # Check rate limit status for each scope
        rate_limit_status = {}
        for scope in scopes:
            cache_key = f"ratelimit:{scope}:{client_ident}"
            current_count = cache.get(cache_key, 0)
            
            from core import throttling
            rate_config = throttling.THROTTLE_RATES.get(scope, 'unknown')
            
            rate_limit_status[scope] = {
                'current_requests': current_count,
                'rate_config': rate_config,
                'cache_key': cache_key,
            }
        
        return Response({
            'client_ident': client_ident,
            'timestamp': datetime.now().isoformat(),
            'rate_limits': rate_limit_status,
        })
    
    def post(self, request):
        """
        Reset rate limit for a specific user or IP.
        
        Request body:
            - user_id or ip_address: Identifier to reset
            - scopes: Optional comma-separated list of scopes to reset
        
        Returns:
            dict: Confirmation of reset
        """
        user_id = request.data.get('user_id')
        ip_address = request.data.get('ip_address')
        scopes_param = request.data.get('scopes')
        
        if not (user_id or ip_address):
            return Response(
                {'error': 'Either user_id or ip_address required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Build client identifier
        if user_id:
            client_ident = f"user_{user_id}"
        else:
            client_ident = f"ip_{ip_address}"
        
        # Get scopes to reset
        if scopes_param:
            scopes = scopes_param.split(',')
        else:
            from core import throttling
            scopes = list(throttling.THROTTLE_RATES.keys())
        
        # Reset cache for each scope
        reset_count = 0
        for scope in scopes:
            cache_key = f"ratelimit:{scope}:{client_ident}"
            if cache.delete(cache_key):
                reset_count += 1
        
        logger.info(
            f"Rate limit reset - Client: {client_ident}, "
            f"Scopes reset: {reset_count}/{len(scopes)}"
        )
        
        return Response({
            'client_ident': client_ident,
            'scopes_reset': reset_count,
            'total_scopes': len(scopes),
            'timestamp': datetime.now().isoformat(),
        })


# ============================================================================
# RATE LIMIT STATISTICS
# ============================================================================

class RateLimitStatsAPI(APIView):
    """
    Admin API to get rate limiting statistics.
    Shows aggregate data about rate limit violations and usage patterns.
    """
    permission_classes = [permissions.IsAdminUser]
    
    def get(self, request):
        """
        Get rate limiting statistics.
        
        Returns:
            dict: Statistics about rate limiting
        """
        cache_info = {
            'cache_backend': settings.CACHES['default']['BACKEND'],
            'cache_location': settings.CACHES['default'].get('LOCATION', 'N/A'),
        }
        
        throttle_config = {
            'default_throttle_classes': settings.REST_FRAMEWORK.get('DEFAULT_THROTTLE_CLASSES', []),
            'default_throttle_rates': settings.REST_FRAMEWORK.get('DEFAULT_THROTTLE_RATES', {}),
        }
        
        return Response({
            'timestamp': datetime.now().isoformat(),
            'cache_configuration': cache_info,
            'throttle_configuration': throttle_config,
            'message': 'Rate limit statistics API. Detailed violation tracking requires database backend.',
        })


# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

def configure_rate_limit_logging():
    """
    Configure logging for rate limiting.
    Call this in settings or management command to enable detailed logging.
    """
    logger = logging.getLogger('rate_limiting')
    logger.setLevel(logging.DEBUG)
    
    # File handler for rate limit violations
    try:
        handler = logging.FileHandler('logs/rate_limiting.log')
        handler.setLevel(logging.WARNING)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    except Exception as e:
        print(f"Error configuring rate limit logging: {e}")
    
    return logger


# ============================================================================
# METRICS FOR PROMETHEUS (Future Enhancement)
# ============================================================================

"""
Prometheus metrics can be added for monitoring:

from prometheus_client import Counter, Histogram, Gauge

rate_limit_violations = Counter(
    'rate_limit_violations_total',
    'Total rate limit violations',
    ['scope', 'throttle_class']
)

rate_limit_requests = Counter(
    'rate_limit_allowed_total',
    'Total allowed requests',
    ['scope']
)

request_latency = Histogram(
    'request_latency_seconds',
    'Request latency'
)

active_rate_limits = Gauge(
    'active_rate_limits',
    'Currently active rate limits'
)
"""


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def is_rate_limit_enabled():
    """Check if rate limiting is enabled"""
    throttle_classes = settings.REST_FRAMEWORK.get('DEFAULT_THROTTLE_CLASSES', [])
    return len(throttle_classes) > 0


def get_throttle_config():
    """Get complete throttle configuration"""
    return {
        'enabled': is_rate_limit_enabled(),
        'classes': settings.REST_FRAMEWORK.get('DEFAULT_THROTTLE_CLASSES', []),
        'rates': settings.REST_FRAMEWORK.get('DEFAULT_THROTTLE_RATES', {}),
    }
