"""
Send a payment receipt PDF email for an existing order (no new orders created).

Usage:
  USE_REAL_SMTP=true python manage.py send_receipt_email --to khaderrizan@gmail.com
  USE_REAL_SMTP=true python manage.py send_receipt_email --to user@example.com --order-id 314
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from Notifications.email_service import EmailService
from Orders.models import Order


class Command(BaseCommand):
    help = "Email an existing order receipt PDF to a recipient (does not create orders)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--to",
            type=str,
            required=True,
            help="Recipient email address",
        )
        parser.add_argument(
            "--order-id",
            type=int,
            default=None,
            help="Existing order ID (default: latest order with a receipt)",
        )

    def handle(self, *args, **options):
        recipient = options["to"].strip()
        order_id = options["order_id"]

        if not EmailService.is_enabled():
            raise CommandError("USE_REAL_SMTP is false. Set USE_REAL_SMTP=true before sending.")

        qs = (
            Order.objects.select_related("payment__receipt", "shipping_address", "user")
            .prefetch_related("items")
            .filter(payment__receipt__isnull=False)
            .order_by("-id")
        )
        if order_id:
            order = qs.filter(id=order_id).first()
            if not order:
                raise CommandError(f"Order #{order_id} not found or has no receipt.")
        else:
            order = qs.first()
            if not order:
                raise CommandError("No existing order with a receipt found.")

        payment = order.payment
        receipt = payment.receipt
        issued_at = timezone.localtime(receipt.generated_at).strftime("%Y-%m-%d %H:%M")
        receipt_attachment = EmailService.build_receipt_pdf_attachment(order, receipt)
        receipt_filename = (
            receipt_attachment[0] if receipt_attachment else f"SimakFresh_Receipt_{receipt.receipt_number}.pdf"
        )

        ok, res = EmailService.send(
            recipient_email=recipient,
            subject=f"Payment Receipt - Order #{order.id}",
            plain_message=(
                f"Your payment receipt for order #{order.id} is attached.\n"
                f"Receipt Number: {receipt.receipt_number}\n"
                f"Amount: AED {payment.amount}\n"
                f"Issued At: {issued_at}\n"
            ),
            html_template="Notifications/emails/payment_receipt.html",
            template_context={
                "order": order,
                "payment": payment,
                "user_name": order.user.first_name or "Customer",
                "receipt_number": receipt.receipt_number,
                "issued_at": issued_at,
                "receipt_filename": receipt_filename,
            },
            attachments=[receipt_attachment] if receipt_attachment else None,
        )

        if not ok:
            raise CommandError(f"Failed to send email: {res}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Sent receipt for order #{order.id} ({receipt.receipt_number}) to {recipient}"
            )
        )
