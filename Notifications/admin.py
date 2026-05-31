from django.contrib import admin
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from .models import NotificationTemplate, Notification, Broadcast, NotificationType, FCMDevice
from .tasks import send_broadcast_push_task
from .services import UnifiedNotificationService

@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "type", "created_at"]
    list_filter = ["type"]
    search_fields = ["name", "subject", "body"]

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["user", "title", "is_read", "created_at"]
    list_filter = ["is_read", "created_at"]
    search_fields = ["user__email", "user__phone_number", "title", "message"]
    readonly_fields = ["created_at", "updated_at"]

@admin.register(Broadcast)
class BroadcastAdmin(admin.ModelAdmin):
    list_display = ["subject", "template", "type", "image", "send_to_all", "is_sent", "sent_at", "created_at"]
    list_filter = ["type", "is_sent", "created_at", "template"]
    search_fields = ["subject", "message"]
    filter_horizontal = ["recipients"]
    actions = ["send_broadcast"]
    fieldsets = (
        (None, {
            "fields": ("template", "subject", "message", "type", "image")
        }),
        (_("Recipients"), {
            "fields": ("send_to_all", "recipients")
        }),
        (_("Status"), {
            "fields": ("is_sent", "sent_at")
        }),
    )
    readonly_fields = ["is_sent", "sent_at", "created_at"]

    def send_broadcast(self, request, queryset):
        User = get_user_model()
        sent_count = 0
        
        for broadcast in queryset:
            if broadcast.is_sent:
                continue

            if broadcast.type == NotificationType.PUSH:
                # Queue async push delivery to avoid blocking admin request.
                send_broadcast_push_task.delay(broadcast.id)
                broadcast.is_sent = True
                broadcast.sent_at = timezone.now()
                broadcast.save(update_fields=["is_sent", "sent_at"])
                sent_count += 1
                continue
            
            # Determine recipients
            if broadcast.send_to_all:
                recipients = User.objects.filter(is_active=True)
            else:
                recipients = broadcast.recipients.all()

            for user in recipients:
                if broadcast.type == NotificationType.IN_APP:
                    Notification.objects.create(
                        user=user,
                        title=broadcast.subject or "Notification",
                        message=broadcast.message
                    )
                elif broadcast.type == NotificationType.EMAIL:
                    if user.email:
                        UnifiedNotificationService.send_email(
                            recipient_email=user.email,
                            subject=broadcast.subject or "Notification",
                            message=broadcast.message,
                        )
                elif broadcast.type == NotificationType.SMS:
                    if user.phone_number:
                        UnifiedNotificationService.send_sms(
                            phone_number=user.phone_number,
                            template_id=getattr(settings, 'MSG91_BROADCAST_SMS_TEMPLATE_ID', None),
                            variables={'VAR1': broadcast.subject or '', 'body_1': broadcast.message},
                        )
                elif broadcast.type == NotificationType.WHATSAPP:
                    if user.phone_number:
                        UnifiedNotificationService.send_whatsapp(
                            phone_number=user.phone_number,
                            template_name=getattr(settings, 'MSG91_BROADCAST_WHATSAPP_TEMPLATE_NAME', None),
                            variables={'VAR1': broadcast.subject or '', 'body_1': broadcast.message},
                        )

            broadcast.is_sent = True
            broadcast.sent_at = timezone.now()
            broadcast.save()
            sent_count += 1
            
        self.message_user(request, _(f"{sent_count} broadcasts sent successfully."))
    
    send_broadcast.short_description = _("Send selected broadcasts now")


@admin.register(FCMDevice)
class FCMDeviceAdmin(admin.ModelAdmin):
    list_display = ["user", "device_type", "device_name", "is_active", "created_at"]
    list_filter = ["device_type", "is_active", "created_at"]
    search_fields = ["user__email", "device_name", "registration_token"]
    readonly_fields = ["created_at", "updated_at"]
