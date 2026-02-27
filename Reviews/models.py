from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from Products.models import Product
from Users.models import SoftDeleteModel

class Review(SoftDeleteModel):
    """
    Model for product reviews and ratings.
    Supports photos and moderation (hiding reviews).
    """
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name="reviews", 
        verbose_name=_("product")
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="reviews", 
        verbose_name=_("user")
    )
    rating = models.PositiveSmallIntegerField(
        _("rating"),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text=_("Rating from 1 to 5")
    )
    comment = models.TextField(_("comment"), blank=True)
    is_visible = models.BooleanField(
        _("is visible"), 
        default=True,
        help_text=_("Admins can uncheck this to hide the review")
    )
    admin_response = models.TextField(_("admin response"), blank=True, null=True)

    class Meta:
        verbose_name = _("Review")
        verbose_name_plural = _("Reviews")
        ordering = ["-created_at"]
        unique_together = ("product", "user")  # One review per user per product

    def __str__(self):
        return f"{self.user} - {self.product.name} ({self.rating}/5)"


class ReviewImage(models.Model):
    """
    Images attached to a product review.
    """
    review = models.ForeignKey(
        Review, 
        on_delete=models.CASCADE, 
        related_name="images", 
        verbose_name=_("review")
    )
    image = models.ImageField(_("image"), upload_to="reviews/")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Review Image")
        verbose_name_plural = _("Review Images")
