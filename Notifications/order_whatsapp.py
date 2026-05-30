"""
MSG91 WhatsApp helpers for order status template `order_status`.

Template layout (MSG91):
  - header_1: product image (image URL)
  - body var_1: status headline + short customer message
  - body var_2: full order details
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

from django.conf import settings
from django.utils import timezone

# WhatsApp template variable safe limit (leave room for template fixed text).
MAX_WHATSAPP_VAR_LEN = 900


def _truncate(text: str, max_len: int = MAX_WHATSAPP_VAR_LEN) -> str:
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def _whatsapp_body_value(text: str) -> str:
    """MSG91 body variables must be a single line (no newlines)."""
    cleaned = (text or "").replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    while "  " in cleaned:
        cleaned = cleaned.replace("  ", " ")
    return _truncate(cleaned.strip())


def resolve_order_status_whatsapp_template_name() -> str:
    name = str(getattr(settings, "MSG91_ORDER_STATUS_WHATSAPP_TEMPLATE_NAME", "") or "").strip()
    name = name.strip('"').strip("'")
    if name:
        return name
    pending = str(getattr(settings, "MSG91_ORDER_PENDING_WHATSAPP_TEMPLATE_NAME", "") or "").strip()
    return pending.strip('"').strip("'") or "order_status"


def get_order_header_image_url(order) -> Optional[str]:
    """Absolute HTTPS URL for template header image."""
    site = (getattr(settings, "SITE_URL", "") or "https://simakfresh.ae").rstrip("/")

    first_item = (
        order.items.select_related("product")
        .filter(product__image__isnull=False)
        .exclude(product__image="")
        .first()
    )
    if first_item and first_item.product and first_item.product.image:
        url = first_item.product.image.url
        if url.startswith("http://") or url.startswith("https://"):
            return url
        return f"{site}{url}"

    for fallback in (
        getattr(settings, "MSG91_ORDER_STATUS_HEADER_IMAGE_URL", ""),
        getattr(settings, "MSG91_ORDER_PENDING_HEADER_IMAGE_URL", ""),
    ):
        if fallback:
            return str(fallback).strip()

    return None


def _format_delivery_line(order) -> str:
    parts = []
    if order.preferred_delivery_date:
        parts.append(order.preferred_delivery_date.strftime("%d %b %Y"))
    slot = order.preferred_delivery_slot
    if slot:
        parts.append(slot.name)
    if parts:
        return "Delivery: " + ", ".join(parts)
    return ""


def _format_address_line(order) -> str:
    snap = order.shipping_address_snapshot or {}
    if snap:
        chunks = [
            snap.get("building_name"),
            snap.get("flat_villa_number"),
            snap.get("street_address"),
            snap.get("area"),
            snap.get("city"),
            snap.get("emirate"),
        ]
        line = ", ".join(c for c in chunks if c)
        if line:
            return f"Address: {line}"
    if order.shipping_address_id:
        addr = order.shipping_address
        if addr:
            chunks = [
                addr.building_name,
                addr.flat_villa_number,
                addr.street_address,
                addr.area,
                addr.city,
                addr.emirate,
            ]
            line = ", ".join(c for c in chunks if c)
            if line:
                return f"Address: {line}"
    return ""


def _format_payment_line(order) -> str:
    try:
        payment = order.payment
    except Exception:
        payment = None
    if payment:
        return f"Payment: {payment.get_payment_method_display()} ({payment.get_status_display()})"
    return ""


def format_order_whatsapp_var1(order, status_message: str) -> str:
    """var_1: status update headline and short message."""
    user = order.user
    name = (user.first_name or "").strip() or "Customer"
    status_label = order.get_status_display()
    text = (
        f"Order #{order.id} - {status_label}. "
        f"Hi {name}, {status_message.strip()}"
    )
    return _whatsapp_body_value(text)


def format_order_whatsapp_var2(order, extra_lines: Optional[list] = None) -> str:
    """var_2: line items, amounts, delivery, address."""
    lines = ["Order details:"]

    items = list(order.items.select_related("product").all())
    if items:
        for item in items[:8]:
            name = item.product_name or (item.product.name if item.product else "Item")
            prep = item.preparation_specification_name
            if prep:
                name = f"{name} ({prep})"
            lines.append(f"- {name} x{item.quantity} - AED {item.subtotal:.2f}")
        if len(items) > 8:
            lines.append(f"- + {len(items) - 8} more item(s)")
    else:
        lines.append("- (no items listed)")

    lines.append("")
    items_subtotal = sum((i.subtotal for i in items), Decimal("0.00"))
    lines.append(f"Items subtotal: AED {items_subtotal:.2f}")
    if order.discount_amount and order.discount_amount > 0:
        code = order.coupon_code or ""
        suffix = f" ({code})" if code else ""
        lines.append(f"Discount{suffix}: -AED {order.discount_amount:.2f}")
    lines.append(f"Delivery: AED {order.delivery_charge:.2f}")
    if order.tip_amount and order.tip_amount > 0:
        lines.append(f"Tip: AED {order.tip_amount:.2f}")
    lines.append(f"Total paid: AED {order.total_amount:.2f}")

    delivery = _format_delivery_line(order)
    if delivery:
        lines.append(delivery)
    if order.delivery_notes:
        lines.append(f"Notes: {order.delivery_notes.strip()}")

    address = _format_address_line(order)
    if address:
        lines.append(address)

    payment = _format_payment_line(order)
    if payment:
        lines.append(payment)

    if order.created_at:
        created = timezone.localtime(order.created_at).strftime("%d %b %Y %I:%M %p")
        lines.append(f"Ordered: {created}")

    if extra_lines:
        for line in extra_lines:
            if line:
                lines.append(str(line).strip())

    return _whatsapp_body_value(" | ".join(lines))


def build_order_status_whatsapp_components(
    order,
    var_1: str,
    var_2: str,
    header_image_url: Optional[str] = None,
) -> Tuple[Optional[Dict[str, Dict[str, Any]]], Optional[str]]:
    """
    Build MSG91 components dict for order_status template.
    Returns (components, error_message).
    """
    image_url = header_image_url or get_order_header_image_url(order)
    if not image_url:
        return None, "missing order header image (product image or MSG91_ORDER_*_HEADER_IMAGE_URL)"

    components = {
        "header_1": {"type": "image", "value": image_url},
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


def send_order_status_whatsapp(
    order,
    status_message: str,
    *,
    template_name: Optional[str] = None,
    extra_var2_lines: Optional[list] = None,
) -> Tuple[bool, Dict]:
    """Send order_status WhatsApp using UnifiedNotificationService."""
    from Notifications.services import UnifiedNotificationService

    user = order.user
    if not user or not user.phone_number:
        return False, {"error": "user has no phone number"}

    var_1 = format_order_whatsapp_var1(order, status_message)
    var_2 = format_order_whatsapp_var2(order, extra_lines=extra_var2_lines)
    components, err = build_order_status_whatsapp_components(order, var_1, var_2)
    if err:
        return False, {"error": err}

    tpl = template_name or resolve_order_status_whatsapp_template_name()
    if not tpl:
        return False, {"error": "missing MSG91 order status WhatsApp template name"}

    return UnifiedNotificationService.send_whatsapp(
        phone_number=user.phone_number,
        template_name=tpl,
        components=components,
    )
