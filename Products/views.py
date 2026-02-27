from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters import rest_framework as django_filters
from django.db.models import Avg, Count, Q
from django.core.cache import cache
from django.conf import settings
import hashlib
from .models import Category, Product, ProductImage, ProductVideo
from .serializers import (
    CategorySerializer,
    ProductSerializer,
    ProductImageSerializer,
    ProductVideoSerializer,
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
    filterset_fields = ["parent"]

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
        fields = ["category", "category_slug", "is_available", "min_price", "max_price"]

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(deleted_at__isnull=True, is_available=True)
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [django_filters.DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ["name", "description", "sku"]
    ordering_fields = ["price", "created_at"]

    def get_queryset(self):
        def with_related(qs):
            return (
                qs.select_related("category")
                .prefetch_related("images", "videos")
                .annotate(
                    average_rating=Avg("reviews__rating", filter=Q(reviews__is_visible=True)),
                    total_reviews=Count("reviews", filter=Q(reviews__is_visible=True)),
                )
            )

        if self.request.user and self.request.user.is_staff:
            return with_related(Product.objects.filter(deleted_at__isnull=True))

        return with_related(super().get_queryset())

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

    @action(detail=True, methods=["get"])
    def related(self, request, pk=None):
        """
        Returns related products in the same category.
        """
        product = self.get_object()
        if request.user and request.user.is_staff:
            return super().related(request, pk=pk)
        cache_key = _build_cache_key("catalog", f"products:related:{pk}", request)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)
        related_products = self.get_queryset().filter(category=product.category).exclude(id=product.id)[:4]
        serializer = self.get_serializer(related_products, many=True)
        data = serializer.data
        cache.set(cache_key, data, getattr(settings, "CACHE_DEFAULT_TIMEOUT", 300))
        return Response(data)

    @action(detail=False, methods=["get"])
    def new_arrivals(self, request):
        """
        Returns the latest 8 products.
        """
        if request.user and request.user.is_staff:
            return super().new_arrivals(request)
        cache_key = _build_cache_key("catalog", "products:new_arrivals", request)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)
        new_products = self.get_queryset().order_by("-created_at")[:8]
        serializer = self.get_serializer(new_products, many=True)
        data = serializer.data
        cache.set(cache_key, data, getattr(settings, "CACHE_DEFAULT_TIMEOUT", 300))
        return Response(data)


class ProductImageViewSet(viewsets.ModelViewSet):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_fields = ["product", "is_feature"]

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


class ProductVideoViewSet(viewsets.ModelViewSet):
    queryset = ProductVideo.objects.all()
    serializer_class = ProductVideoSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_fields = ["product"]

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
