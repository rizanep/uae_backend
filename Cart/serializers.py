from rest_framework import serializers
from .models import Cart, CartItem
from Products.serializers import ProductSerializer
from Products.models import ProductPreparationSpecification


class CartPreparationSpecificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductPreparationSpecification
        fields = ["id", "name", "description", "image", "extra_price", "sort_order"]
        read_only_fields = fields

class CartItemSerializer(serializers.ModelSerializer):
    product_details = ProductSerializer(source="product", read_only=True)
    preparation_specification_details = CartPreparationSpecificationSerializer(source="preparation_specification", read_only=True)
    base_unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    preparation_extra_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = [
            "id",
            "product",
            "product_details",
            "preparation_specification",
            "preparation_specification_details",
            "preparation_instructions",
            "quantity",
            "base_unit_price",
            "preparation_extra_price",
            "unit_price",
            "subtotal",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "preparation_specification_details",
            "base_unit_price",
            "preparation_extra_price",
            "unit_price",
            "subtotal",
            "created_at",
            "updated_at",
        ]

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return value


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_items = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cart
        fields = ["id", "user", "items", "total_price", "total_items", "created_at", "updated_at"]
        read_only_fields = ["id", "user", "total_price", "total_items", "created_at", "updated_at"]
