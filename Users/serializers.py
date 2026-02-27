from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, UserProfile, OTPToken, UserAddress
from django.utils import timezone
from datetime import timedelta
import random
from .tasks import send_email_task


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            'profile_picture',
            'date_of_birth',
            'gender',
            'preferred_language',
            'newsletter_subscribed',
            'notification_enabled',
        ]
        # Allow these fields to be writable for profile updates
        # read_only_fields = ['preferred_language', 'newsletter_subscribed', 'notification_enabled']


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'phone_number',
            'first_name',
            'last_name',
            'role',
            'is_active',
            'is_email_verified',
            'is_phone_verified',
            'google_id',
            'created_at',
            'updated_at',
            'deleted_at',
            'last_login_at',
            'profile',
        ]
        read_only_fields = [
            'role',
            'is_active',
            'is_email_verified',
            'is_phone_verified',
            'google_id',
            'created_at',
            'updated_at',
            'deleted_at',
            'last_login_at',
        ]


class UserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'email',
            'phone_number',
            'first_name',
            'last_name',
        ]

    def validate(self, attrs):
        email = attrs.get('email')
        phone = attrs.get('phone_number')
        if not email and not phone:
            raise serializers.ValidationError('At least one of email or phone_number is required.')
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data.get('email'),
            password=None,
            phone_number=validated_data.get('phone_number'),
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
        )
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(required=False)

    class Meta:
        model = User
        fields = [
            'email',
            'phone_number',
            'first_name',
            'last_name',
            'profile',
        ]

    def update(self, instance, validated_data):
        # Handle verification flags
        new_email = validated_data.get('email')
        new_phone = validated_data.get('phone_number')
        
        if new_email and new_email != instance.email:
            instance.is_email_verified = False
            
        if new_phone and new_phone != instance.phone_number:
            instance.is_phone_verified = False

        # Handle profile update
        profile_data = validated_data.pop('profile', None)
        
        # Update user instance
        instance = super().update(instance, validated_data)
        
        # Update profile instance
        if profile_data:
            if hasattr(instance, 'profile'):
                profile = instance.profile
                for attr, value in profile_data.items():
                    setattr(profile, attr, value)
                profile.save()
            else:
                UserProfile.objects.create(user=instance, **profile_data)
                 
        return instance


class UserAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'phone_number',
            'first_name',
            'last_name',
            'role',
            'is_active',
            'is_email_verified',
            'is_phone_verified',
            'created_at',
            'updated_at',
            'deleted_at',
        ]


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': 'Passwords do not match.'})
        return attrs


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'email'

    def validate(self, attrs):
        identifier = attrs.get('email') or self.initial_data.get('identifier')
        password = attrs.get('password')
        user = None
        if identifier and password:
            if '@' in identifier:
                user = authenticate(self.context['request'], email=identifier, password=password)
            else:
                # Try phone_number based login: find user by phone then authenticate by email
                try:
                    candidate = User.objects.get(phone_number=identifier)
                    user = authenticate(self.context['request'], email=candidate.email, password=password)
                except User.DoesNotExist:
                    user = None
        if not user:
            raise serializers.ValidationError({'detail': 'Invalid credentials.'})
        data = super().validate({'email': user.email, 'password': password})
        return data


class GoogleOAuthSerializer(serializers.Serializer):
    code = serializers.CharField()


class OTPRequestSerializer(serializers.Serializer):
    otp_type = serializers.ChoiceField(choices=[('phone', 'phone'), ('email', 'email')])
    phone_number = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)

    def validate(self, attrs):
        otp_type = attrs.get('otp_type')
        phone = attrs.get('phone_number')
        email = attrs.get('email')
        if otp_type == 'phone' and not phone:
            raise serializers.ValidationError({'phone_number': 'Phone number is required for phone OTP.'})
        if otp_type == 'email' and not email:
            raise serializers.ValidationError({'email': 'Email is required for email OTP.'})
        return attrs

    def create(self, validated_data):
        otp_type = validated_data['otp_type']
        phone = validated_data.get('phone_number')
        email = validated_data.get('email')
        user = None
        if otp_type == 'phone':
            user, _ = User.objects.get_or_create(
                phone_number=phone,
            )
        else:
            user, _ = User.objects.get_or_create(
                email=email
            )
        code = "000000"
        expires_at = timezone.now() + timedelta(minutes=5)
        otp = OTPToken.objects.create(
            user=user,
            otp_code=code,
            otp_type=otp_type,
            phone_number=phone if otp_type == 'phone' else None,
            email=email if otp_type == 'email' else None,
            expires_at=expires_at
        )
        if otp_type == 'email' and email:
            subject = "Your login OTP"
            message = f"Your OTP code is {code}. It will expire in 5 minutes."
            send_email_task.delay(subject, message, [email])
        return otp


class OTPLoginSerializer(serializers.Serializer):
    otp_type = serializers.ChoiceField(choices=[('phone', 'phone'), ('email', 'email')])
    phone_number = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    otp_code = serializers.CharField()

    def validate(self, attrs):
        otp_type = attrs['otp_type']
        phone = attrs.get('phone_number')
        email = attrs.get('email')
        if otp_type == 'phone' and not phone:
            raise serializers.ValidationError({'phone_number': 'Phone number is required for phone OTP.'})
        if otp_type == 'email' and not email:
            raise serializers.ValidationError({'email': 'Email is required for email OTP.'})
        return attrs


class UserAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAddress
        fields = [
            'id',
            'label',
            'address_type',
            'is_default',
            'full_name',
            'phone_number',
            'building_name',
            'flat_villa_number',
            'street_address',
            'area',
            'city',
            'emirate',
            'postal_code',
            'country',
            'latitude',
            'longitude',
        ]
