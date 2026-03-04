from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, UserProfile, OTPToken, UserAddress
from django.utils import timezone
from datetime import timedelta
import random
from .tasks import send_email_task
from django.conf import settings


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
            'referral_code',
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
            'referral_code',
        ]


class UserCreateSerializer(serializers.ModelSerializer):
    referral_code = serializers.CharField(required=False, write_only=True)

    class Meta:
        model = User
        fields = [
            'email',
            'phone_number',
            'first_name',
            'last_name',
            'referral_code',
        ]

    def validate(self, attrs):
        email = attrs.get('email')
        phone = attrs.get('phone_number')
        referral_code = attrs.get('referral_code')

        if not email and not phone:
            raise serializers.ValidationError('At least one of email or phone_number is required.')
        
        if referral_code:
            try:
                referrer = User.objects.get(referral_code=referral_code)
                attrs['referrer'] = referrer
            except User.DoesNotExist:
                raise serializers.ValidationError({'referral_code': 'Invalid referral code.'})

        return attrs

    def create(self, validated_data):
        referrer = validated_data.pop('referrer', None)
        # remove referral_code from validated_data as it's not a model field for create_user
        validated_data.pop('referral_code', None) 

        extra_fields = {
            'phone_number': validated_data.get('phone_number'),
            'first_name': validated_data.get('first_name', ''),
            'last_name': validated_data.get('last_name', ''),
        }
        
        if referrer:
            extra_fields['referred_by'] = referrer

        user = User.objects.create_user(
            email=validated_data.get('email'),
            password=None,
            **extra_fields
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

    def validate(self, attrs):
        email = attrs.get('email', None)
        if email is not None:
            email = email.strip()
            if email == '':
                attrs['email'] = None
        final_email = attrs.get('email', getattr(self.instance, 'email', None))
        final_phone = attrs.get('phone_number', getattr(self.instance, 'phone_number', None))
        if not final_email and not final_phone:
            raise serializers.ValidationError('At least one of email or phone_number must be set.')
        return attrs

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', None)
        
        # Update User fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update UserProfile fields if provided
        if profile_data:
            # Create profile if it doesn't exist (though signal should have created it)
            profile, created = UserProfile.objects.get_or_create(user=instance)
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()
            
        return instance


class UserAdminSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = '__all__'

    def validate(self, attrs):
        email = attrs.get('email', None)
        if email is not None:
            email = email.strip()
            if email == '':
                attrs['email'] = None
        final_email = attrs.get('email', getattr(self.instance, 'email', None))
        final_phone = attrs.get('phone_number', getattr(self.instance, 'phone_number', None))
        if not final_email and not final_phone:
            raise serializers.ValidationError('At least one of email or phone_number must be set.')
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['email'] = user.email
        return token


class GoogleOAuthSerializer(serializers.Serializer):
    code = serializers.CharField(required=True)
    redirect_uri = serializers.CharField(required=False)


class OTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone_number = serializers.CharField(required=False)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    otp_type = serializers.ChoiceField(choices=[('email', 'Email'), ('phone', 'Phone')])

    def validate(self, attrs):
        otp_type = attrs.get('otp_type')
        if otp_type == 'email' and not attrs.get('email'):
            raise serializers.ValidationError("Email is required for email OTP.")
        if otp_type == 'phone' and not attrs.get('phone_number'):
            raise serializers.ValidationError("Phone number is required for phone OTP.")
        return attrs
    
    def create(self, validated_data):
        user = None
        email = validated_data.get('email')
        phone_number = validated_data.get('phone_number')
        first_name = validated_data.get('first_name', '')
        last_name = validated_data.get('last_name', '')
        otp_type = validated_data.get('otp_type')

        # Try to find existing user
        if otp_type == 'email':
            user = User.objects.filter(email=email).first()
        else:
            user = User.objects.filter(phone_number=phone_number).first()
        
        # If user not found, try to use the authenticated user (for contact update)
        if not user and 'request' in self.context and self.context['request'].user.is_authenticated:
            user = self.context['request'].user

        if not user:
            # if not email:
            #     normalized_phone = (phone_number or "").strip().lstrip("+")
            #     email = f"phone_{normalized_phone}@otp.local"
            user = User.objects.create_user(
                email=email,
                password=None,
                phone_number=phone_number,
                first_name=first_name,
                last_name=last_name,
            )

        # Generate 6 digit OTP
        if settings.USE_REAL_TWILIO_OTP and otp_type == 'phone':
            code = str(random.randint(100000, 999999))
        else:
            code = "000000"
            
        # Save OTP to database (we need a user, so if user is None, we might fail)
        # Let's assume user must exist for Login via OTP.
        if not user:
            raise serializers.ValidationError("User not found. Please register first.")

        # Invalidate old tokens
        OTPToken.objects.filter(user=user, otp_type=otp_type).delete()

        expires_at = timezone.now() + timedelta(minutes=5)
        otp = OTPToken.objects.create(
            user=user,
            otp_code=code,
            otp_type=otp_type,
            email=email,
            phone_number=phone_number,
            expires_at=expires_at,
        )
        return otp


class OTPLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone_number = serializers.CharField(required=False)
    otp_code = serializers.CharField(max_length=6)
    otp_type = serializers.ChoiceField(choices=[('email', 'Email'), ('phone', 'Phone')])

    def validate(self, attrs):
        email = attrs.get('email')
        phone_number = attrs.get('phone_number')
        otp_code = attrs.get('otp_code')
        otp_type = attrs.get('otp_type')

        user = None
        if otp_type == 'email':
            user = User.objects.filter(email=email).first()
        else:
            user = User.objects.filter(phone_number=phone_number).first()

        if not user:
            raise serializers.ValidationError("User not found.")

        otp_record = OTPToken.objects.filter(
            user=user,
            otp_code=otp_code,
            otp_type=otp_type,
            is_verified=False
        ).first()

        if not otp_record:
            raise serializers.ValidationError("Invalid or expired OTP.")
        
        if otp_record.is_expired():
             raise serializers.ValidationError("OTP has expired.")

        attrs['user'] = user
        attrs['otp_record'] = otp_record
        return attrs


class VerifyNewContactSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone_number = serializers.CharField(required=False)
    otp_code = serializers.CharField(max_length=6)
    otp_type = serializers.ChoiceField(choices=[('email', 'Email'), ('phone', 'Phone')])

    def validate(self, attrs):
        email = attrs.get('email')
        phone_number = attrs.get('phone_number')
        otp_code = attrs.get('otp_code')
        otp_type = attrs.get('otp_type')
        user = self.context['request'].user

        if otp_type == 'email' and not email:
            raise serializers.ValidationError("Email is required for email OTP.")
        if otp_type == 'phone' and not phone_number:
            raise serializers.ValidationError("Phone number is required for phone OTP.")

        # Check if the new contact is already in use by another user
        if otp_type == 'email':
            if User.objects.filter(email=email).exclude(id=user.id).exists():
                raise serializers.ValidationError("This email is already in use.")
        else:
            if User.objects.filter(phone_number=phone_number).exclude(id=user.id).exists():
                raise serializers.ValidationError("This phone number is already in use.")

        otp_record = OTPToken.objects.filter(
            user=user,
            otp_code=otp_code,
            otp_type=otp_type,
            is_verified=False
        ).order_by('-created_at').first()

        # Check if OTP matches the contact provided
        if otp_record:
            if otp_type == 'email' and otp_record.email != email:
                 raise serializers.ValidationError("OTP does not match the provided email.")
            if otp_type == 'phone' and otp_record.phone_number != phone_number:
                 raise serializers.ValidationError("OTP does not match the provided phone number.")

        if not otp_record:
            raise serializers.ValidationError("Invalid or expired OTP.")
        
        if otp_record.is_expired():
             raise serializers.ValidationError("OTP has expired.")

        attrs['otp_record'] = otp_record
        return attrs


class UserAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAddress
        fields = [
            'id',
            'user',
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
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
