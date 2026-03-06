from rest_framework import serializers
from django.db.models import Avg
from .models import Category, Product, ProductImage, ProductVideo, ProductDeliveryTier, ProductDiscountTier

class ProductDeliveryTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductDeliveryTier
        fields = ["id", "product", "min_quantity", "delivery_days"]

class ProductDiscountTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductDiscountTier
        fields = ["id", "product", "min_quantity", "discount_percentage"]

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description", "image", "parent"]
        read_only_fields = ["id", "slug"]


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "is_feature", "created_at"]
        read_only_fields = ["id", "created_at"]


class ProductVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVideo
        fields = ["id", "video_file", "video_url", "title", "created_at"]
        read_only_fields = ["id", "created_at"]


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    videos = ProductVideoSerializer(many=True, read_only=True)
    delivery_tiers = ProductDeliveryTierSerializer(many=True, read_only=True)
    discount_tiers = ProductDiscountTierSerializer(many=True, read_only=True)
    final_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    average_rating = serializers.SerializerMethodField()
    total_reviews = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "category",
            "category_name",
            "name",
            "slug",
            "description",
            "price",
            "discount_price",
            "final_price",
            "stock",
            "is_available",
            "image",
            "sku",
            "unit",
            "expected_delivery_time",
            "images",
            "videos",
            "delivery_tiers",
            "discount_tiers",
            "average_rating",
            "total_reviews",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "slug", "created_at", "updated_at"]

    def get_average_rating(self, obj):
        annotated_value = getattr(obj, "average_rating", None)
        if annotated_value is not None:
            return annotated_value

        prefetched_cache = getattr(obj, "_prefetched_objects_cache", None) or {}
        prefetched_reviews = prefetched_cache.get("reviews")
        if prefetched_reviews is not None:
            visible_ratings = [r.rating for r in prefetched_reviews if getattr(r, "is_visible", True)]
            if not visible_ratings:
                return 0
            return sum(visible_ratings) / len(visible_ratings)

        return obj.reviews.filter(is_visible=True).aggregate(Avg("rating"))["rating__avg"] or 0

    def get_total_reviews(self, obj):
        annotated_value = getattr(obj, "total_reviews", None)
        if annotated_value is not None:
            return annotated_value

        prefetched_cache = getattr(obj, "_prefetched_objects_cache", None) or {}
        prefetched_reviews = prefetched_cache.get("reviews")
        if prefetched_reviews is not None:
            return sum(1 for r in prefetched_reviews if getattr(r, "is_visible", True))

        return obj.reviews.filter(is_visible=True).count()

