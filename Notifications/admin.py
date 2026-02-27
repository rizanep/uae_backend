from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from .models import NotificationTemplate, Notification, Broadcast, NotificationType

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
    list_display = ["subject", "template", "type", "send_to_all", "is_sent", "sent_at", "created_at"]
    list_filter = ["type", "is_sent", "created_at", "template"]
    search_fields = ["subject", "message"]
    filter_horizontal = ["recipients"]
    actions = ["send_broadcast"]
    fieldsets = (
        (None, {
            "fields": ("template", "subject", "message", "type")
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
            
            # Determine recipients
            if broadcast.send_to_all:
                recipients = User.objects.all()
            else:
                recipients = broadcast.recipients.all()
            
            # Send to each recipient
            for user in recipients:
                if broadcast.type == NotificationType.IN_APP:
                    Notification.objects.create(
                        user=user,
                        title=broadcast.subject or "Notification",
                        message=broadcast.message
                    )
                elif broadcast.type == NotificationType.EMAIL:
                    # Mock Email
                    print(f"Mock Sending Email to {user}: {broadcast.subject}")
                elif broadcast.type == NotificationType.SMS:
                    # Mock SMS
                    print(f"Mock Sending SMS to {user}: {broadcast.message}")
                elif broadcast.type == NotificationType.PUSH:
                    # Mock Push
                    print(f"Mock Sending Push to {user}: {broadcast.message}")

            broadcast.is_sent = True
            broadcast.sent_at = timezone.now()
            broadcast.save()
            sent_count += 1
            
        self.message_user(request, _(f"{sent_count} broadcasts sent successfully."))
    
    send_broadcast.short_description = _("Send selected broadcasts now")
