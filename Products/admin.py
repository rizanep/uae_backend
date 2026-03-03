from django.contrib import admin
from .models import Category, Product, ProductImage, ProductVideo
from .delivery_models import ProductDeliveryTier

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "parent", "created_at", "deleted_at"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name", "description"]
    list_filter = ["deleted_at", "created_at"]


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductVideoInline(admin.TabularInline):
    model = ProductVideo
    extra = 1


class ProductDeliveryTierInline(admin.TabularInline):
    model = ProductDeliveryTier
    extra = 1
    ordering = ("min_quantity",)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "category",
        "price",
        "discount_price",
        "stock",
        "is_available",
        "expected_delivery_time",
        "created_at",
        "deleted_at",
    ]
    list_filter = ["category", "is_available", "created_at", "deleted_at"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name", "description", "sku"]
    inlines = [ProductImageInline, ProductVideoInline, ProductDeliveryTierInline]
    list_editable = ["price", "discount_price", "stock", "is_available", "expected_delivery_time"]
