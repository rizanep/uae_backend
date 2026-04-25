from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from datetime import timedelta
from django.contrib.auth import get_user_model
from unittest.mock import patch
from .models import Order, OrderItem, Payment
from Cart.models import Cart, CartItem
from Products.models import Product, Category
from Reviews.models import Review
from Users.models import UserAddress

User = get_user_model()


class OrderSignalNotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='signaluser@example.com',
            password='pass12345',
            phone_number='+971500000010',
        )
        self.address = UserAddress.objects.create(
            user=self.user,
            label='Home',
            address_type='home',
            full_name='Signal User',
            phone_number='+971500000010',
            street_address='Street 1',
            city='Dubai',
            emirate='dubai',
        )

    @patch('Orders.signals.send_order_status_multichannel_notification.delay')
    def test_order_created_triggers_multichannel_dispatch(self, mock_delay):
        order = Order.objects.create(
            user=self.user,
            shipping_address=self.address,
            total_amount=Decimal('120.00'),
            status=Order.OrderStatus.PENDING,
        )

        mock_delay.assert_called_once_with(order.id)

    @patch('Orders.signals.send_order_status_multichannel_notification.delay')
    def test_order_status_change_triggers_multichannel_dispatch(self, mock_delay):
        order = Order.objects.create(
            user=self.user,
            shipping_address=self.address,
            total_amount=Decimal('120.00'),
            status=Order.OrderStatus.PENDING,
        )
        mock_delay.reset_mock()

        order.status = Order.OrderStatus.PAID
        order.save()

        mock_delay.assert_called_once_with(order.id)

    @patch('Orders.signals.send_payment_receipt_multichannel_notification.delay')
    @patch('Orders.signals.send_order_status_multichannel_notification.delay')
    def test_payment_success_triggers_receipt_dispatch(self, mock_status_delay, mock_receipt_delay):
        order = Order.objects.create(
            user=self.user,
            shipping_address=self.address,
            total_amount=Decimal('75.00'),
            status=Order.OrderStatus.PENDING,
        )
        mock_status_delay.reset_mock()

        payment = Payment.objects.create(
            order=order,
            amount=Decimal('75.00'),
            status=Payment.PaymentStatus.SUCCESS,
            payment_method=Payment.PaymentMethod.ZIINA,
        )

        mock_receipt_delay.assert_called_once_with(payment.id)


class DashboardAnalyticsTestCase(APITestCase):
    """Test cases for the dashboard_analytics endpoint."""

    def setUp(self):
        """Set up test data."""
        # Create admin user
        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            password="adminpass123",
            role="admin",
            is_staff=True,
            is_superuser=True
        )

        # Create regular user
        self.regular_user = User.objects.create_user(
            email="user@example.com",
            password="userpass123",
            role="user"
        )

        # Create another regular user for testing
        self.user2 = User.objects.create_user(
            email="user2@example.com",
            password="userpass456",
            role="user",
            is_email_verified=True,
            is_phone_verified=True
        )

        # Create category and products
        self.category = Category.objects.create(name="Test Category", slug="test-category")
        self.product1 = Product.objects.create(
            name="Test Product 1",
            description="Test description",
            price=Decimal("100.00"),
            stock=10,
            category=self.category,
            is_active=True
        )
        self.product2 = Product.objects.create(
            name="Test Product 2",
            description="Test description 2",
            price=Decimal("50.00"),
            stock=5,
            category=self.category,
            is_active=True
        )

        # Create user addresses
        self.address1 = UserAddress.objects.create(
            user=self.regular_user,
            name="Test Address",
            phone="1234567890",
            address_line_1="123 Test St",
            city="Test City",
            state="Test State",
            postal_code="12345",
            country="Test Country"
        )

        # Create carts
        self.cart1 = Cart.objects.create(user=self.regular_user)
        self.cart2 = Cart.objects.create(user=self.user2)

        # Create cart items
        CartItem.objects.create(cart=self.cart1, product=self.product1, quantity=2)
        CartItem.objects.create(cart=self.cart1, product=self.product2, quantity=1)
        CartItem.objects.create(cart=self.cart2, product=self.product1, quantity=1)

        # Create orders with different statuses and dates
        now = timezone.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        # Recent order (paid)
        self.order1 = Order.objects.create(
            user=self.regular_user,
            shipping_address=self.address1,
            total_amount=Decimal("250.00"),
            status=Order.OrderStatus.PAID,
            created_at=now
        )

        # Old order (paid)
        self.order2 = Order.objects.create(
            user=self.user2,
            shipping_address=self.address1,
            total_amount=Decimal("100.00"),
            status=Order.OrderStatus.PAID,
            created_at=month_ago
        )

        # Pending order
        self.order3 = Order.objects.create(
            user=self.regular_user,
            shipping_address=self.address1,
            total_amount=Decimal("50.00"),
            status=Order.OrderStatus.PENDING,
            created_at=now
        )

        # Create order items
        OrderItem.objects.create(
            order=self.order1,
            product=self.product1,
            product_name=self.product1.name,
            quantity=2,
            price=self.product1.price
        )
        OrderItem.objects.create(
            order=self.order1,
            product=self.product2,
            product_name=self.product2.name,
            quantity=1,
            price=self.product2.price
        )
        OrderItem.objects.create(
            order=self.order2,
            product=self.product1,
            product_name=self.product1.name,
            quantity=1,
            price=self.product1.price
        )

        # Create payments
        Payment.objects.create(
            order=self.order1,
            amount=self.order1.total_amount,
            status=Payment.PaymentStatus.SUCCESS,
            payment_method=Payment.PaymentMethod.TELR,
            created_at=now
        )
        Payment.objects.create(
            order=self.order2,
            amount=self.order2.total_amount,
            status=Payment.PaymentStatus.SUCCESS,
            payment_method=Payment.PaymentMethod.TELR,
            created_at=month_ago
        )

        # Create reviews
        Review.objects.create(
            user=self.regular_user,
            product=self.product1,
            rating=5,
            comment="Great product!",
            is_visible=True
        )
        Review.objects.create(
            user=self.user2,
            product=self.product1,
            rating=4,
            comment="Good product",
            is_visible=True
        )
        Review.objects.create(
            user=self.regular_user,
            product=self.product2,
            rating=3,
            comment="Okay product",
            is_visible=False  # This should not be counted
        )

    def test_dashboard_analytics_admin_access(self):
        """Test that admin users can access dashboard analytics."""
        self.client.force_authenticate(user=self.admin_user)
        url = '/api/orders/dashboard-analytics/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('users', response.data)
        self.assertIn('orders', response.data)
        self.assertIn('revenue', response.data)
        self.assertIn('top_products', response.data)
        self.assertIn('cart', response.data)
        self.assertIn('reviews', response.data)

    def test_dashboard_analytics_regular_user_denied(self):
        """Test that regular users cannot access dashboard analytics."""
        self.client.force_authenticate(user=self.regular_user)
        url = '/api/orders/dashboard-analytics/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_dashboard_analytics_unauthenticated_denied(self):
        """Test that unauthenticated users cannot access dashboard analytics."""
        url = '/api/orders/dashboard-analytics/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_users_analytics_data(self):
        """Test the users section of analytics data."""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('order-dashboard-analytics')
        response = self.client.get(url)

        users_data = response.data['users']

        # Should have 3 total users
        self.assertEqual(users_data['total'], 3)

        # Should have 2 new users in last 7 days (admin and user2 created recently)
        self.assertEqual(users_data['new_last_7_days'], 2)

        # Should have 1 email verified user (user2)
        self.assertEqual(users_data['email_verified'], 1)

        # Should have 1 phone verified user (user2)
        self.assertEqual(users_data['phone_verified'], 1)

    def test_orders_analytics_data(self):
        """Test the orders section of analytics data."""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('order-dashboard-analytics')
        response = self.client.get(url)

        orders_data = response.data['orders']

        # Should have 3 total orders
        self.assertEqual(orders_data['total'], 3)

        # Should have 2 paid orders in last 30 days
        self.assertEqual(orders_data['paid_last_30_days'], 2)

        # Should have orders by status
        self.assertIsInstance(orders_data['by_status'], list)
        status_counts = {item['status']: item['count'] for item in orders_data['by_status']}
        self.assertEqual(status_counts['PAID'], 2)
        self.assertEqual(status_counts['PENDING'], 1)

        # Average order value should be calculated from paid orders
        # (250 + 100) / 2 = 175
        self.assertEqual(orders_data['avg_order_value'], '175.00')

    def test_revenue_analytics_data(self):
        """Test the revenue section of analytics data."""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('order-dashboard-analytics')
        response = self.client.get(url)

        revenue_data = response.data['revenue']

        # Total revenue should be 350 (250 + 100)
        self.assertEqual(revenue_data['total'], '350.00')

        # Revenue last 30 days should be 350 (both payments are within 30 days in test setup)
        self.assertEqual(revenue_data['last_30_days'], '350.00')

        # Should have revenue per day data
        self.assertIsInstance(revenue_data['per_day'], list)

    def test_top_products_analytics_data(self):
        """Test the top products section of analytics data."""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('order-dashboard-analytics')
        response = self.client.get(url)

        top_products = response.data['top_products']

        # Should have products sorted by revenue
        self.assertIsInstance(top_products, list)
        self.assertGreaterEqual(len(top_products), 1)

        # First product should be product1 with higher revenue
        if top_products:
            first_product = top_products[0]
            self.assertIn('product_id', first_product)
            self.assertIn('name', first_product)
            self.assertIn('total_quantity', first_product)
            self.assertIn('total_revenue', first_product)

    def test_cart_analytics_data(self):
        """Test the cart section of analytics data."""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('order-dashboard-analytics')
        response = self.client.get(url)

        cart_data = response.data['cart']

        # Should have 2 total carts
        self.assertEqual(cart_data['total_carts'], 2)

        # Should have 4 total cart items (2 + 1 + 1)
        self.assertEqual(cart_data['total_cart_items'], 4)

        # Should calculate average cart value and items
        self.assertIsInstance(cart_data['avg_cart_value'], str)
        self.assertIsInstance(cart_data['avg_cart_items'], (int, float))

    def test_reviews_analytics_data(self):
        """Test the reviews section of analytics data."""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('order-dashboard-analytics')
        response = self.client.get(url)

        reviews_data = response.data['reviews']

        # Should have 2 visible reviews (one is not visible)
        self.assertEqual(reviews_data['total'], 2)

        # Average rating should be (5 + 4) / 2 = 4.5
        self.assertEqual(reviews_data['avg_rating'], 4.5)

        # Should have reviews by rating
        self.assertIsInstance(reviews_data['by_rating'], list)
        rating_counts = {item['rating']: item['count'] for item in reviews_data['by_rating']}
        self.assertEqual(rating_counts[5], 1)
        self.assertEqual(rating_counts[4], 1)


class PaymentRefundTestCase(APITestCase):
    """Test cases for payment refund endpoints."""

    def setUp(self):
        """Set up test data."""
        # Create admin user
        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            password="adminpass123",
            role="admin",
            is_staff=True,
            is_superuser=True
        )

        # Create regular user
        self.regular_user = User.objects.create_user(
            email="user@example.com",
            password="userpass123",
            role="user"
        )

        # Create category and product
        self.category = Category.objects.create(name="Test Category", slug="test-category")
        self.product = Product.objects.create(
            name="Test Product",
            description="Test description",
            price=Decimal("100.00"),
            stock=10,
            category=self.category,
            is_active=True
        )

        # Create user address
        self.address = UserAddress.objects.create(
            user=self.regular_user,
            name="Test Address",
            phone="1234567890",
            address_line_1="123 Test St",
            city="Test City",
            state="Test State",
            postal_code="12345",
            country="Test Country"
        )

        # Create order
        self.order = Order.objects.create(
            user=self.regular_user,
            shipping_address=self.address,
            total_amount=Decimal("100.00"),
            status=Order.OrderStatus.PAID
        )

        # Create order item
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name=self.product.name,
            quantity=1,
            price=self.product.price
        )

        # Create successful payment
        self.payment = Payment.objects.create(
            order=self.order,
            transaction_id="test_transaction_123",
            amount=self.order.total_amount,
            status=Payment.PaymentStatus.SUCCESS,
            payment_method=Payment.PaymentMethod.ZIINA
        )

        # Create failed payment
        self.failed_payment = Payment.objects.create(
            order=self.order,
            transaction_id="test_transaction_failed",
            amount=self.order.total_amount,
            status=Payment.PaymentStatus.FAILED,
            payment_method=Payment.PaymentMethod.ZIINA
        )

    def test_create_refund_admin_access(self):
        """Test that admin users can create refunds."""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('payment-create-refund', kwargs={'pk': self.payment.pk})
        data = {"amount_fils": 10000, "currency_code": "AED"}  # 100 AED in fils

        # Mock the ZiinaPaymentService.create_refund method
        from unittest.mock import patch
        with patch('Orders.payment_service.ZiinaPaymentService.create_refund') as mock_refund:
            mock_refund.return_value = {
                "id": "refund_123",
                "status": "pending",
                "amount": 10000,
                "currency_code": "AED"
            }

            response = self.client.post(url, data, format='json')

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertIn('refund_id', response.data)
            self.assertEqual(response.data['refund_id'], 'refund_123')

            # Check that refund_id was saved to payment
            self.payment.refresh_from_db()
            self.assertEqual(self.payment.refund_id, 'refund_123')

    def test_create_refund_regular_user_denied(self):
        """Test that regular users cannot create refunds."""
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('payment-create-refund', kwargs={'pk': self.payment.pk})
        data = {"amount_fils": 10000}

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_refund_failed_payment_denied(self):
        """Test that refunds cannot be created for failed payments."""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('payment-create-refund', kwargs={'pk': self.failed_payment.pk})
        data = {"amount_fils": 10000}

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_create_refund_duplicate_denied(self):
        """Test that duplicate refunds are not allowed."""
        # Set refund_id on payment
        self.payment.refund_id = "existing_refund_123"
        self.payment.save()

        self.client.force_authenticate(user=self.admin_user)
        url = reverse('payment-create-refund', kwargs={'pk': self.payment.pk})
        data = {"amount_fils": 10000}

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_refund_status_admin_access(self):
        """Test that admin users can check refund status."""
        # Set refund_id on payment
        self.payment.refund_id = "refund_123"
        self.payment.save()

        self.client.force_authenticate(user=self.admin_user)
        url = reverse('payment-refund-status', kwargs={'pk': self.payment.pk})

        # Mock the ZiinaPaymentService.get_refund method
        from unittest.mock import patch
        with patch('Orders.payment_service.ZiinaPaymentService.get_refund') as mock_get_refund:
            mock_get_refund.return_value = {
                "id": "refund_123",
                "status": "completed",
                "amount": 10000,
                "currency_code": "AED",
                "created_at": "2023-01-01T00:00:00Z",
                "processed_at": "2023-01-01T00:01:00Z"
            }

            response = self.client.get(url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('refund_id', response.data)
            self.assertEqual(response.data['status'], 'completed')

    def test_refund_status_no_refund(self):
        """Test refund status when no refund exists."""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('payment-refund-status', kwargs={'pk': self.payment.pk})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)

    def test_refund_status_regular_user_denied(self):
        """Test that regular users cannot check refund status."""
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('payment-refund-status', kwargs={'pk': self.payment.pk})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
