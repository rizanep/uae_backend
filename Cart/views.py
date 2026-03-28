from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Prefetch
from django.utils import timezone
from datetime import timedelta
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer
from Products.models import Product
from Products.delivery_models import ProductDeliveryTier
from Reviews.models import Review

# Optimize ProductDeliveryTier queryset for prefetch
def get_optimized_delivery_tiers():
    return ProductDeliveryTier.objects.all().order_by('-min_quantity')

class CartViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing the user's shopping cart.
    Users can only access their own cart.
    """
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = "__all__"

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user).prefetch_related(
            Prefetch(
                "items",
                queryset=CartItem.objects.select_related("product", "product__category").prefetch_related(
                    "product__images",
                    "product__videos",
                    Prefetch("product__reviews", queryset=Review.objects.filter(is_visible=True)),
                ),
            )
        )

    def get_object(self):
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        return self.get_queryset().get(pk=cart.pk)

    @action(detail=False, methods=["get"])
    def my_cart(self, request):
        """Retrieve the current user's cart."""
        cart = self.get_object()
        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def add_item(self, request):
        """Add a product to the cart or update quantity if it exists."""
        cart = self.get_object()
        product_id = request.data.get("product")
        quantity = int(request.data.get("quantity", 1))

        try:
            product = Product.objects.get(id=product_id, is_available=True)
        except Product.DoesNotExist:
            return Response(
                {"error": "Product not found or unavailable."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check stock
        if product.stock < quantity:
            return Response(
                {"error": f"Only {product.stock} items in stock."},
                status=status.HTTP_400_BAD_REQUEST
            )

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={"quantity": quantity}
        )

        if not created:
            cart_item.quantity += quantity
            # Re-check stock after increment
            if product.stock < cart_item.quantity:
                return Response(
                    {"error": f"Cannot add more. Only {product.stock} items in stock."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            cart_item.save()

        return Response(
            {"message": "Item added to cart."},
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=["get"])
    def delivery_options(self, request):
        """
        Calculate available delivery dates and slots based on cart items.
        Logic:
        1. Find the required delivery days (lead time) for each item based on quantity tiers.
        2. Take the maximum lead time among all items.
        3. Generate available dates starting from today + max_lead_time.
        """
        cart = self.get_object()
        items = cart.items.select_related('product').prefetch_related('product__delivery_tiers').all()
        
        if not items.exists():
            return Response(
                {"error": "Cart is empty"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        max_lead_days = 0
        details = []
        today = timezone.now().date()
        
        for item in items:
            # Find applicable tier (use prefetched data)
            tier = None
            for t in item.product.delivery_tiers.all():
                if t.min_quantity <= item.quantity:
                    tier = t
                    break
            
            if tier:
                lead_days = tier.delivery_days
                reason = f"Tier: Qty >= {tier.min_quantity}"
            else:
                # Default logic if no tier matches
                lead_days = 1 
                reason = "Default (No matching tier)"
                
            if lead_days > max_lead_days:
                max_lead_days = lead_days
                
            details.append({
                "product": item.product.name,
                "quantity": item.quantity,
                "lead_days": lead_days,
                "reason": reason
            })
            
        # Calculate dates
        start_date = today + timedelta(days=max_lead_days)
        
        # Generate next 7 available days
        available_dates = []
        for i in range(7):
            current_date = start_date + timedelta(days=i)
            available_dates.append({
                "date": current_date.isoformat(),
                "day_name": current_date.strftime("%A"),
                "slots": [
                    {"id": "morning", "label": "09:00 AM - 12:00 PM"},
                    {"id": "afternoon", "label": "02:00 PM - 05:00 PM"},
                    {"id": "evening", "label": "06:00 PM - 09:00 PM"},
                ]
            })
            
        return Response({
            "max_lead_days": max_lead_days,
            "earliest_delivery_date": start_date.isoformat(),
            "available_dates": available_dates,
            "item_details": details
        })

    @action(detail=False, methods=["post"])
    def update_item_quantity(self, request):
        """Update the quantity of an item already in the cart."""
        cart = self.get_object()
        product_id = request.data.get("product")
        quantity = int(request.data.get("quantity"))

        if quantity < 1:
            return Response(
                {"error": "Quantity must be at least 1."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            cart_item = CartItem.objects.get(cart=cart, product_id=product_id)
            # Check stock
            if cart_item.product.stock < quantity:
                return Response(
                    {"error": f"Only {cart_item.product.stock} items in stock."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            cart_item.quantity = quantity
            cart_item.save()
            return Response({"message": "Quantity updated."})
        except CartItem.DoesNotExist:
            return Response(
                {"error": "Item not found in cart."},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=["post"])
    def remove_item(self, request):
        """Remove an item from the cart."""
        cart = self.get_object()
        product_id = request.data.get("product")

        try:
            cart_item = CartItem.objects.get(cart=cart, product_id=product_id)
            cart_item.delete()
            return Response({"message": "Item removed from cart."})
        except CartItem.DoesNotExist:
            return Response(
                {"error": "Item not found in cart."},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=["post"])
    def clear(self, request):
        """Remove all items from the cart."""
        cart = self.get_object()
        cart.items.all().delete()
        return Response({"message": "Cart cleared."})
