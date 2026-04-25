from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, throttle_classes, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.db.models import Count, Sum, Avg, F, Q
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from datetime import timedelta
from decimal import Decimal
import re
import logging
import hmac
import hashlib
import json
import datetime
import pytz

from .models import (
    Order,
    OrderItem,
    Payment,
    Receipt,
    DeliveryChargeConfig,
    DeliveryAssignment,
    DeliveryProof,
    DeliveryCancellationRequest,
    DeliveryTimeSlot,
    DeliverySlotOverride,
)
from .serializers import (
    OrderSerializer,
    AdminPaymentSerializer,
    DeliveryTimeSlotSerializer,
    AdminDeliveryTimeSlotSerializer,
    DeliverySlotOverrideSerializer,
)
from Cart.models import Cart, CartItem
from Users.models import UserAddress, User
from Reviews.models import Review
from .payment_service import ZiinaPaymentService
from .receipt_templates import render_receipt_image, render_receipt_pdf, render_admin_receipt_pdf
from .utils import calculate_delivery_estimate, get_earliest_delivery_date
from .coupon_service import validate_and_calculate_coupon, apply_coupon_to_order, get_delivery_charge
from core.throttling import UserOrderThrottle, UserPaymentThrottle, AnonGeneralThrottle

UAE_TZ = pytz.timezone('Asia/Dubai')

logger = logging.getLogger(__name__)
webhook_logger = logging.getLogger('Orders.webhook')
payment_logger = logging.getLogger('Orders.payment')

class OrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user orders.
    Supports checkout from cart and payment simulation.
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = [
        "id",
        "user",
        "status",
        "shipping_address",
        "total_amount",
        "tip_amount",
        "preferred_delivery_date",
        "preferred_delivery_slot",
        "created_at",
        "updated_at",
        "payment__status",  # Payment status
        "payment__payment_method",
        "payment__amount",
    ]
    search_fields = [
        'id',
        'user__email',
        'user__phone_number',
        'user__first_name',
        'user__last_name',
        'shipping_address__emirate',
    ]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Order.objects.none()
        qs = Order.objects.select_related(
            "user", "shipping_address", "payment", "payment__receipt", "delivery_assignment", "delivery_proof"
        ).prefetch_related("items", "items__product", "status_history")
        if user.role == "admin":
            return qs
        if user.role == "delivery_boy":
            delivery_profile = getattr(user, "delivery_profile", None)
            if not delivery_profile:
                return Order.objects.none()
            assigned_emirates = delivery_profile.assigned_emirates or []
            return qs.filter(
                Q(delivery_assignment__delivery_boy=user)
                |
                (
                    Q(shipping_address__emirate__in=assigned_emirates)
                    & Q(status__in=[Order.OrderStatus.PAID, Order.OrderStatus.PROCESSING])
                    & Q(delivery_assignment__isnull=True)
                )
            ).distinct()
        return qs.filter(user=user)

    def _validate_delivery_access(self, order, user):
        if user.role != 'delivery_boy':
            return False, Response({'error': 'Only delivery boys can perform this action.'}, status=status.HTTP_403_FORBIDDEN)

        delivery_profile = getattr(user, 'delivery_profile', None)
        if not delivery_profile or not delivery_profile.is_available:
            return False, Response({'error': 'Delivery profile is not available.'}, status=status.HTTP_403_FORBIDDEN)

        if not order.shipping_address:
            return False, Response({'error': 'Order does not have a valid shipping address.'}, status=status.HTTP_400_BAD_REQUEST)

        if order.shipping_address.emirate not in (delivery_profile.assigned_emirates or []):
            return False, Response({'error': 'Order emirate is outside your assigned coverage.'}, status=status.HTTP_403_FORBIDDEN)

        return True, None

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def delivery_dashboard(self, request):
        user = request.user
        if user.role != 'delivery_boy':
            return Response({'error': 'Only delivery boys can access this dashboard.'}, status=status.HTTP_403_FORBIDDEN)

        profile = getattr(user, 'delivery_profile', None)
        if not profile:
            return Response({'error': 'Delivery profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        today = timezone.now().date()
        assigned_qs = DeliveryAssignment.objects.filter(delivery_boy=user)
        completed_today = assigned_qs.filter(delivered_at__date=today).count()
        pending_assigned = assigned_qs.exclude(order__status__in=[Order.OrderStatus.DELIVERED, Order.OrderStatus.CANCELLED]).count()

        available_orders_qs = Order.objects.filter(
            shipping_address__emirate__in=(profile.assigned_emirates or []),
            status__in=[Order.OrderStatus.PAID, Order.OrderStatus.PROCESSING],
            delivery_assignment__isnull=True,
        )

        recent_orders = Order.objects.filter(delivery_assignment__delivery_boy=user).order_by('-updated_at')[:10]

        return Response({
            'delivery_boy': {
                'id': user.id,
                'name': f"{user.first_name} {user.last_name}".strip() or user.email or user.phone_number,
                'is_available': profile.is_available,
                'assigned_emirates': profile.assigned_emirates,
                'assigned_emirates_display': profile.assigned_emirates_display,
            },
            'kpis': {
                'assigned_orders': assigned_qs.count(),
                'completed_today': completed_today,
                'pending_assigned_orders': pending_assigned,
                'available_orders_in_region': available_orders_qs.count(),
                'completed_total': assigned_qs.filter(status=DeliveryAssignment.AssignmentStatus.COMPLETED).count(),
            },
            'recent_assigned_orders': OrderSerializer(recent_orders, many=True, context={'request': request}).data,
        })

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def available_orders(self, request):
        user = request.user
        if user.role != 'delivery_boy':
            return Response({'error': 'Only delivery boys can access available orders.'}, status=status.HTTP_403_FORBIDDEN)

        profile = getattr(user, 'delivery_profile', None)
        if not profile:
            return Response({'error': 'Delivery profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        qs = Order.objects.filter(
            shipping_address__emirate__in=(profile.assigned_emirates or []),
            status__in=[Order.OrderStatus.PAID, Order.OrderStatus.PROCESSING],
            delivery_assignment__isnull=True,
        ).select_related('shipping_address', 'user', 'payment')

        serializer = OrderSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    @transaction.atomic
    def claim_order(self, request, pk=None):
        order = self.get_object()
        is_valid, error_response = self._validate_delivery_access(order, request.user)
        if not is_valid:
            return error_response

        if order.status not in [Order.OrderStatus.PAID, Order.OrderStatus.PROCESSING]:
            return Response({'error': 'Only paid or processing orders can be claimed.'}, status=status.HTTP_400_BAD_REQUEST)

        if hasattr(order, 'delivery_assignment'):
            return Response({'error': 'Order is already assigned.'}, status=status.HTTP_400_BAD_REQUEST)

        assignment = DeliveryAssignment.objects.create(
            order=order,
            delivery_boy=request.user,
            assigned_by=request.user,
            status=DeliveryAssignment.AssignmentStatus.ASSIGNED,
            accepted_at=timezone.now(),
            notes=request.data.get('notes', 'Claimed by delivery boy from regional queue.')
        )

        if order.status == Order.OrderStatus.PAID:
            order.status = Order.OrderStatus.PROCESSING
            order.save(update_fields=['status', 'updated_at'])

        return Response({
            'message': 'Order claimed successfully.',
            'order_id': order.id,
            'assignment_id': assignment.id,
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    @transaction.atomic
    def delivery_update_status(self, request, pk=None):
        order = self.get_object()
        if request.user.role != 'delivery_boy':
            return Response({'error': 'Only delivery boys can update delivery status.'}, status=status.HTTP_403_FORBIDDEN)

        assignment = getattr(order, 'delivery_assignment', None)
        if not assignment or assignment.delivery_boy_id != request.user.id:
            return Response({'error': 'Order is not assigned to you.'}, status=status.HTTP_403_FORBIDDEN)

        new_status = request.data.get('status')
        notes = request.data.get('notes', '')

        if new_status == Order.OrderStatus.SHIPPED:
            if order.status not in [Order.OrderStatus.PAID, Order.OrderStatus.PROCESSING]:
                return Response({'error': 'Order cannot be moved to SHIPPED from current status.'}, status=status.HTTP_400_BAD_REQUEST)

            order.status = Order.OrderStatus.SHIPPED
            order.save(update_fields=['status', 'updated_at'])
            assignment.status = DeliveryAssignment.AssignmentStatus.IN_TRANSIT
            if not assignment.accepted_at:
                assignment.accepted_at = timezone.now()
            assignment.notes = notes or assignment.notes
            assignment.save(update_fields=['status', 'accepted_at', 'notes'])
            return Response({'message': 'Order marked as shipped.'})

        if new_status == Order.OrderStatus.DELIVERED:
            if order.status != Order.OrderStatus.SHIPPED:
                return Response({'error': 'Order must be SHIPPED before DELIVERED.'}, status=status.HTTP_400_BAD_REQUEST)

            proof_image = request.FILES.get('proof_image')
            existing_proof = getattr(order, 'delivery_proof', None)
            if not proof_image and not existing_proof:
                return Response({'error': 'proof_image is required for delivery confirmation.'}, status=status.HTTP_400_BAD_REQUEST)

            order.status = Order.OrderStatus.DELIVERED
            order.save(update_fields=['status', 'updated_at'])

            assignment.status = DeliveryAssignment.AssignmentStatus.COMPLETED
            assignment.delivered_at = timezone.now()
            assignment.notes = notes or assignment.notes
            assignment.save(update_fields=['status', 'delivered_at', 'notes'])

            if existing_proof:
                if proof_image:
                    existing_proof.proof_image = proof_image
                existing_proof.signature_name = request.data.get('signature_name')
                existing_proof.notes = request.data.get('proof_notes')
                existing_proof.uploaded_by = request.user
                existing_proof.save()
            else:
                DeliveryProof.objects.create(
                    order=order,
                    assignment=assignment,
                    proof_image=proof_image,
                    signature_name=request.data.get('signature_name'),
                    notes=request.data.get('proof_notes'),
                    uploaded_by=request.user,
                )

            return Response({'message': 'Order marked as delivered with proof.'})

        if new_status == Order.OrderStatus.CANCELLED:
            reason = request.data.get('reason', '').strip()
            if not reason:
                return Response({'error': 'reason is required for cancellation request.'}, status=status.HTTP_400_BAD_REQUEST)

            cancel_request, created = DeliveryCancellationRequest.objects.get_or_create(
                order=order,
                defaults={
                    'requested_by': request.user,
                    'reason': reason,
                    'status': DeliveryCancellationRequest.RequestStatus.PENDING,
                }
            )
            if not created and cancel_request.status == DeliveryCancellationRequest.RequestStatus.PENDING:
                return Response({'error': 'Cancellation request is already pending admin review.'}, status=status.HTTP_400_BAD_REQUEST)

            if not created:
                cancel_request.requested_by = request.user
                cancel_request.reason = reason
                cancel_request.status = DeliveryCancellationRequest.RequestStatus.PENDING
                cancel_request.review_notes = None
                cancel_request.reviewed_by = None
                cancel_request.reviewed_at = None
                cancel_request.save()

            return Response({'message': 'Cancellation request submitted for admin approval.'}, status=status.HTTP_202_ACCEPTED)

        return Response(
            {'error': f'Invalid delivery status. Allowed: {Order.OrderStatus.SHIPPED}, {Order.OrderStatus.DELIVERED}, {Order.OrderStatus.CANCELLED}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    @transaction.atomic
    def admin_review_cancel_request(self, request, pk=None):
        order = self.get_object()
        cancel_request = getattr(order, 'delivery_cancel_request', None)
        if not cancel_request:
            return Response({'error': 'Cancellation request not found.'}, status=status.HTTP_404_NOT_FOUND)

        if cancel_request.status != DeliveryCancellationRequest.RequestStatus.PENDING:
            return Response({'error': 'Only pending cancellation requests can be reviewed.'}, status=status.HTTP_400_BAD_REQUEST)

        decision = request.data.get('decision')
        review_notes = request.data.get('review_notes', '')

        if decision == 'approve':
            order.status = Order.OrderStatus.CANCELLED
            order.save(update_fields=['status', 'updated_at'])
            cancel_request.status = DeliveryCancellationRequest.RequestStatus.APPROVED
        elif decision == 'reject':
            cancel_request.status = DeliveryCancellationRequest.RequestStatus.REJECTED
        else:
            return Response({'error': "decision must be either 'approve' or 'reject'."}, status=status.HTTP_400_BAD_REQUEST)

        cancel_request.reviewed_by = request.user
        cancel_request.review_notes = review_notes
        cancel_request.reviewed_at = timezone.now()
        cancel_request.save()

        return Response({'message': f'Cancellation request {cancel_request.status.lower()}.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    @transaction.atomic
    def admin_assign_delivery_boy(self, request, pk=None):
        order = self.get_object()
        delivery_boy_id = request.data.get('delivery_boy_id')
        notes = request.data.get('notes', 'Assigned by admin.')

        if not delivery_boy_id:
            return Response({'error': 'delivery_boy_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        delivery_boy = get_object_or_404(User, id=delivery_boy_id, role='delivery_boy')
        profile = getattr(delivery_boy, 'delivery_profile', None)
        if not profile:
            return Response({'error': 'Delivery boy profile not found.'}, status=status.HTTP_400_BAD_REQUEST)

        if not order.shipping_address:
            return Response({'error': 'Order does not have a shipping address.'}, status=status.HTTP_400_BAD_REQUEST)

        if order.shipping_address.emirate not in (profile.assigned_emirates or []):
            return Response({'error': 'Selected delivery boy is not assigned to this emirate.'}, status=status.HTTP_400_BAD_REQUEST)

        assignment_values = {
            'delivery_boy': delivery_boy,
            'assigned_by': request.user,
            'notes': notes,
        }

        assignment, created = DeliveryAssignment.objects.update_or_create(
            order=order,
            defaults=assignment_values,
        )

        if created and order.status == Order.OrderStatus.PAID:
            order.status = Order.OrderStatus.PROCESSING
            order.save(update_fields=['status', 'updated_at'])

        return Response({
            'message': 'Delivery boy assigned successfully.',
            'order_id': order.id,
            'assignment_id': assignment.id,
        })

    @throttle_classes([UserOrderThrottle(), AnonGeneralThrottle()])
    @action(detail=False, methods=["post"])
    def validate_coupon(self, request):
        """
        Validate a coupon code and calculate the discount amount.
        Returns breakdown of discount for confirmation before checkout.
        
        Request body:
        {
            "coupon_code": "SAVE20",
            "cart_total": 500.00
        }
        
        Response:
        {
            "success": true,
            "message": "Coupon 'SAVE20' is valid...",
            "discount_amount": 100.00,
            "discount_type": "percentage",
            "discount_percentage": 20,
            "cart_total": 500.00,
            "final_amount": 400.00
        }
        
        Rate limited: 100 requests/hour for users
        """
        user = request.user
        coupon_code = request.data.get("coupon_code", "").upper().strip()
        cart_total = Decimal(str(request.data.get("cart_total", 0)))
        
        if not coupon_code:
            return Response(
                {"error": "coupon_code is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if cart_total <= 0:
            return Response(
                {"error": "cart_total must be greater than 0."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate and calculate discount
        result = validate_and_calculate_coupon(coupon_code, user, cart_total)
        
        response_data = {
            "success": result['success'],
            "message": result['message'],
            "coupon_code": coupon_code,
            "discount_amount": str(result['discount_amount']),
            "discount_type": result['discount_type'],
            "cart_total": str(cart_total),
            "final_amount": str(result['final_amount'])
        }
        
        # Add discount percentage if percentage type
        if result['discount_type'] == 'percentage' and result['coupon']:
            response_data['discount_percentage'] = float(result['coupon'].discount_value)
        
        status_code = status.HTTP_200_OK if result['success'] else status.HTTP_400_BAD_REQUEST
        return Response(response_data, status=status_code)

    @throttle_classes([UserOrderThrottle(), AnonGeneralThrottle()])
    @action(detail=False, methods=["post"])
    def checkout_summary(self, request):
        """
        Get order summary with all discounts and totals calculated.
        This is a confirmation endpoint before final checkout.
        
        Request body:
        {
            "address_id": 1,
            "coupon_code": "SAVE20",  (optional)
            "tip_amount": 50,
            "preferred_delivery_date": "2026-04-10",
            "preferred_delivery_slot": "9AM-12PM"
        }
        
        Response:
        {
            "success": true,
            "cart_total_before_discount": "500.00",
            "discount_amount": "100.00",
            "discount_type": "percentage",
            "discount_code": "SAVE20",
            "cart_total_after_discount": "400.00",
            "tip_amount": "50.00",
            "final_total": "450.00"
        }
        
        Rate limited: 100 requests/hour for users
        """
        user = request.user
        
        # Validate phone verification
        if not user.phone_number or not user.is_phone_verified:
            return Response(
                {"error": "Only verified users with a phone number can purchase products."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        address_id = request.data.get("address_id")
        coupon_code = request.data.get("coupon_code", "").upper().strip()
        tip_amount = Decimal(str(request.data.get("tip_amount", 0)))
        
        # Validate address
        address = get_object_or_404(UserAddress, id=address_id, user=user)
        
        # Get cart
        try:
            cart = Cart.objects.get(user=user)
            cart_items = list(cart.items.select_related("product").prefetch_related("product__discount_tiers").all())
            if not cart_items:
                return Response({"error": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)
        except Cart.DoesNotExist:
            return Response({"error": "Cart not found."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate stock availability
        stock_errors = []
        for cart_item in cart_items:
            if cart_item.product.stock < cart_item.quantity:
                stock_errors.append({
                    "product_id": cart_item.product.id,
                    "product_name": cart_item.product.name,
                    "requested_quantity": cart_item.quantity,
                    "available_stock": cart_item.product.stock
                })
        
        if stock_errors:
            return Response({
                "error": "Insufficient stock for one or more products.",
                "stock_details": stock_errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Calculate cart total
        cart_total_before = sum(cart_item.subtotal for cart_item in cart_items)
        discount_amount = Decimal('0.00')
        discount_type = None
        cart_total_after = cart_total_before
        
        # Apply coupon if provided
        coupon_message = None
        if coupon_code:
            coupon_result = validate_and_calculate_coupon(coupon_code, user, cart_total_before)
            if coupon_result['success']:
                discount_amount = coupon_result['discount_amount']
                discount_type = coupon_result['discount_type']
                cart_total_after = coupon_result['final_amount']
            else:
                coupon_message = f"Warning: {coupon_result['message']}"
        
        # Calculate delivery charge based on cart total after discount
        delivery_charge = get_delivery_charge(cart_total_after)
        
        # Calculate final total (after discount + delivery charge + tip)
        final_total = cart_total_after + delivery_charge + tip_amount
        
        return Response({
            "success": True,
            "cart_total_before_discount": str(cart_total_before),
            "discount_amount": str(discount_amount),
            "discount_type": discount_type,
            "discount_code": coupon_code if coupon_code else None,
            "coupon_message": coupon_message,
            "cart_total_after_discount": str(cart_total_after),
            "delivery_charge": str(delivery_charge),
            "tip_amount": str(tip_amount),
            "final_total": str(final_total),
            "items_count": len(cart_items)
        })

    @throttle_classes([UserOrderThrottle(), AnonGeneralThrottle()])
    @action(detail=False, methods=["post"])
    @transaction.atomic
    def checkout(self, request):
        """
        Create an order from the current user's cart.
        Validates stock and calculates totals within an atomic transaction.
        
        Rate limited: 100 requests/hour for users
        """
        user = request.user
        
        # Validate phone verification
        if not user.phone_number or not user.is_phone_verified:
            return Response(
                {"error": "Only verified users with a phone number can purchase products. Please verify your phone number to continue."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        address_id = request.data.get("address_id")
        delivery_date = request.data.get("preferred_delivery_date")
        delivery_slot_id = request.data.get("preferred_delivery_slot")
        delivery_notes = request.data.get("delivery_notes")
        payment_method = request.data.get("payment_method", "ZIINA")
        device = request.data.get("device")
        tip_amount = Decimal(str(request.data.get("tip_amount", 0)))
        coupon_code = request.data.get("coupon_code", "").upper().strip()
        
        if tip_amount < 0:
            return Response({"error": "Tip amount cannot be negative."}, status=status.HTTP_400_BAD_REQUEST)
        
        # 0.5. Resolve delivery slot FK
        delivery_slot = None
        if delivery_slot_id:
            try:
                delivery_slot = DeliveryTimeSlot.objects.get(id=delivery_slot_id, is_active=True)
            except DeliveryTimeSlot.DoesNotExist:
                return Response(
                    {"error": "Invalid or inactive delivery time slot."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # 1. Validate Address
        address = get_object_or_404(UserAddress, id=address_id, user=user)
        
        # 2. Get Cart
        try:
            cart = Cart.objects.get(user=user)
            # Optimize query to fetch discount tiers
            cart_items = list(cart.items.select_related("product").prefetch_related("product__discount_tiers").all())
            if not cart_items:
                return Response({"error": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)
        except Cart.DoesNotExist:
            return Response({"error": "Cart not found."}, status=status.HTTP_400_BAD_REQUEST)

        # 2.5. Validate Preferred Delivery Date
        if delivery_date:
            min_delivery_date = get_earliest_delivery_date(cart_items)
            # Convert string to date if necessary (DRF usually handles this but input is from request.data)
            # Assuming YYYY-MM-DD format from frontend
            from datetime import datetime
            try:
                if isinstance(delivery_date, str):
                    parsed_date = datetime.strptime(delivery_date, "%Y-%m-%d").date()
                else:
                    parsed_date = delivery_date
                
                if parsed_date < min_delivery_date:
                    return Response(
                        {"error": f"Preferred delivery date cannot be earlier than {min_delivery_date}."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        # 3. Validate Stock for all items
        stock_errors = []
        for cart_item in cart_items:
            if cart_item.product.stock < cart_item.quantity:
                stock_errors.append({
                    "product_id": cart_item.product.id,
                    "product_name": cart_item.product.name,
                    "requested_quantity": cart_item.quantity,
                    "available_stock": cart_item.product.stock
                })
        
        if stock_errors:
            return Response({
                "error": "Insufficient stock for one or more products.",
                "stock_details": stock_errors
            }, status=status.HTTP_400_BAD_REQUEST)

        # 4. Create Order
        cart_total = sum(cart_item.subtotal for cart_item in cart_items)
        discount_amount = Decimal('0.00')
        coupon = None
        
        # 4.5. Apply Coupon if provided
        if coupon_code:
            coupon_result = validate_and_calculate_coupon(coupon_code, user, cart_total)
            if not coupon_result['success']:
                return Response(
                    {"error": f"Coupon error: {coupon_result['message']}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            discount_amount = coupon_result['discount_amount']
            coupon = coupon_result['coupon']
            cart_total = coupon_result['final_amount']
            
            # Update coupon: mark as invalid and increment used count
            coupon.is_active = False
            coupon.used_count += 1
            coupon.save()
        
        # 4.6. Calculate Delivery Charge
        delivery_charge = get_delivery_charge(cart_total)
        
        # 4.7. Calculate Final Total
        total_amount = cart_total + delivery_charge + tip_amount
        
        order = Order.objects.create(
            user=user,
            shipping_address=address,
            total_amount=total_amount,
            tip_amount=tip_amount,
            coupon=coupon,
            coupon_code=coupon_code if coupon else None,
            discount_amount=discount_amount,
            delivery_charge=delivery_charge,
            status=Order.OrderStatus.PENDING,
            preferred_delivery_date=delivery_date,
            preferred_delivery_slot=delivery_slot,
            delivery_notes=delivery_notes
        )

        # 5. Create Order Items (Snapshots)
        order_items = []
        for cart_item in cart_items:
            order_items.append(OrderItem(
                order=order,
                product=cart_item.product,
                product_name=cart_item.product.name,
                quantity=cart_item.quantity,
                price=cart_item.unit_price
            ))
        OrderItem.objects.bulk_create(order_items)

        # 5.5. Reduce Stock
        for item in order.items.all():
            product = item.product
            if product:
                product.stock -= item.quantity
                if product.stock < 0:
                    product.stock = 0
                product.save()

        # 6. Handle Payment
        if payment_method == "COD":
            Payment.objects.create(
                order=order,
                amount=order.total_amount,
                status=Payment.PaymentStatus.PENDING,
                payment_method=Payment.PaymentMethod.COD
            )
            # Clear Cart (Items only, keep the cart object)
            cart.items.all().delete()
            
            return Response({
                "message": "Order created successfully. Please pay upon delivery.",
                "order_id": order.id,
                "total_amount": order.total_amount,
                "payment_method": "COD"
            }, status=status.HTTP_201_CREATED)
        
        else:
            # Create Ziina Payment Intent
            use_app_urls = bool(device and str(device).strip().lower() in ("mobile", "android", "ios"))
            try:
                payment_data = ZiinaPaymentService.create_payment_intent(order, use_app_urls=use_app_urls)
            except Exception as e:
                logger.error(f"Ziina payment intent creation failed for Order #{order.id}: {e}")
                return Response(
                    {"error": "Payment gateway error. Please try again."},
                    status=status.HTTP_502_BAD_GATEWAY
                )

            Payment.objects.create(
                order=order,
                ziina_payment_intent_id=payment_data["payment_intent_id"],
                amount=order.total_amount,
                status=Payment.PaymentStatus.PENDING,
                payment_method=Payment.PaymentMethod.ZIINA
            )

            # Clear Cart (Items only, keep the cart object)
            cart.items.all().delete()

            return Response({
                "message": "Order created successfully.",
                "order_id": order.id,
                "payment_url": payment_data["redirect_url"],
                "total_amount": order.total_amount,
                "payment_method": "ZIINA"
            }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def admin_update_status(self, request, pk=None):
        """
        Allows an admin to manually update the order status.
        Useful for marking orders as Shipped, Delivered, etc.
        When status is changed to PAID, coupon usage is incremented (for COD orders).
        """
        order = self.get_object()
        new_status = request.data.get("status")
        notes = request.data.get("notes", f"Status manually updated by admin.")

        if new_status not in Order.OrderStatus.values:
            return Response(
                {"error": f"Invalid status. Choose from: {Order.OrderStatus.values}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        old_status = order.status
        order.status = new_status
        order.save()
        
        # Update status history notes
        latest_history = order.status_history.last()
        if latest_history and latest_history.status == new_status:
            latest_history.notes = notes
            latest_history.save()

        return Response({"message": f"Order status updated to {new_status}."})


    @throttle_classes([UserPaymentThrottle(), AnonGeneralThrottle()])
    @action(detail=True, methods=["post"])
    @transaction.atomic
    def verify_payment(self, request, pk=None):
        """
        Verify payment status with Ziina.
        Checks the payment intent status via Ziina API.
        
        Rate limited: 30 requests/hour for users (fraud prevention)
        """
        order = self.get_object()
        payment = getattr(order, "payment", None)
        
        if not payment:
            return Response({"error": "Payment record not found."}, status=status.HTTP_404_NOT_FOUND)
            
        if payment.status != Payment.PaymentStatus.PENDING:
            return Response({"error": "Payment is not in pending status."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ziina_data = ZiinaPaymentService.get_payment_intent(payment.ziina_payment_intent_id)
        except Exception as e:
            logger.error(f"Ziina verify_payment failed for Order #{order.id}: {e}")
            return Response(
                {"error": "Unable to verify payment. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY
            )

        ziina_status = ziina_data.get("status", "").upper()

        if ziina_status == "COMPLETED":
            # 1. Update Payment Status (This triggers signal handle_payment_success)
            payment.status = Payment.PaymentStatus.SUCCESS
            payment.transaction_id = ziina_data.get("id")
            payment.provider_response = ziina_data
            payment.save()

            return Response({"message": "Payment verified, order updated, and receipt generated."})
        
        if ziina_status in ("FAILED", "EXPIRED", "CANCELLED"):
            payment.status = Payment.PaymentStatus.FAILED
            payment.provider_response = ziina_data
            payment.save()
            return Response({"error": "Payment verification failed."}, status=status.HTTP_400_BAD_REQUEST)

        # Still pending
        return Response({"message": "Payment is still being processed.", "status": ziina_status})

    @throttle_classes([UserPaymentThrottle(), AnonGeneralThrottle()])
    @action(detail=True, methods=["post"])
    @transaction.atomic
    def retry_payment(self, request, pk=None):
        """
        Retry payment for an order whose payment failed, expired, or was cancelled.
        Creates a new Ziina payment intent and returns the new payment link.
        
        Rate limited: 30 requests/hour for users (fraud prevention)
        """
        order = self.get_object()

        if order.status != Order.OrderStatus.PENDING:
            return Response(
                {"error": "Only pending orders can retry payment."},
                status=status.HTTP_400_BAD_REQUEST
            )

        payment = getattr(order, "payment", None)
        if not payment:
            return Response({"error": "Payment record not found."}, status=status.HTTP_404_NOT_FOUND)

        if payment.status == Payment.PaymentStatus.SUCCESS:
            return Response(
                {"error": "Payment already completed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if payment.status == Payment.PaymentStatus.PENDING:
            # Check with Ziina if it's actually still valid
            try:
                ziina_data = ZiinaPaymentService.get_payment_intent(payment.ziina_payment_intent_id)
                ziina_status = ziina_data.get("status", "").upper()

                if ziina_status not in ("FAILED", "EXPIRED", "CANCELLED"):
                    # Still active — return the existing redirect URL
                    return Response({
                        "message": "Payment is still active.",
                        "order_id": order.id,
                        "payment_url": ziina_data.get("redirect_url"),
                        "total_amount": str(order.total_amount),
                    })
                # Mark as failed so we can create a new one
                payment.status = Payment.PaymentStatus.FAILED
                payment.provider_response = ziina_data
                payment.save()
            except Exception as e:
                logger.error(f"Ziina status check failed during retry for Order #{order.id}: {e}")

        # Create a new Ziina payment intent
        try:
            payment_data = ZiinaPaymentService.create_payment_intent(order)
        except Exception as e:
            logger.error(f"Ziina retry payment intent creation failed for Order #{order.id}: {e}")
            return Response(
                {"error": "Payment gateway error. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY
            )

        # Update the existing payment record with the new intent
        payment.ziina_payment_intent_id = payment_data["payment_intent_id"]
        payment.status = Payment.PaymentStatus.PENDING
        payment.provider_response = None
        payment.save()

        logger.info(f"Retry payment: new Ziina intent {payment_data['payment_intent_id']} for Order #{order.id}")

        return Response({
            "message": "New payment link generated.",
            "order_id": order.id,
            "payment_url": payment_data["redirect_url"],
            "total_amount": str(order.total_amount),
            "payment_method": "ZIINA"
        })

    @action(detail=True, methods=["post"])
    def cancel_order(self, request, pk=None):
        """Cancel a pending order and restore stock."""
        order = self.get_object()
        if order.status == Order.OrderStatus.PENDING:
            # Restore stock for all items in the order
            for item in order.items.all():
                product = item.product
                if product:
                    product.stock += item.quantity
                    product.save()
            
            order.status = Order.OrderStatus.CANCELLED
            order.save()
            return Response({"message": "Order cancelled and stock restored."})
        return Response({"error": "Only pending orders can be cancelled."}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"])
    def receipt_image(self, request, pk=None):
        """
        Generate a simple image receipt for a successful payment.
        """
        order = self.get_object()
        payment = getattr(order, "payment", None)

        if not payment or payment.status != Payment.PaymentStatus.SUCCESS:
            return Response(
                {"error": "Receipt is available only for successful payments."},
                status=status.HTTP_400_BAD_REQUEST
            )

        receipt = getattr(payment, "receipt", None)
        if not receipt:
            return Response(
                {"error": "Receipt not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        buffer = render_receipt_image(order, receipt)
        return HttpResponse(buffer.getvalue(), content_type="image/png")

    @action(detail=True, methods=["get"])
    def receipt_pdf(self, request, pk=None):
        order = self.get_object()
        payment = getattr(order, "payment", None)

        if not payment or payment.status != Payment.PaymentStatus.SUCCESS:
            return Response(
                {"error": "Receipt is available only for successful payments."},
                status=status.HTTP_400_BAD_REQUEST
            )

        receipt = getattr(payment, "receipt", None)
        if not receipt:
            return Response(
                {"error": "Receipt not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        buffer = render_receipt_pdf(order, receipt)
        response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="receipt_{receipt.receipt_number}.pdf"'
        return response

    @action(detail=True, methods=["get"], permission_classes=[permissions.IsAdminUser])
    def admin_receipt_pdf(self, request, pk=None):
        """
        Generate a detailed PDF receipt for admin use with all order details and QR code.
        """
        order = self.get_object()

        buffer = render_admin_receipt_pdf(order)
        response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="order_receipt_{order.id}.pdf"'
        return response

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAdminUser])
    def orders_count(self, request):
        """
        Get a summary of order counts by status.
        Returns: total orders, processing, shipped, delivered counts.
        """
        orders_qs = Order.objects.all()
        total_orders = orders_qs.count()
        
        processing = orders_qs.filter(status=Order.OrderStatus.PROCESSING).count()
        shipped = orders_qs.filter(status=Order.OrderStatus.SHIPPED).count()
        delivered = orders_qs.filter(status=Order.OrderStatus.DELIVERED).count()
        
        total_revenue = Payment.objects.filter(status=Payment.PaymentStatus.SUCCESS).aggregate(
            total=Sum("amount")
        )["total"] or 0
        
        return Response({
            "total_orders": total_orders,
            "processing": processing,
            "shipped": shipped,
            "delivered": delivered,
            "total_revenue": str(total_revenue)
        })

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAdminUser])
    def dashboard_analytics(self, request):
        now = timezone.now()
        last_7_days = now - timedelta(days=7)
        last_30_days = now - timedelta(days=30)

        users_qs = User.objects.filter(deleted_at__isnull=True)
        total_users = users_qs.count()
        new_users_last_7_days = users_qs.filter(created_at__gte=last_7_days).count()
        active_users_last_30_days = users_qs.filter(last_login_at__gte=last_30_days).count()
        email_verified = users_qs.filter(is_email_verified=True).count()
        phone_verified = users_qs.filter(is_phone_verified=True).count()

        orders_qs = Order.objects.all()
        total_orders = orders_qs.count()
        orders_by_status = list(
            orders_qs.values("status").annotate(count=Count("id")).order_by("status")
        )
        paid_orders_qs = orders_qs.filter(status=Order.OrderStatus.PAID)
        paid_last_30_days = paid_orders_qs.filter(created_at__gte=last_30_days).count()
        avg_order_value = paid_orders_qs.aggregate(avg=Avg("total_amount"))["avg"] or 0

        payments_success_qs = Payment.objects.filter(
            status=Payment.PaymentStatus.SUCCESS
        )
        revenue_total = (
            payments_success_qs.aggregate(total=Sum("amount"))["total"] or 0
        )
        revenue_last_30_days = (
            payments_success_qs.filter(created_at__gte=last_30_days).aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )
        revenue_per_day_qs = (
            payments_success_qs.filter(created_at__gte=last_30_days)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(total=Sum("amount"))
            .order_by("day")
        )
        revenue_per_day = [
            {"date": row["day"].isoformat(), "total_amount": str(row["total"])}
            for row in revenue_per_day_qs
        ]

        top_products_qs = (
            OrderItem.objects.filter(
                order__status=Order.OrderStatus.PAID, product__isnull=False
            )
            .values("product_id", "product_name")
            .annotate(
                total_quantity=Sum("quantity"),
                total_revenue=Sum(F("price") * F("quantity")),
            )
            .order_by("-total_revenue")[:10]
        )
        top_products = [
            {
                "product_id": row["product_id"],
                "name": row["product_name"],
                "total_quantity": row["total_quantity"],
                "total_revenue": str(row["total_revenue"]),
            }
            for row in top_products_qs
        ]

        carts_qs = Cart.objects.all()
        total_carts = carts_qs.count()
        cart_items_qs = CartItem.objects.all()
        total_cart_items = (
            cart_items_qs.aggregate(total=Sum("quantity"))["total"] or 0
        )
        total_cart_value = (
            cart_items_qs.aggregate(
                total=Sum(F("product__final_price") * F("quantity"))
            )["total"]
            or 0
        )
        avg_cart_value = (
            total_cart_value / total_carts if total_carts and total_cart_value else 0
        )
        avg_cart_items = (
            float(total_cart_items) / float(total_carts)
            if total_carts and total_cart_items
            else 0
        )

        reviews_qs = Review.objects.filter(
            is_visible=True, deleted_at__isnull=True
        )
        total_reviews = reviews_qs.count()
        avg_rating = reviews_qs.aggregate(avg=Avg("rating"))["avg"] or 0
        reviews_by_rating = list(
            reviews_qs.values("rating")
            .annotate(count=Count("id"))
            .order_by("rating")
        )

        data = {
            "users": {
                "total": total_users,
                "new_last_7_days": new_users_last_7_days,
                "active_last_30_days": active_users_last_30_days,
                "email_verified": email_verified,
                "phone_verified": phone_verified,
            },
            "orders": {
                "total": total_orders,
                "by_status": orders_by_status,
                "paid_last_30_days": paid_last_30_days,
                "avg_order_value": str(avg_order_value),
            },
            "revenue": {
                "total": str(revenue_total),
                "last_30_days": str(revenue_last_30_days),
                "per_day": revenue_per_day,
            },
            "top_products": top_products,
            "cart": {
                "total_carts": total_carts,
                "total_cart_items": total_cart_items,
                "avg_cart_value": str(avg_cart_value),
                "avg_cart_items": avg_cart_items,
            },
            "reviews": {
                "total": total_reviews,
                "avg_rating": avg_rating,
                "by_rating": reviews_by_rating,
            },
        }
        return Response(data)

    @action(detail=False, methods=["get"])
    def estimate_delivery(self, request):
        """
        Calculate the estimated delivery date for the items in the user's cart.
        Returns the earliest possible delivery date for the entire order.
        """
        user = request.user
        try:
            cart = Cart.objects.get(user=user)
            cart_items = list(cart.items.select_related("product").all())
            if not cart_items:
                return Response({"error": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)
        except Cart.DoesNotExist:
            return Response({"error": "Cart not found."}, status=status.HTTP_404_NOT_FOUND)

        # Validate stock availability
        stock_errors = []
        for cart_item in cart_items:
            if cart_item.product.stock < cart_item.quantity:
                stock_errors.append({
                    "product_id": cart_item.product.id,
                    "product_name": cart_item.product.name,
                    "requested_quantity": cart_item.quantity,
                    "available_stock": cart_item.product.stock
                })
        
        if stock_errors:
            return Response({
                "error": "Insufficient stock for one or more products.",
                "stock_details": stock_errors
            }, status=status.HTTP_400_BAD_REQUEST)

        max_days, details = calculate_delivery_estimate(cart_items)
        estimated_date = timezone.now().date() + timedelta(days=max_days)
        
        return Response({
            "estimated_delivery_date": estimated_date,
            "max_delivery_days": max_days,
            "details": details
        })

    @action(detail=False, methods=["get", "post"])
    def delivery_charge_settings(self, request):
        """
        Endpoint to view delivery charge settings.
        
        GET: Retrieve current delivery charge configuration (authenticated users)
        POST: Update delivery charge configuration (admin only)
        
        Request body (POST):
        {
            "min_free_shipping_amount": 40.00,
            "delivery_charge": 10.00,
            "is_active": true
        }
        
        Response:
        {
            "min_free_shipping_amount": "40.00",
            "delivery_charge": "10.00",
            "is_active": true,
            "message": "Configuration retrieved/updated successfully"
        }
        """
        if request.method == "POST" and not request.user.is_staff:
            return Response(
                {"error": "Admin privileges required to update delivery charge settings."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        config = DeliveryChargeConfig.get_config()
        
        if request.method == "GET":
            return Response({
                "min_free_shipping_amount": str(config.min_free_shipping_amount),
                "delivery_charge": str(config.delivery_charge),
                "is_active": config.is_active,
                "updated_at": config.updated_at,
                "message": "Current delivery charge configuration"
            })
        
        elif request.method == "POST":
            # Update configuration
            min_free = request.data.get("min_free_shipping_amount")
            charge = request.data.get("delivery_charge")
            is_active = request.data.get("is_active")
            
            if min_free is not None:
                try:
                    config.min_free_shipping_amount = Decimal(str(min_free))
                except (ValueError, TypeError):
                    return Response(
                        {"error": "min_free_shipping_amount must be a valid decimal"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            if charge is not None:
                try:
                    config.delivery_charge = Decimal(str(charge))
                except (ValueError, TypeError):
                    return Response(
                        {"error": "delivery_charge must be a valid decimal"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            if is_active is not None:
                config.is_active = bool(is_active)
            
            config.updated_by = request.user
            config.save()
            
            return Response({
                "min_free_shipping_amount": str(config.min_free_shipping_amount),
                "delivery_charge": str(config.delivery_charge),
                "is_active": config.is_active,
                "updated_at": config.updated_at,
                "message": "Delivery charge configuration updated successfully"
            }, status=status.HTTP_200_OK)


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Admin-only ViewSet for viewing payment details.
    Allows admins to:
    - List all payments with customer, order, and transaction info
    - View detailed payment information
    - Filter by payment status, method, date range, order status
    - Search by customer email, phone, or order ID
    """
    serializer_class = AdminPaymentSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        'status',
        'payment_method',
        'order__status',
        'created_at',
    ]
    search_fields = [
        'order__user__email',
        'order__user__phone_number',
        'order__id',
        'transaction_id',
    ]
    ordering_fields = [
        'created_at',
        'amount',
        'status',
    ]
    ordering = ['-created_at']

    def get_queryset(self):
        """Return all payments with optimized queries."""
        return Payment.objects.select_related(
            'order',
            'order__user'
        ).order_by('-created_at')

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, permissions.IsAdminUser])
    def create_refund(self, request, pk=None):
        """
        Create a refund for a payment. Admin-only endpoint.
        POST /api/orders/payments/{id}/create_refund/
        Body: {"amount_fils": 1000, "currency_code": "AED"} (optional amount_fils for partial refund)
        """
        payment = self.get_object()

        # Validate payment exists and is successful
        if payment.status.lower() not in ['success', 'paid']:
            return Response(
                {"error": "Can only refund successful payments"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if payment already has a refund
        if hasattr(payment, 'refund_id') and payment.refund_id:
            return Response(
                {"error": "Payment already has a refund"},
                status=status.HTTP_400_BAD_REQUEST
            )

        amount_fils = request.data.get('amount_fils')
        currency_code = request.data.get('currency_code', 'AED')

        try:
            # Create refund via Ziina
            refund_data = ZiinaPaymentService.create_refund(
                payment_intent_id=payment.transaction_id,
                amount_fils=amount_fils,
                currency_code=currency_code
            )

            # Store refund ID in payment record
            payment.refund_id = refund_data.get('id')
            payment.save(update_fields=['refund_id'])

            return Response({
                "message": "Refund initiated successfully",
                "refund_id": refund_data.get('id'),
                "status": refund_data.get('status'),
                "amount": refund_data.get('amount'),
                "currency": refund_data.get('currency_code')
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"error": f"Failed to create refund: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated, permissions.IsAdminUser])
    def refund_status(self, request, pk=None):
        """
        Get the status of a refund for a payment. Admin-only endpoint.
        GET /api/orders/payments/{id}/refund_status/
        """
        payment = self.get_object()

        if not hasattr(payment, 'refund_id') or not payment.refund_id:
            return Response(
                {"error": "No refund found for this payment"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            # Get refund status from Ziina
            refund_data = ZiinaPaymentService.get_refund(payment.refund_id)

            return Response({
                "refund_id": payment.refund_id,
                "status": refund_data.get('status'),
                "amount": refund_data.get('amount'),
                "currency": refund_data.get('currency_code'),
                "created_at": refund_data.get('created_at'),
                "processed_at": refund_data.get('processed_at'),
                "reason": refund_data.get('reason')
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": f"Failed to get refund status: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================================
# WEBHOOK HANDLERS
# ============================================================================

def verify_webhook_signature(request_body, signature, webhook_secret):
    """
    Verify the authenticity of a webhook request using HMAC-SHA256.
    
    Args:
        request_body: Raw request body (bytes)
        signature: Signature from the X-Webhook-Signature header
        webhook_secret: Secret key configured for the webhook
    
    Returns:
        bool: True if signature is valid, False otherwise
    """
    try:
        # Create HMAC signature
        expected_signature = hmac.new(
            webhook_secret.encode(),
            request_body,
            hashlib.sha256
        ).hexdigest()
        
        # Use constant-time comparison to prevent timing attacks
        return hmac.compare_digest(signature, expected_signature)
    except Exception as e:
        webhook_logger.error(f"Webhook signature verification error: {e}")
        return False


@csrf_exempt
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@transaction.atomic
def ziina_webhook(request):
    """
    Webhook endpoint to receive real-time payment status updates from Ziina.
    
    Handles the 'payment_intent.status.updated' event.
    Verifies webhook authenticity using HMAC-SHA256 if secret is configured.
    
    Webhook Payload Structure:
    {
        "event": "payment_intent.status.updated",
        "data": {
            "id": "<payment_intent_id>",
            "status": "COMPLETED|FAILED|EXPIRED|CANCELLED",
            "amount": <amount_in_fils>,
            "currency_code": "AED",
            ...
        }
    }
    
    Response:
    {
        "success": true,
        "message": "Webhook processed successfully"
    }
    """
    try:
        # Get request body for signature verification
        request_body = request.body
        
        # Get webhook signature from header
        signature = request.headers.get('X-Webhook-Signature', '')
        
        # Parse JSON payload
        try:
            payload = json.loads(request_body.decode('utf-8'))
        except (ValueError, AttributeError) as e:
            webhook_logger.error(f"Invalid webhook payload: {e}")
            return JsonResponse({
                "success": False,
                "error": "Invalid JSON payload"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify signature if webhook secret is configured
        webhook_secret = getattr(settings, 'ZIINA_WEBHOOK_SECRET', None)
        if webhook_secret:
            if not signature:
                webhook_logger.warning("Webhook signature missing but secret is configured")
                return JsonResponse({
                    "success": False,
                    "error": "Signature required"
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            if not verify_webhook_signature(request_body, signature, webhook_secret):
                webhook_logger.warning("Webhook signature verification failed")
                return JsonResponse({
                    "success": False,
                    "error": "Invalid signature"
                }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Extract event and data
        event = payload.get('event')
        data = payload.get('data', {})
        
        # Only handle payment_intent.status.updated events
        if event != 'payment_intent.status.updated':
            webhook_logger.info(f"Ignoring webhook event: {event}")
            return JsonResponse({
                "success": True,
                "message": f"Event {event} not handled"
            }, status=status.HTTP_200_OK)
        
        # Extract payment intent ID and status
        payment_intent_id = data.get('id')
        ziina_status = data.get('status', '').upper()
        
        if not payment_intent_id:
            webhook_logger.error("Webhook missing payment_intent_id")
            return JsonResponse({
                "success": False,
                "error": "Missing payment_intent_id"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not ziina_status:
            webhook_logger.error("Webhook missing status")
            return JsonResponse({
                "success": False,
                "error": "Missing status"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Find the payment record by Ziina payment intent ID
        try:
            payment = Payment.objects.get(ziina_payment_intent_id=payment_intent_id)
        except Payment.DoesNotExist:
            webhook_logger.warning(f"Payment not found for intent ID: {payment_intent_id}")
            return JsonResponse({
                "success": False,
                "error": "Payment intent not found"
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Update payment status based on Ziina status
        old_status = payment.status
        
        if ziina_status == "COMPLETED":
            payment.status = Payment.PaymentStatus.SUCCESS
            payment.transaction_id = data.get('id')
        elif ziina_status in ("FAILED", "EXPIRED", "CANCELLED"):
            payment.status = Payment.PaymentStatus.FAILED
        else:
            # Unknown status, log but don't change
            webhook_logger.warning(f"Unknown Ziina status: {ziina_status}")
            return JsonResponse({
                "success": False,
                "error": f"Unknown status: {ziina_status}"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Store the full provider response for audit trail
        payment.provider_response = data
        payment.save()
        
        webhook_logger.info(
            f"Webhook processed: Payment #{payment.id} (Order #{payment.order.id}) "
            f"status updated from {old_status} to {payment.status}"
        )
        
        return JsonResponse({
            "success": True,
            "message": "Webhook processed successfully",
            "payment_id": payment.id,
            "order_id": payment.order.id,
            "status": payment.status
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        webhook_logger.error(f"Webhook processing error: {e}", exc_info=True)
        return JsonResponse({
            "success": False,
            "error": "Internal server error"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeliveryTimeSlotViewSet(viewsets.ModelViewSet):
    """
    Admin-only ViewSet for managing delivery timeslots.
    Regular users get a read-only view of available slots via the
    `available` action: GET /api/orders/delivery-slots/available/?date=YYYY-MM-DD
    """
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name']
    ordering_fields = ['sort_order', 'start_time', 'created_at']
    ordering = ['sort_order', 'start_time']

    def get_queryset(self):
        return DeliveryTimeSlot.objects.all()

    def get_serializer_class(self):
        if self.request.user.is_staff:
            return AdminDeliveryTimeSlotSerializer
        return DeliveryTimeSlotSerializer

    def get_permissions(self):
        if self.action in ['available']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), permissions.IsAdminUser()]

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a timeslot globally."""
        slot = self.get_object()
        slot.is_active = True
        slot.save(update_fields=['is_active'])
        return Response({"detail": "Timeslot activated.", "is_active": True}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a timeslot globally."""
        slot = self.get_object()
        slot.is_active = False
        slot.save(update_fields=['is_active'])
        return Response({"detail": "Timeslot deactivated.", "is_active": False}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def available(self, request):
        """
        Returns available delivery timeslots for a given date.
        Filters by: global active, per-date override, cutoff time (for today).

        Query param:
          - date (optional, YYYY-MM-DD) -- defaults to today (UAE timezone)
        """
        now_uae = timezone.now().astimezone(UAE_TZ)

        date_param = request.query_params.get('date')
        if date_param:
            try:
                target_date = datetime.date.fromisoformat(date_param)
            except ValueError:
                return Response(
                    {"detail": "Invalid date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            target_date = now_uae.date()

        # Reject past dates
        if target_date < now_uae.date():
            return Response({"detail": "Cannot select a past date.", "available_slots": []}, status=status.HTTP_400_BAD_REQUEST)

        all_active_slots = DeliveryTimeSlot.objects.filter(is_active=True).order_by('sort_order', 'start_time')

        # Fetch all overrides for this date in one query
        overrides = {
            o.slot_id: o.is_active
            for o in DeliverySlotOverride.objects.filter(date=target_date)
        }

        available = []
        for slot in all_active_slots:
            # Per-date override takes priority
            if slot.id in overrides:
                if not overrides[slot.id]:
                    continue  # override says inactive for this date
            # For today: check cutoff time
            if target_date == now_uae.date():
                if now_uae.time() >= slot.cutoff_time:
                    continue  # cutoff passed, skip
            available.append(slot)

        serializer = DeliveryTimeSlotSerializer(available, many=True)
        return Response({
            "date": target_date.isoformat(),
            "available_slots": serializer.data,
        }, status=status.HTTP_200_OK)


class DeliverySlotOverrideViewSet(viewsets.ModelViewSet):
    """
    Admin-only ViewSet for per-date slot availability overrides.
    Use this to disable/enable a specific slot on a specific date
    (e.g. disable 8-9 AM on a holiday or when no drivers are available).
    """
    serializer_class = DeliverySlotOverrideSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['slot', 'date', 'is_active']
    ordering_fields = ['date', 'slot__sort_order']
    ordering = ['date', 'slot__sort_order']

    def get_queryset(self):
        return DeliverySlotOverride.objects.select_related('slot').all()
