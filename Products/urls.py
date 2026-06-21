from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet,
    ProductUnitViewSet,
    ProductViewSet,
    ProductImageViewSet,
    ProductVideoViewSet,
    ProductDeliveryTierViewSet,
    ProductDiscountTierViewSet,
    ProductPreparationSpecificationViewSet,
)

router = DefaultRouter()
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"units", ProductUnitViewSet, basename="product-unit")
router.register(r"products", ProductViewSet, basename="product")
router.register(r"product-images", ProductImageViewSet, basename="product-image")
router.register(r"product-videos", ProductVideoViewSet, basename="product-video")
router.register(r"delivery-tiers", ProductDeliveryTierViewSet, basename="delivery-tier")
router.register(r"discount-tiers", ProductDiscountTierViewSet, basename="discount-tier")
router.register(r"preparation-specs", ProductPreparationSpecificationViewSet, basename="preparation-spec")

urlpatterns = [
    path("", include(router.urls)),
]
