from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet,
    LoginView,
    RefreshView,
    LogoutView,
    GoogleAuthCallbackView,
    OTPRequestView,
    OTPLoginView,
    VerifyNewContactView
)
from .user_address_viewset import UserAddressViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')
router.register(r'addresses', UserAddressViewSet, basename='user-address')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/login/', LoginView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', RefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/google/callback/', GoogleAuthCallbackView.as_view(), name='google_callback'),
    path('auth/otp/request/', OTPRequestView.as_view(), name='otp_request'),
    path('auth/otp/login/', OTPLoginView.as_view(), name='otp_login'),
    path('auth/otp/verify-update/', VerifyNewContactView.as_view(), name='otp_verify_update'),
]
