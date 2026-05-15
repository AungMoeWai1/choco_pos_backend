from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrderViewSet, ReturnOrderViewSet

router = DefaultRouter()
router.register("orders", OrderViewSet, basename="order")
router.register("returns", ReturnOrderViewSet, basename="return-order")

urlpatterns = [path("", include(router.urls))]
