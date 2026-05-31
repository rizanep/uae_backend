from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Prefetch
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer
from Products.models import Product, ProductPreparationSpecification
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
        preparation_specification_id = request.data.get("preparation_specification")
        preparation_instructions = (request.data.get("preparation_instructions") or "").strip()

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

        preparation_specification = None
        active_specs = product.preparation_specifications.filter(is_active=True)
        if active_specs.exists():
            if not preparation_specification_id:
                return Response(
                    {"error": "Preparation specification is required for this product."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                preparation_specification = active_specs.get(id=preparation_specification_id)
            except ProductPreparationSpecification.DoesNotExist:
                return Response(
                    {"error": "Invalid preparation specification for this product."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        elif preparation_specification_id:
            return Response(
                {"error": "This product does not support preparation specifications."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                # Serialize cart writes to avoid concurrent duplicate rows for the same cart.
                Cart.objects.select_for_update().get(pk=cart.pk)

                matching_items = CartItem.objects.filter(
                    cart=cart,
                    product=product,
                    preparation_specification=preparation_specification,
                    preparation_instructions=preparation_instructions,
                ).order_by("id")

                cart_item = matching_items.first()
                created = cart_item is None

                if created:
                    cart_item = CartItem(
                        cart=cart,
                        product=product,
                        preparation_specification=preparation_specification,
                        preparation_instructions=preparation_instructions,
                        quantity=quantity,
                    )
                else:
                    existing_quantity = sum(item.quantity for item in matching_items)
                    cart_item.quantity = existing_quantity + quantity

                if product.stock < cart_item.quantity:
                    return Response(
                        {"error": f"Cannot add more. Only {product.stock} items in stock."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                cart_item.save()

                # Self-heal any duplicate rows with the same logical identity.
                duplicate_ids = list(matching_items.values_list("id", flat=True))[1:]
                if duplicate_ids:
                    CartItem.objects.filter(id__in=duplicate_ids).delete()
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"message": "Item added to cart.", "cart_item_id": cart_item.id},
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
        cart_item_id = request.data.get("cart_item_id")
        product_id = request.data.get("product")
        quantity = int(request.data.get("quantity"))

        if quantity < 1:
            return Response(
                {"error": "Quantity must be at least 1."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            lookup = {"cart": cart}
            if cart_item_id:
                lookup["id"] = cart_item_id
            else:
                lookup["product_id"] = product_id

            cart_items = CartItem.objects.filter(**lookup).select_related('product').order_by("id")
            if not cart_items.exists():
                raise CartItem.DoesNotExist

            if not cart_item_id and cart_items.count() > 1:
                return Response(
                    {"error": "Multiple cart items found for this product. Provide cart_item_id."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            cart_item = cart_items.first()
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
        cart_item_id = request.data.get("cart_item_id")
        product_id = request.data.get("product")

        try:
            lookup = {"cart": cart}
            if cart_item_id:
                lookup["id"] = cart_item_id
            else:
                lookup["product_id"] = product_id

            cart_items = CartItem.objects.filter(**lookup).order_by("id")
            if not cart_items.exists():
                raise CartItem.DoesNotExist

            if not cart_item_id and cart_items.count() > 1:
                return Response(
                    {"error": "Multiple cart items found for this product. Provide cart_item_id."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            cart_items.delete()
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
