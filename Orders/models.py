from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from Products.models import Product
from Users.models import UserAddress
from decimal import Decimal
import uuid
from django.utils import timezone
import datetime
import pytz

UAE_TZ = pytz.timezone('Asia/Dubai')


class DeliveryTimeSlot(models.Model):
    """
    Master configuration for delivery timeslots.
    e.g. 8-9 AM with a 7:30 AM cutoff.
    Active/inactive controlled globally and per-date via DeliverySlotOverride.
    """
    name = models.CharField(
        _("slot name"),
        max_length=100,
        help_text=_("e.g. 'Morning Slot', '8 AM - 9 AM'")
    )
    start_time = models.TimeField(_("start time"), help_text=_("Slot starts at (e.g. 08:00)"))
    end_time = models.TimeField(_("end time"), help_text=_("Slot ends at (e.g. 09:00)"))
    cutoff_time = models.TimeField(
        _("cutoff time"),
        help_text=_("Orders must be placed before this time (same day) to select this slot. e.g. 07:30")
    )
    is_active = models.BooleanField(_("is active"), default=True, help_text=_("Globally enable/disable this slot"))
    sort_order = models.PositiveIntegerField(_("sort order"), default=0, help_text=_("Lower numbers appear first"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Delivery Time Slot")
        verbose_name_plural = _("Delivery Time Slots")
        ordering = ["sort_order", "start_time"]

    def __str__(self):
        return f"{self.name} ({self.start_time.strftime('%I:%M %p')} - {self.end_time.strftime('%I:%M %p')})"

    def clean(self):
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError(_("Start time must be before end time."))
        if self.cutoff_time and self.start_time and self.cutoff_time >= self.start_time:
            raise ValidationError(_("Cutoff time must be before the slot start time."))

    def is_available_for_date(self, date):
        """
        Returns True if this slot is available for the given date.
        Checks: global active, per-date override, and cutoff time (for today).
        """
        if not self.is_active:
            return False

        # Check per-date override
        override = self.overrides.filter(date=date).first()
        if override is not None:
            return override.is_active

        # If date is today, check cutoff time
        now_uae = timezone.now().astimezone(UAE_TZ)
        if date == now_uae.date():
            return now_uae.time() < self.cutoff_time

        # For future dates, slot is available as long as it's active
        if date > now_uae.date():
            return True

        # Past dates - not available
        return False


class DeliverySlotOverride(models.Model):
    """
    Per-date availability override for a delivery timeslot.
    Admins use this to deactivate a slot on a specific date (e.g. holiday, no drivers).
    """
    slot = models.ForeignKey(
        DeliveryTimeSlot,
        on_delete=models.CASCADE,
        related_name="overrides",
        verbose_name=_("delivery time slot")
    )
    date = models.DateField(_("date"), db_index=True)
    is_active = models.BooleanField(
        _("is active"),
        default=False,
        help_text=_("Set to False to disable this slot on this specific date")
    )
    reason = models.CharField(_("reason"), max_length=255, blank=True, help_text=_("Optional reason for override"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Delivery Slot Override")
        verbose_name_plural = _("Delivery Slot Overrides")
        unique_together = [("slot", "date")]
        ordering = ["date", "slot__sort_order"]

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.slot.name} on {self.date} - {status}"


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
    coupon = models.ForeignKey(
        'Marketing.Coupon',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name=_("coupon"),
    )
    coupon_code = models.CharField(_("coupon code"), max_length=50, blank=True, null=True)
    discount_amount = models.DecimalField(_("discount amount"), max_digits=12, decimal_places=2, default=Decimal("0.00"))
    delivery_charge = models.DecimalField(_("delivery charge"), max_digits=10, decimal_places=2, default=Decimal("0.00"))
    
    # Delivery Preferences
    preferred_delivery_date = models.DateField(_("preferred delivery date"), blank=True, null=True)
    preferred_delivery_slot = models.ForeignKey(
        DeliveryTimeSlot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name=_("preferred delivery slot"),
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


class DeliveryAssignment(models.Model):
    class AssignmentStatus(models.TextChoices):
        ASSIGNED = "ASSIGNED", _("Assigned")
        IN_TRANSIT = "IN_TRANSIT", _("In Transit")
        COMPLETED = "COMPLETED", _("Completed")

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="delivery_assignment",
        verbose_name=_("order"),
    )
    delivery_boy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="delivery_assignments",
        verbose_name=_("delivery boy"),
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_deliveries",
        verbose_name=_("assigned by"),
    )
    status = models.CharField(
        _("assignment status"),
        max_length=20,
        choices=AssignmentStatus.choices,
        default=AssignmentStatus.ASSIGNED,
    )
    assigned_at = models.DateTimeField(auto_now_add=True, db_index=True)
    accepted_at = models.DateTimeField(blank=True, null=True)
    delivered_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = _("Delivery Assignment")
        verbose_name_plural = _("Delivery Assignments")
        ordering = ["-assigned_at"]
        indexes = [
            models.Index(fields=["delivery_boy", "status"], name="delivery_boy_status_idx"),
        ]

    def __str__(self):
        return f"Order #{self.order_id} assigned to {self.delivery_boy}"

    def clean(self):
        super().clean()
        if self.delivery_boy.role != 'delivery_boy':
            raise ValidationError("Assigned user must have delivery_boy role.")

        profile = getattr(self.delivery_boy, 'delivery_profile', None)
        if not profile:
            raise ValidationError("Delivery boy profile is required before assignment.")

        order_emirate = getattr(self.order.shipping_address, 'emirate', None)
        if order_emirate and profile.assigned_emirates and order_emirate not in profile.assigned_emirates:
            raise ValidationError("Delivery boy is not assigned to this order's emirate.")


class DeliveryCancellationRequest(models.Model):
    class RequestStatus(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        APPROVED = "APPROVED", _("Approved")
        REJECTED = "REJECTED", _("Rejected")

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="delivery_cancel_request",
        verbose_name=_("order"),
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="delivery_cancel_requests",
        verbose_name=_("requested by"),
    )
    reason = models.TextField(_("reason"))
    status = models.CharField(
        _("request status"),
        max_length=20,
        choices=RequestStatus.choices,
        default=RequestStatus.PENDING,
        db_index=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_delivery_cancel_requests",
        verbose_name=_("reviewed by"),
    )
    review_notes = models.TextField(_("review notes"), blank=True, null=True)
    requested_at = models.DateTimeField(auto_now_add=True, db_index=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = _("Delivery Cancellation Request")
        verbose_name_plural = _("Delivery Cancellation Requests")
        ordering = ["-requested_at"]

    def __str__(self):
        return f"Cancel request for Order #{self.order_id} ({self.status})"


class DeliveryProof(models.Model):
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="delivery_proof",
        verbose_name=_("order"),
    )
    assignment = models.ForeignKey(
        DeliveryAssignment,
        on_delete=models.CASCADE,
        related_name="proofs",
        verbose_name=_("delivery assignment"),
    )
    proof_image = models.ImageField(upload_to="delivery/proofs/")
    signature_name = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_delivery_proofs",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Delivery Proof")
        verbose_name_plural = _("Delivery Proofs")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Delivery proof for Order #{self.order_id}"


class Payment(models.Model):
    """
    Detailed storage for payment transactions.
    Integrated with Ziina payment gateway.
    """
    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        SUCCESS = "SUCCESS", _("Success")
        FAILED = "FAILED", _("Failed")
        REFUNDED = "REFUNDED", _("Refunded")

    class PaymentMethod(models.TextChoices):
        ZIINA = "ZIINA", _("Ziina / Card")
        COD = "COD", _("Cash on Delivery")

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="payment",
        verbose_name=_("order"),
    )
    transaction_id = models.CharField(_("transaction ID"), max_length=100, unique=True, blank=True, null=True)
    ziina_payment_intent_id = models.CharField(_("Ziina Payment Intent ID"), max_length=200, blank=True, null=True)
    refund_id = models.CharField(_("refund ID"), max_length=200, blank=True, null=True)
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
        default=PaymentMethod.ZIINA
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


class DeliveryChargeConfig(models.Model):
    """
    Configuration for delivery charges.
    Admin can manage delivery charge rules (threshold and charge amount).
    There should only be one instance of this model.
    """
    min_free_shipping_amount = models.DecimalField(
        _("minimum amount for free shipping"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("40.00"),
        help_text=_("Orders >= this amount get free shipping. Default: AED 40")
    )
    delivery_charge = models.DecimalField(
        _("delivery charge"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("10.00"),
        help_text=_("Delivery charge for orders below min_free_shipping_amount. Default: AED 10")
    )
    is_active = models.BooleanField(
        _("is active"),
        default=True,
        help_text=_("Enable/disable delivery charges")
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delivery_configs"
    )

    class Meta:
        verbose_name = _("Delivery Charge Configuration")
        verbose_name_plural = _("Delivery Charge Configuration")

    def __str__(self):
        return f"Delivery Charges: Free above AED {self.min_free_shipping_amount}, Otherwise AED {self.delivery_charge}"

    @classmethod
    def get_config(cls):
        """Get the active delivery charge configuration."""
        config, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                'min_free_shipping_amount': Decimal("40.00"),
                'delivery_charge': Decimal("10.00"),
                'is_active': True
            }
        )
        return config

    def save(self, *args, **kwargs):
        # Only allow one instance
        if not self.pk:
            self.pk = 1
        super().save(*args, **kwargs)
