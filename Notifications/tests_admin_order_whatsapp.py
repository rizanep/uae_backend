from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from Notifications.admin_order_whatsapp import (
    build_admin_order_whatsapp_components,
    format_admin_order_whatsapp_var1,
    get_admin_order_whatsapp_phone,
    resolve_admin_order_whatsapp_template_name,
)


class AdminOrderWhatsAppFormatTests(SimpleTestCase):
    def test_var1_paid(self):
        order = MagicMock()
        order.id = 100
        order.total_amount = Decimal("200.00")
        order.user.first_name = "Sara"
        order.user.email = "sara@example.com"
        order.user.phone_number = "971501111111"
        text = format_admin_order_whatsapp_var1(order)
        self.assertIn("PAID", text)
        self.assertIn("Sara", text)
        self.assertIn("sara@example.com", text)

    def test_components_body_only(self):
        components, err = build_admin_order_whatsapp_components("Headline", "Details")
        self.assertIsNone(err)
        self.assertNotIn("header_1", components)
        self.assertEqual(components["body_var_1"]["parameter_name"], "var_1")
        self.assertEqual(components["body_var_2"]["parameter_name"], "var_2")

    @override_settings(
        MSG91_ADMIN_ORDER_WHATSAPP_TEMPLATE_NAME="admin_order_notification",
        ADMIN_ORDER_WHATSAPP_PHONE="918281740483",
    )
    def test_settings_resolution(self):
        self.assertEqual(resolve_admin_order_whatsapp_template_name(), "admin_order_notification")
        self.assertEqual(get_admin_order_whatsapp_phone(), "918281740483")
