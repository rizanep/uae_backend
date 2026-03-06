from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Order, OrderStatusHistory, Payment, Receipt
from Notifications.models import Notification
from django.contrib.auth import get_user_model

User = get_user_model()

@receiver(pre_save, sender=Order)
def capture_old_order_status(sender, instance, **kwargs):
    """
    Capture the old status of the order before saving.
    This helps in determining if the status has changed.
    """
    if instance.pk:
        try:
            old_instance = Order.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except Order.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

@receiver(post_save, sender=Order)
def create_order_status_history(sender, instance, created, **kwargs):
    """
    Automatically creates a status history entry whenever an order is created
    or its status is updated.
    """
    # Check if this is a new order or if the status has changed
    # We check the last history entry to determine if status changed
    last_history = OrderStatusHistory.objects.filter(order=instance).order_by("-created_at").first()
    
    if not last_history or last_history.status != instance.status:
        OrderStatusHistory.objects.create(
            order=instance,
            status=instance.status,
            notes=f"Order status updated to {instance.status}"
        )

@receiver(post_save, sender=Order)
def send_order_status_notification(sender, instance, created, **kwargs):
    """
    Send a notification to the user when the order status changes.
    Also notify admins when a new order is created.
    """
    if created:
        # Notify the customer
        Notification.objects.create(
            user=instance.user,
            title="Order Placed Successfully",
            message=f"Your order #{instance.id} has been placed successfully.",
            action_url=f"/orders/{instance.id}"
        )

        # Notify Admins
        admins = User.objects.filter(role='admin') | User.objects.filter(is_superuser=True)
        admins = admins.distinct()
        
        admin_notifications = []
        for admin in admins:
            # Avoid notifying the user if they are also an admin (optional, but good practice)
            # But usually admins want to know even if they placed a test order.
            
            admin_notifications.append(Notification(
                user=admin,
                title="New Order Received",
                message=f"New order #{instance.id} from {instance.user.email or instance.user.phone_number}. Total: {instance.total_amount}",
                action_url=f"/admin/orders/{instance.id}" # Or appropriate admin link
            ))
        
        if admin_notifications:
            Notification.objects.bulk_create(admin_notifications)

    else:
        old_status = getattr(instance, '_old_status', None)
        if old_status and old_status != instance.status:
            Notification.objects.create(
                user=instance.user,
                title=f"Order Status Update: {instance.get_status_display()}",
                message=f"Your order #{instance.id} status has been updated to {instance.get_status_display()}.",
                action_url=f"/orders/{instance.id}"
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
