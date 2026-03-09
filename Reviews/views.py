from rest_framework import viewsets, permissions
from rest_framework.decorators import action, throttle_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from core.throttling import UserReviewThrottle, AnonGeneralThrottle

from .models import Review
from .serializers import ReviewSerializer


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Allows access only to review owner or admin.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj.user == request.user


class ReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet for product reviews.

    Public:
        - List reviews
        - Retrieve review

    Authenticated users:
        - Create review (rate limited: 20/hour)
        - Update/delete own review (rate limited: 20/hour)

    Admin:
        - Hide/show reviews
        - Delete any review
    """

    serializer_class = ReviewSerializer
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["product", "user", "rating"]

    def get_throttles(self):
        """Apply stricter throttling for write operations to prevent review spam"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [UserReviewThrottle(), AnonGeneralThrottle()]
        # Default throttling for list/retrieve
        return super().get_throttles()

    def get_queryset(self):
        queryset = Review.objects.select_related(
            "user", "product"
        ).prefetch_related("images", "product__category")

        if self.request.user.is_staff:
            return queryset

        return queryset.filter(is_visible=True)

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]

        if self.action == "create":
            return [permissions.AllowAny()]

        if self.action in ["update", "partial_update", "destroy"]:
            return [IsOwnerOrAdmin()]

        if self.action == "toggle_visibility":
            return [permissions.IsAdminUser()]

        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def my_review(self, request):
        """
        Get the current user's review for a specific product.
        Useful for checking if user already reviewed a product before creating a new one.
        """
        product_id = request.query_params.get('product_id')
        
        if not product_id:
            return Response(
                {"error": "product_id parameter is required"}, 
                status=400
            )
        
        try:
            review = Review.objects.get(
                user=request.user, 
                product_id=product_id
            )
            serializer = self.get_serializer(review)
            return Response(serializer.data)
        except Review.DoesNotExist:
            return Response(
                {"detail": "No review found for this product"}, 
                status=404
            )

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def toggle_visibility(self, request, pk=None):
        """
        Admin action to toggle review visibility.
        Hidden reviews are not shown to regular users.
        """
        review = self.get_object()
        review.is_visible = not review.is_visible
        review.save()
        
        return Response({
            "id": review.id,
            "is_visible": review.is_visible,
            "message": f"Review is now {'visible' if review.is_visible else 'hidden'}"
        })