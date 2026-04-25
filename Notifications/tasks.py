from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.utils import timezone
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from .models import ContactMessage, Notification
from .services import UnifiedNotificationService

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
        # Render HTML email template
        html_message = render_to_string('Notifications/emails/contact_reply.html', {
            'contact_name': contact_msg.name,
            'original_message': contact_msg.message,
            'reply_message': reply_message,
            'is_resolved': mark_resolved,
            'site_url': settings.SITE_URL,
        })

        # Create plain text version
        subject = f"Re: {contact_msg.subject}"
        plain_message = f"""
Dear {contact_msg.name},

Thank you for contacting us. Here's our response to your message:

Your original message:
"{contact_msg.message}"

Our reply:
{reply_message}

Best regards,
Support Team
        """

        send_mail(
            subject,
            plain_message.strip(),
            settings.DEFAULT_FROM_EMAIL,
            [contact_msg.email],
            html_message=html_message,
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


@shared_task
def send_stock_notification_email(user_id, product_name):
    """
    Send email notification when product comes back in stock.
    """
    if not getattr(settings, "USE_REAL_SMTP", False):
        return f"Email disabled (console mode). Would send to user {user_id} about {product_name}"

    try:
        user = User.objects.get(id=user_id)
        if not user.email:
            return f"User {user_id} has no email"

        # Render HTML email template
        html_message = render_to_string('Notifications/emails/stock_notification.html', {
            'user': user,
            'product_name': product_name,
            'site_url': settings.SITE_URL,
        })

        # Create plain text version
        subject = f"Good news! {product_name} is back in stock"
        plain_message = f"""
Dear {user.first_name or user.email},

Great news! The product "{product_name}" that you were waiting for is now back in stock.

You can now place your order through our app.

Best regards,
Your Store Team
        """

        send_mail(
            subject=subject,
            message=plain_message.strip(),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return f"Stock notification email sent to {user.email}"

    except User.DoesNotExist:
        return f"User {user_id} not found"
    except Exception as e:
        return f"Failed to send stock notification email: {str(e)}"


@shared_task
def send_stock_notification_whatsapp(user_id, product_name):
    """
    Send WhatsApp notification when product comes back in stock.
    """
    if not getattr(settings, "USE_REAL_TWILIO_OTP", False):  # Reuse the setting
        return f"WhatsApp disabled (console mode). Would send to user {user_id} about {product_name}"

    try:
        user = User.objects.get(id=user_id)
        if not user.phone_number:
            return f"User {user_id} has no phone number"

        account_sid = settings.TWILIO_ACCOUNT_SID
        auth_token = settings.TWILIO_AUTH_TOKEN
        whatsapp_from = f"whatsapp:{settings.TWILIO_PHONE_NUMBER}"  # Assuming same number for WhatsApp

        if not all([account_sid, auth_token, whatsapp_from]):
            return "Twilio WhatsApp credentials not configured"

        client = Client(account_sid, auth_token)

        message_body = f"Good news! {product_name} is back in stock. You can now place your order!"

        message = client.messages.create(
            body=message_body,
            from_=whatsapp_from,
            to=f"whatsapp:{user.phone_number}"
        )
        return f"WhatsApp stock notification sent. SID: {message.sid}"

    except User.DoesNotExist:
        return f"User {user_id} not found"
    except TwilioRestException as e:
        return f"Twilio WhatsApp error: {e}"
    except Exception as e:
        return f"Failed to send WhatsApp stock notification: {str(e)}"


@shared_task
def send_otp_verification_email(user_id, otp_code):
    """
    Send OTP verification email to user.
    """
    if not getattr(settings, "USE_REAL_SMTP", False):
        return f"Email disabled (console mode). Would send OTP {otp_code} to user {user_id}"

    try:
        user = User.objects.get(id=user_id)
        if not user.email:
            return f"User {user_id} has no email"

        # Render HTML email template
        html_message = render_to_string('Notifications/emails/otp_verification.html', {
            'user': user,
            'otp_code': otp_code,
            'site_url': settings.SITE_URL,
        })

        # Create plain text version
        subject = "Your verification code"
        plain_message = f"""
Hello {user.first_name or 'there'},

Your verification code is: {otp_code}

This code will expire in 5 minutes.

If you didn't request this verification, please ignore this email.

Best regards,
Simak Fresh Team
        """

        send_mail(
            subject=subject,
            message=plain_message.strip(),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return f"OTP verification email sent to {user.email}"

    except User.DoesNotExist:
        return f"User {user_id} not found"
    except Exception as e:
        return f"Failed to send OTP verification email: {str(e)}"


@shared_task
def send_order_confirmed_email(order_id):
    """
    Send email when order status changes to PAID (confirmed).
    """
    if not getattr(settings, "USE_REAL_SMTP", False):
        return f"Email disabled (console mode). Would send order confirmation for order {order_id}"

    try:
        from Orders.models import Order
        order = Order.objects.select_related('user', 'shipping_address', 'delivery_slot').get(id=order_id)

        if not order.user.email:
            return f"User {order.user.id} has no email"

        # Render HTML email template
        html_message = render_to_string('Notifications/emails/order_confirmed.html', {
            'order': order,
            'site_url': settings.SITE_URL,
        })

        # Create plain text version
        subject = f"Order Confirmed - #{order.id}"
        plain_message = f"""
Dear {order.user.first_name or order.user.email},

Your order #{order.id} has been confirmed and payment has been successfully processed.

Order Details:
- Order ID: {order.id}
- Total Amount: AED {order.total_amount}
- Order Date: {order.created_at.strftime('%B %d, %Y')}

We'll send you another email when your order is out for delivery.

Thank you for choosing Simak Fresh!

Best regards,
Simak Fresh Team
        """

        send_mail(
            subject=subject,
            message=plain_message.strip(),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return f"Order confirmation email sent to {order.user.email}"

    except Order.DoesNotExist:
        return f"Order {order_id} not found"
    except Exception as e:
        return f"Failed to send order confirmation email: {str(e)}"


@shared_task
def send_order_delivered_email(order_id):
    """
    Send email when order status changes to DELIVERED.
    """
    if not getattr(settings, "USE_REAL_SMTP", False):
        return f"Email disabled (console mode). Would send order delivered notification for order {order_id}"

    try:
        from Orders.models import Order
        order = Order.objects.select_related('user', 'shipping_address').get(id=order_id)

        if not order.user.email:
            return f"User {order.user.id} has no email"

        # Render HTML email template
        html_message = render_to_string('Notifications/emails/order_delivered.html', {
            'order': order,
            'site_url': settings.SITE_URL,
        })

        # Create plain text version
        subject = f"Order Delivered - #{order.id}"
        plain_message = f"""
Dear {order.user.first_name or order.user.email},

Your order #{order.id} has been successfully delivered!

Delivery Details:
- Order ID: {order.id}
- Total Amount: AED {order.total_amount}
- Delivered On: {order.delivered_at or order.updated_at}

Thank you for choosing Simak Fresh! We hope you enjoyed your fresh products.

Please check your order upon delivery and contact us within 24 hours if you have any issues.

Best regards,
Simak Fresh Team
        """

        send_mail(
            subject=subject,
            message=plain_message.strip(),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return f"Order delivered email sent to {order.user.email}"

    except Order.DoesNotExist:
        return f"Order {order_id} not found"
    except Exception as e:
        return f"Failed to send order delivered email: {str(e)}"


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 3})
def send_login_otp_notification(self, otp_id, otp_platform='sms'):
    """
    Route login OTP through selected platform.

    - Email OTP uses email channel.
    - Phone OTP can use SMS (default) or WhatsApp.
    """
    from Users.models import OTPToken

    try:
        otp = OTPToken.objects.select_related('user').get(id=otp_id)
    except OTPToken.DoesNotExist:
        return f"OTP token {otp_id} not found"

    if otp.is_expired() or otp.is_verified:
        return f"OTP token {otp_id} is not active"

    if otp.otp_type == 'email':
        if not otp.email:
            return f"OTP token {otp_id} missing email"
        subject = "Your verification code"
        message = (
            f"Hello {otp.user.first_name or 'there'},\n\n"
            f"Your verification code is: {otp.otp_code}\n\n"
            "This code will expire in 5 minutes."
        )
        success, response = UnifiedNotificationService.send_email(
            recipient_email=otp.email,
            subject=subject,
            message=message,
        )
        return {'channel': 'email', 'success': success, 'response': response}

    if not otp.phone_number:
        return f"OTP token {otp_id} missing phone number"

    selected_platform = (otp_platform or 'sms').lower()
    otp_variables = {
        'VAR1': otp.otp_code,
        'body_1': otp.otp_code,
    }

    if selected_platform == 'whatsapp':
        success, response = UnifiedNotificationService.send_whatsapp(
            phone_number=otp.phone_number,
            template_name=getattr(settings, 'MSG91_OTP_WHATSAPP_TEMPLATE_NAME', ''),
            variables=otp_variables,
        )
        if success:
            return {'channel': 'whatsapp', 'success': True, 'response': response}

    success, response = UnifiedNotificationService.send_sms(
        phone_number=otp.phone_number,
        template_id=getattr(settings, 'MSG91_OTP_SMS_TEMPLATE_ID', ''),
        variables=otp_variables,
    )
    return {'channel': 'sms', 'success': success, 'response': response}


def _order_status_copy(order):
    status_label = order.get_status_display()
    user_name = order.user.first_name or order.user.email or 'Customer'

    status_messages = {
        'PENDING': {
            'subject': f"Action Needed: Complete Payment for Order #{order.id}",
            'message': (
                f"Hi {user_name}, your order #{order.id} is waiting for payment. "
                "Please complete payment now so we can confirm and start preparing it."
            ),
            'whatsapp_template': getattr(settings, 'MSG91_ORDER_PENDING_WHATSAPP_TEMPLATE_NAME', ''),
            'sms_template': getattr(settings, 'MSG91_ORDER_PENDING_SMS_TEMPLATE_ID', ''),
        },
        'PAID': {
            'subject': f"Order Confirmed: #{order.id}",
            'message': (
                f"Great news {user_name}! Payment received for order #{order.id}. "
                "Your order is confirmed and being prepared."
            ),
            'whatsapp_template': getattr(settings, 'MSG91_ORDER_PAID_WHATSAPP_TEMPLATE_NAME', ''),
            'sms_template': getattr(settings, 'MSG91_ORDER_PAID_SMS_TEMPLATE_ID', ''),
        },
        'PROCESSING': {
            'subject': f"Order Processing: #{order.id}",
            'message': (
                f"Hi {user_name}, your order #{order.id} is being carefully prepared. "
                "We will notify you when it is on the way."
            ),
            'whatsapp_template': getattr(settings, 'MSG91_ORDER_PROCESSING_WHATSAPP_TEMPLATE_NAME', ''),
            'sms_template': getattr(settings, 'MSG91_ORDER_PROCESSING_SMS_TEMPLATE_ID', ''),
        },
        'SHIPPED': {
            'subject': f"Order On The Way: #{order.id}",
            'message': (
                f"Awesome {user_name}! Your order #{order.id} is out for delivery. "
                "Please keep your phone reachable for delivery updates."
            ),
            'whatsapp_template': getattr(settings, 'MSG91_ORDER_SHIPPED_WHATSAPP_TEMPLATE_NAME', ''),
            'sms_template': getattr(settings, 'MSG91_ORDER_SHIPPED_SMS_TEMPLATE_ID', ''),
        },
        'DELIVERED': {
            'subject': f"Delivered Successfully: #{order.id}",
            'message': (
                f"Wonderful {user_name}! Your order #{order.id} has been delivered. "
                "Thank you for shopping with us."
            ),
            'whatsapp_template': getattr(settings, 'MSG91_ORDER_DELIVERED_WHATSAPP_TEMPLATE_NAME', ''),
            'sms_template': getattr(settings, 'MSG91_ORDER_DELIVERED_SMS_TEMPLATE_ID', ''),
        },
        'CANCELLED': {
            'subject': f"Order Cancelled: #{order.id}",
            'message': (
                f"Hi {user_name}, your order #{order.id} has been cancelled. "
                "If this was unexpected, please contact support."
            ),
            'whatsapp_template': getattr(settings, 'MSG91_ORDER_CANCELLED_WHATSAPP_TEMPLATE_NAME', ''),
            'sms_template': getattr(settings, 'MSG91_ORDER_CANCELLED_SMS_TEMPLATE_ID', ''),
        },
    }

    return status_messages.get(order.status, {
        'subject': f"Order Status Updated: {status_label} (#{order.id})",
        'message': f"Hi {user_name}, your order #{order.id} status is now {status_label}.",
        'whatsapp_template': '',
        'sms_template': '',
    })


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 3})
def send_order_status_multichannel_notification(self, order_id):
    """
    Send order lifecycle updates through WhatsApp, SMS, and email via a shared service layer.
    """
    from Orders.models import Order

    try:
        order = Order.objects.select_related('user').get(id=order_id)
    except Order.DoesNotExist:
        return f"Order {order_id} not found"

    content = _order_status_copy(order)
    user = order.user
    results = {
        'order_id': order.id,
        'status': order.status,
        'channels': {},
    }

    variables = {
        'VAR1': order.id,
        'VAR2': str(order.total_amount),
        'body_1': order.id,
        'body_2': str(order.total_amount),
        'body_3': order.get_status_display(),
    }

    if user.phone_number:
        wa_success, wa_response = UnifiedNotificationService.send_whatsapp(
            phone_number=user.phone_number,
            template_name=content['whatsapp_template'],
            variables=variables,
        )
        results['channels']['whatsapp'] = {'success': wa_success, 'response': wa_response}

        sms_success, sms_response = UnifiedNotificationService.send_sms(
            phone_number=user.phone_number,
            template_id=content['sms_template'],
            variables=variables,
        )
        results['channels']['sms'] = {'success': sms_success, 'response': sms_response}

    if user.email:
        email_success, email_response = UnifiedNotificationService.send_email(
            recipient_email=user.email,
            subject=content['subject'],
            message=content['message'],
        )
        results['channels']['email'] = {'success': email_success, 'response': email_response}

    return results


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 3})
def send_payment_receipt_multichannel_notification(self, payment_id):
    """
    Send payment receipt notification after successful payment and receipt creation.
    """
    from Orders.models import Payment

    try:
        payment = Payment.objects.select_related('order__user', 'receipt').get(id=payment_id)
    except Payment.DoesNotExist:
        return f"Payment {payment_id} not found"
    except Payment.receipt.RelatedObjectDoesNotExist:
        return f"Payment {payment_id} has no receipt"

    order = payment.order
    user = order.user
    receipt_number = payment.receipt.receipt_number
    issued_at = timezone.localtime(payment.receipt.generated_at).strftime('%Y-%m-%d %H:%M')

    subject = f"Payment Receipt - Order #{order.id}"
    message = (
        f"Hi {user.first_name or 'Customer'}, your payment for order #{order.id} is successful.\n"
        f"Receipt Number: {receipt_number}\n"
        f"Amount: AED {payment.amount}\n"
        f"Issued At: {issued_at}"
    )

    variables = {
        'VAR1': order.id,
        'VAR2': receipt_number,
        'VAR3': str(payment.amount),
        'body_1': order.id,
        'body_2': receipt_number,
        'body_3': str(payment.amount),
    }

    results = {
        'payment_id': payment.id,
        'order_id': order.id,
        'channels': {},
    }

    if user.phone_number:
        wa_success, wa_response = UnifiedNotificationService.send_whatsapp(
            phone_number=user.phone_number,
            template_name=getattr(settings, 'MSG91_PAYMENT_RECEIPT_WHATSAPP_TEMPLATE_NAME', ''),
            variables=variables,
        )
        results['channels']['whatsapp'] = {'success': wa_success, 'response': wa_response}

        sms_success, sms_response = UnifiedNotificationService.send_sms(
            phone_number=user.phone_number,
            template_id=getattr(settings, 'MSG91_PAYMENT_RECEIPT_SMS_TEMPLATE_ID', ''),
            variables=variables,
        )
        results['channels']['sms'] = {'success': sms_success, 'response': sms_response}

    if user.email:
        email_success, email_response = UnifiedNotificationService.send_email(
            recipient_email=user.email,
            subject=subject,
            message=message,
        )
        results['channels']['email'] = {'success': email_success, 'response': email_response}

    return results
