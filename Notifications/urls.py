from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, NotificationTemplateViewSet, BroadcastViewSet, ContactMessageViewSet, FCMDeviceViewSet

router = DefaultRouter()
router.register(r'templates', NotificationTemplateViewSet, basename='notification-templates')
router.register(r'broadcasts', BroadcastViewSet, basename='broadcasts')
router.register(r'contact', ContactMessageViewSet, basename='contact-messages')
router.register(r'devices', FCMDeviceViewSet, basename='fcm-devices')
router.register(r'', NotificationViewSet, basename='notifications')

urlpatterns = router.urls
