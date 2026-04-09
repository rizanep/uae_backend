from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrderViewSet, PaymentViewSet, ziina_webhook

router = DefaultRouter()
# Register payments FIRST (more specific routes before catch-all)
router.register(r"payments", PaymentViewSet, basename="payments")
# Register orders with empty prefix (catch-all) LAST
router.register(r"", OrderViewSet, basename="order")

urlpatterns = [
    path("", include(router.urls)),
    path("webhook/ziina/", ziina_webhook, name="ziina-webhook"),
]
