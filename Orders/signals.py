from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Order, OrderStatusHistory, Payment, Receipt

@receiver(post_save, sender=Order)
def create_order_status_history(sender, instance, created, **kwargs):
    """
    Automatically creates a status history entry whenever an order is created
    or its status is updated.
    """
    # Check if this is a new order or if the status has changed
    # For simplicity in this implementation, we always create a history entry
    # if it's the latest status. In a more advanced version, we'd check if status changed.
    last_history = OrderStatusHistory.objects.filter(order=instance).order_by("-created_at").first()
    
    if not last_history or last_history.status != instance.status:
        OrderStatusHistory.objects.create(
            order=instance,
            status=instance.status,
            notes=f"Order status updated to {instance.status}"
        )

@receiver(post_save, sender=Payment)
def handle_payment_success(sender, instance, **kwargs):
    """
    When a payment is successful:
    1. Update the order status to PAID.
    2. Generate a receipt.
    """
    if instance.status == Payment.PaymentStatus.SUCCESS:
        # 1. Update Order
        order = instance.order
        if order.status != Order.OrderStatus.PAID:
            order.status = Order.OrderStatus.PAID
            order.save()
        
        # 2. Create Receipt if it doesn't exist
        if not hasattr(instance, "receipt"):
            Receipt.objects.create(
                payment=instance,
                receipt_number=Receipt.generate_number()
            )
