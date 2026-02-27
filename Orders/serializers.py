from rest_framework import serializers
from .models import Order, OrderItem, OrderStatusHistory, Payment, Receipt
from Users.serializers import UserAddressSerializer

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

    class Meta:
        model = OrderItem
        fields = ["id", "product", "product_name", "quantity", "price", "subtotal"]


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
            "preferred_delivery_date",
            "preferred_delivery_slot",
            "delivery_notes",
            "items",
            "status_history",
            "payment",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "total_amount", "created_at", "updated_at"]
