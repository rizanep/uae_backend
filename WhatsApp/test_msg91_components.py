"""Unit tests for MSG91 WhatsApp template component building."""
from django.test import SimpleTestCase

from WhatsApp.services import MSG91WhatsAppService


class MSG91TemplateComponentsTests(SimpleTestCase):
    def test_otp_components_include_url_button(self):
        components = MSG91WhatsAppService.build_template_components(
            {"body_1": "123456", "button_1": "123456"}
        )
        self.assertEqual(
            components["body_1"],
            {"type": "text", "value": "123456"},
        )
        self.assertEqual(
            components["button_1"],
            {"subtype": "url", "type": "text", "value": "123456"},
        )

    def test_prebuilt_component_dict_passthrough(self):
        image_header = {"type": "image", "value": "https://example.com/img.png"}
        components = MSG91WhatsAppService.build_template_components(
            {"header_1": image_header}
        )
        self.assertEqual(components["header_1"], image_header)

    def test_normalize_recipient_strips_plus(self):
        self.assertEqual(
            MSG91WhatsAppService.normalize_recipient_number("+918281740483"),
            "918281740483",
        )
