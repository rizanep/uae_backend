from rest_framework import serializers
from .models import Review, ReviewImage


class ReviewImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewImage
        fields = ["id", "image", "created_at"]


class ReviewSerializer(serializers.ModelSerializer):
    images = ReviewImageSerializer(many=True, read_only=True)
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)

    uploaded_images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Review
        fields = [
            "id",
            "product",
            "user",
            "user_name",
            "rating",
            "comment",
            "images",
            "uploaded_images",
            "admin_response",
            "is_visible",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "user",
            "admin_response",
            "is_visible",
            "created_at",
        ]

    def create(self, validated_data):
        user = self.context['request'].user
        product = validated_data['product']
        
        # Check if user already has a review for this product
        existing_review = Review.objects.filter(user=user, product=product).first()
        if existing_review:
            raise serializers.ValidationError({
                "detail": "You have already reviewed this product. You can edit your existing review instead.",
                "existing_review_id": existing_review.id,
                "can_edit": True
            })
        
        uploaded_images = validated_data.pop("uploaded_images", [])

        review = Review.objects.create(**validated_data)

        for image in uploaded_images:
            ReviewImage.objects.create(review=review, image=image)

        return review

    def update(self, instance, validated_data):
        uploaded_images = validated_data.pop("uploaded_images", [])
        
        # Update the review fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Add new images if provided
        for image in uploaded_images:
            ReviewImage.objects.create(review=instance, image=image)
        
        return instance