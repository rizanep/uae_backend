"""
Absolute image URLs for FCM rich push notifications on product-related events.
"""
from __future__ import annotations

from typing import Optional

from django.conf import settings


def absolute_media_url(url: str) -> Optional[str]:
    """Turn a relative media path or absolute URL into an HTTPS-ready URL for FCM."""
    url = (url or "").strip()
    if not url:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        return url
    site = (getattr(settings, "SITE_URL", "") or "https://simakfresh.ae").rstrip("/")
    if not url.startswith("/"):
        url = f"/{url}"
    return f"{site}{url}"


def get_product_push_image_url(product) -> Optional[str]:
    """
    Resolve the best product image for push notifications (main image, then gallery).
    """
    if not product:
        return None

    if getattr(product, "image", None):
        try:
            if product.image:
                return absolute_media_url(product.image.url)
        except ValueError:
            pass

    images_qs = product.images.exclude(image="").exclude(image__isnull=True)
    feature = images_qs.filter(is_feature=True).first()
    if feature:
        return absolute_media_url(feature.image.url)

    first_gallery = images_qs.first()
    if first_gallery:
        return absolute_media_url(first_gallery.image.url)

    return None


def get_order_push_image_url(order) -> Optional[str]:
    """
    Product image from order line items, then configured fallbacks.
    """
    items = order.items.select_related("product").prefetch_related("product__images")
    for item in items:
        if not item.product:
            continue
        url = get_product_push_image_url(item.product)
        if url:
            return url

    for fallback in (
        getattr(settings, "ORDER_STATUS_PUSH_IMAGE_URL", ""),
        getattr(settings, "MSG91_ORDER_STATUS_HEADER_IMAGE_URL", ""),
        getattr(settings, "MSG91_ORDER_PENDING_HEADER_IMAGE_URL", ""),
    ):
        value = str(fallback or "").strip()
        if value:
            return value

    return None
