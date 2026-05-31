from celery import shared_task
from django.conf import settings
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from Notifications.email_service import EmailService


@shared_task
<<<<<<< HEAD
def send_email_task(subject, message, recipient_list, from_email=None, html_message=None, html_template=None, template_context=None):
  """Generic Celery email task — respects USE_REAL_SMTP via EmailService."""
  if not isinstance(recipient_list, (list, tuple)):
    recipient_list = [recipient_list]

  results = []
  for recipient in recipient_list:
    success, response = EmailService.send(
      recipient_email=recipient,
      subject=subject,
      plain_message=message,
      html_template=html_template,
      template_context=template_context,
=======
def send_email_task(subject, message, recipient_list, from_email=None, html_message=None):
    if not getattr(settings, "USE_REAL_SMTP", False):
        print(
            "[EMAIL CONSOLE MODE] "
            f"subject={subject!r} recipients={recipient_list} html={bool(html_message)}"
        )
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
>>>>>>> dev
    )
    results.append({"recipient": recipient, "success": success, "response": response})
  return results


@shared_task
def send_otp_via_twilio(phone_number, otp_code):
    """
    Sends an OTP via SMS using Twilio.
    """
    if not getattr(settings, "USE_REAL_TWILIO_OTP", False):
        print(f"USE_REAL_TWILIO_OTP is False. Skipping real SMS. OTP: {otp_code} to {phone_number}")
        return "Twilio disabled (console mode)"
    account_sid = settings.TWILIO_ACCOUNT_SID
    auth_token = settings.TWILIO_AUTH_TOKEN
    from_number = settings.TWILIO_PHONE_NUMBER

    if not all([account_sid, auth_token, from_number]):
        print("Twilio credentials not configured.")
        return "Twilio credentials missing"

    client = Client(account_sid, auth_token)

    try:
        message = client.messages.create(
            body=f"Your verification code is: {otp_code}",
            from_=from_number,
            to=phone_number
        )
        return f"OTP sent successfully. SID: {message.sid}"
    except TwilioRestException as e:
        print(f"Twilio Error: {e}")
        return f"Failed to send OTP: {e}"
