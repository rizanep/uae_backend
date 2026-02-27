from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from Products.models import Product

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
    quantity = models.PositiveIntegerField(_("quantity"), default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Cart Item")
        verbose_name_plural = _("Cart Items")
        unique_together = ("cart", "product")

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in {self.cart.user}'s cart"

    @property
    def subtotal(self):
        return self.product.final_price * self.quantity
