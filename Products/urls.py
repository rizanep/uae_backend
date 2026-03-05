from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet, 
    ProductViewSet, 
    ProductImageViewSet, 
    ProductVideoViewSet, 
    ProductDeliveryTierViewSet, 
    ProductDiscountTierViewSet
)

router = DefaultRouter()
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"products", ProductViewSet, basename="product")
router.register(r"product-images", ProductImageViewSet, basename="product-image")
router.register(r"product-videos", ProductVideoViewSet, basename="product-video")
router.register(r"delivery-tiers", ProductDeliveryTierViewSet, basename="delivery-tier")
router.register(r"discount-tiers", ProductDiscountTierViewSet, basename="discount-tier")

urlpatterns = [
    path("", include(router.urls)),
]
