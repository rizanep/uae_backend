from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MarketingMediaViewSet


router = DefaultRouter()
router.register(r"media", MarketingMediaViewSet, basename="marketing-media")

urlpatterns = [
    path("", include(router.urls)),
]

