from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from Users.models import TimestampedModel, SoftDeleteModel

class NotificationType(models.TextChoices):
    EMAIL = 'EMAIL', _('Email')
    SMS = 'SMS', _('SMS')
    PUSH = 'PUSH', _('Push Notification')
    IN_APP = 'IN_APP', _('In-App Notification')

class NotificationTemplate(SoftDeleteModel):
    name = models.CharField(_("template name"), max_length=100)
    type = models.CharField(_("type"), max_length=20, choices=NotificationType.choices)
    subject = models.CharField(_("subject"), max_length=255, blank=True, help_text=_("Subject for Email/Push"))
    body = models.TextField(_("body"), help_text=_("Content. Use {{ user.first_name }} for dynamic values."))
    
    class Meta:
        verbose_name = _("Notification Template")
        verbose_name_plural = _("Notification Templates")

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"

class Notification(TimestampedModel):
    """
    In-App notifications for users.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(_("title"), max_length=255)
    message = models.TextField(_("message"))
    action_url = models.CharField(_("action URL"), max_length=500, blank=True, null=True)
    is_read = models.BooleanField(_("is read"), default=False)
    
    class Meta:
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.title}"

class Broadcast(TimestampedModel):
    """
    For Admin to send bulk notifications.
    """
    subject = models.CharField(_("subject"), max_length=255, blank=True)
    message = models.TextField(_("message"), blank=True)
    template = models.ForeignKey(NotificationTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name="broadcasts")
    type = models.CharField(_("type"), max_length=20, choices=NotificationType.choices, default=NotificationType.IN_APP)
    recipients = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="broadcasts")
    send_to_all = models.BooleanField(_("send to all users"), default=False)
    is_sent = models.BooleanField(_("is sent"), default=False)
    sent_at = models.DateTimeField(_("sent at"), null=True, blank=True)

    class Meta:
        verbose_name = _("Broadcast Message")
        verbose_name_plural = _("Broadcast Messages")

    def __str__(self):
        return f"Broadcast: {self.subject or self.message[:50]} ({self.get_type_display()})"
    
    def save(self, *args, **kwargs):
        if self.template:
            if not self.message:
                self.message = self.template.body
            if not self.subject:
                self.subject = self.template.subject
            if self.type == NotificationType.IN_APP and self.template.type != NotificationType.IN_APP:
                # If user didn't change type from default, use template type
                self.type = self.template.type
        super().save(*args, **kwargs)


class ContactMessage(TimestampedModel):
    """
    Stores 'Contact Us' messages from users.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="contact_messages", null=True, blank=True)
    name = models.CharField(_("full name"), max_length=255)
    email = models.EmailField(_("email address"))
    subject = models.CharField(_("subject"), max_length=255)
    message = models.TextField(_("message"), max_length=2000)
    is_resolved = models.BooleanField(_("is resolved"), default=False)

    class Meta:
        verbose_name = _("Contact Message")
        verbose_name_plural = _("Contact Messages")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.subject} - {self.email}"


class DeviceType(models.TextChoices):
    WEB = 'WEB', _('Web')
    ANDROID = 'ANDROID', _('Android')
    IOS = 'IOS', _('iOS')


class FCMDevice(TimestampedModel):
    """
    Stores FCM registration tokens for push notifications.
    A user can have multiple devices/tokens.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="fcm_devices",
    )
    registration_token = models.TextField(_("FCM registration token"), unique=True)
    device_type = models.CharField(
        _("device type"),
        max_length=10,
        choices=DeviceType.choices,
        default=DeviceType.WEB,
    )
    device_name = models.CharField(_("device name"), max_length=255, blank=True)
    is_active = models.BooleanField(_("is active"), default=True)

    class Meta:
        verbose_name = _("FCM Device")
        verbose_name_plural = _("FCM Devices")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.device_type} ({self.registration_token[:20]}...)"
