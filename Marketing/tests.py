from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from Orders.models import DeliveryChargeConfig, DeliveryTimeSlot
from datetime import time

User = get_user_model()


class PromotionalContentTestCase(APITestCase):
    """Test cases for promotional content endpoints."""

    def setUp(self):
        """Set up test data."""
        # Create delivery charge config
        self.delivery_config = DeliveryChargeConfig.get_config()
        self.delivery_config.min_free_shipping_amount = 20.00
        self.delivery_config.delivery_charge = 5.00
        self.delivery_config.is_active = True
        self.delivery_config.save()

        # Create delivery time slots
        self.morning_slot = DeliveryTimeSlot.objects.create(
            name="Morning Slot",
            start_time=time(8, 0),  # 8:00 AM
            end_time=time(9, 0),    # 9:00 AM
            cutoff_time=time(7, 30),  # 7:30 AM
            is_active=True,
            sort_order=1
        )

        self.afternoon_slot = DeliveryTimeSlot.objects.create(
            name="Afternoon Slot",
            start_time=time(11, 0),  # 11:00 AM
            end_time=time(12, 0),    # 12:00 PM
            cutoff_time=time(10, 30),  # 10:30 AM
            is_active=True,
            sort_order=2
        )

    def test_delivery_offers_endpoint(self):
        """Test that the delivery offers endpoint returns promotional text."""
        url = reverse('promotional-delivery-offers')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('promotional_texts', response.data)
        self.assertIn('timestamp', response.data)
        self.assertIn('timezone', response.data)

        texts = response.data['promotional_texts']
        self.assertIn('en', texts)
        self.assertIn('ar', texts)
        self.assertIn('zh', texts)

        for lang in ['en', 'ar', 'zh']:
            self.assertIn('free_delivery', texts[lang])
            self.assertIn('delivery_time', texts[lang])
            self.assertIsInstance(texts[lang]['free_delivery'], str)
            self.assertIsInstance(texts[lang]['delivery_time'], str)
            self.assertGreater(len(texts[lang]['free_delivery']), 0)
            self.assertGreater(len(texts[lang]['delivery_time']), 0)

        # Basic language-specific checks
        self.assertIn('20', texts['en']['free_delivery'])
        self.assertIn('free delivery', texts['en']['free_delivery'])
        self.assertIn('درهم', texts['ar']['free_delivery'])
        self.assertIn('免运费', texts['zh']['free_delivery'])

    def test_delivery_offers_unauthenticated(self):
        """Test that the endpoint works for unauthenticated users."""
        url = reverse('promotional-delivery-offers')
        response = self.client.get(url)

        # Should work for unauthenticated users (AllowAny permission)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
