"""
Coupon and discount calculation service for Orders.
Handles validation, calculation, and application of coupons.
"""
from django.utils import timezone
from decimal import Decimal
from Marketing.models import Coupon
from .models import DeliveryChargeConfig


def get_delivery_charge(order_amount):
    """
    Calculate delivery charge based on order amount.
    
    Args:
        order_amount (Decimal): The cart/order total
    
    Returns:
        Decimal: The delivery charge (0 for free shipping, or charge amount)
    """
    order_amount = Decimal(str(order_amount))
    config = DeliveryChargeConfig.get_config()
    
    if not config.is_active:
        return Decimal('0.00')
    
    if order_amount >= config.min_free_shipping_amount:
        # Free shipping
        return Decimal('0.00')
    else:
        # Apply delivery charge
        return config.delivery_charge.quantize(Decimal('0.01'))


def validate_and_calculate_coupon(coupon_code, user, order_amount):
    """
    Validate a coupon code and calculate the discount amount.
    
    Args:
        coupon_code (str): The coupon code to validate
        user: The user applying the coupon
        order_amount (Decimal): The cart/order total before discount
    
    Returns:
        dict: {
            'success': bool,
            'message': str,
            'coupon': Coupon object (if valid),
            'discount_amount': Decimal,
            'discount_type': str ('percentage' or 'fixed'),
            'final_amount': Decimal
        }
    """
    
    # Check if coupon exists
    try:
        coupon = Coupon.objects.get(code=coupon_code, deleted_at__isnull=True)
    except Coupon.DoesNotExist:
        return {
            'success': False,
            'message': f'Coupon code "{coupon_code}" not found.',
            'coupon': None,
            'discount_amount': Decimal('0.00'),
            'discount_type': None,
            'final_amount': order_amount
        }
    
    # Validate coupon
    is_valid, validation_message = coupon.is_valid(user=user, order_amount=order_amount)
    
    if not is_valid:
        return {
            'success': False,
            'message': validation_message,
            'coupon': coupon,
            'discount_amount': Decimal('0.00'),
            'discount_type': coupon.discount_type,
            'final_amount': order_amount
        }
    
    # Calculate discount
    discount_amount = calculate_discount(coupon, order_amount)
    final_amount = order_amount - discount_amount
    
    return {
        'success': True,
        'message': f'Coupon "{coupon_code}" is valid. Discount: {discount_amount}',
        'coupon': coupon,
        'discount_amount': discount_amount,
        'discount_type': coupon.discount_type,
        'final_amount': final_amount
    }


def calculate_discount(coupon, order_amount):
    """
    Calculate the discount amount for a given coupon and order amount.
    
    Args:
        coupon: Coupon object
        order_amount (Decimal): The order total before discount
    
    Returns:
        Decimal: The discount amount to apply
    """
    order_amount = Decimal(str(order_amount))
    
    if coupon.discount_type == 'percentage':
        # Calculate percentage discount
        discount = order_amount * (coupon.discount_value / Decimal(100))
        
        # Apply max discount cap if set
        if coupon.max_discount_amount:
            max_discount = Decimal(str(coupon.max_discount_amount))
            discount = min(discount, max_discount)
    else:
        # Fixed amount discount
        discount = Decimal(str(coupon.discount_value))
    
    # Discount cannot exceed order amount
    discount = min(discount, order_amount)
    
    return discount.quantize(Decimal('0.01'))


def apply_coupon_to_order(order, coupon_code, user, cart_total):
    """
    Apply a coupon to an order and calculate the final amount.
    
    Args:
        order: Order object to apply coupon to
        coupon_code (str): The coupon code
        user: The user making the order
        cart_total (Decimal): The cart total before discount
    
    Returns:
        dict: {
            'success': bool,
            'message': str,
            'discount_amount': Decimal,
            'final_amount': Decimal
        }
    """
    
    result = validate_and_calculate_coupon(coupon_code, user, cart_total)
    
    if not result['success']:
        return {
            'success': False,
            'message': result['message'],
            'discount_amount': Decimal('0.00'),
            'final_amount': cart_total
        }
    
    # Update order with coupon info
    order.coupon = result['coupon']
    order.coupon_code = coupon_code
    order.discount_amount = result['discount_amount']
    # Update total_amount to reflect discount
    order.total_amount = result['final_amount'] + order.tip_amount
    
    return {
        'success': True,
        'message': f'Coupon applied successfully. Discount: {result["discount_amount"]} {result["discount_type"]}',
        'discount_amount': result['discount_amount'],
        'final_amount': result['final_amount']
    }
