"""
Central email delivery for Simak Fresh.

All outbound email must go through EmailService so USE_REAL_SMTP is enforced
consistently. HTML emails load the logo from media/branding/email_logo.png.
"""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Each attachment: (filename, content_bytes, mimetype)
EmailAttachment = Tuple[str, bytes, str]

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

# Single canonical logo used in all emails (user-maintained).
BRANDING_LOGO_RELATIVE = Path("media/branding/email_logo.png")


class EmailService:
    @staticmethod
    def is_enabled() -> bool:
        return bool(getattr(settings, "USE_REAL_SMTP", False))

    @staticmethod
    def get_logo_path() -> Path:
        configured = getattr(settings, "EMAIL_LOGO_PATH", None)
        if configured:
            return Path(configured)
        return Path(settings.BASE_DIR) / BRANDING_LOGO_RELATIVE

    @staticmethod
    def get_logo_url() -> str:
        explicit = getattr(settings, "EMAIL_LOGO_URL", None)
        site = getattr(settings, "SITE_URL", "https://simakfresh.ae").rstrip("/")
        base = explicit or f"{site}/media/branding/email_logo.png"

        logo_path = EmailService.get_logo_path()
        if logo_path.is_file():
            version = int(logo_path.stat().st_mtime)
            separator = "&" if "?" in base else "?"
            return f"{base}{separator}v={version}"
        return base

    @staticmethod
    def logo_file_is_valid() -> bool:
        logo_path = EmailService.get_logo_path()
        if not logo_path.is_file():
            return False
        with logo_path.open("rb") as logo_file:
            return logo_file.read(8).startswith(b"\x89PNG\r\n\x1a\n")

    @staticmethod
    def get_base_context() -> Dict[str, Any]:
        site_url = getattr(settings, "SITE_URL", "https://simakfresh.ae").rstrip("/")
        return {
            "site_url": site_url,
            "logo_url": EmailService.get_logo_url(),
            "logo_available": EmailService.logo_file_is_valid(),
            "app_name": getattr(settings, "APP_NAME", "Simak Fresh"),
            "store_motto": getattr(settings, "STORE_MOTTO", "Live Seafood from SEA to HOME"),
            "support_email": getattr(settings, "SUPPORT_EMAIL", "support@simakfresh.com"),
        }

    @staticmethod
    def render(template_name: str, context: Optional[Dict[str, Any]] = None) -> str:
        merged = {**EmailService.get_base_context(), **(context or {})}
        return render_to_string(template_name, merged)

    @staticmethod
    def build_receipt_pdf_attachment(order, receipt) -> Optional[EmailAttachment]:
        """Build customer PDF receipt bytes for email attachment."""
        from Orders.receipt_templates import render_receipt_pdf

        logo_path = EmailService.get_logo_path()
        logo_arg = str(logo_path) if logo_path.is_file() else None
        try:
            pdf_buffer = render_receipt_pdf(order, receipt, logo_path=logo_arg)
            filename = f"SimakFresh_Receipt_{receipt.receipt_number}.pdf"
            return filename, pdf_buffer.getvalue(), "application/pdf"
        except Exception:
            logger.exception("Failed to generate receipt PDF for order #%s", order.id)
            return None

    @staticmethod
    def send(
        recipient_email: str,
        subject: str,
        plain_message: str,
        html_template: Optional[str] = None,
        template_context: Optional[Dict[str, Any]] = None,
        attachments: Optional[List[EmailAttachment]] = None,
        fail_silently: bool = False,
    ) -> Tuple[bool, Dict[str, Any]]:
        if not recipient_email:
            return False, {"error": "missing recipient email"}

        if not EmailService.is_enabled():
            logger.info(
                "Email skipped (USE_REAL_SMTP=false): subject=%r recipient=%s",
                subject,
                recipient_email,
            )
            return True, {"status": "skipped", "reason": "USE_REAL_SMTP is false"}

        from_email = settings.DEFAULT_FROM_EMAIL
        plain_message = (plain_message or "").strip()

        try:
            if html_template:
                html_message = EmailService.render(html_template, template_context)
                message = EmailMultiAlternatives(
                    subject=subject,
                    body=plain_message or "Please view this message in an HTML-capable email client.",
                    from_email=from_email,
                    to=[recipient_email],
                )
                message.attach_alternative(html_message, "text/html")
                for filename, content, mimetype in attachments or []:
                    message.attach(filename, content, mimetype)
                message.send(fail_silently=fail_silently)
            else:
                send_mail(
                    subject=subject,
                    message=plain_message,
                    from_email=from_email,
                    recipient_list=[recipient_email],
                    fail_silently=fail_silently,
                )
            return True, {"status": "sent"}
        except Exception as exc:
            logger.exception("Email send failed: subject=%r recipient=%s", subject, recipient_email)
            return False, {"error": str(exc)}

    @staticmethod
    def send_template(
        recipient_email: str,
        subject: str,
        html_template: str,
        template_context: Optional[Dict[str, Any]] = None,
        plain_message: Optional[str] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        return EmailService.send(
            recipient_email=recipient_email,
            subject=subject,
            plain_message=plain_message or subject,
            html_template=html_template,
            template_context=template_context,
        )
