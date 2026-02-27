from django.contrib import admin
from .models import Cart, CartItem

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ["subtotal"]

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ["user", "total_items", "total_price", "created_at", "updated_at"]
    search_fields = ["user__email", "user__phone_number"]
    inlines = [CartItemInline]
    readonly_fields = ["created_at", "updated_at"]

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ["cart", "product", "quantity", "subtotal", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["cart__user__email", "product__name"]
