from rest_framework import serializers
from .models import Order, OrderItem, OrderStatusHistory, Payment, Receipt
from Users.serializers import UserAddressSerializer, UserSerializer

class OrderStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusHistory
        fields = ["status", "notes", "created_at"]


class ReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Receipt
        fields = ["receipt_number", "generated_at"]


class PaymentSerializer(serializers.ModelSerializer):
    receipt = ReceiptSerializer(read_only=True)
    
    class Meta:
        model = Payment
        fields = ["transaction_id", "amount", "status", "payment_method", "receipt", "created_at"]


class OrderItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    product_image = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ["id", "product", "product_name", "product_image", "quantity", "price", "subtotal"]

    def get_product_image(self, obj):
        if obj.product and obj.product.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.product.image.url)
            return obj.product.image.url
        return None


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    shipping_address_details = UserAddressSerializer(source="shipping_address", read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)
    payment = PaymentSerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "status",
            "shipping_address",
            "shipping_address_details",
            "total_amount",
            "tip_amount",
            "preferred_delivery_date",
            "preferred_delivery_slot",
            "delivery_notes",
            "items",
            "status_history",
            "payment",
            "created_at",
            "updated_at",
            "user"
        ]
        read_only_fields = ["id","user", "status", "total_amount", "tip_amount", "created_at", "updated_at"]
