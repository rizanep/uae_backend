from django.utils import timezone
from django.db import models
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters import rest_framework as django_filters
from .models import MarketingMedia, Coupon
from .serializers import MarketingMediaSerializer, CouponSerializer, ApplyReferralSerializer
from .services import grant_referral_rewards
from Users.models import User


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


class CouponViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CouponSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Users see their own assigned coupons
        user = self.request.user
        qs = Coupon.objects.filter(assigned_user=user, deleted_at__isnull=True)
        return qs.order_by("-created_at")

    @action(detail=False, methods=['post'], serializer_class=ApplyReferralSerializer)
    def apply_referral(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        referral_code = serializer.validated_data['referral_code']
        
        user = request.user
        
        # Check if already referred
        if user.referred_by:
             return Response({"detail": "You have already been referred."}, status=status.HTTP_400_BAD_REQUEST)
             
        if user.referral_code == referral_code:
             return Response({"detail": "You cannot refer yourself."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            referrer = User.objects.get(referral_code=referral_code)
        except User.DoesNotExist:
            return Response({"detail": "Invalid referral code."}, status=status.HTTP_404_NOT_FOUND)
            
        # Set referrer
        user.referred_by = referrer
        user.save(update_fields=['referred_by'])
        
        # Grant rewards
        if not user.referral_reward_claimed:
            grant_referral_rewards(referrer, user)
            user.referral_reward_claimed = True
            user.save(update_fields=['referral_reward_claimed'])
            
        return Response({"detail": "Referral code applied successfully. Coupons granted!"}, status=status.HTTP_200_OK)
