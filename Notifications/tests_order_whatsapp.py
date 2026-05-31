from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase

from Notifications.order_whatsapp import (
    build_order_status_whatsapp_components,
    format_order_whatsapp_var1,
    format_order_whatsapp_var2,
    get_order_header_image_url,
)


class OrderWhatsAppFormatTests(SimpleTestCase):
    def test_var1_includes_order_and_status(self):
        order = MagicMock()
        order.id = 42
        order.get_status_display.return_value = "Paid"
        order.user.first_name = "Ali"
        text = format_order_whatsapp_var1(order, "Payment received.")
        self.assertIn("Order #42", text)
        self.assertIn("Paid", text)
        self.assertIn("Payment received", text)

    def test_components_match_msg91_shape(self):
        order = MagicMock()
        components, err = build_order_status_whatsapp_components(
            order,
            "Status line",
            "Details line",
            header_image_url="https://simakfresh.ae/media/products/x.png",
        )
        self.assertIsNone(err)
        self.assertEqual(components["header_1"]["type"], "image")
        self.assertEqual(components["body_var_1"]["parameter_name"], "var_1")
        self.assertEqual(components["body_var_2"]["parameter_name"], "var_2")


class OrderWhatsAppHeaderImageTests(TestCase):
    def test_fallback_url_when_no_product_image(self):
        from django.contrib.auth import get_user_model
        from Orders.models import Order

        User = get_user_model()
        user = User.objects.create_user(email="wa_test@example.com", password=None)
        order = Order.objects.create(user=user, total_amount=Decimal("10.00"), status="PENDING")
        with patch("Notifications.push_images.settings") as mock_settings:
            mock_settings.SITE_URL = "https://simakfresh.ae"
            mock_settings.ORDER_STATUS_PUSH_IMAGE_URL = ""
            mock_settings.MSG91_ORDER_STATUS_HEADER_IMAGE_URL = "https://simakfresh.ae/fallback.png"
            mock_settings.MSG91_ORDER_PENDING_HEADER_IMAGE_URL = ""
            url = get_order_header_image_url(order)
        self.assertEqual(url, "https://simakfresh.ae/fallback.png")
