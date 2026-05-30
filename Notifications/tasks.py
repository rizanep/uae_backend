from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.utils import timezone
from .models import ContactMessage, Notification
from .services import UnifiedNotificationService
from .push_service import send_push_to_tokens

User = get_user_model()


@shared_task
def send_broadcast_push_task(broadcast_id):
    """
    Send PUSH broadcast asynchronously in token batches.
    This avoids blocking admin/API requests for large recipient sets.
    """
    from .models import Broadcast, NotificationType, FCMDevice

    try:
        broadcast = Broadcast.objects.select_related("template").get(id=broadcast_id)
    except Broadcast.DoesNotExist:
        return {"success": False, "error": f"Broadcast {broadcast_id} not found"}

    if broadcast.type != NotificationType.PUSH:
        return {"success": False, "error": "Broadcast type is not PUSH"}

    template = broadcast.template
    subject = broadcast.subject or (template.subject if template else None) or "Notification"
    message = broadcast.message or (template.body if template else "")
    if broadcast.image:
        from django.conf import settings
        image_url = settings.SITE_URL.rstrip("/") + broadcast.image.url
    else:
        image_url = None

    if broadcast.send_to_all:
        token_qs = FCMDevice.objects.filter(is_active=True, user__is_active=True)
    else:
        recipient_ids = broadcast.recipients.values_list("id", flat=True)
        token_qs = FCMDevice.objects.filter(is_active=True, user_id__in=recipient_ids)

    tokens = list(token_qs.values_list("registration_token", flat=True))
    if not tokens:
        return {
            "success": True,
            "broadcast_id": broadcast_id,
            "success_count": 0,
            "failure_count": 0,
            "message": "No active tokens",
        }

    # FCM multicast limit is 500 tokens/request.
    batch_size = 500
    total_success = 0
    total_failure = 0
    for i in range(0, len(tokens), batch_size):
        batch = tokens[i:i + batch_size]
        result = send_push_to_tokens(batch, subject, message, image=image_url)
        total_success += result.get("success_count", 0)
        total_failure += result.get("failure_count", 0)

    return {
        "success": True,
        "broadcast_id": broadcast_id,
        "success_count": total_success,
        "failure_count": total_failure,
        "token_count": len(tokens),
    }


@shared_task
def send_broadcast_email_task(broadcast_id):
    """Send EMAIL broadcast asynchronously to avoid blocking the request."""
    from .models import Broadcast, NotificationType

    try:
        broadcast = Broadcast.objects.select_related("template").get(id=broadcast_id)
    except Broadcast.DoesNotExist:
        return {"success": False, "error": f"Broadcast {broadcast_id} not found"}

    template = broadcast.template
    subject = broadcast.subject or (template.subject if template else None) or "Notification"
    message = broadcast.message or (template.body if template else "")

    if broadcast.send_to_all:
        users = User.objects.filter(is_active=True).values_list('email', flat=True)
    else:
        users = broadcast.recipients.filter(is_active=True).values_list('email', flat=True)

    sent_count = 0
    for email in users:
        if email:
            try:
                UnifiedNotificationService.send_email(
                    recipient_email=email,
                    subject=subject,
                    message=message,
                )
                sent_count += 1
            except Exception:
                pass

    return {"success": True, "broadcast_id": broadcast_id, "sent_count": sent_count}


@shared_task
def send_broadcast_sms_task(broadcast_id):
    """Send SMS broadcast asynchronously to avoid blocking the request."""
    from .models import Broadcast
    from django.conf import settings

    try:
        broadcast = Broadcast.objects.select_related("template").get(id=broadcast_id)
    except Broadcast.DoesNotExist:
        return {"success": False, "error": f"Broadcast {broadcast_id} not found"}

    template = broadcast.template
    subject = broadcast.subject or (template.subject if template else None) or "Notification"
    message = broadcast.message or (template.body if template else "")

    if broadcast.send_to_all:
        phones = User.objects.filter(is_active=True).values_list('phone_number', flat=True)
    else:
        phones = broadcast.recipients.filter(is_active=True).values_list('phone_number', flat=True)

    sent_count = 0
    for phone in phones:
        if phone:
            try:
                UnifiedNotificationService.send_sms(
                    phone_number=phone,
                    template_id=getattr(settings, 'MSG91_BROADCAST_SMS_TEMPLATE_ID', None),
                    variables={'VAR1': subject, 'body_1': message},
                )
                sent_count += 1
            except Exception:
                pass

    return {"success": True, "broadcast_id": broadcast_id, "sent_count": sent_count}


@shared_task
def send_broadcast_whatsapp_task(broadcast_id):
    """Send WhatsApp broadcast asynchronously to avoid blocking the request."""
    from .models import Broadcast
    from django.conf import settings

    try:
        broadcast = Broadcast.objects.select_related("template").get(id=broadcast_id)
    except Broadcast.DoesNotExist:
        return {"success": False, "error": f"Broadcast {broadcast_id} not found"}

    template = broadcast.template
    subject = broadcast.subject or (template.subject if template else None) or "Notification"
    message = broadcast.message or (template.body if template else "")

    if broadcast.send_to_all:
        phones = User.objects.filter(is_active=True).values_list('phone_number', flat=True)
    else:
        phones = broadcast.recipients.filter(is_active=True).values_list('phone_number', flat=True)

    sent_count = 0
    for phone in phones:
        if phone:
            try:
                UnifiedNotificationService.send_whatsapp(
                    phone_number=phone,
                    template_name=getattr(settings, 'MSG91_BROADCAST_WHATSAPP_TEMPLATE_NAME', None),
                    variables={'VAR1': subject, 'body_1': message},
                )
                sent_count += 1
            except Exception:
                pass

    return {"success": True, "broadcast_id": broadcast_id, "sent_count": sent_count}


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
        if not getattr(settings, "USE_REAL_SMTP", False):
            console_payload = {
                "to": contact_msg.email,
                "subject": subject,
                "reply_message": reply_message,
                "mark_resolved": mark_resolved,
            }
            print(f"[EMAIL CONSOLE MODE] {console_payload}")

            # Keep in-app behavior even when email transport is disabled.
            Notification.objects.create(
                user=contact_msg.user,
                title="Response to Your Message",
                message=f"We have replied to your message: {contact_msg.subject}\n\n{reply_message[:100]}..."
            )

            if mark_resolved:
                contact_msg.is_resolved = True
                contact_msg.save()
                Notification.objects.create(
                    user=contact_msg.user,
                    title="Your Message Has Been Resolved",
                    message=f"Your inquiry about '{contact_msg.subject}' has been marked as resolved."
                )

            return f"Email disabled (console mode). Printed payload for {contact_msg.email}"

        from Notifications.email_service import EmailService

        subject = f"Re: {contact_msg.subject}"
        plain_message = (
            f"Dear {contact_msg.name},\n\n"
            "Thank you for contacting us. Here's our response to your message:\n\n"
            f'Your original message:\n"{contact_msg.message}"\n\n'
            f"Our reply:\n{reply_message}\n\n"
            "Best regards,\nSupport Team"
        )
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
    """
    Send email notification when product comes back in stock.
    """
    if not getattr(settings, "USE_REAL_SMTP", False):
        return f"Email disabled (console mode). Would send to user {user_id} about {product_name}"

    try:
        user = User.objects.get(id=user_id)
        if not user.email:
            return f"User {user_id} has no email"

        from Notifications.email_service import EmailService

        subject = f"Good news! {product_name} is back in stock"
        plain_message = (
            f"Dear {user.first_name or user.email},\n\n"
            f'Great news! The product "{product_name}" that you were waiting for is now back in stock.\n\n'
            "You can now place your order through our app.\n\n"
            "Best regards,\nSimak Fresh Team"
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
def send_stock_notification_whatsapp(user_id, product_id):
    """
    TODO: Send WhatsApp notification when a product comes back in stock.
    Uses MSG91 template: MSG91_STOCK_WHATSAPP_TEMPLATE_NAME
    """
    pass


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
        order = Order.objects.select_related(
            'user', 'shipping_address', 'preferred_delivery_slot'
        ).prefetch_related('items').get(id=order_id)

        if not order.user.email:
            return f"User {order.user.id} has no email"

        from Notifications.email_service import EmailService

        subject = f"Order Confirmed - #{order.id}"
        plain_message = (
            f"Dear {order.user.first_name or order.user.email},\n\n"
            f"Your order #{order.id} has been confirmed and payment has been successfully processed.\n\n"
            f"Order ID: {order.id}\n"
            f"Total Amount: AED {order.total_amount}\n"
            f"Order Date: {order.created_at.strftime('%B %d, %Y')}\n\n"
            "We'll send you another email when your order is out for delivery.\n\n"
            "Thank you for choosing Simak Fresh!"
        )
        success, response = EmailService.send(
            recipient_email=order.user.email,
            subject=subject,
            plain_message=plain_message,
            html_template="Notifications/emails/order_confirmed.html",
            template_context={"order": order},
        )
        if success:
            return f"Order confirmation email sent to {order.user.email}"
        return f"Failed to send order confirmation email: {response}"

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
        order = Order.objects.select_related(
            'user', 'shipping_address', 'delivery_assignment'
        ).prefetch_related('items').get(id=order_id)

        if not order.user.email:
            return f"User {order.user.id} has no email"

        from Notifications.email_service import EmailService

        delivered_at = order.updated_at
        if hasattr(order, 'delivery_assignment') and order.delivery_assignment:
            delivered_at = order.delivery_assignment.delivered_at or delivered_at

        subject = f"Order Delivered - #{order.id}"
        plain_message = (
            f"Dear {order.user.first_name or order.user.email},\n\n"
            f"Your order #{order.id} has been successfully delivered!\n\n"
            f"Order ID: {order.id}\n"
            f"Total Amount: AED {order.total_amount}\n"
            f"Delivered On: {delivered_at}\n\n"
            "Thank you for choosing Simak Fresh!"
        )
        success, response = EmailService.send(
            recipient_email=order.user.email,
            subject=subject,
            plain_message=plain_message,
            html_template="Notifications/emails/order_delivered.html",
            template_context={"order": order},
        )
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

    - Email OTP uses email channel with HTML template.
    - Phone OTP can use SMS (default) or WhatsApp.
    """
    # return True  # Placeholder to avoid "no return" warning during development
    from Users.models import OTPToken
    from Notifications.email_service import EmailService

    try:
        otp = OTPToken.objects.select_related('user').get(id=otp_id)
    except OTPToken.DoesNotExist:
        return f"OTP token {otp_id} not found"

    if otp.is_expired() or otp.is_verified:
        return f"OTP token {otp_id} is not active"

    if otp.otp_type == 'email':
        if not otp.email:
            return f"OTP token {otp_id} missing email"
        subject = "Your Verification Code"
        plain_message = (
            f"Hello {otp.user.first_name or 'there'},\n\n"
            f"Your verification code is: {otp.otp_code}\n\n"
            "This code will expire in 5 minutes."
        )
        # Send using HTML template
        success, response = EmailService.send_template(
            recipient_email=otp.email,
            subject=subject,
            html_template='Notifications/emails/otp_verification.html',
            plain_message=plain_message,
            template_context={
                'user': otp.user,
                'otp_code': otp.otp_code,
            }
        )
        return {'channel': 'email', 'success': success, 'response': response}

    if not otp.phone_number:
        return f"OTP token {otp_id} missing phone number"

    selected_platform = (otp_platform or 'sms').lower()
    sms_template_id = getattr(settings, 'MSG91_OTP_SMS_TEMPLATE_ID', '')
    whatsapp_variables = {
        'body_1': otp.otp_code,
        'button_1': otp.otp_code,
    }
    sms_variables = {
        'VAR1': otp.otp_code,
    }

    if selected_platform == 'whatsapp':
        success, response = UnifiedNotificationService.send_whatsapp(
            phone_number=otp.phone_number,
            template_name=getattr(settings, 'MSG91_OTP_WHATSAPP_TEMPLATE_NAME', ''),
            variables=whatsapp_variables,
        )
        if success:
            return {'channel': 'whatsapp', 'success': True, 'response': response}

        # If WhatsApp was explicitly selected and failed, only fallback to SMS if configured.
        if not sms_template_id:
            return {'channel': 'whatsapp', 'success': False, 'response': response}

        sms_success, sms_response = UnifiedNotificationService.send_sms(
            phone_number=otp.phone_number,
            template_id=sms_template_id,
            variables=sms_variables,
        )
        return {'channel': 'sms', 'success': sms_success, 'response': sms_response}

    if selected_platform == 'sms' and not sms_template_id:
        return {
            'channel': 'sms',
            'success': False,
            'response': {
                'error': 'missing MSG91 SMS template id',
                'hint': 'set MSG91_OTP_SMS_TEMPLATE_ID or request otp_platform=whatsapp',
            },
        }

    success, response = UnifiedNotificationService.send_sms(
        phone_number=otp.phone_number,
        template_id=sms_template_id,
        variables=sms_variables,
    )
    return {'channel': 'sms', 'success': success, 'response': response}


def _order_status_copy(order):
    """Email/push copy per status. WhatsApp uses `order_status` template via order_whatsapp helpers."""
    status_label = order.get_status_display()
    user_name = order.user.first_name or order.user.email or 'Customer'

    status_messages = {
        'PENDING': {
            'subject': f"Order Status Updated: {status_label} (#{order.id})",
            'message': f"Hi {user_name}, your order #{order.id} status is now {status_label}.",
            'sms_template': 'order_status_pending',
        },
        'PAID': {
            'subject': f"Order Confirmed: #{order.id}",
            'message': (
                f"Great news {user_name}! Payment received for order #{order.id}. "
                "Your order is confirmed and being prepared."
            ),
            'sms_template': getattr(settings, 'MSG91_ORDER_PAID_SMS_TEMPLATE_ID', ''),
        },
        'PROCESSING': {
            'subject': f"Order Processing: #{order.id}",
            'message': (
                f"Hi {user_name}, your order #{order.id} is being carefully prepared. "
                "We will notify you when it is on the way."
            ),
            'sms_template': getattr(settings, 'MSG91_ORDER_PROCESSING_SMS_TEMPLATE_ID', ''),
        },
        'SHIPPED': {
            'subject': f"Order On The Way: #{order.id}",
            'message': (
                f"Awesome {user_name}! Your order #{order.id} is out for delivery. "
                "Please keep your phone reachable for delivery updates."
            ),
            'sms_template': getattr(settings, 'MSG91_ORDER_SHIPPED_SMS_TEMPLATE_ID', ''),
        },
        'DELIVERED': {
            'subject': f"Delivered Successfully: #{order.id}",
            'message': (
                f"Wonderful {user_name}! Your order #{order.id} has been delivered. "
                "Thank you for shopping with us."
            ),
            'sms_template': getattr(settings, 'MSG91_ORDER_DELIVERED_SMS_TEMPLATE_ID', ''),
        },
        'CANCELLED': {
            'subject': f"Order Cancelled: #{order.id}",
            'message': (
                f"Hi {user_name}, your order #{order.id} has been cancelled. "
                "If this was unexpected, please contact support."
            ),
            'sms_template': getattr(settings, 'MSG91_ORDER_CANCELLED_SMS_TEMPLATE_ID', ''),
        },
    }

    return status_messages.get(order.status, {
        'subject': f"Order Status Updated: {status_label} (#{order.id})",
        'message': f"Hi {user_name}, your order #{order.id} status is now {status_label}.",
        'sms_template': 'order_status_pending',
    })


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 3})
def send_order_status_multichannel_notification(self, order_id):
    """
    Send order lifecycle updates through WhatsApp, SMS, and email via a shared service layer.
    """
    from Orders.models import Order
    from Notifications.order_whatsapp import send_order_status_whatsapp

    try:
        order = (
            Order.objects.select_related("user", "preferred_delivery_slot", "shipping_address", "payment")
            .prefetch_related("items__product")
            .get(id=order_id)
        )
    except Order.DoesNotExist:
        return f"Order {order_id} not found"

    content = _order_status_copy(order)
    user = order.user
    results = {
        'order_id': order.id,
        'status': order.status,
        'channels': {},
    }

    if user.phone_number:
        wa_success, wa_response = send_order_status_whatsapp(
            order,
            content["message"],
        )
        results['channels']['whatsapp'] = {'success': wa_success, 'response': wa_response}

    if user.email:
        from Notifications.email_service import EmailService

        user_name = user.first_name or user.email
        if order.status == Order.OrderStatus.PAID:
            email_success, email_response = EmailService.send(
                recipient_email=user.email,
                subject=content['subject'],
                plain_message=content['message'],
                html_template="Notifications/emails/order_confirmed.html",
                template_context={"order": order},
            )
        elif order.status == Order.OrderStatus.DELIVERED:
            email_success, email_response = EmailService.send(
                recipient_email=user.email,
                subject=content['subject'],
                plain_message=content['message'],
                html_template="Notifications/emails/order_delivered.html",
                template_context={"order": order},
            )
        else:
            email_success, email_response = EmailService.send(
                recipient_email=user.email,
                subject=content['subject'],
                plain_message=content['message'],
                html_template="Notifications/emails/order_status_update.html",
                template_context={
                    "order": order,
                    "user_name": user_name,
                    "headline": content['subject'],
                    "body_message": content['message'],
                    "status_label": order.get_status_display(),
                    "subject_line": content['subject'],
                },
            )
        results['channels']['email'] = {'success': email_success, 'response': email_response}

    # FCM Push notification
    from .push_service import send_push_to_user
    push_image = getattr(settings, 'ORDER_STATUS_PUSH_IMAGE_URL', None)
    push_result = send_push_to_user(
        user=user,
        title=content['subject'],
        body=content['message'],
        data={'type': 'order_status', 'order_id': str(order.id), 'status': order.status},
        image=push_image,
    )
    results['channels']['push'] = push_result

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

    if user.email:
        from Notifications.email_service import EmailService

        receipt_attachment = EmailService.build_receipt_pdf_attachment(order, payment.receipt)
        receipt_filename = (
            receipt_attachment[0] if receipt_attachment else f"SimakFresh_Receipt_{receipt_number}.pdf"
        )
        email_success, email_response = EmailService.send(
            recipient_email=user.email,
            subject=subject,
            plain_message=message,
            html_template="Notifications/emails/payment_receipt.html",
            template_context={
                "order": order,
                "payment": payment,
                "user_name": user.first_name or "Customer",
                "receipt_number": receipt_number,
                "issued_at": issued_at,
                "receipt_filename": receipt_filename,
            },
            attachments=[receipt_attachment] if receipt_attachment else None,
        )
        results['channels']['email'] = {'success': email_success, 'response': email_response}

    return results


# ============================================================================
# Scenario-specific task stubs
# Implementations to be added once MSG91 templates are configured.
# ============================================================================

# --- OTP ---

@shared_task
def send_otp_sms(user_id, otp_code):
    """
    TODO: Send login OTP to user via SMS.
    Uses MSG91 template: MSG91_OTP_SMS_TEMPLATE_ID
    """
    pass


@shared_task
def send_otp_whatsapp(user_id, otp_code):
    """
    Send login OTP to user via WhatsApp.
    Uses MSG91 template: MSG91_OTP_WHATSAPP_TEMPLATE_NAME
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return f"User {user_id} not found"

    if not user.phone_number:
        return f"User {user_id} has no phone number"

    variables = {
        'body_1': otp_code,
        'button_1': otp_code,
    }

    success, response = UnifiedNotificationService.send_whatsapp(
        phone_number=user.phone_number,
        template_name=getattr(settings, 'MSG91_OTP_WHATSAPP_TEMPLATE_NAME', ''),
        variables=variables,
    )

    if success:
        return f"OTP WhatsApp sent to {user.phone_number}"
    return f"Failed to send OTP WhatsApp to {user.phone_number}: {response}"


# --- Admin order notifications (new order + paid) ---

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 3})
def send_admin_order_whatsapp_notification(self, order_id):
    """
    Notify store admin via WhatsApp when an order becomes PAID.
    Template: MSG91_ADMIN_ORDER_WHATSAPP_TEMPLATE_NAME (admin_order_notification)
    Recipient: ADMIN_ORDER_WHATSAPP_PHONE
    """
    from Orders.models import Order
    from Notifications.admin_order_whatsapp import send_admin_order_whatsapp

    try:
        order = (
            Order.objects.select_related("user", "preferred_delivery_slot", "shipping_address", "payment")
            .prefetch_related("items__product")
            .get(id=order_id)
        )
    except Order.DoesNotExist:
        return f"Order {order_id} not found"

    if order.status != Order.OrderStatus.PAID:
        return f"Order {order_id} is {order.status}, skipping admin WhatsApp"

    success, response = send_admin_order_whatsapp(order)
    if success:
        return f"Admin paid-order WhatsApp sent for order {order_id}"
    return f"Failed admin paid-order WhatsApp for order {order_id}: {response}"


# --- Admin broadcast notifications ---

@shared_task
def send_admin_notification_sms(phone_number, template_variables=None):
    """
    TODO: Admin-triggered SMS broadcast to a single recipient.
    Uses MSG91 template: MSG91_ADMIN_NOTIFICATION_SMS_TEMPLATE_ID
    """
    pass


@shared_task
def send_admin_notification_whatsapp(phone_number, template_variables=None):
    """
    TODO: Admin-triggered WhatsApp broadcast to a single recipient.
    Uses MSG91 template: MSG91_ADMIN_NOTIFICATION_WHATSAPP_TEMPLATE_NAME
    """
    pass


# --- Stock back-in-stock ---

@shared_task
def send_stock_back_sms(user_id, product_id):
    """
    TODO: Notify user via SMS that a requested product is back in stock.
    Uses MSG91 template: MSG91_STOCK_SMS_TEMPLATE_ID
    """
    pass


# --- Order: pending payment reminder (WhatsApp + email only) ---
# Triggered with a 5-minute countdown after order creation (apply_async countdown=300).
# Task must abort if order status has already changed to PAID before it runs.

@shared_task
def send_order_pending_reminder_whatsapp(order_id):
    """
    Remind user via WhatsApp to complete payment for a pending order.
    Schedule: apply_async(countdown=300) — aborts if order.status != PENDING.
    Uses MSG91 template: MSG91_ORDER_STATUS_WHATSAPP_TEMPLATE_NAME
    """
    from Orders.models import Order
    from Notifications.order_whatsapp import send_order_status_whatsapp

    try:
        order = (
            Order.objects.select_related("user", "preferred_delivery_slot", "shipping_address", "payment")
            .prefetch_related("items__product")
            .get(id=order_id)
        )
    except Order.DoesNotExist:
        return f"Order {order_id} not found"

    if order.status != 'PENDING':
        return f"Order {order_id} is {order.status}, skipping reminder"

    user = order.user
    if not user.phone_number:
        return f"User {user.id} has no phone number"

    pay_url = f"{getattr(settings, 'SITE_URL', 'https://simakfresh.ae').rstrip('/')}/orders/{order.id}"
    status_message = (
        "Your order is awaiting payment. "
        "Please complete payment to start preparation and dispatch."
    )

    success, response = send_order_status_whatsapp(
        order,
        status_message,
        extra_var2_lines=[f"Complete payment: {pay_url}"],
    )

    if success:
        return f"Pending order reminder sent to {user.phone_number} for order {order_id}"
    return f"Failed to send pending reminder for order {order_id}: {response}"


@shared_task
def send_order_pending_reminder_email(order_id):
    """
    TODO: Remind user via email to complete payment for a pending order.
    Schedule: apply_async(countdown=300) — abort if order.status != PENDING.
    """
    pass


# --- Order: paid (WhatsApp + email) ---

@shared_task
def send_order_paid_whatsapp(order_id):
    """
    TODO: Notify user via WhatsApp that payment was received and order is confirmed.
    Uses MSG91 template: MSG91_ORDER_PAID_WHATSAPP_TEMPLATE_NAME
    """
    pass


@shared_task
def send_order_paid_email(order_id):
    """
    TODO: Notify user via email that payment was received and order is confirmed.
    """
    pass


# --- Order: post-paid status changes (WhatsApp only) ---

@shared_task
def send_order_processing_whatsapp(order_id):
    """
    TODO: Notify user via WhatsApp that their order is being processed/prepared.
    Uses MSG91 template: MSG91_ORDER_PROCESSING_WHATSAPP_TEMPLATE_NAME
    """
    pass


@shared_task
def send_order_shipped_whatsapp(order_id):
    """
    TODO: Notify user via WhatsApp that their order is out for delivery.
    Uses MSG91 template: MSG91_ORDER_SHIPPED_WHATSAPP_TEMPLATE_NAME
    """
    pass


@shared_task
def send_order_delivered_whatsapp(order_id):
    """
    TODO: Notify user via WhatsApp that their order has been delivered.
    Uses MSG91 template: MSG91_ORDER_DELIVERED_WHATSAPP_TEMPLATE_NAME
    """
    pass


@shared_task
def send_order_cancelled_whatsapp(order_id):
    """
    TODO: Notify user via WhatsApp that their order has been cancelled.
    Uses MSG91 template: MSG91_ORDER_CANCELLED_WHATSAPP_TEMPLATE_NAME
    """
    pass


@shared_task
def send_order_cancelled_email(order_id):
    """
    TODO: Notify user via email that their order has been cancelled.
    """
    pass


# --- Review request (triggered after DELIVERED status) ---

@shared_task
def send_review_request_whatsapp(order_id):
    """
    TODO: Send a WhatsApp message asking the user to leave a review after delivery.
    Uses MSG91 template: MSG91_REVIEW_REQUEST_WHATSAPP_TEMPLATE_NAME
    """
    pass


@shared_task
def send_review_request_email(order_id):
    """
    TODO: Send an email asking the user to leave a review after delivery.
    """
    pass