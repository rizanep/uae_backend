from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters import rest_framework as django_filters
from django.db import models
from django.db.models import Avg, Count, Q
from django.core.cache import cache
from django.conf import settings
import hashlib
from .models import Category, Product, ProductImage, ProductVideo, ProductDeliveryTier, ProductDiscountTier
from .serializers import (
    CategorySerializer,
    ProductSerializer,
    ProductImageSerializer,
    ProductVideoSerializer,
    ProductDeliveryTierSerializer,
    ProductDiscountTierSerializer,
)

def _get_cache_version(group):
    return cache.get(f"cv:{group}", 1)

def _bump_cache_version(group):
    key = f"cv:{group}"
    current = cache.get(key, 1)
    cache.set(key, current + 1, None)

def _build_cache_key(group, prefix, request):
    version = _get_cache_version(group)
    digest = hashlib.md5(request.get_full_path().encode("utf-8")).hexdigest()
    return f"{prefix}:v{version}:{digest}"

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow admins to edit objects.
    Read-only permissions are allowed for any request.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.filter(deleted_at__isnull=True)
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, django_filters.DjangoFilterBackend]
    search_fields = ["name", "description"]
    filterset_fields = [
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
        "name",
        "slug",
        "description",
        "parent",
    ]

    def list(self, request, *args, **kwargs):
        if request.user and request.user.is_staff:
            return super().list(request, *args, **kwargs)
        cache_key = _build_cache_key("catalog", "categories:list", request)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)
        response = super().list(request, *args, **kwargs)
        if response.status_code == 200:
            cache.set(cache_key, response.data, getattr(settings, "CACHE_DEFAULT_TIMEOUT", 300))
        return response

    def retrieve(self, request, *args, **kwargs):
        if request.user and request.user.is_staff:
            return super().retrieve(request, *args, **kwargs)
        cache_key = _build_cache_key("catalog", "categories:detail", request)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)
        response = super().retrieve(request, *args, **kwargs)
        if response.status_code == 200:
            cache.set(cache_key, response.data, getattr(settings, "CACHE_DEFAULT_TIMEOUT", 300))
        return response

    def perform_create(self, serializer):
        result = super().perform_create(serializer)
        _bump_cache_version("catalog")
        return result

    def perform_update(self, serializer):
        result = super().perform_update(serializer)
        _bump_cache_version("catalog")
        return result

    def perform_destroy(self, instance):
        result = super().perform_destroy(instance)
        _bump_cache_version("catalog")
        return result


class ProductFilter(django_filters.FilterSet):
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr='lte')
    category_slug = django_filters.CharFilter(field_name="category__slug")

    class Meta:
        model = Product
        fields = "__all__"
        filter_overrides = {
            models.ImageField: {
                "filter_class": django_filters.CharFilter,
            },
            models.FileField: {
                "filter_class": django_filters.CharFilter,
            },
            models.JSONField: {
                "filter_class": django_filters.CharFilter,
            },
        }

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(deleted_at__isnull=True, is_available=True).select_related('category').prefetch_related('images', 'videos', 'discount_tiers', 'delivery_tiers')
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, django_filters.DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ["name", "description", "sku"]
    ordering_fields = ["price", "created_at", "stock"]

    def list(self, request, *args, **kwargs):
        if request.user and request.user.is_staff:
            return super().list(request, *args, **kwargs)
        cache_key = _build_cache_key("catalog", "products:list", request)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)
        response = super().list(request, *args, **kwargs)
        if response.status_code == 200:
            cache.set(cache_key, response.data, getattr(settings, "CACHE_DEFAULT_TIMEOUT", 300))
        return response

    def retrieve(self, request, *args, **kwargs):
        if request.user and request.user.is_staff:
            return super().retrieve(request, *args, **kwargs)
        cache_key = _build_cache_key("catalog", "products:detail", request)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)
        response = super().retrieve(request, *args, **kwargs)
        if response.status_code == 200:
            cache.set(cache_key, response.data, getattr(settings, "CACHE_DEFAULT_TIMEOUT", 300))
        return response

    def perform_create(self, serializer):
        result = super().perform_create(serializer)
        _bump_cache_version("catalog")
        return result

    def perform_update(self, serializer):
        result = super().perform_update(serializer)
        _bump_cache_version("catalog")
        return result

    def perform_destroy(self, instance):
        result = super().perform_destroy(instance)
        _bump_cache_version("catalog")
        return result

class ProductImageViewSet(viewsets.ModelViewSet):
    queryset = ProductImage.objects.select_related('product')
    serializer_class = ProductImageSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_fields = ["id", "product", "is_feature", "created_at"]

class ProductVideoViewSet(viewsets.ModelViewSet):
    queryset = ProductVideo.objects.select_related('product')
    serializer_class = ProductVideoSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_fields = ["id", "product", "video_url", "title", "created_at"]

class ProductDeliveryTierViewSet(viewsets.ModelViewSet):
    """
    API for managing product delivery tiers.
    Admins can add/edit/delete tiers.
    """
    queryset = ProductDeliveryTier.objects.select_related('product')
    serializer_class = ProductDeliveryTierSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_fields = "__all__"

class ProductDiscountTierViewSet(viewsets.ModelViewSet):
    """
    API for managing product discount tiers.
    Admins can add/edit/delete tiers.
    """
    queryset = ProductDiscountTier.objects.select_related('product')
    serializer_class = ProductDiscountTierSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_fields = "__all__"
