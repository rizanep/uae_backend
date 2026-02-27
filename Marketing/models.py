from django.db import models
from django.utils.translation import gettext_lazy as _
from Users.models import SoftDeleteModel


class MarketingMedia(SoftDeleteModel):
    POSITION_CHOICES = [
        ("home_banner", "Home Banner"),
        ("category_banner", "Category Banner"),
        ("popup", "Popup"),
        ("announcement", "Announcement"),
    ]

    key = models.CharField(
        _("key"),
        max_length=100,
        db_index=True,
        help_text=_("Logical key, e.g. 'home_top_banner', 'festival_popup'"),
    )
    position = models.CharField(
        _("position"),
        max_length=50,
        choices=POSITION_CHOICES,
        default="home_banner",
    )
    title = models.CharField(_("title"), max_length=255, blank=True)
    subtitle = models.CharField(_("subtitle"), max_length=255, blank=True)
    description = models.TextField(_("description"), blank=True)
    image_mobile = models.ImageField(
        ("mobile image"),
        upload_to="marketing/mobile/",
        blank=True,
        null=True,
        help_text=_("Smaller image optimized for phones and small screens."),
    )
    image_desktop = models.ImageField(
        _("desktop image"),
        upload_to="marketing/desktop/",
        blank=True,
        null=True,
        help_text=_("Larger image for tablets/desktop."),
    )
    is_active = models.BooleanField(_("is active"), default=True)
    start_at = models.DateTimeField(_("start at"), blank=True, null=True)
    end_at = models.DateTimeField(_("end at"), blank=True, null=True)
    sort_order = models.PositiveIntegerField(_("sort order"), default=0)

    class Meta:
        verbose_name = _("Marketing Media")
        verbose_name_plural = _("Marketing Media")
        ordering = ["sort_order", "-created_at"]

    def __str__(self):
        return self.title or self.key
