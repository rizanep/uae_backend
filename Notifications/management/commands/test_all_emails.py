"""
Send every HTML email template to a test inbox.

Usage:
  USE_REAL_SMTP=true python manage.py test_all_emails
  USE_REAL_SMTP=true python manage.py test_all_emails --to other@example.com
  python manage.py test_all_emails --dry-run
"""

from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from Notifications.email_service import EmailService
from Notifications.tasks import (
    _send_order_confirmed_email_to,
    _send_order_delivered_email_to,
    _send_otp_verification_email_to,
)
from Orders.models import Order, OrderItem, Payment, Receipt
from Users.models import UserAddress

User = get_user_model()

DEFAULT_TEST_EMAIL = "khaderrizan@gmail.com"


class Command(BaseCommand):
    help = "Send all transactional email templates to a test address"

    def add_arguments(self, parser):
        parser.add_argument(
            "--to",
            type=str,
            default=DEFAULT_TEST_EMAIL,
            help=f"Recipient inbox (default: {DEFAULT_TEST_EMAIL})",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be sent without calling SMTP",
        )

    def handle(self, *args, **options):
        recipient = options["to"].strip()
        dry_run = options["dry_run"]

        self.stdout.write(self.style.SUCCESS("=" * 72))
        self.stdout.write(self.style.SUCCESS("Simak Fresh email template test"))
        self.stdout.write(self.style.SUCCESS("=" * 72))
        self.stdout.write(f"Recipient: {recipient}")
        self.stdout.write(f"USE_REAL_SMTP: {EmailService.is_enabled()}")
        self.stdout.write(f"Logo file: {EmailService.get_logo_path()} (exists={EmailService.get_logo_path().is_file()})")
        self.stdout.write(f"FROM: {settings.DEFAULT_FROM_EMAIL}\n")

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run - no messages sent.\n"))
            for name in self._email_specs():
                self.stdout.write(f"  - {name}")
            return

        if not EmailService.is_enabled():
            raise CommandError(
                "USE_REAL_SMTP is false. Set USE_REAL_SMTP=true in the environment before sending."
            )

        if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
            raise CommandError("EMAIL_HOST_USER / EMAIL_HOST_PASSWORD are not configured.")

        user, address, order = self._ensure_fixtures(recipient)
        payment, receipt = self._ensure_payment(order)

        results = []

        def record(label, success, response):
            mark = self.style.SUCCESS("OK") if success else self.style.ERROR("FAIL")
            self.stdout.write(f"{mark} {label}: {response}")
            results.append((label, success))

        ok, res = _send_otp_verification_email_to(recipient, user, "123456")
        record("OTP verification", ok, res)

        ok, res = EmailService.send(
            recipient_email=recipient,
            subject="[TEST] Product back in stock",
            plain_message="Test stock notification plain text.",
            html_template="Notifications/emails/stock_notification.html",
            template_context={"user": user, "product_name": "Fresh Hammour (Test)"},
        )
        record("Stock notification", ok, res)

        ok, res = EmailService.send(
            recipient_email=recipient,
            subject="[TEST] Re: Delivery question",
            plain_message="Test contact reply plain text.",
            html_template="Notifications/emails/contact_reply.html",
            template_context={
                "contact_name": user.first_name or "Customer",
                "original_message": "When will my order arrive?",
                "reply_message": "Your order is scheduled for tomorrow morning.",
                "is_resolved": True,
            },
        )
        record("Contact reply", ok, res)

        ok, res = EmailService.send(
            recipient_email=recipient,
            subject=f"[TEST] Order #{order.id} - PENDING",
            plain_message="Test pending payment reminder.",
            html_template="Notifications/emails/order_status_update.html",
            template_context={
                "order": order,
                "user_name": user.first_name or recipient,
                "headline": "Complete your payment",
                "body_message": "Your order is waiting for payment.",
                "status_label": order.get_status_display(),
                "subject_line": "Complete your payment",
            },
        )
        record("Order pending (payment reminder)", ok, res)

        order.status = Order.OrderStatus.PAID
        order.save(update_fields=["status"])
        ok, res = _send_order_confirmed_email_to(recipient, order)
        record("Order confirmed (PAID)", ok, res)

        for status, headline in [
            (Order.OrderStatus.PROCESSING, "Order is being prepared"),
            (Order.OrderStatus.SHIPPED, "Order on the way"),
        ]:
            order.status = status
            order.save(update_fields=["status"])
            ok, res = EmailService.send(
                recipient_email=recipient,
                subject=f"[TEST] Order #{order.id} - {status}",
                plain_message=f"Test status email for {status}.",
                html_template="Notifications/emails/order_status_update.html",
                template_context={
                    "order": order,
                    "user_name": user.first_name or recipient,
                    "headline": headline,
                    "body_message": f"This is a test email for status {status}.",
                    "status_label": order.get_status_display(),
                    "subject_line": f"Order update - {status}",
                },
            )
            record(f"Order status ({status})", ok, res)

        order.status = Order.OrderStatus.DELIVERED
        order.save(update_fields=["status"])
        ok, res = _send_order_delivered_email_to(recipient, order)
        record("Order delivered", ok, res)

        order.status = Order.OrderStatus.CANCELLED
        order.save(update_fields=["status"])
        ok, res = EmailService.send(
            recipient_email=recipient,
            subject=f"[TEST] Order #{order.id} - CANCELLED",
            plain_message="Test cancelled order email.",
            html_template="Notifications/emails/order_status_update.html",
            template_context={
                "order": order,
                "user_name": user.first_name or recipient,
                "headline": "Order cancelled",
                "body_message": "This is a test email for a cancelled order.",
                "status_label": order.get_status_display(),
                "subject_line": "Order update - CANCELLED",
            },
        )
        record("Order status (CANCELLED)", ok, res)

        receipt_attachment = EmailService.build_receipt_pdf_attachment(order, receipt)
        receipt_filename = (
            receipt_attachment[0] if receipt_attachment else f"SimakFresh_Receipt_{receipt.receipt_number}.pdf"
        )
        ok, res = EmailService.send(
            recipient_email=recipient,
            subject=f"[TEST] Payment receipt - Order #{order.id}",
            plain_message=(
                f"Test payment receipt. PDF attached: {receipt_filename}"
                if receipt_attachment
                else "Test payment receipt (PDF generation failed)."
            ),
            html_template="Notifications/emails/payment_receipt.html",
            template_context={
                "order": order,
                "payment": payment,
                "user_name": user.first_name or "Customer",
                "receipt_number": receipt.receipt_number,
                "issued_at": timezone.localtime(receipt.generated_at).strftime("%Y-%m-%d %H:%M"),
                "receipt_filename": receipt_filename,
            },
            attachments=[receipt_attachment] if receipt_attachment else None,
        )
        record("Payment receipt (with PDF)", ok, res)

        ok, res = EmailService.send(
            recipient_email=recipient,
            subject="[TEST] Account permanently deleted",
            plain_message="Test account deletion plain text.",
            html_template="Notifications/emails/account_deletion.html",
            template_context={
                "subject_line": "Your Account Has Been Permanently Deleted",
                "headline": "Account permanently deleted",
                "body_message": "This is a test deletion confirmation email.",
                "deletion_time": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
        )
        record("Account deletion", ok, res)

        passed = sum(1 for _, ok in results if ok)
        self.stdout.write(self.style.SUCCESS(f"\nDone: {passed}/{len(results)} emails sent to {recipient}"))

    def _email_specs(self):
        return [
            "OTP verification",
            "Stock notification",
            "Contact reply",
            "Order confirmed (PAID)",
            "Order pending (payment reminder)",
            "Order status (PROCESSING, SHIPPED, DELIVERED, CANCELLED)",
            "Order delivered",
            "Payment receipt",
            "Account deletion",
        ]

    def _ensure_fixtures(self, recipient):
        user, _ = User.objects.get_or_create(
            email=recipient,
            defaults={
                "first_name": "Khader",
                "last_name": "Test",
                "phone_number": "+971500000001",
                "is_email_verified": True,
            },
        )
        user.first_name = user.first_name or "Khader"
        user.save(update_fields=["first_name"])

        address, _ = UserAddress.objects.get_or_create(
            user=user,
            street_address="Test Street 1",
            defaults={
                "label": "Home",
                "address_type": "home",
                "full_name": "Khader Test",
                "phone_number": "+971500000001",
                "city": "Dubai",
                "emirate": "dubai",
            },
        )

        # Always use a fresh order so status transitions are not blocked by CANCELLED.
        order = Order.objects.create(
            user=user,
            shipping_address=address,
            total_amount=Decimal("149.50"),
            status=Order.OrderStatus.PENDING,
        )
        return user, address, order

    def _ensure_payment(self, order):
        payment = getattr(order, "payment", None)
        if not payment:
            payment = Payment.objects.create(
                order=order,
                amount=order.total_amount,
                status=Payment.PaymentStatus.SUCCESS,
                payment_method=Payment.PaymentMethod.ZIINA,
                transaction_id=f"test-{order.id}",
            )
        if not hasattr(payment, "receipt"):
            receipt = Receipt.objects.create(
                payment=payment,
                receipt_number=Receipt.generate_number(),
            )
        else:
            receipt = payment.receipt
        return payment, receipt
