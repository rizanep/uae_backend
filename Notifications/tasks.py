from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import ContactMessage


@shared_task
def send_contact_reply_email(contact_message_id, reply_message, mark_resolved=False):
    """
    Celery task to send reply email to contact message sender.
    
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

        # Mark as resolved if requested
        if mark_resolved:
            contact_msg.is_resolved = True
            contact_msg.save()

        return f"Reply email sent successfully to {contact_msg.email}"

    except Exception as e:
        return f"Failed to send reply email: {str(e)}"
