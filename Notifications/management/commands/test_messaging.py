"""
Management command to test SMS/WhatsApp/Email messaging integration.
Usage: python manage.py test_messaging
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.conf import settings
from decimal import Decimal
from Users.models import OTPToken, UserAddress
from Orders.models import Order, Payment, Receipt
from Notifications.services import UnifiedNotificationService
from Notifications.tasks import (
    send_login_otp_notification,
    send_order_status_multichannel_notification,
    send_payment_receipt_multichannel_notification,
)
from django.utils import timezone
from datetime import timedelta
import random

User = get_user_model()


class Command(BaseCommand):
    help = 'Test SMS, WhatsApp, and Email messaging integration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--phone',
            type=str,
            default='918281740483',
            help='Test phone number (default: 918281740483)',
        )
        parser.add_argument(
            '--email',
            type=str,
            default='test@example.com',
            help='Test email address',
        )
        parser.add_argument(
            '--test',
            type=str,
            choices=['otp', 'order', 'payment', 'all'],
            default='all',
            help='Which test to run',
        )

    def handle(self, *args, **options):
        phone = options['phone']
        email = options['email']
        test_type = options['test']

        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('Messaging Integration Test Suite'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

        self.stdout.write(f"\nTest Phone: {phone}")
        self.stdout.write(f"Test Email: {email}")
        self.stdout.write(f"SMS Enabled: {getattr(settings, 'USE_REAL_MSG91_SMS', False)}")
        self.stdout.write(f"WhatsApp Enabled: {getattr(settings, 'USE_REAL_MSG91_WHATSAPP', False)}")
        self.stdout.write(f"Email Enabled: {getattr(settings, 'USE_REAL_SMTP', False)}\n")

        if test_type in ['otp', 'all']:
            self.test_otp(phone, email)

        if test_type in ['order', 'all']:
            self.test_order(phone, email)

        if test_type in ['payment', 'all']:
            self.test_payment(phone, email)

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 80))
        self.stdout.write(self.style.SUCCESS('All tests completed!'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

    def test_otp(self, phone, email):
        """Test OTP sending via SMS/WhatsApp/Email"""
        self.stdout.write(self.style.WARNING('\n>>> Testing OTP Notifications <<<\n'))

        # Create or get test user
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'phone_number': phone,
                'first_name': 'Test',
                'last_name': 'User',
                'is_email_verified': True,
                'is_phone_verified': True,
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Created test user: {email}'))
        else:
            self.stdout.write(f'ℹ Using existing user: {email}')

        # Test 1: Email OTP
        self.stdout.write('\n1. Testing Email OTP...')
        otp_email = OTPToken.objects.create(
            user=user,
            otp_code='123456',
            otp_type='email',
            email=email,
            expires_at=timezone.now() + timedelta(minutes=5),
        )
        
        result = send_login_otp_notification.apply(args=[otp_email.id, 'email']).get()
        self.stdout.write(f'   Result: {result}')

        # Test 2: Phone OTP via SMS
        self.stdout.write('\n2. Testing Phone OTP via SMS...')
        otp_sms = OTPToken.objects.create(
            user=user,
            otp_code='654321',
            otp_type='phone',
            phone_number=phone,
            expires_at=timezone.now() + timedelta(minutes=5),
        )
        
        result = send_login_otp_notification.apply(args=[otp_sms.id, 'sms']).get()
        self.stdout.write(f'   Result: {result}')

        # Test 3: Phone OTP via WhatsApp
        self.stdout.write('\n3. Testing Phone OTP via WhatsApp...')
        otp_wa = OTPToken.objects.create(
            user=user,
            otp_code='789012',
            otp_type='phone',
            phone_number=phone,
            expires_at=timezone.now() + timedelta(minutes=5),
        )
        
        result = send_login_otp_notification.apply(args=[otp_wa.id, 'whatsapp']).get()
        self.stdout.write(f'   Result: {result}')

    def test_order(self, phone, email):
        """Test order status notifications"""
        self.stdout.write(self.style.WARNING('\n>>> Testing Order Notifications <<<\n'))

        # Create or get test user
        user, _ = User.objects.get_or_create(
            email=email,
            defaults={
                'phone_number': phone,
                'first_name': 'Test',
                'last_name': 'User',
                'is_email_verified': True,
                'is_phone_verified': True,
            }
        )

        # Create test address
        address, _ = UserAddress.objects.get_or_create(
            user=user,
            defaults={
                'full_name': 'Test User',
                'phone_number': phone,
                'street_address': '123 Test St',
                'city': 'Dubai',
                'emirate': 'dubai',
                'address_type': 'home',
            }
        )

        # Test each order status
        statuses = [
            Order.OrderStatus.PENDING,
            Order.OrderStatus.PAID,
            Order.OrderStatus.PROCESSING,
            Order.OrderStatus.SHIPPED,
            Order.OrderStatus.DELIVERED,
        ]

        for i, status in enumerate(statuses, 1):
            self.stdout.write(f'\n{i}. Testing {status} notification...')
            
            order = Order.objects.create(
                user=user,
                shipping_address=address,
                total_amount=Decimal('99.99'),
                status=status,
            )
            
            result = send_order_status_multichannel_notification.apply(args=[order.id]).get()
            self.stdout.write(f'   Channels: {list(result.get("channels", {}).keys())}')
            for channel, res in result.get('channels', {}).items():
                status_str = '✓' if res.get('success') else '✗'
                self.stdout.write(f'   {status_str} {channel.upper()}: {res.get("response", {}).get("status", "sent")}')

    def test_payment(self, phone, email):
        """Test payment receipt notifications"""
        self.stdout.write(self.style.WARNING('\n>>> Testing Payment Receipt Notifications <<<\n'))

        # Create or get test user
        user, _ = User.objects.get_or_create(
            email=email,
            defaults={
                'phone_number': phone,
                'first_name': 'Test',
                'last_name': 'User',
                'is_email_verified': True,
                'is_phone_verified': True,
            }
        )

        # Create test address
        address, _ = UserAddress.objects.get_or_create(
            user=user,
            defaults={
                'full_name': 'Test User',
                'phone_number': phone,
                'street_address': '123 Test St',
                'city': 'Dubai',
                'emirate': 'dubai',
                'address_type': 'home',
            }
        )

        # Create order
        order = Order.objects.create(
            user=user,
            shipping_address=address,
            total_amount=Decimal('150.00'),
            status=Order.OrderStatus.PAID,
        )

        self.stdout.write(f'\n1. Creating payment for order {order.id}...')
        
        # Create payment (this will trigger signal to create receipt)
        payment = Payment.objects.create(
            order=order,
            amount=Decimal('150.00'),
            status=Payment.PaymentStatus.SUCCESS,
            payment_method=Payment.PaymentMethod.ZIINA,
        )

        # Check if receipt was auto-created by signal
        if hasattr(payment, 'receipt'):
            receipt = payment.receipt
            self.stdout.write(f'   ✓ Receipt auto-created: {receipt.receipt_number}')
        else:
            # Fallback: manually create if not auto-created
            receipt = Receipt.objects.create(
                payment=payment,
                receipt_number=Receipt.generate_number()
            )
            self.stdout.write(f'   Receipt: {receipt.receipt_number}')

        self.stdout.write(f'\n2. Testing receipt notification...')

        result = send_payment_receipt_multichannel_notification.apply(args=[payment.id]).get()
        self.stdout.write(f'   Channels: {list(result.get("channels", {}).keys())}')
        for channel, res in result.get('channels', {}).items():
            status_str = '✓' if res.get('success') else '✗'
            self.stdout.write(f'   {status_str} {channel.upper()}: {res.get("response", {}).get("status", "sent")}')
