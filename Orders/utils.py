import re
from datetime import timedelta
from django.utils import timezone

def calculate_delivery_estimate(cart_items):
    """
    Calculate the estimated delivery days for a list of cart items.
    Returns a tuple: (max_days, details_list)
    """
    max_days = 0
    details = []

    for item in cart_items:
        product = item.product
        quantity = item.quantity
        days = 1  # Default fallback
        source = "default"

        # Check for delivery tiers
        # Find the tier with the highest min_quantity that is <= item.quantity
        tier = product.delivery_tiers.filter(min_quantity__lte=quantity).order_by('-min_quantity').first()
        
        if tier:
            days = tier.delivery_days
            source = "tier"
        elif product.expected_delivery_time:
            # Try to parse string like "2-3 Days", "Next Day"
            lower_time = product.expected_delivery_time.lower()
            if "next day" in lower_time:
                days = 1
                source = "parsed_next_day"
            elif "day" in lower_time:
                # Extract all numbers, take the largest one (e.g. "2-3 days" -> 3)
                nums = [int(n) for n in re.findall(r'\d+', lower_time)]
                if nums:
                    days = max(nums)
                    source = "parsed_days"
            elif "hour" in lower_time or "min" in lower_time:
                # Same day delivery
                days = 0
                source = "parsed_same_day"

        if days > max_days:
            max_days = days
        
        details.append({
            "product_id": product.id,
            "product_name": product.name,
            "quantity": quantity,
            "estimated_days": days,
            "source": source
        })

    return max_days, details

def get_earliest_delivery_date(cart_items):
    """
    Returns the earliest possible delivery date (date object) for the given cart items.
    """
    max_days, _ = calculate_delivery_estimate(cart_items)
    return timezone.now().date() + timedelta(days=max_days)
