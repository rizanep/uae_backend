from django.test import SimpleTestCase, override_settings

from Users.otp_utils import generate_otp_code, is_test_user_contact


class GenerateOtpCodeTests(SimpleTestCase):
    @override_settings(TEST_USER_ENABLED=False)
    def test_random_otp_when_test_users_disabled(self):
        codes = {generate_otp_code(otp_type="phone", phone_number="+971501234567") for _ in range(20)}
        self.assertTrue(all(c.isdigit() and len(c) == 6 for c in codes))
        self.assertTrue(any(c != "000000" for c in codes))

    @override_settings(
        TEST_USER_ENABLED=True,
        TEST_USER_EMAILS="test@example.com",
        TEST_USER_PHONES="971501111111",
        TEST_USER_OTP="000000",
    )
    def test_fixed_otp_for_whitelisted_contacts(self):
        self.assertEqual(
            generate_otp_code(otp_type="email", email="test@example.com"),
            "000000",
        )
        self.assertEqual(
            generate_otp_code(otp_type="phone", phone_number="+971501111111"),
            "000000",
        )

    @override_settings(
        TEST_USER_ENABLED=True,
        TEST_USER_EMAILS="test@example.com",
        TEST_USER_OTP="000000",
    )
    def test_random_otp_for_non_whitelisted(self):
        code = generate_otp_code(otp_type="email", email="other@example.com")
        self.assertNotEqual(code, "000000")

    @override_settings(TEST_USER_ENABLED=True, TEST_USER_EMAILS="a@b.com")
    def test_is_test_user_contact(self):
        self.assertTrue(is_test_user_contact(otp_type="email", email="a@b.com"))
        self.assertFalse(is_test_user_contact(otp_type="email", email="x@y.com"))
