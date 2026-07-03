from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters import rest_framework as django_filters
from django.db import models
from django.db.models import Avg, Count, Q
from django.core.cache import cache
from django.conf import settings
import hashlib
from .models import Category, Product, ProductImage, ProductVideo, ProductDeliveryTier, ProductDiscountTier, ProductNotification, ProductPreparationSpecification, ProductUnit
from .serializers import (
    CategorySerializer,
    ProductSerializer,
    ProductImageSerializer,
    ProductVideoSerializer,
    ProductDeliveryTierSerializer,
    ProductDiscountTierSerializer,
    ProductPreparationSpecificationSerializer,
    ProductPreparationSpecificationAdminSerializer,
    ProductNotificationSerializer,
    ProductUnitSerializer,
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
    search_fields = ["name", "name_arabic", "name_chinese", "description"]
    filterset_fields = [
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
        "name",
        "name_arabic",
        "name_chinese",
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


class ProductUnitViewSet(viewsets.ModelViewSet):
    queryset = ProductUnit.objects.all()
    serializer_class = ProductUnitSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [filters.SearchFilter, django_filters.DjangoFilterBackend, filters.OrderingFilter]
    search_fields = ["name"]
    filterset_fields = ["is_active"]
    ordering_fields = ["sort_order", "name", "created_at"]



class ProductFilter(django_filters.FilterSet):

    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")

    category_slug = django_filters.CharFilter(field_name="category__slug")
    category_name = django_filters.CharFilter(field_name="category__name")
    
    available_emirates = django_filters.CharFilter(method="filter_emirates")

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
        }
    def filter_emirates(self, queryset, name, value):
    	emirates = value.split(",")
    	return queryset.filter(available_emirates__overlap=emirates)

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(deleted_at__isnull=True, is_available=True).select_related('category', 'unit_option').prefetch_related('images', 'videos', 'discount_tiers', 'delivery_tiers').order_by('sortorder', 'id')
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, django_filters.DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ["name", "description", "sku"]
    ordering_fields = ["sortorder", "price", "created_at", "stock"]

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

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAdminUser])
    def products_count(self, request):
        """
        Get a summary of product counts by status.
        Returns: total products, active, out of stock, low stock.
        """
        product_counts = Product.objects.filter(deleted_at__isnull=True).aggregate(
            total_products=Count('id'),
            active=Count('id', filter=Q(is_available=True, stock__gt=0)),
            out_of_stock=Count('id', filter=Q(stock=0)),
            low_stock=Count('id', filter=Q(stock__gt=0, stock__lte=20)),
        )

        return Response({
            "total_products": product_counts['total_products'],
            "active": product_counts['active'],
            "out_of_stock": product_counts['out_of_stock'],
            "low_stock": product_counts['low_stock'],
        })

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def notify_stock(self, request, pk=None):
        """
        Allow authenticated users to request notification when product comes back in stock.
        Only one notification per user per product.
        """
        try:
            product = self.get_object()
        except Product.DoesNotExist:
            return Response({"detail": "Product not found."}, status=404)

        if product.stock > 0:
            return Response({"detail": "Product is currently in stock."}, status=400)

        # Try to get or create the notification
        notification, created = ProductNotification.objects.get_or_create(
            user=request.user,
            product=product,
            defaults={'notified': False}
        )

        # Always return success, whether created or already existed
        return Response({
            "detail": "You will be notified when this product comes back in stock.",
            "created": created
        })

    def perform_destroy(self, instance):
        result = super().perform_destroy(instance)
        _bump_cache_version("catalog")
        return result

    @action(detail=True, methods=["get", "post"], url_path="preparation-specs",
            permission_classes=[IsAdminOrReadOnly])
    def preparation_specs(self, request, pk=None):
        """
        GET  /api/products/products/{id}/preparation-specs/  — list all specs for a product (admin sees all; customers see active only)
        POST /api/products/products/{id}/preparation-specs/  — create a new spec (admin only)
        """
        product = self.get_object()
        if request.method == "GET":
            qs = product.preparation_specifications.all()
            if not (request.user and request.user.is_staff):
                qs = qs.filter(is_active=True)
            qs = qs.order_by("sort_order", "id")
            serializer = ProductPreparationSpecificationAdminSerializer(qs, many=True, context={"request": request})
            return Response(serializer.data)
        # POST — admin only
        if not (request.user and request.user.is_staff):
            return Response({"detail": "Permission denied."}, status=403)
        data = request.data.copy()
        data["product"] = product.pk
        serializer = ProductPreparationSpecificationAdminSerializer(data=data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        _bump_cache_version("catalog")
        return Response(serializer.data, status=201)

    @action(detail=True, methods=["get"], url_path="notifying-users",
            permission_classes=[permissions.IsAdminUser])
    def notifying_users(self, request, pk=None):
        """
        Get list of users who are notified for this product (admin only).
        Shows count of notifying users and their details.
        Only displays users with pending notifications (notified=False).
        """
        product = self.get_object()
        
        # Get pending notifications (notified=False)
        pending_notifications = ProductNotification.objects.filter(
            product=product,
            notified=False
        ).select_related('user').order_by('-created_at')
        
        # Get count
        pending_count = pending_notifications.count()
        
        serializer = ProductNotificationSerializer(pending_notifications, many=True)
        
        return Response({
            "product_id": product.id,
            "product_name": product.name,
            "pending_notifications_count": pending_count,
            "notifying_users": serializer.data
        })


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


class ProductPreparationSpecificationViewSet(viewsets.ModelViewSet):
    """
    CRUD endpoint for preparation specifications.
    Admin: full create/read/update/delete.
    Customers: read-only (active specs only via product detail).

    Endpoints:
      GET    /api/products/preparation-specs/?product={id}  — list specs (filter by product)
      POST   /api/products/preparation-specs/               — create spec
      GET    /api/products/preparation-specs/{id}/          — retrieve spec
      PATCH  /api/products/preparation-specs/{id}/          — update spec
      DELETE /api/products/preparation-specs/{id}/          — delete spec
    """
    queryset = ProductPreparationSpecification.objects.select_related("product").order_by("sort_order", "id")
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_fields = ["product", "is_active"]

    def get_serializer_class(self):
        return ProductPreparationSpecificationAdminSerializer

    def perform_create(self, serializer):
        serializer.save()
        _bump_cache_version("catalog")

    def perform_update(self, serializer):
        serializer.save()
        _bump_cache_version("catalog")

    def perform_destroy(self, instance):
        instance.delete()
        _bump_cache_version("catalog")
