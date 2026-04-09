from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, throttle_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils import timezone
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
import json
import requests
import logging
import jwt
from datetime import datetime
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from .models import User, GoogleOAuthToken, OTPToken, UserProfile, UserAddress
from .serializers import (
    UserSerializer, UserCreateSerializer, UserUpdateSerializer,
    UserAdminSerializer, CustomTokenObtainPairSerializer,
    ChangePasswordSerializer, GoogleOAuthSerializer,
    OTPRequestSerializer, OTPLoginSerializer, VerifyNewContactSerializer,
    DeliveryBoyCreateSerializer, DeliveryBoyUpdateSerializer
)
from .permissions import IsOwnerOrAdmin, IsAdmin
from core.rate_limit_utils import throttle_auth_view, throttle_otp_view
from Marketing.services import apply_referral_code
from core.throttling import (
    UserAuthThrottle, AnonAuthThrottle,
    UserGeneralThrottle, AnonGeneralThrottle
)

# Cookie settings
COOKIE_ACCESS_NAME = 'access_token'
COOKIE_REFRESH_NAME = 'refresh_token'
COOKIE_MAX_AGE = 7 * 24 * 60 * 60  # 7 days


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for User CRUD operations
    - List/Create users
    - Retrieve/Update/Delete user details
    - Admin can manage all users
    - Users can manage their own profiles
    """
    queryset = User.objects.filter(deleted_at__isnull=True)
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = "__all__"
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action and user role"""
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action == 'update' or self.action == 'partial_update':
            if self.request.user.is_authenticated and self.request.user.role == 'admin':
                return UserAdminSerializer
            return UserUpdateSerializer
        elif self.request.user.is_authenticated and self.request.user.role == 'admin':
            return UserAdminSerializer
        return UserSerializer
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action == 'create':
            return [permissions.AllowAny()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsOwnerOrAdmin()]
        return [permissions.IsAuthenticated()]
    
    def get_queryset(self):
        """Filter queryset based on user role"""
        user = self.request.user
        if user.is_authenticated and user.role == 'admin':
            return User.objects.filter(deleted_at__isnull=True).select_related("profile", "delivery_profile").prefetch_related("addresses", "orders")
        return User.objects.filter(id=user.id, deleted_at__isnull=True).select_related("profile", "delivery_profile").prefetch_related("addresses")
    
    def create(self, request, *args, **kwargs):
        """Create a new user (registration)"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED
        )

    def retrieve(self, request, *args, **kwargs):
        """Retrieve a specific user; show delivery-boy-safe view for delivery boys."""
        instance = self.get_object()
        serializer_class = UserSerializer if instance.role == 'delivery_boy' else self.get_serializer_class()
        return Response(serializer_class(instance).data)
    
    def update(self, request, *args, **kwargs):
        """Update user details"""
        instance = self.get_object()
        
        # Check permissions
        if request.user != instance and (not request.user.is_authenticated or request.user.role != 'admin'):
            return Response(
                {'detail': 'You do not have permission to update this user.'},
                status=status.HTTP_403_FORBIDDEN
            )
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        # Refresh instance to reflect nested updates and return full read serializer
        refreshed = User.objects.select_related("profile").get(pk=instance.pk)
        return Response(UserSerializer(refreshed).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete user"""
        instance = self.get_object()
        
        # Check permissions
        if request.user != instance and (not request.user.is_authenticated or request.user.role != 'admin'):
            return Response(
                {'detail': 'You do not have permission to delete this user.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        instance.soft_delete()
        
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user profile"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @throttle_classes([UserAuthThrottle(), AnonAuthThrottle()])
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """
        Change user password.
        Rate limited: 50 requests/hour for users
        """
        user = request.user
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Verify old password
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {'old_password': 'Wrong password.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Set new password
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({'detail': 'Password changed successfully.'})
    
    @action(detail=True, methods=['post'])
    def set_role(self, request, pk=None):
        """Admin: Set user role"""
        if request.user.role != 'admin':
            return Response(
                {'detail': 'Only admins can set user roles.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user = self.get_object()
        role = request.data.get('role')
        
        if role not in ['admin', 'user', 'delivery_boy']:
            return Response(
                {'detail': 'Invalid role. Must be "admin", "user", or "delivery_boy".'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.role = role
        user.save()
        
        return Response(
            UserSerializer(user).data,
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['get'])
    def admin_list(self, request):
        """Admin: Get all users including soft-deleted"""
        if request.user.role != 'admin':
            return Response(
                {'detail': 'Only admins can view all users.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        include_deleted = request.query_params.get('include_deleted', 'false').lower() == 'true'
        
        role = request.query_params.get('role')

        if include_deleted:
            queryset = User.objects.all()
        else:
            queryset = User.objects.filter(deleted_at__isnull=True)

        queryset = queryset.select_related('profile', 'delivery_profile').prefetch_related('addresses', 'orders')

        if role:
            queryset = queryset.filter(role=role)

        serializer_class = UserAdminSerializer
        if role == 'delivery_boy':
            serializer_class = UserSerializer

        serializer = serializer_class(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def delivery_boys(self, request):
        """Admin: List delivery boys with delivery-profile-specific details."""
        if request.user.role != 'admin':
            return Response(
                {'detail': 'Only admins can view delivery boys.'},
                status=status.HTTP_403_FORBIDDEN
            )

        include_deleted = request.query_params.get('include_deleted', 'false').lower() == 'true'
        queryset = User.objects.filter(role='delivery_boy')
        if not include_deleted:
            queryset = queryset.filter(deleted_at__isnull=True)

        queryset = queryset.select_related('profile', 'delivery_profile').prefetch_related('addresses', 'orders')
        serializer = UserSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def delivery_boy_detail(self, request, pk=None):
        """Admin: Get one delivery boy with delivery-profile-specific details."""
        if request.user.role != 'admin':
            return Response(
                {'detail': 'Only admins can view delivery boys.'},
                status=status.HTTP_403_FORBIDDEN
            )

        delivery_boy = self.get_object()
        if delivery_boy.role != 'delivery_boy':
            return Response(
                {'detail': 'Requested user is not a delivery boy.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(UserSerializer(delivery_boy).data)

    @action(detail=True, methods=['patch'])
    def update_delivery_boy(self, request, pk=None):
        """Admin: Update delivery-boy-specific user and profile fields."""
        if request.user.role != 'admin':
            return Response(
                {'detail': 'Only admins can update delivery boys.'},
                status=status.HTTP_403_FORBIDDEN
            )

        delivery_boy = self.get_object()
        if delivery_boy.role != 'delivery_boy':
            return Response(
                {'detail': 'Requested user is not a delivery boy.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = DeliveryBoyUpdateSerializer(
            delivery_boy,
            data=request.data,
            partial=True,
            context={'delivery_boy': delivery_boy},
        )
        serializer.is_valid(raise_exception=True)
        updated_delivery_boy = serializer.save()
        return Response(UserSerializer(updated_delivery_boy).data)
    
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Admin: Restore soft-deleted user"""
        if request.user.role != 'admin':
            return Response(
                {'detail': 'Only admins can restore users.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user = User.objects.get(id=pk)
        user.restore()
        
        return Response(
            UserSerializer(user).data,
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAdminUser])
    def users_count(self, request):
        """
        Get a summary of user counts by status.
        Returns: total users, active, blocked/inactive, admins.
        """
        users_qs = User.objects.filter(deleted_at__isnull=True)
        total_users = users_qs.count()
        
        active = users_qs.filter(is_active=True).count()
        blocked = users_qs.filter(is_active=False).count()
        admins = users_qs.filter(role='admin').count()
        
        return Response({
            "total_users": total_users,
            "active": active,
            "blocked": blocked,
            "admins": admins
        })

    @action(detail=False, methods=['post'])
    def create_delivery_boy(self, request):
        """
        Admin-only: Create a new delivery boy user with profile.
        
        Request body:
        {
            "email": "delivery@example.com",
            "phone_number": "+971501234567",
            "first_name": "Ahmed",
            "last_name": "Ali",
            "assigned_emirates": ["abu_dhabi", "dubai"],
            "vehicle_number": "ABC123",
            "identity_number": "784-1234-5678-9",
            "emergency_contact": "+971509876543",
            "notes": "Fast delivery driver",
            "is_available": true
        }
        """
        if request.user.role != 'admin':
            return Response(
                {'detail': 'Only admins can create delivery boys.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = DeliveryBoyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED
        )


class LoginView(TokenObtainPairView):
    """
    Login view with cookie support
    - Issues JWT tokens
    - Sets HttpOnly cookies for tokens
    - Updates last login time
    - Handles referral code application with coupon creation
    """
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        # Check user active status
        email = request.data.get('email')
        phone = request.data.get('phone_number')
        referral_code = request.data.get('referral_code', '').strip()
        
        if email:
            user = User.objects.filter(email=email).first()
            if user and not user.is_active:
                return Response(
                    {'detail': 'user is inactive pls contact support'},
                    status=status.HTTP_403_FORBIDDEN
                )

        response = super().post(request, *args, **kwargs)
        
        if response.status_code == status.HTTP_200_OK and isinstance(response.data, dict):
            access = response.data.get('access')
            refresh = response.data.get('refresh')
            
            if access:
                response.set_cookie(
                    COOKIE_ACCESS_NAME,
                    access,
                    max_age=COOKIE_MAX_AGE,
                    httponly=True,
                    secure=settings.DEBUG is False,
                    samesite='Lax',
                )
            
            if refresh:
                response.set_cookie(
                    COOKIE_REFRESH_NAME,
                    refresh,
                    max_age=COOKIE_MAX_AGE,
                    httponly=True,
                    secure=settings.DEBUG is False,
                    samesite='Lax',
                )
            
            # Handle referral code after successful login
            if referral_code:
                # Try to get user by email first, then by phone
                user = None
                if email:
                    user = User.objects.filter(email=email).first()
                elif phone:
                    user = User.objects.filter(phone_number=phone).first()
                
                if user:
                    try:
                        success, message = apply_referral_code(user, referral_code)
                        response.data['referral'] = {
                            'success': success,
                            'message': message
                        }
                        if success:
                            response.data['detail'] = 'Login successful. Referral code applied and coupons created!'
                        else:
                            # Add warning if referral failed but login succeeded
                            response.data['detail'] = 'Login successful but referral code could not be applied.'
                    except Exception as e:
                        response.data['referral'] = {
                            'success': False,
                            'message': f'Error applying referral code: {str(e)}'
                        }
                else:
                    response.data['referral'] = {
                        'success': False,
                        'message': 'User not found to apply referral code'
                    }
            
        return response


class RefreshView(TokenRefreshView):
    """
    Token refresh view with cookie support
    - Reads refresh token from cookies if not in body
    - Issues new access token
    - Sets new access token in cookie
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        # Check if refresh token is in cookies
        if 'refresh' not in request.data and COOKIE_REFRESH_NAME in request.COOKIES:
            request.data = request.data.copy()
            request.data['refresh'] = request.COOKIES.get(COOKIE_REFRESH_NAME)
        
        # Check user active status from refresh token
        refresh_token = request.data.get('refresh')
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                user_id = token['user_id']
                user = User.objects.get(id=user_id)
                if not user.is_active:
                    return Response(
                        {'detail': 'user is inactive pls contact support'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            except Exception:
                # If token is invalid, let super().post() handle it
                pass
        
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == status.HTTP_200_OK and isinstance(response.data, dict):
            access = response.data.get('access')
            
            if access:
                response.set_cookie(
                    COOKIE_ACCESS_NAME,
                    access,
                    max_age=COOKIE_MAX_AGE,
                    httponly=True,
                    secure=settings.DEBUG is False,
                    samesite='Lax',
                )
        
        return response


class LogoutView(APIView):
    """
    Logout view
    - Blacklists refresh token
    - Clears auth cookies
    
    Rate limited: 50 requests/hour (user_auth throttle)
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get(COOKIE_REFRESH_NAME) or request.data.get('refresh')
        
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                pass
        
        response = Response(
            {'detail': 'Successfully logged out.'},
            status=status.HTTP_200_OK
        )
        response.delete_cookie(COOKIE_ACCESS_NAME)
        response.delete_cookie(COOKIE_REFRESH_NAME)
        
        return response


@throttle_auth_view
class GoogleAuthCallbackView(APIView):
    """
    Google OAuth callback handler
    - Exchange authorization code for tokens
    - Create/update user
    - Issue JWT tokens
    
    Rate limited: 30 requests/hour per IP for anonymous, 50/hour for users
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        code = request.query_params.get('code')
        if not code:
            return Response(
                {'detail': 'Authorization code is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return self._handle_code(code)

    def post(self, request):
        code = request.data.get('code')
        if not code:
            return Response(
                {'detail': 'Authorization code is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return self._handle_code(code)

    def _verify_google_token(self, token):
        """
        Verify and decode Google ID token (JWT) using Google's official library.
        
        Args:
            token: Google ID token from frontend
            
        Returns:
            dict: Decoded token payload with user info
            
        Raises:
            ValueError: If token is invalid
        """
        try:
            # Use Google's official library to verify the token
            request = google_requests.Request()
            payload = id_token.verify_oauth2_token(
                token,
                request,
                audience=settings.GOOGLE_OAUTH_CLIENT_ID
            )
            
            # Additional validation
            if payload.get('iss') not in ['https://accounts.google.com', 'accounts.google.com']:
                raise ValueError('Invalid token issuer')
            
            return payload
            
        except ValueError as e:
            # Re-raise with more specific message
            error_msg = str(e)
            if 'expired' in error_msg.lower():
                raise ValueError('Token has expired')
            elif 'audience' in error_msg.lower():
                raise ValueError(f'Invalid token audience. Expected {settings.GOOGLE_OAUTH_CLIENT_ID}')
            else:
                raise ValueError(f'Invalid token: {error_msg}')
        except Exception as e:
            raise ValueError(f'Token verification failed: {str(e)}')

    def _handle_code(self, code):
        try:
            # Debug: Log the token format
            logger = logging.getLogger(__name__)
            logger.debug(f"Google token received - Type: {type(code)}, Length: {len(code) if isinstance(code, str) else 'N/A'}")
            
            if not isinstance(code, str) or not code.strip():
                raise ValueError('Token must be a non-empty string')
            
            # Count segments for JWT validation
            segments = code.strip().count('.')
            if segments != 2:
                logger.error(f"Invalid JWT format. Expected 3 segments (2 dots), got {segments + 1}")
                raise ValueError(f'Invalid token format. Expected JWT with 3 segments, got {segments + 1}. Token may not be a valid Google ID token.')
            
            # Verify the Google ID token (JWT)
            userinfo = self._verify_google_token(code)
            
            google_id = userinfo['sub']  # 'sub' is the Google user ID in JWT
            email = userinfo.get('email', '')
            first_name = userinfo.get('given_name', '')
            last_name = userinfo.get('family_name', '')
            picture_url = userinfo.get('picture')
            locale = userinfo.get('locale')

            with transaction.atomic():
                user = User.objects.filter(google_id=google_id).first()
                created = False

                if not user and email:
                    # Link Google login to an existing account with the same email.
                    user = User.objects.filter(email=email).first()

                if user:
                    # If google_id differs but email matches verified Google email,
                    # re-link to the latest provider id for this account.
                    user.google_id = google_id
                    user.email = email
                    user.first_name = first_name
                    user.last_name = last_name
                    user.google_email = email
                    user.is_email_verified = True
                    user.save()
                else:
                    created = True
                    try:
                        user = User.objects.create_user(
                            email=email,
                            password=None,
                            first_name=first_name,
                            last_name=last_name,
                            google_id=google_id,
                            google_email=email,
                            is_email_verified=True,
                        )
                    except IntegrityError:
                        # Handle race conditions safely by reloading existing user.
                        user = User.objects.filter(email=email).first()
                        if not user:
                            raise
                        created = False
                        user.google_id = google_id
                        user.google_email = email
                        user.is_email_verified = True
                        user.save(update_fields=['google_id', 'google_email', 'is_email_verified'])

            if not user.is_active:
                return Response(
                    {'detail': 'user is inactive pls contact support'},
                    status=status.HTTP_403_FORBIDDEN
                )

            if not created:
                user.email = email
                user.first_name = first_name
                user.last_name = last_name
                user.google_email = email
                user.is_email_verified = True
                user.save()
            else:
                # Create first order coupon for new Google OAuth user
                from Marketing.services import create_first_order_coupon
                try:
                    create_first_order_coupon(user)
                except Exception as e:
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to create first order coupon for Google OAuth user {user.id}: {str(e)}")

            profile, _ = UserProfile.objects.get_or_create(user=user)

            if picture_url:
                try:
                    picture_response = requests.get(picture_url, timeout=5)
                    picture_response.raise_for_status()
                    file_name = f'google_{user.id}.jpg'
                    profile.profile_picture.save(file_name, ContentFile(picture_response.content), save=False)
                except requests.RequestException:
                    pass

            if locale:
                if locale.startswith('ar'):
                    profile.preferred_language = 'ar'
                else:
                    profile.preferred_language = 'en'

            profile.save()

            # No need to store Google tokens when using ID token flow
            # The ID token is validated directly
            
            refresh = RefreshToken.for_user(user)

            response = Response(
                {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                    'user': UserSerializer(user).data,
                },
                status=status.HTTP_200_OK
            )

            response.set_cookie(
                COOKIE_ACCESS_NAME,
                str(refresh.access_token),
                max_age=COOKIE_MAX_AGE,
                httponly=True,
                secure=settings.DEBUG is False,
                samesite='Lax',
            )
            response.set_cookie(
                COOKIE_REFRESH_NAME,
                str(refresh),
                max_age=COOKIE_MAX_AGE,
                httponly=True,
                secure=settings.DEBUG is False,
                samesite='Lax',
            )

            return response

        except ValueError as e:
            # Token verification failed
            return Response(
                {
                    'detail': 'Failed to verify Google token',
                    'error': str(e),
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except requests.RequestException as e:
            error_detail = str(e)
            error_body = None
            response = getattr(e, "response", None)
            if response is not None:
                try:
                    error_body = response.json()
                except Exception:
                    error_body = response.text
            return Response(
                {
                    'detail': 'Failed to authenticate with Google',
                    'error': error_detail,
                    'google_response': error_body,
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'detail': f'An error occurred: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class OTPRequestView(APIView):
    """
    Request OTP for authentication.
    Very strict rate limiting to prevent OTP spam.
    
    Rate limited: 5 requests/hour per IP
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp = serializer.save()
        
        if not otp.user.is_active:
            otp.delete()
            return Response(
                {'detail': 'user is inactive pls contact support'},
                status=status.HTTP_403_FORBIDDEN
            )

        # DEV: print OTP to console for testing
        print("=" * 50)
        print("OTP generated")
        print(f"User: {otp.user}")
        print(f"Type: {otp.otp_type}")
        print(f"Contact: {otp.phone_number or otp.email}")
        print(f"Code: {otp.otp_code}")
        print(f"Expires at: {otp.expires_at}")
        print("=" * 50)

        # Send OTP via Celery task if flag is enabled and it's a phone number
        if otp.otp_type == 'phone' and otp.phone_number and getattr(settings, "USE_REAL_TWILIO_OTP", False):
            from .tasks import send_otp_via_twilio
            send_otp_via_twilio.delay(otp.phone_number, otp.otp_code)
        if otp.otp_type == 'email' and otp.email:
            from .tasks import send_email_task
            send_email_task.delay(
                subject="Your verification code",
                message=f"Your verification code is: {otp.otp_code}",
                recipient_list=[otp.email],
            )

        return Response(
            {
                'detail': f'OTP sent to {otp.otp_type}',
                'otp_type': otp.otp_type,
                'contact': otp.phone_number or otp.email,
                'expires_in_minutes': 5
            },
            status=status.HTTP_200_OK
        )

class OTPLoginView(APIView):
    """
    Login with OTP verification.
    Very strict rate limiting to prevent brute force OTP guessing.
    
    Rate limited: 5 requests/hour per IP
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = OTPLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp_type = serializer.validated_data['otp_type']
        otp_code = serializer.validated_data['otp_code']
        phone = serializer.validated_data.get('phone_number')
        email = serializer.validated_data.get('email')

        try:
            if otp_type == 'phone':
                otp_record = OTPToken.objects.filter(
                    phone_number=phone, otp_type='phone', is_verified=False
                ).order_by('-created_at').first()
            else:
                otp_record = OTPToken.objects.filter(
                    email=email, otp_type='email', is_verified=False
                ).order_by('-created_at').first()
            if not otp_record:
                return Response({'detail': 'OTP not found.'}, status=status.HTTP_400_BAD_REQUEST)
            if otp_record.is_expired():
                return Response({'detail': 'OTP expired.'}, status=status.HTTP_400_BAD_REQUEST)
            if otp_record.is_attempts_exceeded():
                return Response({'detail': 'Too many attempts.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
            if otp_record.otp_code != otp_code:
                otp_record.attempts += 1
                otp_record.save(update_fields=['attempts'])
                return Response({'detail': 'Invalid OTP.'}, status=status.HTTP_400_BAD_REQUEST)

            otp_record.is_verified = True
            otp_record.verified_at = timezone.now()
            otp_record.save(update_fields=['is_verified', 'verified_at'])

            user = otp_record.user

            if not user.is_active:
                return Response(
                    {'detail': 'user is inactive pls contact support'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Mark user contact as verified
            if otp_type == 'email':
                if not user.is_email_verified:
                    user.is_email_verified = True
                    user.email_verified_at = timezone.now()
                    user.save(update_fields=['is_email_verified', 'email_verified_at'])
            elif otp_type == 'phone':
                if not user.is_phone_verified:
                    user.is_phone_verified = True
                    user.phone_verified_at = timezone.now()
                    user.save(update_fields=['is_phone_verified', 'phone_verified_at'])

            refresh = RefreshToken.for_user(user)
            response = Response(
                {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                    'user': UserSerializer(user).data,
                },
                status=status.HTTP_200_OK
            )
            response.set_cookie(
                COOKIE_ACCESS_NAME,
                str(refresh.access_token),
                max_age=COOKIE_MAX_AGE,
                httponly=True,
                secure=settings.DEBUG is False,
                samesite='Lax',
            )
            response.set_cookie(
                COOKIE_REFRESH_NAME,
                str(refresh),
                max_age=COOKIE_MAX_AGE,
                httponly=True,
                secure=settings.DEBUG is False,
                samesite='Lax',
            )
            
            # Handle referral code if provided
            referral_code = request.data.get('referral_code', '').strip()
            if referral_code:
                try:
                    success, message = apply_referral_code(user, referral_code)
                    response.data['referral'] = {
                        'success': success,
                        'message': message
                    }
                    if success:
                        response.data['detail'] = 'Login successful. Referral code applied and coupons created!'
                    else:
                        response.data['detail'] = 'Login successful but referral code could not be applied.'
                except Exception as e:
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error applying referral code in OTP login: {str(e)}")
                    response.data['referral'] = {
                        'success': False,
                        'message': f'Error applying referral code: {str(e)}'
                    }
            
            return response
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyNewContactView(APIView):
    """
    Verify and update new contact information (email/phone).
    Rate limited to authenticated users.
    
    Rate limited: 50 requests/hour for users
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = VerifyNewContactSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        otp_record = serializer.validated_data['otp_record']
        otp_type = serializer.validated_data['otp_type']
        new_contact = serializer.validated_data.get('email') if otp_type == 'email' else serializer.validated_data.get('phone_number')
        user = request.user

        try:
            # Verify OTP
            otp_record.is_verified = True
            otp_record.verified_at = timezone.now()
            otp_record.save(update_fields=['is_verified', 'verified_at'])

            # Update User Contact
            if otp_type == 'email':
                user.email = new_contact
                user.is_email_verified = True
                user.email_verified_at = timezone.now()
                user.save(update_fields=['email', 'is_email_verified', 'email_verified_at'])
            else:
                user.phone_number = new_contact
                user.is_phone_verified = True
                user.phone_verified_at = timezone.now()
                user.save(update_fields=['phone_number', 'is_phone_verified', 'phone_verified_at'])

            return Response(
                {
                    'detail': f'{otp_type.capitalize()} updated successfully.',
                    'user': UserSerializer(user).data
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
