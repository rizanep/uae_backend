from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import ContactMessage, Notification

User = get_user_model()


@shared_task
def send_contact_reply_email(contact_message_id, reply_message, mark_resolved=False):
    """
    Celery task to send reply email to contact message sender.
    Also creates in-app notification for the user.
    
    Args:
        contact_message_id: ID of the ContactMessage instance
        reply_message: Admin's reply message
        mark_resolved: Whether to mark the message as resolved
    """
    try:
        contact_msg = ContactMessage.objects.get(id=contact_message_id)
    except ContactMessage.DoesNotExist:
        return f"Contact message with ID {contact_message_id} not found"

    # Compose reply email
    subject = f"Re: {contact_msg.subject}"
    message = f"""
Dear {contact_msg.name},

Thank you for contacting us. Here's our response to your message:

Your original message:
"{contact_msg.message}"

Our reply:
{reply_message}

Best regards,
Support Team
    """

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [contact_msg.email],
            fail_silently=False,
        )

        # Create in-app notification for the user
        Notification.objects.create(
            user=contact_msg.user,
            title="Response to Your Message",
            message=f"We have replied to your message: {contact_msg.subject}\n\n{reply_message[:100]}..."
        )

        # Mark as resolved if requested
        if mark_resolved:
            contact_msg.is_resolved = True
            contact_msg.save()
            
            # Create notification about resolution
            Notification.objects.create(
                user=contact_msg.user,
                title="Your Message Has Been Resolved",
                message=f"Your inquiry about '{contact_msg.subject}' has been marked as resolved."
            )

        return f"Reply email sent successfully to {contact_msg.email} and notification created"

    except Exception as e:
        return f"Failed to send reply email: {str(e)}"
