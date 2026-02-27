from rest_framework import serializers
from .models import MarketingMedia


class MarketingMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketingMedia
        fields = [
            "id",
            "key",
            "position",
            "title",
            "subtitle",
            "description",
            "image_mobile",
            "image_desktop",
            "is_active",
            "start_at",
            "end_at",
            "sort_order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

