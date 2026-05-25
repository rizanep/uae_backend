"""
Management command to generate a demo admin receipt PDF from a real order.
Usage: python manage.py generate_demo_receipt
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
import random
import os
from pathlib import Path

from Users.models import User, UserAddress
from Products.models import Product
from Orders.models import Order, OrderItem, Payment, Receipt
from Orders.receipt_templates import render_admin_receipt_pdf


class Command(BaseCommand):
    help = "Generate a demo admin receipt PDF from a real order"

    def add_arguments(self, parser):
        parser.add_argument(
            '--order-id',
            type=int,
            help='Use existing order with this ID',
        )
        parser.add_argument(
            '--create',
            action='store_true',
            help='Create a new test order if none found',
        )
        parser.add_argument(
            '--output',
            type=str,
            default=None,
            help='Output directory for PDF (default: project root/demo_receipts)',
        )

    def handle(self, *args, **options):
        order_id = options.get('order_id')
        create = options.get('create', False)
        output_dir = options.get('output')

        # Find or create an order
        order = None
        if order_id:
            try:
                order = Order.objects.get(id=order_id)
            except Order.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Order #{order_id} not found."))
                return

        # If no order specified, look for one with a successful payment
        if not order:
            order = (
                Order.objects
                .filter(payment__status=Payment.PaymentStatus.SUCCESS)
                .select_related('user', 'shipping_address', 'payment', 'payment__receipt')
                .prefetch_related('items')
                .first()
            )

        # If still no order and --create flag, create a test order
        if not order and create:
            order = self._create_test_order()
            if order:
                self.stdout.write(self.style.SUCCESS(f"Created test order #{order.id}"))

        if not order:
            self.stdout.write(
                self.style.ERROR(
                    "No suitable order found. "
                    "Try: python manage.py generate_demo_receipt --create"
                )
            )
            return

        # Ensure order has payment and receipt
        if not hasattr(order, 'payment'):
            self.stdout.write(self.style.ERROR(f"Order #{order.id} has no payment record."))
            return

        payment = order.payment
        if payment.status != Payment.PaymentStatus.SUCCESS:
            self.stdout.write(
                self.style.WARNING(
                    f"Order #{order.id} payment status is {payment.status}. "
                    f"Admin receipts work best with successful payments."
                )
            )

        # Create receipt if it doesn't exist
        if not hasattr(payment, 'receipt'):
            receipt = Receipt.objects.create(
                payment=payment,
                receipt_number=Receipt.generate_number()
            )
            self.stdout.write(self.style.SUCCESS(f"Created receipt: {receipt.receipt_number}"))
        else:
            receipt = payment.receipt

        # Generate PDF
        try:
            buffer = render_admin_receipt_pdf(order)
            self.stdout.write(self.style.SUCCESS("PDF generated successfully"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to generate PDF: {e}"))
            import traceback
            traceback.print_exc()
            return

        # Determine output path
        if not output_dir:
            # Use project root/demo_receipts
            project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
            output_dir = project_root / "demo_receipts"
        else:
            output_dir = Path(output_dir)

        # Create directory if needed
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save PDF
        filename = f"order_receipt_{order.id}.pdf"
        filepath = output_dir / filename

        try:
            with open(filepath, 'wb') as f:
                f.write(buffer.getvalue())
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Demo receipt saved to: {filepath}"
                )
            )
            self.stdout.write(f"\nOrder Details:")
            self.stdout.write(f"  Order ID: {order.id}")
            self.stdout.write(f"  Customer: {order.user.get_full_name() or order.user.email}")
            self.stdout.write(f"  Total: AED {order.total_amount}")
            self.stdout.write(f"  Items: {order.items.count()}")
            self.stdout.write(f"  Receipt Number: {receipt.receipt_number}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to save PDF: {e}"))
            return

    def _create_test_order(self):
        """Create a test order with items and successful payment."""
        # Get or create user
        user = User.objects.filter(is_active=True, is_email_verified=True).first()
        if not user:
            # Create a test user
            user = User.objects.create_user(
                email='test@demo.local',
                phone_number='+971501234567',
                password='test123456',
                first_name='Demo',
                last_name='Customer',
                is_email_verified=True,
                is_phone_verified=True,
            )
            self.stdout.write(self.style.SUCCESS(f"Created test user: {user.email}"))

        # Get or create address
        address, _ = UserAddress.objects.get_or_create(
            user=user,
            is_default=True,
            defaults={
                'label': 'Home',
                'address_type': 'home',
                'full_name': user.get_full_name() or 'Customer',
                'phone_number': user.phone_number or '+971501234567',
                'street_address': '123 Demo Street',
                'area': 'Downtown',
                'city': 'Dubai',
                'emirate': 'dubai',
                'country': 'AE',
                'postal_code': '12345',
            }
        )

        # Get products
        products = list(Product.objects.filter(is_available=True, stock__gt=0)[:3])
        if not products:
            self.stdout.write(self.style.ERROR("No products available for demo order."))
            return None

        # Create order
        total_amount = sum(p.final_price * random.randint(1, 2) for p in products)
        order = Order.objects.create(
            user=user,
            status=Order.OrderStatus.PAID,
            shipping_address=address,
            total_amount=Decimal(str(total_amount)),
            delivery_charge=Decimal('10.00'),
            tip_amount=Decimal('5.00'),
            preferred_delivery_date=timezone.now().date(),
            delivery_notes='Demo order - leave at main entrance',
        )

        # Add items
        for product in products:
            quantity = random.randint(1, 2)
            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                quantity=quantity,
                price=product.final_price,
            )

        # Create successful payment
        payment = Payment.objects.create(
            order=order,
            transaction_id=f"DEMO-{order.id}-{random.randint(100000, 999999)}",
            amount=order.total_amount,
            status=Payment.PaymentStatus.SUCCESS,
            payment_method=Payment.PaymentMethod.ZIINA,
            provider_response={'demo': True},
        )

        # Create receipt
        Receipt.objects.create(
            payment=payment,
            receipt_number=Receipt.generate_number()
        )

        return order
