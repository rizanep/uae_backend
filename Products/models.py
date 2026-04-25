from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from Users.models import SoftDeleteModel

# Import Delivery Models (Circular import handling might be needed if they import Product)
# But here we can define them or import them if they are separate.
# Since Product is used in ProductDeliveryTier as ForeignKey('Product'), it's fine.

class Category(SoftDeleteModel):
    """
    Product Category model with support for subcategories.
    Suitable for marine products like Fish, Meat, etc.
    """
    name = models.CharField(_("name"), max_length=100)
    name_arabic = models.CharField(_("name arabic"), max_length=100, blank=True)
    name_chinese = models.CharField(_("name chinese"), max_length=100, blank=True)
    slug = models.SlugField(_("slug"), max_length=120, unique=True, blank=True)
    description = models.TextField(_("description"), blank=True)
    image = models.ImageField(_("image"), upload_to="categories/", blank=True, null=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        verbose_name=_("parent category"),
    )

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class ProductUnit(models.TextChoices):
    PIECE = "piece", _("Piece")
    KG = "kg", _("Kg")
    G = "Gram", _("g")


DEFAULT_AVAILABLE_EMIRATES = [
    "abu_dhabi",
    "dubai",
    "sharjah",
    "ajman",
    "umm_al_quwain",
    "ras_al_khaimah",
    "fujairah",
]


def default_available_emirates():
    return DEFAULT_AVAILABLE_EMIRATES.copy()


class Product(SoftDeleteModel):
    """
    Product model with professional ecommerce fields.
    Optimized for fresh products like fish and meats.
    """
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="products",
        verbose_name=_("category"),
    )
    name = models.CharField(_("name"), max_length=255)
    slug = models.SlugField(_("slug"), max_length=255, unique=True, blank=True)
    description = models.TextField(_("description"))
    price = models.DecimalField(_("price"), max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(
        _("discount price"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    stock = models.PositiveIntegerField(_("stock"), default=0)
    is_available = models.BooleanField(_("is available"), default=True)
    image = models.ImageField(_("main image"), upload_to="products/", blank=True, null=True)
    sku = models.CharField(_("SKU"), max_length=50, unique=True, blank=True)
    unit = models.CharField(_("unit"), max_length=20, choices=ProductUnit.choices, default=ProductUnit.PIECE)
    available_emirates = models.JSONField(_("available emirates"), default=default_available_emirates)
    expected_delivery_time = models.CharField(
        _("expected delivery time"), 
        max_length=100, 
        blank=True, 
        null=True,
        help_text=_("e.g., '30-60 mins', 'Next Day', '2-3 Business Days'")
    )

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Check if stock is increasing from 0
        if self.pk:
            try:
                old_product = Product.objects.get(pk=self.pk)
                stock_was_zero = old_product.stock == 0
                stock_now_positive = self.stock > 0
                if stock_was_zero and stock_now_positive:
                    # Trigger notifications
                    self._notify_stock_availability()
            except Product.DoesNotExist:
                pass

        if not self.slug:
            self.slug = slugify(self.name)
        if not self.sku:
            base = slugify(self.name)[:40] or "product"
            candidate = base
            index = 1
            ModelClass = type(self)
            while ModelClass.objects.filter(sku=candidate).exclude(pk=self.pk).exists():
                index += 1
                suffix = f"-{index}"
                candidate = f"{base[:50 - len(suffix)]}{suffix}"
            self.sku = candidate
        super().save(*args, **kwargs)

    def _notify_stock_availability(self):
        """
        Notify users who requested notifications for this product.
        """
        from django.db import transaction
        from Notifications.tasks import send_stock_notification_email, send_stock_notification_whatsapp
        from Notifications.push_service import send_push_to_user

        # Get all pending notifications for this product
        pending_notifications = ProductNotification.objects.filter(
            product=self,
            notified=False
        ).select_related('user')

        for notification in pending_notifications:
            user = notification.user

            # Send email if user has email
            if user.email:
                send_stock_notification_email.delay(user.id, self.name)

            # Send WhatsApp if user has phone
            if user.phone_number:
                send_stock_notification_whatsapp.delay(user.id, self.name)

            # Send push notification
            send_push_to_user(
                user=user,
                title="Product Back in Stock!",
                body=f"Good news! {self.name} is now available.",
                data={"product_id": self.id, "type": "stock_available"}
            )

            # Mark as notified
            notification.notified = True
            notification.save()

    @property
    def final_price(self):
        if self.discount_price:
            return self.discount_price
        return self.price

from .delivery_models import ProductDeliveryTier
from .discount_models import ProductDiscountTier


class ProductImage(models.Model):
    """
    Additional images for a product.
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name=_("product"),
    )
    image = models.ImageField(_("image"), upload_to="products/gallery/")
    is_feature = models.BooleanField(_("is feature"), default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Product Image")
        verbose_name_plural = _("Product Images")


class ProductVideo(models.Model):
    """
    Video content for a product.
    Can be a direct upload or a link (e.g., YouTube/Vimeo).
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="videos",
        verbose_name=_("product"),
    )
    video_file = models.FileField(_("video file"), upload_to="products/videos/", blank=True, null=True)
    video_url = models.URLField(_("video URL"), blank=True, null=True, help_text=_("Link to YouTube, Vimeo, etc."))
    title = models.CharField(_("title"), max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Product Video")
        verbose_name_plural = _("Product Videos")

    def __str__(self):
        return self.title or f"Video for {self.product.name}"


class ProductNotification(models.Model):
    """
    Tracks users who want to be notified when a product comes back in stock.
    """
    user = models.ForeignKey(
        'Users.User',
        on_delete=models.CASCADE,
        related_name='product_notifications',
        verbose_name=_("user"),
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_("product"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    notified = models.BooleanField(_("notified"), default=False)

    class Meta:
        verbose_name = _("Product Notification")
        verbose_name_plural = _("Product Notifications")
        unique_together = ['user', 'product']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.product.name}"
