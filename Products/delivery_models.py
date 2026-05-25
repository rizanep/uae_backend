
from django.db import models
from django.utils.translation import gettext_lazy as _

class ProductDeliveryTier(models.Model):
    """
    Defines delivery time rules based on quantity thresholds for a product.
    e.g. 1-10 items -> 2 days, 11-50 items -> 5 days.
    """
    product = models.ForeignKey(
        'Products.Product', 
        related_name='delivery_tiers', 
        on_delete=models.CASCADE
    )
    min_quantity = models.PositiveIntegerField(
        _("minimum quantity"), 
        default=1,
        help_text=_("Minimum quantity for this tier to apply")
    )
    delivery_days = models.PositiveIntegerField(
        _("delivery days"), 
        help_text=_("Number of days required for delivery for this quantity range")
    )

    class Meta:
        verbose_name = _("Delivery Tier")
        verbose_name_plural = _("Delivery Tiers")
        ordering = ['min_quantity']
        unique_together = ('product', 'min_quantity')

    def __str__(self):
        return f"{self.product.name} (Qty >= {self.min_quantity}): {self.delivery_days} days"
