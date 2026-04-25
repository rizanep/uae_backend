from rest_framework import serializers
from .models import (
    Order,
    OrderItem,
    OrderStatusHistory,
    Payment,
    Receipt,
    DeliveryAssignment,
    DeliveryProof,
    DeliveryCancellationRequest,
    DeliveryTimeSlot,
    DeliverySlotOverride,
)
from Users.serializers import UserAddressSerializer, UserSerializer


class DeliveryTimeSlotSerializer(serializers.ModelSerializer):
    """Public serializer - used for customer slot selection."""
    start_time_display = serializers.SerializerMethodField()
    end_time_display = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryTimeSlot
        fields = [
            "id",
            "name",
            "start_time",
            "end_time",
            "cutoff_time",
            "start_time_display",
            "end_time_display",
            "sort_order",
        ]

    def get_start_time_display(self, obj):
        return obj.start_time.strftime('%I:%M %p')

    def get_end_time_display(self, obj):
        return obj.end_time.strftime('%I:%M %p')


class AdminDeliveryTimeSlotSerializer(serializers.ModelSerializer):
    """Admin serializer - full CRUD with all fields."""
    class Meta:
        model = DeliveryTimeSlot
        fields = [
            "id",
            "name",
            "start_time",
            "end_time",
            "cutoff_time",
            "is_active",
            "sort_order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        start_time = attrs.get('start_time') or (self.instance.start_time if self.instance else None)
        end_time = attrs.get('end_time') or (self.instance.end_time if self.instance else None)
        cutoff_time = attrs.get('cutoff_time') or (self.instance.cutoff_time if self.instance else None)

        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError({'end_time': 'End time must be after start time.'})
        if cutoff_time and start_time and cutoff_time >= start_time:
            raise serializers.ValidationError({'cutoff_time': 'Cutoff time must be before start time.'})
        return attrs


class DeliverySlotOverrideSerializer(serializers.ModelSerializer):
    slot_name = serializers.CharField(source='slot.name', read_only=True)

    class Meta:
        model = DeliverySlotOverride
        fields = [
            "id",
            "slot",
            "slot_name",
            "date",
            "is_active",
            "reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusHistory
        fields = ["status", "notes", "created_at"]


class DeliveryAssignmentSerializer(serializers.ModelSerializer):
    delivery_boy_name = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryAssignment
        fields = [
            "id",
            "delivery_boy",
            "delivery_boy_name",
            "status",
            "assigned_at",
            "accepted_at",
            "delivered_at",
            "notes",
        ]

    def get_delivery_boy_name(self, obj):
        user = obj.delivery_boy
        if user.first_name or user.last_name:
            return f"{user.first_name} {user.last_name}".strip()
        return user.email or user.phone_number


class DeliveryProofSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryProof
        fields = ["id", "proof_image", "signature_name", "notes", "created_at"]


class DeliveryCancellationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryCancellationRequest
        fields = [
            "id",
            "reason",
            "status",
            "review_notes",
            "requested_at",
            "reviewed_at",
        ]


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
    delivery_assignment = DeliveryAssignmentSerializer(read_only=True)
    delivery_proof = DeliveryProofSerializer(read_only=True)
    delivery_cancel_request = DeliveryCancellationRequestSerializer(read_only=True)
    preferred_delivery_slot_details = DeliveryTimeSlotSerializer(source="preferred_delivery_slot", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "status",
            "shipping_address",
            "shipping_address_details",
            "total_amount",
            "tip_amount",
            "coupon",
            "coupon_code",
            "discount_amount",
            "delivery_charge",
            "preferred_delivery_date",
            "preferred_delivery_slot",
            "preferred_delivery_slot_details",
            "delivery_notes",
            "items",
            "status_history",
            "payment",
            "delivery_assignment",
            "delivery_proof",
            "delivery_cancel_request",
            "created_at",
            "updated_at",
            "user"
        ]
        read_only_fields = ["id","user", "status", "total_amount", "tip_amount", "coupon", "discount_amount", "delivery_charge", "created_at", "updated_at"]


class AdminPaymentSerializer(serializers.ModelSerializer):
    """
    Admin-only Payment serializer with full details including customer and order info.
    """
    payment_id = serializers.CharField(source='id', read_only=True)
    order_id = serializers.IntegerField(source='order.id', read_only=True)
    customer_id = serializers.IntegerField(source='order.user.id', read_only=True)
    customer_name = serializers.SerializerMethodField()
    customer_email = serializers.CharField(source='order.user.email', read_only=True)
    customer_phone = serializers.CharField(source='order.user.phone_number', read_only=True)
    order_status = serializers.CharField(source='order.status', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_status_display', read_only=True)
    transaction_date = serializers.DateTimeField(source='created_at', read_only=True)
    updated_date = serializers.DateTimeField(source='updated_at', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'payment_id',
            'order_id',
            'customer_id',
            'customer_name',
            'customer_email',
            'customer_phone',
            'amount',
            'payment_method',
            'payment_method_display',
            'status',
            'payment_status_display',
            'transaction_id',
            'ziina_payment_intent_id',
            'order_status',
            'transaction_date',
            'updated_date',
            'provider_response'
        ]
        read_only_fields = fields
    
    def get_customer_name(self, obj):
        """Get customer's full name or email as fallback."""
        user = obj.order.user
        if user.first_name or user.last_name:
            return f"{user.first_name} {user.last_name}".strip()
        return user.email
