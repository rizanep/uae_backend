from rest_framework import serializers
from django.db.models import Avg
from .models import Category, Product, ProductImage, ProductVideo

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
            "expected_delivery_time",
            "images",
            "videos",
            "average_rating",
            "total_reviews",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "slug", "created_at", "updated_at"]

    def get_average_rating(self, obj):
        return obj.reviews.filter(is_visible=True).aggregate(Avg('rating'))['rating__avg'] or 0

    def get_total_reviews(self, obj):
        return obj.reviews.filter(is_visible=True).count()

