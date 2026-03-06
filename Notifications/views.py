from rest_framework import viewsets, mixins, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from Users.permissions import IsAdmin
from .models import Notification, Broadcast, NotificationTemplate, NotificationType, ContactMessage
from .serializers import (
    NotificationSerializer,
    BroadcastSerializer,
    NotificationTemplateSerializer,
    ContactMessageSerializer
)

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
        return Notification.objects.filter(user=self.request.user).order_by("-created_at")

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
    queryset = Broadcast.objects.all().order_by("-created_at")
    serializer_class = BroadcastSerializer
    permission_classes = [IsAdmin]

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        broadcast = self.get_object()
        if broadcast.is_sent:
            return Response({"detail": "Broadcast already sent."}, status=status.HTTP_400_BAD_REQUEST)

        User = get_user_model()

        # Determine recipients
        if broadcast.send_to_all:
            recipients = User.objects.all()
        else:
            recipients = broadcast.recipients.all()

        # Resolve template defaults if provided
        template = broadcast.template
        subject = broadcast.subject or (template.subject if template else None) or "Notification"
        message = broadcast.message or (template.body if template else "")
        notif_type = broadcast.type
        if notif_type == NotificationType.IN_APP and template and template.type != NotificationType.IN_APP:
            notif_type = template.type

        # Send notifications (mock for non IN_APP types)
        sent_count = 0
        for user in recipients:
            if notif_type == NotificationType.IN_APP:
                Notification.objects.create(
                    user=user,
                    title=subject,
                    message=message,
                )
                sent_count += 1
            elif notif_type == NotificationType.EMAIL:
                print(f"Mock Sending Email to {user}: {subject}")
                sent_count += 1
            elif notif_type == NotificationType.SMS:
                print(f"Mock Sending SMS to {user}: {message}")
                sent_count += 1
            elif notif_type == NotificationType.PUSH:
                print(f"Mock Sending Push to {user}: {message}")
                sent_count += 1

        broadcast.is_sent = True
        broadcast.sent_at = timezone.now()
        broadcast.subject = subject
        broadcast.message = message
        broadcast.type = notif_type
        broadcast.save()
        
        return Response({"detail": f"Broadcast sent to {sent_count} recipients."}, status=status.HTTP_200_OK)


class ContactMessageViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    API for 'Contact Us' form.
    Only allows authenticated users with verified emails to send messages.
    """
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer, **kwargs):
        serializer.save(**kwargs)

    def create(self, request, *args, **kwargs):
        if not request.user.is_email_verified:
            return Response(
                {"detail": "Your email must be verified to send a message."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Auto-fill name and email from authenticated user
        user_name = request.user.get_full_name() or request.user.email
        self.perform_create(serializer, name=user_name, email=request.user.email)
        
        # Send Email to Admin
        contact_msg = serializer.instance
        
        subject = f"New Contact Message: {contact_msg.subject}"
        message = f"""
You have received a new message from the contact form.

Name: {contact_msg.name}
Email: {contact_msg.email}
Subject: {contact_msg.subject}

Message:
{contact_msg.message}
        """
        
        # Send from DEFAULT_FROM_EMAIL to DEFAULT_FROM_EMAIL (Admin)
        # Reply-to is set to the user's email
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [settings.DEFAULT_FROM_EMAIL], 
                fail_silently=False,
                reply_to=[contact_msg.email]
            )
        except Exception as e:
            # Log error but don't fail the request if DB save was successful
            print(f"Error sending contact email: {e}")

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
