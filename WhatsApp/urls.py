from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    WhatsAppTemplateViewSet,
    WhatsAppMessageViewSet,
    WhatsAppConfigurationViewSet
)

router = DefaultRouter()
router.register(r'templates', WhatsAppTemplateViewSet, basename='whatsapp-template')
router.register(r'messages', WhatsAppMessageViewSet, basename='whatsapp-message')
router.register(r'config', WhatsAppConfigurationViewSet, basename='whatsapp-config')

urlpatterns = [
    path('', include(router.urls)),
]
