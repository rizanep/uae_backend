from django.contrib import admin
from .models import MarketingMedia


@admin.register(MarketingMedia)
class MarketingMediaAdmin(admin.ModelAdmin):
    list_display = (
        "key",
        "position",
        "title",
        "is_active",
        "start_at",
        "end_at",
        "sort_order",
    )
    list_filter = ("position", "is_active")
    search_fields = ("key", "title", "subtitle", "description")
    ordering = ("sort_order", "-created_at")
