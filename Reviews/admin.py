from django.contrib import admin
from .models import Review, ReviewImage

class ReviewImageInline(admin.TabularInline):
    model = ReviewImage
    extra = 1

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["product", "user", "rating", "is_visible", "created_at"]
    list_filter = ["rating", "is_visible", "created_at"]
    search_fields = ["product__name", "user__email", "comment"]
    actions = ["make_visible", "hide_reviews"]
    inlines = [ReviewImageInline]

    def make_visible(self, request, queryset):
        queryset.update(is_visible=True)
    make_visible.short_description = "Mark selected reviews as visible"

    def hide_reviews(self, request, queryset):
        queryset.update(is_visible=False)
    hide_reviews.short_description = "Hide selected reviews"
