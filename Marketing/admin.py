from django.contrib import admin
from .models import MarketingMedia, Coupon

@admin.action(description="Soft delete selected items")
def soft_delete_selected(modeladmin, request, queryset):
    for obj in queryset:
        obj.soft_delete()

@admin.action(description="Restore selected items")
def restore_selected(modeladmin, request, queryset):
    for obj in queryset:
        obj.restore()

@admin.register(MarketingMedia)
class MarketingMediaAdmin(admin.ModelAdmin):
    list_display = (
        "key",
        "position",
        "title",
        "is_active",
        "start_at",
        "end_at",
        "deleted_at",
        "sort_order",
    )
    list_filter = ("position", "is_active", "start_at", "end_at")
    search_fields = ("key", "title", "subtitle", "description")
    ordering = ("sort_order", "-created_at")
    readonly_fields = ("created_at", "updated_at", "deleted_at")
    actions = [soft_delete_selected, restore_selected]

    fieldsets = (
        (None, {
            "fields": (
                "key",
                "position",
                "title",
                "subtitle",
                "description",
                "image_mobile",
                "image_desktop",
                "is_active",
                "sort_order",
            )
        }),
        ("Schedule", {
            "fields": (
                "start_at",
                "end_at",
            )
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at", "deleted_at"),
            "classes": ("collapse",),
        }),
    )

    def get_queryset(self, request):
        """
        Show all items (including soft-deleted) in admin so they can be restored.
        """
        # Since SoftDeleteModel doesn't filter by default in the manager, 
        # this is just the default behavior, but explicit is good.
        return super().get_queryset(request)


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "discount_type",
        "discount_value",
        "is_active",
        "valid_from",
        "valid_to",
        "usage_limit",
        "used_count",
        "assigned_user",
        "is_referral_reward",
        "is_first_order_reward",
    )
    list_filter = (
        "is_active",
        "discount_type",
        "is_referral_reward",
        "is_first_order_reward",
        "valid_from",
        "valid_to",
    )
    search_fields = ("code", "description", "assigned_user__email", "assigned_user__phone_number")
    readonly_fields = ("used_count", "created_at", "updated_at", "deleted_at")
    
    fieldsets = (
        (None, {
            "fields": (
                "code",
                "description",
                "discount_type",
                "discount_value",
                "is_active",
            )
        }),
        ("Conditions", {
            "fields": (
                "min_order_amount",
                "max_discount_amount",
                "valid_from",
                "valid_to",
                "usage_limit",
                "assigned_user",
            )
        }),
        ("System Flags", {
            "fields": (
                "is_referral_reward",
                "is_first_order_reward",
                "used_count",
            ),
            "classes": ("collapse",),
        }),
         ("Timestamps", {
            "fields": ("created_at", "updated_at", "deleted_at"),
             "classes": ("collapse",),
        }),
    )

    def get_queryset(self, request):
        # Show all including soft-deleted ones in admin to allow restoration if needed
        # Assuming SoftDeleteModel doesn't filter by default in admin, or we need to override if it does.
        # But wait, standard manager usually returns all unless overridden. 
        # If SoftDeleteModel has a custom manager that hides deleted, we might need objects.all_with_deleted() or similar.
        # Based on previous code search, SoftDeleteModel didn't show a custom manager.
        return super().get_queryset(request)
