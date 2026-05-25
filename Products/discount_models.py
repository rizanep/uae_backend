from django.db import models
from django.utils.translation import gettext_lazy as _

class ProductDiscountTier(models.Model):
    """
    Defines discount rules based on quantity thresholds for a product.
    e.g. 10-50 items -> 5% off, 51+ items -> 10% off.
    """
    product = models.ForeignKey(
        'Products.Product', 
        related_name='discount_tiers', 
        on_delete=models.CASCADE
    )
    min_quantity = models.PositiveIntegerField(
        _("minimum quantity"), 
        default=1,
        help_text=_("Minimum quantity for this discount to apply")
    )
    discount_percentage = models.DecimalField(
        _("discount percentage"),
        max_digits=5,
        decimal_places=2,
        help_text=_("Percentage discount (0-100) for this quantity range")
    )

    class Meta:
        verbose_name = _("Discount Tier")
        verbose_name_plural = _("Discount Tiers")
        ordering = ['min_quantity']
        unique_together = ('product', 'min_quantity')

    def __str__(self):
        return f"{self.product.name} (Qty >= {self.min_quantity}): {self.discount_percentage}% off"
