"""
Utilities for Product Preparation Specifications.

This module provides helper functions for:
- Creating order items with preparation specifications
- Validating preparation selections
- Calculating totals with preparation extra prices
- Serializing preparation data
"""

from decimal import Decimal
from django.core.exceptions import ValidationError
from Orders.models import Order, OrderItem
from .models import Product, ProductPreparationSpecification


class PreparationSpecificationValidator:
    """Validator for product preparation specifications."""
    
    @staticmethod
    def validate_preparation_selection(product: Product, prep_spec_id: int) -> ProductPreparationSpecification:
        """
        Validate that a preparation specification is valid for a product.
        
        Args:
            product: Product instance
            prep_spec_id: ID of the preparation specification
            
        Returns:
            ProductPreparationSpecification instance
            
        Raises:
            ValidationError: If spec is invalid or not available
        """
        try:
            prep_spec = ProductPreparationSpecification.objects.get(
                id=prep_spec_id,
                product=product
            )
        except ProductPreparationSpecification.DoesNotExist:
            raise ValidationError(
                f"Preparation specification {prep_spec_id} does not exist for product {product.name}."
            )
        
        if not prep_spec.is_active:
            raise ValidationError(
                f"Preparation specification '{prep_spec.name}' is no longer available."
            )
        
        return prep_spec
    
    @staticmethod
    def validate_order_item_preparation(order_item: OrderItem) -> None:
        """
        Validate that an order item has required preparation data.
        
        Args:
            order_item: OrderItem instance
            
        Raises:
            ValidationError: If preparation spec is required but not provided
        """
        # Check if product has any active preparation specs
        has_active_specs = ProductPreparationSpecification.objects.filter(
            product=order_item.product,
            is_active=True
        ).exists()
        
        if has_active_specs and not order_item.preparation_specification:
            raise ValidationError({
                'preparation_specification': 'Preparation specification is required for this product.'
            })
    
    @staticmethod
    def validate_preparation_instructions(instructions: str, max_length: int = 500) -> str:
        """
        Validate and sanitize preparation instructions.
        
        Args:
            instructions: User-provided preparation instructions
            max_length: Maximum allowed length
            
        Returns:
            Cleaned instructions
            
        Raises:
            ValidationError: If instructions exceed max length
        """
        if instructions:
            instructions = instructions.strip()
            if len(instructions) > max_length:
                raise ValidationError(
                    f"Preparation instructions cannot exceed {max_length} characters."
                )
        
        return instructions or None


class OrderItemPreparationHelper:
    """Helper functions for order items with preparation specifications."""
    
    @staticmethod
    def create_order_item_with_preparation(
        order: Order,
        product: Product,
        quantity: int,
        price: Decimal,
        prep_spec_id: int = None,
        instructions: str = None,
        **kwargs
    ) -> OrderItem:
        """
        Create an order item with preparation specification.
        
        Args:
            order: Order instance
            product: Product instance
            quantity: Quantity ordered
            price: Unit price
            prep_spec_id: ID of preparation specification (required if product has active specs)
            instructions: Custom preparation instructions
            **kwargs: Additional OrderItem fields
            
        Returns:
            OrderItem instance (saved)
            
        Raises:
            ValidationError: If preparation data is invalid
        """
        # Validate preparation selection if provided
        prep_spec = None
        if prep_spec_id:
            prep_spec = PreparationSpecificationValidator.validate_preparation_selection(
                product, prep_spec_id
            )
        
        # Validate instructions
        if instructions:
            instructions = PreparationSpecificationValidator.validate_preparation_instructions(instructions)
        
        # Validate that preparation is required if product has active specs
        order_item = OrderItem(
            order=order,
            product=product,
            product_name=product.name,
            quantity=quantity,
            price=price,
            preparation_specification=prep_spec,
            preparation_instructions=instructions,
            **kwargs
        )
        
        # This will call full_clean which should validate preparation if needed
        PreparationSpecificationValidator.validate_order_item_preparation(order_item)
        
        # Set snapshots for data integrity
        if prep_spec:
            order_item.preparation_specification_name = prep_spec.name
            order_item.preparation_extra_price = prep_spec.extra_price
        
        order_item.save()
        return order_item
    
    @staticmethod
    def update_order_item_preparation(
        order_item: OrderItem,
        prep_spec_id: int = None,
        instructions: str = None
    ) -> OrderItem:
        """
        Update preparation specification and/or instructions for an order item.
        
        Only works for pending orders (allows modification before processing).
        
        Args:
            order_item: OrderItem instance
            prep_spec_id: New preparation spec ID (optional)
            instructions: New instructions (optional)
            
        Returns:
            Updated OrderItem instance
            
        Raises:
            ValidationError: If order cannot be modified or data is invalid
        """
        if order_item.order.status not in ['PENDING']:
            raise ValidationError(
                f"Cannot modify order items for orders with status: {order_item.order.status}"
            )
        
        if prep_spec_id is not None:
            prep_spec = PreparationSpecificationValidator.validate_preparation_selection(
                order_item.product, prep_spec_id
            )
            order_item.preparation_specification = prep_spec
            order_item.preparation_specification_name = prep_spec.name
            order_item.preparation_extra_price = prep_spec.extra_price
        
        if instructions is not None:
            order_item.preparation_instructions = PreparationSpecificationValidator.validate_preparation_instructions(
                instructions
            )
        
        order_item.save()
        return order_item
    
    @staticmethod
    def calculate_total_with_preparation(
        quantity: int,
        unit_price: Decimal,
        prep_extra_price: Decimal = None
    ) -> Decimal:
        """
        Calculate total price including preparation extra cost.
        
        Formula: (unit_price * quantity) + (prep_extra_price * quantity)
        
        Args:
            quantity: Quantity of items
            unit_price: Price per unit
            prep_extra_price: Extra price for preparation (default 0)
            
        Returns:
            Total price as Decimal
        """
        if prep_extra_price is None:
            prep_extra_price = Decimal("0.00")
        
        base_total = Decimal(str(unit_price)) * Decimal(str(quantity))
        prep_total = Decimal(str(prep_extra_price)) * Decimal(str(quantity))
        
        return base_total + prep_total
    
    @staticmethod
    def get_preparation_summary(order_item: OrderItem) -> dict:
        """
        Get a summary of preparation details for an order item.
        
        Args:
            order_item: OrderItem instance
            
        Returns:
            Dictionary with preparation details
        """
        return {
            'id': order_item.preparation_specification.id if order_item.preparation_specification else None,
            'name': order_item.preparation_specification_name,
            'extra_price': float(order_item.preparation_extra_price or Decimal("0.00")),
            'instructions': order_item.preparation_instructions,
            'subtotal_base': float(order_item.subtotal),
            'subtotal_preparation': float((order_item.preparation_extra_price or Decimal("0.00")) * order_item.quantity),
            'total': float(order_item.total_with_preparation),
        }


class PreparationSpecificationQueryHelper:
    """Helper functions for querying preparation specifications."""
    
    @staticmethod
    def get_active_specs_for_product(product: Product) -> list:
        """
        Get all active preparation specifications for a product.
        
        Args:
            product: Product instance
            
        Returns:
            QuerySet of active ProductPreparationSpecification
        """
        return ProductPreparationSpecification.objects.filter(
            product=product,
            is_active=True
        ).order_by('sort_order', 'name')
    
    @staticmethod
    def product_has_preparation_options(product: Product) -> bool:
        """
        Check if a product has active preparation specifications.
        
        Args:
            product: Product instance
            
        Returns:
            True if product has active specs, False otherwise
        """
        return ProductPreparationSpecification.objects.filter(
            product=product,
            is_active=True
        ).exists()
    
    @staticmethod
    def get_preparation_extra_price(product: Product, prep_spec_id: int) -> Decimal:
        """
        Get the extra price for a specific preparation specification.
        
        Args:
            product: Product instance
            prep_spec_id: ID of preparation specification
            
        Returns:
            Extra price as Decimal
            
        Raises:
            ProductPreparationSpecification.DoesNotExist: If spec not found
        """
        prep_spec = ProductPreparationSpecification.objects.get(
            id=prep_spec_id,
            product=product
        )
        return prep_spec.extra_price
    
    @staticmethod
    def get_orders_with_preparation_instructions(
        start_date=None,
        end_date=None,
        has_instructions_only=True
    ):
        """
        Get orders that have preparation instructions.
        
        Args:
            start_date: Filter orders from this date (optional)
            end_date: Filter orders until this date (optional)
            has_instructions_only: Only return items with custom instructions (default True)
            
        Returns:
            QuerySet of OrderItems
        """
        queryset = OrderItem.objects.filter(
            preparation_specification__isnull=False
        )
        
        if has_instructions_only:
            queryset = queryset.exclude(
                preparation_instructions__isnull=True,
                preparation_instructions=''
            )
        
        if start_date:
            queryset = queryset.filter(order__created_at__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(order__created_at__lte=end_date)
        
        return queryset.select_related(
            'order', 'product', 'preparation_specification'
        ).order_by('-order__created_at')
