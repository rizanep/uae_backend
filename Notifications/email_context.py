"""Shared context for HTML email templates (delegates to EmailService)."""
from Notifications.email_service import EmailService


def build_email_context(**extra):
    return {**EmailService.get_base_context(), **extra}
