from django.contrib import admin
from .models import (
    Order,
    OrderItem,
    OrderStatusHistory,
    Payment,
    Receipt,
    DeliveryChargeConfig,
    DeliveryAssignment,
    DeliveryCancellationRequest,
    DeliveryProof,
)

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


class DeliveryAssignmentInline(admin.StackedInline):
    model = DeliveryAssignment
    extra = 0
    readonly_fields = ["assigned_at", "accepted_at", "delivered_at"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "status", "total_amount", "created_at", "tip_amount"]
    list_filter = ["status", "created_at"]
    search_fields = ["id", "user__email", "user__phone_number"]
    inlines = [OrderItemInline, OrderStatusHistoryInline, PaymentInline, DeliveryAssignmentInline]
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
    search_fields = ["transaction_id", "ziina_payment_intent_id", "order__id"]
    
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


@admin.register(DeliveryAssignment)
class DeliveryAssignmentAdmin(admin.ModelAdmin):
    list_display = ["order", "delivery_boy", "status", "assigned_by", "assigned_at", "delivered_at"]
    list_filter = ["status", "assigned_at"]
    search_fields = ["order__id", "delivery_boy__email", "delivery_boy__phone_number"]
    readonly_fields = ["assigned_at", "accepted_at", "delivered_at"]


@admin.register(DeliveryCancellationRequest)
class DeliveryCancellationRequestAdmin(admin.ModelAdmin):
    list_display = ["order", "requested_by", "status", "requested_at", "reviewed_by", "reviewed_at"]
    list_filter = ["status", "requested_at", "reviewed_at"]
    search_fields = ["order__id", "requested_by__email", "requested_by__phone_number"]
    readonly_fields = ["requested_at", "reviewed_at"]


@admin.register(DeliveryProof)
class DeliveryProofAdmin(admin.ModelAdmin):
    list_display = ["order", "assignment", "uploaded_by", "created_at"]
    search_fields = ["order__id", "uploaded_by__email", "uploaded_by__phone_number"]
    readonly_fields = ["created_at"]
