from django.test import TestCase, override_settings

from .serializers import OTPRequestSerializer, OTPLoginSerializer
from .models import User


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


@override_settings(
	TEST_USER_ENABLED=True,
	TEST_USER_EMAIL='testuser@test.com',
	TEST_USER_OTP='000000',
	USE_REAL_SMTP=True,
)
class TestUserOTPTests(TestCase):
	def test_request_uses_fixed_otp_for_test_email(self):
		serializer = OTPRequestSerializer(
			data={
				'otp_type': 'email',
				'email': 'testuser@test.com',
			}
		)
		self.assertTrue(serializer.is_valid(), serializer.errors)
		otp = serializer.save()
		self.assertEqual(otp.otp_code, '000000')

	def test_login_accepts_fixed_otp_without_prior_request(self):
		serializer = OTPLoginSerializer(
			data={
				'otp_type': 'email',
				'email': 'testuser@test.com',
				'otp_code': '000000',
			}
		)
		self.assertTrue(serializer.is_valid(), serializer.errors)
		self.assertTrue(serializer.validated_data.get('is_test_login'))
		user = serializer.validated_data['user']
		self.assertEqual(user.email, 'testuser@test.com')

	def test_login_rejects_wrong_otp_for_test_email(self):
		User.objects.create_user(email='testuser@test.com', password=None)
		serializer = OTPLoginSerializer(
			data={
				'otp_type': 'email',
				'email': 'testuser@test.com',
				'otp_code': '123456',
			}
		)
		self.assertFalse(serializer.is_valid())
