from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from Products.models import Product, ProductPreparationSpecification
from decimal import Decimal

class Cart(models.Model):
    """
    Cart model linked to a user.
    Each user has only one active cart.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
        verbose_name=_("user"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Cart")
        verbose_name_plural = _("Carts")

    def __str__(self):
        return f"Cart for {self.user}"

    @property
    def total_price(self):
        return sum(item.subtotal for item in self.items.all())

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    """
    Items within a cart.
    Links a specific product and its quantity to a cart.
    """
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("cart"),
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="cart_items",
        verbose_name=_("product"),
    )
    preparation_specification = models.ForeignKey(
        ProductPreparationSpecification,
        on_delete=models.PROTECT,
        related_name="cart_items",
        verbose_name=_("preparation specification"),
        null=True,
        blank=True,
    )
    preparation_instructions = models.TextField(
        _("preparation instructions"),
        blank=True,
        help_text=_("Optional customer instructions for the selected preparation."),
    )
    quantity = models.PositiveIntegerField(_("quantity"), default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Cart Item")
        verbose_name_plural = _("Cart Items")
        indexes = [
            models.Index(fields=["cart", "product"]),
            models.Index(fields=["cart", "preparation_specification"]),
        ]

    def __str__(self):
        prep_name = self.preparation_specification.name if self.preparation_specification else "default"
        return f"{self.quantity} x {self.product.name} ({prep_name}) in {self.cart.user}'s cart"

    def clean(self):
        if self.preparation_specification:
            if self.preparation_specification.product_id != self.product_id:
                raise ValidationError({
                    "preparation_specification": _("Selected preparation specification does not belong to this product.")
                })
            if not self.preparation_specification.is_active:
                raise ValidationError({
                    "preparation_specification": _("Selected preparation specification is not available.")
                })
        elif self.product_id and self.product.preparation_specifications.filter(is_active=True).exists():
            raise ValidationError({
                "preparation_specification": _("A preparation specification is required for this product.")
            })

    def save(self, *args, **kwargs):
        self.preparation_instructions = (self.preparation_instructions or "").strip()
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def base_unit_price(self):
        """Product price after quantity discounts, before preparation surcharge."""
        price = self.product.final_price
        tier = self.product.discount_tiers.filter(min_quantity__lte=self.quantity).order_by('-min_quantity').first()

        if tier:
            discount_amount = (price * tier.discount_percentage) / Decimal("100")
            price -= discount_amount

        return price

    @property
    def preparation_extra_price(self):
        if self.preparation_specification:
            return self.preparation_specification.extra_price
        return Decimal("0.00")

    @property
    def unit_price(self):
        return self.base_unit_price + self.preparation_extra_price

    @property
    def subtotal(self):
        return self.unit_price * self.quantity
