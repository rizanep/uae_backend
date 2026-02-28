from django.contrib import admin
from .models import Order, OrderItem, OrderStatusHistory, Payment, Receipt

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


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ["receipt_number", "payment", "generated_at"]
    search_fields = ["receipt_number", "payment__transaction_id"]
