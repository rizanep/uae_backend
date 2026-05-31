from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from Users.models import SoftDeleteModel, User


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
    
    tag = models.CharField(
        _("tag"),
        max_length=100,
        blank=True,
        help_text=_("Tag for categorizing/filtering media (e.g. 'summer', 'sale', 'new')"),
    )
    highlight = models.TextField(
        _("highlight"),
        blank=True,
        help_text=_("Highlight text or badge to display on media"),
    )
    cta = models.CharField(
        _("call to action"),
        max_length=255,
        blank=True,
        help_text=_("Call-to-action text or link (e.g. 'Shop Now', 'Learn More', '/products/sale')"),
    )

    class Meta:
        verbose_name = _("Marketing Media")
        verbose_name_plural = _("Marketing Media")
        ordering = ["sort_order", "-created_at"]

    def __str__(self):
        return self.title or self.key


class Coupon(SoftDeleteModel):
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]

    code = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.TextField(blank=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES, default='percentage')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, help_text="Percentage value (0-100) or Fixed Amount")
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Max discount for percentage based coupons")
    
    valid_from = models.DateTimeField(default=timezone.now)
    valid_to = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    usage_limit = models.PositiveIntegerField(null=True, blank=True, help_text="Total number of times this coupon can be used")
    used_count = models.PositiveIntegerField(default=0)
    
    assigned_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_coupons', help_text="If set, only this user can use the coupon")
    
    is_referral_reward = models.BooleanField(default=False)
    is_first_order_reward = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("Coupon")
        verbose_name_plural = _("Coupons")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.code} ({self.discount_value} {self.discount_type})"

    def is_valid(self, user=None, order_amount=0):
        now = timezone.now()
        if not self.is_active:
            return False, "Coupon is inactive"
        if self.valid_to and now > self.valid_to:
            return False, "Coupon has expired"
        if self.valid_from and now < self.valid_from:
            return False, "Coupon is not yet valid"
        if self.usage_limit and self.used_count >= self.usage_limit:
            return False, "Coupon usage limit reached"
        if self.assigned_user and user and self.assigned_user != user:
            return False, "This coupon is not valid for your account"
        if order_amount < self.min_order_amount:
            return False, f"Minimum order amount of {self.min_order_amount} required"
        return True, "Valid"


class RewardConfiguration(models.Model):
    """
    Singleton model to manage reward scales and configuration.
    Controls referral rewards, first order rewards, and validity periods.
    """
    
    # First Order Reward Settings
    first_order_discount_type = models.CharField(
        max_length=20, 
        choices=[('percentage', 'Percentage'), ('fixed', 'Fixed Amount')],
        default='percentage'
    )
    first_order_discount_value = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=10.00,
        help_text="First order discount percentage or fixed amount"
    )
    first_order_min_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=50.00,
        help_text="Minimum order amount to use first order coupon"
    )
    first_order_validity_days = models.PositiveIntegerField(
        default=30, 
        help_text="Days from account creation when first order coupon is valid"
    )
    
    # Referral Reward Settings
    referral_discount_type = models.CharField(
        max_length=20, 
        choices=[('percentage', 'Percentage'), ('fixed', 'Fixed Amount')],
        default='percentage'
    )
    referral_discount_value = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=15.00,
        help_text="Referral reward discount percentage or fixed amount"
    )
    referral_min_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=100.00,
        help_text="Minimum order amount to use referral coupon"
    )
    referral_validity_days = models.PositiveIntegerField(
        default=60, 
        help_text="Days from referral when referral coupon is valid"
    )
    referral_usage_limit = models.PositiveIntegerField(
        default=1, 
        help_text="How many times each referral coupon can be used"
    )
    
    # Referrer Rewards
    referrer_discount_value = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=15.00,
        help_text="Discount given to referrer for successful referral"
    )
    referrer_validity_days = models.PositiveIntegerField(
        default=60, 
        help_text="Days from referral when referrer coupon is valid"
    )
    
    # Max Discount Settings
    max_discount_percentage = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Maximum discount cap for percentage-based coupons"
    )
    
    is_referral_active = models.BooleanField(default=True, help_text="Enable/disable referral rewards system")
    is_first_order_active = models.BooleanField(default=True, help_text="Enable/disable first order rewards")
    
    updated_by = models.ForeignKey(
        'Users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reward_config_updates'
    )
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Reward Configuration"
        verbose_name_plural = "Reward Configuration"
    
    def __str__(self):
        return "Reward Configuration"
    
    @classmethod
    def get_config(cls):
        """Get or create the singleton reward configuration."""
        config, created = cls.objects.get_or_create(pk=1)
        return config
