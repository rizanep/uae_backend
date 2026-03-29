from django.contrib import admin
from .models import Order, OrderItem, OrderStatusHistory, Payment, Receipt, DeliveryChargeConfig

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["product_name", "quantity", "price", "subtotal"]


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ["created_at"]


class PaymentInline(admin.StackedInline):
    model = Payment
    extra = 0
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "status", "total_amount", "created_at", "tip_amount"]
    list_filter = ["status", "created_at"]
    search_fields = ["id", "user__email", "user__phone_number"]
    inlines = [OrderItemInline, OrderStatusHistoryInline, PaymentInline]
    readonly_fields = ["total_amount", "created_at", "updated_at"]
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('user', 'shipping_address', 'payment')
    
    fieldsets = (
        ("Order Info", {
            "fields": ("user", "status", "total_amount", "created_at", "updated_at", "tip_amount")
        }),
        ("Shipping Info", {
            "fields": ("shipping_address",)
        }),
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["order", "transaction_id", "amount", "status", "created_at"]
    list_filter = ["status", "payment_method"]
    search_fields = ["transaction_id", "telr_reference", "order__id"]
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('order', 'receipt')


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ["receipt_number", "payment", "generated_at"]
    search_fields = ["receipt_number", "payment__transaction_id"]
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('payment')


@admin.register(DeliveryChargeConfig)
class DeliveryChargeConfigAdmin(admin.ModelAdmin):
    list_display = ["min_free_shipping_amount", "delivery_charge", "is_active", "updated_at"]
    list_editable = ["min_free_shipping_amount", "delivery_charge", "is_active"]
    list_display_links = None  # Allow editing without opening individual records
    readonly_fields = ["updated_at", "updated_by"]
    
    def has_add_permission(self, request):
        # Only allow one instance
        return not DeliveryChargeConfig.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion
        return False
    
    fieldsets = (
        ("Configuration", {
            "fields": ("min_free_shipping_amount", "delivery_charge", "is_active")
        }),
        ("Meta", {
            "fields": ("updated_at", "updated_by"),
            "classes": ("collapse",)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
