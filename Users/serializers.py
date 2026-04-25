from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, UserProfile, OTPToken, UserAddress, DeliveryBoyProfile
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
    delivery_profile = serializers.SerializerMethodField()

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
            'delivery_profile',
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

    def get_delivery_profile(self, obj):
        delivery_profile = getattr(obj, 'delivery_profile', None)
        if not delivery_profile:
            return None
        return {
            'is_available': delivery_profile.is_available,
            'assigned_emirates': delivery_profile.assigned_emirates,
            'assigned_emirates_display': delivery_profile.assigned_emirates_display,
            'vehicle_number': delivery_profile.vehicle_number,
            'identity_number': delivery_profile.identity_number,
            'emergency_contact': delivery_profile.emergency_contact,
            'notes': delivery_profile.notes,
        }


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
        
        # Create first order welcome coupon
        from Marketing.services import create_first_order_coupon, grant_referral_rewards
        try:
            create_first_order_coupon(user)
        except Exception as e:
            # Log error but don't fail user creation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create first order coupon for user {user.id}: {str(e)}")
        
        # If user was referred, grant referral rewards
        if referrer:
            try:
                grant_referral_rewards(referrer, user)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to grant referral rewards for user {user.id}: {str(e)}")
        
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
            profile, created = UserProfile.objects.get_or_create(user=instance)
            plang = profile_data.get('preferred_language')
            if plang == 'zh':
                profile_data['preferred_language'] = 'cn'
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()
            
        return instance


class UserAdminSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = User
        exclude = ['password']

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
    otp_platform = serializers.ChoiceField(
        choices=[('sms', 'SMS'), ('whatsapp', 'WhatsApp')],
        required=False,
        default='sms'
    )

    def validate(self, attrs):
        otp_type = attrs.get('otp_type')
        if otp_type == 'email' and not attrs.get('email'):
            raise serializers.ValidationError("Email is required for email OTP.")
        if otp_type == 'phone' and not attrs.get('phone_number'):
            raise serializers.ValidationError("Phone number is required for phone OTP.")
        if otp_type == 'email':
            attrs['otp_platform'] = 'sms'
        return attrs
    
    def create(self, validated_data):
        user = None
        email = validated_data.get('email')
        phone_number = validated_data.get('phone_number')
        first_name = validated_data.get('first_name', '')
        last_name = validated_data.get('last_name', '')
        otp_type = validated_data.get('otp_type')
        is_new_user = False

        # Try to find existing user
        if otp_type == 'email':
            user = User.objects.filter(email=email).first()
        else:
            user = User.objects.filter(phone_number=phone_number).first()
        
        # If user not found, try to use the authenticated user (for contact update)
        if not user and 'request' in self.context and self.context['request'].user.is_authenticated:
            user = self.context['request'].user

        if not user:
            # Create new user
            user = User.objects.create_user(
                email=email,
                password=None,
                phone_number=phone_number,
                first_name=first_name,
                last_name=last_name,
            )
            is_new_user = True

        # Generate a secure OTP only when real delivery channel is enabled.
        use_real_phone_otp = (
            getattr(settings, 'USE_REAL_TWILIO_OTP', False)
            or getattr(settings, 'USE_REAL_MSG91_SMS', False)
            or getattr(settings, 'USE_REAL_MSG91_WHATSAPP', False)
        )
        # use_real_email_otp = getattr(settings, 'USE_REAL_SMTP', False)
        use_real_email_otp =False

        should_use_real_otp = (otp_type == 'phone' and use_real_phone_otp) or (otp_type == 'email' and use_real_email_otp)
        code = str(random.randint(100000, 999999)) if should_use_real_otp else "000000"
            
        # Save OTP to database
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
        
        # Create first order welcome coupon for new users
        if is_new_user:
            from Marketing.services import create_first_order_coupon
            try:
                create_first_order_coupon(user)
            except Exception as e:
                # Log error but don't fail OTP creation
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to create first order coupon for user {user.id}: {str(e)}")
        
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


class DeliveryBoyProfileSerializer(serializers.ModelSerializer):
    """Serializer for delivery boy profile"""
    class Meta:
        model = DeliveryBoyProfile
        fields = [
            'id',
            'user',
            'assigned_emirates',
            'is_available',
            'identity_number',
            'vehicle_number',
            'emergency_contact',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class DeliveryBoyCreateSerializer(serializers.Serializer):
    """
    Admin-only serializer for creating a delivery boy with user account and profile.
    Creates a User with role='delivery_boy' and associated DeliveryBoyProfile.
    """
    # User fields
    email = serializers.EmailField(required=True)
    phone_number = serializers.CharField(required=True, max_length=20)
    first_name = serializers.CharField(required=True, max_length=150)
    last_name = serializers.CharField(required=True, max_length=150)
    
    # Delivery Profile fields
    assigned_emirates = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text='List of emirate codes (e.g., ["abu_dhabi", "dubai"])'
    )
    identity_number = serializers.CharField(required=False, allow_blank=True, max_length=100)
    vehicle_number = serializers.CharField(required=False, allow_blank=True, max_length=50)
    emergency_contact = serializers.CharField(required=False, allow_blank=True, max_length=20)
    notes = serializers.CharField(required=False, allow_blank=True, style={'base_template': 'textarea.html'})
    is_available = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        """Validate email and phone uniqueness"""
        email = attrs.get('email')
        phone = attrs.get('phone_number')
        
        if User.objects.filter(email=email, deleted_at__isnull=True).exists():
            raise serializers.ValidationError({'email': 'A user with this email already exists.'})
        
        if User.objects.filter(phone_number=phone, deleted_at__isnull=True).exists():
            raise serializers.ValidationError({'phone_number': 'A user with this phone number already exists.'})

        profile = DeliveryBoyProfile(
            assigned_emirates=attrs.get('assigned_emirates', []),
            identity_number=attrs.get('identity_number', ''),
            vehicle_number=attrs.get('vehicle_number', ''),
            emergency_contact=attrs.get('emergency_contact', ''),
            notes=attrs.get('notes', ''),
            is_available=attrs.get('is_available', True),
        )
        profile.clean()
        
        return attrs

    def create(self, validated_data):
        from django.db import transaction
        
        # Extract user and profile data
        email = validated_data.pop('email')
        phone_number = validated_data.pop('phone_number')
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name')
        
        assigned_emirates = validated_data.pop('assigned_emirates', [])
        identity_number = validated_data.pop('identity_number', '')
        vehicle_number = validated_data.pop('vehicle_number', '')
        emergency_contact = validated_data.pop('emergency_contact', '')
        notes = validated_data.pop('notes', '')
        is_available = validated_data.pop('is_available', True)
        
        try:
            with transaction.atomic():
                # Create user with delivery_boy role
                user = User.objects.create_user(
                    email=email,
                    phone_number=phone_number,
                    first_name=first_name,
                    last_name=last_name,
                    password=None,  # No password - they'll use Google OAuth or OTP
                    role='delivery_boy'
                )
                
                # Signal auto-creates DeliveryBoyProfile for delivery_boy users.
                profile, _ = DeliveryBoyProfile.objects.get_or_create(user=user)
                profile.assigned_emirates = assigned_emirates
                profile.identity_number = identity_number
                profile.vehicle_number = vehicle_number
                profile.emergency_contact = emergency_contact
                profile.notes = notes
                profile.is_available = is_available
                profile.full_clean()
                profile.save()

                return User.objects.select_related('profile', 'delivery_profile').get(pk=user.pk)
        except Exception as e:
            raise serializers.ValidationError({'detail': f'Failed to create delivery boy: {str(e)}'})

    def to_representation(self, instance):
        """Return full user data including delivery profile"""
        return UserSerializer(instance).data


class DeliveryBoyUpdateSerializer(serializers.Serializer):
    """Admin-only serializer for updating a delivery boy user and profile."""
    email = serializers.EmailField(required=False)
    phone_number = serializers.CharField(required=False, max_length=20)
    first_name = serializers.CharField(required=False, max_length=150)
    last_name = serializers.CharField(required=False, max_length=150)
    is_active = serializers.BooleanField(required=False)
    assigned_emirates = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text='List of emirate codes (e.g., ["abu_dhabi", "dubai"])'
    )
    identity_number = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=100)
    vehicle_number = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=50)
    emergency_contact = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=20)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    is_available = serializers.BooleanField(required=False)

    def validate(self, attrs):
        user = self.context['delivery_boy']
        email = attrs.get('email')
        phone = attrs.get('phone_number')

        if email and User.objects.filter(email=email, deleted_at__isnull=True).exclude(pk=user.pk).exists():
            raise serializers.ValidationError({'email': 'A user with this email already exists.'})

        if phone and User.objects.filter(phone_number=phone, deleted_at__isnull=True).exclude(pk=user.pk).exists():
            raise serializers.ValidationError({'phone_number': 'A user with this phone number already exists.'})

        profile = getattr(user, 'delivery_profile', DeliveryBoyProfile(user=user))
        for field in ['assigned_emirates', 'identity_number', 'vehicle_number', 'emergency_contact', 'notes', 'is_available']:
            if field in attrs:
                setattr(profile, field, attrs[field])
        profile.clean()

        return attrs

    def update(self, instance, validated_data):
        for field in ['email', 'phone_number', 'first_name', 'last_name', 'is_active']:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        instance.save()

        profile, _ = DeliveryBoyProfile.objects.get_or_create(user=instance)
        for field in ['assigned_emirates', 'identity_number', 'vehicle_number', 'emergency_contact', 'notes', 'is_available']:
            if field in validated_data:
                setattr(profile, field, validated_data[field])
        profile.full_clean()
        profile.save()

        return User.objects.select_related('profile', 'delivery_profile').get(pk=instance.pk)


class AccountDeletionRequestSerializer(serializers.Serializer):
    """Serializer for account deletion request"""
    # password = serializers.CharField(
    #     write_only=True,
    #     required=False,
    #     help_text="Password confirmation required for security"
    # )
    delete_method = serializers.ChoiceField(
        choices=['soft', 'hard'],
        default='soft',
        help_text="soft: anonymize account, hard: permanently delete all data"
    )
    confirm_deletion = serializers.BooleanField(
        default=False,
        help_text="Must be True to confirm account deletion"
    )
    
    def validate(self, data):
        """Validate deletion request"""
        user = self.context['request'].user
        
        # Verify password
        # if not user.check_password(data['password']):
        #     raise serializers.ValidationError("Invalid password")
        
        # Require explicit confirmation
        if not data['confirm_deletion']:
            raise serializers.ValidationError(
                "You must confirm account deletion by setting confirm_deletion to true"
            )
        
        # Check if account can be deleted
        from .account_deletion_service import AccountDeletionService
        can_delete, reason = AccountDeletionService.can_delete_account(user)
        if not can_delete:
            raise serializers.ValidationError(reason)
        
        return data


class AccountDeletionInfoSerializer(serializers.Serializer):
    """Serializer for account deletion information"""
    user = serializers.DictField()
    related_data = serializers.DictField()
    note = serializers.CharField()


class AccountDeletionResponseSerializer(serializers.Serializer):
    """Serializer for account deletion response"""
    status = serializers.CharField()
    user_id = serializers.IntegerField()
    user_email = serializers.EmailField()
    user_phone = serializers.CharField(allow_null=True)
    deletion_method = serializers.CharField()
    deletion_status = serializers.CharField()
    deleted_at = serializers.DateTimeField()
    message = serializers.CharField()
