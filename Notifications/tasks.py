from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from .email_service import EmailService
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

    subject = f"Re: {contact_msg.subject}"
    plain_message = f"""Dear {contact_msg.name},

Thank you for contacting us. Here's our response to your message:

Your original message:
"{contact_msg.message}"

Our reply:
{reply_message}

Best regards,
Support Team"""

    try:
        success, response = EmailService.send(
            recipient_email=contact_msg.email,
            subject=subject,
            plain_message=plain_message,
            html_template="Notifications/emails/contact_reply.html",
            template_context={
                "contact_name": contact_msg.name,
                "original_message": contact_msg.message,
                "reply_message": reply_message,
                "is_resolved": mark_resolved,
            },
        )
        if not success:
            return f"Failed to send reply email: {response}"

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
    """Send email notification when product comes back in stock."""
    try:
        user = User.objects.get(id=user_id)
        if not user.email:
            return f"User {user_id} has no email"

        subject = f"Good news! {product_name} is back in stock"
        plain_message = (
            f"Dear {user.first_name or user.email},\n\n"
            f'"{product_name}" is back in stock. You can place your order in the app.\n\n'
            f"Best regards,\n{settings.APP_NAME} Team"
        )
        success, response = EmailService.send(
            recipient_email=user.email,
            subject=subject,
            plain_message=plain_message,
            html_template="Notifications/emails/stock_notification.html",
            template_context={"user": user, "product_name": product_name},
        )
        if success:
            return f"Stock notification email sent to {user.email}"
        return f"Failed to send stock notification email: {response}"

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


def _send_otp_verification_email_to(recipient_email, user, otp_code):
    subject = "Your verification code"
    plain_message = (
        f"Hello {user.first_name or 'there'},\n\n"
        f"Your verification code is: {otp_code}\n\n"
        "This code will expire in 5 minutes.\n\n"
        "If you didn't request this verification, please ignore this email."
    )
    return EmailService.send(
        recipient_email=recipient_email,
        subject=subject,
        plain_message=plain_message,
        html_template="Notifications/emails/otp_verification.html",
        template_context={"user": user, "otp_code": otp_code},
    )


@shared_task
def send_otp_verification_email(user_id, otp_code):
    """Send OTP verification email to user."""
    try:
        user = User.objects.get(id=user_id)
        if not user.email:
            return f"User {user_id} has no email"
        success, response = _send_otp_verification_email_to(user.email, user, otp_code)
        if success:
            return f"OTP verification email sent to {user.email}"
        return f"Failed to send OTP verification email: {response}"
    except User.DoesNotExist:
        return f"User {user_id} not found"
    except Exception as e:
        return f"Failed to send OTP verification email: {str(e)}"


def _send_order_confirmed_email_to(recipient_email, order):
    subject = f"Order Confirmed - #{order.id}"
    plain_message = (
        f"Dear {order.user.first_name or order.user.email},\n\n"
        f"Your order #{order.id} has been confirmed. Total: AED {order.total_amount}.\n\n"
        f"Thank you for choosing {settings.APP_NAME}!"
    )
    return EmailService.send(
        recipient_email=recipient_email,
        subject=subject,
        plain_message=plain_message,
        html_template="Notifications/emails/order_confirmed.html",
        template_context={"order": order},
    )


@shared_task
def send_order_confirmed_email(order_id):
    """Send email when order is confirmed (PAID)."""
    from Orders.models import Order

    try:
        order = Order.objects.select_related(
            "user", "shipping_address", "preferred_delivery_slot"
        ).prefetch_related("items").get(id=order_id)
        if not order.user.email:
            return f"User {order.user.id} has no email"
        success, response = _send_order_confirmed_email_to(order.user.email, order)
        if success:
            return f"Order confirmation email sent to {order.user.email}"
        return f"Failed to send order confirmation email: {response}"
    except Order.DoesNotExist:
        return f"Order {order_id} not found"
    except Exception as e:
        return f"Failed to send order confirmation email: {str(e)}"


def _send_order_delivered_email_to(recipient_email, order):
    subject = f"Order Delivered - #{order.id}"
    plain_message = (
        f"Dear {order.user.first_name or order.user.email},\n\n"
        f"Your order #{order.id} has been delivered. Total: AED {order.total_amount}.\n\n"
        f"Thank you for choosing {settings.APP_NAME}!"
    )
    return EmailService.send(
        recipient_email=recipient_email,
        subject=subject,
        plain_message=plain_message,
        html_template="Notifications/emails/order_delivered.html",
        template_context={"order": order},
    )


@shared_task
def send_order_delivered_email(order_id):
    """Send email when order status is DELIVERED."""
    from Orders.models import Order

    try:
        order = Order.objects.select_related("user", "shipping_address").prefetch_related("items").get(
            id=order_id
        )
        if not order.user.email:
            return f"User {order.user.id} has no email"
        success, response = _send_order_delivered_email_to(order.user.email, order)
        if success:
            return f"Order delivered email sent to {order.user.email}"
        return f"Failed to send order delivered email: {response}"
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
        success, response = EmailService.send(
            recipient_email=otp.email,
            subject=subject,
            plain_message=message,
            html_template="Notifications/emails/otp_verification.html",
            template_context={"user": otp.user, "otp_code": otp.otp_code},
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
            'headline': 'Complete your payment',
            'html_template': 'Notifications/emails/order_status_update.html',
            'whatsapp_template': getattr(settings, 'MSG91_ORDER_PENDING_WHATSAPP_TEMPLATE_NAME', ''),
            'sms_template': getattr(settings, 'MSG91_ORDER_PENDING_SMS_TEMPLATE_ID', ''),
        },
        'PAID': {
            'subject': f"Order Confirmed: #{order.id}",
            'message': (
                f"Great news {user_name}! Payment received for order #{order.id}. "
                "Your order is confirmed and being prepared."
            ),
            'headline': 'Order confirmed',
            'html_template': 'Notifications/emails/order_confirmed.html',
            'whatsapp_template': getattr(settings, 'MSG91_ORDER_PAID_WHATSAPP_TEMPLATE_NAME', ''),
            'sms_template': getattr(settings, 'MSG91_ORDER_PAID_SMS_TEMPLATE_ID', ''),
        },
        'PROCESSING': {
            'subject': f"Order Processing: #{order.id}",
            'message': (
                f"Hi {user_name}, your order #{order.id} is being carefully prepared. "
                "We will notify you when it is on the way."
            ),
            'headline': 'Order is being prepared',
            'html_template': 'Notifications/emails/order_status_update.html',
            'whatsapp_template': getattr(settings, 'MSG91_ORDER_PROCESSING_WHATSAPP_TEMPLATE_NAME', ''),
            'sms_template': getattr(settings, 'MSG91_ORDER_PROCESSING_SMS_TEMPLATE_ID', ''),
        },
        'SHIPPED': {
            'subject': f"Order On The Way: #{order.id}",
            'message': (
                f"Awesome {user_name}! Your order #{order.id} is out for delivery. "
                "Please keep your phone reachable for delivery updates."
            ),
            'headline': 'Order on the way',
            'html_template': 'Notifications/emails/order_status_update.html',
            'whatsapp_template': getattr(settings, 'MSG91_ORDER_SHIPPED_WHATSAPP_TEMPLATE_NAME', ''),
            'sms_template': getattr(settings, 'MSG91_ORDER_SHIPPED_SMS_TEMPLATE_ID', ''),
        },
        'DELIVERED': {
            'subject': f"Delivered Successfully: #{order.id}",
            'message': (
                f"Wonderful {user_name}! Your order #{order.id} has been delivered. "
                "Thank you for shopping with us."
            ),
            'headline': 'Order delivered',
            'html_template': 'Notifications/emails/order_delivered.html',
            'whatsapp_template': getattr(settings, 'MSG91_ORDER_DELIVERED_WHATSAPP_TEMPLATE_NAME', ''),
            'sms_template': getattr(settings, 'MSG91_ORDER_DELIVERED_SMS_TEMPLATE_ID', ''),
        },
        'CANCELLED': {
            'subject': f"Order Cancelled: #{order.id}",
            'message': (
                f"Hi {user_name}, your order #{order.id} has been cancelled. "
                "If this was unexpected, please contact support."
            ),
            'headline': 'Order cancelled',
            'html_template': 'Notifications/emails/order_status_update.html',
            'whatsapp_template': getattr(settings, 'MSG91_ORDER_CANCELLED_WHATSAPP_TEMPLATE_NAME', ''),
            'sms_template': getattr(settings, 'MSG91_ORDER_CANCELLED_SMS_TEMPLATE_ID', ''),
        },
    }

    return status_messages.get(order.status, {
        'subject': f"Order Status Updated: {status_label} (#{order.id})",
        'message': f"Hi {user_name}, your order #{order.id} status is now {status_label}.",
        'headline': f"Order status: {status_label}",
        'html_template': 'Notifications/emails/order_status_update.html',
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
        order = Order.objects.select_related(
            'user', 'shipping_address', 'preferred_delivery_slot'
        ).prefetch_related('items').get(id=order_id)
    except Order.DoesNotExist:
        return f"Order {order_id} not found"

    content = _order_status_copy(order)
    user = order.user
    user_name = user.first_name or user.email or 'Customer'
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
        email_success, email_response = EmailService.send(
            recipient_email=user.email,
            subject=content['subject'],
            plain_message=content['message'],
            html_template=content.get('html_template'),
            template_context={
                'order': order,
                'user_name': user_name,
                'headline': content.get('headline', content['subject']),
                'body_message': content['message'],
                'status_label': order.get_status_display(),
                'subject_line': content['subject'],
            },
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
        payment = Payment.objects.select_related(
            'order__user',
            'order__shipping_address',
            'receipt',
        ).prefetch_related('order__items').get(id=payment_id)
    except Payment.DoesNotExist:
        return f"Payment {payment_id} not found"
    except Payment.receipt.RelatedObjectDoesNotExist:
        return f"Payment {payment_id} has no receipt"

    order = payment.order
    user = order.user
    receipt = payment.receipt
    receipt_number = receipt.receipt_number
    issued_at = timezone.localtime(receipt.generated_at).strftime('%Y-%m-%d %H:%M')
    receipt_attachment = EmailService.build_receipt_pdf_attachment(order, receipt)
    receipt_filename = receipt_attachment[0] if receipt_attachment else f"SimakFresh_Receipt_{receipt_number}.pdf"

    subject = f"Payment Receipt - Order #{order.id}"
    message = (
        f"Hi {user.first_name or 'Customer'}, your payment for order #{order.id} is successful.\n"
        f"Receipt Number: {receipt_number}\n"
        f"Amount: AED {payment.amount}\n"
        f"Issued At: {issued_at}\n\n"
        f"Your PDF receipt is attached ({receipt_filename})."
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
        attachments = [receipt_attachment] if receipt_attachment else None
        email_success, email_response = EmailService.send(
            recipient_email=user.email,
            subject=subject,
            plain_message=message,
            html_template='Notifications/emails/payment_receipt.html',
            template_context={
                'order': order,
                'payment': payment,
                'user_name': user.first_name or 'Customer',
                'receipt_number': receipt_number,
                'issued_at': issued_at,
                'receipt_filename': receipt_filename,
            },
            attachments=attachments,
        )
        results['channels']['email'] = {
            'success': email_success,
            'response': email_response,
            'pdf_attached': bool(receipt_attachment),
        }

    return results
