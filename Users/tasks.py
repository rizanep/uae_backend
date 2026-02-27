from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings


@shared_task
def send_email_task(subject, message, recipient_list, from_email=None, html_message=None):
    if not getattr(settings, "USE_REAL_SMTP", False):
        return 0
    from_email = from_email or settings.DEFAULT_FROM_EMAIL
    if not isinstance(recipient_list, (list, tuple)):
        recipient_list = [recipient_list]
    return send_mail(
        subject=subject,
        message=message,
        from_email=from_email,
        recipient_list=recipient_list,
        html_message=html_message,
    )
