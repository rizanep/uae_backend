from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend

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
        - Create review
        - Update/delete own review

    Admin:
        - Hide/show reviews
        - Delete any review
    """

    serializer_class = ReviewSerializer
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["product", "user", "rating"]

    def get_queryset(self):
        queryset = Review.objects.select_related(
            "user", "product"
        ).prefetch_related("images")

        if self.request.user.is_staff:
            return queryset

        return queryset.filter(is_visible=True)

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]

        if self.action == "create":
            return [permissions.IsAuthenticated()]

        if self.action in ["update", "partial_update", "destroy"]:
            return [IsOwnerOrAdmin()]

        if self.action == "toggle_visibility":
            return [permissions.IsAdminUser()]

        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def toggle_visibility(self, request, pk=None):
        """
        Admin can hide/show a review.
        """
        review = self.get_object()
        review.is_visible = not review.is_visible
        review.save()

        status_text = "visible" if review.is_visible else "hidden"

        return Response({
            "message": f"Review is now {status_text}"
        })