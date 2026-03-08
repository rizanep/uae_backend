from django.contrib import admin
from .models import User, OTPToken, GoogleOAuthToken, UserProfile, UserAddress


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'phone_number', 'first_name', 'last_name', 'role', 'is_active', 'is_email_verified', 'is_phone_verified')
    search_fields = ('email', 'phone_number', 'first_name', 'last_name')
    list_filter = ('role', 'is_active', 'is_email_verified', 'is_phone_verified')
    readonly_fields = ('created_at', 'updated_at', 'deleted_at', 'last_login_at')
    fields = (
        'email',
        'phone_number',
        'first_name',
        'last_name',
        'role',
        'is_active',
        'is_staff',
        'is_superuser',
        'is_email_verified',
        'is_phone_verified',
        'google_id',
        'google_email',
        'created_at',
        'updated_at',
        'deleted_at',
        'last_login_at',
    )

    def save_model(self, request, obj, form, change):
        if not change and not obj.password:
            obj.set_unusable_password()
        super().save_model(request, obj, form, change)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'preferred_language', 'newsletter_subscribed', 'notification_enabled')
    search_fields = ('user__email', 'user__phone_number')


@admin.register(OTPToken)
class OTPTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'otp_type', 'phone_number', 'email', 'is_verified', 'attempts', 'expires_at', 'created_at')
    list_filter = ('otp_type', 'is_verified')
    search_fields = ('user__email', 'phone_number', 'email')


@admin.register(GoogleOAuthToken)
class GoogleOAuthTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'expires_at', 'created_at')
    search_fields = ('user__email',)


@admin.register(UserAddress)
class UserAddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'address_type', 'city', 'emirate', 'is_default')
    list_filter = ('address_type', 'emirate', 'is_default')
    search_fields = ('user__email', 'full_name', 'city')
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('user')
