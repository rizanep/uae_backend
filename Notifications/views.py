from rest_framework import viewsets, mixins, status, permissions
from rest_framework.decorators import action, throttle_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from django.contrib.auth import get_user_model
from Users.permissions import IsAdmin
from core.throttling import UserContactThrottle, AnonContactThrottle
from .models import Notification, Broadcast, NotificationTemplate, NotificationType, ContactMessage
from .serializers import (
    NotificationSerializer,
    BroadcastSerializer,
    NotificationTemplateSerializer,
    ContactMessageSerializer
)
from .tasks import send_contact_reply_email

class NotificationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).select_related('user').order_by("-created_at")

    @action(detail=False, methods=["post"])
    def mark_all_as_read(self, request):
        self.get_queryset().update(is_read=True)
        return Response({"status": "success"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({"status": "success"}, status=status.HTTP_200_OK)


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    queryset = NotificationTemplate.objects.filter(deleted_at__isnull=True)
    serializer_class = NotificationTemplateSerializer
    permission_classes = [IsAdmin]


class BroadcastViewSet(viewsets.ModelViewSet):
    queryset = Broadcast.objects.select_related('template').prefetch_related('recipients').order_by("-created_at")
    serializer_class = BroadcastSerializer
    permission_classes = [IsAdmin]

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        broadcast = self.get_object()
        if broadcast.is_sent:
            return Response({"detail": "Broadcast already sent."}, status=status.HTTP_400_BAD_REQUEST)

        User = get_user_model()

        # Determine recipients (use values_list for optimization)
        if broadcast.send_to_all:
            recipient_ids = User.objects.values_list('id', flat=True)
        else:
            recipient_ids = broadcast.recipients.values_list('id', flat=True)

        # Resolve template defaults if provided
        template = broadcast.template
        subject = broadcast.subject or (template.subject if template else None) or "Notification"
        message = broadcast.message or (template.body if template else "")
        notif_type = broadcast.type
        if notif_type == NotificationType.IN_APP and template and template.type != NotificationType.IN_APP:
            notif_type = template.type

        # Send notifications (mock for non IN_APP types)
        sent_count = 0
        if notif_type == NotificationType.IN_APP:
            # Bulk create for IN_APP notifications (much faster)
            notifications = [
                Notification(
                    user_id=user_id,
                    title=subject,
                    message=message,
                )
                for user_id in recipient_ids
            ]
            Notification.objects.bulk_create(notifications, batch_size=1000)
            sent_count = len(notifications)
        else:
            # For other types, still iterate but get user count only
            sent_count = len(list(recipient_ids))
            for user_id in recipient_ids:
                if notif_type == NotificationType.EMAIL:
                    print(f"Mock Sending Email to user {user_id}: {subject}")
                elif notif_type == NotificationType.SMS:
                    print(f"Mock Sending SMS to user {user_id}: {message}")
                elif notif_type == NotificationType.PUSH:
                    print(f"Mock Sending Push to user {user_id}: {message}")

        broadcast.is_sent = True
        broadcast.sent_at = timezone.now()
        broadcast.subject = subject
        broadcast.message = message
        broadcast.type = notif_type
        broadcast.save()
        
        return Response({"detail": f"Broadcast sent to {sent_count} recipients."}, status=status.HTTP_200_OK)


class ContactMessageViewSet(viewsets.ModelViewSet):
    """
    API for 'Contact Us' form.
    - Authenticated users with verified emails can send messages (rate limited: 10/hour)
    - Anonymous users can send messages (rate limited: 3/hour)
    - Admin users can view all messages and reply to them via email
    """
    queryset = ContactMessage.objects.all().order_by("-created_at")
    serializer_class = ContactMessageSerializer

    def get_throttles(self):
        """Apply strict throttling for contact message creation to prevent spam"""
        if self.action == 'create':
            return [UserContactThrottle(), AnonContactThrottle()]
        # Default throttling for other actions
        return super().get_throttles()

    def get_permissions(self):
        """
        Different permissions for different actions:
        - list/retrieve: Admin only
        - create: Authenticated users only
        - reply: Admin only
        """
        if self.action in ['list', 'retrieve']:
            return [IsAdmin()]
        elif self.action == 'reply':
            return [IsAdmin()]
        elif self.action == 'create':
            return [IsAuthenticated()]
        return [IsAuthenticated()]

    def get_queryset(self):
        """
        Admin sees all messages, regular users see none (no list access for non-admins).
        """
        if self.request.user.role == 'admin':
            return ContactMessage.objects.all().order_by("-created_at")
        return ContactMessage.objects.none()

    def create(self, request, *args, **kwargs):
        """
        Only authenticated users with verified email can send messages.
        Messages are automatically associated with the user's name and email.
        Creates notifications for all admin users.
        """
        if not request.user.is_email_verified:
            return Response(
                {"detail": "Your email must be verified to send a message."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Auto-fill name and email from authenticated user
        user_name = request.user.get_full_name() or request.user.email
        serializer.validated_data['name'] = user_name
        serializer.validated_data['email'] = request.user.email
        serializer.validated_data['user'] = request.user
        
        self.perform_create(serializer)

        # Create notifications for all admin users
        contact_msg = serializer.instance
        User = get_user_model()
        admin_users = User.objects.filter(role='admin', is_active=True)
        
        notifications = [
            Notification(
                user=admin,
                title=f"New Contact Message from {contact_msg.name}",
                message=f"Subject: {contact_msg.subject}\n\n{contact_msg.message[:100]}..."
            )
            for admin in admin_users
        ]
        Notification.objects.bulk_create(notifications)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=["post"], permission_classes=[IsAdmin])
    def reply(self, request, pk=None):
        """
        Admin can reply to a contact message via email (asynchronous task).
        Sends reply to the user's email address who submitted the message.
        """
        contact_msg = self.get_object()
        reply_message = request.data.get('reply_message')

        if not reply_message:
            return Response(
                {"detail": "Reply message is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Queue the email task to be processed asynchronously
        mark_resolved = request.data.get('mark_resolved', False)
        send_contact_reply_email.delay(
            contact_message_id=contact_msg.id,
            reply_message=reply_message,
            mark_resolved=mark_resolved
        )

        return Response(
            {"detail": "Reply is being sent. Email will be delivered shortly."},
            status=status.HTTP_200_OK
        )
