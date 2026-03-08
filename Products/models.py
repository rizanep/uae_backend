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
