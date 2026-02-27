from django.utils import timezone
from django.db import models
from rest_framework import viewsets, permissions
from django_filters import rest_framework as django_filters
from .models import MarketingMedia
from .serializers import MarketingMediaSerializer


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)


class MarketingMediaFilter(django_filters.FilterSet):
    class Meta:
        model = MarketingMedia
        fields = ["key", "position", "is_active"]


class MarketingMediaViewSet(viewsets.ModelViewSet):
    serializer_class = MarketingMediaSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_class = MarketingMediaFilter

    def get_queryset(self):
        qs = MarketingMedia.objects.filter(deleted_at__isnull=True)
        user = self.request.user
        if not user or not user.is_staff:
            now = timezone.now()
            qs = qs.filter(is_active=True).filter(
                models.Q(start_at__isnull=True) | models.Q(start_at__lte=now),
                models.Q(end_at__isnull=True) | models.Q(end_at__gte=now),
            )
        return qs.order_by("sort_order", "-created_at")
