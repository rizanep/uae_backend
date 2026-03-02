from rest_framework import serializers
from .models import MarketingMedia, Coupon
from Users.serializers import UserSerializer


class MarketingMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketingMedia
        fields = [
            "id",
            "key",
            "position",
            "title",
            "subtitle",
            "description",
            "image_mobile",
            "image_desktop",
            "is_active",
            "start_at",
            "end_at",
            "sort_order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = [
            'id',
            'code',
            'description',
            'discount_type',
            'discount_value',
            'min_order_amount',
            'max_discount_amount',
            'valid_from',
            'valid_to',
            'is_active',
            'usage_limit',
            'used_count',
            'assigned_user',
            'is_referral_reward',
            'is_first_order_reward',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'used_count']

    def validate(self, attrs):
        # Additional validation if needed
        return attrs


class ApplyReferralSerializer(serializers.Serializer):
    referral_code = serializers.CharField(required=True)
