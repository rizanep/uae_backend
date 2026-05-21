from django.contrib import admin
from .models import Category, Product, ProductImage, ProductVideo, ProductNotification, ProductPreparationSpecification
from .delivery_models import ProductDeliveryTier

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "name_arabic", "name_chinese", "slug", "parent", "created_at", "deleted_at"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name", "name_arabic", "name_chinese", "description"]
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


class ProductPreparationSpecificationInline(admin.TabularInline):
    model = ProductPreparationSpecification
    extra = 1
    fields = ['name', 'description', 'extra_price', 'image', 'is_active', 'sort_order']
    ordering = ('sort_order', 'name')


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
    inlines = [ProductImageInline, ProductVideoInline, ProductDeliveryTierInline, ProductPreparationSpecificationInline]
    list_editable = ["price", "discount_price", "stock", "is_available", "expected_delivery_time"]


@admin.register(ProductPreparationSpecification)
class ProductPreparationSpecificationAdmin(admin.ModelAdmin):
    list_display = ["product", "name", "extra_price", "is_active", "sort_order", "created_at"]
    list_filter = ["product", "is_active", "created_at"]
    search_fields = ["product__name", "name", "description"]
    list_editable = ["extra_price", "is_active", "sort_order"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["product", "sort_order", "name"]
    
    fieldsets = (
        ("Basic Info", {
            "fields": ("product", "name", "description")
        }),
        ("Pricing & Display", {
            "fields": ("extra_price", "sort_order", "is_active")
        }),
        ("Image", {
            "fields": ("image",)
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )


@admin.register(ProductNotification)
class ProductNotificationAdmin(admin.ModelAdmin):
    list_display = ["user", "product", "notified", "created_at"]
    list_filter = ["notified", "created_at", "product"]
    search_fields = ["user__email", "user__phone_number", "product__name"]
    readonly_fields = ["created_at"]
    list_editable = ["notified"]
    ordering = ["-created_at"]
