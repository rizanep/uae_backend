import uuid
from django.db import models
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.utils import timezone


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(TimestampedModel):
    deleted_at = models.DateTimeField(blank=True, null=True, db_index=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        if not self.deleted_at:
            self.deleted_at = timezone.now()
            self.save(update_fields=['deleted_at'])

    def restore(self):
        if self.deleted_at:
            self.deleted_at = None
            self.save(update_fields=['deleted_at'])


class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("The Email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None

    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('user', 'User'),
    ]

    email = models.EmailField(unique=True,null=True,blank=True)
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        unique=True,
        verbose_name='phone number',
        validators=[
            RegexValidator(
                regex=r'^\+?[1-9]\d{6,14}$',
                message='Enter a valid phone number in international format, e.g. +971501234567'
            )
        ]
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='user',
        db_index=True,
        verbose_name='role'
    )
    google_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        unique=True
    )
    google_email = models.EmailField(
        blank=True,
        null=True
    )
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(blank=True, null=True)
    phone_verified_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(blank=True, null=True, db_index=True)
    last_login_at = models.DateTimeField(blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        db_table = 'users'
        ordering = ['-created_at']

    def __str__(self):
        if self.email:
            return self.email
        return self.phone_number or f"User {self.pk}"

    def soft_delete(self):
        if not self.deleted_at:
            self.deleted_at = timezone.now()
            self.is_active = False
            self.save(update_fields=['deleted_at', 'is_active'])

    def restore(self):
        if self.deleted_at:
            self.deleted_at = None
            self.is_active = True
            self.save(update_fields=['deleted_at', 'is_active'])


class GoogleOAuthToken(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='google_token',
        verbose_name='user'
    )
    access_token = models.TextField()
    refresh_token = models.TextField(blank=True, null=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Google OAuth Token'
        verbose_name_plural = 'Google OAuth Tokens'
        db_table = 'google_oauth_tokens'

    def __str__(self):
        return f"Google OAuth Token for {self.user}"

    def is_expired(self):
        return timezone.now() >= self.expires_at


class OTPToken(models.Model):
    OTP_TYPE_CHOICES = [
        ('phone', 'Phone OTP'),
        ('email', 'Email OTP'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='otp_tokens',
        verbose_name='user'
    )
    otp_code = models.CharField(max_length=6)
    otp_type = models.CharField(
        max_length=10,
        choices=OTP_TYPE_CHOICES,
        db_index=True
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        db_index=True
    )
    email = models.EmailField(
        blank=True,
        null=True,
        db_index=True
    )
    is_verified = models.BooleanField(
        default=False,
        db_index=True
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=5)
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )
    expires_at = models.DateTimeField(db_index=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'OTP Token'
        verbose_name_plural = 'OTP Tokens'
        db_table = 'otp_tokens'
        ordering = ['-created_at']
        indexes = [
            models.Index(
                fields=['phone_number', 'otp_type', 'is_verified'],
                name='otp_phone_lookup_idx'
            ),
            models.Index(
                fields=['email', 'otp_type', 'is_verified'],
                name='otp_email_lookup_idx'
            ),
        ]

    def __str__(self):
        return f"OTP {self.otp_type.upper()} for {self.user}"

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def is_attempts_exceeded(self):
        return self.attempts >= self.max_attempts


class UserProfile(models.Model):
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('ar', 'Arabic'),
        ('cn', 'Chineese')
    ]
    
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='user'
    )
    profile_picture = models.ImageField(
        upload_to='profiles/',
        blank=True,
        null=True
    )
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
        blank=True,
        null=True,
        verbose_name='gender'
    )
    preferred_language = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
        default='en',
        verbose_name='preferred language'
    )
    newsletter_subscribed = models.BooleanField(default=True)
    notification_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        db_table = 'user_profiles'

    def __str__(self):
        return f"Profile of {self.user}"


class UserAddress(models.Model):
    ADDRESS_TYPE_CHOICES = [
        ('home', 'Home'),
        ('work', 'Work'),
        ('other', 'Other'),
    ]

    EMIRATE_CHOICES = [
        ('abu_dhabi', 'Abu Dhabi'),
        ('dubai', 'Dubai'),
        ('sharjah', 'Sharjah'),
        ('ajman', 'Ajman'),
        ('umm_al_quwain', 'Umm Al Quwain'),
        ('ras_al_khaimah', 'Ras Al Khaimah'),
        ('fujairah', 'Fujairah'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='addresses',
        verbose_name='user'
    )
    label = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Optional custom label, e.g. 'Mom's house'"
    )
    address_type = models.CharField(
        max_length=10,
        choices=ADDRESS_TYPE_CHOICES,
        default='home'
    )
    is_default = models.BooleanField(
        default=False,
        db_index=True,
        help_text='Marks this address as the default delivery address.'
    )
    full_name = models.CharField(
        max_length=255,
        verbose_name='recipient full name'
    )
    phone_number = models.CharField(
        max_length=20,
        verbose_name='contact phone',
        validators=[
            RegexValidator(
                regex=r'^\+?[1-9]\d{6,14}$',
                message='Enter a valid phone number in international format, e.g. +971501234567'
            )
        ]
    )
    building_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    flat_villa_number = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )
    street_address = models.CharField(max_length=255)
    area = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    city = models.CharField(max_length=100)
    emirate = models.CharField(
        max_length=20,
        choices=EMIRATE_CHOICES
    )
    postal_code = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    country = models.CharField(
        max_length=2,
        default='AE'
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Address'
        verbose_name_plural = 'User Addresses'
        db_table = 'user_addresses'
        ordering = ['-is_default', '-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(is_default=True),
                name='unique_default_address_per_user'
            )
        ]

    def __str__(self):
        return f"{self.full_name} - {self.address_type.title()} ({self.city})"
