from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters import rest_framework as django_filters
from .models import Category, Product, ProductImage, ProductVideo
from .serializers import (
    CategorySerializer,
    ProductSerializer,
    ProductImageSerializer,
    ProductVideoSerializer,
)

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
        queryset = super().get_queryset()
        # Optimization: prefetch images and reviews for list view
        queryset = queryset.prefetch_related("images", "reviews")
        if self.request.user and self.request.user.is_staff:
            return Product.objects.filter(deleted_at__isnull=True).prefetch_related("images", "reviews")
        return queryset

    @action(detail=True, methods=["get"])
    def related(self, request, pk=None):
        """
        Returns related products in the same category.
        """
        product = self.get_object()
        related_products = Product.objects.filter(
            category=product.category, 
            is_available=True,
            deleted_at__isnull=True
        ).exclude(id=product.id)[:4]
        serializer = self.get_serializer(related_products, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def new_arrivals(self, request):
        """
        Returns the latest 8 products.
        """
        new_products = self.get_queryset().order_by("-created_at")[:8]
        serializer = self.get_serializer(new_products, many=True)
        return Response(serializer.data)


class ProductImageViewSet(viewsets.ModelViewSet):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_fields = ["product", "is_feature"]


class ProductVideoViewSet(viewsets.ModelViewSet):
    queryset = ProductVideo.objects.all()
    serializer_class = ProductVideoSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_fields = ["product"]
