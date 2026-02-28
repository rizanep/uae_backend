from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from Products.models import Product
from Users.models import UserAddress
from decimal import Decimal
import uuid

class Order(models.Model):
    """
    Order model representing a customer's purchase.
    Tracks status, totals, and shipping details.
    """
    class OrderStatus(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        PAID = "PAID", _("Paid")
        PROCESSING = "PROCESSING", _("Processing")
        SHIPPED = "SHIPPED", _("Shipped")
        DELIVERED = "DELIVERED", _("Delivered")
        CANCELLED = "CANCELLED", _("Cancelled")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
        verbose_name=_("user"),
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
    )
    shipping_address = models.ForeignKey(
        UserAddress,
        on_delete=models.SET_NULL,
        null=True,
        related_name="orders",
        verbose_name=_("shipping address"),
    )
    total_amount = models.DecimalField(_("total amount"), max_digits=12, decimal_places=2)
    tip_amount = models.DecimalField(_("tip amount"), max_digits=10, decimal_places=2, default=Decimal("0.00"))
    
    # Delivery Preferences
    preferred_delivery_date = models.DateField(_("preferred delivery date"), blank=True, null=True)
    preferred_delivery_slot = models.CharField(
        _("preferred delivery slot"), 
        max_length=50, 
        blank=True, 
        null=True,
        help_text=_("e.g., 9AM - 12PM, 2PM - 5PM")
    )
    delivery_notes = models.TextField(_("delivery notes"), blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.id} by {self.user}"


class OrderItem(models.Model):
    """
    Individual items within an order.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("order"),
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        related_name="order_items",
        verbose_name=_("product"),
    )
    product_name = models.CharField(_("product name"), max_length=255)
    quantity = models.PositiveIntegerField(_("quantity"))
    price = models.DecimalField(_("price"), max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = _("Order Item")
        verbose_name_plural = _("Order Items")

    @property
    def subtotal(self):
        if self.price is None or self.quantity is None:
            return Decimal("0.00")
        return self.price * self.quantity


class OrderStatusHistory(models.Model):
    """
    Tracks the timeline of an order's status changes.
    Allows users to see real-time updates (e.g., Shipped at 10:00 AM).
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="status_history",
        verbose_name=_("order"),
    )
    status = models.CharField(_("status"), max_length=20, choices=Order.OrderStatus.choices)
    notes = models.TextField(_("notes"), blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Order Status History")
        verbose_name_plural = _("Order Status Histories")
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.order.id} moved to {self.status}"


class Payment(models.Model):
    """
    Detailed storage for payment transactions.
    Prepares for Telr integration.
    """
    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        SUCCESS = "SUCCESS", _("Success")
        FAILED = "FAILED", _("Failed")
        REFUNDED = "REFUNDED", _("Refunded")

    class PaymentMethod(models.TextChoices):
        TELR = "TELR", _("Telr / Card")
        COD = "COD", _("Cash on Delivery")

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="payment",
        verbose_name=_("order"),
    )
    transaction_id = models.CharField(_("transaction ID"), max_length=100, unique=True, blank=True, null=True)
    telr_reference = models.CharField(_("Telr Reference"), max_length=100, blank=True, null=True)
    amount = models.DecimalField(_("amount"), max_digits=12, decimal_places=2)
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    payment_method = models.CharField(
        _("payment method"), 
        max_length=50, 
        choices=PaymentMethod.choices,
        default=PaymentMethod.TELR
    )
    provider_response = models.JSONField(_("provider response"), blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")

    def __str__(self):
        return f"Payment for Order #{self.order.id} - {self.status}"


class Receipt(models.Model):
    """
    Official receipt generated after a successful payment.
    """
    payment = models.OneToOneField(
        Payment,
        on_delete=models.CASCADE,
        related_name="receipt",
        verbose_name=_("payment"),
    )
    receipt_number = models.CharField(_("receipt number"), max_length=50, unique=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Receipt")
        verbose_name_plural = _("Receipts")

    def __str__(self):
        return f"Receipt {self.receipt_number}"

    @classmethod
    def generate_number(cls):
        """Generates a professional unique receipt number."""
        return f"REC-{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[:4].upper()}"
