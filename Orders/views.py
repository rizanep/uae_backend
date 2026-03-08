from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Count, Sum, Avg, F
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from .models import Order, OrderItem, Payment, Receipt
from .serializers import OrderSerializer
from Cart.models import Cart, CartItem
from Users.models import UserAddress, User
from Reviews.models import Review
from .payment_service import TelrPaymentService
from .receipt_templates import render_receipt_image, render_receipt_pdf, render_admin_receipt_pdf
from .utils import calculate_delivery_estimate, get_earliest_delivery_date
import re

class OrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user orders.
    Supports checkout from cart and payment simulation.
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Order.objects.none()
        qs = Order.objects.select_related(
            "user", "shipping_address", "payment", "payment__receipt"
        ).prefetch_related("items", "status_history")
        if user.role == "admin":
            return qs
        return qs.filter(user=user)

    @action(detail=False, methods=["post"])
    @transaction.atomic
    def checkout(self, request):
        """
        Create an order from the current user's cart.
        Validates stock and calculates totals within an atomic transaction.
        """
        user = request.user
        address_id = request.data.get("address_id")
        delivery_date = request.data.get("preferred_delivery_date")
        delivery_slot = request.data.get("preferred_delivery_slot")
        delivery_notes = request.data.get("delivery_notes")
        payment_method = request.data.get("payment_method", "TELR")
        tip_amount = Decimal(str(request.data.get("tip_amount", 0)))
        
        if tip_amount < 0:
            return Response({"error": "Tip amount cannot be negative."}, status=status.HTTP_400_BAD_REQUEST)
        
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
        for cart_item in cart_items:
            if cart_item.product.stock < cart_item.quantity:
                return Response(
                    {"error": f"Insufficient stock for {cart_item.product.name}."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # 4. Create Order
        cart_total = sum(cart_item.subtotal for cart_item in cart_items)
        total_amount = cart_total + tip_amount
        
        order = Order.objects.create(
            user=user,
            shipping_address=address,
            total_amount=total_amount,
            tip_amount=tip_amount,
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
            # Create Pending Payment (Telr)
            payment_data = TelrPaymentService.initiate_payment(order)
            Payment.objects.create(
                order=order,
                telr_reference=payment_data["reference"],
                amount=order.total_amount,
                status=Payment.PaymentStatus.PENDING,
                payment_method=Payment.PaymentMethod.TELR
            )

            # Clear Cart (Items only, keep the cart object)
            cart.items.all().delete()

            return Response({
                "message": "Order created successfully.",
                "order_id": order.id,
                "payment_url": payment_data["payment_url"],
                "total_amount": order.total_amount,
                "payment_method": "TELR"
            }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def admin_update_status(self, request, pk=None):
        """
        Allows an admin to manually update the order status.
        Useful for marking orders as Shipped, Delivered, etc.
        """
        order = self.get_object()
        new_status = request.data.get("status")
        notes = request.data.get("notes", f"Status manually updated by admin.")

        if new_status not in Order.OrderStatus.values:
            return Response(
                {"error": f"Invalid status. Choose from: {Order.OrderStatus.values}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.status = new_status
        order.save()
        
        # We can also add custom notes to the history here if needed
        # The signal handles the basic history, but we can update the notes of the latest entry
        latest_history = order.status_history.last()
        if latest_history and latest_history.status == new_status:
            latest_history.notes = notes
            latest_history.save()

        return Response({"message": f"Order status updated to {new_status}."})

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def verify_payment(self, request, pk=None):
        """
        Simulate payment verification.
        In production, this would be a webhook from Telr.
        Updates payment status, order status, and reduces product stock.
        """
        order = self.get_object()
        payment = getattr(order, "payment", None)
        
        if not payment:
            return Response({"error": "Payment record not found."}, status=status.HTTP_404_NOT_FOUND)
            
        if payment.status != Payment.PaymentStatus.PENDING:
            return Response({"error": "Payment is not in pending status."}, status=status.HTTP_400_BAD_REQUEST)

        # Mock verification
        verification_result = TelrPaymentService.verify_payment(payment.telr_reference)
        
        if verification_result["status"] == "SUCCESS":
            # 1. Update Payment Status (This triggers signal handle_payment_success)
            payment.status = Payment.PaymentStatus.SUCCESS
            payment.transaction_id = verification_result["transaction_id"]
            payment.provider_response = verification_result
            payment.save()

            # 2. Reduce Stock
            for item in order.items.all():
                product = item.product
                if product:
                    product.stock -= item.quantity
                    if product.stock < 0:
                        product.stock = 0
                    product.save()

            return Response({"message": "Payment verified, order updated, and receipt generated."})
        
        # Handle failure
        payment.status = Payment.PaymentStatus.FAILED
        payment.save()
        return Response({"error": "Payment verification failed."}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def cancel_order(self, request, pk=None):
        """Cancel a pending order."""
        order = self.get_object()
        if order.status == Order.OrderStatus.PENDING:
            order.status = Order.OrderStatus.CANCELLED
            order.save()
            return Response({"message": "Order cancelled."})
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

        max_days, details = calculate_delivery_estimate(cart_items)
        estimated_date = timezone.now().date() + timedelta(days=max_days)
        
        return Response({
            "estimated_delivery_date": estimated_date,
            "max_delivery_days": max_days,
            "details": details
        })
