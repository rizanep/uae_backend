from django.utils import timezone
from django.db import models
from django.core.cache import cache
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters import rest_framework as django_filters
from .models import MarketingMedia, Coupon, RewardConfiguration
from .serializers import (
    MarketingMediaSerializer, 
    CouponSerializer, 
    ApplyReferralSerializer,
    AdminCouponSerializer,
    RewardConfigurationSerializer
)
from .services import grant_referral_rewards
from Users.models import User
from Orders.models import DeliveryChargeConfig, DeliveryTimeSlot, DeliverySlotOverride
from django.conf import settings
import datetime
import pytz

# UAE timezone
UAE_TZ = pytz.timezone('Asia/Dubai')

PROMOTIONAL_LANGUAGES = ['en', 'ar', 'zh']

PROMOTIONAL_TEMPLATES = {
    'free_delivery': {
        'en': 'Purchase for {amount} AED or above for free delivery',
        'ar': 'اشتري بقيمة {amount} درهم أو أكثر للحصول على توصيل مجاني',
        'zh': '购买满 {amount} AED 或以上可享免运费',
    },
    'free_delivery_all': {
        'en': 'Free delivery on all orders',
        'ar': 'التوصيل مجاني لجميع الطلبات',
        'zh': '全场订单免运费',
    },
    'delivery_time': {
        'en': 'Purchase before {cutoff} to get delivery between {start} - {end}',
        'ar': 'اشترِ قبل {cutoff} للحصول على توصيل بين {start} - {end}',
        'zh': '请在 {cutoff} 前下单，配送时间为 {start} - {end}',
    },
    'delivery_time_tomorrow': {
        'en': 'Order now for delivery tomorrow between {start} - {end}',
        'ar': 'اطلب الآن ليتم التوصيل غداً بين {start} - {end}',
        'zh': '立即下单，明天 {start} - {end} 送达',
    },
    'delivery_time_fallback': {
        'en': 'Fast delivery available - order now!',
        'ar': 'التوصيل السريع متاح - اطلب الآن!',
        'zh': '快速配送可用 - 立即下单!',
    },
}


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)


class MarketingMediaFilter(django_filters.FilterSet):
    class Meta:
        model = MarketingMedia
        fields = "__all__"
        filter_overrides = {
            models.ImageField: {
                "filter_class": django_filters.CharFilter,
            },
            models.FileField: {
                "filter_class": django_filters.CharFilter,
            },
        }


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

    def list(self, request, *args, **kwargs):
        user = request.user
        is_staff = user and user.is_staff
        
        # Determine cache key based on user role
        cache_key = "marketing_media_list_staff" if is_staff else "marketing_media_list_public"
        
        # Check cache
        cached_data = cache.get(cache_key)
        if cached_data is not None:
             return Response(cached_data)
             
        # Generate response
        response = super().list(request, *args, **kwargs)
        
        # Set cache (15 minutes = 900 seconds)
        cache.set(cache_key, response.data, timeout=900)
        
        return response


class CouponViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CouponSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_fields = "__all__"

    def get_queryset(self):
        # Users see their own assigned coupons
        user = self.request.user
        qs = Coupon.objects.filter(assigned_user=user, deleted_at__isnull=True).select_related('assigned_user').order_by("-created_at")
        return qs

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


class AdminCouponViewSet(viewsets.ModelViewSet):
    """
    Admin-only ViewSet for managing all coupons.
    Allows admins to:
    - View all coupons (including global and user-specific)
    - Create new coupons
    - Update coupon details
    - Delete/soft-delete coupons
    - Filter by various fields
    """
    serializer_class = AdminCouponSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_fields = [
        'is_active',
        'discount_type',
        'is_referral_reward',
        'is_first_order_reward',
        'assigned_user',
        'valid_from',
        'valid_to',
    ]
    search_fields = ['code', 'description', 'assigned_user__email', 'assigned_user__phone_number']
    ordering_fields = ['created_at', 'updated_at', 'discount_value', 'used_count']
    ordering = ['-created_at']

    def get_queryset(self):
        # Admins see all coupons including soft-deleted ones
        return Coupon.objects.select_related('assigned_user').order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()

    @action(detail=True, methods=['post'])
    def soft_delete(self, request, pk=None):
        """Soft delete a coupon."""
        coupon = self.get_object()
        coupon.soft_delete()
        return Response({"detail": "Coupon soft deleted successfully."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Restore a soft-deleted coupon."""
        coupon = self.get_object()
        coupon.restore()
        return Response({"detail": "Coupon restored successfully."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a coupon."""
        coupon = self.get_object()
        coupon.is_active = False
        coupon.save(update_fields=['is_active'])
        return Response({"detail": "Coupon deactivated successfully.", "is_active": coupon.is_active}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a coupon."""
        coupon = self.get_object()
        coupon.is_active = True
        coupon.save(update_fields=['is_active'])
        return Response({"detail": "Coupon activated successfully.", "is_active": coupon.is_active}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get coupon statistics and usage insights."""
        coupons = self.get_queryset()
        
        total_coupons = coupons.count()
        active_coupons = coupons.filter(is_active=True, deleted_at__isnull=True).count()
        referral_coupons = coupons.filter(is_referral_reward=True).count()
        first_order_coupons = coupons.filter(is_first_order_reward=True).count()
        
        total_redeemed = coupons.aggregate(models.Sum('used_count'))['used_count__sum'] or 0
        
        return Response({
            "total_coupons": total_coupons,
            "active_coupons": active_coupons,
            "referral_coupons": referral_coupons,
            "first_order_coupons": first_order_coupons,
            "total_redeemed": total_redeemed,
        }, status=status.HTTP_200_OK)


class RewardConfigurationViewSet(viewsets.ModelViewSet):
    """
    Admin-only ViewSet for managing reward configuration and scales.
    This is a singleton resource - there's only one configuration object.
    
    Allows admins to:
    - View current reward configuration
    - Update reward scales (referral %, first order %, validity periods, etc.)
    - Enable/disable reward programs
    """
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    queryset = RewardConfiguration.objects.all()
    serializer_class = RewardConfigurationSerializer

    def get_allowed_methods(self):
        """
        Return allowed methods. For singleton resources, allow PATCH on list endpoint.
        """
        if getattr(self, 'action', None) == 'list':
            return ['GET', 'POST', 'PUT', 'PATCH', 'HEAD', 'OPTIONS']
        return super().get_allowed_methods()

    def list(self, request):
        """Get or update the reward configuration."""
        if request.method == 'PATCH':
            return self.partial_update(request, pk=None)
        
        config = RewardConfiguration.get_config()
        serializer = RewardConfigurationSerializer(config)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        """Create or update the singleton reward configuration."""
        config = RewardConfiguration.get_config()
        serializer = RewardConfigurationSerializer(config, data=request.data)
        if serializer.is_valid():
            serializer.validated_data['updated_by'] = request.user
            serializer.save()
            return Response(
                {
                    "detail": "Reward configuration saved successfully.",
                    "config": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        """Get specific reward configuration (always returns the singleton)."""
        config = RewardConfiguration.get_config()
        serializer = RewardConfigurationSerializer(config)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, pk=None):
        """Update the reward configuration."""
        config = RewardConfiguration.get_config()
        serializer = RewardConfigurationSerializer(config, data=request.data, partial=False)
        
        if serializer.is_valid():
            serializer.validated_data['updated_by'] = request.user
            serializer.save()
            return Response(
                {
                    "detail": "Reward configuration updated successfully.",
                    "config": serializer.data
                },
                status=status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        """Partially update the reward configuration (PATCH)."""
        config = RewardConfiguration.get_config()
        serializer = RewardConfigurationSerializer(config, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.validated_data['updated_by'] = request.user
            serializer.save()
            return Response(
                {
                    "detail": "Reward configuration updated successfully.",
                    "config": serializer.data
                },
                status=status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def reset_to_defaults(self, request):
        """Reset reward configuration to default values."""
        config = RewardConfiguration.get_config()
        
        # Reset to defaults
        config.first_order_discount_type = 'percentage'
        config.first_order_discount_value = 10.00
        config.first_order_min_amount = 50.00
        config.first_order_validity_days = 30
        
        config.referral_discount_type = 'percentage'
        config.referral_discount_value = 15.00
        config.referral_min_amount = 100.00
        config.referral_validity_days = 60
        config.referral_usage_limit = 1
        
        config.referrer_discount_value = 15.00
        config.referrer_validity_days = 60
        
        config.max_discount_percentage = None
        config.is_referral_active = True
        config.is_first_order_active = True
        config.updated_by = request.user
        
        config.save()
        
        serializer = RewardConfigurationSerializer(config)
        return Response(
            {
                "detail": "Reward configuration reset to defaults.",
                "config": serializer.data
            },
            status=status.HTTP_200_OK
        )


class PromotionalContentViewSet(viewsets.ViewSet):
    """
    ViewSet for promotional content like delivery offers and time slots.
    Provides dynamic promotional text based on current delivery settings and time.
    """
    permission_classes = [permissions.AllowAny]  # Public endpoint

    @action(detail=False, methods=['get'])
    def delivery_offers(self, request):
        """
        Returns promotional text for delivery offers.
        Includes free delivery threshold and next available delivery time slot.
        """
        # Get delivery charge configuration
        delivery_config = DeliveryChargeConfig.get_config()

        # Get current time in UAE timezone
        now_uae = timezone.now().astimezone(UAE_TZ)
        current_time = now_uae.time()

        # Get available delivery slots for today
        today = now_uae.date()
        all_active_slots = DeliveryTimeSlot.objects.filter(is_active=True).order_by('sort_order', 'start_time')

        # Get overrides for today
        overrides = {
            o.slot_id: o.is_active
            for o in DeliverySlotOverride.objects.filter(date=today)
        }

        # Find the next available slot
        next_slot = None
        for slot in all_active_slots:
            # Check per-date override
            if slot.id in overrides:
                if not overrides[slot.id]:
                    continue  # override says inactive

            # Check cutoff time for today
            if current_time < slot.cutoff_time:
                next_slot = slot
                break

        # Build promotional texts for all supported languages
        promotional_texts = {lang: {} for lang in PROMOTIONAL_LANGUAGES}

        for lang in PROMOTIONAL_LANGUAGES:
            if delivery_config.is_active and delivery_config.min_free_shipping_amount > 0:
                promotional_texts[lang]["free_delivery"] = PROMOTIONAL_TEMPLATES["free_delivery"][lang].format(
                    amount=delivery_config.min_free_shipping_amount
                )
            else:
                promotional_texts[lang]["free_delivery"] = PROMOTIONAL_TEMPLATES["free_delivery_all"][lang]

        # Delivery time text (only one based on current time)
        if next_slot:
            start_time_12hr = next_slot.start_time.strftime('%I:%M %p').lstrip('0')
            end_time_12hr = next_slot.end_time.strftime('%I:%M %p').lstrip('0')
            cutoff_time_12hr = next_slot.cutoff_time.strftime('%I:%M %p').lstrip('0')

            for lang in PROMOTIONAL_LANGUAGES:
                promotional_texts[lang]["delivery_time"] = PROMOTIONAL_TEMPLATES["delivery_time"][lang].format(
                    cutoff=cutoff_time_12hr,
                    start=start_time_12hr,
                    end=end_time_12hr,
                )
        else:
            # If no slots available today, show tomorrow's first slot
            tomorrow = today + datetime.timedelta(days=1)
            tomorrow_slots = DeliveryTimeSlot.objects.filter(is_active=True).order_by('sort_order', 'start_time')

            # Get overrides for tomorrow
            tomorrow_overrides = {
                o.slot_id: o.is_active
                for o in DeliverySlotOverride.objects.filter(date=tomorrow)
            }

            tomorrow_slot = None
            for slot in tomorrow_slots:
                if slot.id in tomorrow_overrides:
                    if not tomorrow_overrides[slot.id]:
                        continue
                tomorrow_slot = slot
                break

            if tomorrow_slot:
                start_time_12hr = tomorrow_slot.start_time.strftime('%I:%M %p').lstrip('0')
                end_time_12hr = tomorrow_slot.end_time.strftime('%I:%M %p').lstrip('0')
                for lang in PROMOTIONAL_LANGUAGES:
                    promotional_texts[lang]["delivery_time"] = PROMOTIONAL_TEMPLATES["delivery_time_tomorrow"][lang].format(
                        start=start_time_12hr,
                        end=end_time_12hr,
                    )
            else:
                for lang in PROMOTIONAL_LANGUAGES:
                    promotional_texts[lang]["delivery_time"] = PROMOTIONAL_TEMPLATES["delivery_time_fallback"][lang]

        return Response({
            "promotional_texts": promotional_texts,
            "timestamp": now_uae.isoformat(),
            "timezone": "Asia/Dubai"
        }, status=status.HTTP_200_OK)
