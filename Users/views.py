from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils import timezone
from django.conf import settings
from django.core.files.base import ContentFile
import json
import requests

from .models import User, GoogleOAuthToken, OTPToken, UserProfile, UserAddress
from .serializers import (
    UserSerializer, UserCreateSerializer, UserUpdateSerializer,
    UserAdminSerializer, CustomTokenObtainPairSerializer,
    ChangePasswordSerializer, GoogleOAuthSerializer,
    OTPRequestSerializer, OTPLoginSerializer
)
from .permissions import IsOwnerOrAdmin, IsAdmin

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
            return User.objects.filter(deleted_at__isnull=True).select_related("profile")
        return User.objects.filter(id=user.id, deleted_at__isnull=True).select_related("profile")
    
    def create(self, request, *args, **kwargs):
        """Create a new user (registration)"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED
        )
    
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
    
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """Change user password"""
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
        
        if role not in ['admin', 'user']:
            return Response(
                {'detail': 'Invalid role. Must be "admin" or "user".'},
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
        
        if include_deleted:
            queryset = User.objects.all()
        else:
            queryset = User.objects.filter(deleted_at__isnull=True)
        
        serializer = UserAdminSerializer(queryset, many=True)
        return Response(serializer.data)
    
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


class LoginView(TokenObtainPairView):
    """
    Login view with cookie support
    - Issues JWT tokens
    - Sets HttpOnly cookies for tokens
    - Updates last login time
    """
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
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


class GoogleAuthCallbackView(APIView):
    """
    Google OAuth callback handler
    - Exchange authorization code for tokens
    - Create/update user
    - Issue JWT tokens
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

    def _handle_code(self, code):
        try:
            token_url = 'https://oauth2.googleapis.com/token'

            token_data = {
                'code': code,
                'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
                'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
                'redirect_uri': settings.GOOGLE_OAUTH_REDIRECT_URI,
                'grant_type': 'authorization_code',
            }
            print("ldsf",token_data)
            token_response = requests.post(token_url, data=token_data)
            token_response.raise_for_status()
            tokens = token_response.json()

            access_token = tokens['access_token']
            userinfo_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
            userinfo_response = requests.get(
                userinfo_url,
                headers={'Authorization': f'Bearer {access_token}'}
            )
            userinfo_response.raise_for_status()
            userinfo = userinfo_response.json()

            google_id = userinfo['id']
            email = userinfo['email']
            first_name = userinfo.get('given_name', '')
            last_name = userinfo.get('family_name', '')
            picture_url = userinfo.get('picture')
            locale = userinfo.get('locale')

            user, created = User.objects.get_or_create(
                google_id=google_id,
                defaults={
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'google_email': email,
                    'is_email_verified': True,
                }
            )

            if not created:
                user.email = email
                user.first_name = first_name
                user.last_name = last_name
                user.google_email = email
                user.save()

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

            expires_in = tokens.get('expires_in', 3600)
            expires_at = timezone.now() + timezone.timedelta(seconds=expires_in)

            GoogleOAuthToken.objects.update_or_create(
                user=user,
                defaults={
                    'access_token': access_token,
                    'refresh_token': tokens.get('refresh_token', ''),
                    'expires_at': expires_at,
                }
            )

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
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp = serializer.save()
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
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
