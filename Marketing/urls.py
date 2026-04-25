from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MarketingMediaViewSet, 
    CouponViewSet,
    AdminCouponViewSet,
    RewardConfigurationViewSet,
    PromotionalContentViewSet
)


router = DefaultRouter()
router.register(r"media", MarketingMediaViewSet, basename="marketing-media")
router.register(r"coupons", CouponViewSet, basename="coupons")
router.register(r"admin/coupons", AdminCouponViewSet, basename="admin-coupons")
router.register(r"promotional", PromotionalContentViewSet, basename="promotional")

# Custom URL for reward configuration (singleton)
urlpatterns = [
    path("admin/rewards/", RewardConfigurationViewSet.as_view({
        'get': 'list',
        'patch': 'list',
        'put': 'update',
        'post': 'create'
    }), name='admin-rewards'),
    path("", include(router.urls)),
]
