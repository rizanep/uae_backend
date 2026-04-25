"""
Management command to generate demo outputs for all three receipt renderers.

Usage:
  python manage.py generate_all_receipts                  # use first available order
  python manage.py generate_all_receipts --order-id 264  # use specific order
  python manage.py generate_all_receipts --create         # create a test order
  python manage.py generate_all_receipts --output /path/  # custom output dir
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from pathlib import Path
import traceback

from Users.models import User, UserAddress
from Products.models import Product
from Orders.models import Order, OrderItem, Payment, Receipt
from Orders.receipt_templates import (
    render_receipt_image,
    render_receipt_pdf,
    render_admin_receipt_pdf,
)


class Command(BaseCommand):
    help = "Generate demo outputs for all three receipt renderers (image, customer PDF, admin PDF)"

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
            help='Output directory (default: project root/demo_receipts)',
        )

    def handle(self, *args, **options):
        order_id   = options.get('order_id')
        create     = options.get('create', False)
        output_dir = options.get('output')

        # ── Resolve order ──────────────────────────────────────────────────
        order = None
        if order_id:
            try:
                order = Order.objects.get(id=order_id)
            except Order.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Order #{order_id} not found."))
                return

        if not order:
            order = (
                Order.objects
                .filter(payment__status=Payment.PaymentStatus.SUCCESS)
                .select_related('user', 'shipping_address', 'payment', 'payment__receipt')
                .prefetch_related('items')
                .first()
            )

        if not order and create:
            order = self._create_test_order()
            if order:
                self.stdout.write(self.style.SUCCESS(f"Created test order #{order.id}"))

        if not order:
            self.stdout.write(self.style.ERROR(
                "No suitable order found. "
                "Try: python manage.py generate_all_receipts --create"
            ))
            return

        # ── Ensure payment + receipt exist ────────────────────────────────
        if not hasattr(order, 'payment'):
            self.stdout.write(self.style.ERROR(f"Order #{order.id} has no payment record."))
            return

        payment = order.payment
        if not hasattr(payment, 'receipt'):
            receipt = Receipt.objects.create(
                payment=payment,
                receipt_number=Receipt.generate_number(),
            )
            self.stdout.write(self.style.SUCCESS(f"Created receipt: {receipt.receipt_number}"))
        else:
            receipt = payment.receipt

        # ── Output directory ───────────────────────────────────────────────
        if not output_dir:
            project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
            out = project_root / "demo_receipts"
        else:
            out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        self.stdout.write(f"\nOrder #{order.id} — {order.user.get_full_name() or order.user.email}")
        self.stdout.write(f"Receipt:  {receipt.receipt_number}")
        self.stdout.write(f"Output:   {out}\n")

        results = []

        # ── 1. Receipt image (PNG) ─────────────────────────────────────────
        self.stdout.write("  [1/3] Rendering receipt image (PNG)…", ending=" ")
        try:
            buf  = render_receipt_image(order, receipt)
            path = out / f"receipt_image_{order.id}.png"
            with open(path, 'wb') as f:
                f.write(buf.getvalue())
            size = path.stat().st_size
            self.stdout.write(self.style.SUCCESS(f"✓  ({size // 1024} KB)  → {path.name}"))
            results.append(("Receipt Image (PNG)", str(path), True, None))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗  {e}"))
            traceback.print_exc()
            results.append(("Receipt Image (PNG)", None, False, str(e)))

        # ── 2. Customer PDF receipt ────────────────────────────────────────
        self.stdout.write("  [2/3] Rendering customer PDF receipt…", ending=" ")
        try:
            buf  = render_receipt_pdf(order, receipt)
            path = out / f"receipt_customer_{order.id}.pdf"
            with open(path, 'wb') as f:
                f.write(buf.getvalue())
            size = path.stat().st_size
            self.stdout.write(self.style.SUCCESS(f"✓  ({size // 1024} KB)  → {path.name}"))
            results.append(("Customer PDF", str(path), True, None))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗  {e}"))
            traceback.print_exc()
            results.append(("Customer PDF", None, False, str(e)))

        # ── 3. Admin PDF receipt ───────────────────────────────────────────
        self.stdout.write("  [3/3] Rendering admin PDF receipt…", ending=" ")
        try:
            buf  = render_admin_receipt_pdf(order)
            path = out / f"receipt_admin_{order.id}.pdf"
            with open(path, 'wb') as f:
                f.write(buf.getvalue())
            size = path.stat().st_size
            self.stdout.write(self.style.SUCCESS(f"✓  ({size // 1024} KB)  → {path.name}"))
            results.append(("Admin PDF", str(path), True, None))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗  {e}"))
            traceback.print_exc()
            results.append(("Admin PDF", None, False, str(e)))

        # ── Summary ────────────────────────────────────────────────────────
        passed = sum(1 for _, _, ok, _ in results if ok)
        failed = len(results) - passed
        self.stdout.write("")
        self.stdout.write("─" * 60)
        self.stdout.write(f"  Results: {passed}/3 passed" +
                          (f"  |  {failed} failed" if failed else ""))
        self.stdout.write("─" * 60)
        for name, path, ok, err in results:
            status = self.style.SUCCESS("PASS") if ok else self.style.ERROR("FAIL")
            self.stdout.write(f"  [{status}]  {name}" + (f"  —  {err}" if err else ""))
        self.stdout.write("")

    # ── Test-order factory ─────────────────────────────────────────────────
    def _create_test_order(self):
        user = User.objects.filter(is_active=True, is_email_verified=True).first()
        if not user:
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

        address = UserAddress.objects.filter(user=user).first()
        if not address:
            address = UserAddress.objects.create(
                user=user,
                full_name=user.get_full_name() or 'Demo Customer',
                phone_number=user.phone_number or '+971501234567',
                street_address='Sheikh Zayed Road',
                area='Al Barsha',
                city='Dubai',
                emirate='DXB',
                is_default=True,
            )

        product = Product.objects.filter(is_available=True).first()
        product_name  = product.name  if product else 'Demo Product'
        product_price = product.price if product else Decimal('99.99')

        order = Order.objects.create(
            user=user,
            shipping_address=address,
            status=Order.Status.CONFIRMED,
            subtotal_amount=product_price,
            delivery_charge=Decimal('10.00'),
            tip_amount=Decimal('5.00'),
            total_amount=product_price + Decimal('15.00'),
        )

        OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product_name,
            quantity=1,
            price=product_price,
            subtotal=product_price,
        )

        payment = Payment.objects.create(
            order=order,
            amount=order.total_amount,
            status=Payment.PaymentStatus.SUCCESS,
            payment_method='Card',
        )

        Receipt.objects.create(
            payment=payment,
            receipt_number=Receipt.generate_number(),
        )

        return order
