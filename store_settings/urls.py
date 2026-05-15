from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StoreViewSet, TerminalViewSet, ShiftViewSet

router = DefaultRouter()
router.register("stores", StoreViewSet, basename="store")
router.register("terminals", TerminalViewSet, basename="terminal")
router.register("shifts", ShiftViewSet, basename="shift")

urlpatterns = [path("", include(router.urls))]
