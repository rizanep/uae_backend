from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Notification, NotificationTemplate, Broadcast, NotificationType, ContactMessage

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "title", "message", "action_url", "is_read", "created_at"]
        read_only_fields = ["created_at"]


class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = ["id", "name", "type", "subject", "body", "created_at", "updated_at", "deleted_at"]
        read_only_fields = ["created_at", "updated_at", "deleted_at"]


class BroadcastSerializer(serializers.ModelSerializer):
    recipients = serializers.PrimaryKeyRelatedField(
        many=True, queryset=get_user_model().objects.all(), required=False
    )
    template = serializers.PrimaryKeyRelatedField(
        queryset=NotificationTemplate.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Broadcast
        fields = [
            "id",
            "subject",
            "message",
            "template",
            "type",
            "recipients",
            "send_to_all",
            "is_sent",
            "sent_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["is_sent", "sent_at", "created_at", "updated_at"]


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ["id", "name", "email", "subject", "message", "is_resolved", "created_at"]
        read_only_fields = ["name", "email", "is_resolved", "created_at"]
