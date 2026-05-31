from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from Notifications.push_images import (
    absolute_media_url,
    get_order_push_image_url,
    get_product_push_image_url,
)


class AbsoluteMediaUrlTests(SimpleTestCase):
    @override_settings(SITE_URL="https://simakfresh.ae")
    def test_relative_path_gets_site_prefix(self):
        self.assertEqual(
            absolute_media_url("/media/products/fish.png"),
            "https://simakfresh.ae/media/products/fish.png",
        )

    def test_absolute_url_unchanged(self):
        url = "https://cdn.example.com/a.png"
        self.assertEqual(absolute_media_url(url), url)


class ProductPushImageTests(SimpleTestCase):
    @override_settings(SITE_URL="https://simakfresh.ae")
    def test_uses_main_product_image(self):
        product = MagicMock()
        product.image.url = "/media/products/salmon.jpg"
        product.images.exclude.return_value.exclude.return_value.filter.return_value.first.return_value = None
        product.images.exclude.return_value.exclude.return_value.first.return_value = None

        self.assertEqual(
            get_product_push_image_url(product),
            "https://simakfresh.ae/media/products/salmon.jpg",
        )

    @override_settings(SITE_URL="https://simakfresh.ae")
    def test_falls_back_to_gallery_when_no_main_image(self):
        product = MagicMock()
        product.image = None
        gallery = MagicMock()
        gallery.image.url = "/media/products/gallery/tuna.jpg"
        qs = product.images.exclude.return_value.exclude.return_value
        qs.filter.return_value.first.return_value = None
        qs.first.return_value = gallery

        self.assertEqual(
            get_product_push_image_url(product),
            "https://simakfresh.ae/media/products/gallery/tuna.jpg",
        )


class OrderPushImageTests(SimpleTestCase):
    @override_settings(
        SITE_URL="https://simakfresh.ae",
        ORDER_STATUS_PUSH_IMAGE_URL="",
        MSG91_ORDER_STATUS_HEADER_IMAGE_URL="https://simakfresh.ae/fallback.png",
        MSG91_ORDER_PENDING_HEADER_IMAGE_URL="",
    )
    def test_order_fallback_when_no_product_images(self):
        order = MagicMock()
        order.items.select_related.return_value.prefetch_related.return_value = []

        self.assertEqual(
            get_order_push_image_url(order),
            "https://simakfresh.ae/fallback.png",
        )
