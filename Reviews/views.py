from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Review
from .serializers import ReviewSerializer

class IsOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj.user == request.user

class ReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet for product reviews.
    Public: List/Retrieve visible reviews.
    Authenticated: Create review, Update/Delete own review.
    Admin: Toggle visibility, Delete any review.
    """
    serializer_class = ReviewSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["product", "user", "rating"]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Review.objects.all()
        return Review.objects.filter(is_visible=True)

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
        Admin only: Hide or show a review.
        """
        review = self.get_object()
        review.is_visible = not review.is_visible
        review.save()
        status_str = "visible" if review.is_visible else "hidden"
        return Response({"message": f"Review is now {status_str}."})
