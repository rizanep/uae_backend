from rest_framework import serializers
from .models import MarketingMedia, Coupon, RewardConfiguration
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
            "tag",
            "highlight",
            "cta",
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


class AdminCouponSerializer(serializers.ModelSerializer):
    """Admin serializer for full CRUD operations on coupons."""
    assigned_user_email = serializers.CharField(source='assigned_user.email', read_only=True)
    
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
            'assigned_user_email',
            'is_referral_reward',
            'is_first_order_reward',
            'created_at',
            'updated_at',
            'deleted_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'assigned_user_email', 'used_count']

    def validate(self, attrs):
        discount_type = attrs.get('discount_type')
        discount_value = attrs.get('discount_value')
        
        # Only validate if discount_value is provided (not None)
        if discount_value is not None:
            if discount_type == 'percentage' and (discount_value < 0 or discount_value > 100):
                raise serializers.ValidationError(
                    {'discount_value': 'Percentage discount must be between 0 and 100.'}
                )
            
            if discount_value < 0:
                raise serializers.ValidationError(
                    {'discount_value': 'Discount value cannot be negative.'}
                )
        
        return attrs


class RewardConfigurationSerializer(serializers.ModelSerializer):
    """Admin serializer for managing reward configuration and scales."""
    updated_by_email = serializers.CharField(source='updated_by.email', read_only=True)
    
    class Meta:
        model = RewardConfiguration
        fields = [
            'first_order_discount_type',
            'first_order_discount_value',
            'first_order_min_amount',
            'first_order_validity_days',
            'referral_discount_type',
            'referral_discount_value',
            'referral_min_amount',
            'referral_validity_days',
            'referral_usage_limit',
            'referrer_discount_value',
            'referrer_validity_days',
            'max_discount_percentage',
            'is_referral_active',
            'is_first_order_active',
            'updated_by',
            'updated_by_email',
            'updated_at',
        ]
        read_only_fields = ['updated_by_email', 'updated_at']

    def validate(self, attrs):
        # Validate first order discount
        if attrs.get('first_order_discount_type') == 'percentage':
            value = attrs.get('first_order_discount_value', 0)
            if value < 0 or value > 100:
                raise serializers.ValidationError(
                    {'first_order_discount_value': 'Percentage must be between 0 and 100.'}
                )
        
        if attrs.get('first_order_discount_value', 0) < 0:
            raise serializers.ValidationError(
                {'first_order_discount_value': 'Discount value cannot be negative.'}
            )
        
        # Validate referral discount
        if attrs.get('referral_discount_type') == 'percentage':
            value = attrs.get('referral_discount_value', 0)
            if value < 0 or value > 100:
                raise serializers.ValidationError(
                    {'referral_discount_value': 'Percentage must be between 0 and 100.'}
                )
        
        if attrs.get('referral_discount_value', 0) < 0:
            raise serializers.ValidationError(
                {'referral_discount_value': 'Discount value cannot be negative.'}
            )
        
        # Validate referrer discount
        if attrs.get('referrer_discount_value', 0) < 0:
            raise serializers.ValidationError(
                {'referrer_discount_value': 'Referrer discount cannot be negative.'}
            )
        
        return attrs
