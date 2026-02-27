from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet,
    RefreshView,
    LogoutView,
    GoogleAuthCallbackView,
    OTPRequestView,
    OTPLoginView,
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/refresh/', RefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/google/callback/', GoogleAuthCallbackView.as_view(), name='google_callback'),
    path('auth/otp/request/', OTPRequestView.as_view(), name='otp_request'),
    path('auth/otp/login/', OTPLoginView.as_view(), name='otp_login'),
]
