import logging
import re
from typing import Dict, Optional, Tuple

from django.conf import settings
from django.core.mail import send_mail

from SMS.services import MSG91SMSService
from WhatsApp.services import MSG91WhatsAppService

logger = logging.getLogger(__name__)


class UnifiedNotificationService:
    """Channel abstraction used by Celery tasks for OTP and order notifications."""

    # Whitelisted numbers for testing (only these receive real messages in test mode)
    TESTING_WHITELISTED_NUMBERS = ['918281740483', '91-8281-740483']

    @staticmethod
    def is_whitelisted_for_testing(phone_number: str) -> bool:
        """Check if phone number is whitelisted for testing."""
        normalized = UnifiedNotificationService.normalize_phone(phone_number)
        for whitelisted in UnifiedNotificationService.TESTING_WHITELISTED_NUMBERS:
            if normalized == UnifiedNotificationService.normalize_phone(whitelisted):
                return True
        return False

    @staticmethod
    def normalize_phone(phone_number: str) -> str:
        if not phone_number:
            return ""
        cleaned = re.sub(r"[^\d+]", "", str(phone_number).strip())
        if not cleaned:
            return ""
        # Return as-is (handles +country format and direct country code format)
        return cleaned

    @staticmethod
    def _mask_phone(phone_number: str) -> str:
        normalized = UnifiedNotificationService.normalize_phone(phone_number)
        if len(normalized) <= 4:
            return normalized
        return f"{normalized[:3]}***{normalized[-2:]}"

    @staticmethod
    def send_sms(
        phone_number: str,
        template_id: Optional[str],
        variables: Optional[Dict] = None,
        realtime_response: bool = True,
    ) -> Tuple[bool, Dict]:
        normalized_phone = UnifiedNotificationService.normalize_phone(phone_number)
        if not normalized_phone:
            return False, {"error": "invalid phone number"}

        if not getattr(settings, "USE_REAL_MSG91_SMS", False):
            return True, {"status": "skipped", "reason": "USE_REAL_MSG91_SMS is false"}

        # Safety check: only allow real SMS to whitelisted test numbers
        if not UnifiedNotificationService.is_whitelisted_for_testing(normalized_phone):
            logger.warning(
                "SMS blocked: number not whitelisted for testing",
                extra={"phone": UnifiedNotificationService._mask_phone(normalized_phone)},
            )
            return True, {"status": "blocked", "reason": "number not whitelisted - spam prevention"}

        if not template_id:
            return False, {"error": "missing MSG91 SMS template id"}

        try:
            service = MSG91SMSService()
            success, response = service.send_message(
                template_id=template_id,
                recipient_number=normalized_phone,
                variables=variables or {},
                realtime_response=realtime_response,
            )
            if not success:
                logger.warning(
                    "SMS send failed",
                    extra={"phone": UnifiedNotificationService._mask_phone(normalized_phone), "response": response},
                )
            return success, response
        except Exception as exc:
            logger.exception(
                "SMS send exception",
                extra={"phone": UnifiedNotificationService._mask_phone(normalized_phone)},
            )
            return False, {"error": str(exc)}

    @staticmethod
    def send_whatsapp(
        phone_number: str,
        template_name: Optional[str],
        variables: Optional[Dict] = None,
    ) -> Tuple[bool, Dict]:
        normalized_phone = UnifiedNotificationService.normalize_phone(phone_number)
        if not normalized_phone:
            return False, {"error": "invalid phone number"}

        if not getattr(settings, "USE_REAL_MSG91_WHATSAPP", False):
            return True, {"status": "skipped", "reason": "USE_REAL_MSG91_WHATSAPP is false"}

        # Safety check: only allow real WhatsApp to whitelisted test numbers
        if not UnifiedNotificationService.is_whitelisted_for_testing(normalized_phone):
            logger.warning(
                "WhatsApp blocked: number not whitelisted for testing",
                extra={"phone": UnifiedNotificationService._mask_phone(normalized_phone)},
            )
            return True, {"status": "blocked", "reason": "number not whitelisted - spam prevention"}

        if not template_name:
            return False, {"error": "missing MSG91 WhatsApp template name"}

        try:
            service = MSG91WhatsAppService()
            success, response = service.send_message(
                template_name=template_name,
                recipient_number=normalized_phone,
                variables=variables or {},
            )
            if not success:
                logger.warning(
                    "WhatsApp send failed",
                    extra={"phone": UnifiedNotificationService._mask_phone(normalized_phone), "response": response},
                )
            return success, response
        except Exception as exc:
            logger.exception(
                "WhatsApp send exception",
                extra={"phone": UnifiedNotificationService._mask_phone(normalized_phone)},
            )
            return False, {"error": str(exc)}

    @staticmethod
    def send_email(
        recipient_email: str,
        subject: str,
        message: str,
        html_message: Optional[str] = None,
    ) -> Tuple[bool, Dict]:
        if not recipient_email:
            return False, {"error": "missing recipient email"}

        if not getattr(settings, "USE_REAL_SMTP", False):
            return True, {"status": "skipped", "reason": "USE_REAL_SMTP is false"}

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                html_message=html_message,
                fail_silently=False,
            )
            return True, {"status": "sent"}
        except Exception as exc:
            logger.exception("Email send exception", extra={"recipient_email": recipient_email})
            return False, {"error": str(exc)}
