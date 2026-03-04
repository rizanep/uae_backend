from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, NotificationTemplateViewSet, BroadcastViewSet

router = DefaultRouter()
router.register(r'templates', NotificationTemplateViewSet, basename='notification-templates')
router.register(r'broadcasts', BroadcastViewSet, basename='broadcasts')
router.register(r'', NotificationViewSet, basename='notifications')

urlpatterns = router.urls
