from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SMSTemplateViewSet,
    SMSMessageViewSet,
    SMSConfigurationViewSet,
    SMSReportViewSet
)

router = DefaultRouter()
router.register(r'templates', SMSTemplateViewSet, basename='sms-template')
router.register(r'messages', SMSMessageViewSet, basename='sms-message')
router.register(r'config', SMSConfigurationViewSet, basename='sms-config')
router.register(r'reports', SMSReportViewSet, basename='sms-report')

urlpatterns = [
    path('', include(router.urls)),
]
