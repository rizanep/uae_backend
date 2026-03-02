from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MarketingMediaViewSet, CouponViewSet


router = DefaultRouter()
router.register(r"media", MarketingMediaViewSet, basename="marketing-media")
router.register(r"coupons", CouponViewSet, basename="coupons")

urlpatterns = [
    path("", include(router.urls)),
]
