import logging
import re
from typing import Dict, Optional, Tuple

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from SMS.services import MSG91SMSService
from WhatsApp.services import MSG91WhatsAppService

logger = logging.getLogger(__name__)


class UnifiedNotificationService:
    """Channel abstraction used by Celery tasks for OTP and order notifications."""

    @staticmethod
    def normalize_phone(phone_number: str) -> str:
        """Digits only (E.164 without +), for MSG91."""
        if not phone_number:
            return ""
        cleaned = re.sub(r"\D", "", str(phone_number).strip())
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
        components: Optional[Dict] = None,
    ) -> Tuple[bool, Dict]:
        normalized_phone = UnifiedNotificationService.normalize_phone(phone_number)
        if not normalized_phone:
            return False, {"error": "invalid phone number"}

        if not getattr(settings, "USE_REAL_MSG91_WHATSAPP", False):
            return True, {"status": "skipped", "reason": "USE_REAL_MSG91_WHATSAPP is false"}

        if not template_name:
            return False, {"error": "missing MSG91 WhatsApp template name"}

        try:
            service = MSG91WhatsAppService()
            success, response = service.send_message(
                template_name=template_name,
                recipient_number=normalized_phone,
                variables=variables or {},
                components=components,
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
        html_template: Optional[str] = None,
        template_context: Optional[Dict] = None,
        html_message: Optional[str] = None,
    ) -> Tuple[bool, Dict]:
        from Notifications.email_service import EmailService

        return EmailService.send(
            recipient_email=recipient_email,
            subject=subject,
            plain_message=message,
            html_template=html_template,
            template_context=template_context,
        )
