from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MarketingMediaViewSet, 
    CouponViewSet,
    AdminCouponViewSet,
    RewardConfigurationViewSet
)


router = DefaultRouter()
router.register(r"media", MarketingMediaViewSet, basename="marketing-media")
router.register(r"coupons", CouponViewSet, basename="coupons")
router.register(r"admin/coupons", AdminCouponViewSet, basename="admin-coupons")
router.register(r"admin/rewards", RewardConfigurationViewSet, basename="admin-rewards")

urlpatterns = [
    path("", include(router.urls)),
]
