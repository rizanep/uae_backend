from django.test import TestCase

from .serializers import OTPRequestSerializer


class OTPRequestSerializerTests(TestCase):
	def test_email_otp_forces_internal_platform_value(self):
		serializer = OTPRequestSerializer(
			data={
				'otp_type': 'email',
				'email': 'user@example.com',
				'otp_platform': 'whatsapp',
			}
		)

		self.assertTrue(serializer.is_valid(), serializer.errors)
		self.assertEqual(serializer.validated_data['otp_platform'], 'sms')

	def test_phone_otp_respects_selected_platform(self):
		serializer = OTPRequestSerializer(
			data={
				'otp_type': 'phone',
				'phone_number': '+971500000001',
				'otp_platform': 'whatsapp',
			}
		)

		self.assertTrue(serializer.is_valid(), serializer.errors)
		self.assertEqual(serializer.validated_data['otp_platform'], 'whatsapp')
