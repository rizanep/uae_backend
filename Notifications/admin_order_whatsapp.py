"""
MSG91 WhatsApp `admin_order_notification` template for store admins.

Template layout (MSG91):
  - body var_1: paid order headline
  - body var_2: order details
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from django.conf import settings

from Notifications.order_whatsapp import (
    _whatsapp_body_value,
    format_order_whatsapp_var2,
)


def resolve_admin_order_whatsapp_template_name() -> str:
    name = str(
        getattr(settings, "MSG91_ADMIN_ORDER_WHATSAPP_TEMPLATE_NAME", "") or ""
    ).strip()
    name = name.strip('"').strip("'")
    if name:
        return name
    fallback = str(
        getattr(settings, "MSG91_ADMIN_NOTIFICATION_WHATSAPP_TEMPLATE_NAME", "") or ""
    ).strip()
    return fallback.strip('"').strip("'") or "admin_order_notification"


def get_admin_order_whatsapp_phone() -> str:
    return str(getattr(settings, "ADMIN_ORDER_WHATSAPP_PHONE", "") or "").strip()


def format_admin_order_whatsapp_var1(order) -> str:
    """var_1: short admin headline when order is paid."""
    user = order.user
    contact = (user.email or user.phone_number or "unknown").strip()
    name = (user.first_name or "").strip()
    if name:
        customer = f"{name} ({contact})"
    else:
        customer = contact

    total = order.total_amount
    text = (
        f"Order #{order.id} is PAID. Customer: {customer}. "
        f"Total AED {total:.2f}. Payment confirmed - please prepare the order."
    )
    return _whatsapp_body_value(text)


def build_admin_order_whatsapp_components(
    var_1: str,
    var_2: str,
) -> Tuple[Dict[str, Dict[str, Any]], None]:
    """Build MSG91 components dict (body only, no header)."""
    components = {
        "body_var_1": {
            "type": "text",
            "value": _whatsapp_body_value(var_1),
            "parameter_name": "var_1",
        },
        "body_var_2": {
            "type": "text",
            "value": _whatsapp_body_value(var_2),
            "parameter_name": "var_2",
        },
    }
    return components, None


def send_admin_order_whatsapp(
    order,
    *,
    template_name: Optional[str] = None,
    admin_phone: Optional[str] = None,
) -> Tuple[bool, Dict]:
    """Send admin_order_notification WhatsApp when order is paid."""
    from Notifications.services import UnifiedNotificationService

    phone = (admin_phone or get_admin_order_whatsapp_phone()).strip()
    if not phone:
        return False, {"error": "ADMIN_ORDER_WHATSAPP_PHONE not configured"}

    var_1 = format_admin_order_whatsapp_var1(order)
    var_2 = format_order_whatsapp_var2(order)
    components, _ = build_admin_order_whatsapp_components(var_1, var_2)

    tpl = template_name or resolve_admin_order_whatsapp_template_name()
    if not tpl:
        return False, {"error": "missing MSG91 admin order WhatsApp template name"}

    return UnifiedNotificationService.send_whatsapp(
        phone_number=phone,
        template_name=tpl,
        components=components,
    )
