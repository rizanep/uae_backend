from rest_framework import serializers
from .models import Cart, CartItem
from Products.serializers import ProductSerializer

class CartItemSerializer(serializers.ModelSerializer):
    product_details = ProductSerializer(source="product", read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ["id", "product", "product_details", "quantity", "subtotal", "created_at", "updated_at"]
        read_only_fields = ["id", "subtotal", "created_at", "updated_at"]

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
