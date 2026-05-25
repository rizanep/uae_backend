import http.client
import json
import logging
import re
import ssl
from typing import Dict, Optional, Tuple

from django.conf import settings
<<<<<<< HEAD
from Notifications.email_service import EmailService
from SMS.services import MSG91SMSService
from WhatsApp.services import MSG91WhatsAppService
=======
from django.core.mail import send_mail
>>>>>>> dev

logger = logging.getLogger(__name__)


class MSG91Service:
    """
    Lightweight MSG91 API client.
    Calls MSG91 templates directly via HTTPS — no database models required.
    Configure templates on the MSG91 platform and reference them by ID / name.
    """

    HOST = "control.msg91.com"

    def __init__(self):
        self.auth_key = getattr(settings, "MSG91_AUTH_KEY", "")
        self.integrated_number = getattr(settings, "MSG91_INTEGRATED_NUMBER", "")

    def _post(self, endpoint: str, payload: dict) -> Tuple[bool, dict]:
        try:
            context = ssl.create_default_context()
            conn = http.client.HTTPSConnection(self.HOST, context=context, timeout=30)
            headers = {
                "authkey": self.auth_key,
                "content-type": "application/json",
                "accept": "application/json",
            }
            conn.request("POST", f"/{endpoint}", json.dumps(payload), headers)
            resp = conn.getresponse()
            body = resp.read().decode("utf-8")
            conn.close()
            try:
                data = json.loads(body) if body else {}
            except json.JSONDecodeError:
                data = {"raw": body}
            success = 200 <= resp.status < 300
            if not success:
                logger.warning("MSG91 %s error %s: %s", endpoint, resp.status, data)
            return success, data
        except Exception as exc:
            logger.exception("MSG91 request to %s failed", endpoint)
            return False, {"error": str(exc)}

    def send_sms(self, template_id: str, mobile: str, variables: Optional[Dict] = None) -> Tuple[bool, dict]:
        """Send SMS via MSG91 flow (template) API."""
        recipient = {"mobiles": mobile}
        if variables:
            recipient.update({k: str(v) for k, v in variables.items()})
        return self._post("api/v5/flow", {
            "template_id": template_id,
            "short_url": "0",
            "recipients": [recipient],
        })

    def send_whatsapp(self, template_name: str, mobile: str, variables: Optional[Dict] = None, components: Optional[Dict] = None) -> Tuple[bool, dict]:
        """Send WhatsApp message via MSG91 outbound template API (to_and_components format).

        Use `components` to pass a fully-formed component dict directly (e.g. for image
        headers or URL buttons).  If `components` is omitted, it is built from `variables`
        where body_* keys map to text components and button_* keys map to url components.
        """
        if components is None:
            # Build named components from body_* and button_* variable keys only.
            # VAR* keys are SMS-specific and are excluded here.
            components = {}
            for key, value in (variables or {}).items():
                if key.startswith('body_'):
                    components[key] = {"type": "text", "text": str(value)}
                elif key.startswith('button_'):
                    components[key] = {"subtype": "url", "type": "text", "text": str(value)}

        template_payload: Dict = {
            "name": template_name,
            "language": {"code": "en", "policy": "deterministic"},
            "to_and_components": [
                {
                    "to": [mobile],
                    "components": components,
                }
            ],
        }
        namespace = getattr(settings, "MSG91_WHATSAPP_NAMESPACE", "")
        if namespace:
            template_payload["namespace"] = namespace

        payload = {
            "integrated_number": self.integrated_number,
            "content_type": "template",
            "payload": {
                "messaging_product": "whatsapp",
                "type": "template",
                "template": template_payload,
            },
        }
        return self._post("api/v5/whatsapp/whatsapp-outbound-message/bulk/", payload)


class UnifiedNotificationService:
    """Channel abstraction used by Celery tasks."""

    @staticmethod
    def _print_console_skip(channel: str, payload: Dict) -> None:
        msg = f"[{channel} CONSOLE MODE] {json.dumps(payload, default=str)}"
        print(msg)
        logger.info(msg)

    @staticmethod
    def normalize_phone(phone_number: str) -> str:
        if not phone_number:
            return ""
        cleaned = re.sub(r"[^\d+]", "", str(phone_number).strip())
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
    ) -> Tuple[bool, Dict]:
        mobile = UnifiedNotificationService.normalize_phone(phone_number)
        if not mobile:
            return False, {"error": "invalid phone number"}
        if not getattr(settings, "USE_REAL_MSG91_SMS", False):
            UnifiedNotificationService._print_console_skip("SMS", {
                "phone_number": mobile,
                "template_id": template_id,
                "variables": variables or {},
            })
            return True, {"status": "skipped", "reason": "USE_REAL_MSG91_SMS is false"}
        if not template_id:
            return False, {"error": "missing MSG91 SMS template id"}
        try:
            success, response = MSG91Service().send_sms(template_id, mobile, variables)
            if not success:
                logger.warning(
                    "SMS send failed",
                    extra={"phone": UnifiedNotificationService._mask_phone(mobile), "response": response},
                )
            return success, response
        except Exception as exc:
            logger.exception("SMS send exception for %s", UnifiedNotificationService._mask_phone(mobile))
            return False, {"error": str(exc)}

    @staticmethod
    def send_whatsapp(
        phone_number: str,
        template_name: Optional[str],
        variables: Optional[Dict] = None,
        components: Optional[Dict] = None,
    ) -> Tuple[bool, Dict]:
        mobile = UnifiedNotificationService.normalize_phone(phone_number)
        if not mobile:
            return False, {"error": "invalid phone number"}
        if not getattr(settings, "USE_REAL_MSG91_WHATSAPP", False):
            UnifiedNotificationService._print_console_skip("WHATSAPP", {
                "phone_number": mobile,
                "template_name": template_name,
                "variables": variables or {},
                "components": components or {},
            })
            return True, {"status": "skipped", "reason": "USE_REAL_MSG91_WHATSAPP is false"}
        if not template_name:
            return False, {"error": "missing MSG91 WhatsApp template name"}
        try:
            success, response = MSG91Service().send_whatsapp(template_name, mobile, variables, components)
            if not success:
                logger.warning(
                    "WhatsApp send failed",
                    extra={"phone": UnifiedNotificationService._mask_phone(mobile), "response": response},
                )
            return success, response
        except Exception as exc:
            logger.exception("WhatsApp send exception for %s", UnifiedNotificationService._mask_phone(mobile))
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
<<<<<<< HEAD
        return EmailService.send(
            recipient_email=recipient_email,
            subject=subject,
            plain_message=message,
            html_template=html_template,
            template_context=template_context,
        )
=======
        if not recipient_email:
            return False, {"error": "missing recipient email"}
        if not getattr(settings, "USE_REAL_SMTP", False):
            UnifiedNotificationService._print_console_skip("EMAIL", {
                "recipient_email": recipient_email,
                "subject": subject,
                "message": message,
                "html_message": bool(html_message),
            })
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
            logger.exception("Email send exception for %s", recipient_email)
            return False, {"error": str(exc)}
>>>>>>> dev
