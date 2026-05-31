"""OTP code generation (random by default; fixed code for whitelisted test accounts)."""
from __future__ import annotations

import random
import re

from django.conf import settings


def _normalize_phone(phone_number: str) -> str:
    return re.sub(r"\D", "", str(phone_number or "").strip())


def _test_user_emails() -> set[str]:
    raw = str(getattr(settings, "TEST_USER_EMAILS", "") or "")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def _test_user_phones() -> set[str]:
    raw = str(getattr(settings, "TEST_USER_PHONES", "") or "")
    return {_normalize_phone(p) for p in raw.split(",") if p.strip()}


def is_test_user_contact(*, otp_type: str, email: str | None = None, phone_number: str | None = None) -> bool:
    if not getattr(settings, "TEST_USER_ENABLED", False):
        return False
    if otp_type == "email" and email:
        return email.strip().lower() in _test_user_emails()
    if otp_type == "phone" and phone_number:
        return _normalize_phone(phone_number) in _test_user_phones()
    return False


def generate_otp_code(*, otp_type: str, email: str | None = None, phone_number: str | None = None) -> str:
    """
    Return a 6-digit OTP string.

    Whitelisted test contacts (TEST_USER_ENABLED + emails/phones in env) get
    TEST_USER_OTP (default 000000). Everyone else gets a random code.
    """
    if is_test_user_contact(otp_type=otp_type, email=email, phone_number=phone_number):
        fixed = str(getattr(settings, "TEST_USER_OTP", "000000") or "000000").strip()
        if fixed.isdigit() and len(fixed) <= 6:
            return fixed.zfill(6)
        return "000000"
    return str(random.randint(100000, 999999))
