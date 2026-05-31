"""Fixed test-user credentials for OTP login (staging/dev only)."""

from django.conf import settings


def test_user_enabled() -> bool:
    return bool(getattr(settings, "TEST_USER_ENABLED", False))


def normalize_email(email: str | None) -> str:
    return (email or "").strip().lower()


def configured_test_user_emails() -> set[str]:
    emails = {
        normalize_email(email)
        for email in getattr(settings, "TEST_USER_EMAILS", [])
        if normalize_email(email)
    }
    legacy_email = normalize_email(getattr(settings, "TEST_USER_EMAIL", ""))
    if legacy_email:
        emails.add(legacy_email)
    return emails


def is_test_user_email(email: str | None) -> bool:
    if not test_user_enabled():
        return False
    configured = configured_test_user_emails()
    if not configured:
        return False
    return normalize_email(email) in configured


def get_test_user_otp() -> str:
    return str(getattr(settings, "TEST_USER_OTP", "000000")).strip()


def is_test_user_login(
    email: str | None,
    phone_number: str | None,
    otp_type: str,
    otp_code: str,
) -> bool:
    if not test_user_enabled() or otp_type != "email":
        return False
    if not is_test_user_email(email):
        return False
    return str(otp_code).strip() == get_test_user_otp()


def get_or_create_test_user(email: str | None = None):
    from .models import User

    selected_email = normalize_email(email)
    configured = configured_test_user_emails()
    if not selected_email or selected_email not in configured:
        selected_email = next(iter(configured), "")
    if not selected_email:
        raise ValueError("No TEST_USER_EMAIL/TEST_USER_EMAILS configured")

    user, _ = User.objects.get_or_create(
        email=selected_email,
        defaults={
            "first_name": "Test",
            "last_name": "User",
            "is_email_verified": True,
        },
    )
    return user
